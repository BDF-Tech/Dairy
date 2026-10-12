import frappe

# Starting rules for the Logged In Details dashboard. Order matters: the first
# matching rule wins, so specific patterns sit above the general domain rules.
DEFAULT_RULES = [
	{"match_on": "Email Ends With", "value": ".driver@bastardairyfarm.com", "user_type": "Driver", "color": "purple"},
	{"match_on": "Linked Employee", "user_type": "Employee", "color": "blue"},
	{"match_on": "Email Ends With", "value": "@bastardairyfarm.com", "user_type": "Employee", "color": "blue"},
	{"match_on": "Email Ends With", "value": "@bdf.com", "user_type": "Customer", "color": "orange"},
]


def execute():
	frappe.reload_doc("dairy", "doctype", "login_user_type_rule")
	frappe.reload_doc("dairy", "doctype", "logged_in_details_settings")

	settings = frappe.get_single("Logged In Details Settings")
	if settings.user_type_rules:
		return

	for rule in DEFAULT_RULES:
		settings.append("user_type_rules", {"enabled": 1, **rule})
	settings.fallback_user_type = settings.fallback_user_type or "Other"
	settings.save(ignore_permissions=True)
