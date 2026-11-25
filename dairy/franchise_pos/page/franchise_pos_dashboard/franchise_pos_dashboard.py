import frappe
from frappe.desk.reportview import build_match_conditions
from frappe.utils import add_days, flt, getdate, today

from dairy.franchise_pos.stock import get_mrp, pending_close_date

SALE = "Franchise Sale"
LEDGER = "Franchise Stock Ledger"


def stock_now(args, ledger_cond):
	"""Per franchise and item: stock in hand now (last Day Close count + ledger rows after it), and wastage /
	received in the period. Three indexed queries, whatever the size of the ledger."""
	only = " and d.franchise = %(franchise)s" if args.get("franchise") else ""
	last = f"""select franchise, max(posting_date) d from `tabFranchise Day Close` d
		where docstatus = 1 {only} group by franchise"""
	out = {}

	def row(f, code):
		return out.setdefault((f, code), frappe._dict(franchise=f, item_code=code, qty=0.0, wastage=0.0, received=0.0))

	for f, code, qty in frappe.db.sql(
		f"""select d.franchise, i.item_code, i.actual_qty from ({last}) s
		join `tabFranchise Day Close` d on d.franchise = s.franchise and d.posting_date = s.d and d.docstatus = 1
		join `tabFranchise Day Close Item` i on i.parent = d.name and i.parenttype = 'Franchise Day Close'""", args):
		row(f, code).qty += flt(qty)
	for f, code, qty in frappe.db.sql(
		f"""select `tab{LEDGER}`.franchise, `tab{LEDGER}`.item_code, sum(`tab{LEDGER}`.qty) from `tab{LEDGER}`
		left join ({last}) s on s.franchise = `tab{LEDGER}`.franchise
		where `tab{LEDGER}`.posting_date > ifnull(s.d, '1900-01-01') {ledger_cond}
		group by `tab{LEDGER}`.franchise, `tab{LEDGER}`.item_code""", args):
		row(f, code).qty += flt(qty)
	for r in frappe.db.sql(
		f"""select franchise, item_code,
			sum(if(entry_type = 'Wastage', -qty, 0)) wastage, sum(if(entry_type = 'Received from BDF', qty, 0)) received
		from `tab{LEDGER}` where posting_date between %(from_date)s and %(to_date)s
			and entry_type in ('Wastage', 'Received from BDF') {ledger_cond}
		group by franchise, item_code""", args, as_dict=True):
		x = row(r.franchise, r.item_code)
		x.wastage, x.received = flt(r.wastage), flt(r.received)
	return list(out.values())


