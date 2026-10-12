# Copyright (c) 2026, BDF and contributors
# For license information, please see license.txt

"""Set a warehouse's FAT/SNF to what the lab measured.

The Milk Ledger is a running total: every movement adds kg FAT and kg SNF on the way
in and takes them off on the way out. Years of movements that carried no quality left
those totals meaningless, and a single wrong line keeps distorting every reading after
it.

This document does not rewrite that history. It reads what the ledger says, takes the
lab's figure for the milk actually standing in the warehouse, and posts the difference
as one adjustment line. From that moment the balance equals the tested figure, and
ordinary movements carry on from there -- the same thing a Stock Reconciliation does
for quantity. Run it once to open the books, then monthly against the physical dip.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, get_datetime

from dairy.milk_standardisation.doctype.milk_standardisation.milk_standardisation import kg_per_stock_unit
from dairy.milk_standardisation.silo import get_quality, get_silo_warehouses

VOUCHER_TYPE = "Milk Fat Reconciliation"


def ledger_qty(warehouse, item_code):
	"""What the Milk Ledger's quantity column adds up to (not the real stock)."""
	return flt(frappe.db.sql(
		"""select sum(actual_qty) from `tabMilk Ledger Entry`
		where warehouse = %s and item_code = %s and ifnull(is_cancelled, 0) = 0""",
		(warehouse, item_code),
	)[0][0])


class MilkFatReconciliation(Document):
	def validate(self):
		self.compute_lines()

	def on_submit(self):
		self.post_adjustments()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("Milk Ledger Entry",)
		self.cancel_adjustments()

	# ---------------------------------------------------------------- compute

	def compute_lines(self):
		"""Per line: the kg the lab implies, the kg the ledger holds, and the gap."""
		totals = frappe._dict(qty_kg=0.0, tested_fat=0.0, tested_snf=0.0, book_fat=0.0,
			book_snf=0.0, adj_fat=0.0, adj_snf=0.0, adj_qty=0.0)

		for row in self.items:
			if not (row.warehouse and row.item):
				continue

			book = get_quality(row.warehouse, row.item)
			row.qty = flt(book.qty)
			row.uom = row.uom or frappe.db.get_value("Item", row.item, "stock_uom")
			row.qty_kg = flt(row.qty) * kg_per_stock_unit(row.item)
			row.book_kg_fat = flt(book.kg_fat)
			row.book_kg_snf = flt(book.kg_snf)
			row.book_fat = flt(book.fat)
			row.book_snf = flt(book.snf)
			# The ledger's own quantity column drifted too, which makes every percentage
			# read from it wrong even once the kg are right.
			row.book_qty = ledger_qty(row.warehouse, row.item)
			row.qty_adjustment = flt(row.qty) - flt(row.book_qty)

			row.tested_kg_fat = row.qty_kg * flt(row.tested_fat) / 100.0
			row.tested_kg_snf = row.qty_kg * flt(row.tested_snf) / 100.0
			row.fat_adjustment = row.tested_kg_fat - row.book_kg_fat
			row.snf_adjustment = row.tested_kg_snf - row.book_kg_snf

			totals.qty_kg += row.qty_kg
			totals.tested_fat += row.tested_kg_fat
			totals.tested_snf += row.tested_kg_snf
			totals.book_fat += row.book_kg_fat
			totals.book_snf += row.book_kg_snf
			totals.adj_fat += row.fat_adjustment
			totals.adj_snf += row.snf_adjustment
			totals.adj_qty += row.qty_adjustment

		self.total_qty_adjustment = totals.adj_qty
		self.total_qty_kg = totals.qty_kg
		self.total_tested_kg_fat = totals.tested_fat
		self.total_tested_kg_snf = totals.tested_snf
		self.total_book_kg_fat = totals.book_fat
		self.total_book_kg_snf = totals.book_snf
		self.total_fat_adjustment = totals.adj_fat
		self.total_snf_adjustment = totals.adj_snf

	# ------------------------------------------------------------- the ledger

	def post_adjustments(self):
		"""Up to two Milk Ledger lines per row: one for the quality, one for the quantity.

		They stay separate because of how the ledger is totalled: kg FAT counts as
		`+fat` on a line whose quantity is zero or more and `-fat` below that. A single
		line carrying a negative quantity correction would therefore flip the sign of its
		own kg. So the quality line moves nothing (quantity 0, signed kg) and the
		quantity line carries no kg.
		"""
		posting = get_datetime(self.posting_datetime)
		quality_lines = qty_lines = 0

		for row in self.items:
			common = {
				"doctype": "Milk Ledger Entry",
				"item_code": row.item,
				"warehouse": row.warehouse,
				"posting_date": posting.date(),
				"posting_time": posting.time(),
				"voucher_type": VOUCHER_TYPE,
				"voucher_no": self.name,
				"voucher_detail_no": row.name,
				"fat_per": flt(row.tested_fat),
				"snf_per": flt(row.tested_snf),
				"stock_uom": row.uom,
				"qty_after_transaction": flt(row.qty),
				"fat_after_transaction": flt(row.tested_kg_fat),
				"snf_after_transaction": flt(row.tested_kg_snf),
				"company": self.company,
				"is_cancelled": 0,
			}

			if abs(flt(row.fat_adjustment)) > 1e-6 or abs(flt(row.snf_adjustment)) > 1e-6:
				frappe.get_doc(dict(common, actual_qty=0,
					fat=flt(row.fat_adjustment), snf=flt(row.snf_adjustment))).insert(ignore_permissions=True)
				quality_lines += 1

			if abs(flt(row.qty_adjustment)) > 1e-6:
				frappe.get_doc(dict(common, actual_qty=flt(row.qty_adjustment),
					fat=0, snf=0)).insert(ignore_permissions=True)
				qty_lines += 1

		frappe.msgprint(
			_("Adjusted {0} line(s) for quality (FAT {1} kg, SNF {2} kg) and {3} for quantity ({4}).").format(
				quality_lines, flt(self.total_fat_adjustment, 2), flt(self.total_snf_adjustment, 2),
				qty_lines, flt(self.total_qty_adjustment, 2)),
			indicator="green", alert=True,
		)

	def cancel_adjustments(self):
		for name in frappe.get_all("Milk Ledger Entry",
			filters={"voucher_type": VOUCHER_TYPE, "voucher_no": self.name}, pluck="name"):
			frappe.db.set_value("Milk Ledger Entry", name, "is_cancelled", 1)


