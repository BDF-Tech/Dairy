# Copyright (c) 2026, BDF and contributors
# For license information, please see license.txt

"""Figures behind the FAT/SNF dashboard.

Everything is read from the Milk Ledger, which carries kg FAT and kg SNF on every
movement -- positive in, negative out. Five things are shown:

* each silo: how much it holds, at what quality, and how that compares with the lab
* the period's milk and fat: bought, taken into the plant, used in production, sold, left
* the gap at each stage, which is where fat is actually lost
* the batches standardised, with the target against what the lab measured
* the documents behind each stage, so any figure can be opened and checked

Quantities are shown in kg and in litres. FAT and SNF are percentages by weight, so kg
is the basis the maths run on; litres are what the plant floor counts in. Both come from
the item's Weight Per Unit (milk is 1.03 kg per litre).
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate

from dairy.milk_standardisation.doctype.milk_standardisation.milk_standardisation import (
	kg_per_stock_unit,
	litres_per_stock_unit,
)
from dairy.milk_standardisation.silo import get_latest_test, get_quality, get_silo_warehouses

MANUFACTURE_PURPOSES = ("Manufacture", "Material Consumption for Manufacture", "Repack")
OUTWARD_TYPES = ("Sales Invoice", "Delivery Note")
TRAIL_LIMIT = 100


@frappe.whitelist()
def get_dashboard_data(from_date, to_date, company=None):
	if not (from_date and to_date):
		frappe.throw(_("From Date and To Date are required."))
	from_date, to_date = getdate(from_date), getdate(to_date)

	return {
		"silos": get_silos(company),
		"flow": get_flow(from_date, to_date, company),
		"stages": get_stage_gaps(from_date, to_date, company),
		"batches": get_batches(from_date, to_date, company),
		"trail": get_trail(from_date, to_date, company),
		"checks": get_checks(from_date, to_date, company),
		"as_on": frappe.utils.now(),
	}


def _factors(item_code):
	"""Kg and litres in one stock unit of the item, held for the request."""
	cache = getattr(frappe.local, "milk_unit_factors", None)
	if cache is None:
		cache = frappe.local.milk_unit_factors = {}
	if item_code not in cache:
		cache[item_code] = (kg_per_stock_unit(item_code), litres_per_stock_unit(item_code))
	return cache[item_code]


def get_silos(company=None):
	"""What each silo holds now, beside the lab's most recent test."""
	out = []
	for silo in get_silo_warehouses(company):
		items = [
			b.item_code
			for b in frappe.get_all("Bin", {"warehouse": silo.name, "actual_qty": [">", 0]}, ["item_code"])
			if frappe.db.get_value("Item", b.item_code, "maintain_fat_snf_clr")
		]
		if not items:
			out.append({
				"silo": silo.name, "item": None, "qty": 0, "qty_kg": 0, "qty_litre": 0,
				"capacity": flt(silo.capacity), "full_pct": 0, "fat": 0, "snf": 0,
				"kg_fat": 0, "kg_snf": 0,
				"tested_fat": None, "tested_snf": None, "tested_on": None, "fat_gap": None,
			})
			continue

		for item in items:
			q = get_quality(silo.name, item)
			test = get_latest_test(silo.name, item)
			row = {
				"silo": silo.name,
				"item": item,
				"qty": flt(q.qty),
				"qty_kg": flt(q.qty_kg),
				"qty_litre": flt(q.qty) * _factors(item)[1],
				"capacity": flt(silo.capacity),
				"full_pct": (flt(q.qty_kg) / flt(silo.capacity) * 100.0) if flt(silo.capacity) else 0,
				"fat": flt(q.fat),
				"snf": flt(q.snf),
				"kg_fat": flt(q.kg_fat),
				"kg_snf": flt(q.kg_snf),
				"tested_fat": flt(test.fat) if test else None,
				"tested_snf": flt(test.snf) if test else None,
				"tested_on": test.posting_datetime if test else None,
			}
			row["fat_gap"] = (row["tested_fat"] - row["fat"]) if test else None
			out.append(row)
	return out


