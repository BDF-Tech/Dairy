# Copyright (c) 2026, BDF and contributors
# For license information, please see license.txt

"""Every standardised batch: what was targeted, what the lab found, and what it took.

The per-1000 kg columns are the ones to watch over time — they show how much SMP and
water each batch needed, which moves with the milk's own quality.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.setdefault("from_date", add_days(getdate(), -30))
	filters.setdefault("to_date", getdate())
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Batch"), "fieldname": "name", "fieldtype": "Link", "options": "Milk Standardisation", "width": 130},
		{"label": _("Date"), "fieldname": "posting_datetime", "fieldtype": "Datetime", "width": 150},
		{"label": _("Milk Base"), "fieldname": "finished_item", "fieldtype": "Link", "options": "Item", "width": 110},
		{"label": _("Total Kg"), "fieldname": "total_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Target FAT"), "fieldname": "target_fat", "fieldtype": "Percent", "width": 100},
		{"label": _("Tested FAT"), "fieldname": "tested_fat", "fieldtype": "Percent", "width": 100},
		{"label": _("FAT Deviation"), "fieldname": "fat_deviation", "fieldtype": "Float", "width": 115},
		{"label": _("Target SNF"), "fieldname": "target_snf", "fieldtype": "Percent", "width": 100},
		{"label": _("Tested SNF"), "fieldname": "tested_snf", "fieldtype": "Percent", "width": 100},
		{"label": _("SNF Deviation"), "fieldname": "snf_deviation", "fieldtype": "Float", "width": 115},
		{"label": _("Milk Kg"), "fieldname": "milk_kg", "fieldtype": "Float", "width": 100},
		{"label": _("SMP Kg"), "fieldname": "smp_kg", "fieldtype": "Float", "width": 95},
		{"label": _("Water Kg"), "fieldname": "water_kg", "fieldtype": "Float", "width": 100},
		{"label": _("SMP / 1000 Kg"), "fieldname": "smp_per_1000", "fieldtype": "Float", "width": 120},
		{"label": _("Water / 1000 Kg"), "fieldname": "water_per_1000", "fieldtype": "Float", "width": 130},
		{"label": _("Stock Entry"), "fieldname": "stock_entry", "fieldtype": "Link", "options": "Stock Entry", "width": 150},
	]


def get_data(filters):
	conditions = {"docstatus": 1, "posting_datetime": ["between", [f"{filters.from_date} 00:00:00", f"{filters.to_date} 23:59:59"]]}
	if filters.get("finished_item"):
		conditions["finished_item"] = filters.finished_item
	if filters.get("company"):
		conditions["company"] = filters.company

	batches = frappe.get_all(
		"Milk Standardisation",
		filters=conditions,
		fields=["name", "posting_datetime", "finished_item", "total_qty", "target_fat", "target_snf",
			"tested_fat", "tested_snf", "achieved_fat", "achieved_snf", "stock_entry"],
		order_by="posting_datetime desc",
	)
	if not batches:
		return []

	roles = lever_roles()
	rows = []
	for batch in batches:
		used = {"milk": 0.0, "SNF Booster": 0.0, "Diluent": 0.0, "Fat Booster": 0.0}
		for row in frappe.get_all("Milk Standardisation Ingredient", {"parent": batch.name},
				["item", "qty_kg"]):
			used[roles.get(row.item, "milk")] = used.get(roles.get(row.item, "milk"), 0.0) + flt(row.qty_kg)

		total = flt(batch.total_qty)
		per_1000 = (lambda v: flt(v / total * 1000, 2) if total else 0)
		rows.append({
			**batch,
			"total_qty": flt(total, 2),
			"fat_deviation": flt(flt(batch.tested_fat) - flt(batch.target_fat), 3),
			"snf_deviation": flt(flt(batch.tested_snf) - flt(batch.target_snf), 3),
			"milk_kg": flt(used["milk"], 2),
			"smp_kg": flt(used["SNF Booster"], 2),
			"water_kg": flt(used["Diluent"], 2),
			"smp_per_1000": per_1000(used["SNF Booster"]),
			"water_per_1000": per_1000(used["Diluent"]),
		})
	return rows


def lever_roles():
	"""item code -> its role, so ingredients can be split into milk and additives."""
	settings = frappe.get_cached_doc("Dairy Settings")
	return {l.item: l.role for l in settings.get("milk_standardisation_levers") or []}
