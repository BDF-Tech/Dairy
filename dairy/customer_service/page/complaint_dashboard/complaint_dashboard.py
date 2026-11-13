# Copyright (c) 2026, BDF and contributors
"""Complaint Dashboard page.

Load design (kept deliberately cheap):
- ONE SQL query per (user, filters): active complaints + complaints in the selected period, using the
  status / date_of_complaint indexes. Every card, chart and list is built from that one result in Python.
- Result cached per user + filters and keyed on a "data version" that changes whenever any complaint
  changes (see customer_complaint.notify_counters), so an unchanged dashboard costs zero DB queries.
- Card clicks filter in the browser; the server is not called again.
"""

import hashlib
from collections import Counter, defaultdict
from datetime import timedelta

import frappe
from frappe.utils import add_days, cint, flt, get_fullname, getdate, nowdate

from dairy.customer_service.doctype.customer_complaint.customer_complaint import (
	BACKLOG_STATES,
	OPEN_STATES,
	dashboard_data_version,
)

FILTER_FIELDS = ("complaint_from", "entry_type", "source", "department", "route")
MAX_PERIOD_DAYS = 366
CACHE_TTL = 15 * 60  # seconds; the version key makes it stale-proof, TTL only frees memory


@frappe.whitelist()
def get_dashboard(filters=None):
	f = frappe._dict(frappe.parse_json(filters) if filters else {})
	today = getdate(nowdate())
	to_date = min(getdate(f.get("to_date") or today), today)
	from_date = getdate(f.get("from_date") or add_days(to_date, -30))
	if (to_date - from_date).days > MAX_PERIOD_DAYS:
		from_date = add_days(to_date, -MAX_PERIOD_DAYS)
	f.from_date, f.to_date = str(from_date), str(to_date)

	user = frappe.session.user
	sig = hashlib.md5(frappe.as_json({k: f.get(k) for k in sorted(f)}, indent=None).encode()).hexdigest()[:12]
	# today in the key: "Created Today" / "Overdue" must roll over at midnight even if nothing changed
	key = f"complaint_dash:{dashboard_data_version()}:{today}:{user}:{sig}"
	# expires=True: read Redis directly (a plain get_value remembers a miss in request memory and would
	# ignore a value stored with an expiry later in the same request)
	cached = frappe.cache.get_value(key, expires=True)
	if cached:
		return cached
	data = build(f, user, today)
	frappe.cache.set_value(key, data, expires_in_sec=CACHE_TTL)
	return data


def _roles_queue(roles):
	"""States that wait on the current user's role (besides complaints assigned to them)."""
	states = []
	if roles & {"Complaint Manager", "System Manager"}:
		states.append("Pending Approval")
	if roles & {"Complaint Accounts Approver", "System Manager"}:
		states.append("Accounts Approval")
	if "BDF Customer Complaint Viewer" in roles:
		states.append("Resolved")  # CS closes after informing the customer
	return states


def fetch_rows(f, user, queue_states):
	from frappe.model.db_query import DatabaseQuery

	# same permission conditions as the list view (role perms, if-owner, shares, confidential rule)
	match = DatabaseQuery("Customer Complaint").build_match_conditions()
	states = list(dict.fromkeys(list(BACKLOG_STATES) + queue_states))
	values = {"states": states, "from_date": f.from_date, "to_date": f.to_date, "user": user}
	conds = ["(status IN %(states)s OR date_of_complaint BETWEEN %(from_date)s AND %(to_date)s)"]
	for k in FILTER_FIELDS:
		if f.get(k):
			conds.append(f"`{k}` = %({k})s")
			values[k] = f[k]
	if cint(f.get("only_mine")):
		conds.append("assigned_user = %(user)s")
	if match:
		conds.append(match)
	return frappe.db.sql(
		f"""SELECT name, raised_by_name, complaint_from, entry_type, source, status, severity_level,
			CASE complaint_from WHEN 'Employee' THEN internal_type WHEN 'Customer' THEN complaint_type ELSE issue_type END AS type, item_name, route, department,
			assigned_user, due_date, date_of_complaint, confidential, resolved_on, resolution_hours,
			LEFT(description_of_issue, 120) AS description
		FROM `tabCustomer Complaint`
		WHERE {" AND ".join(conds)}
		ORDER BY date_of_complaint DESC, time_of_complaint DESC""",
		values,
		as_dict=True,
	)


