# -*- coding: utf-8 -*-
# Copyright (c) 2019, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from datetime import timedelta, date,datetime
from frappe.model.document import Document
from dateutil.relativedelta import relativedelta

class OrderBook(Document):
	def on_submit(self):
		self.get_sales_order()
	
	def get_sales_order(self):
		customers = frappe.db.sql(""" select distinct customer from `tabOrder Book Line` where parent='{0}' """.format(self.name))
		
		for cust in customers:
			order_lines = frappe.db.get_all("Order Book Line",{"parent": self.name,"customer":cust[0]})
			
			doc = frappe.new_doc('Sales Order')
			doc.customer = cust[0]
			doc.order_date = self.date
			# doc.delivery_date = src.delivery_date
			doc.company = self.company
			doc.order_book = self.name
			for ord in order_lines:
				src = frappe.get_doc('Order Book Line',ord['name'])
				
				item = frappe.get_doc("Item",src.product)
				doc.append('items', {
					'item_code':src.product,
					'item_name':item.item_name,
					'description':item.description,
					'delivery_date':datetime.now().date(),
					'qty':src.qty,
					'uom':src.uom,
					# 'stock_uom': item_code.stock_uom,
					'rate':src.rate,
					'warehouse':self.delivery_warehouse
				})
			doc.save()
			doc.submit()


def get_data_per_day(doctype, txt, searchfield, start, page_len, filters, as_dict):
	print("====doctype",doctype,"==txt",txt,"==searchfield",searchfield,"==filters",filters,"==as_dict",as_dict)
	data = frappe.db.sql(""" select name,customer,transaction_date from `tabField Order` where (transaction_date = %(date)s or (next_order_date = %(date)s or Null)  )
			and docstatus= 1 and disable = 0 and order_book is null and company=%(com)s  """,{"date":filters.get('date'),"com":filters.get('company')})
	print("====data",data)
	
	return data
	 