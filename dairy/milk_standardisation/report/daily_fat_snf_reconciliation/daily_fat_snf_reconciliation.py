# Copyright (c) 2026, BDF and contributors
# For license information, please see license.txt

"""Per silo, per day: what came in, what went out, and whether the fat adds up.

Opening + received - used = closing is always true of the ledger itself. The figure
worth reading is the last line: the lab's dip and test for that day against the
ledger's closing. That gap is the day's real gain or loss.
"""

import frappe
from frappe import _
from frappe.utils import add_days, flt, getdate

from dairy.milk_standardisation.doctype.milk_standardisation.milk_standardisation import kg_per_stock_unit
from dairy.milk_standardisation.silo import get_silo_warehouses


def execute(filters=None):
	filters = frappe._dict(filters or {})
	filters.setdefault("from_date", add_days(getdate(), -7))
	filters.setdefault("to_date", getdate())
	return get_columns(), get_data(filters)


def get_columns():
	return [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": _("Silo"), "fieldname": "silo", "fieldtype": "Link", "options": "Warehouse", "width": 160},
		{"label": _("Milk"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 100},
		{"label": _("Opening Kg"), "fieldname": "opening_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Received Kg"), "fieldname": "in_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Used Kg"), "fieldname": "out_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Closing Kg"), "fieldname": "closing_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Opening Kg FAT"), "fieldname": "opening_fat", "fieldtype": "Float", "width": 130},
		{"label": _("Received Kg FAT"), "fieldname": "in_fat", "fieldtype": "Float", "width": 135},
		{"label": _("Used Kg FAT"), "fieldname": "out_fat", "fieldtype": "Float", "width": 120},
		{"label": _("Closing Kg FAT"), "fieldname": "closing_fat", "fieldtype": "Float", "width": 130},
		{"label": _("Closing Kg SNF"), "fieldname": "closing_snf", "fieldtype": "Float", "width": 130},
		{"label": _("Closing FAT %"), "fieldname": "closing_fat_pct", "fieldtype": "Percent", "width": 120},
		{"label": _("Tested FAT %"), "fieldname": "tested_fat", "fieldtype": "Percent", "width": 110},
		{"label": _("Dip Kg"), "fieldname": "tested_qty", "fieldtype": "Float", "width": 100},
		{"label": _("Qty Gap Kg"), "fieldname": "qty_gap", "fieldtype": "Float", "width": 110},
		{"label": _("FAT Gap Kg"), "fieldname": "fat_gap", "fieldtype": "Float", "width": 110},
	]


def get_data(filters):
	silos = [s.name for s in get_silo_warehouses(filters.get("company"))]
	if filters.get("silo"):
		silos = [filters.silo] if filters.silo in silos else []
	if not silos:
		return []

	ledger = frappe.db.sql(
		"""
		select
			warehouse, item_code, posting_date,
			sum(if(actual_qty >= 0, actual_qty, 0)) as in_qty,
			sum(if(actual_qty < 0, -actual_qty, 0)) as out_qty,
			sum(if(actual_qty >= 0, fat, 0)) as in_fat,
			sum(if(actual_qty < 0, fat, 0)) as out_fat,
			sum(if(actual_qty >= 0, snf, 0)) as in_snf,
			sum(if(actual_qty < 0, snf, 0)) as out_snf
		from `tabMilk Ledger Entry`
		where ifnull(is_cancelled, 0) = 0 and warehouse in %(silos)s and posting_date <= %(to_date)s
		group by warehouse, item_code, posting_date
		order by warehouse, item_code, posting_date
		""",
		{"silos": silos, "to_date": filters.to_date},
		as_dict=True,
	)

	running = {}
	rows = []
	for day in ledger:
		key = (day.warehouse, day.item_code)
		qty, kg_fat, kg_snf = running.get(key, (0.0, 0.0, 0.0))
		density = kg_per_stock_unit(day.item_code)

		opening_qty, opening_fat, opening_snf = qty, kg_fat, kg_snf
		qty += flt(day.in_qty) - flt(day.out_qty)
		kg_fat += flt(day.in_fat) - flt(day.out_fat)
		kg_snf += flt(day.in_snf) - flt(day.out_snf)
		running[key] = (qty, kg_fat, kg_snf)

		if getdate(day.posting_date) < getdate(filters.from_date):
			continue  # only builds the opening balance

		closing_kg = qty * density
		row = {
			"date": day.posting_date,
			"silo": day.warehouse,
			"item_code": day.item_code,
			"opening_qty": flt(opening_qty * density, 2),
			"in_qty": flt(flt(day.in_qty) * density, 2),
			"out_qty": flt(flt(day.out_qty) * density, 2),
			"closing_qty": flt(closing_kg, 2),
			"opening_fat": flt(opening_fat, 2),
			"in_fat": flt(day.in_fat, 2),
			"out_fat": flt(day.out_fat, 2),
			"closing_fat": flt(kg_fat, 2),
			"closing_snf": flt(kg_snf, 2),
			"closing_fat_pct": flt(kg_fat / closing_kg * 100, 3) if closing_kg else 0,
		}

		test = last_test_of_day(day.warehouse, day.item_code, day.posting_date)
		if test:
			tested_kg = flt(test.tested_qty) * density
			row.update({
				"tested_fat": flt(test.fat, 3),
				"tested_qty": flt(tested_kg, 2) or None,
				"qty_gap": flt(tested_kg - closing_kg, 2) if tested_kg else None,
				"fat_gap": flt(tested_kg * flt(test.fat) / 100 - kg_fat, 2) if tested_kg else None,
			})
		rows.append(row)
	return rows


def last_test_of_day(silo, item_code, date):
	if not frappe.db.exists("DocType", "Silo Quality Test"):
		return None
	tests = frappe.get_all(
		"Silo Quality Test",
		filters={"silo": silo, "item": item_code, "docstatus": 1,
			"posting_datetime": ["between", [f"{date} 00:00:00", f"{date} 23:59:59"]]},
		fields=["fat", "snf", "tested_qty"],
		order_by="posting_datetime desc",
		limit=1,
	)
	return tests[0] if tests else None