def build(f, user, today):
	roles = set(frappe.get_roles(user))
	queue_states = _roles_queue(roles)
	from_date, to_date = getdate(f.from_date), getdate(f.to_date)
	rows = fetch_rows(f, user, queue_states)

	counts = Counter()
	by = defaultdict(Counter)
	hours = []
	out_rows = []
	for r in rows:
		d = r.date_of_complaint
		in_period = bool(d and from_date <= d <= to_date)
		pending = r.status in BACKLOG_STATES
		overdue = r.status in OPEN_STATES and r.due_date and r.due_date < today
		mine = (r.status in OPEN_STATES and r.assigned_user == user) or r.status in queue_states
		buckets = []
		if d == today:
			buckets.append("today")
		if r.status == "Open":
			buckets.append("open")
		elif r.status == "Assigned":
			buckets.append("in_process")
		elif r.status in ("Pending Approval", "Accounts Approval"):
			buckets.append("approval")
		if overdue:
			buckets.append("overdue")
		if mine:
			buckets.append("mine")
		if in_period:
			buckets.append("period")
			if r.status in ("Resolved", "Closed"):
				buckets.append("resolved")
			elif r.status == "Rejected":
				buckets.append("rejected")
			by["source"][r.source or "Not Set"] += 1
			by["type"][r.type or "Not Set"] += 1
			by["status"][r.status] += 1
			if r.complaint_from == "Customer":
				by["route"][r.route or "Not Set"] += 1
			if flt(r.resolution_hours) > 0:
				hours.append(flt(r.resolution_hours))
		if pending:
			by["department"][r.department or "Not Set"] += 1
		if not buckets:
			continue  # e.g. an old Resolved row fetched only for someone else's queue
		counts.update(buckets)
		out_rows.append({
			"name": r.name, "raised_by": r.raised_by_name, "from": r.complaint_from, "source": r.source,
			"status": r.status, "severity": r.severity_level, "type": r.type or r.entry_type, "item": r.item_name,
			"route": r.route, "department": r.department, "assigned": get_fullname(r.assigned_user) if r.assigned_user else "",
			"due": str(r.due_date) if r.due_date else "", "date": str(d) if d else "", "age": (today - d).days if d else None,
			"overdue": bool(overdue), "confidential": cint(r.confidential), "desc": r.description, "b": buckets,
		})

	top = lambda c, n=10: [[k, v] for k, v in c.most_common(n)]
	return {
		"counts": {k: counts.get(k, 0) for k in ("today", "open", "in_process", "approval", "overdue", "mine", "resolved", "rejected", "period")},
		"avg_hours": round(sum(hours) / len(hours), 1) if hours else 0,
		"charts": {
			"trend": _trend(rows, from_date, to_date),
			"source": top(by["source"]), "type": top(by["type"]), "status": top(by["status"]),
			"department": top(by["department"]), "route": top(by["route"]),
		},
		"rows": out_rows,
		"period": [f.from_date, f.to_date],
		"generated": frappe.utils.now(),
	}


def _trend(rows, start, end):
	span = (end - start).days
	unit = "day" if span <= 62 else "week" if span <= 366 else "month"

	def bucket(d):
		d = getdate(d)
		if unit == "week":
			return d - timedelta(days=d.weekday())
		return d if unit == "day" else d.replace(day=1)

	created, resolved = Counter(), Counter()
	for r in rows:
		if r.date_of_complaint and start <= r.date_of_complaint <= end:
			created[bucket(r.date_of_complaint)] += 1
		if r.resolved_on and start <= getdate(r.resolved_on) <= end:
			resolved[bucket(r.resolved_on)] += 1
	keys, d = [], bucket(start)
	while d <= end:
		keys.append(d)
		d = d + timedelta(days=1 if unit == "day" else 7) if unit != "month" else (d.replace(day=28) + timedelta(days=4)).replace(day=1)
	fmt = "%b %y" if unit == "month" else "%d %b"
	return {"unit": unit, "labels": [k.strftime(fmt) for k in keys],
		"created": [created[k] for k in keys], "resolved": [resolved[k] for k in keys]}
