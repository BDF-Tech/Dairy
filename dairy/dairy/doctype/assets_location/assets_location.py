# Copyright (c) 2026, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.model.naming import append_number_if_name_exists


class AssetsLocation(Document):
	def autoname(self):
		# fetch_from values are set after naming, so resolve them here for
		# API / data import inserts that only send the link fields
		asset_name = self.asset_name
		if not asset_name and self.assets_code:
			asset_name = frappe.db.get_value("Item", self.assets_code, "item_name")

		custodian_name = self.custodian_name
		if not custodian_name and self.custodian:
			custodian_name = frappe.db.get_value("Employee", self.custodian, "employee_name")

		parts = [frappe.utils.cstr(part).strip() for part in (asset_name, custodian_name) if part]
		self.name = append_number_if_name_exists(self.doctype, " - ".join(parts) or self.doctype)
