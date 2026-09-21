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

		target = flt(self.target_batch_qty)
		if target and self.total_qty > target + flt(self.batch_qty_tolerance) + 1e-9:
			over = self.total_qty - target
			frappe.throw(
				_(
					"Total batch quantity {0} exceeds the Target Batch Quantity {1} by {2} "
					"(allowed +{3}).<br>The additives add volume on top of the milk. To land on "
					"{1}, reduce the milk/ingredient quantities (or use Auto mode, which solves to "
					"exactly {1}), or raise the Target Batch Quantity."
				).format(
					flt(self.total_qty, 3), flt(target, 3), flt(over, 3), flt(self.batch_qty_tolerance, 3),
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
		if not self.batch_qty_tolerance:
			self.batch_qty_tolerance = 1.0

	def compute_batch(self):
		"""Per-row Kg Fat/SNF, then roll up the batch's achieved FAT/SNF.

		Each row's quantity is converted to the item's stock unit first, so rows
		entered in different units (kg / gm / litre) reconcile onto one basis.
		"""
		total_qty = total_kg_fat = total_kg_snf = 0.0
		for row in self.ingredients:
			cf = flt(row.conversion_factor) or 1.0
			row.conversion_factor = cf
			row.stock_qty = flt(row.qty) * cf
			row.kg_fat = row.stock_qty * flt(row.fat) / 100.0
			row.kg_snf = row.stock_qty * flt(row.snf) / 100.0
			total_qty += row.stock_qty
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
		self.batch_qty_deviation = total_qty - flt(self.target_batch_qty)
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
		# from_bom must be truthy or Stock Entry.validate zeroes fg_completed_qty
		# (erpnext stock_entry.py: "if not self.from_bom: fg_completed_qty = 0").
		# It does NOT auto-pull BOM items — that only happens on an explicit get_items().
		se.from_bom = 1
		se.use_multi_level_bom = 0
		se.fg_completed_qty = flt(self.total_qty)
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
				"s_warehouse": row.warehouse or row.source_name or self.source_warehouse,
				"uom": row.uom or frappe.db.get_value("Item", row.item, "stock_uom"),
				"conversion_factor": flt(row.conversion_factor) or 1,
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
	"""Solve the whole recipe so the FINAL total equals the Target Batch Quantity
	exactly, at the target FAT/SNF.

	The milk rows define the blend (ratio + quality); their quantities are scaled so
	that milk + additives = Target Batch Quantity. Three unknowns (milk, SNF booster,
	FAT lever), three balance equations (total, fat, snf).

	Returns the full replacement ingredient list (scaled milk + additives).
	"""
	doc = frappe.parse_json(doc)
	F = flt(doc.get("target_fat"))
	S = flt(doc.get("target_snf"))
	Q = flt(doc.get("target_batch_qty"))
	if not (F and S):
		frappe.throw(_("Set Target FAT and Target SNF before suggesting quantities."))
	if not Q:
		frappe.throw(_(
			"Set the Target Batch Quantity first. Auto mode solves the recipe to hit exactly "
			"that quantity."
		))

	levers = _get_levers()
	lever_items = {l["item"] for l in levers}

	# Milk = every row whose item is not a configured additive; work in stock units.
	milk_rows, milk_qty, mf, ms = [], 0.0, 0.0, 0.0
	for row in doc.get("ingredients") or []:
		if row.get("item") in lever_items:
			continue
		sq = flt(row.get("qty")) * (flt(row.get("conversion_factor")) or 1.0)
		milk_qty += sq
		mf += sq * flt(row.get("fat")) / 100.0
		ms += sq * flt(row.get("snf")) / 100.0
		milk_rows.append(row)

	if milk_qty <= 0:
		frappe.throw(_("Add at least one milk source with quantity before suggesting quantities."))

	fr = mf / milk_qty * 100.0
	sr = ms / milk_qty * 100.0

	snf_lever = _pick(levers, "SNF Booster")
	if not snf_lever:
		frappe.throw(_("No 'SNF Booster' additive is configured in Dairy Settings &rarr; Milk Standardisation."))
	diluent = _pick(levers, "Diluent")
	booster = _pick(levers, "Fat Booster")

	# Pick the FAT lever by direction (water if milk is fat-rich, cream if fat-poor);
	# fall back to the other if the first is infeasible.
	primary = diluent if fr >= F else booster
	secondary = booster if fr >= F else diluent

	attempts = []
	solution = None
	for fat_lever in (primary, secondary):
		if not fat_lever:
			continue
		m_qty, p, x = _solve_three(fr, sr, F, S, Q, snf_lever, fat_lever)
		attempts.append((fat_lever, m_qty, p, x))
		if m_qty >= -1e-6 and p >= -1e-6 and x >= -1e-6:
			solution = (fat_lever, m_qty, p, x)
			break

	if not solution:
		_throw_infeasible(fr, sr, F, S, Q, snf_lever, diluent, booster, attempts)

	fat_lever, m_qty, p, x = solution
	factor = m_qty / milk_qty  # scale milk to the solved amount, preserving the blend
	source_warehouse = doc.get("source_warehouse")

	out = []
	for row in milk_rows:
		out.append({
			"source_name": row.get("source_name"),
			"item": row.get("item"),
			"warehouse": row.get("warehouse"),
			"qty": flt(flt(row.get("qty")) * factor, 3),
			"uom": row.get("uom"),
			"conversion_factor": flt(row.get("conversion_factor")) or 1,
			"fat": flt(row.get("fat")),
			"snf": flt(row.get("snf")),
		})
	for lever, qty in ((snf_lever, p), (fat_lever, x)):
		if qty <= 1e-6:
			continue
		out.append({
			"source_name": source_warehouse,
			"item": lever["item"],
			"warehouse": source_warehouse,
			"qty": flt(qty, 3),
			"uom": frappe.db.get_value("Item", lever["item"], "stock_uom"),
			"conversion_factor": 1,
			"fat": lever["fat"],
			"snf": lever["snf"],
		})
	return out


def _get_levers():
	settings = frappe.get_cached_doc("Dairy Settings")
	levers = []
	for l in settings.get("milk_standardisation_levers") or []:
		levers.append({
			"item": l.item,
			"role": l.role,
			"fat": flt(l.fat),
			"snf": flt(l.snf),
			"default_uom": l.get("default_uom"),
			"source_name": l.get("source_name"),
		})
	return levers


@frappe.whitelist()
def get_item_row_defaults(item):
	"""Defaults for a blend-sheet row: the item's stock UOM, and — if the item is a
	configured additive lever — its FAT/SNF impact and preferred UOM from settings."""
	stock_uom = frappe.db.get_value("Item", item, "stock_uom")
	out = {"stock_uom": stock_uom, "is_lever": False}
	for lever in _get_levers():
		if lever["item"] == item:
			out.update({
				"is_lever": True,
				"role": lever["role"],
				"fat": lever["fat"],
				"snf": lever["snf"],
				"uom": lever.get("default_uom") or stock_uom,
			})
			break
	return out


def _pick(levers, role):
	for l in levers:
		if l["role"] == role:
			return l
	return None


def _det3(m):
	return (
		m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
		- m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
		+ m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])
	)