def _not_cp_collection():
	"""SQL that keeps a CP inward's movement out of the plant's figures.

	Milk collected for a chilling centre is unloaded at that centre, not at the plant,
	but it travels in the same tanker warehouse. Counting it would show milk leaving the
	tanker that the plant never received. Returns nothing where Tanker Inward is not
	installed, since then there is no CP flow to exclude.
	"""
	if not frappe.db.exists("DocType", "Tanker Inward"):
		return None
	if not frappe.db.has_column("Stock Entry", "custom_tanker_inward"):
		return None
	return """not exists (
		select 1 from `tabStock Entry` cp_se
			join `tabTanker Inward` cp_ti on cp_ti.name = cp_se.custom_tanker_inward
		where cp_se.name = mle.voucher_no and cp_ti.cp_collection = 1
	)"""


def _ledger(from_date, to_date, company, conditions=None, values=None, joins=None,
	exclude_cp=False):
	"""What actually moved, per item, so quantities can be converted to kg and litres.

	A Milk Fat Reconciliation is a correction, not a movement -- it carries signed kg on
	a line with no quantity, so counting it here would show up as milk arriving (or
	leaving) that never did. Corrections belong in the closing balance only.
	"""
	where = [
		"ifnull(mle.is_cancelled, 0) = 0",
		"mle.voucher_type != 'Milk Fat Reconciliation'",
		"mle.posting_date between %(from_date)s and %(to_date)s",
	]
	vals = {"from_date": from_date, "to_date": to_date}
	if company:
		where.append("mle.company = %(company)s")
		vals["company"] = company
	if conditions:
		where += conditions
	if exclude_cp and _not_cp_collection():
		where.append(_not_cp_collection())
	if values:
		vals.update(values)

	rows = frappe.db.sql(
		"""
		select
			mle.item_code,
			sum(if(mle.actual_qty >= 0, mle.fat, 0)) as fat_in,
			sum(if(mle.actual_qty < 0, mle.fat, 0)) as fat_out,
			sum(if(mle.actual_qty >= 0, mle.snf, 0)) as snf_in,
			sum(if(mle.actual_qty < 0, mle.snf, 0)) as snf_out,
			sum(if(mle.actual_qty >= 0, mle.actual_qty, 0)) as qty_in,
			sum(if(mle.actual_qty < 0, -mle.actual_qty, 0)) as qty_out
		from `tabMilk Ledger Entry` mle
			{joins}
		where {where}
		group by mle.item_code
		""".format(joins=" ".join(joins or []), where=" and ".join(where)),
		vals, as_dict=True,
	)
	return _fold(rows)


def _fold(rows):
	"""Add per-item totals up into one set of kg, litre, FAT and SNF figures."""
	t = frappe._dict(fat_in=0.0, fat_out=0.0, snf_in=0.0, snf_out=0.0,
		kg_in=0.0, kg_out=0.0, litre_in=0.0, litre_out=0.0, qty_in=0.0, qty_out=0.0)
	for r in rows:
		kg, litre = _factors(r.item_code)
		# The ledger keeps kg FAT positive on both sides; the quantity's sign says which
		# way it went, which is what the query has already split on.
		t.fat_in += flt(r.fat_in)
		t.fat_out += flt(r.fat_out)
		t.snf_in += flt(r.snf_in)
		t.snf_out += flt(r.snf_out)
		t.qty_in += flt(r.qty_in)
		t.qty_out += flt(r.qty_out)
		t.kg_in += flt(r.qty_in) * kg
		t.kg_out += flt(r.qty_out) * kg
		t.litre_in += flt(r.qty_in) * litre
		t.litre_out += flt(r.qty_out) * litre
	return t


def _tile(label, sub, kg, litre, fat, snf):
	return {"label": label, "sub": sub, "kg": flt(kg), "litre": flt(litre),
		"fat": flt(fat), "snf": flt(snf),
		"fat_pct": (flt(fat) / flt(kg) * 100.0) if flt(kg) else 0,
		"snf_pct": (flt(snf) / flt(kg) * 100.0) if flt(kg) else 0}


