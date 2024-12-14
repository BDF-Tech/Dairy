# -*- coding: utf-8 -*-
# Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import set_missing_values
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from erpnext.assets.doctype.asset.depreciation \
	import get_disposal_account_and_cost_center, get_depreciation_accounts
from datetime import datetime

class CrateReconciliation(Document):
	def validate(self):
		if not self.get("__islocal"):
			self.calculate_total_count()

	def after_insert(self):
		self.calculate_total_count()
		self.settlement()

	def settlement(self):
		dist_crate_type =frappe.db.sql(""" select distinct crate_type from `tabCrate Reconciliation Child` where parent = %(name)s """,
									   {'name':self.name})
		for i in range(0,len(dist_crate_type)):
			totals = frappe.db.sql(""" select sum(outgoing),sum(incoming),sum(damaged) from `tabCrate Reconciliation Child` where 
			 		parent = %(name)s and crate_type = %(crate_type)s""",{'name':self.name,'crate_type':dist_crate_type[i][0]})
			difference = totals[0][0] - totals[0][1]

			self.append("settlement_info", {
				"crate_type": dist_crate_type[i][0],
				"total_outgoing": totals[0][0],
				"total_incoming": totals[0][1],
				"total_damaged": totals[0][2],
				"difference": difference
			})


	
	def calculate_total_count(self):
		total_outgoing = 0.0
		total_incoming = 0.0
		total_damage = 0.0
		for i in self.delivery_info:
			if i.outgoing:
				total_outgoing += i.outgoing
			if i.incoming:
				total_incoming += i.incoming
			if i.damaged:
				total_damage += i.damaged
		self.total_outgoing =total_outgoing
		self.total_incoming =total_incoming
		self.total_damaged =total_damage
		self.difference = total_outgoing - total_incoming
		self.db_update()

	def on_submit(self):
		for i in self.delivery_info:
			if i.delivery_note:
				del_note = frappe.get_doc("Delivery Note",i.delivery_note)
				del_note.crate_reconcilation_done =1
				del_note.db_update()
			if i.gate_pass:
				del_note = frappe.get_doc("Gate Pass", i.gate_pass)
				del_note.crate_reconcilation_done = 1
				del_note.db_update()
			if i.crate_log:
				crate_log = frappe.get_doc("Crate Log", i.crate_log)
				crate_log.crate_reconsilliation_done = 1
				crate_log.db_update()
			if i.sales_invoice:
				si = frappe.get_doc("Sales Invoice", i.sales_invoice)
				si.crate_reconcilation_done = 1
				si.db_update()
			doc=frappe.new_doc("Crate Log")
			doc.crate_type=i.crate_type
			val=frappe.db.get_value("Crate Log",{"customer":i.customer},["name","crate_balance"],order_by="creation desc")
			doc.route=i.route
			doc.date=self.date
			doc.customer=i.customer
			if val:
				doc.crate_opening=val[1]
				doc.crate_issue=i.outgoing
				doc.crate_return=abs(i.incoming)
				doc.crate_balance=val[1]+i.outgoing-i.incoming
			doc.voucher_type="Crate Reconciliation"
			doc.voucher=self.name
			doc.company=self.company
			doc.save(ignore_permissions=True)
			doc.submit()


	def on_cancel(self):
		for i in self.delivery_info:
			if i.delivery_note:
				del_note = frappe.get_doc("Delivery Note",i.delivery_note)
				del_note.crate_reconcilation_done =0
				del_note.db_update()
			if i.gate_pass:
				del_note = frappe.get_doc("Gate Pass",i.gate_pass)
				del_note.crate_reconcilation_done =0
				del_note.db_update()
			if i.crate_log:
				crate_log = frappe.get_doc("Crate Log", i.crate_log)
				crate_log.crate_reconsilliation_done = 0
				crate_log.db_update()
			if i.sales_invoice:
				si = frappe.get_doc("Sales Invoice", i.sales_invoice)
				si.crate_reconcilation_done = 0
				si.db_update()
	@frappe.whitelist()
	def calculate_crate_type_summary(self):
		if self:
			frappe.db.sql("delete from `tabCrate Type Summary Child` where parent = %s", (self.name))
			result = frappe.db.sql("""select crate_type,sum(difference) as diff from `tabCrate Reconciliation Child`
									where crate_type is not null and parent =%s
									group by crate_type""", (self.name), as_dict=True)
			for i in result:
				self.append("crate_type_summary", {
					"crate_type": i.get('crate_type'),
					"difference": i.get('diff')
				})
			self.flags.ignore_validate_update_after_submit = True   #ignore after submit permission
			self.save(ignore_permissions=True)
		return True
	
	@frappe.whitelist()
	def make_sales_invoice(self):
		si = frappe.new_doc("Sales Invoice")
		si.company = self.company
		si.customer = self.customer
		si.crate_reconciliation = self.name
		si.route = self.route
		si.due_date = datetime.now().date()
		si.currency = frappe.get_cached_value('Company', self.company, "default_currency")
		disposal_account, depreciation_cost_center = get_disposal_account_and_cost_center(self.company)
		result = frappe.db.sql("""select crate_type,sum(difference) as diff from `tabCrate Reconciliation Child`
											where crate_type is not null and parent =%s
											group by crate_type""", (self.name), as_dict=True)
		for i in result:
			crate_type_doc = frappe.get_doc("Crate Type",i.get('crate_type'))
			si.append("items", {
				"item_code": crate_type_doc.item,
				"income_account": disposal_account,
				"cost_center": depreciation_cost_center,
				"qty": i.get('diff'),
				"rate":crate_type_doc.price
			})
		si.set_missing_values()
		return si


