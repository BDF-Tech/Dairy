import frappe
from frappe.model.document import Document
from frappe.utils import flt


class CrateDelivery(Document):

    # =========================================================
    # VALIDATE
    # =========================================================

    def validate(self):

        self._set_fields_from_vml()

        self._set_customer_from_invoice()

        self._refresh_customer_balance()

        self._validate_crates_delivered()

        self._validate_crates_returned()

    # =========================================================
    # ON SUBMIT
    # =========================================================

    def on_submit(self):

        self._create_delivery_ledger()

        self._create_return_ledger()

    # =========================================================
    # ON CANCEL
    # =========================================================

    def on_cancel(self):

        self._reverse_delivery_ledger()

        self._reverse_return_ledger()

        # Delete all ledger entries created by this Crate Delivery
        frappe.db.delete(
            "Customer Crate Ledger",
            {"crate_delivery": self.name}
        )

    # =========================================================
    # VALIDATE HELPERS
    # =========================================================

    def _set_fields_from_vml(self):
        """Auto-fill driver, vehicle, route from VML."""

        if not self.vehicle_movement_log:
            return

        vml = frappe.db.get_value(
            "Vehicle Movement Log",
            self.vehicle_movement_log,
            ["driver", "vehicle", "route"],
            as_dict=True
        )

        if not vml:
            return

        if not self.driver:
            self.driver = vml.driver

        if not self.vehicle:
            self.vehicle = vml.vehicle

        if not self.route:
            self.route = vml.route

    def _set_customer_from_invoice(self):
        """
        Auto-fill customer and invoice_crate_qty from Sales Invoice.
        Sets actual_customer = customer if not already set (redirect case).
        invoice_crate_qty = sum of all items with UOM = Crate on the invoice.
        """

        if not self.sales_invoice:
            return

        customer = frappe.db.get_value(
            "Sales Invoice",
            self.sales_invoice,
            "customer"
        )

        if not customer:
            return

        self.customer = customer

        if not self.actual_customer:
            self.actual_customer = customer

        result = frappe.db.sql(
            """
                SELECT COALESCE(SUM(qty), 0)
                FROM `tabSales Invoice Item`
                WHERE parent = %s
                  AND uom = 'Crate'
            """,
            self.sales_invoice
        )

        self.invoice_crate_qty = flt(
            result[0][0] if result else 0
        )

    def _validate_crates_delivered(self):
        """
        crates_delivered must be >= invoice_crate_qty.
        Driver cannot deliver fewer crates than what the invoice says.
        """

        if not self.crates_delivered:
            return

        if (
            self.invoice_crate_qty
            and self.crates_delivered < self.invoice_crate_qty
        ):

            frappe.throw(
                title="Crates Delivered Too Low",
                msg=(
                    f"<b>Crates Delivered</b> ({self.crates_delivered}) "
                    f"cannot be less than "
                    f"<b>Invoice Crate Qty</b> ({self.invoice_crate_qty}).<br><br>"
                    f"Deliver all invoice crates before submitting."
                )
            )

    def _validate_crates_returned(self):
        """
        crates_returned must be <= crates_delivered + customer's existing balance.
        Customer can return newly delivered crates AND any crates they already had.
        """

        if not self.crates_returned:
            return

        existing_balance = flt(self.customer_current_balance)
        max_returnable = flt(self.crates_delivered) + existing_balance

        if max_returnable and self.crates_returned > max_returnable:

            frappe.throw(
                title="Crates Returned Too High",
                msg=(
                    f"You are returning <b>{self.crates_returned}</b> crates "
                    f"but only <b>{max_returnable}</b> crates are assigned to this customer.<br><br>"
                    f"Delivered this trip: <b>{flt(self.crates_delivered)}</b><br>"
                    f"Customer existing balance: <b>{existing_balance}</b>"
                )
            )

    def _refresh_customer_balance(self):
        """Show live balance of actual_customer before this delivery."""

        if not self.actual_customer:
            return

        self.customer_current_balance = flt(
            frappe.db.get_value(
                "Customer",
                self.actual_customer,
                "custom_current_crate_balance"
            )
        )

    # =========================================================
    # SUBMIT — DELIVERY LEDGER (Driver → Customer)
    # =========================================================

    def _create_delivery_ledger(self):
        """
        Driver hands crates to customer.
          Customer Crate Ledger OUT  (ledger_type=Customer, entry_type=OUT)
          Customer.custom_current_crate_balance  UP by crates_delivered
          Driver.custom_invoice_crate_balance    DOWN by crates_delivered

        Flaw 4: idempotency guard — skip if OUT ledger already exists.
        Flaw 5: uses actual_customer, not customer — handles redirect case.
        """

        # Idempotency guard
        if frappe.db.exists(
            "Customer Crate Ledger",
            {
                "crate_delivery": self.name,
                "entry_type": "OUT",
                "ledger_type": "Customer"
            }
        ):
            return

        current_balance = flt(
            frappe.db.get_value(
                "Customer",
                self.actual_customer,
                "custom_current_crate_balance"
            )
        )

        new_customer_balance = current_balance + self.crates_delivered

        ledger = frappe.new_doc("Customer Crate Ledger")

        ledger.posting_date = self.date

        ledger.ledger_type = "Customer"

        ledger.driver = self.driver

        ledger.customer = self.actual_customer

        ledger.sales_invoice = self.sales_invoice

        ledger.vehicle_movement_log = self.vehicle_movement_log

        ledger.crate_delivery = self.name

        ledger.crates_out = self.crates_delivered

        ledger.crates_in = 0

        ledger.balance_crates = new_customer_balance

        ledger.entry_type = "OUT"

        ledger.insert(ignore_permissions=True)

        # Customer balance UP
        frappe.db.set_value(
            "Customer",
            self.actual_customer,
            "custom_current_crate_balance",
            new_customer_balance
        )

        # Driver invoice balance DOWN
        current_driver_balance = flt(
            frappe.db.get_value(
                "Driver",
                self.driver,
                "custom_invoice_crate_balance"
            )
        )

        frappe.db.set_value(
            "Driver",
            self.driver,
            "custom_invoice_crate_balance",
            max(0, current_driver_balance - self.crates_delivered)
        )

    # =========================================================
    # SUBMIT — RETURN LEDGER (Customer → Driver)
    # =========================================================

    def _create_return_ledger(self):
        """
        Customer hands empty crates back to driver on the spot.
          Customer Crate Ledger IN  (ledger_type=Customer, entry_type=IN)
          Customer.custom_current_crate_balance  DOWN by crates_returned
          Driver.custom_invoice_crate_balance    UP by crates_returned
              (driver holds these until vehicle returns to plant)

        Skipped entirely if crates_returned = 0.
        Flaw 4: idempotency guard on IN entry.
        """

        if not self.crates_returned:
            return

        # Idempotency guard
        if frappe.db.exists(
            "Customer Crate Ledger",
            {
                "crate_delivery": self.name,
                "entry_type": "IN",
                "ledger_type": "Customer"
            }
        ):
            return

        current_balance = flt(
            frappe.db.get_value(
                "Customer",
                self.actual_customer,
                "custom_current_crate_balance"
            )
        )

        new_customer_balance = current_balance - self.crates_returned

        ledger = frappe.new_doc("Customer Crate Ledger")

        ledger.posting_date = self.date

        ledger.ledger_type = "Customer"

        ledger.driver = self.driver

        ledger.customer = self.actual_customer

        ledger.sales_invoice = self.sales_invoice

        ledger.vehicle_movement_log = self.vehicle_movement_log

        ledger.crate_delivery = self.name

        ledger.crates_out = 0

        ledger.crates_in = self.crates_returned

        ledger.balance_crates = new_customer_balance

        ledger.entry_type = "IN"

        ledger.insert(ignore_permissions=True)

        # Customer balance DOWN
        frappe.db.set_value(
            "Customer",
            self.actual_customer,
            "custom_current_crate_balance",
            new_customer_balance
        )

        # Driver invoice balance UP (driver holds these crates until back at plant)
        current_driver_balance = flt(
            frappe.db.get_value(
                "Driver",
                self.driver,
                "custom_invoice_crate_balance"
            )
        )

        frappe.db.set_value(
            "Driver",
            self.driver,
            "custom_invoice_crate_balance",
            current_driver_balance + self.crates_returned
        )

    # =========================================================
    # CANCEL — REVERSE DELIVERY
    # =========================================================

    def _reverse_delivery_ledger(self):
        """
        Reverse the delivery:
          Customer.custom_current_crate_balance  DOWN by crates_delivered
          Driver.custom_invoice_crate_balance    UP by crates_delivered
        """

        current_balance = flt(
            frappe.db.get_value(
                "Customer",
                self.actual_customer,
                "custom_current_crate_balance"
            )
        )

        frappe.db.set_value(
            "Customer",
            self.actual_customer,
            "custom_current_crate_balance",
            current_balance - self.crates_delivered
        )

        current_driver_balance = flt(
            frappe.db.get_value(
                "Driver",
                self.driver,
                "custom_invoice_crate_balance"
            )
        )

        frappe.db.set_value(
            "Driver",
            self.driver,
            "custom_invoice_crate_balance",
            current_driver_balance + self.crates_delivered
        )

    # =========================================================
    # CANCEL — REVERSE RETURN
    # =========================================================

    def _reverse_return_ledger(self):
        """
        Reverse the customer return (if any):
          Customer.custom_current_crate_balance  UP by crates_returned
          Driver.custom_invoice_crate_balance    DOWN by crates_returned
        """

        if not self.crates_returned:
            return

        current_balance = flt(
            frappe.db.get_value(
                "Customer",
                self.actual_customer,
                "custom_current_crate_balance"
            )
        )

        frappe.db.set_value(
            "Customer",
            self.actual_customer,
            "custom_current_crate_balance",
            current_balance + self.crates_returned
        )

        current_driver_balance = flt(
            frappe.db.get_value(
                "Driver",
                self.driver,
                "custom_invoice_crate_balance"
            )
        )

        frappe.db.set_value(
            "Driver",
            self.driver,
            "custom_invoice_crate_balance",
            max(0, current_driver_balance - self.crates_returned)
        )


# =============================================================
# WHITELISTED HELPERS
# =============================================================

@frappe.whitelist()
def get_invoice_crate_qty(sales_invoice):
    """Return total crate qty (UOM = Crate) from a Sales Invoice."""

    result = frappe.db.sql(
        """
            SELECT COALESCE(SUM(qty), 0)
            FROM `tabSales Invoice Item`
            WHERE parent = %s
              AND uom = 'Crate'
        """,
        sales_invoice
    )

    return flt(result[0][0]) if result else 0
