import frappe

@frappe.whitelist()
def set_child_data(values):
    print("Python method is being called.")
    
    stock_entry = frappe.get_value("Stock Entry", {"stock_entry_type": "Material Transfer", "docstatus": 1}, "name")

    if stock_entry:
        for s in stock_entry:
            child_data = frappe.get_all("Stock Entry Detail", filters={"parent": s.name}, fields=["name", "item_code", "item_name", "uom", "qty"])
            if child_data:
                for i in child_data:
                    # Process child data here
                    pass  # Placeholder, replace with your logic

        # total_arrear_amount = frappe.get_value("Total Arrear Calculated", {"date": ["between", [start_date, end_date]], "employee_id": i.employee}, "arrear_amount")

        # salary_slip = frappe.get_value("Salary Slip", {"payroll_entry": payroll_entry, "employee": i.employee}, "name")

        # if total_arrear_amount:
        #     doc = frappe.get_doc("Salary Slip", salary_slip)
        #     arrear_exists = any(e.salary_component == "Arrear" for e in doc.earnings)

        #     if not arrear_exists:
        #         doc.append("earnings", {
        #             "salary_component": "Arrear",
        #             "amount": total_arrear_amount,
        #         })
        #         doc.save()



                # dairy.dairy.milk_entry.gate_pass_stock_entry.set_child_data
                # sugar_mill.sugar_mill.delivery_order.get_raw_materials