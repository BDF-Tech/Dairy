import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime


class MaterialGatePass(Document):

    def before_save(self):
        if not self.time:
            self.time = now_datetime().strftime("%H:%M:%S")

    def validate(self):
        if not self.gate_pass_type:
            frappe.throw("Gate Pass Type is required.")
        if not self.trip_type:
            frappe.throw("Trip Type is required.")
        if self.gate_pass_type == "Transfer" and self.from_location == self.to_location:
            frappe.throw("From Location and To Location cannot be the same.")
        if not self.items:
            frappe.throw("Please add at least one item in Outgoing Items.")
