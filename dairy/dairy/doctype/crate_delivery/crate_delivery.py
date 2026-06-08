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

    phone = doc.customer_phone
    if not phone:
        phone = _get_customer_phone(doc.actual_customer)

    if not phone:
        frappe.throw("No mobile number linked to this customer. Please add a phone number in the customer's Contact.")

    otp = str(random.randint(1000, 9999))
    expiry = add_to_date(now_datetime(), minutes=10)

    # Build the message
    driver_name = frappe.db.get_value("Driver", doc.driver, "full_name") or doc.driver
    balance_after = flt(doc.customer_current_balance) + flt(doc.crates_delivered) - flt(doc.crates_returned)
    message = (
        f"Dear Customer,\n"
        f"Bastar Dairy Farm Delivery Confirmation.\n"
        f"Driver: {driver_name}\n"
        f"Crates Delivered: {int(flt(doc.crates_delivered))}\n"
        f"Crates Returned: {int(flt(doc.crates_returned))}\n"
        f"Your Crate Balance: {int(balance_after)}\n"
        f"OTP: {otp}\n"
        f"Share this OTP with the driver to confirm. Valid for 10 minutes."
    )

    channel = "WhatsApp"
    test_otp = None  # populated only when no channel is configured
    try:
        _send_whatsapp(phone, message)
    except Exception:
        try:
            _send_sms(phone, otp)
            channel = "SMS"
        except Exception:
            # Neither WhatsApp nor SMS is configured yet.
            # Save the OTP and return it in the response so the driver
            # can still complete the flow during testing.
            # Once SMS Settings has a valid otp_id, this branch will never run.
            channel = "manual"
            test_otp = otp

    # Persist OTP
    frappe.db.set_value("Crate Delivery", crate_delivery_name, {
        "otp": otp,
        "otp_expiry": expiry,
        "otp_sent_to": phone,
        "customer_phone": phone,
    })
    frappe.db.commit()

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
        frappe.throw("OTP has expired. Please send a new OTP.")

    if str(otp).strip() != str(doc.otp).strip():
        frappe.throw("Incorrect OTP. Please try again.")

    frappe.db.set_value("Crate Delivery", crate_delivery_name, {
        "customer_confirmed": 1,
        "otp": "",
        "otp_expiry": None,
    })
    frappe.db.commit()

    # Submit the draft Crate Delivery now that customer confirmed
    cd = frappe.get_doc("Crate Delivery", crate_delivery_name)
    if cd.docstatus == 0:
        cd.submit()

    return {"confirmed": 1}


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


def _send_whatsapp(phone, message):
    """Insert a frappe_whatsapp WhatsApp Message doc to send a plain text message."""

    wa_doc = frappe.new_doc("WhatsApp Message")
    wa_doc.to = phone
    wa_doc.type = "Outgoing"
    wa_doc.message_type = "Manual"
    wa_doc.content_type = "text"
    wa_doc.message = message
    wa_doc.insert(ignore_permissions=True)


def _send_sms(phone, otp_value):
    """
    Send OTP via Fast2SMS OTP API (https://www.fast2sms.com/dev/otp/send).
    Reads 'authorization' and 'otp_id' from SMS Settings → Parameters child table.
    """
    import requests

    sms_settings = frappe.get_doc("SMS Settings")

    api_key = None
    otp_id = None
    for row in sms_settings.get("parameters", []):
        key = (row.parameter or "").lower().strip()
        if key == "authorization":
            api_key = row.value
        elif key == "otp_id":
            otp_id = row.value

    if not api_key:
        frappe.throw("SMS API key (authorization) not found in SMS Settings parameters.")
    if not otp_id:
        frappe.throw(
            "OTP Template ID missing. Add a parameter named 'otp_id' in SMS Settings "
            "with your Fast2SMS OTP Template ID."
        )

    # Normalize to 10-digit Indian mobile number
    mobile = (phone or "").strip().replace(" ", "").replace("-", "")
    if mobile.startswith("+91"):
        mobile = mobile[3:]
    elif mobile.startswith("91") and len(mobile) == 12:
        mobile = mobile[2:]

    headers = {
        "authorization": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "mobile": mobile,
        "otp_id": otp_id,
        "otp": str(otp_value),
        "otp_expiry": 10,
        "otp_length": 4,
    }

    response = requests.post(
        "https://www.fast2sms.com/dev/otp/send",
        headers=headers,
        json=payload,
    )

    if not response.ok:
        frappe.throw(f"SMS OTP error ({response.status_code}): {response.text}")

    resp_data = response.json()
    if not resp_data.get("return", True):
        frappe.throw(f"Fast2SMS error: {resp_data.get('message', response.text)}")
