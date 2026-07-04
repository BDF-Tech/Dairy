import frappe
import random
from frappe.model.document import Document
from frappe.utils import flt, now_datetime, add_to_date


class CrateDelivery(Document):

    # =========================================================
    # VALIDATE
    # =========================================================

    def validate(self):

        self._set_fields_from_vml()

        self._set_customer_from_invoice()

        self._set_crates_from_stock_entry()

        self._refresh_customer_balance()

        self._validate_crates_delivered()

        self._validate_crates_returned()

        self._set_location_source()

    def _set_location_source(self):
        """Default location source to ERP Manual when not captured from mobile GPS."""
        if not self.location_source:
            self.location_source = "ERP Manual"

    # =========================================================
    # ON SUBMIT
    # =========================================================

    def on_submit(self):
        # For invoice deliveries, ledger is created only after OTP verification.
        # Stock entries have no OTP so create ledger immediately.
        if self.sales_invoice and not self.customer_confirmed:
            return

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

        self.invoice_crate_qty = flt(get_invoice_crate_qty(self.sales_invoice))

    def _set_crates_from_stock_entry(self):
        """
        For stock-entry deliveries, set invoice_crate_qty = whole crates received
        into transit on the Stock Entry (same count the VML uses).
        """

        if not self.stock_entry:
            return

        self.invoice_crate_qty = flt(get_stock_entry_crate_qty(self.stock_entry))

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

        row = frappe.db.get_value(
            "Customer",
            self.actual_customer,
            "custom_current_crate_balance"
        )

        self.customer_current_balance = flt(row)

        if not self.customer_phone:
            phone = _get_customer_phone(self.actual_customer)
            if phone:
                self.customer_phone = phone

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

        # Idempotency guard — any OUT row already created for this delivery
        if frappe.db.exists(
            "Customer Crate Ledger",
            {
                "crate_delivery": self.name,
                "entry_type": "OUT"
            }
        ):
            return

        # Customer ledger + balance — ONLY for customer (invoice) deliveries.
        # Stock-entry deliveries have no customer; those crates are tracked via
        # the Driver + Warehouse movements below, not a Customer ledger row.
        if self.actual_customer:

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

            ledger.stock_entry = self.stock_entry

            ledger.crate_category = "Stock Entry" if self.stock_entry else "Sales Invoice"

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

        # Warehouse balance DOWN by crates delivered
        self._warehouse_movement(out_qty=self.crates_delivered, entry_type="OUT")

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

        # Idempotency guard — any IN row already created for this delivery
        if frappe.db.exists(
            "Customer Crate Ledger",
            {
                "crate_delivery": self.name,
                "entry_type": "IN"
            }
        ):
            return

        # Customer ledger + balance — ONLY for customer (invoice) deliveries.
        if self.actual_customer:

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

            ledger.stock_entry = self.stock_entry

            ledger.crate_category = "Stock Entry" if self.stock_entry else "Sales Invoice"

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

        # Warehouse balance UP by crates returned
        self._warehouse_movement(in_qty=self.crates_returned, entry_type="IN")

    # =========================================================
    # CANCEL — REVERSE DELIVERY
    # =========================================================

    def _reverse_delivery_ledger(self):
        """
        Reverse the delivery:
          Customer.custom_current_crate_balance  DOWN by crates_delivered
          Driver.custom_invoice_crate_balance    UP by crates_delivered
        """

        if self.actual_customer:
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

        # Warehouse balance back UP by crates delivered
        self._reverse_warehouse_movement(out_qty=self.crates_delivered)

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

        if self.actual_customer:
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

        # Warehouse balance back DOWN by crates returned
        self._reverse_warehouse_movement(in_qty=self.crates_returned)

    # =========================================================
    # WAREHOUSE CRATE BALANCE
    # =========================================================

    def _get_stock_entry_transit_warehouse(self):
        """Transit (target) warehouse of the delivery's Stock Entry, or None."""
        if not self.stock_entry:
            return None
        transit = frappe.db.get_value("Stock Entry", self.stock_entry, "to_warehouse")
        if not transit:
            transit = frappe.db.get_value(
                "Stock Entry Detail",
                {"parent": self.stock_entry, "t_warehouse": ["is", "set"]},
                "t_warehouse"
            )
        return transit

    def _get_mapped_warehouse(self):
        """
        Warehouse crate movement applies ONLY to stock-entry deliveries, and
        ONLY when the stock entry's transit (target) warehouse is explicitly
        mapped in Crate Settings → Transit → Warehouse Mapping.

          - Invoice deliveries        → None (no warehouse movement).
          - Stock entry, no mapping   → None (no warehouse movement).
          - Stock entry, mapped       → the LINKED warehouse.
        """
        transit = self._get_stock_entry_transit_warehouse()
        if not transit:
            return None

        # Only act if this transit warehouse is explicitly mapped. No fallback.
        return frappe.db.get_value(
            "Crate Transit Warehouse Map",
            {"parenttype": "Crate Settings", "transit_warehouse": transit},
            "warehouse"
        )

    def _warehouse_movement(self, out_qty=0, in_qty=0, entry_type="OUT"):
        """
        Apply a crate movement to the mapped warehouse and log it.
          OUT (delivery) → warehouse balance DOWN
          IN  (return)   → warehouse balance UP
        Writes a Warehouse-type Customer Crate Ledger row for traceability.
        Skipped silently if no warehouse can be resolved or qty is zero.
        """
        if not (flt(out_qty) or flt(in_qty)):
            return

        warehouse = self._get_mapped_warehouse()
        if not warehouse:
            # Stock-entry delivery whose transit warehouse has no mapping →
            # block the submit so it can't post crates against an unknown warehouse.
            transit = self._get_stock_entry_transit_warehouse()
            if transit:
                frappe.throw(
                    f"No mapped warehouse found in Crate Settings for transit "
                    f"warehouse <b>{transit}</b>. Add a Transit → Warehouse mapping "
                    f"in Crate Settings before submitting this delivery.",
                    title="Mapped Warehouse Not Found",
                )
            return

        # Stock-entry delivery = crates ARRIVE at the mapped depot warehouse:
        #   delivery → warehouse UP by out_qty ; return → warehouse DOWN by in_qty
        delta = flt(out_qty) - flt(in_qty)
        current = flt(frappe.db.get_value("Warehouse", warehouse, "custom_crate_balance"))
        new_balance = current + delta

        ledger = frappe.new_doc("Customer Crate Ledger")
        ledger.posting_date         = self.date
        ledger.ledger_type          = "Warehouse"
        ledger.warehouse            = warehouse
        ledger.driver               = self.driver
        ledger.customer             = self.actual_customer
        ledger.sales_invoice        = self.sales_invoice
        ledger.stock_entry          = self.stock_entry
        ledger.vehicle_movement_log = self.vehicle_movement_log
        ledger.crate_delivery       = self.name
        ledger.crate_category       = "Stock Entry" if self.stock_entry else "Sales Invoice"
        ledger.crates_out           = flt(out_qty)
        ledger.crates_in            = flt(in_qty)
        ledger.balance_crates       = new_balance
        ledger.entry_type           = entry_type
        ledger.insert(ignore_permissions=True)

        frappe.db.set_value("Warehouse", warehouse, "custom_crate_balance", new_balance)

    def _reverse_warehouse_movement(self, out_qty=0, in_qty=0):
        """Reverse the balance effect on the mapped warehouse (on cancel).
        Ledger rows are deleted separately in on_cancel (by crate_delivery)."""
        if not (flt(out_qty) or flt(in_qty)):
            return

        warehouse = self._get_mapped_warehouse()
        if not warehouse:
            return

        delta = flt(out_qty) - flt(in_qty)   # was ADDED on create → subtract back
        current = flt(frappe.db.get_value("Warehouse", warehouse, "custom_crate_balance"))
        frappe.db.set_value("Warehouse", warehouse, "custom_crate_balance", current - delta)


