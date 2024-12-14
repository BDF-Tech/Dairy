frappe.query_reports["Sales Invoice Summery"] = {
    "filters": [
        {
            "fieldname": "from_date",
            "label": __("From Date"),
            "fieldtype": "Date",
            "reqd": 1,
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "width": "80px"
        },
        {
            "fieldname": "to_date",
            "label": __("To Date"),
            "fieldtype": "Date",
            "reqd": 1,
            "default": frappe.datetime.get_today(),
            "width": "80px"
        },  
        // {
        //     "fieldname": "interval",
        //     "label": __("Interval"),
        //     "fieldtype": "Select",
        //     "options": "\nWeekly\nMonthly\nQuarterly\nYearly",
        //     "default": "Weekly",
        //     "reqd": 1,
        //     "width": "80px"
        // }
        {
            "fieldname": "set_warehouse",
            "label": __("Warehouse"),
            "fieldtype": "Link",
            "options": "Warehouse"
        },
        {
            "fieldname": "route",
            "label": __("Route"),
            "fieldtype": "Link",
            "options": "Route Master"
        }
    ]
};




// // Copyright (c) 2024, Dexciss Technology Pvt Ltd and contributors
// // For license information, please see license.txt
// /* eslint-disable */

// frappe.query_reports["Sales Invoice Summery"] = {
// 	"filters": [
// 		{
// 			"fieldname":"from_date",
// 			"label": __("From Date"),
// 			"fieldtype": "Date",
// 			"width": "80",
// 			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
// 		},
// 		{ 
// 			"fieldname":"to_date",
// 			"label": __("To Date"),
// 			"fieldtype": "Date",
// 			"width": "80",
// 			"default": frappe.datetime.get_today()
// 		},
// 		{
// 			"fieldname": "route",
// 			"label": __("Route Wise"),
// 			"fieldtype": "Link",
// 			"options": "Route Master",
// 			"width": "100",
// 		},
// 		{
// 			"fieldname":"set_warehouse",
// 			"label": __("Warehouse"),
// 			"fieldtype": "Select",
// 			"options": ["","Depo Warehouse - BDF", "Dispatch Cold Room - BDF"],
// 			"width": "100",
// 		},
// 		{
// 			fieldname: "range",
// 			label: __("Range"),
// 			fieldtype: "Select",
// 			options: [
// 				{ value: "Weekly", label: __("Weekly") },
// 				{ value: "Monthly", label: __("Monthly") },
// 				{ value: "Quarterly", label: __("Quarterly") },
// 				{ value: "Yearly", label: __("Yearly") },
// 			],
// 			default: "Monthly",
// 			reqd: 1,
// 		}		
// 	]
// }
