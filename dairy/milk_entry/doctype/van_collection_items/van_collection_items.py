# -*- coding: utf-8 -*-
# Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.model.mapper import get_mapped_doc
from math import ceil

class VanCollectionItems(Document):
	
	@frappe.whitelist()
	def creatr_stock(self):
		van_collection = frappe.get_doc("Van Collection", self.van_collection)
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Material Transfer"
		stock_entry.stock_entry_type = "Material Transfer"
		stock_entry.set_posting_time = 1
		stock_entry.posting_date = van_collection.date
		stock_entry.company = van_collection.company
		stock_entry.van_collection = van_collection.name
		stock_entry.van_collection_item = self.name
		stock_entry.docstatus = 1
		stock_entry.status = "Submited"

		route = frappe.get_doc("Route Master", van_collection.route)
		stock_entry.target_warehouse = route.source_warehouse
		
		# doc1 = frappe.get_doc('Dairy Settings')
		# if doc1.quality_inspection_required_for_van_collection == 1:
		# 	stock_entry.inspection_required = 1

		cost_center = frappe.get_cached_value('Company', van_collection.company, 'cost_center')
		perpetual_inventory = frappe.get_cached_value('Company', van_collection.company, 'enable_perpetual_inventory')
		expense_account = frappe.get_cached_value('Company', van_collection.company, 'stock_adjustment_account')

		cow_item = frappe.db.get_single_value("Dairy Settings", "cow_pro")
		buf_item = frappe.db.get_single_value("Dairy Settings", "buf_pro")
		mix_item = frappe.db.get_single_value("Dairy Settings", "mix_pro")

		doc = frappe.get_doc("Van Collection Items", self.name)

		if doc.cow_milk_collected > 0:
			self.set_value_depend_milk_type(cow_item, stock_entry, doc, doc.cow_milk_collected, doc.cow_milk_fat, doc.cow_milk_clr,doc.cow_milk_snf, route, cost_center, expense_account, perpetual_inventory)

		if doc.buffalow_milk_collected > 0:
			self.set_value_depend_milk_type(buf_item, stock_entry, doc, doc.buffalow_milk_collected, doc.buf_milk_fat,doc.buffalow_milk_snf,  doc.buf_milk_clr, route, cost_center, expense_account, perpetual_inventory)

		if doc.mix_milk_collected > 0:
			self.set_value_depend_milk_type(mix_item, stock_entry,doc,doc.mix_milk_collected, doc.mix_milk_fat, doc.mix_milk_clr, doc.mix_milk_snf,route, cost_center, expense_account,perpetual_inventory)

		
		stock_entry.save()
		return stock_entry

	def set_value_depend_milk_type(self, item_name,inspection_required, stock_entry, doc, milk_collected,fat,clr,snf, route, cost_center, expense_account, perpetual_inventory=None):
			item = frappe.get_doc("Item", item_name)
			print('clr@@@@@@@@@@@@@@@@',clr,snf,fat)
			se_child = stock_entry.append('items')
			se_child.item_code = item.item_code
			se_child.item_name = item.item_name
			se_child.uom = item.stock_uom
			se_child.stock_uom = item.stock_uom
			se_child.qty = milk_collected
			se_child.fat = (milk_collected * item.weight_per_unit) * (fat/100)
			se_child.fat_per = fat
			se_child.snf_clr = (milk_collected * item.weight_per_unit) * (clr/100)
			se_child.snf_clr_per = clr
			se_child.snf = (milk_collected * item.weight_per_unit) * (snf/100)
			se_child.snf_per = snf
			se_child.s_warehouse = doc.dcs
			se_child.t_warehouse = route.source_warehouse
			se_child.basic_rate = item.valuation_rate
			se_child.inspection_required = item.inspection_required
			# in stock uom
			se_child.transfer_qty = doc.cow_milk_collected
			se_child.cost_center = cost_center
			se_child.expense_account = expense_account if perpetual_inventory else None




	def validate(self):
		if self.get('__islocal'):
			result = frappe.db.sql("""select * from `tabVan Collection Items` where dcs =%s and shift =%s
							and date=%s and docstatus = 1""",(self.dcs,self.shift,self.date))
			if result:
				frappe.throw("You can not create duplicate entry on same date and same DCS")

	@frappe.whitelist()
	def calculate_milk_cans(self):
		allow_max_capacity = float(frappe.db.get_single_value("Dairy Settings", "max_allowed"))

		if self.cow_milk_vol < self.cow_milk_collected:
			frappe.throw("Can not allow Cow Milk Collected greater then the Cow Milk Entry")

		if self.buf_milk_vol < self.buffalow_milk_collected:
			frappe.throw("Can not allow Buffalo Milk Collected greater then the Buffalo Milk Entry")

		if self.mix_milk_vol < self.mix_milk_collected:
			frappe.throw("Can not allow Mix Milk Collected greater then the Mix Milk Entry")

		if allow_max_capacity > 0:
			self.cow_milk_cans = ceil(self.cow_milk_collected / allow_max_capacity)
			self.buf_milk_cans = ceil(self.buffalow_milk_collected / allow_max_capacity)
			self.mix_milk_cans = ceil(self.mix_milk_collected / allow_max_capacity)
			self.db_update()
			# self.save(ignore_permissions=True)

		return True

	@frappe.whitelist()
	def make_stock_entry(self):
		van_collection = frappe.get_doc("Van Collection", self.van_collection)
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Material Transfer"
		stock_entry.stock_entry_type = "Material Transfer"
		stock_entry.set_posting_time = 1
		stock_entry.posting_date = van_collection.date
		stock_entry.company = van_collection.company
		stock_entry.van_collection = van_collection.name
		stock_entry.van_collection_item = self.name

		route = frappe.get_doc("Route Master", van_collection.route)
		stock_entry.target_warehouse = route.source_warehouse
		
		doc1 = frappe.get_doc('Dairy Settings')
		if doc1.quality_inspection_required_for_van_collection == 1:
			stock_entry.inspection_required = 1

		cost_center = frappe.get_cached_value('Company', van_collection.company, 'cost_center')
		perpetual_inventory = frappe.get_cached_value('Company', van_collection.company, 'enable_perpetual_inventory')
		expense_account = frappe.get_cached_value('Company', van_collection.company, 'stock_adjustment_account')

		cow_item = frappe.db.get_single_value("Dairy Settings", "cow_pro")
		buf_item = frappe.db.get_single_value("Dairy Settings", "buf_pro")
		mix_item = frappe.db.get_single_value("Dairy Settings", "mix_pro")

		doc = frappe.get_doc("Van Collection Items", self.name)

		if doc.cow_milk_collected > 0:
			self.set_value_depend_milk_type(cow_item, stock_entry, doc, doc.cow_milk_collected, doc.cow_milk_fat, doc.cow_milk_clr,doc.cow_milk_snf, route, cost_center, expense_account, perpetual_inventory)

		if doc.buffalow_milk_collected > 0:
			self.set_value_depend_milk_type(buf_item, stock_entry, doc, doc.buffalow_milk_collected, doc.buf_milk_fat,doc.buffalow_milk_snf,  doc.buf_milk_clr, route, cost_center, expense_account, perpetual_inventory)

		if doc.mix_milk_collected > 0:
			self.set_value_depend_milk_type(mix_item, stock_entry,doc,doc.mix_milk_collected, doc.mix_milk_fat, doc.mix_milk_clr, doc.mix_milk_snf,route, cost_center, expense_account,perpetual_inventory)

		

		return stock_entry

	def set_value_depend_milk_type(self, item_name, stock_entry, doc, milk_collected,fat,clr,snf, route, cost_center, expense_account, perpetual_inventory=None):
		item = frappe.get_doc("Item", item_name)
		print('clr@@@@@@@@@@@@@@@@',clr,snf,fat)
		se_child = stock_entry.append('items')
		se_child.item_code = item.item_code
		se_child.item_name = item.item_name
		se_child.uom = item.stock_uom
		se_child.stock_uom = item.stock_uom
		se_child.qty = milk_collected
		se_child.fat = (milk_collected * item.weight_per_unit) * (fat/100)
		se_child.fat_per = fat
		se_child.snf_clr = (milk_collected * item.weight_per_unit) * (clr/100)
		se_child.snf_clr_per = clr
		se_child.snf = (milk_collected * item.weight_per_unit) * (snf/100)
		se_child.snf_per = snf
		se_child.s_warehouse = doc.dcs
		se_child.t_warehouse = route.source_warehouse
		se_child.basic_rate = item.valuation_rate
		# in stock uom
		se_child.transfer_qty = doc.cow_milk_collected
		se_child.cost_center = cost_center
		se_child.expense_account = expense_account if perpetual_inventory else None