def get_flow(from_date, to_date, company=None):
	"""Milk and fat bought, moved into the plant, used, sold, and still held."""
	silos = [s.name for s in get_silo_warehouses(company)]

	bought = _ledger(from_date, to_date, company, ["mle.voucher_type = 'Purchase Receipt'"])
	sold = _ledger(from_date, to_date, company,
		["mle.voucher_type in %(outward)s"], {"outward": OUTWARD_TYPES})

	into_plant = _fold([])
	if silos:
		into_plant = _ledger(from_date, to_date, company,
			["mle.warehouse in %(silos)s"], {"silos": silos})

	made = _ledger(from_date, to_date, company,
		["mle.voucher_type = 'Stock Entry'", "se.purpose in %(purposes)s"],
		{"purposes": MANUFACTURE_PURPOSES},
		joins=["join `tabStock Entry` se on se.name = mle.voucher_no"])

	held = _held(to_date, company)

	return {
		"tiles": [
			_tile(_("Bought"), _("from farmers"), bought.kg_in, bought.litre_in, bought.fat_in, bought.snf_in),
			_tile(_("Into silos"), _("reached the plant"), into_plant.kg_in, into_plant.litre_in,
				into_plant.fat_in, into_plant.snf_in),
			_tile(_("Used in production"), _("consumed in batches"), made.kg_out, made.litre_out,
				made.fat_out, made.snf_out),
			_tile(_("In finished goods"), _("came out as product"), made.kg_in, made.litre_in,
				made.fat_in, made.snf_in),
			_tile(_("Sold"), _("left as sales"), sold.kg_out, sold.litre_out, sold.fat_out, sold.snf_out),
			# Quantity comes from stock on hand, not from the ledger's own running total:
			# until every warehouse has been reconciled the ledger's quantity is still
			# carrying the old mess, and the data check below reports the difference.
			_tile(_("Held now"), _("stock on hand"), held.kg, held.litre, held.fat, held.snf),
		],
		# kept flat as well, so the stage table and anything else can reuse them
		"bought_fat": flt(bought.fat_in),
		"into_silo_fat": flt(into_plant.fat_in),
		"used_fat": flt(made.fat_out),
		"produced_fat": flt(made.fat_in),
		"sold_fat": flt(sold.fat_out),
		"closing_fat": flt(held.fat),
	}


def _ledger_balance(to_date, company=None):
	"""The ledger's own balance up to a date, per warehouse and item.

	Corrections count here, because the whole point of a reconciliation is to set the
	balance.
	"""
	where = ["ifnull(mle.is_cancelled, 0) = 0", "mle.posting_date <= %(to_date)s"]
	vals = {"to_date": to_date}
	if company:
		where.append("mle.company = %(company)s")
		vals["company"] = company

	return frappe.db.sql(
		"""
		select mle.warehouse, mle.item_code,
			sum(mle.actual_qty) as qty,
			sum(if(mle.actual_qty >= 0, mle.fat, -mle.fat)) as kg_fat,
			sum(if(mle.actual_qty >= 0, mle.snf, -mle.snf)) as kg_snf
		from `tabMilk Ledger Entry` mle
		where {where}
		group by mle.warehouse, mle.item_code
		""".format(where=" and ".join(where)),
		vals, as_dict=True,
	)


def _stock_on_hand(company=None, by=None):
	"""What the warehouses actually hold now, from Bin, in kg and litres."""
	rows = frappe.db.sql(
		"""
		select b.item_code, {warehouse} sum(b.actual_qty) as qty
		from `tabBin` b
			join `tabItem` i on i.name = b.item_code
			join `tabWarehouse` w on w.name = b.warehouse
		where i.maintain_fat_snf_clr = 1 {company}
		group by b.item_code {group}
		""".format(
			warehouse="b.warehouse," if by else "",
			company="and w.company = %(company)s" if company else "",
			group=", b.warehouse" if by else "",
		),
		{"company": company}, as_dict=True,
	)
	if by:
		return {(r.warehouse, r.item_code): flt(r.qty) for r in rows}

	t = frappe._dict(qty=0.0, kg=0.0, litre=0.0)
	for r in rows:
		kg, litre = _factors(r.item_code)
		t.qty += flt(r.qty)
		t.kg += flt(r.qty) * kg
		t.litre += flt(r.qty) * litre
	return t


