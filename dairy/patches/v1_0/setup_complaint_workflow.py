import frappe

DT = "Customer Complaint"
WORKFLOW = "Customer Complaint Workflow"
CS = "BDF Customer Complaint Viewer"  # existing Live role (Ranjana, Customer Care...): logs, assigns, closes
HANDLER, MANAGER, ACCOUNTS = "Complaint Handler", "Complaint Manager", "Complaint Accounts Approver"
ACC = "doc.resolution_type in ('Refund', 'Credit Note')"
FEEDBACK = "doc.entry_type != 'Complaint'"

HR = "HR Manager"  # handles employee complaints
STATES = [  # state, style, roles that may edit in this state
	("Open", "Warning", [CS, MANAGER, HR]),
	("Assigned", "Primary", [HANDLER, CS, MANAGER, HR]),
	("Pending Approval", "Info", [MANAGER]),
	("Accounts Approval", "Info", [ACCOUNTS]),
	("Resolved", "Success", [CS, MANAGER, HR]),
	("Closed", "Inverse", [MANAGER]),
	("Rejected", "Danger", [MANAGER]),
]
TRANSITIONS = [  # from, action, to, roles, condition
	("Open", "Assign", "Assigned", [CS, MANAGER, HR], None),
	("Open", "Reject", "Rejected", [MANAGER], None),
	("Open", "Close", "Closed", [CS, MANAGER, HR], FEEDBACK),
	("Assigned", "Submit Resolution", "Pending Approval", [HANDLER, CS, MANAGER, HR], None),
	("Assigned", "Close", "Closed", [CS, MANAGER, HR], FEEDBACK),
	("Assigned", "Reject", "Rejected", [MANAGER], None),
	("Pending Approval", "Approve", "Accounts Approval", [MANAGER], ACC),
	("Pending Approval", "Approve", "Resolved", [MANAGER], f"not ({ACC})"),
	("Pending Approval", "Send Back", "Assigned", [MANAGER], None),
	("Accounts Approval", "Approve", "Resolved", [ACCOUNTS], None),
	("Accounts Approval", "Send Back", "Assigned", [ACCOUNTS], None),
	("Resolved", "Close", "Closed", [CS, MANAGER, HR], None),
	("Resolved", "Reopen", "Assigned", [CS, MANAGER, HR], None),
	("Closed", "Reopen", "Assigned", [MANAGER], None),
]
# Access is NOT granted here. Roles are created empty; what each role may do is set by the team in
# Role Permission Manager (Customer Complaint, Complaint Category) and Role Permission for Page and Report.


def execute():
	make_roles()
	make_masters()
	backfill()
	update_list_columns()
	if not frappe.db.exists("Workflow", WORKFLOW):  # never overwrite edits made later in the UI
		make_workflow()


def make_roles():
	for role in (HANDLER, MANAGER, ACCOUNTS):
		if not frappe.db.exists("Role", role):
			frappe.get_doc({"doctype": "Role", "role_name": role, "desk_access": 1}).insert(ignore_permissions=True)


def make_masters():
	for state, style, _roles in STATES:
		if not frappe.db.exists("Workflow State", state):
			frappe.get_doc({"doctype": "Workflow State", "workflow_state_name": state, "style": style}).insert(ignore_permissions=True)
	for action in {t[1] for t in TRANSITIONS}:
		if not frappe.db.exists("Workflow Action Master", action):
			frappe.get_doc({"doctype": "Workflow Action Master", "workflow_action_name": action}).insert(ignore_permissions=True)


def backfill():
	frappe.db.sql("UPDATE `tabCustomer Complaint` SET complaint_from = 'Customer' WHERE IFNULL(complaint_from, '') = ''")
	frappe.db.sql("""
		UPDATE `tabCustomer Complaint` SET raised_by_name = name_of_a_customer
		WHERE IFNULL(raised_by_name, '') = '' AND complaint_from = 'Customer'
	""")


def make_workflow():
	wf = frappe.new_doc("Workflow")
	wf.workflow_name = WORKFLOW
	wf.document_type = DT
	wf.workflow_state_field = "status"
	wf.is_active = 1
	wf.send_email_alert = 0
	for state, _style, roles in STATES:
		for role in roles:
			wf.append("states", {"state": state, "doc_status": "0", "allow_edit": role})
	for frm, action, to, roles, cond in TRANSITIONS:
		for role in roles:
			wf.append("transitions", {
				"state": frm, "action": action, "next_state": to, "allowed": role,
				"allow_self_approval": 1, "condition": cond,
			})
	wf.insert(ignore_permissions=True)


def update_list_columns():
	"""Live's List View Settings shows 'Name of a Customer' (empty for employee complaints): show 'Raised By' + 'From'.
	Only touched if still exactly the 2026-07-31 setup, so later UI changes are never overwritten."""
	old = [
		{"fieldname": "name", "label": "ID"}, {"fieldname": "status_field", "label": "Status"},
		{"fieldname": "complaint_id", "label": "Complaint ID"}, {"fieldname": "name_of_a_customer", "label": "Name of a Customer"},
		{"fieldname": "type_of_customer", "label": "Type of Customer "},
	]
	if not frappe.db.exists("List View Settings", DT):
		return
	current = frappe.parse_json(frappe.db.get_value("List View Settings", DT, "fields") or "[]")
	if current != old:
		return
	new = [
		{"fieldname": "name", "label": "ID"}, {"fieldname": "status_field", "label": "Status"},
		{"fieldname": "raised_by_name", "label": "Raised By"}, {"fieldname": "complaint_from", "label": "Complaint From"},
		{"fieldname": "complaint_id", "label": "Complaint ID"},
	]
	frappe.db.set_value("List View Settings", DT, "fields", frappe.as_json(new, indent=None), update_modified=False)
