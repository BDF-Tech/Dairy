// Copyright (c) 2023, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Member Milk Ledger"] = {
	"filters": [
		{
			"fieldname":"company",
			"label": __("Company"),
			"fieldtype": "Link",
			"options": "Company",
			"reqd": 1,
			"default": frappe.defaults.get_user_default("Company")
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"reqd": 1,
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname":"group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": [" ","DCS","Member","Shift","Date"]
		},
		{
			"fieldname":"member",
			"label": __("Member"),
			"fieldtype": "Link",
			// "reqd": 1,
			"options":"Supplier",
			// "depends_on": "eval: doc.group_by == 'Member'",
		},
		{
			"fieldname":"dcs",
			"label": __("DCS"),
			"fieldtype": "Link",
			// "reqd": 1,
			"options":"Warehouse",
			// "depends_on": "eval: doc.group_by == 'DCS'",
		},
		{
			"fieldname":"shift",
			"label": __("Shift"),
			"fieldtype": "Select",
			// "reqd": 1,
			// "default": frappe.datetime.get_today(),
			"options":[" ","Morning","Evening"],
			// "depends_on": "eval: doc.group_by == 'Shift'",
		},
		

	],

	
};