def get_checks(from_date, to_date, company=None):
	"""Two things that decide whether the figures above can be trusted.

	The first is milk that moved without any FAT recorded on it -- the reason the fat
	book has holes. The second is the ledger's own quantity against stock on hand, which
	only a reconciliation can close.
	"""
	where = ["ifnull(mle.is_cancelled, 0) = 0", "mle.voucher_type != 'Milk Fat Reconciliation'",
		"mle.actual_qty != 0", "mle.posting_date between %(from_date)s and %(to_date)s"]
	vals = {"from_date": from_date, "to_date": to_date}
	if company:
		where.append("mle.company = %(company)s")
		vals["company"] = company

	rows = frappe.db.sql(
		"""
		select mle.voucher_type, mle.item_code,
			sum(if(ifnull(mle.fat, 0) = 0, 1, 0)) as blank_rows,
			count(*) as all_rows,
			sum(if(ifnull(mle.fat, 0) = 0, abs(mle.actual_qty), 0)) as blank_qty,
			sum(abs(mle.actual_qty)) as all_qty
		from `tabMilk Ledger Entry` mle
		where {where}
		group by mle.voucher_type, mle.item_code
		""".format(where=" and ".join(where)),
		vals, as_dict=True,
	)

	untracked, totals = {}, frappe._dict(blank_rows=0, all_rows=0, blank_kg=0.0, all_kg=0.0)
	for r in rows:
		kg, litre = _factors(r.item_code)
		u = untracked.setdefault(r.voucher_type, {"voucher_type": r.voucher_type,
			"blank_rows": 0, "all_rows": 0, "blank_kg": 0.0, "blank_litre": 0.0, "all_kg": 0.0})
		u["blank_rows"] += int(r.blank_rows)
		u["all_rows"] += int(r.all_rows)
		u["blank_kg"] += flt(r.blank_qty) * kg
		u["blank_litre"] += flt(r.blank_qty) * litre
		u["all_kg"] += flt(r.all_qty) * kg
		totals.blank_rows += int(r.blank_rows)
		totals.all_rows += int(r.all_rows)
		totals.blank_kg += flt(r.blank_qty) * kg
		totals.all_kg += flt(r.all_qty) * kg

	for u in untracked.values():
		u["pct"] = (u["blank_kg"] / u["all_kg"] * 100.0) if u["all_kg"] else 0

	held = _held(to_date, company)

	return {
		"untracked": sorted(untracked.values(), key=lambda x: -x["blank_kg"]),
		"untracked_rows": totals.blank_rows,
		"untracked_of_rows": totals.all_rows,
		"untracked_kg": totals.blank_kg,
		"untracked_pct": (totals.blank_kg / totals.all_kg * 100.0) if totals.all_kg else 0,
		"ledger_off_warehouses": held.off_rows,
		"ledger_off_kg": held.off_kg,
		"stranded_fat": held.stranded_fat,
		"stranded_rows": held.stranded_rows,
	}


def get_stage_gaps(from_date, to_date, company=None):
	"""Fat in against fat out at each stage; the difference is the loss there."""
	silos = [s.name for s in get_silo_warehouses(company)]
	stages = []

	collection = _ledger(from_date, to_date, company, ["mle.warehouse like 'DCS-%%'"], exclude_cp=True)
	stages.append({"stage": _("Collection centres"), "data": collection})

	tanker = _ledger(from_date, to_date, company, ["mle.warehouse like '%%Tanker%%'"], exclude_cp=True)
	stages.append({"stage": _("Tanker"), "data": tanker})

	if silos:
		silo = _ledger(from_date, to_date, company, ["mle.warehouse in %(silos)s"], {"silos": silos},
			exclude_cp=True)
		stages.append({"stage": _("Silos"), "data": silo})

	out = []
	for s in stages:
		d = s.pop("data")
		s.update({
			"kg_in": flt(d.kg_in), "kg_out": flt(d.kg_out),
			"litre_in": flt(d.litre_in), "litre_out": flt(d.litre_out),
			"fat_in": flt(d.fat_in), "fat_out": flt(d.fat_out),
		})
		s["gap"] = s["fat_in"] - s["fat_out"]
		s["gap_pct"] = (s["gap"] / s["fat_in"] * 100.0) if s["fat_in"] else 0
		out.append(s)
	return out


