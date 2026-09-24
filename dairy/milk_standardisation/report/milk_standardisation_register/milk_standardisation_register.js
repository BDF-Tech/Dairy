// Copyright (c) 2026, BDF and contributors
// For license information, please see license.txt

frappe.query_reports["Milk Standardisation Register"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1,
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -30) },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1,
			default: frappe.datetime.get_today() },
		{ fieldname: "finished_item", label: __("Milk Base"), fieldtype: "Link", options: "Item",
			get_query: () => ({ filters: { item_group: "Semi-Finished Goods" } }) },
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
			default: frappe.defaults.get_user_default("Company") },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (["fat_deviation", "snf_deviation"].includes(column.fieldname) && data) {
			const limit = column.fieldname === "fat_deviation" ? 0.1 : 0.2;
			if (Math.abs(flt(data[column.fieldname])) > limit) {
				value = `<span style="color:var(--orange-600)">${value}</span>`;
			}
		}
		return value;
	},
};
