import frappe
from frappe.model.document import Document
from frappe.utils import flt


class PickupLog(Document):

    # =========================================================
    # VALIDATE
    # =========================================================

    def validate(self):

        self._update_crate_summary_balance()

        self._populate_customer_names()

        self._update_total_crates()

    # =========================================================
    # ON SUBMIT
    # =========================================================

    def on_submit(self):

        self._process_crate_ledger()

        self._link_invoices()

    # =========================================================
    # ON CANCEL
    # =========================================================

    def on_cancel(self):

        self._reverse_crate_ledger()

        self._delink_invoices()

    # =========================================================
    # VALIDATE HELPERS
    # =========================================================

    def _update_crate_summary_balance(self):

        for row in self.crate_summary:

            row.balance_crate = flt(row.total_crate_out) - flt(row.total_crate_in)

            row.return_verified = 1 if flt(row.total_crate_in) > 0 else 0

    def _populate_customer_names(self):

        for row in self.crate_summary:

            if row.sales_invoice and not row.customer_name:

                row.customer_name = frappe.db.get_value(
                    "Sales Invoice", row.sales_invoice, "customer_name"
                )

    def _update_total_crates(self):

        self.total_invoice_crates = sum(
            flt(row.total_crate_out) for row in self.crate_summary
        )

    # =========================================================
    # SUBMIT — CRATE LEDGER
    # =========================================================

    def _process_crate_ledger(self):
        """
        For each invoice row:
          OUT entry  — crates leaving with the customer (balance UP)
          IN  entry  — crates the customer returns on the spot (balance DOWN)
        Both update Customer.custom_current_crate_balance immediately.
        """

        for row in self.crate_summary:

            if not row.sales_invoice:
                continue

            customer = frappe.db.get_value(
                "Sales Invoice", row.sales_invoice, "customer"
            )

            if not customer:
                continue

            current_balance = flt(
                frappe.db.get_value(
                    "Customer", customer, "custom_current_crate_balance"
                )
            )

            # --- OUT ---
            if flt(row.total_crate_out) > 0:

                if not frappe.db.exists(
                    "Customer Crate Ledger",
                    {
                        "sales_invoice": row.sales_invoice,
                        "entry_type": "OUT",
                        "ledger_type": "Customer",
                        "pickup_log": self.name
                    }
                ):

                    new_balance = current_balance + flt(row.total_crate_out)

                    ledger = frappe.new_doc("Customer Crate Ledger")
                    ledger.posting_date    = self.date
                    ledger.ledger_type     = "Customer"
                    ledger.crate_category  = "Pickup"
                    ledger.customer        = customer
                    ledger.sales_invoice   = row.sales_invoice
                    ledger.pickup_log      = self.name
                    ledger.crates_out      = flt(row.total_crate_out)
                    ledger.crates_in       = 0
                    ledger.balance_crates  = new_balance
                    ledger.entry_type      = "OUT"
                    ledger.insert(ignore_permissions=True)

                    frappe.db.set_value(
                        "Customer", customer,
                        "custom_current_crate_balance", new_balance
                    )

                    current_balance = new_balance

            # --- IN (return at counter) ---
            if flt(row.total_crate_in) > 0:

                if not frappe.db.exists(
                    "Customer Crate Ledger",
                    {
                        "sales_invoice": row.sales_invoice,
                        "entry_type": "IN",
                        "ledger_type": "Customer",
                        "pickup_log": self.name
                    }
                ):

                    new_balance = current_balance - flt(row.total_crate_in)

                    ledger = frappe.new_doc("Customer Crate Ledger")
                    ledger.posting_date    = self.date
                    ledger.ledger_type     = "Customer"
                    ledger.crate_category  = "Pickup"
                    ledger.customer        = customer
                    ledger.sales_invoice   = row.sales_invoice
                    ledger.pickup_log      = self.name
                    ledger.crates_out      = 0
                    ledger.crates_in       = flt(row.total_crate_in)
                    ledger.balance_crates  = new_balance
                    ledger.entry_type      = "IN"
                    ledger.insert(ignore_permissions=True)

                    frappe.db.set_value(
                        "Customer", customer,
                        "custom_current_crate_balance", new_balance
                    )

    def _link_invoices(self):

        for row in self.crate_summary:

            if row.sales_invoice:

                frappe.db.set_value(
                    "Sales Invoice", row.sales_invoice,
                    "custom_pickup_log", self.name
                )

    # =========================================================
    # CANCEL — REVERSE LEDGER
    # =========================================================

    def _reverse_crate_ledger(self):
        """
        Undo all balance changes by reversing each ledger entry,
        then delete all entries created by this Pickup Log.
        """

        entries = frappe.db.get_all(
            "Customer Crate Ledger",
            filters={"pickup_log": self.name},
            fields=["name", "customer", "entry_type", "crates_out", "crates_in"]
        )

        customer_changes = {}

        for e in entries:

            if not e.customer:
                continue

            # OUT originally added → reverse subtracts
            # IN  originally subtracted → reverse adds
            change = flt(e.crates_in) - flt(e.crates_out)

            customer_changes[e.customer] = (
                customer_changes.get(e.customer, 0) + change
            )

        frappe.db.delete("Customer Crate Ledger", {"pickup_log": self.name})

        for customer, change in customer_changes.items():

            current = flt(
                frappe.db.get_value(
                    "Customer", customer, "custom_current_crate_balance"
                )
            )

            frappe.db.set_value(
                "Customer", customer,
                "custom_current_crate_balance", current + change
            )

    def _delink_invoices(self):

        for row in self.crate_summary:

            if row.sales_invoice:

                frappe.db.set_value(
                    "Sales Invoice", row.sales_invoice,
                    "custom_pickup_log", None
                )
