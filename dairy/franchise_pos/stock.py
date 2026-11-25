"""Franchise POS: the franchise's own stock book.

Nothing here touches BDF's Stock Ledger or accounts. A franchise's stock is just the sum of the
rows in `Franchise Stock Ledger`:

	+ Received from BDF   (Franchise Stock Receipt: the franchise confirms the BDF delivery, short/damaged left out;
	                       or the BDF Sales Invoice itself when "Franchise must confirm delivery" is off)
	- Returned to BDF     (BDF credit note / return invoice)
	- Sale                (Franchise Sale = the bill the franchise gives its buyer)
	+ Sale Return         (Franchise Sale return)
	- Wastage             (Franchise Day Close)
	+/- Stock Adjustment  (Franchise Day Close: counted stock vs book stock)
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate, now, nowtime, today

LEDGER = "Franchise Stock Ledger"
SETTINGS = "Franchise POS Settings"
RECEIPT = "Franchise Stock Receipt"


def is_pos_franchise(customer):
	"""Franchise POS is switched on per customer (Customer > Franchise POS tick)."""
	return bool(customer and frappe.get_cached_value("Customer", customer, "custom_franchise_pos"))


def need_pos_franchise(customer):
	if not is_pos_franchise(customer):
		frappe.throw(_("Franchise POS is not switched on for customer {0}.").format(frappe.bold(customer or "")))


def get_settings():
	return frappe.get_cached_doc(SETTINGS)


# ---------------------------------------------------------------- ledger writes (system only)

def add_ledger_rows(rows):
	"""SYSTEM ACTION: ledger rows are written only by code, as a result of a submitted document.
	No user ever gets Create on Franchise Stock Ledger, so nobody can add stock by hand."""
	rows = [r for r in rows if flt(r.get("qty"))]
	if not rows:
		return
	ts, user = now(), frappe.session.user
	fields = ["name", "creation", "modified", "owner", "modified_by", "docstatus", "franchise", "franchise_code", "item_code",
			"item_name",
			"uom", "posting_date", "posting_time", "qty", "entry_type", "voucher_type", "voucher_no", "remarks"]
	values = [
		(frappe.generate_hash(length=12), ts, ts, user, user, 0, r["franchise"], r["franchise"], r["item_code"],
		r.get("item_name"),
		r.get("uom"), r["posting_date"], r.get("posting_time"), flt(r["qty"]), r["entry_type"], r["voucher_type"],
		r["voucher_no"], r.get("remarks"))
		for r in rows
	]
	frappe.db.bulk_insert(LEDGER, fields, values)


def remove_ledger_rows(voucher_type, voucher_no):
	"""SYSTEM ACTION: a cancelled document takes its ledger rows away with it.
	A row on a day that is already closed is never changed: the closed day's counted stock is the starting point
	for every later balance (see get_balances). Such a row is reversed on the first open day instead."""
	rows = frappe.get_all(
		LEDGER, filters={"voucher_type": voucher_type, "voucher_no": voucher_no},
		fields=["name", "franchise", "item_code", "item_name", "uom", "posting_date", "qty", "entry_type"],
	)
	if not rows:
		return
	closed, delete, reverse = {}, [], []
	for r in rows:
		if r.franchise not in closed:
			closed[r.franchise] = last_closed_date(r.franchise)
		c = closed[r.franchise]
		(reverse if c and getdate(r.posting_date) <= c else delete).append(r)
	if delete:
		frappe.db.delete(LEDGER, {"name": ["in", [r.name for r in delete]]})
	add_ledger_rows([{
		"franchise": r.franchise, "item_code": r.item_code, "item_name": r.item_name, "uom": r.uom,
		"posting_date": receipt_stock_date(r.franchise, today()), "posting_time": nowtime(), "qty": -flt(r.qty),
		"entry_type": r.entry_type, "voucher_type": voucher_type, "voucher_no": voucher_no,
		"remarks": f"{voucher_no} cancelled after {_fmt(r.posting_date)} was closed",
	} for r in reverse])


# ---------------------------------------------------------------- reads

def close_snapshot(franchise, on_or_before=None, before=None, items=None):
	"""The counted closing stock of the latest submitted Day Close (on or before / strictly before a date).
	Returns (close date, {item_code: row with qty, item_name, uom}); (None, {}) when no day is closed yet.
	Every later balance starts from here and adds only the ledger rows after that day, so reading stock costs the
	same on day 1 and in year 5. Closed days never change (see remove_ledger_rows), which keeps this exact."""
	cond, vals = "", {"f": franchise}
	if on_or_before:
		cond += " and posting_date <= %(d)s"
		vals["d"] = getdate(on_or_before)
	if before:
		cond += " and posting_date < %(b)s"
		vals["b"] = getdate(before)
	close = frappe.db.sql(
		f"""select name, posting_date from `tabFranchise Day Close`
		where franchise = %(f)s and docstatus = 1 {cond} order by posting_date desc limit 1""", vals)
	if not close:
		return None, {}
	icond, ivals = "", {"p": close[0][0]}
	if items:
		icond = " and item_code in %(items)s"
		ivals["items"] = tuple(items)
	rows = frappe.db.sql(
		f"""select item_code, item_name, uom, actual_qty qty from `tabFranchise Day Close Item`
		where parent = %(p)s and parenttype = 'Franchise Day Close' {icond}""", ivals, as_dict=True)
	return getdate(close[0][1]), {r.item_code: r for r in rows}


def get_balances(franchise, upto_date=None, items=None):
	"""{item_code: qty in hand}: the last Day Close count + the ledger rows after it."""
	since, base = close_snapshot(franchise, on_or_before=upto_date, items=items)
	out = {code: flt(r.qty) for code, r in base.items()}
	cond, vals = "", {"franchise": franchise}
	if since:
		cond += " and posting_date > %(since)s"
		vals["since"] = since
	if upto_date:
		cond += " and posting_date <= %(upto)s"
		vals["upto"] = upto_date
	if items:
		cond += " and item_code in %(items)s"
		vals["items"] = tuple(items)
	rows = frappe.db.sql(
		f"select item_code, sum(qty) from `tab{LEDGER}` where franchise = %(franchise)s {cond} group by item_code", vals
	)
	for code, qty in rows:
		out[code] = out.get(code, 0) + flt(qty)
	return {code: flt(qty, 3) for code, qty in out.items()}


def get_mrp(item_codes, on_date=None):
	"""{item_code: MRP per stock unit} from the MRP price list in Franchise POS Settings."""
	item_codes = tuple(set(item_codes or []))
	if not item_codes:
		return {}
	price_list = get_settings().mrp_price_list
	if not price_list:
		frappe.throw(_("Set the MRP Price List in Franchise POS Settings."))
	rows = frappe.db.sql(
		"""select ip.item_code, ip.price_list_rate
		from `tabItem Price` ip join `tabItem` i on i.name = ip.item_code
		where ip.price_list = %(pl)s and ip.selling = 1 and ip.item_code in %(items)s
			and (ifnull(ip.uom, '') = '' or ip.uom = i.stock_uom)
			and ifnull(ip.customer, '') = ''
			and (ip.valid_from is null or ip.valid_from <= %(d)s)
			and (ip.valid_upto is null or ip.valid_upto >= %(d)s)
		order by ip.valid_from asc, ip.modified asc""",
		{"pl": price_list, "items": item_codes, "d": on_date or today()},
	)
	return {r[0]: flt(r[1]) for r in rows}  # the newest valid price wins


def last_closed_date(franchise, exclude=None):
	cond = "and name != %(x)s" if exclude else ""
	d = frappe.db.sql(
		f"select max(posting_date) from `tabFranchise Day Close` where franchise = %(f)s and docstatus = 1 {cond}",
		{"f": franchise, "x": exclude},
	)[0][0]
	return getdate(d) if d else None


def pos_start_date(franchise):
	"""The shop's first Franchise POS day: when its first stock reached the POS or its first bill, whichever is
	earlier. Days before that never need a close."""
	d = frappe.db.sql(
		f"""select least(
			ifnull((select min(date(creation)) from `tab{LEDGER}` where franchise = %(f)s), '9999-12-31'),
			ifnull((select min(posting_date) from `tabFranchise Sale` where franchise = %(f)s and docstatus = 1), '9999-12-31'))""",
		{"f": franchise},
	)[0][0]
	d = getdate(d) if d else None
	return None if not d or d.year == 9999 else d


def pending_close_date(franchise, before=None):
	"""The oldest day before `before` (default today) that is not closed yet; None = nothing pending.
	EVERY day counts, with or without bills (the user's rule, 2026-11-18): days are closed one after another,
	starting from the shop's first POS day."""
	closed = last_closed_date(franchise)
	nxt = getdate(add_days(closed, 1)) if closed else pos_start_date(franchise)
	if nxt and nxt < getdate(before or today()):
		return nxt
	return None


def pending_receipts(franchise, upto_date=None):
	"""BDF deliveries the franchise has not confirmed yet (optionally only those invoiced up to a date)."""
	filters = {"franchise": franchise, "docstatus": 0}
	if upto_date:
		filters["invoice_date"] = ["<=", getdate(upto_date)]
	return frappe.get_all(RECEIPT, filters=filters, fields=["name", "sales_invoice", "invoice_date", "total_invoiced_qty"],
						order_by="invoice_date, creation")


def receipt_stock_date(franchise, invoice_date):
	"""The franchise day a confirmed delivery is booked on: the invoice date, but never a closed day and never
	after today (if today is already closed, tomorrow)."""
	day = min(getdate(invoice_date), getdate(today()))
	closed = last_closed_date(franchise)
	if closed and day <= closed:
		day = getdate(add_days(closed, 1))
	return day


def invoice_stock_rows(sales_invoice):
	"""Stock items of a BDF invoice in stock units, one row per item: qty and net rate per stock unit."""
	rows = frappe.db.sql(
		"""select sii.item_code, max(sii.item_name) item_name, max(sii.stock_uom) uom,
			sum(ifnull(nullif(sii.stock_qty, 0), sii.qty * ifnull(nullif(sii.conversion_factor, 0), 1))) qty,
			sum(sii.base_net_amount) amount
		from `tabSales Invoice Item` sii join `tabItem` i on i.name = sii.item_code and i.is_stock_item = 1
		where sii.parent = %s and sii.parenttype = 'Sales Invoice'
		group by sii.item_code order by min(sii.idx)""",
		sales_invoice, as_dict=True,
	)
	for r in rows:
		r.qty = flt(r.qty, 3)
		r.rate = flt(flt(r.amount) / r.qty, 4) if r.qty else 0
	return rows


def _fmt(d):
	return frappe.format(getdate(d), {"fieldtype": "Date"})


def check_day_open(franchise, posting_date, need_previous_closed=True):
	"""A bill can be made only on a day that is not closed, and (for new bills) only after every
	earlier day with bills has been closed."""
	closed = last_closed_date(franchise)
	if closed and getdate(posting_date) <= closed:
		frappe.throw(
			_("The day is already closed up to {0}. Bills cannot be made or changed for {1}.").format(
				_fmt(closed), _fmt(posting_date)
			)
		)
	if need_previous_closed:
		pending = pending_close_date(franchise, before=posting_date)
		if pending:
			frappe.throw(
				_("Close the day for {0} first. Billing opens after that.").format(_fmt(pending)),
				title=_("Day close pending"),
			)


def auto_close_days():
	"""SYSTEM ACTION (scheduler, hourly): a day with bills that is still not closed after
	"Auto close after (days)" is closed by the system with the book stock as the count and no wastage.
	It is marked Auto Closed so the sales team can see that nobody counted the stock."""
	after = get_settings().auto_close_after_days
	after = 2 if after is None else int(after)
	if after <= 0:
		return
	cutoff = getdate(add_days(today(), -after))
	for franchise in frappe.get_all("Customer", filters={"custom_franchise_pos": 1, "disabled": 0}, pluck="name"):
		try:
			for _i in range(31):  # at most a month of missed days per run
				day = pending_close_date(franchise)
				if not day or day > cutoff:
					break
				# a day cannot close with a delivery still waiting: the system takes it in full first
				_auto_receive(franchise, upto_date=day)
				doc = frappe.get_doc({
					"doctype": "Franchise Day Close", "franchise": franchise, "posting_date": day,
					"auto_closed": 1, "remarks": _("Closed by the system: not closed by the franchise within {0} days.").format(after),
				})
				doc.flags.ignore_permissions = True
				doc.insert()
				doc.submit()
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(frappe.get_traceback(), f"Franchise POS auto close failed: {franchise}")


def _auto_receive(franchise, upto_date):
	from dairy.franchise_pos.doctype.franchise_stock_receipt.franchise_stock_receipt import confirm

	for r in pending_receipts(franchise, upto_date):
		confirm(frappe.get_doc(RECEIPT, r.name), auto=True)


def auto_receive_deliveries():
	"""SYSTEM ACTION (scheduler, hourly): a delivery not confirmed within "Auto receive after (days)" of its invoice
	date is taken in full by the system and marked Auto Received."""
	after = get_settings().auto_receive_after_days
	after = 1 if after is None else int(after)
	if after <= 0:
		return
	cutoff = getdate(add_days(today(), -after))
	for franchise in frappe.get_all(RECEIPT, filters={"docstatus": 0, "invoice_date": ["<=", cutoff]}, pluck="franchise",
									distinct=True):
		try:
			_auto_receive(franchise, cutoff)
			frappe.db.commit()
		except Exception:
			frappe.db.rollback()
			frappe.log_error(frappe.get_traceback(), f"Franchise POS auto receive failed: {franchise}")


def run_hourly():
	auto_receive_deliveries()
	auto_close_days()


def day_figures(franchise, posting_date):
	"""Per item for one day: opening, received, sold (net of sale returns), returned to BDF, system closing.
	Wastage / adjustment rows of the same day are left out: they are what the Day Close itself decides.
	Opening = the last Day Close count before this day + the ledger rows after it (normally none)."""
	posting_date = getdate(posting_date)
	since, base = close_snapshot(franchise, before=posting_date)
	rows = frappe.db.sql(
		f"""select l.item_code, max(l.item_name) item_name, max(l.uom) uom,
			sum(if(l.posting_date < %(d)s, l.qty, 0)) opening_qty,
			sum(if(l.posting_date = %(d)s and l.entry_type = 'Received from BDF', l.qty, 0)) received_qty,
			sum(if(l.posting_date = %(d)s and l.entry_type in ('Sale', 'Sale Return'), -l.qty, 0)) sold_qty,
			sum(if(l.posting_date = %(d)s and l.entry_type = 'Returned to BDF', -l.qty, 0)) returned_qty
		from `tab{LEDGER}` l
		where l.franchise = %(f)s and l.posting_date > %(since)s and l.posting_date <= %(d)s
			and not (l.posting_date = %(d)s and l.entry_type in ('Wastage', 'Stock Adjustment'))
		group by l.item_code""",
		{"f": franchise, "d": posting_date, "since": since or "1900-01-01"}, as_dict=True,
	)
	moved = {r.item_code: r for r in rows}
	for code, b in base.items():
		r = moved.get(code)
		if r:
			r.opening_qty = flt(r.opening_qty) + flt(b.qty)
		else:
			moved[code] = frappe._dict(item_code=code, item_name=b.item_name, uom=b.uom, opening_qty=flt(b.qty),
									received_qty=0, sold_qty=0, returned_qty=0)
	out = []
	for r in moved.values():
		for k in ("opening_qty", "received_qty", "sold_qty", "returned_qty"):
			r[k] = flt(r[k], 3)
		r.expected_qty = flt(r.opening_qty + r.received_qty - r.sold_qty - r.returned_qty, 3)
		if r.opening_qty or r.received_qty or r.sold_qty or r.returned_qty:
			out.append(r)
	out.sort(key=lambda r: r.item_name or "")
	return out


def day_sales(franchise, posting_date):
	"""Bill totals of one day, split by payment mode (returns are taken off)."""
	rows = frappe.db.sql(
		"""select payment_mode, is_return, count(*) n, sum(grand_total) amount
		from `tabFranchise Sale` where franchise = %s and posting_date = %s and docstatus = 1
		group by payment_mode, is_return""",
		(franchise, posting_date), as_dict=True,
	)
	out = frappe._dict(bill_count=0, total_sales=0.0, return_amount=0.0, net_sales=0.0,
					cash_sales=0.0, upi_sales=0.0, card_sales=0.0, credit_sales=0.0)
	for r in rows:
		amount = flt(r.amount)
		key = f"{(r.payment_mode or 'Cash').lower()}_sales"
		if r.is_return:
			out.return_amount += amount
			out[key] = out.get(key, 0) - amount
		else:
			out.bill_count += r.n
			out.total_sales += amount
			out[key] = out.get(key, 0) + amount
	out.net_sales = flt(out.total_sales - out.return_amount, 2)
	return out


# ---------------------------------------------------------------- BDF Sales Invoice -> franchise stock

def on_sales_invoice_submit(doc, method=None):
	"""A BDF invoice to a POS franchise = a delivery. The franchise confirms it (Franchise Stock Receipt) and only
	the good quantity becomes its stock. A credit note against an invoice with a delivery goes through that delivery
	(see apply_credit_note); any other credit note (negative quantities) = stock returned to BDF, booked at once."""
	if not is_pos_franchise(doc.customer) or doc.get("is_debit_note"):
		return
	rows = invoice_stock_rows(doc.name)
	if not rows:
		return
	day = receipt_stock_date(doc.customer, doc.posting_date)  # never book on a day already closed
	confirm_needed = get_settings().confirm_deliveries

	def ledger_row(r):
		return {
			"franchise": doc.customer, "item_code": r.item_code, "item_name": r.item_name, "uom": r.uom,
			"posting_date": day, "posting_time": doc.posting_time, "qty": r.qty,
			"entry_type": "Returned to BDF" if r.qty < 0 else "Received from BDF",
			"voucher_type": "Sales Invoice", "voucher_no": doc.name,
		}

	if doc.get("is_return"):
		receipt = doc.get("return_against") and frappe.db.get_value(
			RECEIPT, {"sales_invoice": doc.return_against, "docstatus": ["<", 2]})
		if receipt:
			from dairy.franchise_pos.doctype.franchise_stock_receipt.franchise_stock_receipt import apply_credit_note

			add_ledger_rows([ledger_row(r) for r in apply_credit_note(receipt, doc)])
		else:
			add_ledger_rows([ledger_row(r) for r in rows if r.qty < 0])
		return

	ledger = [ledger_row(r) for r in rows if r.qty < 0 or not confirm_needed]
	add_ledger_rows(ledger)
	if confirm_needed and any(r.qty > 0 for r in rows):
		# SYSTEM ACTION: the dispatch user submitting the invoice is not the one who confirms it
		receipt = frappe.get_doc({"doctype": RECEIPT, "franchise": doc.customer, "sales_invoice": doc.name})
		receipt.flags.ignore_permissions = True
		receipt.insert()


def on_sales_invoice_cancel(doc, method=None):
	if doc.get("is_return") and doc.get("return_against"):
		from dairy.franchise_pos.doctype.franchise_stock_receipt.franchise_stock_receipt import remove_credit_note

		for name in frappe.get_all(RECEIPT, filters={"sales_invoice": doc.return_against, "docstatus": ["<", 2]}, pluck="name"):
			remove_credit_note(name, doc.name)
	for r in frappe.get_all(RECEIPT, filters={"sales_invoice": doc.name, "docstatus": ["<", 2]}, fields=["name", "docstatus"]):
		if r.docstatus == 0:
			frappe.delete_doc(RECEIPT, r.name, ignore_permissions=True, force=True)
		else:
			receipt = frappe.get_doc(RECEIPT, r.name)
			receipt.flags.ignore_permissions = True
			receipt.flags.from_invoice_cancel = True
			receipt.cancel()
	if frappe.db.exists(LEDGER, {"voucher_type": "Sales Invoice", "voucher_no": doc.name}):
		remove_ledger_rows("Sales Invoice", doc.name)


# ---------------------------------------------------------------- desk helper

@frappe.whitelist()
def get_item_info(franchise, item_code):
	"""Desk form: MRP and stock in hand when an item is picked on a Franchise Sale."""
	frappe.has_permission("Franchise Sale", "read", throw=True)
	item = frappe.get_cached_value("Item", item_code, ["item_name", "stock_uom"], as_dict=True)
	return {
		"item_name": item.item_name, "uom": item.stock_uom,
		"rate": get_mrp([item_code]).get(item_code, 0),
		"balance": get_balances(franchise, items=[item_code]).get(item_code, 0),
	}
