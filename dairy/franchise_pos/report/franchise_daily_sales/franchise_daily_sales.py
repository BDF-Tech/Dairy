import frappe
from frappe import _
from frappe.desk.reportview import build_match_conditions
from frappe.utils import add_days, today

SALE = "Franchise Sale"


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.to_date = filters.to_date or today()
	filters.from_date = filters.from_date or add_days(filters.to_date, -6)
	return get_columns(), get_data(filters)


def get_columns():
	cur = lambda label, name, width=110: {"label": _(label), "fieldname": name, "fieldtype": "Currency", "width": width}
	return [
		{"label": _("Date"), "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
		# plain text on purpose: a Link to Customer would show the customer's name, not the code
		{"label": _("Franchise"), "fieldname": "franchise", "fieldtype": "Data", "width": 110},
		{"label": _("Franchise Name"), "fieldname": "franchise_name", "fieldtype": "Data", "width": 190},
		{"label": _("Bills"), "fieldname": "bill_count", "fieldtype": "Int", "width": 70},
		{"label": _("Qty Sold"), "fieldname": "qty", "fieldtype": "Float", "width": 90},
		cur("Sales", "total_sales"), cur("Sale Returns", "return_amount"), cur("Net Sales", "net_sales", 120),
		cur("Cash", "cash_sales", 100), cur("UPI", "upi_sales", 100), cur("Card", "card_sales", 100),
		cur("Credit", "credit_sales", 100),
		{"label": _("Day Closed"), "fieldname": "day_closed", "fieldtype": "Data", "width": 100},
	]


def get_data(filters):
	# the reader's own permissions (role + User Permissions on Customer) decide which franchises show
	frappe.has_permission(SALE, "read", throw=True)
	cond = ""
	match = build_match_conditions(SALE)
	if match:
		cond += f" and {match}"
	if filters.franchise:
		cond += " and franchise = %(franchise)s"

	sign = "if(is_return, -1, 1)"
	rows = frappe.db.sql(
		f"""select posting_date, franchise, max(franchise_name) franchise_name,
			sum(if(is_return, 0, 1)) bill_count,
			sum({sign} * total_qty) qty,
			sum(if(is_return, 0, grand_total)) total_sales,
			sum(if(is_return, grand_total, 0)) return_amount,
			sum({sign} * grand_total) net_sales,
			sum(if(payment_mode = 'Cash', {sign} * grand_total, 0)) cash_sales,
			sum(if(payment_mode = 'UPI', {sign} * grand_total, 0)) upi_sales,
			sum(if(payment_mode = 'Card', {sign} * grand_total, 0)) card_sales,
			sum(if(payment_mode = 'Credit', {sign} * grand_total, 0)) credit_sales
		from `tab{SALE}`
		where docstatus = 1 and posting_date between %(from_date)s and %(to_date)s {cond}
		group by posting_date, franchise
		order by posting_date desc, franchise_name""",
		filters, as_dict=True,
	)
	closed = set()
	if rows and frappe.has_permission("Franchise Day Close", "read"):
		closed = {
			(d.franchise, d.posting_date)
			for d in frappe.get_list("Franchise Day Close", fields=["franchise", "posting_date"], limit_page_length=0,
									filters={"docstatus": 1, "posting_date": ["between", [filters.from_date, filters.to_date]]})
		}
	for r in rows:
		r.day_closed = _("Yes") if (r.franchise, r.posting_date) in closed else _("No")
	return rows
