# Copyright (c) 2026, BDF and contributors

import frappe
from frappe import _
# _add(ignore_permissions=True): assignments here are system actions (auto-assign, escalation, app follow-up),
# so they must not depend on whether the user who triggered them may assign.
from frappe.desk.form.assign_to import DuplicateToDoError, close_all_assignments
from frappe.desk.form.assign_to import _add as _add_assignment


def add_assignment(args):
	return _add_assignment(args, ignore_permissions=True)

from frappe.model.document import Document
from frappe.utils import add_days, get_datetime, getdate, now_datetime, nowdate, time_diff_in_hours

# Status is moved by the Workflow ("Customer Complaint Workflow"). The only automatic move kept in code
# is Open -> Assigned when an assignee is set, so API / mobile / WhatsApp entries work without clicks.
OPEN_STATES = ("Open", "Assigned")
BACKLOG_STATES = ("Open", "Assigned", "Pending Approval", "Accounts Approval")
DONE_STATES = ("Resolved", "Closed", "Rejected")
# resolution types that need Accounts approval (workflow condition uses the same list)
ACCOUNTS_RESOLUTIONS = ("Refund", "Credit Note")
# used when no Complaint Category is picked
DAYS_BY_SEVERITY = {"Critical": 1, "Major": 2, "Minor": 3}
# Issue Type options per group (the form shows only the group's own list; checked again on save)
# Resolution Type options per group (customer.js shows only these; checked again on save)
RESOLUTION_TYPES = {
	"Customer": ["Replacement", "Credit Note", "Refund", "Explanation Given", "Process Fixed", "No Action Needed", "Other"],
	"Employee": ["Issue Fixed", "Policy / Process Changed", "Explanation Given", "Escalated to Management", "Referred to Department", "Disciplinary Action Taken", "No Action Needed", "Other"],
	"Farmer": ["Payment Released", "Fat / SNF Corrected", "Rate Corrected", "Explanation Given", "Process Fixed", "No Action Needed", "Other"],
	"Vendor": ["Payment Released", "PO Corrected", "Goods Returned / Replaced", "Explanation Given", "No Action Needed", "Other"],
	"Other": ["Explanation Given", "Process Fixed", "Replacement", "No Action Needed", "Other"],
}

ISSUE_TYPES = {
	"Farmer": ["Payment Pending", "Wrong Fat / SNF", "Wrong Quantity", "Collection Timing", "Milk Rate", "Bonus / Incentive", "Other"],
	"Vendor": ["Payment Delay", "Purchase Order Issue", "Quality", "Returns", "Vehicle / Transport", "Other"],
	"Other": ["General", "Quality", "Service", "Other"],
}
# Customer Group -> "Type of Customer" (existing field options)
CUSTOMER_TYPE = {"Franchise": "Franchise", "Sub Franchise": "Sub-Franchise", "Line Customer": "Line Customer"}


def short_address(address_name):
	"""First address line + city, as the old free-text Address field expects (max 140 chars)."""
	if not address_name:
		return None
	a = frappe.db.get_value("Address", address_name, ["address_line1", "city"], as_dict=True)
	return ", ".join(filter(None, [a.address_line1, a.city]))[:140] if a else None


