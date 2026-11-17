import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field

# Created EMPTY. What each role can do is set in Role Permission Manager, and who gets a role is set
# on the User. Nothing here grants access.
ROLES = (
	("Franchise POS User", 0),  # franchise login: bills from the mobile app, no ERP desk
	("Franchise POS Manager", 1),  # BDF sales team / directors: dashboard and reports
)


def execute():
	for role, desk_access in ROLES:
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": desk_access}).insert(
				ignore_permissions=True
			)

	# the switch that puts a customer on Franchise POS
	after = "custom_app_template" if frappe.get_meta("Customer").has_field("custom_app_template") else "customer_group"
	create_custom_field("Customer", {
		"fieldname": "custom_franchise_pos",
		"label": "Franchise POS",
		"fieldtype": "Check",
		"insert_after": after,
		"description": "Tick to give this franchise the POS: its BDF invoices become its stock, and it can bill from the app",
	})

	settings = frappe.get_single("Franchise POS Settings")
	if not settings.mrp_price_list and frappe.db.exists("Price List", "Mrp Price"):
		settings.mrp_price_list = "Mrp Price"
		settings.flags.ignore_permissions = True
		settings.save()