def get_batches(from_date, to_date, company=None):
	"""Batches standardised in the period: what was aimed at, and what the lab found."""
	filters = {"docstatus": 1, "posting_datetime": ["between", [from_date, f"{to_date} 23:59:59"]]}
	if company:
		filters["company"] = company

	rows = frappe.get_all(
		"Milk Standardisation", filters=filters,
		fields=["name", "posting_datetime", "finished_item", "total_qty", "output_qty", "target_fat",
			"target_snf", "achieved_fat", "achieved_snf", "tested_fat", "tested_snf", "in_spec",
			"lab_in_spec", "work_order", "stock_entry"],
		order_by="posting_datetime desc", limit=TRAIL_LIMIT,
	)
	for r in rows:
		r["fat_gap"] = flt(r.get("tested_fat")) - flt(r.get("achieved_fat"))
		r["kg_fat"] = flt(r.get("total_qty")) * flt(r.get("tested_fat") or r.get("achieved_fat")) / 100.0
		r["qty_litre"] = flt(r.get("total_qty")) * _factors(r.get("finished_item"))[1]
	return rows


# ---------------------------------------------------------------- the stage trail

def get_trail(from_date, to_date, company=None):
	"""The documents behind each stage, so every figure on the page can be opened."""
	return {
		"inward": _trail_inward(from_date, to_date, company),
		"quality": _trail_quality(from_date, to_date, company),
		"standardisation": get_batches(from_date, to_date, company),
		"manufacture": _trail_vouchers(from_date, to_date, company,
			["mle.voucher_type = 'Stock Entry'", "se.purpose in %(purposes)s"],
			{"purposes": MANUFACTURE_PURPOSES},
			joins=["join `tabStock Entry` se on se.name = mle.voucher_no"],
			doctype="Stock Entry"),
		"outward": _trail_vouchers(from_date, to_date, company,
			["mle.voucher_type in %(outward)s"], {"outward": OUTWARD_TYPES}),
		"left": _trail_left(to_date, company),
	}


def _trail_inward(from_date, to_date, company=None):
	"""Tanker Inwards: what the tanker carried, and which silo it went into.

	Tanker Inward belongs to the bdf_dairy app, so the stage is simply left empty where
	that app is not installed.
	"""
	if not frappe.db.exists("DocType", "Tanker Inward"):
		return []

	# A CP inward ends at its own chilling centre, not at the plant, so it is no part of
	# the fat that reaches a silo. Tanker Inward carries no company field; its silo does,
	# which the other stages already filter on.
	filters = {"docstatus": 1, "cp_collection": 0,
		"tanker_inward_date": ["between", [from_date, to_date]]}
	if company:
		silos = [w.name for w in frappe.get_all("Warehouse", {"company": company}, ["name"])]
		filters["plant_warehouse"] = ["in", silos or [""]]

	rows = frappe.get_all(
		"Tanker Inward", filters=filters,
		fields=["name", "tanker_inward_date", "dcs", "vehicle_number", "milk_type", "plant_warehouse",
			"total_qty_in_kg1", "total_qty_in_litre1", "fat1", "snf1", "kg_fat1", "kg_snf1",
			"total_qty_in_kg", "total_qty_in_liter", "fat", "snf", "kg_fat", "kg_snf"],
		order_by="tanker_inward_date desc, creation desc", limit=TRAIL_LIMIT,
	)

	out = []
	for r in rows:
		# The plant-side totals are filled in by the form; fall back to the collection
		# side for an inward that was not keyed in through the browser.
		plant_side = flt(r.total_qty_in_kg1) or flt(r.kg_fat1)
		kg = flt(r.total_qty_in_kg1) if plant_side else flt(r.total_qty_in_kg)
		litre = flt(r.total_qty_in_litre1) if plant_side else flt(r.total_qty_in_liter)
		kg_fat = flt(r.kg_fat1) if plant_side else flt(r.kg_fat)
		kg_snf = flt(r.kg_snf1) if plant_side else flt(r.kg_snf)
		fat, snf = (flt(r.fat1), flt(r.snf1)) if plant_side else (flt(r.fat), flt(r.snf))
		out.append({
			"doc": r.name, "doctype": "Tanker Inward", "date": r.tanker_inward_date,
			"what": r.dcs, "where": r.plant_warehouse,
			"note": " ".join(x for x in [r.vehicle_number, r.milk_type] if x),
			"kg": kg, "litre": litre, "kg_fat": kg_fat, "kg_snf": kg_snf,
			"fat": fat or ((kg_fat / kg * 100.0) if kg else 0),
			"snf": snf or ((kg_snf / kg * 100.0) if kg else 0),
		})
	return out


