# Copyright (c) 2026, BDF and contributors

import frappe
from frappe import _
from frappe.utils import date_diff, getdate, nowdate

from dairy.customer_service.doctype.customer_complaint.customer_complaint import (
	BACKLOG_STATES as PENDING,
	OPEN_STATES,
)


def execute(filters=None):
	filters = frappe._dict(filters or {})
	data = get_data(filters)
	return get_columns(), data, None, get_chart(data), get_summary(data)


def get_columns():
	def c(label, fieldname, fieldtype="Data", width=110, options=None):
		d = {"label": _(label), "fieldname": fieldname, "fieldtype": fieldtype, "width": width}
		if options:
			d["options"] = options
		return d

	return [
		c("ID", "name", "Link", 140, "Customer Complaint"),
		c("Complaint ID", "complaint_id", width=95),
		c("Date", "date_of_complaint", "Date", 95),
		c("Entry Type", "entry_type", width=90),
		c("From", "complaint_from", width=85),
		c("Raised By", "raised_by_name", width=190),
		c("Customer Type", "type_of_customer", width=105),
		c("Route", "route", "Link", 120, "Route Master"),
		c("Item", "item_name", width=130),
		c("Complaint Type", "complaint_type", width=115),
		c("Internal Type", "internal_type", width=130),
		c("Issue Type", "issue_type", width=130),
		c("Farmer / Supplier", "supplier_name", width=170),
		c("Against Dept", "against_department", "Link", 140, "Department"),
		c("Category", "category", "Link", 140, "Complaint Category"),
		c("Severity", "severity_level", width=75),
		c("Description", "description_of_issue", width=220),
		c("Status", "status", width=85),
		c("Department", "department", "Link", 140, "Department"),
		c("Assigned To", "assigned_user", "Link", 150, "User"),
		c("Due Date", "due_date", "Date", 95),
		c("Overdue", "overdue", width=70),
		c("Age (Days)", "age_days", "Int", 80),
		c("Resolution (Hrs)", "resolution_hours", "Float", 105),
		c("Preferred Resolution", "preferred_resolution", width=120),
		c("Resolution Type", "resolution_type", width=120),
		c("Action Taken", "action_taken", width=220),
		c("Satisfied", "customer_satisfied", width=70),
	]


FIELDS = [
	"name", "complaint_id", "date_of_complaint", "entry_type", "complaint_from", "raised_by_name", "issue_type", "supplier_name", "internal_type",
	"against_department", "type_of_customer", "route", "item_code", "item_name", "complaint_type", "category",
	"severity_level", "description_of_issue", "status", "department", "assigned_user", "due_date", "resolved_on",
	"closed_on", "modified", "resolution_hours", "preferred_resolution", "resolution_type", "action_taken",
	"customer_satisfied",
]


def get_data(f):
	# frappe.get_list: the user's own permissions apply (roles, "only if creator", user permissions)
	filters = [["date_of_complaint", "between", [f.from_date, f.to_date]]]
	for key in ("entry_type", "complaint_from", "internal_type", "issue_type", "complaint_type", "category", "route", "customer_id",
			"item_code", "department", "assigned_user"):
		if f.get(key):
			filters.append([key, "=", f[key]])
	if f.status == "Pending (not yet resolved)":
		filters.append(["status", "in", PENDING])
	elif f.status == "Overdue":
		filters += [["status", "in", OPEN_STATES], ["due_date", "is", "set"], ["due_date", "<", nowdate()]]
	elif f.status:
		filters.append(["status", "=", f.status])
	rows = frappe.get_list("Customer Complaint", filters=filters, fields=FIELDS,
		order_by="date_of_complaint desc, time_of_complaint desc", limit_page_length=0)

	today = getdate()
	for r in rows:
		pending = r.status in PENDING
		# old records have no resolved_on; fall back to last modified
		end = today if pending else getdate(r.resolved_on or r.closed_on or r.modified)
		r.item_name = r.item_name or r.item_code
		r.age_days = date_diff(end, getdate(r.date_of_complaint))
		r.overdue = "Yes" if r.status in OPEN_STATES and r.due_date and getdate(r.due_date) < today else ""
	return rows


def get_chart(data):
	if not data:
		return None
	counts = {}
	for r in data:
		key = {"Employee": r.internal_type, "Customer": r.complaint_type}.get(r.complaint_from, r.issue_type) or _("Not Set")
		counts[key] = counts.get(key, 0) + 1
	top = sorted(counts.items(), key=lambda x: -x[1])
	return {
		"data": {"labels": [k for k, _ in top], "datasets": [{"name": _("Entries"), "values": [v for _, v in top]}]},
		"type": "bar",
		"colors": ["#5e64ff"],
	}


def get_summary(data):
	total = len(data)
	pending = sum(1 for r in data if r.status in PENDING)
	hrs = [r.resolution_hours for r in data if r.resolution_hours]
	return [
		{"label": _("Total"), "value": total, "indicator": "Blue"},
		{"label": _("Pending"), "value": pending, "indicator": "Orange"},
		{"label": _("Overdue"), "value": sum(1 for r in data if r.overdue), "indicator": "Red"},
		{"label": _("Resolved / Closed"), "value": total - pending, "indicator": "Green"},
		{"label": _("Avg Resolution (Hrs)"), "value": round(sum(hrs) / len(hrs), 1) if hrs else 0, "indicator": "Blue"},
	]
