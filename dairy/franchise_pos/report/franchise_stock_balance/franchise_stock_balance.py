import frappe
from frappe import _
from frappe.desk.reportview import build_match_conditions
from frappe.utils import add_days, flt, today

from dairy.franchise_pos.stock import get_mrp

LEDGER = "Franchise Stock Ledger"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.to_date = filters.to_date or today()
	filters.from_date = filters.from_date or filters.to_date
	return get_columns(), get_data(filters)


def get_columns():
	qty = lambda label, name: {"label": _(label), "fieldname": name, "fieldtype": "Float", "width": 100}
	return [
		# plain text on purpose: a Link to Customer would show the customer's name, not the code
		{"label": _("Franchise"), "fieldname": "franchise", "fieldtype": "Data", "width": 110},
		{"label": _("Franchise Name"), "fieldname": "franchise_name", "fieldtype": "Data", "width": 180},
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 110},
		{"label": _("Item Name"), "fieldname": "item_name", "fieldtype": "Data", "width": 200},
		{"label": _("UOM"), "fieldname": "uom", "fieldtype": "Data", "width": 60},
		qty("Opening", "opening_qty"), qty("Received", "received_qty"), qty("Sold", "sold_qty"),
		qty("Returned to BDF", "returned_qty"), qty("Wastage", "wastage_qty"), qty("Adjustment", "adjustment_qty"),
		qty("Closing", "closing_qty"),
		{"label": _("MRP"), "fieldname": "mrp", "fieldtype": "Currency", "width": 90},
		{"label": _("Stock Value (MRP)"), "fieldname": "stock_value", "fieldtype": "Currency", "width": 130},
	]


def get_data(filters):
	# the reader's own permissions (role + User Permissions on Customer) decide which franchises show
	frappe.has_permission(LEDGER, "read", throw=True)
	cond = ""
	match = build_match_conditions(LEDGER)
	if match:
		cond += f" and {match}"
	if filters.franchise:
		cond += " and franchise = %(franchise)s"
	if filters.item_code:
		cond += " and item_code = %(item_code)s"

	rows = frappe.db.sql(
		f"""select franchise, item_code, max(item_name) item_name, max(uom) uom,
			sum(if(posting_date < %(from_date)s, qty, 0)) opening_qty,
			sum(if(posting_date >= %(from_date)s and entry_type = 'Received from BDF', qty, 0)) received_qty,
			sum(if(posting_date >= %(from_date)s and entry_type in ('Sale', 'Sale Return'), -qty, 0)) sold_qty,
			sum(if(posting_date >= %(from_date)s and entry_type = 'Returned to BDF', -qty, 0)) returned_qty,
			sum(if(posting_date >= %(from_date)s and entry_type = 'Wastage', -qty, 0)) wastage_qty,
			sum(if(posting_date >= %(from_date)s and entry_type = 'Stock Adjustment', qty, 0)) adjustment_qty,
			sum(qty) closing_qty
		from `tab{LEDGER}`
		where posting_date <= %(to_date)s {cond}
		group by franchise, item_code
		order by franchise, item_name""",
		filters, as_dict=True,
	)
	names = dict(frappe.get_all("Customer", filters={"name": ["in", list({r.franchise for r in rows})]},
								fields=["name", "customer_name"], as_list=True)) if rows else {}
	mrp = get_mrp([r.item_code for r in rows], filters.to_date)
	out = []
	for r in rows:
		if not any(flt(r[k]) for k in ("opening_qty", "received_qty", "sold_qty", "returned_qty", "wastage_qty",
										"adjustment_qty", "closing_qty")):
			continue
		r.franchise_name = names.get(r.franchise)
		r.mrp = mrp.get(r.item_code, 0)
		r.stock_value = flt(flt(r.closing_qty) * r.mrp, 2)
		out.append(r)
	return out