# =============================================================
# WHITELISTED HELPERS
# =============================================================

@frappe.whitelist()
def get_available_invoices_for_cd(doctype, txt, searchfield, start, page_len, filters):
    """Return Sales Invoices linked to a VML that have no draft/submitted Crate Delivery."""
    vml = (filters or {}).get("vml", "")
    return frappe.db.sql(
        """
        SELECT si.name, si.customer_name
        FROM `tabSales Invoice` si
        WHERE si.custom_vehicle_movement_log = %(vml)s
          AND si.docstatus = 1
          AND NOT EXISTS (
              SELECT 1 FROM `tabCrate Delivery` cd
              WHERE cd.sales_invoice = si.name
                AND cd.docstatus IN (0, 1)
          )
          AND (si.name LIKE %(txt)s OR si.customer_name LIKE %(txt)s)
        ORDER BY si.name
        LIMIT %(start)s, %(page_len)s
        """,
        {"vml": vml, "txt": f"%{txt}%", "start": int(start), "page_len": int(page_len)},
        as_list=True,
    )


@frappe.whitelist()
def get_available_stock_entries_for_cd(doctype, txt, searchfield, start, page_len, filters):
    """Return Stock Entries linked to a VML that have no draft/submitted Crate Delivery."""
    vml = (filters or {}).get("vml", "")
    return frappe.db.sql(
        """
        SELECT se.name, se.stock_entry_type
        FROM `tabStock Entry` se
        WHERE se.van_collection_item = %(vml)s
          AND se.docstatus = 1
          AND NOT EXISTS (
              SELECT 1 FROM `tabCrate Delivery` cd
              WHERE cd.stock_entry = se.name
                AND cd.docstatus IN (0, 1)
          )
          AND se.name LIKE %(txt)s
        ORDER BY se.name
        LIMIT %(start)s, %(page_len)s
        """,
        {"vml": vml, "txt": f"%{txt}%", "start": int(start), "page_len": int(page_len)},
        as_list=True,
    )


