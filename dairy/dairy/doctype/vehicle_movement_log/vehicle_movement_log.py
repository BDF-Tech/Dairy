import frappe
import json

from frappe.model.document import Document
from frappe.utils import getdate, nowdate, flt


class VehicleMovementLog(Document):

    # =========================================================
    # VALIDATION
    # =========================================================

    def validate(self):

        self.check_vehicle_not_on_active_trip()

        self.check_vehicle_documents()

        self.update_crate_summary_balance()

        self.populate_crate_summary_customer_names()

        self.update_loose_crate_balance()

        self.update_total_invoice_crates()

        self.sync_crate_item_details()

    # =========================================================
    # UPDATE CRATE SUMMARY BALANCE
    # =========================================================

    def update_crate_summary_balance(self):

        for row in self.crate_summary:

            total_out = row.total_crate_out or 0

            total_in = row.total_crate_in or 0

            row.balance_crate = (
                total_out - total_in
            )

            if total_in > 0:

                row.return_verified = 1

            else:

                row.return_verified = 0

    # =========================================================
    # POPULATE CUSTOMER NAMES IN CRATE SUMMARY
    # =========================================================

    def populate_crate_summary_customer_names(self):
        """Fill customer_name on each crate_summary row from the linked Sales Invoice."""
        for row in self.crate_summary:
            if row.sales_invoice and not row.customer_name:
                row.customer_name = frappe.db.get_value(
                    "Sales Invoice", row.sales_invoice, "customer_name"
                )

    # =========================================================
    # UPDATE LOOSE CRATE BALANCE
    # =========================================================

    def update_loose_crate_balance(self):

        for row in self.loose_crate_detail:

            total_out = row.crates_out or 0

            total_in = row.crates_in or 0

            row.balance = (
                total_out - total_in
            )

            if total_in > 0:

                row.return_verified = 1

            else:

                row.return_verified = 0

    # =========================================================
    # UPDATE TOTAL INVOICE CRATES
    # =========================================================

    def update_total_invoice_crates(self):

        self.total_invoice_crates = sum(
            row.total_crate_out or 0
            for row in self.crate_summary
        )

    # =========================================================
    # SYNC CRATE ITEM DETAILS
    # =========================================================

    def sync_crate_item_details(self):
        """
        Removes rows from crate_item_details whose sales_invoice or
        stock_entry no longer exists in crate_summary.
        Called on every save so deletions from the summary table
        are immediately reflected in the item detail table.
        """

        valid_invoices = {
            row.sales_invoice
            for row in self.crate_summary
            if row.sales_invoice
        }

        valid_stock_entries = {
            row.stock_entry
            for row in self.crate_summary
            if row.stock_entry
        }

        filtered = []

        for row in self.crate_item_details:

            keep = False

            if row.sales_invoice and row.sales_invoice in valid_invoices:
                keep = True

            if row.stock_entry and row.stock_entry in valid_stock_entries:
                keep = True

            if keep:
                filtered.append(row)

        self.crate_item_details = filtered

    # =========================================================
    # MAIN UPDATE LOGIC
    # =========================================================

    def on_update(self):

        if self.workflow_state == "Gate Check":

            self.link_sales_invoices()

            self.create_driver_crate_ledger_for_invoices()

            self.create_driver_crate_ledger_for_stock_entries()

            self.create_loose_crate_out_ledger()

        if self.workflow_state in ("Vehicle Returned", "Submitted"):

            self.process_customer_crate_return()

            self.settle_driver_crates_on_return()

            self.create_loose_crate_in_ledger()

        if self.workflow_state == "Cancelled":

            self._cleanup_crate_entries()

    # =========================================================
    # ON TRASH
    # =========================================================

    def on_trash(self):

        self._cleanup_crate_entries()

    # =========================================================
    # CLEANUP ON CANCEL / TRASH
    # =========================================================

    def _cleanup_crate_entries(self):
        """
        Called when workflow_state → Cancelled or document is deleted.

        1. Delinks all Sales Invoices linked to this VML.
        2. Reverses Driver custom_invoice_crate_balance.
        3. Reverses Customer custom_current_crate_balance.
        4. Deletes all Customer Crate Ledger entries for this VML.
        """

        # ----------------------------------------------------------
        # Step 1: Delink Sales Invoices and Stock Entries
        # ----------------------------------------------------------

        linked_invoices = frappe.db.get_all(
            "Sales Invoice",
            filters={"custom_vehicle_movement_log": self.name},
            pluck="name"
        )

        for inv in linked_invoices:
            frappe.db.set_value(
                "Sales Invoice",
                inv,
                "custom_vehicle_movement_log",
                None
            )

        linked_stock_entries = frappe.db.get_all(
            "Stock Entry",
            filters={"van_collection_item": self.name},
            pluck="name"
        )

        for se in linked_stock_entries:
            frappe.db.set_value(
                "Stock Entry",
                se,
                "van_collection_item",
                None
            )

        # ----------------------------------------------------------
        # Step 2: Collect all ledger entries for this VML
        # ----------------------------------------------------------

        entries = frappe.db.get_all(
            "Customer Crate Ledger",
            filters={"vehicle_movement_log": self.name},
            fields=[
                "name",
                "ledger_type",
                "entry_type",
                "crates_out",
                "crates_in",
                "driver",
                "customer"
            ]
        )

        if not entries and not linked_invoices and not linked_stock_entries:
            return

        # ----------------------------------------------------------
        # Step 3: Calculate reversals
        #
        # Original logic:
        #   Driver OUT  → driver balance += crates_out
        #   Driver IN   → driver balance -= crates_in
        #   Customer IN → customer balance -= crates_in
        #
        # Reverse (undo):
        #   Driver OUT  → driver balance -= crates_out  (change = -crates_out)
        #   Driver IN   → driver balance += crates_in   (change = +crates_in)
        #   Customer IN → customer balance += crates_in (change = +crates_in)
        # ----------------------------------------------------------

        # Initialised here so message block can reference them
        # even when entries list is empty (e.g. cancelled pre-Gate Check)
        driver_changes = {}
        customer_changes = {}

        for e in entries:

            if e.ledger_type == "Driver" and e.driver:

                change = (e.crates_in or 0) - (e.crates_out or 0)

                driver_changes[e.driver] = (
                    driver_changes.get(e.driver, 0) + change
                )

            elif e.ledger_type == "Customer" and e.customer:

                change = (e.crates_in or 0) - (e.crates_out or 0)

                customer_changes[e.customer] = (
                    customer_changes.get(e.customer, 0) + change
                )

        # ----------------------------------------------------------
        # Step 4: Delete all ledger entries for this VML
        # ----------------------------------------------------------

        frappe.db.delete(
            "Customer Crate Ledger",
            {"vehicle_movement_log": self.name}
        )

        # ----------------------------------------------------------
        # Step 5: Apply reversals to Driver
        # ----------------------------------------------------------

        for driver, change in driver_changes.items():

            current = flt(
                frappe.db.get_value(
                    "Driver",
                    driver,
                    "custom_invoice_crate_balance"
                )
            )

            frappe.db.set_value(
                "Driver",
                driver,
                "custom_invoice_crate_balance",
                max(0, current + change)
            )

        # ----------------------------------------------------------
        # Step 6: Apply reversals to Customer
        # ----------------------------------------------------------

        for customer, change in customer_changes.items():

            current = flt(
                frappe.db.get_value(
                    "Customer",
                    customer,
                    "custom_current_crate_balance"
                )
            )

            frappe.db.set_value(
                "Customer",
                customer,
                "custom_current_crate_balance",
                max(0, current + change)
            )

        # ----------------------------------------------------------
        # Final: Detailed cancellation message
        # ----------------------------------------------------------

        msg = "<b>VML Cancelled — Cleanup Complete</b>"

        if linked_invoices:
            msg += (
                f"<br><br><b>Invoices Delinked "
                f"({len(linked_invoices)}):</b>"
            )
            for inv in linked_invoices:
                msg += f"<br>&nbsp;&nbsp;&nbsp;• {inv}"

        if linked_stock_entries:
            msg += (
                f"<br><br><b>Stock Entries Delinked "
                f"({len(linked_stock_entries)}):</b>"
            )
            for se in linked_stock_entries:
                msg += f"<br>&nbsp;&nbsp;&nbsp;• {se}"

        if entries:
            driver_out = sum(
                1 for e in entries
                if e.ledger_type == "Driver" and e.entry_type == "OUT"
            )
            driver_in = sum(
                1 for e in entries
                if e.ledger_type == "Driver" and e.entry_type == "IN"
            )
            customer_in = sum(
                1 for e in entries
                if e.ledger_type == "Customer" and e.entry_type == "IN"
            )

            msg += (
                f"<br><br><b>Ledger Entries Deleted "
                f"({len(entries)}):</b>"
            )

            if driver_out:
                msg += f"<br>&nbsp;&nbsp;&nbsp;• Driver OUT: {driver_out}"

            if driver_in:
                msg += f"<br>&nbsp;&nbsp;&nbsp;• Driver IN: {driver_in}"

            if customer_in:
                msg += f"<br>&nbsp;&nbsp;&nbsp;• Customer IN: {customer_in}"

        if driver_changes or customer_changes:
            msg += "<br><br><b>Balances Reversed:</b>"
            for drv, chg in driver_changes.items():
                msg += f"<br>&nbsp;&nbsp;&nbsp;• Driver {drv}: {'+' if chg >= 0 else ''}{chg} crates"
            for cust, chg in customer_changes.items():
                msg += f"<br>&nbsp;&nbsp;&nbsp;• Customer {cust}: {'+' if chg >= 0 else ''}{chg} crates"

        frappe.msgprint(msg, title="VML Cancelled", indicator="orange")

    # =========================================================
    # LINK SALES INVOICES
    # =========================================================

    def link_sales_invoices(self):

        linked_invoices = []
        new_invoice_links = 0

        for row in self.crate_summary:

            if not row.sales_invoice:
                continue

            existing_trip = frappe.db.get_value(
                "Sales Invoice",
                row.sales_invoice,
                "custom_vehicle_movement_log"
            )

            if (
                existing_trip
                and existing_trip != self.name
            ):

                frappe.throw(
                    f"Sales Invoice "
                    f"{row.sales_invoice} "
                    f"is already linked with "
                    f"Vehicle Movement "
                    f"{existing_trip}"
                )

            if not existing_trip:

                frappe.db.set_value(
                    "Sales Invoice",
                    row.sales_invoice,
                    "custom_vehicle_movement_log",
                    self.name
                )

                new_invoice_links += 1

            linked_invoices.append(
                row.sales_invoice
            )

        new_se_links = 0

        for row in self.crate_summary:

            if not row.stock_entry:
                continue

            existing_trip = frappe.db.get_value(
                "Stock Entry",
                row.stock_entry,
                "van_collection_item"
            )

            if (
                existing_trip
                and existing_trip != self.name
            ):

                frappe.throw(
                    f"Stock Entry "
                    f"{row.stock_entry} "
                    f"is already linked with "
                    f"Vehicle Movement "
                    f"{existing_trip}"
                )

            if not existing_trip:

                frappe.db.set_value(
                    "Stock Entry",
                    row.stock_entry,
                    "van_collection_item",
                    self.name
                )

                new_se_links += 1

        # Only show message when new links were actually created
        if not new_invoice_links and not new_se_links:
            return

        # ----------------------------------------------------------
        # Comprehensive Gate Check message
        # ----------------------------------------------------------

        si_crates = {}
        se_crates = {}

        for row in self.crate_summary:
            if row.sales_invoice:
                si_crates[row.sales_invoice] = row.total_crate_out or 0
            if row.stock_entry:
                se_crates[row.stock_entry] = row.total_crate_out or 0

        item_totals = {}

        for row in self.crate_item_details:
            key = row.item_name or row.item_code or "Unknown"
            item_totals[key] = item_totals.get(key, 0) + (row.qty or 0)

        total_crates = (
            sum(si_crates.values()) + sum(se_crates.values())
        )

        msg = "<b>Gate Check — Dispatch Complete</b>"

        if si_crates:
            msg += (
                f"<br><br><b>Sales Invoices Linked "
                f"({len(si_crates)}):</b>"
            )
            for inv, crates in si_crates.items():
                msg += f"<br>&nbsp;&nbsp;&nbsp;• {inv} — <b>{crates}</b> crates"

        if se_crates:
            msg += (
                f"<br><br><b>Stock Entries Linked "
                f"({len(se_crates)}):</b>"
            )
            for se, crates in se_crates.items():
                msg += f"<br>&nbsp;&nbsp;&nbsp;• {se} — <b>{crates}</b> crates"

        msg += f"<br><br><b>Total Crates Out: {total_crates}</b>"

        if item_totals:
            msg += "<br><br><b>Item Breakdown:</b>"
            for item, qty in sorted(
                item_totals.items(), key=lambda x: -x[1]
            ):
                msg += f"<br>&nbsp;&nbsp;&nbsp;• {item}: <b>{qty}</b>"

        frappe.msgprint(msg, title="Gate Check Complete", indicator="green")

    # =========================================================
    # DRIVER CRATE LEDGER OUT ENTRY (INVOICE CRATES)
    # =========================================================

    def create_driver_crate_ledger_for_invoices(self):

        new_crates = 0

        for row in self.crate_summary:

            if not row.sales_invoice:
                continue

            if not row.total_crate_out:
                continue

            existing_ledger = frappe.db.exists(
                "Customer Crate Ledger",
                {
                    "sales_invoice": row.sales_invoice,
                    "entry_type": "OUT",
                    "ledger_type": "Driver",
                    "vehicle_movement_log": self.name
                }
            )

            if existing_ledger:
                continue

            customer = frappe.db.get_value(
                "Sales Invoice",
                row.sales_invoice,
                "customer"
            )

            ledger = frappe.new_doc(
                "Customer Crate Ledger"
            )

            ledger.posting_date = self.date_and_time

            ledger.ledger_type = "Driver"

            ledger.driver = self.driver

            ledger.vehicle = self.vehicle

            ledger.customer = customer

            ledger.sales_invoice = row.sales_invoice

            ledger.vehicle_movement_log = self.name

            ledger.crate_category = "Sales Invoice"

            ledger.crates_out = row.total_crate_out

            ledger.crates_in = 0

            ledger.balance_crates = row.total_crate_out

            ledger.entry_type = "OUT"

            ledger.insert(
                ignore_permissions=True
            )

            new_crates += row.total_crate_out

        if new_crates and self.driver:

            current = flt(
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
                current + new_crates
            )

    # =========================================================
    # CUSTOMER CRATE RETURN PROCESS (FALLBACK — no Crate Delivery)
    # =========================================================

    def process_customer_crate_return(self):
        """
        Fallback: runs at VML Submitted when no Crate Delivery was created.
        Handles crates that customers returned directly to the driver
        (tracked via total_crate_in on the VML crate_summary row).

        Fixes applied:
          Flaw 1 — Guard now includes vehicle_movement_log for proper idempotency.
          Flaw 3 — Skips invoices already handled by a submitted Crate Delivery.
          Flaw 6 — balance_crates uses actual running Customer balance, not trip row balance.
          Flaw 7 — frappe.get_doc replaced with frappe.db.get_value (one field, one SQL).
        """

        processed_invoices = []

        for row in self.crate_summary:

            if not row.sales_invoice:
                continue

            if not row.total_crate_in:
                continue

            # Flaw 3: Crate Delivery already handled this invoice — skip
            if frappe.db.exists(
                "Crate Delivery",
                {
                    "sales_invoice": row.sales_invoice,
                    "docstatus": 1
                }
            ):
                continue

            # Flaw 1: idempotency guard scoped to this VML
            existing_ledger = frappe.db.exists(
                "Customer Crate Ledger",
                {
                    "sales_invoice": row.sales_invoice,
                    "entry_type": "IN",
                    "ledger_type": "Customer",
                    "vehicle_movement_log": self.name
                }
            )

            if existing_ledger:
                continue

            # Flaw 7: single-field fetch, no full doc load
            customer = frappe.db.get_value(
                "Sales Invoice",
                row.sales_invoice,
                "customer"
            )

            # Flaw 6: running balance from DB, not trip-level row.balance_crate
            current_balance = flt(
                frappe.db.get_value(
                    "Customer",
                    customer,
                    "custom_current_crate_balance"
                )
            )

            new_balance = current_balance - row.total_crate_in

            ledger = frappe.new_doc(
                "Customer Crate Ledger"
            )

            ledger.posting_date = self.date_and_time

            ledger.ledger_type = "Customer"

            ledger.customer = customer

            ledger.sales_invoice = row.sales_invoice

            ledger.vehicle_movement_log = self.name

            ledger.crates_out = 0

            ledger.crates_in = row.total_crate_in

            ledger.balance_crates = new_balance

            ledger.entry_type = "IN"

            ledger.insert(
                ignore_permissions=True
            )

            frappe.db.set_value(
                "Customer",
                customer,
                "custom_current_crate_balance",
                new_balance
            )

            processed_invoices.append(
                row.sales_invoice
            )

        if processed_invoices:

            frappe.msgprint(
                "<b>Successfully processed returned crates:</b><br><br>"
                + "<br>".join(processed_invoices),

                title="Vehicle Return Processed",

                indicator="green"
            )

    # =========================================================
    # CLOSE DRIVER INVOICE CRATES ON VML RETURN (FLAW 2 FIX)
    # =========================================================

    def settle_driver_crates_on_return(self):
        """
        At Vehicle Returned: security physically counts all invoice + stock
        entry crates coming off the vehicle and enters one total in
        security_total_crates_in.

        Creates ONE Driver IN ledger entry for that amount.
        Any shortfall (expected > actual) stays on driver balance automatically.
        """

        if not self.driver:
            return

        total_in = flt(self.security_total_crates_in)

        if not total_in:
            return

        # Idempotency: settlement entry has no sales_invoice, stock_entry, or crate_item
        already_settled = frappe.db.get_value(
            "Customer Crate Ledger",
            {
                "vehicle_movement_log": self.name,
                "ledger_type": "Driver",
                "entry_type": "IN",
                "sales_invoice": ["is", "not set"],
                "crate_type": ["is", "not set"]
            },
            "name"
        )

        if already_settled:
            return

        current = flt(
            frappe.db.get_value(
                "Driver",
                self.driver,
                "custom_invoice_crate_balance"
            )
        )

        ledger = frappe.new_doc("Customer Crate Ledger")
        ledger.posting_date = self.date_and_time
        ledger.ledger_type = "Driver"
        ledger.driver = self.driver
        ledger.vehicle = self.vehicle
        ledger.vehicle_movement_log = self.name
        ledger.crates_out = 0
        ledger.crates_in = total_in
        ledger.balance_crates = max(0, current - total_in)
        ledger.entry_type = "IN"
        ledger.insert(ignore_permissions=True)

        frappe.db.set_value(
            "Driver",
            self.driver,
            "custom_invoice_crate_balance",
            max(0, current - total_in)
        )

    # =========================================================
    # DRIVER STOCK ENTRY CRATE LEDGER — OUT (Gate Check)
    # =========================================================

    def create_driver_crate_ledger_for_stock_entries(self):
        """
        At Gate Check: create a Driver OUT ledger entry for every
        crate_summary row that is linked to a Stock Entry (van-load
        crates that are NOT tied to a specific Sales Invoice).
        """

        new_crates = 0

        for row in self.crate_summary:

            if not row.stock_entry:
                continue

            if not row.total_crate_out:
                continue

            existing_ledger = frappe.db.exists(
                "Customer Crate Ledger",
                {
                    "stock_entry": row.stock_entry,
                    "entry_type": "OUT",
                    "ledger_type": "Driver",
                    "vehicle_movement_log": self.name
                }
            )

            if existing_ledger:
                continue

            ledger = frappe.new_doc("Customer Crate Ledger")

            ledger.posting_date = self.date_and_time

            ledger.ledger_type = "Driver"

            ledger.driver = self.driver

            ledger.stock_entry = row.stock_entry

            ledger.vehicle_movement_log = self.name

            ledger.crate_category = "Stock Entry"

            ledger.crates_out = row.total_crate_out

            ledger.crates_in = 0

            ledger.balance_crates = row.total_crate_out

            ledger.entry_type = "OUT"

            ledger.insert(ignore_permissions=True)

            new_crates += row.total_crate_out

        if new_crates and self.driver:

            current = flt(
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
                current + new_crates
            )


    # =========================================================
    # LOOSE CRATE OUT LEDGER
    # =========================================================

    def create_loose_crate_out_ledger(self):

        new_changes = {}

        for row in self.loose_crate_detail:

            if not row.crate_item:
                continue

            if not row.crates_out:
                continue

            existing_ledger = frappe.db.exists(
                "Customer Crate Ledger",
                {
                    "vehicle_movement_log": self.name,
                    "crate_type": row.crate_item,
                    "entry_type": "OUT",
                    "ledger_type": "Driver"
                }
            )

            if existing_ledger:
                continue

            ledger = frappe.new_doc(
                "Customer Crate Ledger"
            )

            ledger.posting_date = self.date_and_time

            ledger.ledger_type = "Driver"

            ledger.driver = self.driver

            ledger.vehicle = self.vehicle

            ledger.vehicle_movement_log = self.name

            ledger.crate_type = row.crate_item

            ledger.crate_category = "Loose Crate"

            ledger.crates_out = row.crates_out

            ledger.crates_in = 0

            ledger.balance_crates = row.balance

            ledger.entry_type = "OUT"

            ledger.insert(
                ignore_permissions=True
            )

            new_changes[row.crate_item] = (
                new_changes.get(row.crate_item, 0)
                + row.crates_out
            )

        self._update_driver_loose_crate_balances(new_changes)

    # =========================================================
    # LOOSE CRATE IN LEDGER
    # =========================================================

    def create_loose_crate_in_ledger(self):
        """
        At Vehicle Returned: security fills security_loose_crate_entries with
        each crate type and physical qty counted. Creates one Driver IN ledger
        entry per type. Shortfall vs what went out stays on driver balance.
        """

        new_changes = {}

        for row in self.security_loose_crate_entries:

            if not row.crate_type:
                continue

            if not row.crates_in:
                continue

            existing_ledger = frappe.db.exists(
                "Customer Crate Ledger",
                {
                    "vehicle_movement_log": self.name,
                    "crate_type": row.crate_type,
                    "entry_type": "IN",
                    "ledger_type": "Driver"
                }
            )

            if existing_ledger:
                continue

            # Find how many went out for this crate type (for balance_crates)
            crates_out = 0
            for lc in self.loose_crate_detail:
                if lc.crate_item == row.crate_type:
                    crates_out = flt(lc.crates_out)
                    break

            ledger = frappe.new_doc("Customer Crate Ledger")
            ledger.posting_date = self.date_and_time
            ledger.ledger_type = "Driver"
            ledger.driver = self.driver
            ledger.vehicle = self.vehicle
            ledger.vehicle_movement_log = self.name
            ledger.crate_type = row.crate_type
            ledger.crate_category = "Loose Crate"
            ledger.crates_out = 0
            ledger.crates_in = row.crates_in
            ledger.balance_crates = max(0, crates_out - flt(row.crates_in))
            ledger.entry_type = "IN"
            ledger.insert(ignore_permissions=True)

            new_changes[row.crate_type] = (
                new_changes.get(row.crate_type, 0)
                - row.crates_in
            )

        self._update_driver_loose_crate_balances(new_changes)

    # =========================================================
    # DRIVER LOOSE CRATE TYPE BALANCE UPDATE
    # =========================================================

    def _update_driver_loose_crate_balances(self, changes):
        if not self.driver or not changes:
            return

        driver_doc = frappe.get_doc("Driver", self.driver)

        # Guard: if custom_crate_type_balances field hasn't been added
        # to the Driver doctype via Customize Form yet, skip silently.
        if not driver_doc.meta.get_field("custom_crate_type_balances"):
            return

        existing_rows = driver_doc.get("custom_crate_type_balances") or []

        for crate_type, qty in changes.items():

            found = False

            for row in existing_rows:

                if row.crate_type == crate_type:
                    row.balance = (row.balance or 0) + qty
                    found = True
                    break

            if not found:

                driver_doc.append(
                    "custom_crate_type_balances",
                    {
                        "crate_type": crate_type,
                        "balance": qty
                    }
                )

        driver_doc.save(ignore_permissions=True)

    # =========================================================
    # STOCK ENTRY FOR LOOSE CRATES (Phase 2 — pending)
    # =========================================================

    def create_stock_entry_for_loose_items(self):
        pass

    # =========================================================
    # VEHICLE DOUBLE-BOOKING CHECK
    # =========================================================

    def check_vehicle_not_on_active_trip(self):

        if not self.vehicle:
            return

        filters = {
            "vehicle": self.vehicle,
            "status": "Out",
        }

        if self.name:
            filters["name"] = ["!=", self.name]

        active_trip = frappe.db.get_value(
            "Vehicle Movement Log",
            filters,
            "name"
        )

        if active_trip:

            frappe.throw(
                title="Vehicle Already On Trip",
                msg=(
                    f"<b>{self.vehicle}</b> is currently assigned "
                    f"to an active trip "
                    f"<b>{active_trip}</b> (Status: Out).<br><br>"
                    f"A vehicle cannot be on two trips simultaneously."
                )
            )

    # =========================================================
    # VEHICLE COMPLIANCE CHECK
    # =========================================================

    def check_vehicle_documents(self):

        if not self.vehicle:
            return

        vehicle = frappe.db.get_value(
            "Vehicle",
            self.vehicle,
            [
                "insurance_company", "policy_no",
                "custom_rc_no", "custom_pollution",
                "custom_pollution_validity", "custom_fitness",
                "custom_fitness_validity", "start_date", "end_date"
            ],
            as_dict=True
        )

        required_fields = {

            "insurance_company":
                "Insurance Company",

            "policy_no":
                "Policy No",

            "custom_rc_no":
                "RC Number",

            "custom_pollution":
                "Pollution Certificate No",

            "custom_pollution_validity":
                "Pollution Validity Date",

            "custom_fitness":
                "Fitness Certificate No",

            "custom_fitness_validity":
                "Fitness Validity Date",

            "start_date":
                "Insurance Start Date",

            "end_date":
                "Insurance End Date"
        }

        errors = []

        today = getdate(nowdate())

        for field, label in required_fields.items():

            if not vehicle.get(field):

                errors.append(
                    f"• <b>{label}</b> is missing."
                )

        if (
            vehicle.get("end_date")
            and getdate(vehicle.end_date) < today
        ):

            errors.append(
                f"• <b>Insurance</b> expired on "
                f"{vehicle.end_date}."
            )

        if (
            vehicle.get("custom_fitness_validity")
            and getdate(
                vehicle.custom_fitness_validity
            ) < today
        ):

            errors.append(
                f"• <b>Fitness Certificate</b> "
                f"expired on "
                f"{vehicle.custom_fitness_validity}."
            )

        if (
            vehicle.get("custom_pollution_validity")
            and getdate(
                vehicle.custom_pollution_validity
            ) < today
        ):

            errors.append(
                f"• <b>Pollution Certificate</b> "
                f"expired on "
                f"{vehicle.custom_pollution_validity}."
            )

        if errors:

            frappe.throw(
                title="Vehicle Compliance Alert",

                msg=
                f"Cannot save Trip. "
                f"<b>{self.vehicle}</b> "
                f"has missing or expired "
                f"documents:<br><br>"

                + "<br>".join(errors)

                + "<br><br>Please update "
                f"the Vehicle Master."
            )


