import frappe
from frappe.model.document import Document


class FranchiseStockLedger(Document):
	"""One row per stock movement of a franchise. Written only by dairy.franchise_pos.stock."""


def on_doctype_update():
	frappe.db.add_index("Franchise Stock Ledger", ["franchise", "item_code", "posting_date"])
	frappe.db.add_index("Franchise Stock Ledger", ["voucher_type", "voucher_no"])
