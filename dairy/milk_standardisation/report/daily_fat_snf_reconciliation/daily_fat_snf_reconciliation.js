// Copyright (c) 2026, BDF and contributors
// For license information, please see license.txt

frappe.query_reports["Daily FAT SNF Reconciliation"] = {
	filters: [
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1,
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -7) },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1,
			default: frappe.datetime.get_today() },
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
			default: frappe.defaults.get_user_default("Company") },
		{ fieldname: "silo", label: __("Silo"), fieldtype: "Link", options: "Warehouse",
			get_query: () => ({ filters: { custom_is_milk_silo: 1, is_group: 0 } }) },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		// A gap between the lab's dip and the ledger is the day's loss or gain.
		if (["qty_gap", "fat_gap"].includes(column.fieldname) && data && flt(data[column.fieldname])) {
			const colour = flt(data[column.fieldname]) < 0 ? "var(--red-600)" : "var(--green-600)";
			value = `<span style="color:${colour}">${value}</span>`;
		}
		return value;
	},
};
