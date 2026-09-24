# Copyright (c) 2026, BDF and contributors
# For license information, please see license.txt

"""What each milk silo holds, and at what quality.

A silo is a Warehouse with "Is Milk Silo" ticked. Its quantity comes from Bin, and
its FAT/SNF from the Milk Ledger: every movement of a milk item writes a line with
kg FAT and kg SNF, positive on the way in and negative on the way out. Adding those
lines up gives the silo's kg FAT and kg SNF, which is what mixing means in practice.

The totals are summed rather than read off the newest ledger line's running balance,
because that balance is written in save order — a back-dated or cancelled entry
leaves it stale.
"""

import frappe
from frappe.utils import flt


def get_silo_warehouses(company=None):
	filters = {"custom_is_milk_silo": 1, "is_group": 0, "disabled": 0}
	if company:
		filters["company"] = company
	return frappe.get_all(
		"Warehouse", filters=filters, fields=["name", "custom_silo_capacity as capacity"], order_by="name"
	)


def is_silo(warehouse):
	return bool(warehouse) and bool(frappe.db.get_value("Warehouse", warehouse, "custom_is_milk_silo"))


def get_quality(warehouse, item_code):
	"""The silo's book quality for one item: quantity, kg FAT/SNF and the percentages.

	Quantities are in the item's stock unit; `qty_kg` converts them with the item's
	Weight Per Unit, because FAT and SNF percentages are by weight.
	"""
	from dairy.milk_standardisation.doctype.milk_standardisation.milk_standardisation import kg_per_stock_unit

	qty = flt(frappe.db.get_value("Bin", {"warehouse": warehouse, "item_code": item_code}, "actual_qty"))
	totals = frappe.db.sql(
		"""
		select
			sum(if(actual_qty >= 0, fat, -fat)) as kg_fat,
			sum(if(actual_qty >= 0, snf, -snf)) as kg_snf
		from `tabMilk Ledger Entry`
		where warehouse = %(warehouse)s and item_code = %(item_code)s and ifnull(is_cancelled, 0) = 0
		""",
		{"warehouse": warehouse, "item_code": item_code},
		as_dict=True,
	)[0]

	qty_kg = qty * kg_per_stock_unit(item_code)
	kg_fat, kg_snf = flt(totals.kg_fat), flt(totals.kg_snf)
	return frappe._dict({
		"warehouse": warehouse,
		"item_code": item_code,
		"qty": qty,
		"qty_kg": qty_kg,
		"kg_fat": kg_fat,
		"kg_snf": kg_snf,
		"fat": (kg_fat / qty_kg * 100.0) if qty_kg else 0.0,
		"snf": (kg_snf / qty_kg * 100.0) if qty_kg else 0.0,
		"source": "Milk Ledger",
	})


def get_latest_test(warehouse, item_code=None, max_age_hours=None):
	"""The newest submitted Silo Quality Test for the silo, if there is one."""
	if not frappe.db.exists("DocType", "Silo Quality Test"):
		return None

	filters = {"silo": warehouse, "docstatus": 1}
	if item_code:
		filters["item"] = item_code
	if max_age_hours:
		filters["posting_datetime"] = [">=", frappe.utils.add_to_date(None, hours=-flt(max_age_hours))]

	rows = frappe.get_all(
		"Silo Quality Test",
		filters=filters,
		fields=["name", "item", "posting_datetime", "fat", "snf", "clr", "tested_qty"],
		order_by="posting_datetime desc",
		limit=1,
	)
	return rows[0] if rows else None


@frappe.whitelist()
def get_silo_milk(company=None, item_code=None, max_test_age_hours=12):
	"""Every silo holding milk, with the quality to standardise from.

	The lab's latest test wins while it is fresh; otherwise the Milk Ledger's figure
	is used, so the blend sheet always has something to work with.
	"""
	out = []
	for silo in get_silo_warehouses(company):
		items = [item_code] if item_code else [
			b.item_code for b in frappe.get_all(
				"Bin", {"warehouse": silo.name, "actual_qty": [">", 0]}, ["item_code"]
			)
			if frappe.db.get_value("Item", b.item_code, "maintain_fat_snf_clr")
		]
		for item in items:
			quality = get_quality(silo.name, item)
			if quality.qty <= 0:
				continue
			test = get_latest_test(silo.name, item, max_test_age_hours)
			if test and (flt(test.fat) or flt(test.snf)):
				quality.update({
					"fat": flt(test.fat),
					"snf": flt(test.snf),
					"source": "Silo Quality Test",
					"test": test.name,
					"tested_on": test.posting_datetime,
				})
			quality["capacity"] = flt(silo.capacity)
			out.append(quality)
	return out