# =============================================================
# FETCH INVOICE + STOCK ENTRY DETAILS
# =============================================================

def _as_list(value):

    if not value:
        return []

    if isinstance(value, str):
        return json.loads(value)

    return value


def _get_stock_entry_crate_details(
    stock_entries=None,
    posting_date=None,
    t_warehouse=None
):

    t_warehouse = (
        t_warehouse
        or frappe.db.get_single_value(
            "Crate Settings", "transit_warehouse"
        )
    )

    conditions = [
        "se.docstatus = 1",
        "sed.uom = %(uom)s",
        "sed.t_warehouse = %(t_warehouse)s"
    ]

    values = {
        "uom": "Crate",
        "t_warehouse": t_warehouse
    }

    if posting_date:

        conditions.append(
            "se.posting_date = %(posting_date)s"
        )

        values["posting_date"] = posting_date

    stock_entries = _as_list(stock_entries)

    if stock_entries:

        conditions.append(
            "se.name in %(stock_entries)s"
        )

        values["stock_entries"] = tuple(stock_entries)

    rows = frappe.db.sql(
        f"""
            select
                se.name,
                sed.item_code,
                sed.item_name,
                sed.qty,
                sed.uom
            from `tabStock Entry` se
            inner join `tabStock Entry Detail` sed
                on sed.parent = se.name
            where {" and ".join(conditions)}
            order by se.name, sed.idx
        """,
        values,
        as_dict=True
    )

    stock_entry_map = {}

    for row in rows:

        if row.name not in stock_entry_map:

            stock_entry_map[row.name] = {
                "name": row.name,
                "total_crates": 0,
                "items": []
            }

        stock_entry_map[row.name][
            "total_crates"
        ] += row.qty or 0

        stock_entry_map[row.name][
            "items"
        ].append({
            "item_code": row.item_code,
            "item_name": row.item_name,
            "qty": row.qty,
            "uom": row.uom,
            "crates": row.qty
        })

    return list(
        stock_entry_map.values()
    )


