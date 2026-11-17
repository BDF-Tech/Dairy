import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, today

from dairy.franchise_pos.stock import (
	add_ledger_rows,
	day_figures,
	day_sales,
	last_closed_date,
	need_pos_franchise,
	remove_ledger_rows,
)


class FranchiseDayClose(Document):
	"""End of day for a franchise: opening / received / sold / closing per item, wastage, and the
	counted stock. The counted closing becomes tomorrow's opening."""

	def validate(self):
		need_pos_franchise(self.franchise)
		self.franchise_code = self.franchise  # the Link shows the customer's name; this shows the code
		self.posting_date = self.posting_date or today()
		if getdate(self.posting_date) > getdate(today()):
			frappe.throw(_("A day cannot be closed in advance."))
		other = frappe.db.get_value(
			"Franchise Day Close",
			{"franchise": self.franchise, "posting_date": self.posting_date, "docstatus": ["<", 2], "name": ["!=", self.name or ""]},
		)
		if other:
			frappe.throw(_("Day Close {0} already exists for this date.").format(other))
		closed = last_closed_date(self.franchise, exclude=self.name)
		if closed and getdate(self.posting_date) <= closed:
			frappe.throw(_("The day is already closed up to {0}.").format(frappe.format(closed, {"fieldtype": "Date"})))
		self.set_figures()

	def set_figures(self):
		"""System figures always come from the ledger; only Wastage and Counted Closing are the user's."""
		entered = {d.item_code: d for d in self.items}
		rows = day_figures(self.franchise, self.posting_date)
		known = {r.item_code for r in rows}
		# an item counted on the shelf that the book does not know about (opening stock on day one)
		extra = [c for c in entered if c not in known]
		if extra:
			for i in frappe.get_all("Item", filters={"name": ["in", extra]}, fields=["name", "item_name", "stock_uom"]):
				rows.append(frappe._dict(item_code=i.name, item_name=i.item_name, uom=i.stock_uom, opening_qty=0,
										received_qty=0, sold_qty=0, returned_qty=0, expected_qty=0))

		self.set("items", [])
		for r in rows:
			old = entered.get(r.item_code)
			wastage = flt(old.wastage_qty) if old else 0
			if wastage < 0:
				frappe.throw(_("{0}: wastage cannot be negative.").format(r.item_name))
			book = flt(r.expected_qty - wastage, 3)
			# not counted = taken as equal to the book
			actual = flt(old.actual_qty) if old and old.actual_qty is not None else book
			if actual < 0:
				frappe.throw(_("{0}: counted closing cannot be negative.").format(r.item_name))
			self.append("items", {
				"item_code": r.item_code, "item_name": r.item_name, "uom": r.uom,
				"opening_qty": r.opening_qty, "received_qty": r.received_qty, "sold_qty": r.sold_qty,
				"returned_qty": r.returned_qty, "expected_qty": r.expected_qty,
				"wastage_qty": wastage, "actual_qty": actual, "difference_qty": flt(actual - book, 3),
			})
		self.update(day_sales(self.franchise, self.posting_date))

	def on_submit(self):
		rows = []
		for d in self.items:
			base = {
				"franchise": self.franchise, "item_code": d.item_code, "item_name": d.item_name, "uom": d.uom,
				"posting_date": self.posting_date, "posting_time": "23:59:59",
				"voucher_type": self.doctype, "voucher_no": self.name,
			}
			if flt(d.wastage_qty):
				rows.append(dict(base, qty=-flt(d.wastage_qty), entry_type="Wastage"))
			if flt(d.difference_qty):
				rows.append(dict(base, qty=flt(d.difference_qty), entry_type="Stock Adjustment",
								remarks="Counted closing differs from the book"))
		add_ledger_rows(rows)

	def before_cancel(self):
		closed = last_closed_date(self.franchise, exclude=self.name)
		if closed and closed > getdate(self.posting_date):
			frappe.throw(_("Only the latest Day Close can be cancelled. Cancel the later ones first."))

	def on_cancel(self):
		remove_ledger_rows(self.doctype, self.name)

	@frappe.whitelist()
	def get_stock(self):
		"""Desk button: fill the item rows for the chosen franchise and date."""
		need_pos_franchise(self.franchise)
		self.set_figures()
		return self.as_dict()


def on_doctype_update():
	frappe.db.add_index("Franchise Day Close", ["franchise", "posting_date"])
