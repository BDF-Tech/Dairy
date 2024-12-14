// Copyright (c) 2023, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Employee Outstanding"] = {
	"filters": [
		{
			fieldname:"employee_id",
			label:"Employee ID",
			fieldtype:"Link",
			options:"Employee"
		},
		{
			fieldname:"from_date",
			label:"From Date",
			fieldtype:"Date",
			reqd:1, 
			default:frappe.datetime.get_today()
		},
		{
			fieldname:"to_date",
			label:"To Date",
			fieldtype:"Date",
			reqd:1, 
			default:frappe.datetime.get_today()
		}
	]
};
