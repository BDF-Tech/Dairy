// Copyright (c) 2016, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Milk Entry vs Van Collection"] = {
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
			"fieldname":"period",
			"label": __("Period"),
			"fieldtype": "Select",
			"options": [
				{ "value": "Monthly", "label": __("Monthly") },
				{ "value": "Quarterly", "label": __("Quarterly") },
				{ "value": "Half-Yearly", "label": __("Half-Yearly") },
				{ "value": "Yearly", "label": __("Yearly") }
			],
			"default": "Monthly"
		},
		// {
		// 	"fieldname":"fiscal_year",
		// 	"label": __("Fiscal Year"),
		// 	"fieldtype": "Link",
		// 	"options":'Fiscal Year',
		// 	"reqd": 1,
		// 	"default": frappe.sys_defaults.fiscal_year
		// },
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
			"fieldname":"based_on",
			"label": __("Based On"),
			"fieldtype": "Select",
			"options": [
				{ "value": "dcs", "label": __("DCS") },
				{ "value": "route", "label": __("Route") },
				{ "value": "vehicle", "label": __("Vehicle") }

			],
			"default": "dcs"
		},
		{
			"fieldname":"group_by",
			"label": __("Group By"),
			"fieldtype": "Select",
			"options": [
				{ "value": "", "label": __("All") },
				{ "value": "dcs", "label": __("DCS") },
				{ "value": "route", "label": __("Route") },
				{ "value": "vehicle", "label": __("Vehicle") }
			],
			"default": ""
		},
	]
};
