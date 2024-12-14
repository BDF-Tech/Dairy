// Copyright (c) 2016, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Collection Item Details"] = {
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
            "fieldname":"parent",
            "label": __("Van Collection"),
            "fieldtype": "Link",
            "options": "Van Collection"
        },
        {
            "fieldname":"dcs",
            "label": __("DCS"),
            "fieldtype": "Link",
            "options":'Warehouse',
        },

//         {
//             "fieldname":"gate_pass",
//             "label": __("Gate Pass"),
//             "fieldtype": "Link",
//             "options":'Supplier'
//         },
        {
            "fieldname":"time",
            "label": __("Time"),
            "fieldtype": "Time"
        }
        
        
//         {
//             "fieldname":"shift",
//             "label": __("Shift"),
//             "fieldtype": "Select",
//             "options":[
//                     { "value": "All", "label": __("") },
//                     { "value": "Morning", "label": __("Morning") },
//                     { "value": "Evening", "label": __("Evening") },
//             ],
//             "default": "All"
//         },
//         {
//             "fieldname":"milk_type",
//             "label": __("Milk Type"),
//             "fieldtype": "Select",
//             "options":[
//                     { "value": "All", "label": __("") },
//                     { "value": "Cow", "label": __("Cow Milk") },
//                     { "value": "Buf", "label": __("Buffao Milk") },
//                     { "value": "Mix", "label": __("Mix Milk") },
//             ],
//             "default": "All"
//         },
//         {
//             "fieldname":"from_date",
//             "label": __("From Date"),
//             "fieldtype": "Date",
//             "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1)
//         },
//         {
//             "fieldname":"to_date",
//             "label": __("To Date"),
//             "fieldtype": "Date",
//             "default": frappe.datetime.get_today()
//         }

	]
};
