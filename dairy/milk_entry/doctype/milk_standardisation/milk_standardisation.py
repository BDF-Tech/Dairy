# Copyright (c) 2026, BDF and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

# Quantity is used directly as the mass basis on the production blend sheet
# (no litre->kg density conversion), matching how the team calculates today.


class MilkStandardisation(Document):
	def validate(self):
		self._apply_setting_defaults()
		self.compute_batch()

	def before_submit(self):
		if not self.in_spec:
			frappe.throw(
				_(
					"Batch is out of tolerance and cannot be submitted.<br>"
					"Achieved FAT {0}% vs target {1}% (allowed &plusmn;{2}).<br>"
					"Achieved SNF {3}% vs target {4}% (allowed &plusmn;{5}).<br>"
					"Adjust the additive quantities until both are within tolerance."
				).format(
					flt(self.achieved_fat, 3), flt(self.target_fat, 3), flt(self.fat_tolerance, 3),
					flt(self.achieved_snf, 3), flt(self.target_snf, 3), flt(self.snf_tolerance, 3),
				)
			)

	def on_submit(self):
		self.create_manufacture_entry()

	def on_cancel(self):
		self.ignore_linked_doctypes = ("Stock Entry", "Work Order", "Stock Ledger Entry", "GL Entry")
		self._cancel_downstream()

	# ---------------------------------------------------------------- compute

	def _apply_setting_defaults(self):
		settings = frappe.get_cached_doc("Dairy Settings")
		if not self.fat_tolerance:
			self.fat_tolerance = flt(settings.get("default_fat_tolerance")) or 0.1
		if not self.snf_tolerance:
			self.snf_tolerance = flt(settings.get("default_snf_tolerance")) or 0.2

	def compute_batch(self):
		"""Per-row Kg Fat/SNF, then roll up the batch's achieved FAT/SNF."""
		total_qty = total_kg_fat = total_kg_snf = 0.0
		for row in self.ingredients:
			row.kg_fat = flt(row.qty) * flt(row.fat) / 100.0
			row.kg_snf = flt(row.qty) * flt(row.snf) / 100.0
			total_qty += flt(row.qty)
			total_kg_fat += row.kg_fat
			total_kg_snf += row.kg_snf

		self.total_qty = total_qty
		self.total_kg_fat = total_kg_fat
		self.total_kg_snf = total_kg_snf

		if total_qty > 0:
			self.achieved_fat = total_kg_fat / total_qty * 100.0
			self.achieved_snf = total_kg_snf / total_qty * 100.0
		else:
			self.achieved_fat = self.achieved_snf = 0.0

		self.fat_deviation = flt(self.achieved_fat) - flt(self.target_fat)
		self.snf_deviation = flt(self.achieved_snf) - flt(self.target_snf)
		self.in_spec = int(
			total_qty > 0
			and abs(self.fat_deviation) <= flt(self.fat_tolerance) + 1e-9
			and abs(self.snf_deviation) <= flt(self.snf_tolerance) + 1e-9
		)

	# ------------------------------------------------------- stock movement

	def create_manufacture_entry(self):
		if self.stock_entry:
			return

		if not self.target_warehouse:
			frappe.throw(_("Target Warehouse is required to produce the batch."))

		work_order = self._create_work_order()

		se = frappe.new_doc("Stock Entry")
		se.purpose = "Manufacture"
		se.stock_entry_type = "Manufacture"
		se.company = self.company
		se.work_order = work_order.name
		se.bom_no = self.bom
		se.fg_completed_qty = flt(self.total_qty)
		# from_bom stays off: items come from the blend sheet, not the BOM (whose
		# quantities are wrong). Setting it would auto-pull BOM raw materials.
		se.use_multi_level_bom = 0
		se.posting_date = frappe.utils.getdate(self.posting_datetime)
		se.set_posting_time = 1
		se.custom_milk_standardization = self.name
		# Our quantities are computed on the blend sheet, not BOM ratios; keep the
		# WO-validation server script (if ever enabled) from rewriting them.
		if se.meta.has_field("custom_bypass_validation"):
			se.custom_bypass_validation = 1

		for row in self.ingredients:
			if flt(row.qty) <= 0:
				continue
			se.append("items", {
				"item_code": row.item,
				"qty": flt(row.qty),
				"s_warehouse": row.warehouse or self.source_warehouse,
				"uom": row.uom or frappe.db.get_value("Item", row.item, "stock_uom"),
				"conversion_factor": 1,
				"is_finished_item": 0,
			})

		se.append("items", {
			"item_code": self.finished_item,
			"qty": flt(self.total_qty),
			"t_warehouse": self.target_warehouse,
			"uom": frappe.db.get_value("Item", self.finished_item, "stock_uom"),
			"conversion_factor": 1,
			"is_finished_item": 1,
		})

		se.insert(ignore_permissions=True)
		se.submit()

		self.db_set("work_order", work_order.name)
		self.db_set("stock_entry", se.name)
		frappe.msgprint(
			_("Manufacture Stock Entry {0} created.").format(frappe.bold(se.name)),
			indicator="green", alert=True,
		)

	def _create_work_order(self):
		# The Work Order is the manufacturing shell (production item, BOM, qty). Its
		# BOM-derived required_items are only a reference — actual consumption is the
		# blend-sheet-driven Manufacture Stock Entry built in create_manufacture_entry.
		wo = frappe.new_doc("Work Order")
		wo.production_item = self.finished_item
		wo.bom_no = self.bom
		wo.company = self.company
		wo.qty = flt(self.total_qty)
		wo.fg_warehouse = self.target_warehouse
		wo.wip_warehouse = self.source_warehouse or self.target_warehouse
		wo.skip_transfer = 1
		wo.use_multi_level_bom = 0
		wo.insert(ignore_permissions=True)
		wo.submit()
		return wo

	def _cancel_downstream(self):
		if self.stock_entry:
			se = frappe.get_doc("Stock Entry", self.stock_entry)
			if se.docstatus == 1:
				se.cancel()
		if self.work_order:
			wo = frappe.get_doc("Work Order", self.work_order)
			if wo.docstatus == 1:
				wo.cancel()


