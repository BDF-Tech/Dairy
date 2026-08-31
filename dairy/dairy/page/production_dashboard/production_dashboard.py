import frappe
from frappe.utils import flt

# Raw milk intake items - the denominator for the production yield ratio
# (produced qty / raw milk consumed, e.g. 126.6 Kg paneer base / 850 L RCM).
# Only TOP-OF-CHAIN raw milk goes here, never the milk bases (SF003/SF004...),
# otherwise the same physical milk would be counted twice down the chain.
# Edit this list if new raw-milk item codes are introduced.
MILK_ITEMS = ("SF001", "SF024")

# ---------------------------------------------------------------------------
# Production Dashboard
#
# Source of truth is the Stock Entry ledger:
#   * "Manufacture" entries  -> what was produced (finished good + inputs,
#                               from_warehouse -> to_warehouse, fg_completed_qty)
#   * "Handling Loss" entries -> loss booked against a run, linked back through
#                               the custom_manufacture_ field.
#
# The whole payload is assembled in exactly THREE queries regardless of how
# many production runs match the filter, so there is no per-card round trip.
# ---------------------------------------------------------------------------


def _run_filter(
	from_date, to_date, company=None, item_group=None, item_code=None, stock_entry=None, item_codes=None
):
	"""Build the shared JOIN / WHERE / values for the manufacture-run selection.

	Kept separate from the queries themselves so the summary can aggregate over
	the *whole* filtered set while the cards are still capped by `limit` - the
	two must never disagree about what "matching" means.
	"""
	conditions = [
		"se.docstatus = 1",
		"se.stock_entry_type = 'Manufacture'",
		"se.posting_date BETWEEN %(from_date)s AND %(to_date)s",
	]
	values = {"from_date": from_date, "to_date": to_date}
	joins = ["LEFT JOIN `tabItem` it ON it.name = se.item"]

	if company:
		conditions.append("se.company = %(company)s")
		values["company"] = company

	if stock_entry:
		conditions.append("se.name = %(stock_entry)s")
		values["stock_entry"] = stock_entry

	if item_code:
		conditions.append("se.item = %(item_code)s")
		values["item_code"] = item_code

	if item_codes:
		# Used by the "Group By: Item" path to pull every run belonging to the
		# already-chosen top-N items, so each item card totals the whole period.
		conditions.append("se.item IN %(item_codes)s")
		values["item_codes"] = tuple(item_codes)

	if item_group:
		# Scope on the finished good's item group, including every descendant
		# group. Item Group is a nested set, so a node's subtree is exactly the
		# groups whose lft/rgt fall inside the selected group's lft/rgt range.
		node = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=True)
		if node:
			joins.append("JOIN `tabItem Group` ig ON ig.name = it.item_group")
			conditions.append("ig.lft >= %(lft)s AND ig.rgt <= %(rgt)s")
			values["lft"] = node.lft
			values["rgt"] = node.rgt

	return " ".join(joins), " AND ".join(conditions), values


def _manufacture_runs(
	from_date, to_date, company=None, item_group=None, item_code=None, stock_entry=None,
	limit=None, item_codes=None
):
	"""Query A - manufacture parents in range (optionally scoped by group/item).

	The Item master is always joined so weight_per_unit / weight_uom come back
	with the run itself - that is what lets a run of 200 Nos of a 0.200 Kg item
	be reported as 40 Kg without a second query.

	`limit` caps how many cards are rendered; it must NOT be used for totals.
	"""
	join, where, values = _run_filter(
		from_date, to_date, company, item_group, item_code, stock_entry, item_codes
	)
	limit_clause = f"LIMIT {int(limit)}" if limit else ""

	return frappe.db.sql(
		f"""
		SELECT
			se.name,
			se.posting_date,
			se.custom_manufacturing_item_name,
			se.item              AS fg_item_code,
			se.fg_completed_qty,
			se.from_warehouse,
			se.to_warehouse,
			se.work_order,
			it.weight_per_unit,
			it.weight_uom
		FROM `tabStock Entry` se
		{join}
		WHERE {where}
		ORDER BY se.posting_date DESC, se.creation DESC
		{limit_clause}
		""",
		values,
		as_dict=True,
	)