@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, ignore_permissions=False):
	def set_item_in_sales_invoice(source, target):
		del_note = frappe.get_doc(source)
		crate_recl = frappe.get_doc(target)
		for i in del_note.crate_count:
			out_count = i.outgoing_count if i.outgoing_count else 0
			in_count = i.incoming_count if i.incoming_count else 0
			dam_count = i.damaged_count if i.damaged_count else 0
			vehicle_name = None
			if del_note.route:
				route_doc = frappe.get_doc("Route Master",del_note.route)
				vehicle_name = route_doc.vehicle
			crate_recl.append("delivery_info",{
				"delivery_date": del_note.posting_date,
				"delivery_note": del_note.name,
				"customer": del_note.customer,
				"route": del_note.route,
				"crate_type": i.crate_type,
				"vehicle": vehicle_name,
				"outgoing": out_count,
				"incoming": in_count,
				"damaged": dam_count,
				"difference": out_count - in_count
			})

	doclist = get_mapped_doc("Delivery Note", source_name, {
		"Delivery Note": {
			"doctype": "Crate Reconciliation",
		}
	}, target_doc,set_item_in_sales_invoice)
	return doclist


@frappe.whitelist()
def make_crate_log(source_name, target_doc=None, ignore_permissions=False):
	def set_item_in_sales_invoice(source, target):
		del_note = frappe.get_doc(source)
		crate_recl = frappe.get_doc(target)
		if del_note.voucher_type=="Sales Invoice":
			crate_recl.append("delivery_info",{
				"delivery_date": del_note.date,
				"crate_log": del_note.name,
				"transporter": del_note.transporter,
				"customer":del_note.customer,
				"sales_invoice":del_note.voucher,
				"route": del_note.route,
				"crate_type": del_note.crate_type,
				"vehicle": del_note.vehicle,
				"outgoing": del_note.crate_issue,
				"incoming": del_note.crate_return,
				"damaged": del_note.damaged,
				"difference": del_note.crate_issue - del_note.crate_return,
				"gate_pass": del_note.gate_pass
			})
		if del_note.voucher_type=="Delivery Note":
			crate_recl.append("delivery_info",{
				"delivery_date": del_note.date,
				"crate_log": del_note.name,
				"transporter": del_note.transporter,
				"customer":del_note.customer,
				"delivery_note":del_note.voucher,
				"route": del_note.route,
				"crate_type": del_note.crate_type,
				"vehicle": del_note.vehicle,
				"outgoing": del_note.crate_issue,
				"incoming": del_note.crate_return,
				"damaged": del_note.damaged,
				"difference": del_note.crate_issue - del_note.crate_return,
				"gate_pass": del_note.gate_pass
			})
		if del_note.voucher_type=="Gate Pass":
			crate_recl.append("delivery_info",{
				"delivery_date": del_note.date,
				"crate_log": del_note.name,
				"transporter": del_note.transporter,
				"customer":del_note.customer,
				"route": del_note.route,
				"crate_type": del_note.crate_type,
				"vehicle": del_note.vehicle,
				"outgoing": del_note.crate_issue,
				"incoming": del_note.crate_return,
				"damaged": del_note.damaged,
				"difference": del_note.crate_issue - del_note.crate_return,
				"gate_pass": del_note.gate_pass
			})

	doclist = get_mapped_doc("Crate Log", source_name, {
		"Crate Log": {
			"doctype": "Crate Reconciliation",
			# "field_map": {
			# 	"date": ""
			# }
		}
	}, target_doc,set_item_in_sales_invoice)
	return doclist