# ------------------------------------------------------------------- fetching


@frappe.whitelist()
def get_milk_stock(company=None, scope="All Warehouses", warehouse=None):
	"""Every warehouse holding milk, with what the ledger currently says about it.

	The lab's own FAT/SNF is left blank -- that is what the person entering this
	document fills in.
	"""
	if scope == "One Warehouse":
		if not warehouse:
			frappe.throw(_("Select the Warehouse to reconcile."))
		warehouses = [warehouse]
	elif scope == "Silos Only":
		warehouses = [s.name for s in get_silo_warehouses(company)]
		if not warehouses:
			frappe.throw(_("No warehouse has 'Is Milk Silo' ticked."))
	else:
		warehouses = None

	conditions = ["b.actual_qty > 0", "i.maintain_fat_snf_clr = 1"]
	values = {}
	if warehouses is not None:
		conditions.append("b.warehouse in %(warehouses)s")
		values["warehouses"] = warehouses
	if company:
		conditions.append("w.company = %(company)s")
		values["company"] = company

	rows = frappe.db.sql(
		"""
		select b.warehouse, b.item_code, b.actual_qty, i.stock_uom
		from tabBin b
			join tabItem i on i.name = b.item_code
			join tabWarehouse w on w.name = b.warehouse
		where {conditions}
		order by b.warehouse, b.item_code
		""".format(conditions=" and ".join(conditions)),
		values,
		as_dict=True,
	)

	out = []
	for r in rows:
		book = get_quality(r.warehouse, r.item_code)
		out.append({
			"warehouse": r.warehouse,
			"item": r.item_code,
			"qty": flt(r.actual_qty),
			"uom": r.stock_uom,
			"qty_kg": flt(r.actual_qty) * kg_per_stock_unit(r.item_code),
			"book_fat": flt(book.fat),
			"book_snf": flt(book.snf),
			"book_kg_fat": flt(book.kg_fat),
			"book_kg_snf": flt(book.kg_snf),
			"book_qty": ledger_qty(r.warehouse, r.item_code),
		})
	return out
