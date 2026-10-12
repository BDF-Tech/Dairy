// Copyright (c) 2026, BDF and contributors
// For license information, please see license.txt

frappe.query_reports["FAT SNF Ledger"] = {
	filters: [
		{ fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
			default: frappe.defaults.get_user_default("Company"), reqd: 1 },
		{ fieldname: "from_date", label: __("From Date"), fieldtype: "Date",
			default: frappe.datetime.add_days(frappe.datetime.get_today(), -7), reqd: 1 },
		{ fieldname: "to_date", label: __("To Date"), fieldtype: "Date",
			default: frappe.datetime.get_today(), reqd: 1 },
		{ fieldname: "warehouse", label: __("Warehouse"), fieldtype: "Link", options: "Warehouse" },
		{ fieldname: "item_code", label: __("Milk Item"), fieldtype: "Link", options: "Item",
			get_query: () => ({ filters: { maintain_fat_snf_clr: 1 } }) },
		{ fieldname: "voucher_type", label: __("Document Type"), fieldtype: "Select",
			options: ["", "Purchase Receipt", "Stock Entry", "Sales Invoice", "Delivery Note",
				"Stock Reconciliation", "Milk Fat Reconciliation"].join("\n") },
		{ fieldname: "silos_only", label: __("Silos Only"), fieldtype: "Check" },
		{ fieldname: "quantity_only", label: __("Hide Quality-only Rows"), fieldtype: "Check",
			description: __("Leave off to include reconciliations, which move no quantity") },
	],
	formatter(value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data);
		if (!data) return value;
		// An opening line, and a correction that moves no milk, both read differently.
		if (data.voucher_type === __("Opening")) {
			value = `<span style="color:var(--text-muted)">${value}</span>`;
		} else if (data.voucher_type === "Milk Fat Reconciliation") {
			value = `<span style="color:var(--blue-600)">${value}</span>`;
		}
		return value;
	},
};
