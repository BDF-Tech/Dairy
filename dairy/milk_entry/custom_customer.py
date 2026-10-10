import re

import frappe
from frappe import _

# FSSAI licence / registration number: 14 digits.
#   1st digit      1 = Licence, 2 = Registration
#   2nd-3rd        state code
#   4th-5th        year of issue
#   6th-8th        enrolling office
#   9th-14th       licence number
FSSAI_PATTERN = re.compile(r"^[12]\d{13}$")


def validate_food_license(doc, method=None):
	"""Customer.validate — keep `food_license_number` a well-formed FSSAI number.

	Only checked when the number is new or changed, so an old malformed value
	does not block unrelated edits to the customer until someone corrects it.
	"""
	if not doc.get("food_license_number"):
		return

	# Allow people to paste "20519 049 000128" or "20519-049-000128".
	cleaned = re.sub(r"[\s\-]", "", doc.food_license_number)
	doc.food_license_number = cleaned

	if not (doc.is_new() or doc.has_value_changed("food_license_number")):
		return

	if not FSSAI_PATTERN.match(cleaned):
		frappe.throw(
			_(
				"Food License Number <b>{0}</b> is not a valid FSSAI number. It must be exactly "
				"14 digits and start with 1 (Licence) or 2 (Registration) — you entered {1} characters."
			).format(frappe.bold(cleaned), len(cleaned)),
			title=_("Invalid FSSAI Number"),
		)

	duplicates = frappe.get_all(
		"Customer",
		filters={"food_license_number": cleaned, "name": ["!=", doc.name]},
		pluck="name",
	)
	if duplicates:
		frappe.msgprint(
			_("FSSAI number {0} is also used on: {1}").format(
				frappe.bold(cleaned), ", ".join(frappe.bold(d) for d in duplicates)
			),
			title=_("Duplicate FSSAI Number"),
			indicator="orange",
		)
