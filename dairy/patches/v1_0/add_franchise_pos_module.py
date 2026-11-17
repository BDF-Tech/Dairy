import frappe


def execute():
	"""Module Def must exist before the Franchise POS doctypes are synced."""
	if not frappe.db.exists("Module Def", "Franchise POS"):
		frappe.get_doc({"doctype": "Module Def", "module_name": "Franchise POS", "app_name": "dairy"}).insert(
			ignore_permissions=True
		)