# ------------------------------------------------------------- auto solver


@frappe.whitelist()
def suggest_quantities(doc):
	"""Given the milk rows already on the sheet + the target, solve how much of
	each configured additive (SNF booster, and water or cream) to add.

	Returns the list of additive rows to append. Milk stays fixed; the batch
	quantity is whatever milk + additives sum to.
	"""
	doc = frappe.parse_json(doc)
	target_fat = flt(doc.get("target_fat"))
	target_snf = flt(doc.get("target_snf"))
	if not (target_fat and target_snf):
		frappe.throw(_("Set Target FAT and Target SNF before suggesting quantities."))

	levers = _get_levers()
	lever_items = {l["item"] for l in levers}

	# Milk = every row whose item is not a configured additive.
	milk_qty = milk_fat_kg = milk_snf_kg = 0.0
	for row in doc.get("ingredients") or []:
		if row.get("item") in lever_items:
			continue
		q = flt(row.get("qty"))
		milk_qty += q
		milk_fat_kg += q * flt(row.get("fat")) / 100.0
		milk_snf_kg += q * flt(row.get("snf")) / 100.0

	if milk_qty <= 0:
		frappe.throw(_("Add at least one milk source with quantity before suggesting additives."))

	blended_fat = milk_fat_kg / milk_qty * 100.0
	blended_snf = milk_snf_kg / milk_qty * 100.0

	snf_lever = _pick(levers, "SNF Booster")
	if not snf_lever:
		frappe.throw(_("No 'SNF Booster' additive is configured in Dairy Settings &rarr; Milk Standardisation."))

	# FAT too high -> dilute with water; FAT too low -> enrich with cream.
	if blended_fat >= target_fat:
		fat_lever = _pick(levers, "Diluent")
		if not fat_lever:
			frappe.throw(_("No 'Diluent' additive is configured in Dairy Settings &rarr; Milk Standardisation."))
	else:
		fat_lever = _pick(levers, "Fat Booster")
		if not fat_lever:
			frappe.throw(_(
				"Blended milk FAT {0}% is below the target {1}% and no 'Fat Booster' additive "
				"is configured. Add one in Dairy Settings, or use higher-fat milk."
			).format(flt(blended_fat, 3), flt(target_fat, 3)))

	p, x = _solve_two(milk_qty, milk_fat_kg, milk_snf_kg, target_fat, target_snf, snf_lever, fat_lever)

	if p < -1e-6 or x < -1e-6:
		frappe.throw(_(
			"The target cannot be reached with the current milk and configured additives "
			"(would need a negative quantity). Check the targets against the milk quality, "
			"or review the additives in Dairy Settings."
		))

	source_warehouse = doc.get("source_warehouse")
	rows = []
	for lever, qty in ((snf_lever, p), (fat_lever, x)):
		if qty <= 1e-6:
			continue
		rows.append({
			"source_name": lever.get("source_name") or "Store",
			"item": lever["item"],
			"warehouse": source_warehouse,
			"qty": flt(qty, 3),
			"fat": lever["fat"],
			"snf": lever["snf"],
		})
	return rows


def _get_levers():
	settings = frappe.get_cached_doc("Dairy Settings")
	levers = []
	for l in settings.get("milk_standardisation_levers") or []:
		levers.append({
			"item": l.item,
			"role": l.role,
			"fat": flt(l.fat),
			"snf": flt(l.snf),
			"source_name": l.get("source_name"),
		})
	return levers


def _pick(levers, role):
	for l in levers:
		if l["role"] == role:
			return l
	return None


def _solve_two(m, mf, ms, F, S, snf_lever, fat_lever):
	"""Solve a 2x2 mass balance for the two additive quantities, milk fixed.

	p = SNF-booster qty, x = FAT-lever qty. Final qty Q = m + p + x.
	  fat:  mf + p*fa/100 + x*fb/100 = F/100 * Q
	  snf:  ms + p*sa/100 + x*sb/100 = S/100 * Q
	"""
	fa, sa = snf_lever["fat"], snf_lever["snf"]
	fb, sb = fat_lever["fat"], fat_lever["snf"]

	a11 = (fa - F) / 100.0
	a12 = (fb - F) / 100.0
	b1 = F / 100.0 * m - mf
	a21 = (sa - S) / 100.0
	a22 = (sb - S) / 100.0
	b2 = S / 100.0 * m - ms

	det = a11 * a22 - a12 * a21
	if abs(det) < 1e-12:
		frappe.throw(_(
			"The configured additives cannot resolve FAT and SNF independently "
			"(their qualities are proportional). Review the additives in Dairy Settings."
		))

	p = (b1 * a22 - b2 * a12) / det
	x = (a11 * b2 - a21 * b1) / det
	return p, x
