import frappe
from frappe.model.document import Document
from frappe.utils import flt


@frappe.whitelist()
def get_party_crate_balances(party_type, party):
    """Return current crate balances for display in the form."""
    if party_type == "Customer":
        balance = flt(frappe.db.get_value("Customer", party, "custom_current_crate_balance"))
        return {"type": "customer", "invoice_balance": balance}

    elif party_type == "Driver":
        invoice_balance = flt(frappe.db.get_value("Driver", party, "custom_invoice_crate_balance"))
        loose_rows = frappe.db.get_all(
            "Driver Crate Type Balance",
            filters={"parent": party},
            fields=["crate_type", "balance"],
            order_by="crate_type"
        )
        return {
            "type": "driver",
            "invoice_balance": invoice_balance,
            "loose_balances": loose_rows
        }

    return {}


class CrateBalanceAdjustment(Document):

    def validate(self):
        if not self.crates:
            frappe.throw("Crates cannot be zero.")
        if self.party_type == "Driver" and not self.driver_balance_type:
            frappe.throw("Balance Type is required for Driver.")
        if self.party_type == "Driver" and self.driver_balance_type == "Loose Crate" and not self.crate_type:
            frappe.throw("Crate Type is required for Loose Crate adjustment.")
        self._check_negative_balance()

    def _check_negative_balance(self):
        crates = flt(self.crates)
        if crates >= 0:
            return  # Adding crates — always fine

        allow_negative = frappe.db.get_single_value("Crate Settings", "allow_negative_crate")
        if allow_negative:
            return

        current = self._get_current_balance()
        if current + crates < 0:
            frappe.throw(
                f"This adjustment would reduce the balance to {current + crates:.0f}, "
                f"which is below zero. Current balance is {current:.0f}. "
                f"Enable <b>Allow Negative Crate Balance</b> in Crate Settings to proceed."
            )

    def _get_current_balance(self):
        if self.party_type == "Customer" and self.customer:
            return flt(frappe.db.get_value("Customer", self.customer, "custom_current_crate_balance"))
        elif self.party_type == "Driver" and self.driver:
            if self.driver_balance_type == "Loose Crate" and self.crate_type:
                return self._get_driver_loose_balance(self.driver, self.crate_type)
            else:
                return flt(frappe.db.get_value("Driver", self.driver, "custom_invoice_crate_balance"))
        return 0

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
        ledger.entry_type     = self.entry_type
        ledger.crate_category = self.entry_type
        ledger.crate_delivery = self.name

        if self.party_type == "Customer":
            ledger.ledger_type    = "Customer"
            ledger.customer       = self.customer
            ledger.crates_out     = crates if crates > 0 else 0
            ledger.crates_in      = abs(crates) if crates < 0 else 0
            ledger.balance_crates = flt(
                frappe.db.get_value("Customer", self.customer, "custom_current_crate_balance")
            ) + crates

        elif self.party_type == "Driver":
            ledger.ledger_type    = "Driver"
            ledger.driver         = self.driver
            ledger.crates_out     = crates if crates > 0 else 0
            ledger.crates_in      = abs(crates) if crates < 0 else 0

            if self.driver_balance_type == "Loose Crate":
                ledger.crate_category = f"{self.entry_type} — Loose"
                ledger.crate_type     = self.crate_type
                current = self._get_driver_loose_balance(self.driver, self.crate_type)
                ledger.balance_crates = current + crates
            else:
                current = flt(frappe.db.get_value("Driver", self.driver, "custom_invoice_crate_balance"))
                ledger.balance_crates = current + crates

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
            frappe.db.set_value("Customer", self.customer, "custom_current_crate_balance", current + delta)

        elif self.party_type == "Driver" and self.driver:
            if self.driver_balance_type == "Loose Crate" and self.crate_type:
                self._update_driver_loose_balance(self.driver, self.crate_type, delta)
            else:
                current = flt(frappe.db.get_value("Driver", self.driver, "custom_invoice_crate_balance"))
                frappe.db.set_value("Driver", self.driver, "custom_invoice_crate_balance", current + delta)

    # =========================================================
    # LOOSE CRATE HELPERS
    # =========================================================

    def _get_driver_loose_balance(self, driver, crate_type):
        result = frappe.db.get_value(
            "Driver Crate Type Balance",
            {"parent": driver, "crate_type": crate_type},
            "balance"
        )
        return flt(result)

    def _update_driver_loose_balance(self, driver, crate_type, delta):
        driver_doc = frappe.get_doc("Driver", driver)
        for row in driver_doc.custom_crate_type_balances:
            if row.crate_type == crate_type:
                row.balance = flt(row.balance) + delta
                driver_doc.save(ignore_permissions=True)
                return
        # Crate type not found — create new row
        driver_doc.append("custom_crate_type_balances", {
            "crate_type": crate_type,
            "balance": delta
        })
        driver_doc.save(ignore_permissions=True)