def _totals_rows(from_date, to_date, company=None, item_group=None, item_code=None, stock_entry=None):
	"""One lightweight row per matching run, ignoring `limit`.

	This is what the summary banner and the chart are built from, so those
	numbers describe the whole filtered period rather than just the page of
	cards being displayed. Only the few columns the totals need are selected,
	and the finished line is reached through a single LEFT JOIN (first finished
	row by idx - the same one the card renderer picks), so this stays cheap even
	across tens of thousands of runs.
	"""
	join, where, values = _run_filter(from_date, to_date, company, item_group, item_code, stock_entry)

	return frappe.db.sql(
		f"""
		SELECT
			se.name,
			se.item                            AS fg_item_code,
			se.custom_manufacturing_item_name,
			CASE
				WHEN IFNULL(se.fg_completed_qty, 0) <> 0 THEN se.fg_completed_qty
				ELSE IFNULL((
					SELECT SUM(f2.qty)
					FROM `tabStock Entry Detail` f2
					WHERE f2.parent = se.name AND f2.is_finished_item = 1
				), 0)
			END                                AS produced_qty,
			fin.uom                            AS uom,
			fin.item_code                      AS fin_item_code,
			fin.item_name                      AS fin_item_name,
			fin.item_group                     AS fin_item_group,
			it.item_group                      AS fg_item_group,
			it.weight_per_unit,
			it.weight_uom
		FROM `tabStock Entry` se
		{join}
		LEFT JOIN `tabStock Entry Detail` fin ON fin.name = (
			SELECT f3.name
			FROM `tabStock Entry Detail` f3
			WHERE f3.parent = se.name AND f3.is_finished_item = 1
			ORDER BY f3.idx
			LIMIT 1
		)
		WHERE {where}
		""",
		values,
		as_dict=True,
	)


def _loss_totals(from_date, to_date, company=None, item_group=None, item_code=None, stock_entry=None):
	"""Handling loss per run across the whole filtered set (again ignoring limit).

	The matching runs are re-selected as a subquery rather than passed in as a
	name list, so this stays a single round trip no matter how many runs match.
	"""
	join, where, values = _run_filter(from_date, to_date, company, item_group, item_code, stock_entry)

	rows = frappe.db.sql(
		f"""
		SELECT
			hl.custom_manufacture_ AS manufacture,
			SUM(hld.qty)           AS qty
		FROM `tabStock Entry` hl
		JOIN `tabStock Entry Detail` hld ON hld.parent = hl.name
		WHERE hl.docstatus = 1
		  AND hl.stock_entry_type = 'Handling Loss'
		  AND hl.custom_manufacture_ IN (
			SELECT se.name FROM `tabStock Entry` se {join} WHERE {where}
		  )
		GROUP BY hl.custom_manufacture_
		""",
		values,
		as_dict=True,
	)
	return {r.manufacture: flt(r.qty) for r in rows}


def _milk_total(from_date, to_date, company=None, item_group=None, item_code=None, stock_entry=None):
	"""Total raw milk (MILK_ITEMS) consumed as input across the whole filtered set.

	One aggregate round trip, same subquery-of-matching-runs shape as the loss
	total, so the summary's "Total Raw Milk" covers the full period regardless
	of the card `limit`. Returns (qty, uom).
	"""
	join, where, values = _run_filter(from_date, to_date, company, item_group, item_code, stock_entry)
	values["milk_items"] = tuple(MILK_ITEMS)

	row = frappe.db.sql(
		f"""
		SELECT SUM(sed.qty) AS qty, MAX(sed.uom) AS uom
		FROM `tabStock Entry Detail` sed
		WHERE sed.item_code IN %(milk_items)s
		  AND sed.is_finished_item = 0
		  AND sed.is_scrap_item = 0
		  AND sed.parent IN (
			SELECT se.name FROM `tabStock Entry` se {join} WHERE {where}
		  )
		""",
		values,
		as_dict=True,
	)
	return (flt(row[0].qty), row[0].uom) if row and row[0].qty else (0.0, None)


def _lines_for(run_names):
	"""Query B - every child row for the matched runs, in one shot."""
	placeholders = ", ".join(["%s"] * len(run_names))
	return frappe.db.sql(
		f"""
		SELECT
			sed.parent,
			sed.item_code,
			sed.item_name,
			sed.item_group,
			sed.qty,
			sed.uom,
			sed.s_warehouse,
			sed.is_finished_item,
			sed.is_scrap_item
		FROM `tabStock Entry Detail` sed
		WHERE sed.parent IN ({placeholders})
		ORDER BY sed.parent, sed.idx
		""",
		tuple(run_names),
		as_dict=True,
	)


