// Copyright (c) 2016, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Milk Entry Detail"] = {
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
			"fieldname":"dcs",
			"label": __("DCS"),
			"fieldtype": "Link",
			"options":'Warehouse',
		},

        {
			"fieldname":"member",
			"label": __("Member"),
			"fieldtype": "Link",
			"options":'Supplier'
		},
		{
			"fieldname":"pricelist",
			"label": __("Pricelist"),
			"fieldtype": "Link",
			"options":'Milk Rate'
		},
		{
			"fieldname":"shift",
			"label": __("Shift"),
			"fieldtype": "Select",
			"options":[
			        { "value": "All", "label": __("") },
			        { "value": "Morning", "label": __("Morning") },
				    { "value": "Evening", "label": __("Evening") },
			],
			"default": "All"
		},
        {
			"fieldname":"milk_type",
			"label": __("Milk Type"),
			"fieldtype": "Select",
			"options":[
			        { "value": "All", "label": __("") },
			        { "value": "Cow", "label": __("Cow Milk") },
				    { "value": "Buf", "label": __("Buffalo Milk") },
				    { "value": "Mix", "label": __("Mix Milk") },
			],
			"default": "All"
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			"default": frappe.datetime.get_today()
		},

//		{
//			"fieldname":"fiscal_year",
//			"label": __("Fiscal Year"),
//			"fieldtype": "Link",
//			"options":'Fiscal Year',
//			"default": frappe.sys_defaults.fiscal_year
//		},
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




//		{
//			"fieldname":"based_on",
//			"label": __("Based On"),
//			"fieldtype": "Select",
//			"options": [
//				{ "value": "Item", "label": __("Item") },
//				{ "value": "Item Group", "label": __("Item Group") },
//				{ "value": "Supplier", "label": __("Supplier") },
//				{ "value": "Supplier Group", "label": __("Supplier Group") },
//				{ "value": "Project", "label": __("Project") }
//			],
//			"default": "Item"
//		},
//		{
//			"fieldname":"group_by",
//			"label": __("Group By"),
//			"fieldtype": "Select",
//			"options": [
//				"",
//				{ "value": "Item", "label": __("Item") },
//				{ "value": "Supplier", "label": __("Supplier") }
//			],
//			"default": ""
//		},


	]
};
