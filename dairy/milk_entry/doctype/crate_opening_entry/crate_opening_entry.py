# Copyright (c) 2023, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils.data import getdate, today

class CrateOpeningEntry(Document):
	@frappe.whitelist()
	def make_crate_log(self , co =0):

		if frappe.db.get_single_value("Dairy Settings", "crate_reconciliation_based_on") == "Crate Opening Entry":

			for crate in self.party_crate_opening:
				log = frappe.new_doc("Crate Log")
				customer_route = frappe.get_doc('Customer',{'customer_name':crate.customer})
				print('customer&&&&&&&&&&&&&&&&&&&&&',customer_route)
				for j in customer_route.links:
					doc=frappe.get_doc("Route Master",j.link_name)
					print('customer route&&&&&&&&&&&&&&&&&&&&&7',doc)
					route = frappe.get_all('Route Master',{'name':j.link_name},['*'])
					for k in route:

						log.transporter = k.transporter
						log.vehicle = k.vehicle
						log.route = doc.name
						log.customer = crate.customer
						# log.shift = self.shift
						log.date = self.date
						log.company = self.company
						log.voucher_type = "Crate Opening Entry"
						log.voucher = self.name
						log.crate_opening = crate.crate_opening
						log.crate_balance = crate.crate_opening
						log.crate_type = crate.crate_type
						log.source_warehouse = k.source_warehouse
						log.note = "Entry Created From Crate Opening Entry"
						
						crate_log = frappe.db.get_value('Crate Log',{'customer':crate.customer,'crate_type':crate.crate_type,"docstatus":1},['name'],"creation desc")

						if crate_log:
							doc=frappe.get_doc("Crate Log",crate_log)
							
							if getdate(doc.date) >= getdate(self.date):
								frappe.throw(
									_("Crate Date Does Not Future Date {0} Date").format(today()))
							if getdate(doc.date) < getdate(self.date) and doc.customer == crate.customer and doc.crate_type == crate.crate_type:
								log.crate_opening = doc.crate_balance

								log.crate_balance = crate.crate_opening
								opening =  crate.crate_opening - doc.crate_balance
								
							
								if int(opening) > 0:
									log.crate_issue = int(opening)
									
								if opening<0:
									log.crate_return = abs(opening)


							
						
					log.save()
					log.submit()
					frappe.msgprint("Crate Log Created.")