def _trail_quality(from_date, to_date, company=None):
	"""Silo Quality Tests: the lab reading beside the book figure it was checked against."""
	if not frappe.db.exists("DocType", "Silo Quality Test"):
		return []

	rows = frappe.get_all(
		"Silo Quality Test",
		filters={"docstatus": 1, "posting_datetime": ["between", [from_date, f"{to_date} 23:59:59"]]},
		fields=["name", "posting_datetime", "silo", "item", "shift", "tested_by", "tested_qty",
			"fat", "snf", "clr", "book_qty", "book_fat", "book_snf", "fat_difference",
			"snf_difference", "qty_difference"],
		order_by="posting_datetime desc", limit=TRAIL_LIMIT,
	)
	for r in rows:
		r["qty_litre"] = flt(r.get("tested_qty")) * _factors(r.get("item"))[1]
		r["kg_fat"] = flt(r.get("tested_qty")) * _factors(r.get("item"))[0] * flt(r.get("fat")) / 100.0
	return rows


def _trail_vouchers(from_date, to_date, company=None, conditions=None, values=None,
	joins=None, doctype=None):
	"""One row per voucher: what went in, what came out, and the fat on each side."""
	where = [
		"ifnull(mle.is_cancelled, 0) = 0",
		"mle.posting_date between %(from_date)s and %(to_date)s",
	]
	vals = {"from_date": from_date, "to_date": to_date}
	if company:
		where.append("mle.company = %(company)s")
		vals["company"] = company
	if conditions:
		where += conditions
	if values:
		vals.update(values)

	rows = frappe.db.sql(
		"""
		select mle.voucher_type, mle.voucher_no, mle.item_code, max(mle.posting_date) as posting_date,
			group_concat(distinct mle.warehouse) as warehouses,
			sum(if(mle.actual_qty >= 0, mle.actual_qty, 0)) as qty_in,
			sum(if(mle.actual_qty < 0, -mle.actual_qty, 0)) as qty_out,
			sum(if(mle.actual_qty >= 0, mle.fat, 0)) as fat_in,
			sum(if(mle.actual_qty < 0, mle.fat, 0)) as fat_out,
			sum(if(mle.actual_qty >= 0, mle.snf, 0)) as snf_in,
			sum(if(mle.actual_qty < 0, mle.snf, 0)) as snf_out
		from `tabMilk Ledger Entry` mle
			{joins}
		where {where}
		group by mle.voucher_type, mle.voucher_no, mle.item_code
		order by max(mle.posting_date) desc, mle.voucher_no desc
		limit 1000
		""".format(joins=" ".join(joins or []), where=" and ".join(where)),
		vals, as_dict=True,
	)

	vouchers = {}
	order = []
	for r in rows:
		key = r.voucher_no
		if key not in vouchers:
			vouchers[key] = {
				"doc": r.voucher_no, "doctype": doctype or r.voucher_type, "date": r.posting_date,
				"what": [], "where": set(),
				"kg": 0.0, "litre": 0.0, "kg_fat": 0.0, "kg_snf": 0.0,
				"out_kg": 0.0, "out_litre": 0.0, "out_kg_fat": 0.0,
			}
			order.append(key)
		v = vouchers[key]
		kg, litre = _factors(r.item_code)
		v["what"].append(r.item_code)
		v["where"].update((r.warehouses or "").split(","))
		v["kg"] += flt(r.qty_in) * kg
		v["litre"] += flt(r.qty_in) * litre
		v["kg_fat"] += flt(r.fat_in)
		v["kg_snf"] += flt(r.snf_in)
		v["out_kg"] += flt(r.qty_out) * kg
		v["out_litre"] += flt(r.qty_out) * litre
		v["out_kg_fat"] += flt(r.fat_out)

	out = []
	for key in order[:TRAIL_LIMIT]:
		v = vouchers[key]
		v["what"] = ", ".join(sorted(set(v["what"])))
		v["where"] = ", ".join(sorted(x for x in v["where"] if x))
		# A sale or a consumption only takes stock out; show that as the row's quantity.
		if not v["kg"] and v["out_kg"]:
			v.update({"kg": v["out_kg"], "litre": v["out_litre"], "kg_fat": v["out_kg_fat"]})
			v["direction"] = "out"
		else:
			v["direction"] = "in"
		v["fat"] = (v["kg_fat"] / v["kg"] * 100.0) if v["kg"] else 0
		v["snf"] = (v["kg_snf"] / v["kg"] * 100.0) if v["kg"] else 0
		out.append(v)
	return out


