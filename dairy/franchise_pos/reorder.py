"""Franchise POS: tomorrow's order suggestion.

Per item the franchise may order in the app:
	need      = average daily sales x (1 + safety margin) - stock in hand - already ordered (not yet invoiced)
	suggested = need rounded UP to whole order units (crates, boxes ...)

Average daily sales = net sales of the last N closed-or-past days / N, where N is "Average sales over
(days)" in Franchise POS Settings, or fewer days for a franchise that started billing recently.
The franchise always checks the list and places the order itself; nothing is ordered automatically.
"""

import math

import frappe
from frappe.utils import add_days, cint, date_diff, flt, getdate, today

from dairy.franchise_pos.stock import LEDGER, get_balances, get_settings


def _orderable_items(customer):
	"""Items the customer may order in the app (its App Template), with the order unit and its size.
	The biggest allowed unit is used (a crate rather than a single piece)."""
	template = frappe.get_cached_value("Customer", customer, "custom_app_template")
	if not template:
		return {}
	rows = frappe.get_all("Item Template Item", filters={"parent": template, "allow_on_app": 1}, fields=["item", "uom"])
	if not rows:
		return {}
	codes = list({r.item for r in rows})
	items = {
		i.name: i
		for i in frappe.get_all(
			"Item", filters={"name": ["in", codes], "disabled": 0, "is_sales_item": 1},
			fields=["name", "item_name", "item_group", "stock_uom", "image"],
		)
	}
	factors = {}
	for u in frappe.get_all("UOM Conversion Detail", filters={"parent": ["in", codes]}, fields=["parent", "uom", "conversion_factor"]):
		factors[(u.parent, u.uom)] = flt(u.conversion_factor) or 1

	out = {}
	for r in rows:
		item = items.get(r.item)
		if not item:
			continue
		factor = 1.0 if r.uom == item.stock_uom else factors.get((r.item, r.uom))
		if not factor:
			continue
		best = out.get(r.item)
		if not best or factor > best["factor"]:
			out[r.item] = {"item": item, "uom": r.uom, "factor": factor}
	return out


def _order_rules(customer):
	"""{item_code: {"uom", "qty", "mandatory"}} from the customer's Mandatory Order table."""
	rules = {}
	for m in frappe.get_all(
		"Mandatory Order set", filters={"parent": customer, "parenttype": "Customer"},
		fields=["item", "uom", "qty", "minimum_qty"],
	):
		rules[m.item] = {"uom": m.uom, "qty": flt(m.qty), "mandatory": not cint(m.minimum_qty)}
	return rules


def _safety(settings):
	default = 10.0 if settings.safety_percent is None else flt(settings.safety_percent)
	by_group = {g.item_group: flt(g.safety_percent) for g in (settings.reorder_groups or [])}
	return default, by_group


def _avg_daily_sales(franchise, days, upto):
	"""{item_code: average net units sold per day}, and the number of days it was averaged over."""
	first = frappe.db.sql(
		f"select min(posting_date) from `tab{LEDGER}` where franchise = %s and entry_type = 'Sale'", franchise
	)[0][0]
	if not first:
		return {}, 0
	n = max(1, min(days, date_diff(upto, first) + 1))
	start = add_days(upto, -(n - 1))
	rows = frappe.db.sql(
		f"""select item_code, -sum(qty) from `tab{LEDGER}`
		where franchise = %s and entry_type in ('Sale', 'Sale Return') and posting_date between %s and %s
		group by item_code""",
		(franchise, start, upto),
	)
	return {r[0]: max(flt(r[1]), 0) / n for r in rows}, n


def _on_order(franchise, from_date):
	"""Stock units already ordered for delivery from `from_date` on and not yet invoiced, plus deliveries invoiced
	but not yet confirmed by the franchise (not in its stock yet)."""
	out = dict(frappe.db.sql(
		"""select soi.item_code, sum(soi.stock_qty * (1 - least(ifnull(soi.billed_amt, 0) / nullif(soi.amount, 0), 1)))
		from `tabSales Order Item` soi join `tabSales Order` so on so.name = soi.parent
		where so.customer = %s and so.docstatus < 2 and so.status not in ('Closed', 'Completed', 'On Hold')
			and so.delivery_date >= %s
		group by soi.item_code""",
		(franchise, from_date),
	))
	for code, qty in frappe.db.sql(
		"""select i.item_code, sum(i.invoiced_qty) from `tabFranchise Stock Receipt Item` i
		join `tabFranchise Stock Receipt` r on r.name = i.parent
		where r.franchise = %s and r.docstatus = 0 group by i.item_code""", franchise):
		out[code] = flt(out.get(code)) + flt(qty)
	return out


def existing_order(franchise, target_date, shift):
	return frappe.db.get_value(
		"Sales Order",
		{"customer": franchise, "delivery_date": target_date, "delivery_shift": shift, "docstatus": ["<", 2]},
		["name", "docstatus", "grand_total"], as_dict=True,
	)


def suggest(franchise, target_date=None, shift="Morning"):
	settings = get_settings()
	target_date = getdate(target_date or add_days(today(), 1))
	days = cint(settings.reorder_days) or 7
	# sales up to yesterday are complete days; today counts too once it has been closed
	upto = getdate(today())
	if not frappe.db.exists("Franchise Day Close", {"franchise": franchise, "posting_date": upto, "docstatus": 1}):
		upto = getdate(add_days(upto, -1))

	orderable = _orderable_items(franchise)
	avg, n_days = _avg_daily_sales(franchise, days, upto)
	stock = get_balances(franchise)
	on_order = _on_order(franchise, today())
	rules = _order_rules(franchise)
	default_safety, group_safety = _safety(settings)

	rows = []
	for code, o in orderable.items():
		item, factor = o["item"], o["factor"]
		safety = group_safety.get(item.item_group, default_safety)
		daily = flt(avg.get(code))
		in_hand = max(flt(stock.get(code)), 0)
		ordered = max(flt(on_order.get(code)), 0)
		need = daily * (1 + safety / 100) - in_hand - ordered
		qty = math.ceil(round(need / factor, 6)) if need > 0 else 0

		rule = rules.get(code)
		fixed = 0.0
		if rule and rule["mandatory"] and rule["uom"] == o["uom"]:
			fixed = rule["qty"]
			qty = max(qty, fixed)  # the order always carries the fixed quantity anyway
		elif rule and not rule["mandatory"] and 0 < qty < rule["qty"] and rule["uom"] == o["uom"]:
			qty = rule["qty"]  # minimum order

		if not (qty or daily or in_hand or ordered):
			continue  # never sold, none in hand: keep the list short
		rows.append({
			"item_code": code, "item_name": item.item_name, "item_group": item.item_group, "image": item.image,
			"uom": o["uom"], "factor": factor, "stock_uom": item.stock_uom,
			"avg_daily": flt(daily, 2), "in_hand": flt(in_hand, 3), "on_order": flt(ordered, 3),
			"safety_percent": safety, "suggested_qty": qty, "fixed_qty": fixed,
			"min_qty": rule["qty"] if rule and not rule["mandatory"] else 0,
		})
	rows.sort(key=lambda r: (-(r["suggested_qty"] > 0), -r["avg_daily"], r["item_name"] or ""))
	return {
		"target_date": str(target_date), "shift": shift, "days": n_days, "upto": str(upto),
		"existing_order": existing_order(franchise, target_date, shift),
		"items": rows,
	}
