// Copyright (c) 2016, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Milk Entry Trends"] = {
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
				{ "value": "Daily", "label": __("Daily") },
				{ "value": "Monthly", "label": __("Monthly") },
				{ "value": "Quarterly", "label": __("Quarterly") },
				{ "value": "Half-Yearly", "label": __("Half-Yearly") },
				{ "value": "Yearly", "label": __("Yearly") }
			],
			"default": "Monthly"
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
			"depends_on":"eval:doc.period == 'Daily'"
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today(),
			"depends_on":"eval:doc.period == 'Daily'"
		},
		{
			"fieldname":"fiscal_year",
			"label": __("Fiscal Year"),
			"fieldtype": "Link",
			"options":'Fiscal Year',
			"reqd": 1,
			"default": frappe.sys_defaults.fiscal_year,
			"depends_on":"eval:doc.period != 'Daily'"
		},
//		{
//			"fieldname":"period_based_on",
//			"label": __("Period based On"),
//			"fieldtype": "Select",
//			"options": [
//				{ "value": "posting_date", "label": __("Posting Date") },
//				{ "value": "bill_date", "label": __("Billing Date") },
//			],
//			"default": "posting_date"
//		},



		{
			"fieldname":"based_on",
			"label": __("Based On"),
			"fieldtype": "Select",
			"options": [
				{ "value": "dcs", "label": __("DCS") },
				{ "value": "milk_type", "label": __("Milk Type") }
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
				{ "value": "member", "label": __("Member")},
				{ "value": "shift", "label": __("Shift")},
			],
			"default": ""
		},
	]
};