def _held_rows(to_date, company=None):
	"""What is still held, warehouse by warehouse: real stock beside the ledger.

	Quantity and quality are worked out on the stock figure, since that is what the
	warehouse holds; the ledger's own quantity sits next to it so any warehouse still
	waiting for a reconciliation is obvious.
	"""
	stock = _stock_on_hand(company, by=True)
	ledger = {(r.warehouse, r.item_code): r for r in _ledger_balance(to_date, company)}

	out = []
	for key in set(stock) | set(ledger):
		warehouse, item = key
		kg, litre = _factors(item)
		row = ledger.get(key)
		qty = flt(stock.get(key))
		qty_kg = qty * kg
		kg_fat = flt(row.kg_fat) if row else 0.0
		kg_snf = flt(row.kg_snf) if row else 0.0
		if not (round(qty, 3) or round(kg_fat, 3)):
			continue
		out.append({
			"doc": warehouse, "doctype": "Warehouse", "date": None,
			"what": item, "where": warehouse, "note": "",
			"qty": qty, "kg": qty_kg, "litre": qty * litre,
			"ledger_qty": flt(row.qty) if row else 0.0,
			"qty_diff": (flt(row.qty) if row else 0.0) - qty,
			"kg_fat": kg_fat, "kg_snf": kg_snf,
			"fat": (kg_fat / qty_kg * 100.0) if qty_kg else 0,
			"snf": (kg_snf / qty_kg * 100.0) if qty_kg else 0,
			# Fat booked against a warehouse that holds nothing is left over from the
			# untracked years; it is reported on its own rather than mixed into the total.
			"stranded": not round(qty_kg, 3),
		})
	out.sort(key=lambda x: -abs(x["kg_fat"]))
	return out


def _held(to_date, company=None):
	"""The closing position: stock on hand, with the fat that sits on milk that exists."""
	t = frappe._dict(kg=0.0, litre=0.0, fat=0.0, snf=0.0,
		stranded_fat=0.0, stranded_rows=0, off_rows=0, off_kg=0.0)
	for r in _held_rows(to_date, company):
		if r["stranded"]:
			t.stranded_fat += r["kg_fat"]
			t.stranded_rows += 1
		else:
			t.kg += r["kg"]
			t.litre += r["litre"]
			t.fat += r["kg_fat"]
			t.snf += r["kg_snf"]
		if abs(r["qty_diff"]) > 1:
			t.off_rows += 1
			t.off_kg += r["qty_diff"]
	return t


def _trail_left(to_date, company=None):
	return _held_rows(to_date, company)[:TRAIL_LIMIT]
