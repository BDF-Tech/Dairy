import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate

class VehicleMovementLog(Document):
	def validate(self):
		self.check_vehicle_documents()

	def check_vehicle_documents(self):
		if not self.vehicle:
			return

		# 1. Fetch the linked Vehicle Document
		vehicle = frappe.get_doc("Vehicle", self.vehicle)
		
		# 2. Define the mandatory fields
		required_fields = {
			"insurance_company": "Insurance Company",
			"policy_no": "Policy No",
			"custom_rc_no": "RC Number",
			"custom_pollution": "Pollution Certificate No",
			"custom_pollution_validity": "Pollution Validity Date",  # Added this
			"custom_fitness": "Fitness Certificate No",
			"custom_fitness_validity": "Fitness Validity Date",
			"start_date": "Insurance Start Date",
			"end_date": "Insurance End Date"
		}

		errors = []
		today = getdate(nowdate())

		# 3. Check for Empty Fields
		for field, label in required_fields.items():
			if not vehicle.get(field):
				errors.append(f"• <b>{label}</b> is missing.")

		# 4. Check for Expired Dates (only if the date exists)
		
		# Check Insurance Expiry
		if vehicle.get("end_date") and getdate(vehicle.end_date) < today:
			errors.append(f"• <b>Insurance</b> expired on {vehicle.end_date}.")

		# Check Fitness Expiry
		if vehicle.get("custom_fitness_validity") and getdate(vehicle.custom_fitness_validity) < today:
			errors.append(f"• <b>Fitness Certificate</b> expired on {vehicle.custom_fitness_validity}.")
			
		# Check Pollution Expiry (Added this)
		if vehicle.get("custom_pollution_validity") and getdate(vehicle.custom_pollution_validity) < today:
			errors.append(f"• <b>Pollution Certificate</b> expired on {vehicle.custom_pollution_validity}.")

		# 5. Stop Save if errors exist
		if errors:
			frappe.throw(
				title="Vehicle Compliance Alert",
				msg=f"Cannot save Trip. <b>{self.vehicle}</b> has missing or expired documents:<br><br>" + "<br>".join(errors) + "<br><br>Please update the Vehicle Master."
			)