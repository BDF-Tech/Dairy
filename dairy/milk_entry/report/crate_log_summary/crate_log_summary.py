# Copyright (c) 2023, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _, _dict


TRANSLATIONS = frappe._dict()


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters, columns)
	return columns, data



def get_columns():
	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Datetime", "width": 150},
		{"label": _("Customer Name"),"fieldname":"customer_name","fieldtype":"Data","width": 150},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "data", "width": 150},
		{"label": _("Route"), "fieldname": "route", "fieldtype": "Data", "width": 150},
		{"label": _("Delivery Shift"), "fieldname": "shift", "fieldtype": "Data", "width": 150},
		{"label": _("Crate Issue"), "fieldname": "crate_issue", "fieldtype": "int", "width": 150},
		{"label": _("Crate Return"), "fieldname": "crate_return", "fieldtype": "int", "width": 150},
		{"label": _("Crate Balance"), "fieldname": "crate_balance", "fieldtype": "int", "width": 150},
	]

	return columns


def get_data(filters, columns):
	data =[]
	from_date = filters.get('from_date')
	to_date = filters.get('to_date')
	customer = filters.get('customer')
	route = filters.get('route')
	
	if customer:
		result = frappe.db.sql("""select cl.date,cl.shift,c.customer_name,cl.customer,cl.route,cl.crate_issue,cl.crate_return,cl.crate_balance
										from `tabCrate Log` cl join `tabCustomer` c on  cl.customer=c.name
										where 
										customer = '{0}'
										and date between '{1}' and  '{2}'
										""".format(customer,from_date,to_date ), as_dict=True)
		data = result
		return data

	else:
		result = frappe.db.sql("""select cl.date,c.customer_name,cl.shift,cl.customer,cl.route,cl.crate_issue,cl.crate_return,cl.crate_balance
										from `tabCrate Log`cl join `tabCustomer` c on cl.customer=c.name 
										where 
										date between '{0}' and '{1}'
										""".format(from_date,to_date,customer ), as_dict=True)
		data = result
		return data


