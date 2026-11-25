import frappe


def execute():
	"""Defaults for the new Day Close / Reorder settings. Milk is short-life: no safety margin."""
	s = frappe.get_single("Franchise POS Settings")
	changed = False
	for field, value in (("auto_close_after_days", 2), ("reorder_days", 7), ("safety_percent", 10)):
		if s.get(field) is None:
			s.set(field, value)
			changed = True
	if not s.reorder_groups and frappe.db.exists("Item Group", "Milk FG"):
		s.append("reorder_groups", {"item_group": "Milk FG", "safety_percent": 0})
		changed = True
	if changed:
		s.flags.ignore_permissions = True
		s.flags.ignore_mandatory = True
		s.save()
