import frappe


def execute():
	"""Module Def must exist before the Customer Service doctypes are synced."""
	if not frappe.db.exists("Module Def", "Customer Service"):
		frappe.get_doc({"doctype": "Module Def", "module_name": "Customer Service", "app_name": "dairy"}).insert(
			ignore_permissions=True
		)
