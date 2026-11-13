import re

import frappe


def execute():
	"""Complaint ID (CI-###) is now automatic. Start the 'CI-' series after the highest number the CS team
	already typed by hand (e.g. ci-089 -> next is CI-090). Never moves the series backwards."""
	if not frappe.db.has_column("Customer Complaint", "complaint_id"):
		return
	highest = 0
	for (cid,) in frappe.db.sql("SELECT complaint_id FROM `tabCustomer Complaint` WHERE complaint_id LIKE 'CI%%'"):
		m = re.match(r"^\s*CI\s*-?\s*(\d+)\s*$", cid or "", re.IGNORECASE)
		if m:
			highest = max(highest, int(m.group(1)))
	frappe.db.sql(
		"""INSERT INTO `tabSeries` (name, current) VALUES ('CI-', %s)
		ON DUPLICATE KEY UPDATE current = GREATEST(current, VALUES(current))""",
		highest,
	)