class CustomerComplaint(Document):
	def before_validate(self):
		# fill from Customer / Item before the mandatory check (the form does this in JS; API needs it here)
		changed = lambda f: self.is_new() or self.has_value_changed(f)
		# pick a Customer and the rest fills itself (phone-call entry = customer + type + one line)
		if self.complaint_from == "Customer" and self.customer_id and (
			changed("customer_id") or not (self.name_of_a_customer and self.type_of_customer)
		):
			c = frappe.db.get_value("Customer", self.customer_id, [
				"customer_name", "customer_group", "custom_route_master", "mobile_no", "customer_primary_address",
			], as_dict=True)
			if c:
				self.name_of_a_customer = self.name_of_a_customer or c.customer_name
				if changed("customer_id") or not self.type_of_customer:
					self.type_of_customer = CUSTOMER_TYPE.get(c.customer_group, "Other")
				self.route = self.route or c.custom_route_master
				self.address = self.address or short_address(c.customer_primary_address)
				if not self.contact_no or self.contact_no.strip() in ("+91", "+91-"):
					self.contact_no = c.mobile_no or self.contact_no
		self.contact_no = normalise_phone(self.contact_no)
		# several products: the first row stays in Item Code / Batch so old reports and lists keep working
		rows = [r for r in (self.get("items") or []) if r.item_code]
		if rows:
			for r in rows:
				if not r.item_name:
					r.item_name = frappe.db.get_value("Item", r.item_code, "item_name")
			if self.item_code != rows[0].item_code:
				self.item_code, self.item_name = rows[0].item_code, rows[0].item_name
			self.data_kxgv = self.data_kxgv or rows[0].batch_no
		if self.item_code and not self.item_name:
			self.item_name = frappe.db.get_value("Item", self.item_code, "item_name")
		if self.complaint_from == "Employee" and self.employee and (changed("employee") or not self.employee_name):
			e = frappe.db.get_value("Employee", self.employee, ["employee_name", "department"], as_dict=True)
			if e:
				self.employee_name, self.employee_department = e.employee_name, e.department
		if self.complaint_from in ("Farmer", "Vendor") and self.supplier and (changed("supplier") or not self.supplier_name):
			sup = frappe.db.get_value("Supplier", self.supplier, ["supplier_name", "dcs", "custom_member_code"], as_dict=True)
			if sup:
				self.supplier_name = sup.supplier_name
				if self.complaint_from == "Farmer":
					self.dcs, self.member_code = sup.dcs, sup.custom_member_code
		self.raised_by_name = {
			"Employee": self.employee_name,
			"Farmer": self.supplier_name,
			"Vendor": self.supplier_name,
		}.get(self.complaint_from, self.name_of_a_customer)

	def before_save(self):
		# Complaint ID continues the CS team's own CI-### numbering (series "CI-", seeded from their last number).
		# Taken here, after all checks passed, so a rejected entry never uses up a number.
		if self.is_new() and self.complaint_from == "Customer" and not self.complaint_id:
			from frappe.model.naming import make_autoname

			self.complaint_id = make_autoname("CI-.###", doc=self)

	def validate(self):
		if self.is_new() and frappe.session.user == "Guest":
			self.source = "Web Form"
		if self.is_new():
			self.validate_required()
		if self.complaint_from == "Employee" and not self.department and self.against_department:
			self.department = self.against_department
		self.validate_resolution_type()
		self.apply_category_defaults()
		self.set_due_date()
		self.auto_assign_status()
		self.on_status_change()

	def validate_resolution_type(self):
		# only when picked/changed: older records keep whatever they already had
		if not self.resolution_type or not (self.is_new() or self.has_value_changed("resolution_type")):
			return
		group = self.complaint_from or "Customer"
		if self.resolution_type not in RESOLUTION_TYPES.get(group, []):
			frappe.throw(_("Resolution Type {0} is not valid for {1} complaints").format(self.resolution_type, group))

	def validate_required(self):
		"""The few fields a new complaint needs (the form shows the same via mandatory_depends_on, which Frappe
		checks only in the browser). Phone call: customer (or name + phone) + type + one line. App / WhatsApp
		entries come from a known customer, so phone and description are not forced there."""
		manual = self.source not in ("Mobile App", "WhatsApp", "Web Form")  # web form has its own required fields
		is_complaint = self.entry_type == "Complaint"
		missing = []
		group = self.complaint_from
		if group == "Employee":
			if not self.employee:
				missing.append(_("Employee"))
			if is_complaint and not self.internal_type:
				missing.append(_("Internal Complaint Type"))
		elif group == "Customer":
			if not self.name_of_a_customer:
				missing.append(_("Customer (or Name of a Customer)"))
			if manual and not self.customer_id and not self.contact_no:
				missing.append(_("Contact No. (for a caller who is not a customer)"))
			if is_complaint and not self.complaint_type:
				missing.append(_("Complaint Type"))
		else:  # Farmer / Vendor / Other
			if group in ("Farmer", "Vendor") and not self.supplier:
				missing.append(_("Farmer / Supplier"))
			if group == "Other" and not self.name_of_a_customer:
				missing.append(_("Name"))
			if manual and not self.contact_no:
				missing.append(_("Contact No."))
			if is_complaint and not self.issue_type:
				missing.append(_("Issue Type"))
		if (manual or not is_complaint) and not (self.description_of_issue or "").strip():
			missing.append(_("Description of Issue"))
		if missing:
			frappe.throw(_("Please fill: {0}").format(", ".join(missing)), frappe.MandatoryError, title=_("Missing fields"))
		if self.issue_type and self.issue_type not in ISSUE_TYPES.get(group, []):
			frappe.throw(_("Issue Type {0} is not valid for {1}").format(self.issue_type, group))

	def on_update(self):
		notify_counters()
		if self.assigned_user and self.has_value_changed("assigned_user") and self.status in OPEN_STATES:
			self.assign_user(self.assigned_user, _("Complaint: {0}").format(self.title_text()))
		if self.has_value_changed("status"):
			prev = self.get_doc_before_save()
			if self.status in DONE_STATES:
				close_all_assignments(self.doctype, self.name, ignore_permissions=True)
			elif self.status == "Assigned" and prev and prev.status != "Open" and self.assigned_user:
				# sent back or reopened -> put it back on the assignee's to-do list
				self.assign_user(self.assigned_user, _("Sent back: {0}").format(self.title_text()))

	def on_trash(self):
		notify_counters()

	def title_text(self):
		what = {"Employee": self.internal_type, "Customer": self.complaint_type}.get(self.complaint_from, self.issue_type)
		item = self.item_name if self.complaint_from == "Customer" else None
		return " - ".join(filter(None, [self.raised_by_name, what or "", item]))

	# ---------------------------------------------------------------- defaults
	def apply_category_defaults(self):
		if not self.category or not (self.is_new() or self.has_value_changed("category")):
			return
		cat = frappe.get_cached_doc("Complaint Category", self.category)
		if not self.department and cat.default_department:
			self.department = cat.default_department
		if not self.assigned_user and cat.default_assignee:
			self.assigned_user = cat.default_assignee
		if cat.category_group and not self.complaint_type:
			self.complaint_type = cat.category_group

	def set_due_date(self):
		"""Due date = complaint date + category days (or by severity).
		Only on new entries, category change or reopen, so old records are never back-dated into escalation."""
		if self.status not in OPEN_STATES or self.entry_type != "Complaint":
			return
		if not (self.is_new() or self.has_value_changed("category") or self.flags.reopened):
			return
		if self.is_new() and self.due_date:
			return  # typed by user
		days = None
		if self.category:
			days = frappe.get_cached_value("Complaint Category", self.category, "resolution_days")
		if days is None:
			days = DAYS_BY_SEVERITY.get(self.severity_level, 2)
		self.due_date = add_days(getdate(self.date_of_complaint or nowdate()), days or 0)

	def auto_assign_status(self):
		if not self.status:
			self.status = "Open"
		if self.assigned_user and self.has_value_changed("assigned_user"):
			self.assigned_on = now_datetime()
		# a new record must start in the workflow's first state; after_insert moves it on
		if self.status == "Open" and self.assigned_user and not self.is_new():
			self.status = "Assigned"

	def after_insert(self):
		if self.status == "Open" and self.assigned_user:
			# not db_set: it reloads _doc_before_save, which would hide the assignee change from on_update
			frappe.db.set_value(self.doctype, self.name, "status", "Assigned", update_modified=False)
			self.status = "Assigned"

	# ---------------------------------------------------------------- workflow rules
	def on_status_change(self):
		"""Checks + stamps for each workflow move. The Workflow decides who may move; this decides what's required."""
		if not self.has_value_changed("status"):
			return
		prev = self.get_doc_before_save()
		before = prev.status if prev else None
		now, user = now_datetime(), frappe.session.user
		is_complaint = self.entry_type == "Complaint"

		if self.status == "Pending Approval":
			if is_complaint and not (self.action_taken and self.resolution_type):
				frappe.throw(_("Fill <b>Action Taken</b> and <b>Resolution Type</b> before submitting the resolution"))
			self.resolved_by, self.resolved_on = user, now
			self.resolution_hours = round(time_diff_in_hours(now, self.complaint_datetime()), 1)

		elif self.status == "Accounts Approval":
			self.approved_by, self.approved_on = user, now

		elif self.status == "Resolved":
			if before == "Accounts Approval":
				self.accounts_approved_by, self.accounts_approved_on = user, now
			else:
				self.approved_by, self.approved_on = user, now

		elif self.status == "Closed":
			self.closed_by, self.closed_on = user, now

		elif self.status == "Rejected":
			if not self.approver_remarks:
				frappe.throw(_("Write the reason in <b>Approver Remarks</b> before rejecting"))
			self.closed_by, self.closed_on = user, now

		elif self.status == "Assigned" and before in ("Pending Approval", "Accounts Approval"):
			# sent back by approver
			if not self.approver_remarks:
				frappe.throw(_("Write what needs fixing in <b>Approver Remarks</b> before sending back"))
			self.clear("resolved_by", "resolved_on", "resolution_hours", "approved_by", "approved_on")

		elif self.status == "Assigned" and before in DONE_STATES:
			# reopened
			self.clear(
				"resolved_by", "resolved_on", "resolution_hours", "approved_by", "approved_on",
				"accounts_approved_by", "accounts_approved_on", "closed_by", "closed_on",
				"customer_satisfied", "closing_remarks", "escalated", "escalated_to", "due_date",
			)
			self.flags.reopened = True
			self.set_due_date()

	def clear(self, *fields):
		for f in fields:
			self.set(f, 0 if self.meta.get_field(f).fieldtype in ("Check", "Float") else None)

	def complaint_datetime(self):
		return get_datetime(f"{self.date_of_complaint} {self.time_of_complaint or '00:00:00'}")

	def assign_user(self, user, description):
		if not frappe.db.exists("User", {"name": user, "enabled": 1}):
			return
		try:
			add_assignment({
				"doctype": self.doctype, "name": self.name, "assign_to": [user], "description": description,
				"date": self.due_date, "priority": "High" if self.severity_level == "Critical" else "Medium",
			})
		except DuplicateToDoError:
			pass