def _solve_three(fr, sr, F, S, Q, snf_lever, fat_lever):
	"""Solve for milk / SNF-booster / FAT-lever quantities so the FINAL total is Q.

	Unknowns m (milk), p (SNF booster), x (FAT lever); blended milk is fr/sr.
	  total:  m + p + x        = Q
	  fat:    m*fr + p*fa + x*fb = Q*F
	  snf:    m*sr + p*sa + x*sb = Q*S
	"""
	fa, sa = snf_lever["fat"], snf_lever["snf"]
	fb, sb = fat_lever["fat"], fat_lever["snf"]

	A = [[1.0, 1.0, 1.0], [fr, fa, fb], [sr, sa, sb]]
	b = [Q, Q * F, Q * S]
	det = _det3(A)
	if abs(det) < 1e-9:
		frappe.throw(_(
			"The milk and configured additives cannot resolve FAT and SNF independently "
			"(their qualities are proportional). Review the additives in Dairy Settings."
		))

	def col(i):
		M = [r[:] for r in A]
		for r in range(3):
			M[r][i] = b[r]
		return _det3(M)

	return col(0) / det, col(1) / det, col(2) / det


def _throw_infeasible(fr, sr, F, S, Q, snf_lever, diluent, booster, attempts):
	"""Raise a specific, numeric message for why no positive recipe hits the target."""
	# Report the first attempt (the direction-appropriate lever) as the diagnosis.
	fat_lever, m_qty, p, x = attempts[0]
	role = fat_lever["role"]
	lines = [_("The target cannot be reached with this milk and the configured additives:")]

	if m_qty < -1e-6:
		lines.append(_(
			"Milk would be negative ({0}) — the additives alone would exceed the Target Batch "
			"Quantity {1}. Increase the Target Batch Quantity, or ease the FAT/SNF targets."
		).format(flt(m_qty, 2), flt(Q, 2)))
	if p < -1e-6:
		lines.append(_(
			"SNF booster ({0}) would be negative ({1} kg) — the milk's SNF {2}% is already high "
			"for the {3}% target at this fat level. SMP can only raise SNF. Lower the target SNF, "
			"or dilute with more water."
		).format(snf_lever["item"], flt(p, 2), flt(sr, 2), flt(S, 2)))
	if x < -1e-6:
		if role == "Diluent":
			lines.append(_(
				"RO Water ({0}) would be negative ({1}) — water only lowers FAT, but the milk FAT "
				"{2}% is already at/below the {3}% target. Use a Fat Booster (cream), or higher-fat milk."
			).format(fat_lever["item"], flt(x, 2), flt(fr, 2), flt(F, 2)))
		else:
			lines.append(_(
				"Cream ({0}) would be negative ({1}) — cream only raises FAT, but the milk FAT {2}% "
				"already exceeds the {3}% target. Use a Diluent (water) instead."
			).format(fat_lever["item"], flt(x, 2), flt(fr, 2), flt(F, 2)))

	if not diluent and fr >= F:
		lines.append(_("Tip: no 'Diluent' additive is configured to lower FAT."))
	if not booster and fr < F:
		lines.append(_("Tip: no 'Fat Booster' additive is configured to raise FAT."))

	frappe.throw("<br>".join(lines))
