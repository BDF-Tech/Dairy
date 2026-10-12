import frappe

# ---------------------------------------------------------------------------
# Logged In Details
#
# Who is logged in right now and who logged in / out in a date range.
#   * Live sessions come from `tabSessions`. Frappe does not delete expired rows
#     immediately, so a session only counts if its last activity is inside the
#     site's session expiry window.
#   * Login / logout history comes from Activity Log (operation Login/Logout).
# Status per user:
#   Online       - live session, active in the last ONLINE_MINUTES
#   Logged In    - live session, but idle
#   Logged Out   - no live session
#   Never        - has never logged in
# ---------------------------------------------------------------------------
ONLINE_MINUTES = 15
SYSTEM_USERS = {"Guest"}

FALLBACK_COLORS = ["blue", "purple", "orange", "green", "cyan", "pink", "yellow", "red"]


def _load_type_rules():
	"""Enabled rules from Logged In Details Settings, in table order."""
	settings = frappe.get_cached_doc("Logged In Details Settings")
	rules = [r for r in settings.user_type_rules if r.enabled and r.user_type]
	return rules, (settings.fallback_user_type or "Other")


def _rule_matches(rule, user, roles, has_employee):
	email = user.lower()
	if rule.match_on == "Email Ends With":
		return bool(rule.value) and email.endswith(rule.value.lower())
	if rule.match_on == "Email Contains":
		return bool(rule.value) and rule.value.lower() in email
	if rule.match_on == "Has Role":
		return rule.role in roles
	if rule.match_on == "Linked Employee":
		return has_employee
	return False


def _classify(user, roles, has_employee, rules, fallback):
	"""First matching rule wins -> (user type, rule department)."""
	for rule in rules:
		if _rule_matches(rule, user, roles, has_employee):
			return rule.user_type, rule.department
	return fallback, None


def _type_legend(rules, fallback):
	"""Distinct user types in rule order, each with a colour, fallback last.

	A type takes the first colour set on any of its rules; types with no colour
	get one not already used by another type.
	"""
	order, colors = [], {}
	for rule in rules:
		if rule.user_type not in colors:
			order.append(rule.user_type)
			colors[rule.user_type] = None
		if rule.color and not colors[rule.user_type]:
			colors[rule.user_type] = rule.color

	used = {c for c in colors.values() if c}
	spare = [c for c in FALLBACK_COLORS if c not in used] or FALLBACK_COLORS
	legend = []
	for i, name in enumerate(order):
		legend.append({"name": name, "color": colors[name] or spare[i % len(spare)]})
	if fallback not in colors:
		legend.append({"name": fallback, "color": "gray"})
	return legend


def _employee_map():
	"""user id -> employee record."""
	return {
		e.user_id: e
		for e in frappe.get_all(
			"Employee",
			filters={"user_id": ["is", "set"]},
			fields=["name", "employee_name", "user_id", "department"],
		)
	}


@frappe.whitelist()
def get_login_activity(from_date=None, to_date=None, include_disabled=0):
	from frappe.sessions import get_expiry_in_seconds
	from frappe.utils import add_to_date, getdate, now_datetime, today

	include_disabled = int(include_disabled)
	from_date = getdate(from_date or today())
	to_date = getdate(to_date or today())
	now = now_datetime()
	expiry_cutoff = add_to_date(now, seconds=-get_expiry_in_seconds())
	online_cutoff = add_to_date(now, minutes=-ONLINE_MINUTES)

	# Live sessions per user
	live = {}
	for s in frappe.db.sql(
		"""select user, count(*) as sessions, max(lastupdate) as last_seen,
				group_concat(distinct device) as devices
		   from `tabSessions`
		   where lastupdate > %s and user != 'Guest'
		   group by user""",
		(expiry_cutoff,),
		as_dict=True,
	):
		live[s.user] = s

	# Login / logout history in range
	hist = {}
	for h in frappe.db.sql(
		"""select user,
				sum(operation = 'Login' and status = 'Success') as logins,
				sum(operation = 'Login' and status = 'Failed') as failed,
				sum(operation = 'Logout') as logouts,
				min(case when operation = 'Login' and status = 'Success' then creation end) as first_login,
				max(case when operation = 'Logout' then creation end) as last_logout
		   from `tabActivity Log`
		   where operation in ('Login', 'Logout')
				and date(creation) between %s and %s
		   group by user""",
		(from_date, to_date),
		as_dict=True,
	):
		hist[h.user] = h

	# Last logout ever (for users who are logged out)
	last_logout = dict(frappe.db.sql(
		"""select user, max(creation) from `tabActivity Log`
		   where operation = 'Logout' group by user"""
	))

	filters = {"name": ["not in", list(SYSTEM_USERS)], "user_type": "System User"}
	if not include_disabled:
		filters["enabled"] = 1
	users = frappe.get_all(
		"User",
		filters=filters,
		fields=["name", "full_name", "enabled", "last_login", "last_active", "last_ip"],
	)
	emp_map = _employee_map()
	rules, fallback = _load_type_rules()
	user_roles = {}
	if any(r.match_on == "Has Role" for r in rules):
		for user, role in frappe.db.sql(
			"select parent, role from `tabHas Role` where parenttype = 'User'"
		):
			user_roles.setdefault(user, set()).add(role)

	rows = []
	for u in users:
		s = live.get(u.name)
		h = hist.get(u.name) or {}
		if s:
			status = "Online" if s.last_seen and s.last_seen > online_cutoff else "Logged In"
		elif u.last_login:
			status = "Logged Out"
		else:
			status = "Never"
		emp = emp_map.get(u.name)
		user_category, rule_department = _classify(
			u.name, user_roles.get(u.name, set()), bool(emp), rules, fallback
		)
		rows.append({
			"user": u.name,
			"full_name": u.full_name or u.name,
			"enabled": u.enabled,
			"employee_name": emp.employee_name if emp else None,
			"department": (emp.department if emp else None) or rule_department,
			"user_category": user_category,
			"status": status,
			"sessions": s.sessions if s else 0,
			"devices": s.devices if s else None,
			"last_seen": (s.last_seen if s else None) or u.last_active,
			"last_login": u.last_login,
			"last_logout": last_logout.get(u.name),
			"last_ip": u.last_ip,
			"logins": int(h.get("logins") or 0),
			"failed": int(h.get("failed") or 0),
			"logouts": int(h.get("logouts") or 0),
			"first_login_in_range": h.get("first_login"),
		})

	order = {"Online": 0, "Logged In": 1, "Logged Out": 2, "Never": 3}
	rows.sort(key=lambda r: (order[r["status"]], -(r["last_seen"].timestamp() if r["last_seen"] else 0)))

	summary = {
		"online": sum(1 for r in rows if r["status"] == "Online"),
		"logged_in": sum(1 for r in rows if r["status"] in ("Online", "Logged In")),
		"logged_out": sum(1 for r in rows if r["status"] == "Logged Out"),
		"never": sum(1 for r in rows if r["status"] == "Never"),
		"logged_in_range": sum(1 for r in rows if r["logins"]),
		"failed": sum(r["failed"] for r in rows),
		"online_minutes": ONLINE_MINUTES,
	}

	events = frappe.db.sql(
		"""select creation, user, full_name, operation, status, ip_address
		   from `tabActivity Log`
		   where operation in ('Login', 'Logout')
				and date(creation) between %s and %s
		   order by creation desc
		   limit 500""",
		(from_date, to_date),
		as_dict=True,
	)

	return {
		"rows": rows,
		"summary": summary,
		"events": events,
		"user_types": _type_legend(rules, fallback),
	}
