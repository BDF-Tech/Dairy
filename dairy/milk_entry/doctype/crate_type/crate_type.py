# -*- coding: utf-8 -*-
# Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CrateType(Document):
	def add_crate_log(self,crate_type,crate_issue,crate_return,transporter,route,warehouse,company):
		if crate_issue <= 0 or crate_return <= 0:
			frappe.throw("Crate Issue and Crate Return should be greter than 0")
		else:
			log = frappe.new_doc("Crate Log")
			log.transporter = transporter
			log.route = route
			log.date = frappe.utils.nowdate()
			log.company = company
			log.voucher_type = "Crate Type"
			log.voucher = self.name
			log.crate_issue = crate_issue
			log.crate_return = crate_return
			log.crate_type = crate_type
			log.source_warehouse = warehouse
			log.note = "Entry Created Manually By "+frappe.session.user
			openning_cnt = frappe.db.sql(""" select count(*) from `tabCrate Log`  where crate_type = %(crate)s and source_warehouse = %(warehouse)s
												 and company = %(company)s and  docstatus = 1	 order by date desc  """,
										 {'crate': crate_type, 'warehouse': warehouse,
										  'company': company}, as_dict=1)
			print("opening_cnt = ", openning_cnt)
			if openning_cnt[0]['count(*)'] > 0:
				print("11111111111111111111111111111111111111111111111111111111111111111111111111111111111111")
				openning = frappe.db.sql(""" select crate_balance from `tabCrate Log`  where crate_type = %(crate)s and source_warehouse = %(warehouse)s and
									company = %(company)s and  docstatus = 1 order by date desc limit 1 """,
										 {'crate': crate_type, 'warehouse': warehouse, 'company': company}, as_dict=1)
				print("------------", openning)
				log.crate_opening = int(openning[0]['crate_balance'])
				log.crate_balance = openning[0]['crate_balance'] - (crate_issue + crate_return)

			else:
				print("0000000000000000000000000000000000000000000000000000000000000000000000000000000")
				log.crate_opening = int(0)
				log.crate_balance = int(0) - (crate_issue + crate_return)

			log.save()
			log.submit()