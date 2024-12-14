# -*- coding: utf-8 -*-
# Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class BulkMilkPriceList(Document):
	pass

@frappe.whitelist()
def fetch_data(doctype, customer):
	all_doc = frappe.db.get_all(doctype,fields=['*'],filters = {"docstatus" :1})
	for doc in all_doc:
		query = """ select customer from `tabBulk Milk Price List Customer` where parent = '{0}'""".format(doc.get("name"))
		customer_name = frappe.db.sql(query, as_dict = True)
		if(customer == customer_name[0].get("customer")):
			return {
				'rate': doc.get("rate"),
				'snf' : doc.get('snf_clr_rate')
			}

@frappe.whitelist()
def fetch_snf_and_fat(item,customer):
	doc = frappe.get_doc('Bulk Milk Price List', {'item': item, 'docstatus':'1'}, as_dict= True)
	return {
				'rate': doc.rate,
				'snf_clr_rate': doc.snf_clr_rate
			}
	# print("******* "*20)
	# print(doc)
	# print(customer)
	# if doc:
	# 	for cust in doc.get('customer'):
	# 		if cust.get('customer') == customer:
	# 			d = {
	# 				'rate': doc.rate,
	# 				'snf_clr_rate': doc.snf_clr_rate
	# 			}
	# 			return d