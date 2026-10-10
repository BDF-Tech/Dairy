# Copyright (c) 2026, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class CustomerCrateLedger(Document):
	def on_trash(self):
		self.validate_vehicle_movement_log_cancelled()

	def validate_vehicle_movement_log_cancelled(self):
		if not self.vehicle_movement_log:
			return

		meta = frappe.get_meta("Vehicle Movement Log")
		fields = ["docstatus"]

		if meta.has_field("workflow_state"):
			fields.append("workflow_state")

		if meta.has_field("status"):
			fields.append("status")

		vehicle_movement_log = frappe.db.get_value(
			"Vehicle Movement Log",
			self.vehicle_movement_log,
			fields,
			as_dict=True,
		)

		if not vehicle_movement_log:
			return

		if (
			vehicle_movement_log.docstatus == 2
			or vehicle_movement_log.get("workflow_state") == "Cancelled"
			or vehicle_movement_log.get("status") == "Cancelled"
		):
			return

		frappe.throw(
			"Cannot delete this Customer Crate Ledger because it is linked "
			f"with Vehicle Movement Log <b>{self.vehicle_movement_log}</b>. "
			"Please cancel the linked Vehicle Movement Log first."
		)