def normalise_phone(value):
	"""Phone field needs a country code. Customer records often hold '9876543210' / '09876543210' / '919876543210'.
	A bare '+91' (the form default) counts as empty."""
	v = (value or "").strip()
	if v in ("", "+91", "+91-"):
		return None
	if v.startswith("+"):
		return v
	digits = "".join(ch for ch in v if ch.isdigit())
	if len(digits) == 11 and digits.startswith("0"):
		digits = digits[1:]
	elif len(digits) == 12 and digits.startswith("91"):
		digits = digits[2:]
	return f"+91-{digits}" if len(digits) == 10 else None  # unusable number: drop it rather than block the save


# -------------------------------------------------------------------- new-form defaults
@frappe.whitelist()
def get_complaint_defaults():
	"""For the desk form: the caller's own Employee record, and whether their permission on complaints is
	'only if creator' (staff raising their own) rather than full (CS / managers logging for others).
	Only a convenience default - it does not change what anyone can access."""
	from frappe.permissions import get_role_permissions

	perms = get_role_permissions(frappe.get_meta("Customer Complaint"))
	only_own = bool(perms.get("has_if_owner_enabled")) and not perms.get("read")
	emp = frappe.db.get_value("Employee", {"user_id": frappe.session.user, "status": "Active"},
		["name", "employee_name"], as_dict=True)
	return {"only_own": only_own, "employee": emp.name if emp else None, "employee_name": emp.employee_name if emp else None}