@frappe.whitelist()
def get_invoice_crate_qty(sales_invoice):
    """Whole crates on a Sales Invoice for Crate-items (floor of nos / crate factor)."""

    from dairy.dairy.doctype.vehicle_movement_log.vehicle_movement_log import (
        whole_crates_for_item,
    )

    crate_uom = (
        frappe.db.get_single_value("Crate Settings", "crate_uom")
        or "Crate"
    )

    rows = frappe.db.sql(
        """
            SELECT item_code, SUM(qty * conversion_factor) AS nos
            FROM `tabSales Invoice Item`
            WHERE parent = %s
            GROUP BY item_code
        """,
        (sales_invoice,),
        as_dict=True
    )

    return sum(whole_crates_for_item(r.item_code, r.nos, crate_uom) for r in rows)


@frappe.whitelist()
def get_stock_entry_crate_qty(stock_entry):
    """Whole crates on a Stock Entry for Crate-items received into a transit
    warehouse (floor of nos / crate factor)."""

    from dairy.dairy.doctype.vehicle_movement_log.vehicle_movement_log import (
        whole_crates_for_item,
    )

    crate_uom = (
        frappe.db.get_single_value("Crate Settings", "crate_uom")
        or "Crate"
    )

    rows = frappe.db.sql(
        """
            SELECT item_code, SUM(qty * conversion_factor) AS nos
            FROM `tabStock Entry Detail`
            WHERE parent = %s
              AND IFNULL(t_warehouse, '') != ''
            GROUP BY item_code
        """,
        (stock_entry,),
        as_dict=True
    )

    return sum(whole_crates_for_item(r.item_code, r.nos, crate_uom) for r in rows)


# =============================================================
# OTP — SEND
# =============================================================