def _handling_loss_for(run_names):
	"""Query C - handling loss rows linked back to the matched runs."""
	placeholders = ", ".join(["%s"] * len(run_names))
	return frappe.db.sql(
		f"""
		SELECT
			hl.custom_manufacture_ AS manufacture,
			hld.item_code,
			hld.item_name,
			hld.qty,
			hld.uom
		FROM `tabStock Entry` hl
		JOIN `tabStock Entry Detail` hld ON hld.parent = hl.name
		WHERE hl.docstatus = 1
		  AND hl.stock_entry_type = 'Handling Loss'
		  AND hl.custom_manufacture_ IN ({placeholders})
		ORDER BY hld.idx
		""",
		tuple(run_names),
		as_dict=True,
	)


@frappe.whitelist()
def get_dashboard_data(from_date, to_date, company=None, item_group=None, item_code=None, stock_entry=None, limit=50, group_by="Stock Entry"):
	"""Master endpoint: returns summary, chart series and cards.

	group_by = "Stock Entry" -> one card per production run (default)
	group_by = "Item"        -> runs of the same finished item clubbed into one
	"""
	if not from_date or not to_date:
		frappe.throw("From Date and To Date are required.")

	limit = None if str(limit).lower() in ("all", "0", "") else int(limit)

	# Totals and chart always describe the FULL filtered period. `limit` only
	# caps how many cards come back, so changing "Show" must never change the
	# headline numbers.
	total_rows = _totals_rows(from_date, to_date, company, item_group, item_code, stock_entry)
	if not total_rows:
		return {
			"summary": _empty_summary(),
			"chart": {"labels": [], "produced": [], "loss": []},
			"item_summary": [],
			"cards": [],
			"unit": "items" if group_by == "Item" else "production runs",
			"total_runs": 0,
			"shown_runs": 0,
			"truncated": False,
		}

	loss_map = _loss_totals(from_date, to_date, company, item_group, item_code, stock_entry)
	summary = _summary_from_rows(total_rows, loss_map)
	chart = _chart_from_rows(total_rows, loss_map)
	item_summary = _item_summary(total_rows, loss_map)

	# Period-wide raw milk consumed + avg milk per run, added to the summary bar.
	milk_qty, milk_uom = _milk_total(from_date, to_date, company, item_group, item_code, stock_entry)
	runs_ct = summary["production_runs"]
	summary["total_milk_used"] = round(milk_qty, 2)
	summary["milk_uom"] = milk_uom
	summary["avg_milk_per_run"] = round(milk_qty / runs_ct, 2) if runs_ct else 0

	# What `limit` means depends on the grouping:
	#   Stock Entry -> newest N runs; each card is one run, so a capped page of
	#                  runs is still an honest card.
	#   Item        -> top N items by produced qty; the limit must be applied to
	#                  ITEMS and every run of a chosen item must be loaded,
	#                  otherwise a card would total only the runs that happened
	#                  to fall inside the newest N and understate the item.
	top_codes = None
	if group_by == "Item":
		by_item = {}
		for r in total_rows:
			code = r.fg_item_code or r.fin_item_code
			if code:
				by_item[code] = by_item.get(code, 0) + flt(r.produced_qty)
		ranked = sorted(by_item.items(), key=lambda kv: kv[1], reverse=True)
		total_items = len(ranked)
		if limit and total_items > limit:
			top_codes = [c for c, _ in ranked[:limit]]

	runs = _manufacture_runs(
		from_date, to_date, company, item_group, item_code, stock_entry,
		limit=None if group_by == "Item" else limit,
		item_codes=top_codes,
	)

	run_names = [r.name for r in runs]

	finished_by_run, inputs_by_run = {}, {}
	for row in _lines_for(run_names):
		if row.is_finished_item:
			finished_by_run.setdefault(row.parent, []).append(row)
		elif not row.is_scrap_item:
			inputs_by_run.setdefault(row.parent, []).append(row)

	loss_by_run = {}
	for row in _handling_loss_for(run_names):
		bucket = loss_by_run.setdefault(row.manufacture, {"qty": 0.0, "items": []})
		bucket["qty"] += flt(row.qty)
		bucket["items"].append(
			{"item_code": row.item_code, "item_name": row.item_name, "qty": flt(row.qty), "uom": row.uom}
		)

	cards = []
	for run in runs:
		finished = finished_by_run.get(run.name, [])
		fg_group = finished[0].item_group if finished else None
		fg_name = run.custom_manufacturing_item_name or (finished[0].item_name if finished else run.fg_item_code)
		fg_code = run.fg_item_code or (finished[0].item_code if finished else None)
		produced_qty = flt(run.fg_completed_qty) or sum(flt(f.qty) for f in finished)
		uom = finished[0].uom if finished else None
		loss = loss_by_run.get(run.name, {"qty": 0.0, "items": []})

		# Weight = produced qty x weight_per_unit, reported in the item's weight_uom.
		wpu = flt(run.weight_per_unit)
		weight_uom = run.weight_uom
		produced_weight = round(produced_qty * wpu, 3) if wpu > 0 and weight_uom else None

		# Raw milk consumed by this run + the yield ratio (produced / milk).
		# Only runs that actually drew raw milk get a yield; a run built from a
		# milk base has no raw milk of its own and is left with yield = None.
		run_inputs = inputs_by_run.get(run.name, [])
		milk_used = sum(flt(r.qty) for r in run_inputs if r.item_code in MILK_ITEMS)
		milk_uom = next((r.uom for r in run_inputs if r.item_code in MILK_ITEMS), None)
		milk_yield = round(produced_qty / milk_used, 4) if milk_used > 0 and produced_qty else None

		cards.append(
			{
				"stock_entry": run.name,
				"posting_date": str(run.posting_date),
				"work_order": run.work_order,
				"fg_item_code": fg_code,
				"fg_item_name": fg_name,
				"fg_item_group": fg_group,
				"produced_qty": produced_qty,
				"uom": uom,
				"produced_weight": produced_weight,
				"weight_uom": weight_uom,
				"weight_per_unit": wpu or None,
				"milk_used": milk_used or None,
				"milk_uom": milk_uom,
				"milk_yield": milk_yield,
				"source_warehouse": run.from_warehouse,
				"target_warehouse": run.to_warehouse,
				"inputs": [
					{
						"item_code": r.item_code,
						"item_name": r.item_name,
						"item_group": r.item_group,
						"qty": flt(r.qty),
						"uom": r.uom,
						"source_warehouse": r.s_warehouse,
					}
					for r in inputs_by_run.get(run.name, [])
				],
				"handling_loss_qty": flt(loss["qty"]),
				"handling_loss_items": loss["items"],
			}
		)

	shown_runs = len(cards)
	if group_by == "Item":
		cards = _aggregate_by_item(cards)

	# Report the cap in the same unit the cards are in, so the notice never
	# describes runs while the user is looking at item cards.
	if group_by == "Item":
		unit, shown, total = "items", len(cards), total_items
	else:
		unit, shown, total = "production runs", shown_runs, summary["production_runs"]

	return {
		"summary": summary,
		"chart": chart,
		"item_summary": item_summary,
		"cards": cards,
		# Lets the UI say "showing 50 of 1,651 runs" instead of silently
		# presenting a truncated page as if it were the whole period.
		"unit": unit,
		"total_runs": total,
		"shown_runs": shown,
		"truncated": shown < total,
	}


