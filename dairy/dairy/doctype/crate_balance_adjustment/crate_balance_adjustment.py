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
        cfg = PARTY_MAP.get(self.party_type)
        if not cfg:
            frappe.throw("Invalid Party Type.")

        _, _, supports_loose = cfg
        if supports_loose and not self.driver_balance_type:
            frappe.throw(f"Balance Type is required for {self.party_type}.")

        if self._is_loose():
            self._validate_crate_items()
        elif not flt(self.crates):
            frappe.throw("Crates cannot be zero.")

        for crate_type, crates in self._adjustment_rows():
            self._check_negative_balance(crate_type, crates)

    def _validate_crate_items(self):
        """One row per crate type; rows left at 0 are dropped."""
        doctype, party_name, _, _ = self._party()

        # old single-type document (before the Crate Types table existed)
        if not self.crate_items and self.crate_type:
            if not flt(self.crates):
                frappe.throw("Crates cannot be zero.")
            return

        self.crate_items = [r for r in self.crate_items if flt(r.crates)]
        if not self.crate_items:
            frappe.throw("Enter crates (+/-) for at least one crate type.")

        seen = set()
        for row in self.crate_items:
            if row.crate_type in seen:
                frappe.throw(f"Crate Type <b>{row.crate_type}</b> is entered more than once.")
            seen.add(row.crate_type)
            row.current_balance = self._get_loose_balance(doctype, party_name, row.crate_type)
            row.new_balance = flt(row.current_balance) + flt(row.crates)

        for i, row in enumerate(self.crate_items, 1):
            row.idx = i

        # loose adjustments keep the parent total for list view / reports
        self.crates = sum(flt(r.crates) for r in self.crate_items)

    def _adjustment_rows(self):
        """[(crate_type or None, crates)] — one ledger entry per item."""
        if not self._is_loose():
            return [(None, flt(self.crates))]
        if self.crate_items:
            return [(r.crate_type, flt(r.crates)) for r in self.crate_items if flt(r.crates)]
        if self.crate_type:  # old single-type document
            return [(self.crate_type, flt(self.crates))]
        return []

    def _check_negative_balance(self, crate_type, crates):
        if crates >= 0:
            return  # Adding crates — always fine

        allow_negative = frappe.db.get_single_value("Crate Settings", "allow_negative_crate")
        if allow_negative:
            return

        current = self._get_current_balance(crate_type)
        if current + crates < 0:
            label = f" for <b>{crate_type}</b>" if crate_type else ""
            frappe.throw(
                f"This adjustment would reduce the balance{label} to {current + crates:.0f}, "
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

    def _get_current_balance(self, crate_type=None):
        doctype, party_name, invoice_field, _ = self._party()
        if not party_name:
            return 0
        if crate_type:
            return self._get_loose_balance(doctype, party_name, crate_type)
        return flt(frappe.db.get_value(doctype, party_name, invoice_field))

    def on_submit(self):
        for crate_type, crates in self._adjustment_rows():
            self._create_ledger_entry(crate_type, crates)
            self._update_master_balance(crate_type, crates)

    def on_cancel(self):
        self._delete_ledger_entries()
        for crate_type, crates in self._adjustment_rows():
            self._update_master_balance(crate_type, -crates)

    # =========================================================
    # LEDGER
    # =========================================================

    def _create_ledger_entry(self, crate_type, crates):
        _, party_name, _, _ = self._party()

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

        if crate_type:
            ledger.crate_category = "Loose Crate"
            ledger.crate_type = crate_type

        ledger.balance_crates = self._get_current_balance(crate_type) + crates
        ledger.insert(ignore_permissions=True)

    def _delete_ledger_entries(self):
        for name in frappe.db.get_all(
            "Customer Crate Ledger",
            filters={"crate_balance_adjustment": self.name},
            pluck="name",
        ):
            frappe.delete_doc("Customer Crate Ledger", name, ignore_permissions=True)

    # =========================================================
    # MASTER BALANCE
    # =========================================================

    def _update_master_balance(self, crate_type, delta):
        doctype, party_name, invoice_field, _ = self._party()
        if not party_name:
            return

        if crate_type:
            self._update_loose_balance(doctype, party_name, crate_type, delta)
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
