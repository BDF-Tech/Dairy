import frappe
from frappe.model.document import Document


class LoggedInDetailsSettings(Document):
	def validate(self):
		for row in self.user_type_rules:
			if row.value:
				row.value = row.value.strip().lower()
			row.user_type = (row.user_type or "").strip()
