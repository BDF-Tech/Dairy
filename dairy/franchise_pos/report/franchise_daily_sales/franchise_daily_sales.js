frappe.query_reports["Franchise Daily Sales"] = {
	filters: [
		{ fieldname: "franchise", label: __("Franchise"), fieldtype: "Link", options: "Customer",
			get_query: () => ({ filters: { custom_franchise_pos: 1 } }) },
		{ fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.add_days(frappe.datetime.get_today(), -6), reqd: 1 },
		{ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: frappe.datetime.get_today(), reqd: 1 },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (column.fieldname === "day_closed" && data && data.day_closed === __("No")) {
			value = `<span style="color: var(--red-500)">${value}</span>`;
		}
		return value;
	},
};
