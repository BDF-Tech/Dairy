import frappe
from frappe.model.document import Document
from frappe.utils import flt


# party_type -> (doctype, invoice_balance_field, supports_loose)
PARTY_MAP = {
    "Customer":  ("Customer",  "custom_current_crate_balance", False),
    "Driver":    ("Driver",    "custom_invoice_crate_balance", True),
    "Warehouse": ("Warehouse", "custom_crate_balance",         True),
}

LOOSE_CHILD_DOCTYPE = "Driver Crate Type Balance"
LOOSE_CHILD_FIELD = "custom_crate_type_balances"


@frappe.whitelist()
def get_party_crate_balances(party_type, party):
    """Return current crate balances for display in the form."""
    cfg = PARTY_MAP.get(party_type)
    if not cfg or not party:
        return {}

    doctype, invoice_field, supports_loose = cfg
    invoice_balance = flt(frappe.db.get_value(doctype, party, invoice_field))

    result = {
        "type": party_type.lower(),
        "invoice_balance": invoice_balance,
        "supports_loose": supports_loose,
    }

    if supports_loose:
        result["loose_balances"] = frappe.db.get_all(
            LOOSE_CHILD_DOCTYPE,
            filters={"parent": party, "parenttype": doctype},
            fields=["crate_type", "balance"],
            order_by="crate_type",
        )

    return result


class CrateBalanceAdjustment(Document):

    def validate(self):
        if not self.crates:
            frappe.throw("Crates cannot be zero.")

        cfg = PARTY_MAP.get(self.party_type)
        if not cfg:
            frappe.throw("Invalid Party Type.")

        _, _, supports_loose = cfg
        if supports_loose:
            if not self.driver_balance_type:
                frappe.throw(f"Balance Type is required for {self.party_type}.")
            if self.driver_balance_type == "Loose Crate" and not self.crate_type:
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

    # =========================================================
    # HELPERS — resolve the selected party
    # =========================================================

    def _party(self):
        """Return (doctype, party_name, invoice_field, supports_loose) for the selected party."""
        cfg = PARTY_MAP.get(self.party_type)
        if not cfg:
            return None, None, None, False
        doctype, invoice_field, supports_loose = cfg
        party_name = {
            "Customer": self.customer,
            "Driver": self.driver,
            "Warehouse": self.warehouse,
        }.get(self.party_type)
        return doctype, party_name, invoice_field, supports_loose

    def _is_loose(self):
        _, _, _, supports_loose = self._party()
        return supports_loose and self.driver_balance_type == "Loose Crate"

    def _get_current_balance(self):
        doctype, party_name, invoice_field, _ = self._party()
        if not party_name:
            return 0
        if self._is_loose():
            return self._get_loose_balance(doctype, party_name, self.crate_type)
        return flt(frappe.db.get_value(doctype, party_name, invoice_field))

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
        doctype, party_name, _, _ = self._party()

        ledger = frappe.new_doc("Customer Crate Ledger")
        ledger.posting_date             = self.date
        ledger.entry_type               = self.entry_type
        ledger.crate_category           = self.entry_type
        ledger.crate_balance_adjustment = self.name
        ledger.ledger_type              = self.party_type
        ledger.crates_out               = crates if crates > 0 else 0
        ledger.crates_in                = abs(crates) if crates < 0 else 0

        # Link the party on the ledger
        if self.party_type == "Customer":
            ledger.customer = party_name
        elif self.party_type == "Driver":
            ledger.driver = party_name
        elif self.party_type == "Warehouse":
            ledger.warehouse = party_name

        if self._is_loose():
            ledger.crate_category = "Loose Crate"
            ledger.crate_type = self.crate_type
            ledger.balance_crates = self._get_loose_balance(doctype, party_name, self.crate_type) + crates
        else:
            ledger.balance_crates = self._get_current_balance() + crates

        ledger.insert(ignore_permissions=True)

    def _delete_ledger_entry(self):
        name = frappe.db.get_value(
            "Customer Crate Ledger",
            {"crate_balance_adjustment": self.name},
            "name"
        )
        if name:
            frappe.delete_doc("Customer Crate Ledger", name, ignore_permissions=True)

    # =========================================================
    # MASTER BALANCE
    # =========================================================

    def _update_master_balance(self, delta):
        doctype, party_name, invoice_field, _ = self._party()
        if not party_name:
            return

        if self._is_loose():
            self._update_loose_balance(doctype, party_name, self.crate_type, delta)
        else:
            current = flt(frappe.db.get_value(doctype, party_name, invoice_field))
            frappe.db.set_value(doctype, party_name, invoice_field, current + delta)

    # =========================================================
    # LOOSE CRATE HELPERS (Driver + Warehouse)
    # =========================================================

    def _get_loose_balance(self, doctype, party_name, crate_type):
        result = frappe.db.get_value(
            LOOSE_CHILD_DOCTYPE,
            {"parent": party_name, "parenttype": doctype, "crate_type": crate_type},
            "balance"
        )
        return flt(result)

    def _update_loose_balance(self, doctype, party_name, crate_type, delta):
        party_doc = frappe.get_doc(doctype, party_name)
        for row in party_doc.get(LOOSE_CHILD_FIELD):
            if row.crate_type == crate_type:
                row.balance = flt(row.balance) + delta
                party_doc.save(ignore_permissions=True)
                return
        # Crate type not found — create new row
        party_doc.append(LOOSE_CHILD_FIELD, {
            "crate_type": crate_type,
            "balance": delta
        })
        party_doc.save(ignore_permissions=True)
