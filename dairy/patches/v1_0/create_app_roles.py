import frappe

# Roles that decide which home screen the mobile app opens (see mobile.api.APP_DASHBOARD_ROLES).
# Created EMPTY: who gets which role is decided in the ERP (User > Roles), never here.
APP_ROLES = ("App Admin", "App Customer", "App Driver", "App Dispatch", "App Production", "App Security", "App Employee")


def execute():
	for role in APP_ROLES:
		if not frappe.db.exists("Role", role):
			# desk_access 0: these roles only open app screens; they do not give ERP desk access
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 0}).insert(ignore_permissions=True)
