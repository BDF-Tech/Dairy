# -*- coding: utf-8 -*-
# Copyright (c) 2019, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class RawMilkSample(Document):
	def validate(self):
		if not self.get('__islocal'):
			self.change_status()

	def after_insert(self):
		self.change_status()

	def change_status(self):
		print('to sample##################################')
		sam_line = frappe.db.sql("""Select distinct(milk_entry) from `tabSample lines` where parent =%s""", (self.name))
		for sam in sam_line:
			doc = frappe.get_doc("Milk Entry", sam[0])
			print('to sample##################################',doc.sample_created)
			res = frappe.db.sql("""select docstatus from `tabPurchase Receipt` where milk_entry =%s limit 1""",(doc.name))
			print('res##################################',res , res[0][0])

			if res:
				if res[0][0] == 1 and doc.sample_created:
					doc.status = "To Sample"
					print('to bill##################################')
				elif res[0][0] ==0 and not doc.sample_created:
					doc.status = "To Post"
				elif res[0][0] ==1 and not doc.sample_created:
					doc.status = "To Sample and Bill"
					print('postedddddddddddddddddddddddddd')
				elif res[0][0] == 0 and doc.sample_created:
					doc.status = "To Post and Sample"
				else:
					doc.status = "To Post and Sample"
			else:
				doc.status = "To Post and Sample"
			doc.db_update()

	def on_submit(self):
		sam_line = frappe.db.sql("""Select distinct(milk_entry) from `tabSample lines` where parent =%s""", (self.name))
		for sam in sam_line:
			doc = frappe.get_doc("Milk Entry", sam[0])
			doc.db_set("sample_created",1)
			res = frappe.db.sql("""select docstatus from `tabPurchase Receipt` where milk_entry =%s limit 1""",(doc.name))
			if res:
				if res[0][0] == 0 and doc.sample_created:
					doc.status = "To Post"
				elif res[0][0] == 1 and doc.sample_created:
					doc.status = "To Sample and Bill"
				elif res[0][0] == 0 and not doc.sample_created:
					doc.status = "To Post"
				elif res[0][0] == 1 and not doc.sample_created:
					doc.status = "To Bill"
				else:
					doc.status = "To Post"
			else:
				doc.status = "To Post"
			doc.db_update()