def _aggregate_by_item(cards):
	"""Club per-run cards into one card per finished item."""
	grouped, order = {}, []

	for c in cards:
		key = c["fg_item_code"] or c["fg_item_name"]
		g = grouped.get(key)
		if g is None:
			g = grouped[key] = {
				"run_count": 0,
				"dates": [],
				"fg_item_code": c["fg_item_code"],
				"fg_item_name": c["fg_item_name"],
				"fg_item_group": c["fg_item_group"],
				"produced_qty": 0.0,
				"uom": c["uom"],
				"produced_weight": 0.0,
				"weight_uom": c.get("weight_uom"),
				"weight_per_unit": c.get("weight_per_unit"),
				"src": set(),
				"tgt": set(),
				"inputs": {},
				"loss": {},
				"handling_loss_qty": 0.0,
				"entries": [],
			}
			order.append(key)

		g["entries"].append(
			{
				"stock_entry": c["stock_entry"],
				"posting_date": c["posting_date"],
				"produced_qty": flt(c["produced_qty"]),
				"uom": c["uom"],
				"work_order": c["work_order"],
				"handling_loss_qty": flt(c["handling_loss_qty"]),
			}
		)
		g["run_count"] += 1
		g["produced_qty"] += flt(c["produced_qty"])
		g["produced_weight"] += flt(c.get("produced_weight"))
		g["weight_uom"] = g["weight_uom"] or c.get("weight_uom")
		g["handling_loss_qty"] += flt(c["handling_loss_qty"])
		g["uom"] = g["uom"] or c["uom"]
		if c["posting_date"]:
			g["dates"].append(c["posting_date"])
		if c["source_warehouse"]:
			g["src"].add(c["source_warehouse"])
		if c["target_warehouse"]:
			g["tgt"].add(c["target_warehouse"])

		for it in c["inputs"]:
			k = (it["item_code"], it["uom"])
			e = g["inputs"].get(k)
			if e is None:
				e = g["inputs"][k] = {
					"item_code": it["item_code"],
					"item_name": it["item_name"],
					"item_group": it["item_group"],
					"qty": 0.0,
					"uom": it["uom"],
					"src": set(),
				}
			e["qty"] += flt(it["qty"])
			if it["source_warehouse"]:
				e["src"].add(it["source_warehouse"])

		for l in c["handling_loss_items"]:
			k = (l["item_code"], l["uom"])
			e = g["loss"].get(k)
			if e is None:
				e = g["loss"][k] = {
					"item_code": l["item_code"],
					"item_name": l["item_name"],
					"qty": 0.0,
					"uom": l["uom"],
				}
			e["qty"] += flt(l["qty"])

	def _wh(values):
		vals = sorted(v for v in values if v)
		if not vals:
			return None
		return vals[0] if len(vals) == 1 else f"Multiple ({len(vals)})"

	result = []
	for key in order:
		g = grouped[key]
		dates = sorted(set(g["dates"]))
		date_label = dates[0] if len(dates) <= 1 else f"{dates[0]} → {dates[-1]}"

		inputs = []
		for e in g["inputs"].values():
			inputs.append(
				{
					"item_code": e["item_code"],
					"item_name": e["item_name"],
					"item_group": e["item_group"],
					"qty": round(e["qty"], 3),
					"uom": e["uom"],
					"source_warehouse": _wh(e["src"]),
				}
			)

		# Item-level yield: total produced across all this item's runs / total raw
		# milk they consumed. Read straight off the already-merged input lines.
		milk_used = sum(e["qty"] for e in g["inputs"].values() if e["item_code"] in MILK_ITEMS)
		milk_uom = next((e["uom"] for e in g["inputs"].values() if e["item_code"] in MILK_ITEMS), None)
		milk_yield = round(g["produced_qty"] / milk_used, 4) if milk_used > 0 and g["produced_qty"] else None
		# Avg raw milk per run for this item (milk clubbed across g["run_count"] runs).
		avg_milk_per_run = round(milk_used / g["run_count"], 2) if milk_used and g["run_count"] else None

		result.append(
			{
				"stock_entry": None,
				"run_count": g["run_count"],
				"posting_date": date_label,
				"work_order": None,
				"fg_item_code": g["fg_item_code"],
				"fg_item_name": g["fg_item_name"],
				"fg_item_group": g["fg_item_group"],
				"produced_qty": round(g["produced_qty"], 3),
				"uom": g["uom"],
				"produced_weight": round(g["produced_weight"], 3) if g["produced_weight"] else None,
				"weight_uom": g["weight_uom"],
				"weight_per_unit": g["weight_per_unit"],
				"milk_used": round(milk_used, 3) if milk_used else None,
				"milk_uom": milk_uom,
				"milk_yield": milk_yield,
				"avg_milk_per_run": avg_milk_per_run,
				"source_warehouse": _wh(g["src"]),
				"target_warehouse": _wh(g["tgt"]),
				"inputs": inputs,
				"handling_loss_qty": round(g["handling_loss_qty"], 3),
				"handling_loss_items": [{**l, "qty": round(l["qty"], 3)} for l in g["loss"].values()],
				"entries": sorted(g["entries"], key=lambda e: e["posting_date"] or "", reverse=True),
			}
		)

	result.sort(key=lambda x: x["produced_qty"], reverse=True)
	return result


