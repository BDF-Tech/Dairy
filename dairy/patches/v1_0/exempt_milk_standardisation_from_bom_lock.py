# Copyright (c) 2026, BDF and contributors
# For license information, please see license.txt

"""Let Milk Standardisation submit its Manufacture entry.

The site's "bom item lock" Server Script rejects a Manufacture entry that leaves out
any BOM item, unless the user is on a short allow-list. A standardisation batch is
built from the blend sheet, not from BOM ratios, so it routinely uses only some of the
BOM's items. This adds one condition so those entries pass, and leaves the check in
place for every other Manufacture entry.

The script lives only in the database, so it is patched here rather than in code.
"""

import frappe

SCRIPT = "bom item lock"
OLD = 'if not is_privileged_user and doc.stock_entry_type == "Manufacture" and doc.bom_no:'
NEW = ('if (not is_privileged_user and not doc.custom_milk_standardization\n'
	'        and doc.stock_entry_type == "Manufacture" and doc.bom_no):')


def execute():
	if not frappe.db.exists("Server Script", SCRIPT):
		return

	doc = frappe.get_doc("Server Script", SCRIPT)
	if "custom_milk_standardization" in (doc.script or ""):
		return
	if OLD not in (doc.script or ""):
		frappe.log_error(
			title="bom item lock not patched",
			message="The expected condition was not found; Milk Standardisation submits may be blocked.",
		)
		return

	doc.script = doc.script.replace(OLD, NEW)
	doc.save(ignore_permissions=True)