@frappe.whitelist()
def send_delivery_otp(crate_delivery_name):
    """
    Generate a 4-digit OTP, save it on the Crate Delivery, then try to
    send it via WhatsApp (frappe_whatsapp).  Falls back to Frappe SMS
    Settings if WhatsApp is not configured or throws.

    Returns a dict: {"sent_to": "<number>", "channel": "WhatsApp|SMS"}
    Raises frappe.ValidationError if no phone number is available.
    """

    doc = frappe.get_doc("Crate Delivery", crate_delivery_name)

    # Fix 4 — guard: already confirmed, nothing to do
    if doc.customer_confirmed:
        frappe.throw("Delivery already confirmed by customer. No OTP needed.")

    phone = doc.otp_phone_override or doc.customer_phone
    if not phone:
        phone = _get_customer_phone(doc.actual_customer)

    if not phone:
        frappe.throw("No mobile number linked to this customer. Please add a phone number in the customer's Contact.")

    otp_length = int(
        frappe.db.get_single_value("Crate Settings", "otp_length") or 4
    )
    otp_expiry_minutes = int(
        frappe.db.get_single_value("Crate Settings", "otp_expiry_minutes") or 10
    )

    customer_name = (
        frappe.db.get_value("Customer", doc.actual_customer, "customer_name")
        or doc.actual_customer
    )

    otp = str(random.randint(10 ** (otp_length - 1), 10 ** otp_length - 1))
    expiry = add_to_date(now_datetime(), minutes=otp_expiry_minutes)

    # Fix 1 — save OTP to DB BEFORE sending via Kit19
    # If Kit19 succeeds but DB write had failed, customer would have OTP with no match in DB.
    # Saving first ensures the OTP is always in DB before the customer receives it.
    frappe.db.set_value("Crate Delivery", crate_delivery_name, {
        "otp": otp,
        "otp_expiry": expiry,
        "otp_sent_to": phone,
        "customer_phone": phone,
    })
    frappe.db.commit()

    channel = "WhatsApp"
    test_otp = None
    try:
        trans_msg = _send_kit19_transactional(
            phone, customer_name,
            int(flt(doc.crates_delivered)),
            doc.sales_invoice or "",
            int(flt(doc.crates_returned))
        )
        otp_msg = _send_kit19_otp(phone, otp)
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            f"Kit19 OTP Send Failed | Crate Delivery: {crate_delivery_name}"
        )
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Comment",
            "reference_doctype": "Crate Delivery",
            "reference_name": crate_delivery_name,
            "content": (
                f"<b>WhatsApp send failed</b> at {now_datetime().strftime('%d-%m-%Y %H:%M')} &mdash; "
                f"{str(e)[:300]}<br>"
                f"OTP is available manually. Check <b>Error Log</b> for full traceback."
            ),
        }).insert(ignore_permissions=True)
        channel = "manual"
        test_otp = otp
    else:
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Comment",
            "reference_doctype": "Crate Delivery",
            "reference_name": crate_delivery_name,
            "content": (
                f"<b>WhatsApp sent successfully</b> at {now_datetime().strftime('%d-%m-%Y %H:%M')} &mdash; "
                f"Delivery summary and OTP sent to {phone}.<br>"
                f"Transactional: {trans_msg}<br>"
                f"OTP: {otp_msg}"
            ),
        }).insert(ignore_permissions=True)

    result = {"sent_to": phone, "channel": channel}
    if test_otp:
        result["test_otp"] = test_otp
    return result


# =============================================================
# OTP — VERIFY
# =============================================================

@frappe.whitelist()
def verify_delivery_otp(crate_delivery_name, otp):
    """
    Verify the OTP entered by the driver.
    Sets customer_confirmed = 1 and clears OTP fields on success.
    Raises frappe.ValidationError on failure.
    """

    doc = frappe.get_doc("Crate Delivery", crate_delivery_name)

    if not doc.otp:
        frappe.throw("No OTP found. Please send an OTP first.")

    if now_datetime() > doc.otp_expiry:
        frappe.db.set_value("Crate Delivery", crate_delivery_name, {
            "otp": "",
            "otp_expiry": None,
        })
        frappe.db.commit()
        frappe.throw("OTP has expired. Please send a new OTP.")

    if str(otp).strip() != str(doc.otp).strip():
        frappe.throw("Incorrect OTP. Please try again.")

    cd = frappe.get_doc("Crate Delivery", crate_delivery_name)

    if cd.docstatus == 0:
        # Mobile flow: mark confirmed + submit in ONE transaction. on_submit
        # creates the ledger; if it fails, everything (incl. confirmation)
        # rolls back so the OTP can be retried.
        cd.customer_confirmed = 1
        cd.otp = ""
        cd.otp_expiry = None
        cd.submit()
    else:
        # ERP flow: already submitted. Create the ledger FIRST — only mark
        # confirmed once it succeeds, so a failure leaves it retryable.
        cd._create_delivery_ledger()
        cd._create_return_ledger()
        frappe.db.set_value("Crate Delivery", crate_delivery_name, {
            "customer_confirmed": 1,
            "otp": "",
            "otp_expiry": None,
        })

    return {"confirmed": 1}


