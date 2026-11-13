frappe.query_reports["Customer Complaint Register"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", default: frappe.datetime.month_start(), reqd: 1 },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "entry_type", label: __("Entry Type"), fieldtype: "Select", options: "\nComplaint\nFeedback\nSuggestion" },
		{ fieldname: "status", label: __("Status"), fieldtype: "Select", options: "\nOpen\nAssigned\nPending Approval\nAccounts Approval\nResolved\nClosed\nRejected\nPending (not yet resolved)\nOverdue" },
		{ fieldname: "complaint_from", label: __("From"), fieldtype: "Select", options: "\nCustomer\nEmployee\nFarmer\nVendor\nOther" },
		{ fieldname: "complaint_type", label: __("Complaint Type"), fieldtype: "Select", options: "\nQuality Issue\nPackaging Issue\nDelivery Issue\nBilling Issue\nService Issue\nOther" },
		{ fieldname: "category", label: __("Category"), fieldtype: "Link", options: "Complaint Category" },
		{ fieldname: "route", label: __("Route"), fieldtype: "Link", options: "Route Master" },
		{ fieldname: "customer_id", label: __("Customer"), fieldtype: "Link", options: "Customer" },
		{ fieldname: "item_code", label: __("Item"), fieldtype: "Link", options: "Item" },
		{ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" },
		{ fieldname: "assigned_user", label: __("Assigned To"), fieldtype: "Link", options: "User" },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (data && column.fieldname === "overdue" && data.overdue === "Yes") value = `<span style="color:var(--red-500);font-weight:600">${value}</span>`;
		return value;
	},
};
