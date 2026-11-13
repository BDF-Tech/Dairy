import frappe


def execute():
	"""Move old custom Customer Complaint records onto the new workflow.
	Old fields are kept as-is; only status and assigned_to change."""
	dt = "Customer Complaint"
	if not frappe.db.table_exists(dt):
		return
	cols = set(frappe.db.get_table_columns(dt))

	# 1. assigned_to -> assigned_user (Frappe core overwrites any field named assigned_to)
	if "assigned_to" in cols:
		frappe.db.sql("""
			UPDATE `tabCustomer Complaint`
			SET assigned_user = assigned_to
			WHERE IFNULL(assigned_to, '') != '' AND IFNULL(assigned_user, '') = ''
		""")

	# 2. old statuses -> new
	frappe.db.sql("""
		UPDATE `tabCustomer Complaint`
		SET status = IF(IFNULL(assigned_user, '') != '', 'Assigned', 'Open')
		WHERE IFNULL(status, '') IN ('', 'New', 'In progress', 'In Progress')
	""")

	# 3. every old record was a complaint
	frappe.db.sql("UPDATE `tabCustomer Complaint` SET entry_type = 'Complaint' WHERE IFNULL(entry_type, '') = ''")

	# 4. old custom DocType State colours (New / In Progress) no longer apply
	frappe.db.delete("DocType State", {"parent": dt, "title": ("in", ["New", "In Progress"])})
