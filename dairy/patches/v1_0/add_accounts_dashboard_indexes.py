# Index that powers the low-load reads of the Accounts Dashboard page.
# Payment Entry ships without any posting_date index, so every date-filtered
# read (this dashboard, and reports generally) full-scans the table. A cheap
# 2-column composite fixes that. Idempotent: add_index skips if it exists.

import frappe


def execute():
	# Dashboard's cash/bank/payment reads filter on posting_date (+ company).
	frappe.db.add_index("Payment Entry", ["posting_date", "company"])
