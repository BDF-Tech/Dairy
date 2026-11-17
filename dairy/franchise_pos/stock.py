"""Franchise POS: the franchise's own stock book.

Nothing here touches BDF's Stock Ledger or accounts. A franchise's stock is just the sum of the
rows in `Franchise Stock Ledger`:

	+ Received from BDF   (BDF Sales Invoice submitted for the franchise)
	- Returned to BDF     (BDF credit note / return invoice)
	- Sale                (Franchise Sale = the bill the franchise gives its buyer)
	+ Sale Return         (Franchise Sale return)
	- Wastage             (Franchise Day Close)
	+/- Stock Adjustment  (Franchise Day Close: counted stock vs book stock)
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, now, today

LEDGER = "Franchise Stock Ledger"
SETTINGS = "Franchise POS Settings"


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
	"""SYSTEM ACTION: a cancelled document takes its ledger rows away with it."""
	frappe.db.delete(LEDGER, {"voucher_type": voucher_type, "voucher_no": voucher_no})


# ---------------------------------------------------------------- reads

def get_balances(franchise, upto_date=None, items=None):
	"""{item_code: qty in hand}."""
	cond, vals = "", {"franchise": franchise}
	if upto_date:
		cond += " and posting_date <= %(upto)s"
		vals["upto"] = upto_date
	if items:
		cond += " and item_code in %(items)s"
		vals["items"] = tuple(items)
	rows = frappe.db.sql(
		f"select item_code, sum(qty) from `tab{LEDGER}` where franchise = %(franchise)s {cond} group by item_code", vals
	)
	return {r[0]: flt(r[1], 3) for r in rows}


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


def check_day_open(franchise, posting_date):
	closed = last_closed_date(franchise)
	if closed and getdate(posting_date) <= closed:
		frappe.throw(
			_("The day is already closed up to {0}. Bills cannot be made or changed for {1}.").format(
				frappe.format(closed, {"fieldtype": "Date"}), frappe.format(getdate(posting_date), {"fieldtype": "Date"})
			)
		)


def day_figures(franchise, posting_date):
	"""Per item for one day: opening, received, sold (net of sale returns), returned to BDF, system closing.
	Wastage / adjustment rows of the same day are left out: they are what the Day Close itself decides."""
	rows = frappe.db.sql(
		f"""select l.item_code, max(l.item_name) item_name, max(l.uom) uom,
			sum(if(l.posting_date < %(d)s, l.qty, 0)) opening_qty,
			sum(if(l.posting_date = %(d)s and l.entry_type = 'Received from BDF', l.qty, 0)) received_qty,
			sum(if(l.posting_date = %(d)s and l.entry_type in ('Sale', 'Sale Return'), -l.qty, 0)) sold_qty,
			sum(if(l.posting_date = %(d)s and l.entry_type = 'Returned to BDF', -l.qty, 0)) returned_qty
		from `tab{LEDGER}` l
		where l.franchise = %(f)s and l.posting_date <= %(d)s
			and not (l.posting_date = %(d)s and l.entry_type in ('Wastage', 'Stock Adjustment'))
		group by l.item_code order by item_name""",
		{"f": franchise, "d": posting_date}, as_dict=True,
	)
	out = []
	for r in rows:
		for k in ("opening_qty", "received_qty", "sold_qty", "returned_qty"):
			r[k] = flt(r[k], 3)
		r.expected_qty = flt(r.opening_qty + r.received_qty - r.sold_qty - r.returned_qty, 3)
		if r.opening_qty or r.received_qty or r.sold_qty or r.returned_qty:
			out.append(r)
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
	"""A BDF invoice to a POS franchise = stock received by that franchise.
	A credit note / return invoice has negative quantities = stock returned to BDF."""
	if not is_pos_franchise(doc.customer) or doc.get("is_debit_note"):
		return
	codes = list({d.item_code for d in doc.items if d.item_code})
	if not codes:
		return
	stock_items = set(frappe.get_all("Item", filters={"name": ["in", codes], "is_stock_item": 1}, pluck="name"))
	rows = []
	for d in doc.items:
		if d.item_code not in stock_items:
			continue
		qty = flt(d.stock_qty) or flt(d.qty) * flt(d.conversion_factor or 1)
		rows.append({
			"franchise": doc.customer, "item_code": d.item_code, "item_name": d.item_name, "uom": d.stock_uom,
			"posting_date": doc.posting_date, "posting_time": doc.posting_time, "qty": qty,
			"entry_type": "Returned to BDF" if qty < 0 else "Received from BDF",
			"voucher_type": "Sales Invoice", "voucher_no": doc.name,
		})
	add_ledger_rows(rows)


def on_sales_invoice_cancel(doc, method=None):
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
