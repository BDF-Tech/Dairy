# -*- coding: utf-8 -*-
# Copyright (c) 2019, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt, nowdate, getdate
from frappe.model.document import Document


class FieldOrder(Document):
	pass

	
@frappe.whitelist()
def make_order_book(source_name, target_doc=None):
# 	field_order = frappe.db.get_value("Field Order", source_name, "transaction_date", as_dict = 1)

	def set_missing_values(source, target):
		
		order_book = frappe.get_doc(target)
		if source.company == target.company:
			order_book.append('order_book_line', {
				'sales_team': source.sales_team,
		        'customer': source.customer,
		        'secondary_customer': source.customer,
		        'product': source.product,
		        'qty':source.qty,
		        'uom':source.uom,
		        'field_order':source.name
		    })

	doclist = get_mapped_doc("Field Order", source_name, {
			"Field Order": {
				"doctype": "Order Book",
				"validation": {
					"docstatus": ["=", 1]
				}
			}
	    }, target_doc, set_missing_values)
	 
	return doclist


	