def _summary_from_rows(rows, loss_map):
	"""Totals over every matching run - deliberately independent of `limit`."""
	# Produced qty mixes UOMs (Nos / Kg / Litre) across items, so a single sum
	# is meaningless - bifurcate it per UOM instead.
	produced_by_uom = {}
	weight_by_uom = {}
	codes = set()
	total_produced = 0.0

	for r in rows:
		qty = flt(r.produced_qty)
		total_produced += qty

		u = r.uom or "—"
		produced_by_uom[u] = produced_by_uom.get(u, 0) + qty

		code = r.fg_item_code or r.fin_item_code
		if code:
			codes.add(code)

		wpu, wu = flt(r.weight_per_unit), r.weight_uom
		if wpu > 0 and wu:
			weight_by_uom[wu] = weight_by_uom.get(wu, 0) + qty * wpu

	produced_list = sorted(
		({"uom": u, "qty": round(q, 2)} for u, q in produced_by_uom.items()),
		key=lambda x: x["qty"],
		reverse=True,
	)
	weight_list = sorted(
		({"uom": u, "qty": round(q, 3)} for u, q in weight_by_uom.items()),
		key=lambda x: x["qty"],
		reverse=True,
	)

	return {
		"production_runs": len(rows),
		"distinct_items": len(codes),
		"total_produced_qty": round(total_produced, 2),
		"produced_by_uom": produced_list,
		"weight_by_uom": weight_list,
		"total_handling_loss_qty": round(sum(loss_map.values()), 2),
		"runs_with_loss": len([1 for r in rows if loss_map.get(r.name)]),
	}


