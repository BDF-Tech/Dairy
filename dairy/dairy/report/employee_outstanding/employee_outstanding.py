# Copyright (c) 2023, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _

def execute(filters=None):
	data = get_data(filters)
	columns = get_columns()
	return columns, data

def get_columns():
	return[ 
		{
			"filedname":"employee",
			"label":_("Employee"),
			"fieldtype":"Link",
			"options":"Employee",
			"width":250
		},
		{
			"filedname":"employee_name",
			"label":_("Employee Name"),
			"fieldtype":"Data",
			"width":200
		},
		{
			"filedname":"opening_balance",
			"label":_("Opening Balance"),
			"fieldtype":"Currency",
			"width":200
		},
		{
			"filedname":"employee_advance",
			"label":_("Employee Advance"),
			"fieldtype":"Currency",
			"width":200
		},
		{
			"filedname":"payment",
			"label":_("Payment"),
			"fieldtype":"Currency",
			"width":200
		},
		{
			"filedname":"closing_balance",
			"label":_("Closing Balance"),
			"fieldtype":"Currency",
			"width":200
		}
	]

def get_data(filters):
	paid_salary = get_query(filters, "AND je.voucher_type = 'Bank Entry' AND pe.start_date <= '{0}'".format(filters.get("from_date")))
	closing_salary = get_query(filters, "AND je.voucher_type = 'Bank Entry'AND pe.end_date <= '{0}'".format(filters.get("to_date")))
	ts_query = ""
	ap_query = ""
	if filters.get("employee_id"):
		ts_query += "AND ss.employee = '{0}'".format(filters.get("employee_id"))
		ap_query += "AND pe.party = '{0}'".format(filters.get("employee_id"))

	employee = frappe.db.get_list("Employee", {"status":"Active"}, pluck='name')
	total_salary = frappe.db.sql("""
		SELECT
			ss.name,
			ss.employee,
			ss.employee_name,
			SUM(ss.gross_pay) as total_amount,
			SUM(ss.gross_pay) as opening_balance
		FROM
			`tabSalary Slip` ss
		WHERE
			ss.docstatus = 1 AND
			ss.start_date < '{from_date}'
			{ts_query}
		GROUP BY
			employee
	""".format(ts_query=ts_query, from_date=filters.get("from_date"), to_date=filters.get("to_date")),
	as_dict=True)
	total_closing_salary = frappe.db.sql("""
		SELECT
			ss.name,
			ss.employee,
			ss.employee_name,
			SUM(ss.gross_pay) as total_amount,
			SUM(ss.gross_pay) as closing_balance
		FROM
			`tabSalary Slip` ss
		WHERE
			ss.docstatus = 1 AND
			ss.end_date <= '{to_date}'
			{ts_query}
		GROUP BY 
			employee
	""".format(ts_query=ts_query, from_date=filters.get("from_date"), to_date=filters.get("to_date")),
	as_dict=True)
	advance_paid = frappe.db.sql("""
		SELECT
			pe.name,
			pe.party,
			SUM(pe.paid_amount) as employee_advance
		FROM
			`tabPayment Entry Reference` per
		INNER JOIN
			`tabPayment Entry` pe
		ON
			per.parent = pe.name
		WHERE
			pe.docstatus = 1 AND
			pe.workflow_state = "Approved" AND
			pe.posting_date BETWEEN '{from_date}' AND '{to_date}' AND
			per.reference_doctype = "Employee Advance" AND
			pe.payment_type = "Pay"
			{ap_query}
		GROUP BY
			pe.party
	""".format(ap_query=ap_query, from_date=filters.get("from_date"), to_date=filters.get("to_date")),
	as_dict=True)

	total_employee_pay = frappe.db.sql("""
		SELECT
			pe.name,
			pe.party,
			SUM(pe.paid_amount) AS total_paid
		FROM
			`tabPayment Entry Reference` per
		INNER JOIN
			`tabPayment Entry` pe
		ON
			per.parent = pe.name
		WHERE
			pe.docstatus = 1 AND
			pe.workflow_state = "Approved" AND
			pe.posting_date BETWEEN '{from_date}' AND '{to_date}' AND
			pe.payment_type = "Pay"
			{ap_query}
		GROUP BY
			pe.party
	""".format(ap_query=ap_query, from_date=filters.get("from_date"), to_date=filters.get("to_date")),
	as_dict=True)
	for salary in total_closing_salary:
		for closed in closing_salary:
			if closed.employee == salary.employee:
				salary["closing_balance"] = salary.total_amount - closed.total_paid_amount
	for salary in total_salary:
		for paid in paid_salary:
			if paid.employee == salary.employee:
				salary["opening_balance"] = salary.total_amount - paid.total_paid_amount
		for advance in advance_paid:
			if advance.party == salary.employee:
				salary["employee_advance"] = advance.employee_advance
		for total_pay in total_employee_pay:
			if total_pay.party == salary.employee:
				salary["payment"] = total_pay.total_paid
		for closing in total_closing_salary:
			if closing.employee == salary.employee:
				salary["closing_balance"] = closing.closing_balance
	return total_salary


def get_query(filters, additional_query=None):
	if not filters.get("from_daye") and not filters.get("to_date"):
		frappe.throw("From Date and To Date are mandatory")
	query = "" 
	if additional_query:
		query += additional_query
	if filters.get("employee_id"):
		query += "AND ped.employee = '{0}'".format(filters.get("employee_id"))
	data = frappe.db.sql("""
		SELECT
			ped.employee,
			ped.employee_name,
			ped.parent,
			ss.name,
			SUM(ss.gross_pay) as total_paid_amount
		FROM
			`tabPayroll Employee Detail` ped
		INNER JOIN
			`tabPayroll Entry` pe
		ON
			pe.name = ped.parent
		INNER JOIN
			`tabSalary Slip` ss
		ON
			ss.payroll_entry = pe.name AND
			ss.employee = ped.employee
		INNER JOIN
			`tabJournal Entry Account` jea
		ON
			jea.reference_name = ped.parent AND
			jea.party = ped.employee
		INNER JOIN
			`tabJournal Entry` je
		ON
			jea.parent = je.name
		WHERE
			pe.docstatus = 1 AND
			ss.docstatus = 1 AND
			je.docstatus = 1
			{query}
		GROUP BY
			ped.employee
	""".format(query=query, from_date=filters.get("from_date"), to_date=filters.get("to_date"), employee=filters.get("employee_id")),
	as_dict=True)
	return data
