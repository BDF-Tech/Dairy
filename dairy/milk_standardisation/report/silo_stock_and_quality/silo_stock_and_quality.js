// Copyright (c) 2026, BDF and contributors
// For license information, please see license.txt

frappe.query_reports["Silo Stock and Quality"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
			default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "silo", label: __("Silo"), fieldtype: "Link", options: "Warehouse",
			get_query: () => ({ filters: { custom_is_milk_silo: 1, is_group: 0 } }) },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		// Flag a lab reading that has drifted from the ERP's figure.
		if (column.fieldname === "fat_difference" && data && Math.abs(flt(data.fat_difference)) > 0.2) {
			value = `<span style="color:var(--orange-600)">${value}</span>`;
		}
		if (column.fieldname === "full_pct" && data && flt(data.full_pct) > 90) {
			value = `<span style="color:var(--red-600)">${value}</span>`;
		}
		return value;
	},
};