@frappe.whitelist()
def regenerate_delivery_ledger(crate_delivery_name):
    """
    Recovery for deliveries that were confirmed but whose ledger failed to
    create (e.g. an earlier error after customer_confirmed was already set).
    Idempotent — the ledger methods skip if rows already exist.
    """
    cd = frappe.get_doc("Crate Delivery", crate_delivery_name)

    if cd.docstatus != 1:
        frappe.throw("Delivery must be submitted to (re)generate its ledger.")
    if not cd.customer_confirmed:
        frappe.throw("Delivery is not confirmed yet.")

    cd._create_delivery_ledger()
    cd._create_return_ledger()

    return {"created": 1}


@frappe.whitelist()
def bypass_delivery_otp(crate_delivery_name, reason=None):
    """
    Confirm a delivery WITHOUT OTP (e.g. customer unreachable).
    Gated by Crate Settings → Allow OTP Bypass. A reason is required and recorded.
    Triggers the same ledger flow as verify_delivery_otp.
    """

    if not frappe.db.get_single_value("Crate Settings", "allow_otp_bypass"):
        frappe.throw("OTP bypass is not enabled. Enable it in Crate Settings.")

    reason = (reason or "").strip()
    if not reason:
        frappe.throw("A reason is required to bypass OTP.")

    cd = frappe.get_doc("Crate Delivery", crate_delivery_name)

    if cd.docstatus == 0:
        # Mark confirmed + submit in one transaction (rolls back on failure)
        cd.customer_confirmed = 1
        cd.otp_bypassed = 1
        cd.otp_bypass_reason = reason
        cd.otp = ""
        cd.otp_expiry = None
        cd.submit()
    else:
        # Already submitted: create ledger first, confirm only on success
        cd._create_delivery_ledger()
        cd._create_return_ledger()
        frappe.db.set_value("Crate Delivery", crate_delivery_name, {
            "customer_confirmed": 1,
            "otp_bypassed": 1,
            "otp_bypass_reason": reason,
            "otp": "",
            "otp_expiry": None,
        })

    return {"confirmed": 1, "bypassed": 1}


# =============================================================
# OTP — SEND VIA SMS
# =============================================================

@frappe.whitelist()
def send_delivery_sms(crate_delivery_name):
    doc = frappe.get_doc("Crate Delivery", crate_delivery_name)

    if doc.customer_confirmed:
        frappe.throw("Delivery already confirmed by customer. No OTP needed.")

    phone = doc.otp_phone_override or doc.customer_phone
    if not phone:
        phone = _get_customer_phone(doc.actual_customer)
    if not phone:
        frappe.throw("No mobile number linked to this customer. Please add a phone number in the customer's Contact.")

    otp_length = int(frappe.db.get_single_value("Crate Settings", "otp_length") or 4)
    otp_expiry_minutes = int(frappe.db.get_single_value("Crate Settings", "otp_expiry_minutes") or 10)

    customer_name = (
        frappe.db.get_value("Customer", doc.actual_customer, "customer_name")
        or doc.actual_customer
    )

    current_balance = flt(
        frappe.db.get_value("Customer", doc.actual_customer, "custom_current_crate_balance") or 0
    )

    otp = str(random.randint(10 ** (otp_length - 1), 10 ** otp_length - 1))
    expiry = add_to_date(now_datetime(), minutes=otp_expiry_minutes)

    frappe.db.set_value("Crate Delivery", crate_delivery_name, {
        "otp": otp,
        "otp_expiry": expiry,
        "otp_sent_to": phone,
        "customer_phone": phone,
    })
    frappe.db.commit()

    channel = "SMS"
    test_otp = None
    try:
        sms_response = _send_sms_otp(
            phone, customer_name,
            int(flt(doc.crates_delivered)),
            doc.sales_invoice or "",
            doc.vehicle_movement_log or "",
            int(flt(doc.crates_returned)),
            int(current_balance),
            otp
        )
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Comment",
            "reference_doctype": "Crate Delivery",
            "reference_name": crate_delivery_name,
            "content": (
                f"<b>SMS sent successfully</b> at {now_datetime().strftime('%d-%m-%Y %H:%M')} &mdash; "
                f"OTP sent to {phone}.<br>{sms_response}"
            ),
        }).insert(ignore_permissions=True)
    except Exception as e:
        frappe.log_error(
            frappe.get_traceback(),
            f"SMS OTP Send Failed | Crate Delivery: {crate_delivery_name}"
        )
        frappe.get_doc({
            "doctype": "Comment",
            "comment_type": "Comment",
            "reference_doctype": "Crate Delivery",
            "reference_name": crate_delivery_name,
            "content": (
                f"<b>SMS send failed</b> at {now_datetime().strftime('%d-%m-%Y %H:%M')} &mdash; "
                f"{str(e)[:300]}<br>"
                f"OTP is available manually. Check <b>Error Log</b> for full traceback."
            ),
        }).insert(ignore_permissions=True)
        channel = "manual"
        test_otp = otp

    result = {"sent_to": phone, "channel": channel}
    if test_otp:
        result["test_otp"] = test_otp
    return result