@frappe.whitelist()
def get_milk_entry(source_name, target_doc=None, ignore_permissions=False):
	def get_milk_entry_data(source, target):

		if source.milk_type == 'Cow':
			target.cow_milk_vol += source.volume
			target.cow_milk_fat += source.fat
			target.cow_milk_clr += source.clr
			result = frappe.db.sql("""Select name from `tabSample lines` where milk_entry =%s""",(source.name))
			if result:
				target.append("cow_milk_sam",{
					'sample_lines':result[0][0]
				})
		if source.milk_type == 'Buffalo':
			target.buf_milk_vol += source.volume
			target.buf_milk_fat += source.fat
			target.buf_milk_clr += source.clr
			result = frappe.db.sql("""Select name from `tabSample lines` where milk_entry =%s""", (source.name))
			if result:
				target.append("buf_milk_sam", {
					'sample_lines': result[0][0]
				})
		if source.milk_type == 'Mix':
			target.mix_milk_vol += source.volume
			target.mix_milk_fat += source.fat
			target.mix_milk_clr += source.clr
			result = frappe.db.sql("""Select name from `tabSample lines` where milk_entry =%s""", (source.name))
			if result:
				target.append("mix_milk_sam", {
					'sample_lines': result[0][0]
				})
		target.db_update()
	doclist = get_mapped_doc("Milk Entry", source_name, {
		"Milk Entry": {
			"doctype": "Van Collection Items",
		}
	}, target_doc, get_milk_entry_data)
	return doclist



