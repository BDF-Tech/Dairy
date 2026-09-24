# Copyright (c) 2026, BDF and contributors
# For license information, please see license.txt

"""What every silo holds right now, and how the lab's last test compares."""

import frappe
from frappe import _
from frappe.utils import flt

from dairy.milk_standardisation.silo import get_latest_test, get_quality, get_silo_warehouses


def execute(filters=None):
	filters = frappe._dict(filters or {})
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Silo"), "fieldname": "silo", "fieldtype": "Link", "options": "Warehouse", "width": 170},
		{"label": _("Milk"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 110},
		{"label": _("Qty (Kg)"), "fieldname": "qty_kg", "fieldtype": "Float", "width": 110},
		{"label": _("Capacity (L)"), "fieldname": "capacity", "fieldtype": "Float", "width": 110},
		{"label": _("Full %"), "fieldname": "full_pct", "fieldtype": "Percent", "width": 80},
		{"label": _("FAT %"), "fieldname": "fat", "fieldtype": "Percent", "width": 90},
		{"label": _("SNF %"), "fieldname": "snf", "fieldtype": "Percent", "width": 90},
		{"label": _("Kg FAT"), "fieldname": "kg_fat", "fieldtype": "Float", "width": 100},
		{"label": _("Kg SNF"), "fieldname": "kg_snf", "fieldtype": "Float", "width": 100},
		{"label": _("Last Test"), "fieldname": "test", "fieldtype": "Link", "options": "Silo Quality Test", "width": 140},
		{"label": _("Tested On"), "fieldname": "tested_on", "fieldtype": "Datetime", "width": 150},
		{"label": _("Tested FAT %"), "fieldname": "tested_fat", "fieldtype": "Percent", "width": 110},
		{"label": _("FAT Difference"), "fieldname": "fat_difference", "fieldtype": "Float", "width": 120},
		{"label": _("SNF Difference"), "fieldname": "snf_difference", "fieldtype": "Float", "width": 120},
	]


def get_data(filters):
	rows = []
	for silo in get_silo_warehouses(filters.get("company")):
		if filters.get("silo") and silo.name != filters.silo:
			continue
		for bin_row in frappe.get_all(
			"Bin", {"warehouse": silo.name, "actual_qty": [">", 0]}, ["item_code"]
		):
			if not frappe.db.get_value("Item", bin_row.item_code, "maintain_fat_snf_clr"):
				continue
			book = get_quality(silo.name, bin_row.item_code)
			test = get_latest_test(silo.name, bin_row.item_code)
			row = {
				"silo": silo.name,
				"item_code": book.item_code,
				"qty_kg": flt(book.qty_kg, 2),
				"capacity": flt(silo.capacity),
				"full_pct": (flt(book.qty) / flt(silo.capacity) * 100) if flt(silo.capacity) else None,
				"fat": flt(book.fat, 3),
				"snf": flt(book.snf, 3),
				"kg_fat": flt(book.kg_fat, 2),
				"kg_snf": flt(book.kg_snf, 2),
			}
			if test:
				row.update({
					"test": test.name,
					"tested_on": test.posting_datetime,
					"tested_fat": flt(test.fat, 3),
					"fat_difference": flt(flt(test.fat) - book.fat, 3),
					"snf_difference": flt(flt(test.snf) - book.snf, 3),
				})
			rows.append(row)
	return rows
