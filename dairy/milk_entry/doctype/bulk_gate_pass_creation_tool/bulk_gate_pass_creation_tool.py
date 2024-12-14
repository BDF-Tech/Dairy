# -*- coding: utf-8 -*-
# Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from frappe import _
class BulkGatePassCreationTool(Document):
	def get_options(self, arg=None):
		if frappe.get_meta("Gate Pass").get_field("naming_series"):
			return frappe.get_meta("Gate Pass").get_field("naming_series").options

	def create_delivery_note(self):

		lst = []
		for itm in self.items:
			lst.append(itm.shift + "," + itm.transporter + "," + itm.vehicle)
		for customer in set(lst):
			doc = frappe.new_doc("Gate Pass")
			doc.total_qty = 0
			doc.total_free_qty = 0
			doc.date = self.date
			doc.naming_series = self.name_series
			doc.customer = self.customer
			total_supp_qty = 0
			total_free_qty = 0
			for itm in self.items:
				if customer == (itm.shift + "," + itm.transporter + "," + itm.vehicle):
					doc.route = itm.route
					doc.transporter = itm.transporter
					doc.vehicle = itm.vehicle
					doc.shift = itm.shift
					doc.warehouse = itm.warehouse
					if itm.batch_no:
						doc.append('item', {
									'item_code': itm.item_code,
									'item_name': itm.item_name,
									'batch_no': itm.batch_no,
									'qty': itm.qty,
									'uom': itm.uom,
									'out_crate': itm.out_crate,
									'free_qty': itm.free_qty,
									'in_crate': itm.in_crate,
									'warehouse': itm.warehouse,
									'delivery_note': itm.delivery_note,
									'is_free_item': itm.is_free_item,
									'total_weight': itm.total_weight,
									'item_group': itm.item_group,
									'weight_per_unit': itm.weight_per_unit

								})
					else:
						doc.append('item', {
							'item_code': itm.item_code,
							'item_name': itm.item_name,
							'qty': itm.qty,
							'uom': itm.uom,
							'out_crate': itm.out_crate,
							'free_qty': itm.free_qty,
							'in_crate': itm.in_crate,
							'warehouse': itm.warehouse,
							'delivery_note': itm.delivery_note,
							'is_free_item': itm.is_free_item,
							'total_weight': itm.total_weight,
							'item_group': itm.item_group,
							'weight_per_unit': itm.weight_per_unit
						})
			doc.save(ignore_permissions=True)

	def get_filter_condition(self):
		self.check_mandatory()

		cond = ''
		for f in ['shift', 'transporter', 'route', 'set_warehouse', 'posting_date']:
			if self.get(f):
				cond += " and DN." + f + " = '" + self.get(f).replace("'", "\'") + "'"

		return cond

	def check_mandatory(self):
		for fieldname in ['name_series', 'date', 'shift', 'warehouse']:
			if not self.get(fieldname):
				frappe.throw(_("Please set {0}").format(self.meta.get_label(fieldname)))

	def get_del_note(self):
		"""
			Returns list of active items based on selected criteria

		"""
		cond = self.get_filter_condition()

		query = """ select DNI.item_code as item_code, DNI.item_name, DNI.stock_qty as qty, DNI.stock_uom as uom, DNI.warehouse,
		 			DNI.is_free_item, DNI.batch_no, DNI.total_weight, DNI.weight_per_unit,
					DN.name as delivery_note, DN.route, DN.vehicle, DN.shift, DN.transporter,
					ITM.item_group
				  from `tabDelivery Note Item` DNI, `tabDelivery Note` DN, `tabItem` ITM
				   where
				 	DN.name = DNI.parent and DN.docstatus = 1 and DN.status in ('To Bill','Completed')  and DN.crate_gate_pass_done = 0
				 	 and ITM.item_code = DNI.item_code"""

		ord_by = "order by DN.posting_date"
		q_data = frappe.db.sql(query+cond+ord_by,as_dict=True)
		return q_data

	def fill_details(self):
		self.set('items', [])
		items = self.get_del_note()
		if not items:
			frappe.throw(_("No Delivery Note for the mentioned criteria"))

		for d in items:
			self.append('items', d)



@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, skip_item_mapping=False):
	def update_item(source, target, source_parent):
		if source_parent.route:
			target.update({'route': source_parent.route})
		if source_parent.shift:
			target.update({'shift': source_parent.shift})
		if source_parent.customer:
			target.update({'customer': source_parent.customer})
		if source_parent.posting_date:
			target.update({'date': source_parent.posting_date})
		if source_parent.transporter:
			target.update({'transporter': source_parent.transporter})
		if source_parent.vehicle:
			target.update({'vehicle': source_parent.vehicle})
		if source_parent.set_warehouse:
			target.update({'warehouse': source_parent.set_warehouse})

	doclist = get_mapped_doc("Delivery Note", source_name, {
		"Delivery Note": {
			"doctype": "Bulk Gate Pass Creation Tool",
			"validation": {
				"docstatus": ["=", 1]
				# "material_request_type": ["=", "Purchase"]
			}
		},
		"Delivery Note Item": {
			"doctype": "Bulk Gate Pass Item",
			"field_map": [
				["stock_qty", 'qty'],
				["item_code", "item_code"],
				["stock_uom", "uom"],
				["delivery_note_item", "name"],
				["is_free_item", "is_free_item"]
			],
			"postprocess": update_item,
		}
	}, target_doc)


	return doclist