def _item_summary(rows, loss_map):
	"""One row per produced item across the whole filtered period.

	This is the dense "what did we make and how much" table shown above the
	cards. Built off the same full-period rows as the summary bar, so it is
	independent of the card `limit` (the "Show" selector).
	"""
	items = {}
	for r in rows:
		code = r.fg_item_code or r.fin_item_code
		if not code:
			continue
		g = items.get(code)
		if g is None:
			g = items[code] = {
				"item_code": code,
				"item_name": r.custom_manufacturing_item_name or r.fin_item_name or code,
				"item_group": r.fg_item_group or r.fin_item_group,
				"uom": r.uom,
				"produced_qty": 0.0,
				"weight": 0.0,
				"weight_uom": r.weight_uom,
				"runs": 0,
				"loss": 0.0,
			}
		qty = flt(r.produced_qty)
		g["produced_qty"] += qty
		g["runs"] += 1
		g["uom"] = g["uom"] or r.uom
		wpu = flt(r.weight_per_unit)
		if wpu > 0 and r.weight_uom:
			g["weight"] += qty * wpu
			g["weight_uom"] = g["weight_uom"] or r.weight_uom
		g["loss"] += loss_map.get(r.name, 0.0)

	out = []
	for g in items.values():
		out.append(
			{
				"item_code": g["item_code"],
				"item_name": g["item_name"],
				"item_group": g["item_group"],
				"runs": g["runs"],
				"produced_qty": round(g["produced_qty"], 2),
				"uom": g["uom"],
				"weight": round(g["weight"], 2) if g["weight"] else None,
				"weight_uom": g["weight_uom"] if g["weight"] else None,
				"handling_loss_qty": round(g["loss"], 2),
			}
		)
	out.sort(key=lambda x: x["produced_qty"], reverse=True)
	return out


def _chart_from_rows(rows, loss_map):
	"""Top 10 produced items across the whole filtered period."""
	produced, loss = {}, {}
	for r in rows:
		key = r.custom_manufacturing_item_name or r.fin_item_name or r.fg_item_code or r.name
		produced[key] = produced.get(key, 0) + flt(r.produced_qty)
		loss[key] = loss.get(key, 0) + loss_map.get(r.name, 0.0)

	top = sorted(produced.items(), key=lambda kv: kv[1], reverse=True)[:10]
	return {
		"labels": [k for k, _ in top],
		"produced": [round(v, 2) for _, v in top],
		"loss": [round(loss.get(k, 0), 2) for k, _ in top],
	}


def _empty_summary():
	return {
		"production_runs": 0,
		"distinct_items": 0,
		"total_produced_qty": 0,
		"produced_by_uom": [],
		"weight_by_uom": [],
		"total_handling_loss_qty": 0,
		"runs_with_loss": 0,
		"total_milk_used": 0,
		"milk_uom": None,
		"avg_milk_per_run": 0,
	}
