# Copyright (c) 2026, BDF and contributors
# For license information, please see license.txt

"""Every FAT/SNF movement, read straight from the Milk Ledger.

The older Milk Ledger report joins the quantity ledger, so it can only show a fat line
that moved stock -- a Milk Fat Reconciliation, which corrects quality and moves nothing,
never appears in it. This report reads the Milk Ledger alone: purchases, transfers,
manufacture, reconciliations, all of them, with or without quantity.

Each row shows what went in and what came out, and the running balance of kg FAT and
kg SNF for that warehouse and item, so the balance can be traced line by line. Opening
balances come from everything before the From Date.
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
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Datetime", "width": 150},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 170},
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 90},
		{"label": _("Type"), "fieldname": "voucher_type", "fieldtype": "Data", "width": 150},
		{"label": _("Document"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 150},
		{"label": _("Qty In"), "fieldname": "qty_in", "fieldtype": "Float", "width": 90},
		{"label": _("Qty Out"), "fieldname": "qty_out", "fieldtype": "Float", "width": 90},
		{"label": _("FAT %"), "fieldname": "fat_per", "fieldtype": "Percent", "width": 80},
		{"label": _("SNF %"), "fieldname": "snf_per", "fieldtype": "Percent", "width": 80},
		{"label": _("Kg FAT In"), "fieldname": "fat_in", "fieldtype": "Float", "width": 100},
		{"label": _("Kg FAT Out"), "fieldname": "fat_out", "fieldtype": "Float", "width": 105},
		{"label": _("Kg SNF In"), "fieldname": "snf_in", "fieldtype": "Float", "width": 100},
		{"label": _("Kg SNF Out"), "fieldname": "snf_out", "fieldtype": "Float", "width": 105},
		{"label": _("Balance Qty"), "fieldname": "balance_qty", "fieldtype": "Float", "width": 110},
		{"label": _("Balance Kg FAT"), "fieldname": "balance_fat", "fieldtype": "Float", "width": 130},
		{"label": _("Balance Kg SNF"), "fieldname": "balance_snf", "fieldtype": "Float", "width": 130},
		{"label": _("Balance FAT %"), "fieldname": "balance_fat_per", "fieldtype": "Percent", "width": 120},
		{"label": _("Balance SNF %"), "fieldname": "balance_snf_per", "fieldtype": "Percent", "width": 120},
	]


def _conditions(filters, warehouses):
	where = ["ifnull(mle.is_cancelled, 0) = 0"]
	values = {}
	if filters.get("company"):
		where.append("mle.company = %(company)s")
		values["company"] = filters.company
	if filters.get("item_code"):
		where.append("mle.item_code = %(item_code)s")
		values["item_code"] = filters.item_code
	if filters.get("voucher_type"):
		where.append("mle.voucher_type = %(voucher_type)s")
		values["voucher_type"] = filters.voucher_type
	if warehouses is not None:
		where.append("mle.warehouse in %(warehouses)s")
		values["warehouses"] = warehouses
	if filters.get("quantity_only"):
		where.append("mle.actual_qty <> 0")
	return where, values


def get_data(filters):
	warehouses = None
	if filters.get("warehouse"):
		warehouses = [filters.warehouse]
	elif filters.get("silos_only"):
		warehouses = [s.name for s in get_silo_warehouses(filters.get("company"))]
		if not warehouses:
			return []

	where, values = _conditions(filters, warehouses)
	values.update({"from_date": filters.from_date, "to_date": filters.to_date})

	# What each warehouse + item held before the period starts.
	opening = {}
	for r in frappe.db.sql(
		"""
		select mle.warehouse, mle.item_code,
			sum(mle.actual_qty) as qty,
			sum(if(mle.actual_qty >= 0, mle.fat, -mle.fat)) as kg_fat,
			sum(if(mle.actual_qty >= 0, mle.snf, -mle.snf)) as kg_snf
		from `tabMilk Ledger Entry` mle
		where {where} and mle.posting_date < %(from_date)s
		group by mle.warehouse, mle.item_code
		""".format(where=" and ".join(where)),
		values, as_dict=True,
	):
		opening[(r.warehouse, r.item_code)] = [flt(r.qty), flt(r.kg_fat), flt(r.kg_snf)]

	rows = frappe.db.sql(
		"""
		select
			concat_ws(" ", mle.posting_date, mle.posting_time) as date,
			mle.warehouse, mle.item_code, mle.voucher_type, mle.voucher_no,
			mle.actual_qty, mle.fat, mle.snf, mle.fat_per, mle.snf_per
		from `tabMilk Ledger Entry` mle
		where {where} and mle.posting_date between %(from_date)s and %(to_date)s
		order by mle.warehouse, mle.item_code, mle.posting_date, mle.posting_time, mle.creation
		""".format(where=" and ".join(where)),
		values, as_dict=True,
	)

	out, running = [], {}
	for r in rows:
		key = (r.warehouse, r.item_code)
		if key not in running:
			qty, kg_fat, kg_snf = opening.get(key, [0.0, 0.0, 0.0])
			running[key] = [qty, kg_fat, kg_snf]
			out.append({
				"date": None, "warehouse": r.warehouse, "item_code": r.item_code,
				"voucher_type": _("Opening"), "balance_qty": qty,
				"balance_fat": kg_fat, "balance_snf": kg_snf,
				"balance_fat_per": _percent(kg_fat, qty, r.item_code),
				"balance_snf_per": _percent(kg_snf, qty, r.item_code),
			})

		incoming = flt(r.actual_qty) >= 0
		kg_fat = flt(r.fat) if incoming else -flt(r.fat)
		kg_snf = flt(r.snf) if incoming else -flt(r.snf)

		bal = running[key]
		bal[0] += flt(r.actual_qty)
		bal[1] += kg_fat
		bal[2] += kg_snf

		out.append({
			"date": r.date,
			"warehouse": r.warehouse,
			"item_code": r.item_code,
			"voucher_type": r.voucher_type,
			"voucher_no": r.voucher_no,
			"qty_in": flt(r.actual_qty) if flt(r.actual_qty) > 0 else 0,
			"qty_out": -flt(r.actual_qty) if flt(r.actual_qty) < 0 else 0,
			"fat_per": flt(r.fat_per),
			"snf_per": flt(r.snf_per),
			"fat_in": kg_fat if kg_fat > 0 else 0,
			"fat_out": -kg_fat if kg_fat < 0 else 0,
			"snf_in": kg_snf if kg_snf > 0 else 0,
			"snf_out": -kg_snf if kg_snf < 0 else 0,
			"balance_qty": bal[0],
			"balance_fat": bal[1],
			"balance_snf": bal[2],
			"balance_fat_per": _percent(bal[1], bal[0], r.item_code),
			"balance_snf_per": _percent(bal[2], bal[0], r.item_code),
		})

	return out


def _percent(kg, qty, item_code):
	"""Percentages are by weight, so the quantity is converted to kg first."""
	qty_kg = flt(qty) * kg_per_stock_unit(item_code)
	return (kg / qty_kg * 100.0) if qty_kg else 0.0