# -------------------------------------------------------------------- list view counters
DASH_VERSION_KEY = "complaint_dashboard_version"


def dashboard_data_version():
	"""Changes whenever any complaint changes; dashboard caches are keyed on it."""
	v = frappe.cache.get_value(DASH_VERSION_KEY)
	if not v:
		v = frappe.generate_hash(length=10)
		frappe.cache.set_value(DASH_VERSION_KEY, v)
	return v


def _bump_dashboard_version():
	frappe.cache.set_value(DASH_VERSION_KEY, frappe.generate_hash(length=10))


def notify_counters():
	"""A complaint changed: invalidate dashboard caches and tell open lists / dashboards (after commit,
	so nobody can cache or read half-saved data)."""
	frappe.db.after_commit.add(_bump_dashboard_version)
	frappe.publish_realtime("complaint_counters_stale", doctype="Customer Complaint", after_commit=True)


@frappe.whitelist()
def get_list_counters():
	"""All list-view counters in ONE indexed query.
	Only active rows are read (pending states + today's), so cost stays flat as history grows.
	Uses the list's own permission conditions (role perms, if-owner, shares, confidential rule)."""
	from frappe.model.db_query import DatabaseQuery

	match = DatabaseQuery("Customer Complaint").build_match_conditions()
	roles = set(frappe.get_roles())
	approval_states = [
		s for s, r in (("Pending Approval", "Complaint Manager"), ("Accounts Approval", "Complaint Accounts Approver"))
		if r in roles or "System Manager" in roles
	]
	values = {"today": nowdate(), "user": frappe.session.user, "backlog": BACKLOG_STATES, "mine_states": OPEN_STATES,
		"approval_states": approval_states or [""]}
	row = frappe.db.sql(
		f"""SELECT
			SUM(date_of_complaint = %(today)s) AS today,
			SUM(status = 'Open') AS open,
			SUM(status = 'Assigned') AS in_process,
			SUM(status IN ('Pending Approval', 'Accounts Approval')) AS approval,
			SUM(status IN %(mine_states)s AND due_date < %(today)s) AS overdue,
			SUM(status IN %(mine_states)s AND assigned_user = %(user)s) AS mine,
			SUM(status IN %(approval_states)s) AS my_approval
		FROM `tabCustomer Complaint`
		WHERE (status IN %(backlog)s OR date_of_complaint = %(today)s){" AND " + match if match else ""}""",
		values,
		as_dict=True,
	)[0]
	out = {k: int(v or 0) for k, v in row.items()}
	out["approval_states"] = approval_states
	return out


