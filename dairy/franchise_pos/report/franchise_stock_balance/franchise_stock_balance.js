frappe.query_reports["Franchise Stock Balance"] = {
	filters: [
		{ fieldname: "franchise", label: __("Franchise"), fieldtype: "Link", options: "Customer",
			get_query: () => ({ filters: { custom_franchise_pos: 1 } }) },
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "item_code", label: __("Item"), fieldtype: "Link", options: "Item" },
	],
};