# =============================================================
# INTERNAL HELPERS
# =============================================================

def _get_customer_phone(customer):
    """
    Fetch mobile number from Customer → customer_primary_contact → Contact.phone_nos.
    Prefers is_primary_mobile_no = 1; falls back to first phone in the list.
    Returns None if nothing is found.
    """
    contact_name = frappe.db.get_value("Customer", customer, "customer_primary_contact")
    if not contact_name:
        return None

    phones = frappe.get_all(
        "Contact Phone",
        filters={"parent": contact_name},
        fields=["phone", "is_primary_mobile_no"],
        order_by="is_primary_mobile_no desc"
    )

    if not phones:
        return None

    # Return the primary mobile if marked, else the first entry
    for row in phones:
        if row.is_primary_mobile_no:
            return row.phone

    return phones[0].phone


def _normalize_phone_kit19(phone):
    """Format phone number to 91XXXXXXXXXX (12-digit) as required by Kit19."""
    mobile = (phone or "").strip().replace(" ", "").replace("-", "")
    if mobile.startswith("+"):
        mobile = mobile[1:]
    if not mobile.startswith("91"):
        mobile = "91" + mobile
    return mobile


def _kit19_credentials():
    """Read Kit19 credentials from Crate Settings. Throws if not configured."""
    from frappe.utils.password import get_decrypted_password

    api_key = get_decrypted_password("Crate Settings", "Crate Settings", "kit19_api_key", raise_exception=False)
    username = frappe.db.get_single_value("Crate Settings", "kit19_username")

    if not api_key or not username:
        frappe.throw("Kit19 WhatsApp credentials not configured. Fill API Key and Username in Crate Settings.")

    return api_key, username


def _send_kit19_transactional(phone, customer_name, crates_delivered, invoice, crates_returned):
    """
    Send delivery info via Kit19 WhatsApp utility template.
    Parameters: customer_name, crates_delivered, invoice, crates_returned.
    """
    import requests

    api_key, username = _kit19_credentials()
    mobile = _normalize_phone_kit19(phone)

    template_name = "crate_return_confirmationnew_copy"
    namespace     = "ab750a7e_4257_4e46_8b29_2bb25087d1c4"

    payload = {
        "key": api_key,
        "username": username,
        "name": "whatsapp",
        "remarks": (
            f"Hey {customer_name}, Total {crates_delivered} crates given to you "
            f"against invoice {invoice}. {crates_returned} crates returned by you."
        ),
        "whatsapp": {
            "to": mobile,
            "type": "template",
            "category": "UTILITY",
            "recipient_type": "individual",
            "template": {
                "namespace": namespace,
                "language": {"policy": "deterministic", "code": "en"},
                "name": template_name,
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            {"type": "text", "text": str(customer_name)},
                            {"type": "text", "text": str(crates_delivered)},
                            {"type": "text", "text": str(invoice)},
                            {"type": "text", "text": str(crates_returned)},
                        ]
                    }
                ]
            }
        }
    }

    response = requests.post(
        "https://services.kit19.com/IMS/Whatsapp/Template",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=10
    )

    if not response.ok:
        frappe.throw(f"Kit19 transactional error ({response.status_code}): {response.text}")

    return response.json().get("meta", {}).get("developer_message", "")