# -------------------------------------------------------------------- daily escalation
def escalate_overdue():
	"""Daily: flag open complaints past due date (one UPDATE) and notify the category's escalation user."""
	rows = frappe.get_all(
		"Customer Complaint",
		# "is set" is required: Frappe treats an empty date as 0001-01-01 in "<" filters
		filters=[["status", "in", OPEN_STATES], ["due_date", "is", "set"], ["due_date", "<", nowdate()], ["escalated", "=", 0]],
		fields=["name", "category", "due_date", "severity_level", "raised_by_name", "complaint_type", "internal_type", "issue_type", "complaint_from"],
	)
	if not rows:
		return
	escalate_to = dict(frappe.get_all("Complaint Category", {"escalate_to": ["is", "set"]}, ["name", "escalate_to"], as_list=True))
	cc = frappe.qb.DocType("Customer Complaint")
	frappe.qb.update(cc).set(cc.escalated, 1).where(cc.name.isin([r.name for r in rows])).run()
	for r in rows:
		to = escalate_to.get(r.category)
		due = frappe.format(r.due_date, "Date")
		if to:
			frappe.db.set_value("Customer Complaint", r.name, "escalated_to", to, update_modified=False)
		frappe.get_doc({"doctype": "Comment", "comment_type": "Info", "reference_doctype": "Customer Complaint",
			"reference_name": r.name, "content": _("Escalated: past due date {0}").format(due)}).insert(ignore_permissions=True)
		if to and frappe.db.exists("User", {"name": to, "enabled": 1}):
			what = {"Employee": r.internal_type, "Customer": r.complaint_type}.get(r.complaint_from, r.issue_type)
			try:
				add_assignment({"doctype": "Customer Complaint", "name": r.name, "assign_to": [to], "date": r.due_date,
					"description": _("ESCALATED (due {0}): {1}").format(due, " - ".join(filter(None, [r.raised_by_name, what]))),
					"priority": "High"})
			except DuplicateToDoError:
				pass
	notify_counters()
	frappe.db.commit()
