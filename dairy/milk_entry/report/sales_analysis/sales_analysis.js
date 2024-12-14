// Copyright (c) 2016, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Sales Analysis"] = {
	"filters": [

//		{
//			"fieldname":"based_on",
//			"label": __("Based On"),
//			"fieldtype": "Select",
//			"options": [
//				{ "value": "item_group", "label": __("Item Group") }
//			],
//			"default": "Item"
//		},
        {
			"fieldname":"item_group",
			"label": __("Item Group"),
			"fieldtype": "Link",
			"options": "Item Group"
		},
		{
			"fieldname":"fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options":'Fiscal Year',
			"default": frappe.sys_defaults.fiscal_year
		},
		{
			"fieldname":"warehouse",
			"label": __("Warehouse"),
			"fieldtype": "Link",
			"options": "Warehouse"
		},
		{
			"fieldname":"shift",
			"label": __("Delivery Shift"),
			"fieldtype": "Select",
			"options": [
				{ "value": "Morning", "label": __("Morning") },
				{ "value": "Evening", "label": __("Evening") }
			],
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date"
		},
		{
			"fieldname":"territory",
			"label": __("Territory"),
			"fieldtype": "Link",
			"options": "Territory"
		},


	]
};