def _send_kit19_otp(phone, otp):
    """
    Send OTP via Kit19 WhatsApp authentication template.
    OTP appears in both the message body and the copy button.
    """
    import requests

    api_key, username = _kit19_credentials()
    mobile = _normalize_phone_kit19(phone)
    otp_str = str(otp)

    template_name = "otp_verification_copy"
    namespace     = "ab750a7e_4257_4e46_8b29_2bb25087d1c4"

    payload = {
        "key": api_key,
        "username": username,
        "name": "whatsapp",
        "remarks": f"{otp_str} is your verification code. For your security, do not share this code.",
        "whatsapp": {
            "to": mobile,
            "type": "template",
            "category": "AUTHENTICATION",
            "recipient_type": "individual",
            "template": {
                "namespace": namespace,
                "language": {"policy": "deterministic", "code": "en"},
                "name": template_name,
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": otp_str}]
                    },
                    {
                        "type": "button",
                        "sub_type": "url",
                        "index": "0",
                        "parameters": [{"type": "text", "text": otp_str}]
                    }
                ]
            }
        }
    }

    response = requests.post(
        "https://services.kit19.com/IMS/Whatsapp/Template",
        headers={"Content-Type": "application/json"},
        json=payload,
        timeout=10
    )

    if not response.ok:
        frappe.throw(f"Kit19 OTP error ({response.status_code}): {response.text}")

    return response.json().get("meta", {}).get("developer_message", "")


def _send_sms_otp(phone, customer_name, crates_delivered, invoice, trip_no, crates_returned, balance, otp):
    import requests
    from frappe.utils.password import get_decrypted_password

    api_key = get_decrypted_password("Crate Settings", "Crate Settings", "sms_api_key", raise_exception=False)
    username = frappe.db.get_single_value("Crate Settings", "sms_username")
    sender_name = frappe.db.get_single_value("Crate Settings", "sms_sender_name")
    pe_id = frappe.db.get_single_value("Crate Settings", "sms_pe_id")
    template_id = frappe.db.get_single_value("Crate Settings", "sms_template_id")

    if not api_key or not username:
        frappe.throw("SMS credentials not configured. Fill SMS API Key and Username in Crate Settings.")

    # Normalize to 10-digit for SMS gateway
    mobile = (phone or "").strip().replace(" ", "").replace("-", "")
    if mobile.startswith("+91"):
        mobile = mobile[3:]
    elif mobile.startswith("91") and len(mobile) == 12:
        mobile = mobile[2:]

    message = (
        f"Hi {customer_name}, Inv No. {invoice}, Delivered: {crates_delivered} crates. "
        f"Trip No. {trip_no}, Returned: {crates_returned} crates. Balance: {balance}. "
        f"OTP: {otp}. Share with driver for verification. Valid 10 min. - BASTAR DAIRY FARM"
    )

    response = requests.get(
        "http://sms.messageindia.in/v2/sendSMS",
        params={
            "username": username,
            "message": message,
            "sendername": sender_name,
            "smstype": "TRANS",
            "numbers": mobile,
            "apikey": api_key,
            "peid": pe_id,
            "templateid": template_id,
        },
        timeout=10
    )

    if not response.ok:
        frappe.throw(f"SMS gateway error ({response.status_code}): {response.text}")

    return response.text


# =============================================================
# SCHEDULED — CLEAR EXPIRED OTPs
# =============================================================

def clear_expired_otps():
    """
    Scheduled hourly job. Finds all Crate Deliveries where the OTP has
    expired but was never cleared (driver abandoned the flow), and wipes
    the otp and otp_expiry fields so they don't sit in the DB indefinitely.
    """
    expired = frappe.db.get_all(
        "Crate Delivery",
        filters={
            "otp": ["!=", ""],
            "otp_expiry": ["<", now_datetime()],
        },
        pluck="name"
    )

    if not expired:
        return

    for name in expired:
        frappe.db.set_value("Crate Delivery", name, {
            "otp": "",
            "otp_expiry": None,
        })

    frappe.db.commit()