@frappe.whitelist()
def get_invoice_details(invoices, posting_date):

    invoices = _as_list(invoices)

    result = {

        "invoices": [],

        "stock_entries": []
    }

    # =========================================================
    # SALES INVOICE DATA
    # =========================================================

    for invoice in invoices:

        doc = frappe.get_doc(
            "Sales Invoice",
            invoice
        )

        total_crates = 0

        item_rows = []

        for item in doc.items:

            if item.uom == "Crate":

                total_crates += item.qty

                item_rows.append({

                    "item_code":
                        item.item_code,

                    "item_name":
                        item.item_name,

                    "qty":
                        item.qty,

                    "uom":
                        item.uom,

                    "crates":
                        item.qty
                })

        result["invoices"].append({

            "name":
                doc.name,

            "customer":
                doc.customer,

            "total_crates":
                total_crates,

            "items":
                item_rows
        })

    return result


@frappe.whitelist()
def get_stock_entry_details(
    stock_entries,
    posting_date=None,
    t_warehouse=None
):

    return _get_stock_entry_crate_details(
        stock_entries=stock_entries,
        posting_date=posting_date,
        t_warehouse=t_warehouse
    )


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_stock_entry_query(
    doctype,
    txt,
    searchfield,
    start,
    page_len,
    filters,
    as_dict=False,
    reference_doctype=None,
    ignore_user_permissions=False
):

    filters = filters or {}

    if isinstance(filters, str):

        filters = json.loads(filters)

    return frappe.db.sql(
        """
            select
                se.name,
                se.posting_date,
                se.stock_entry_type
            from `tabStock Entry` se
            where
                se.docstatus = 1
                and se.posting_date = %(posting_date)s
                and se.name like %(txt)s
                and exists (
                    select 1
                    from `tabStock Entry Detail` sed
                    where
                        sed.parent = se.name
                        and sed.uom = %(uom)s
                        and sed.t_warehouse = %(t_warehouse)s
                )
            order by se.posting_date desc, se.name desc
            limit %(start)s, %(page_len)s
        """,
        {
            "posting_date": filters.get("posting_date"),
            "t_warehouse": (
                filters.get("t_warehouse")
                or frappe.db.get_single_value(
                    "Crate Settings", "transit_warehouse"
                )
            ),
            "uom": "Crate",
            "txt": f"%{txt or ''}%",
            "start": start,
            "page_len": page_len
        },
        as_dict=as_dict
    )
