// Copyright (c) 2023, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt
/* eslint-disable */

frappe.query_reports["Crate Log Summary"] = {

	"filters": [
		{
			"fieldname":"customer",
			"label": __("Customer"),
			"fieldtype": "Link",
			"options": "Customer",
			// "reqd": 1,
			"default": frappe.defaults.get_user_default("Customer")
		},
		{
			"fieldname":"from_date",
			"label": __("From Date"),
			"fieldtype": "Date",
			// "reqd": 0,
			"default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
		},
		{
			"fieldname":"to_date",
			"label": __("To Date"),
			"fieldtype": "Date",
			// "reqd": 0,
			"default": frappe.datetime.get_today(),
		},
		{
			"fieldname":"route",
			"label": __("Route"),
			"fieldtype":"Link",
			"options":"Route Master",
			// "reqd": 1,
			"default":frappe.defaults.get_user_default("Route Master"),
		},

	]
};
