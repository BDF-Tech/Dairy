import frappe
from frappe.utils import flt

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


def _manufacture_runs(
	from_date, to_date, company=None, item_group=None, item_code=None, stock_entry=None, limit=None
):
	"""Query A - manufacture parents in range (optionally scoped by group/item).

	The Item master is always joined so weight_per_unit / weight_uom come back
	with the run itself - that is what lets a run of 200 Nos of a 0.200 Kg item
	be reported as 40 Kg without a second query.
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

	where = " AND ".join(conditions)
	join = " ".join(joins)
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

	runs = _manufacture_runs(from_date, to_date, company, item_group, item_code, stock_entry, limit)
	if not runs:
		return {"summary": _empty_summary(), "chart": {"labels": [], "produced": [], "loss": []}, "cards": []}

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

	cards, chart_produced, chart_loss = [], {}, {}
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

		key = fg_name or fg_code or run.name
		chart_produced[key] = chart_produced.get(key, 0) + produced_qty
		chart_loss[key] = chart_loss.get(key, 0) + flt(loss["qty"])

	# Top 10 produced items for the chart.
	top = sorted(chart_produced.items(), key=lambda kv: kv[1], reverse=True)[:10]
	chart = {
		"labels": [k for k, _ in top],
		"produced": [round(v, 2) for _, v in top],
		"loss": [round(chart_loss.get(k, 0), 2) for k, _ in top],
	}

	# Summary always reflects the raw runs; cards may then be clubbed by item.
	summary = _build_summary(cards)
	if group_by == "Item":
		cards = _aggregate_by_item(cards)

	return {"summary": summary, "chart": chart, "cards": cards}


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


def _build_summary(cards):
	# Produced qty mixes UOMs (Nos / Kg / Litre) across items, so a single sum
	# is meaningless - bifurcate it per UOM instead.
	produced_by_uom = {}
	weight_by_uom = {}
	for c in cards:
		u = c["uom"] or "—"
		produced_by_uom[u] = produced_by_uom.get(u, 0) + flt(c["produced_qty"])

		w, wu = flt(c.get("produced_weight")), c.get("weight_uom")
		if w and wu:
			weight_by_uom[wu] = weight_by_uom.get(wu, 0) + w

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
		"production_runs": len(cards),
		"distinct_items": len({c["fg_item_code"] for c in cards if c["fg_item_code"]}),
		"total_produced_qty": round(sum(c["produced_qty"] for c in cards), 2),
		"produced_by_uom": produced_list,
		"weight_by_uom": weight_list,
		"total_handling_loss_qty": round(sum(c["handling_loss_qty"] for c in cards), 2),
		"runs_with_loss": len([c for c in cards if c["handling_loss_qty"]]),
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
	}
