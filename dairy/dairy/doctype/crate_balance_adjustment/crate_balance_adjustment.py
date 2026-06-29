import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CrateBalanceAdjustment(Document):

    def validate(self):
        if not self.crates:
            frappe.throw("Crates cannot be zero.")

    def on_submit(self):
        self._create_ledger_entry()
        self._update_master_balance(flt(self.crates))

    def on_cancel(self):
        self._delete_ledger_entry()
        self._update_master_balance(-flt(self.crates))

    # =========================================================
    # LEDGER
    # =========================================================

    def _create_ledger_entry(self):
        crates = flt(self.crates)
        ledger = frappe.new_doc("Customer Crate Ledger")
        ledger.posting_date   = self.date
        ledger.entry_type     = self.entry_type       # "Opening" or "Adjustment"
        ledger.crate_category = self.entry_type
        ledger.crate_delivery = self.name             # reference back to this doc

        if self.party_type == "Customer":
            ledger.ledger_type  = "Customer"
            ledger.customer     = self.customer
            ledger.crates_out   = crates if crates > 0 else 0
            ledger.crates_in    = abs(crates) if crates < 0 else 0
            ledger.balance_crates = flt(
                frappe.db.get_value("Customer", self.customer, "custom_current_crate_balance")
            ) + crates

        elif self.party_type == "Driver":
            ledger.ledger_type  = "Driver"
            ledger.driver       = self.driver
            ledger.crates_out   = crates if crates > 0 else 0
            ledger.crates_in    = abs(crates) if crates < 0 else 0
            ledger.balance_crates = flt(
                frappe.db.get_value("Driver", self.driver, "custom_invoice_crate_balance")
            ) + crates

        ledger.insert(ignore_permissions=True)

    def _delete_ledger_entry(self):
        name = frappe.db.get_value(
            "Customer Crate Ledger",
            {"crate_delivery": self.name},
            "name"
        )
        if name:
            frappe.delete_doc("Customer Crate Ledger", name, ignore_permissions=True)

    # =========================================================
    # MASTER BALANCE
    # =========================================================

    def _update_master_balance(self, delta):
        if self.party_type == "Customer" and self.customer:
            current = flt(frappe.db.get_value("Customer", self.customer, "custom_current_crate_balance"))
            frappe.db.set_value("Customer", self.customer, "custom_current_crate_balance", max(0, current + delta))

        elif self.party_type == "Driver" and self.driver:
            current = flt(frappe.db.get_value("Driver", self.driver, "custom_invoice_crate_balance"))
            frappe.db.set_value("Driver", self.driver, "custom_invoice_crate_balance", max(0, current + delta))
