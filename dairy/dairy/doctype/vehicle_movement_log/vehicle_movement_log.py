import frappe
from frappe.model.document import Document
from frappe.utils import getdate, nowdate
from frappe import _

class VehicleMovementLog(Document):
    def validate(self):
        # 1. Existing Compliance Logic
        self.check_vehicle_documents()

    def on_update(self):
        """
        Triggered every time the document is saved.
        Handles the movement of loose crates when status changes to 'Gate Check'.
        """
        # Logic: Move stock ONLY when status is Gate Check AND movement hasn't happened yet
        if self.status == "Gate Check" and not self.custom_stock_entry:
            self.create_stock_entry_for_loose_items()

    def check_vehicle_documents(self):
        if not self.vehicle:
            return

        vehicle = frappe.get_doc("Vehicle", self.vehicle)
        required_fields = {
            "insurance_company": "Insurance Company",
            "policy_no": "Policy No",
            "custom_rc_no": "RC Number",
            "custom_pollution": "Pollution Certificate No",
            "custom_pollution_validity": "Pollution Validity Date",
            "custom_fitness": "Fitness Certificate No",
            "custom_fitness_validity": "Fitness Validity Date",
            "start_date": "Insurance Start Date",
            "end_date": "Insurance End Date"
        }

        errors = []
        today = getdate(nowdate())

        for field, label in required_fields.items():
            if not vehicle.get(field):
                errors.append(f"• <b>{label}</b> is missing.")

        if vehicle.get("end_date") and getdate(vehicle.end_date) < today:
            errors.append(f"• <b>Insurance</b> expired on {vehicle.end_date}.")

        if vehicle.get("custom_fitness_validity") and getdate(vehicle.custom_fitness_validity) < today:
            errors.append(f"• <b>Fitness Certificate</b> expired on {vehicle.custom_fitness_validity}.")
            
        if vehicle.get("custom_pollution_validity") and getdate(vehicle.custom_pollution_validity) < today:
            errors.append(f"• <b>Pollution Certificate</b> expired on {vehicle.custom_pollution_validity}.")

        if errors:
            frappe.throw(
                title="Vehicle Compliance Alert",
                msg=f"Cannot save Trip. <b>{self.vehicle}</b> has missing or expired documents:<br><br>" + "<br>".join(errors) + "<br><br>Please update the Vehicle Master."
            )

    @frappe.whitelist()
    def get_invoices(self):
        """
        Fetches Route-wise Invoices and calculates Crate/Can counts
        """
        if not self.date_and_time or not self.route:
            frappe.throw(_("Please select both Date and Route before fetching invoices."))

        target_date = getdate(self.date_and_time)
        self.set("route_wise_sales_invoice", [])

        invoices = frappe.get_all("Sales Invoice",
            filters={"posting_date": target_date, "route": self.route, "docstatus": 1},
            fields=["name", "customer_name"]
        )

        if not invoices:
            frappe.msgprint(_("No matching Invoices found."))
            return

        for inv in invoices:
            item_data = frappe.get_all("Sales Invoice Item",
                filters={"parent": inv.name, "packaging_item": ["in", ["CRT007", "CAN004"]]},
                fields=["packaging_item", "qty"]
            )

            crates, cans = 0, 0
            for item in item_data:
                if item.packaging_item == "CRT007":
                    crates += item.qty
                elif item.packaging_item == "CAN004":
                    cans += item.qty

            self.append("route_wise_sales_invoice", {
                "sales_invoice_id": inv.name,
                "customer_name": inv.customer_name,
                "crates_count": crates,
                "cans_count": cans
            })
        
        self.save()
        return True

    def create_stock_entry_for_loose_items(self):
        """
        Creates a Material Transfer for items entered in the 'loose_crate' table.
        """
        if not self.loose_crate:
            return

        se = frappe.new_doc("Stock Entry")
        se.stock_entry_type = "Material Transfer"
        se.from_warehouse = "Dispatch Cold Room - BDF"
        se.to_warehouse = "crate in transit - BDF"
        se.remarks = f"Loose Packaging for Vehicle Log: {self.name}"
        
        item_added = False
        for row in self.loose_crate:
            if row.qty > 0:
                se.append("items", {
                    "item_code": row.item_code,
                    "qty": row.qty,
                    "s_warehouse": "Dispatch Cold Room - BDF",
                    "t_warehouse": "crate in transit - BDF",
                    "uom": frappe.db.get_value("Item", row.item_code, "stock_uom"),
                    "conversion_factor": 1
                })
                item_added = True

        if item_added:
            se.insert()
            se.submit()
            # Update the reference so it doesn't run again
            self.db_set("custom_stock_entry", se.name)
            frappe.msgprint(_("Stock Entry {0} created for Loose Items").format(se.name))