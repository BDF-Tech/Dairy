import frappe
from frappe.utils import add_months, date_diff, getdate, today

# ---------------------------------------------------------------------------
# Customer License Dashboard
#
# FSSAI food licence status for every customer, from the Customer custom
# fields `food_license_number` and `food_license_validity`.
#
# Status buckets (relative to today):
#   Expired        validity <  today                       -> red
#   Expiring Soon  today <= validity <= today + 3 months   -> yellow
#   Valid          validity >  today + 3 months            -> green
#   Not Set        licence number present but no validity -> grey
# ---------------------------------------------------------------------------

EXPIRING_WINDOW_MONTHS = 3


def _status(validity, cutoff, now):
	if not validity:
		return "Not Set"
	if validity < now:
		return "Expired"
	if validity <= cutoff:
		return "Expiring Soon"
	return "Valid"


@frappe.whitelist()
def get_license_overview(include_disabled=0, include_unlicensed=0):
	include_disabled = frappe.utils.cint(include_disabled)
	include_unlicensed = frappe.utils.cint(include_unlicensed)

	conditions = []
	if not include_disabled:
		conditions.append("c.disabled = 0")
	if not include_unlicensed:
		conditions.append(
			"(ifnull(c.food_license_number, '') != '' or c.food_license_validity is not null)"
		)
	where = ("where " + " and ".join(conditions)) if conditions else ""

	rows = frappe.db.sql(
		f"""select c.name as customer, c.customer_name, c.customer_group, c.territory,
		           c.disabled, c.food_license_number, c.food_license_validity
		    from `tabCustomer` c
		    {where}
		    order by c.food_license_validity is null, c.food_license_validity asc, c.customer_name asc""",
		as_dict=True,
	)

	now = getdate(today())
	cutoff = getdate(add_months(now, EXPIRING_WINDOW_MONTHS))

	# Same licence number on several customers is usually a data-entry slip.
	license_count = {}
	for r in rows:
		lic = (r.food_license_number or "").strip()
		if lic:
			license_count[lic] = license_count.get(lic, 0) + 1

	for r in rows:
		validity = getdate(r.food_license_validity) if r.food_license_validity else None
		r.status = _status(validity, cutoff, now)
		r.days_left = date_diff(validity, now) if validity else None
		r.duplicate = license_count.get((r.food_license_number or "").strip(), 0) > 1

	return {
		"rows": rows,
		"today": str(now),
		"cutoff": str(cutoff),
		"customer_groups": sorted({r.customer_group for r in rows if r.customer_group}),
		"territories": sorted({r.territory for r in rows if r.territory}),
	}
