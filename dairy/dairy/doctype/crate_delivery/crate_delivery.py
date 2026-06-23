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

        crate_uom = (
            frappe.db.get_single_value("Crate Settings", "crate_uom")
            or "Crate"
        )

        result = frappe.db.sql(
            """
                SELECT COALESCE(SUM(qty), 0)
                FROM `tabSales Invoice Item`
                WHERE parent = %s
                  AND uom = %s
            """,
            (self.sales_invoice, crate_uom)
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
    """Return total crate qty from a Sales Invoice (uses Crate Settings UOM)."""

    crate_uom = (
        frappe.db.get_single_value("Crate Settings", "crate_uom")
        or "Crate"
    )

    result = frappe.db.sql(
        """
            SELECT COALESCE(SUM(qty), 0)
            FROM `tabSales Invoice Item`
            WHERE parent = %s
              AND uom = %s
        """,
        (sales_invoice, crate_uom)
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

    # Fix 4 — guard: already confirmed, nothing to do
    if doc.customer_confirmed:
        frappe.throw("Delivery already confirmed by customer. No OTP needed.")

    phone = doc.customer_phone
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
# OTP — SEND VIA SMS
# =============================================================

@frappe.whitelist()
def send_delivery_sms(crate_delivery_name):
    doc = frappe.get_doc("Crate Delivery", crate_delivery_name)

    if doc.customer_confirmed:
        frappe.throw("Delivery already confirmed by customer. No OTP needed.")

    phone = doc.customer_phone
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
        f"Hello {customer_name}, A total of {crates_delivered} crates have been delivered to you "
        f"against Invoice No. {invoice}. Against Trip No. {trip_no}, you have returned {crates_returned} crates. "
        f"Your current crate balance is: {balance}. "
        f"To approve and verify this transaction, please share OTP {otp} with the driver. "
        f"This OTP is valid for 10 minutes. Regards, BASTAR DAIRY"
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
