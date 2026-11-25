import frappe


def execute():
	"""Defaults for delivery confirmation (on, auto receive after 1 day). Existing deliveries were already
	added to stock from the invoice, so nothing is backfilled."""
	for field, value in (("confirm_deliveries", 1), ("auto_receive_after_days", 1)):
		saved = frappe.db.sql(
			"select 1 from `tabSingles` where doctype = 'Franchise POS Settings' and field = %s", field)
		if not saved:
			frappe.db.set_single_value("Franchise POS Settings", field, value)
