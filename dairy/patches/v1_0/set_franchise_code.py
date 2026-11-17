import frappe


def execute():
	"""Franchise Code (the customer code as plain text) on rows made before the field existed."""
	for doctype in ("Franchise Sale", "Franchise Day Close", "Franchise Stock Ledger"):
		frappe.db.sql(f"update `tab{doctype}` set franchise_code = franchise where ifnull(franchise_code, '') = ''")