@frappe.whitelist()
def get_data(from_date=None, to_date=None, franchise=None):
	"""Everything the dashboard shows, for the reader's own permissions.
	Role permission on Franchise Sale opens it; User Permissions on Customer narrow which franchises show."""
	frappe.has_permission(SALE, "read", throw=True)
	to_date = getdate(to_date or today())
	from_date = getdate(from_date or add_days(to_date, -6))
	args = {"from_date": from_date, "to_date": to_date, "franchise": franchise, "today": today()}

	def cond(doctype):
		c = ""
		match = build_match_conditions(doctype)
		if match:
			c += f" and {match}"
		if franchise:
			c += f" and `tab{doctype}`.franchise = %(franchise)s"
		return c

	sign = "if(is_return, -1, 1)"

	# ---- sales per franchise
	sales = frappe.db.sql(
		f"""select franchise, sum(if(is_return, 0, 1)) bills, sum({sign} * grand_total) net_sales,
			sum(if(is_return, grand_total, 0)) returns, max(posting_date) last_bill
		from `tab{SALE}` where docstatus = 1 and posting_date between %(from_date)s and %(to_date)s {cond(SALE)}
		group by franchise""", args, as_dict=True)
	sales = {r.franchise: r for r in sales}

	# ---- stock in hand now + wastage in the period, per franchise and item
	can_stock = frappe.has_permission(LEDGER, "read")
	stock_rows = stock_now(args, cond(LEDGER)) if can_stock else []
	mrp = get_mrp([r.item_code for r in stock_rows])
	stock = {}
	for r in stock_rows:
		s = stock.setdefault(r.franchise, frappe._dict(stock_value=0.0, wastage_value=0.0, received_value=0.0))
		rate = mrp.get(r.item_code, 0)
		s.stock_value += flt(r.qty) * rate
		s.wastage_value += flt(r.wastage) * rate
		s.received_value += flt(r.received) * rate

	# ---- bought from BDF (invoice value) - only for readers who may see Sales Invoices
	bought = {}
	can_invoice = frappe.has_permission("Sales Invoice", "read")
	if can_invoice:
		bought = dict(frappe.db.sql(
			"""select si.customer, sum(si.base_net_total) from `tabSales Invoice` si
			join `tabCustomer` c on c.name = si.customer and c.custom_franchise_pos = 1
			where si.docstatus = 1 and si.posting_date between %(from_date)s and %(to_date)s
				and (%(franchise)s is null or si.customer = %(franchise)s)
			group by si.customer""", args))

	# ---- last day close per franchise
	closes, auto = {}, set()
	if frappe.has_permission("Franchise Day Close", "read"):
		closes = dict(frappe.db.sql(
			f"""select franchise, max(posting_date) from `tabFranchise Day Close`
			where docstatus = 1 {cond('Franchise Day Close')} group by franchise""", args))
		auto = {r[0] for r in frappe.db.sql(
			"""select d.franchise from `tabFranchise Day Close` d
			where d.docstatus = 1 and d.auto_closed = 1 and d.posting_date = (
				select max(x.posting_date) from `tabFranchise Day Close` x where x.franchise = d.franchise and x.docstatus = 1)""")}

	# ---- cash short/extra at day close, in the period
	cash = {}
	if frappe.has_permission("Franchise Day Close", "read"):
		cash = {r.franchise: r for r in frappe.db.sql(
			f"""select franchise, sum(cash_difference) diff, sum(if(cash_difference < 0, cash_difference, 0)) short
			from `tabFranchise Day Close` where docstatus = 1 and posting_date between %(from_date)s and %(to_date)s
				{cond('Franchise Day Close')} group by franchise""", args, as_dict=True)}

	# ---- BDF deliveries: waiting for the franchise, and short / damaged in the period
	deliveries = {}
	if frappe.has_permission("Franchise Stock Receipt", "read"):
		deliveries = {r.franchise: r for r in frappe.db.sql(
			f"""select franchise, sum(docstatus = 0) waiting,
				sum(if(docstatus = 1 and invoice_date between %(from_date)s and %(to_date)s, open_loss_amount, 0)) loss,
				sum(docstatus = 1 and auto_received = 1 and invoice_date between %(from_date)s and %(to_date)s) auto
			from `tabFranchise Stock Receipt` where docstatus < 2 {cond('Franchise Stock Receipt')}
			group by franchise""", args, as_dict=True)}

	# ---- the franchises the reader may see
	cust_filters = {"custom_franchise_pos": 1}
	if franchise:
		cust_filters["name"] = franchise
	customers = frappe.get_list("Customer", filters=cust_filters, fields=["name", "customer_name", "territory", "disabled"],
								order_by="customer_name", limit_page_length=0)
	rows = []
	for c in customers:
		s, st = sales.get(c.name, frappe._dict()), stock.get(c.name, frappe._dict())
		last_close = closes.get(c.name)
		pend = pending_close_date(c.name)
		rows.append({
			"franchise": c.name, "franchise_name": c.customer_name, "territory": c.territory,
			"bought": flt(bought.get(c.name), 2), "received_value": flt(st.get("received_value"), 2),
			"net_sales": flt(s.get("net_sales"), 2), "bills": int(s.get("bills") or 0),
			"returns": flt(s.get("returns"), 2), "stock_value": flt(st.get("stock_value"), 2),
			"wastage_value": flt(st.get("wastage_value"), 2),
			"last_bill": s.get("last_bill"), "last_close": last_close, "last_close_auto": c.name in auto,
			"pending_close": pend,
			"close_pending": bool(pend),
			"cash_difference": flt((cash.get(c.name) or {}).get("diff"), 2),
			"cash_short": flt((cash.get(c.name) or {}).get("short"), 2),
			"deliveries_waiting": int((deliveries.get(c.name) or {}).get("waiting") or 0),
			"delivery_loss": flt((deliveries.get(c.name) or {}).get("loss"), 2),
			"deliveries_auto": int((deliveries.get(c.name) or {}).get("auto") or 0),
		})
	rows.sort(key=lambda r: -r["net_sales"])

	# ---- day-wise trend, top items, payment split
	trend = frappe.db.sql(
		f"""select posting_date, sum({sign} * grand_total) amount, sum(if(is_return, 0, 1)) bills
		from `tab{SALE}` where docstatus = 1 and posting_date between %(from_date)s and %(to_date)s {cond(SALE)}
		group by posting_date order by posting_date""", args, as_dict=True)
	items = frappe.db.sql(
		f"""select i.item_code, max(i.item_name) item_name, max(i.uom) uom,
			sum({sign} * i.qty) qty, sum({sign} * i.amount) amount
		from `tabFranchise Sale Item` i join `tab{SALE}` on `tab{SALE}`.name = i.parent
		where `tab{SALE}`.docstatus = 1 and `tab{SALE}`.posting_date between %(from_date)s and %(to_date)s {cond(SALE)}
		group by i.item_code order by amount desc limit 10""", args, as_dict=True)
	modes = frappe.db.sql(
		f"""select payment_mode, sum({sign} * grand_total) amount
		from `tab{SALE}` where docstatus = 1 and posting_date between %(from_date)s and %(to_date)s {cond(SALE)}
		group by payment_mode order by amount desc""", args, as_dict=True)
	billed_today = frappe.db.sql(
		f"""select count(distinct franchise) from `tab{SALE}`
		where docstatus = 1 and is_return = 0 and posting_date = %(today)s {cond(SALE)}""", args)[0][0]

	return {
		"from_date": str(from_date), "to_date": str(to_date),
		"can_invoice": bool(can_invoice), "can_stock": bool(can_stock),
		"can_cash": frappe.has_permission("Franchise Day Close", "read"),
		"can_delivery": frappe.has_permission("Franchise Stock Receipt", "read"),
		"kpi": {
			"net_sales": sum(r["net_sales"] for r in rows),
			"bills": sum(r["bills"] for r in rows),
			"bought": sum(r["bought"] for r in rows),
			"stock_value": sum(r["stock_value"] for r in rows),
			"wastage_value": sum(r["wastage_value"] for r in rows),
			"franchises": len([r for r in rows]),
			"billed_today": billed_today,
			"close_pending": len([r for r in rows if r["close_pending"]]),
			"cash_short": sum(r["cash_short"] for r in rows),
			"deliveries_waiting": sum(r["deliveries_waiting"] for r in rows),
			"delivery_loss": sum(r["delivery_loss"] for r in rows),
		},
		"franchises": rows, "trend": trend, "items": items, "modes": modes,
	}
