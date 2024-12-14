# -*- coding: utf-8 -*-
# Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from math import ceil

class RMRDLines(Document):
	def validate(self):
		if self.get('__islocal'):
			result = frappe.db.sql("""select * from `tabRMRD Lines` where dcs =%s and shift =%s
							and date=%s and docstatus = 1""",(self.dcs,self.shift,self.date))
			if result:
				frappe.throw("You can not create duplicate entry on same date and same DCS")


	@frappe.whitelist()
	def item_weight(self,item_name):
		g_cow_item = frappe.db.get_single_value("Dairy Settings", "cow_pro")
		g_buf_item = frappe.db.get_single_value("Dairy Settings", "buf_pro")
		g_mix_item = frappe.db.get_single_value("Dairy Settings", "mix_pro")

		g_cow_weight = frappe.db.get_value('Item',g_cow_item,['weight_per_unit','item_name'])

		g_cow_name = frappe.db.get_value('Item',g_cow_item,['item_name'])

		g_buf_weight = frappe.db.get_value('Item',g_buf_item,['weight_per_unit','item_name'])

		g_buf_name = frappe.db.get_value('Item',g_buf_item,['item_name'])

		g_mix_weight = frappe.db.get_value('Item',g_mix_item,['weight_per_unit','item_name'])

		g_mix_name =  frappe.db.get_value('Item',g_mix_item,['item_name'])

		a = []
		a.append(g_cow_weight)
		a.append(g_cow_name)
		a.append(g_buf_weight)
		a.append(g_buf_name)
		a.append(g_mix_weight)
		a.append(g_mix_name)
		return a

	@frappe.whitelist()
	def calculate_total_cans_wt(self):
		allow_max_capacity = float(frappe.db.get_single_value("Dairy Settings", "max_allowed"))

		sum_cow_milk = self.rmrd_good_cow_milk + self.s_cow_milk + self.c_cow_milk
		
		sum_buffalo_milk = self.rmrd_good_buf_milk + self.s_buf_milk + self.c_buf_milk
		
		sum_mix_milk = self.rmrd_good_mix_milk + self.s_mix_milk + self.c_mix_milk

		if self.g_cow_milk < self.rmrd_good_cow_milk:
			frappe.throw("Can not allow More Milk than the Cow Milk Collected")

		if self.g_cow_milk < sum_cow_milk:
			frappe.throw("Can not allow Cow Milk Collected greater than the Cow Milk Collected")

		if self.g_buf_milk < self.rmrd_good_buf_milk:
			frappe.throw("Can not allow Buffalo Milk Collected greater than the Buffalo Milk Collected")

		if self.g_buf_milk < sum_buffalo_milk:
			frappe.throw("Can not allow Cow Milk Collected greater than the Cow Milk Collected")


		if self.g_mix_milk < self.rmrd_good_mix_milk:
			frappe.throw("Can not allow Mix Milk Collected greater than the Mix Milk Collected")

		if self.g_mix_milk < sum_mix_milk:
			frappe.throw("Can not allow Cow Milk Collected greater than the Cow Milk Collected")

		print('alow max capacity&&&&&&&&&&&&&&&&&&&&&&&&&&',allow_max_capacity)
		if allow_max_capacity > 0:
			self.g_cow_milk_can = ceil(self.rmrd_good_cow_milk / allow_max_capacity)
			self.g_buf_milk_can = ceil(self.rmrd_good_buf_milk / allow_max_capacity)
			self.g_mix_milk_can = ceil(self.rmrd_good_mix_milk / allow_max_capacity)
			self.s_cow_milk_can = ceil(self.s_cow_milk / allow_max_capacity)  
			self.s_buf_milk_can = ceil(self.s_buf_milk / allow_max_capacity)
			self.s_mix_milk_can = ceil(self.s_mix_milk / allow_max_capacity)
			self.c_cow_milk_can = ceil(self.c_cow_milk / allow_max_capacity)
			self.c_buf_milk_can = ceil(self.c_buf_milk / allow_max_capacity)
			self.c_mix_milk_can = ceil(self.c_mix_milk / allow_max_capacity)
			

		g_cow_milk = self.rmrd_good_cow_milk if self.rmrd_good_cow_milk else 0
		g_buf_milk = self.rmrd_good_buf_milk if self.rmrd_good_buf_milk else 0
		g_mix_milk = self.rmrd_good_mix_milk if self.rmrd_good_mix_milk else 0
		g_total_m = g_cow_milk + g_buf_milk + g_mix_milk

		g_total_c = self.g_cow_milk_can + self.g_buf_milk_can + self.g_mix_milk_can

		s_cow_milk = self.s_cow_milk if self.s_cow_milk else 0
		s_buf_milk = self.s_buf_milk if self.s_buf_milk else 0
		s_mix_milk = self.s_mix_milk if self.s_mix_milk else 0
		s_total_m = s_cow_milk + s_buf_milk + s_mix_milk

		s_total_c = self.s_cow_milk_can + self.s_buf_milk_can + self.s_mix_milk_can
		
		c_cow_milk = self.c_cow_milk if self.c_cow_milk else 0
		c_buf_milk = self.c_buf_milk if self.c_buf_milk else 0
		c_mix_milk = self.c_mix_milk if self.c_mix_milk else 0
		c_total_m =c_cow_milk + c_buf_milk + c_mix_milk

		c_total_c = self.c_cow_milk_can + self.c_buf_milk_can + self.c_mix_milk_can

		self.total_milk_can = g_total_c + s_total_c + c_total_c
		print('g_total_m - s_total_m - c_total_m************************',g_total_m,s_total_m,c_total_m)
		self.total_milk_wt = g_total_m + s_total_m + c_total_m
		self.db_update()
		

		return True


	@frappe.whitelist()
	def make_stock_entry(self):
		rmrd = frappe.get_doc("RMRD", self.rmrd)
		print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!',rmrd.date)
		# if rmrd.t_g_cow_wt > 0 or rmrd.t_g_buf_wt > 0 or rmrd.t_g_mix_wt > 0:
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Material Transfer"
		stock_entry.stock_entry_type = "Material Transfer"
		stock_entry.set_posting_time = 1
		stock_entry.posting_date = self.date
		stock_entry.rmrd = rmrd.name
		stock_entry.rmrd_lines = self.name
		# stock_entry.set_posting_time = 0

		stock_entry.company = rmrd.company
		stock_entry.rmrd = rmrd.name

		route = frappe.get_doc("Route Master", rmrd.route)

		cost_center = frappe.get_cached_value('Company', self.company, 'cost_center')
		print('cost center make stock entry****************',cost_center)
		perpetual_inventory = frappe.get_cached_value('Company', self.company, 'enable_perpetual_inventory')
		expense_account = frappe.get_cached_value('Company', self.company, 'stock_adjustment_account')

		g_cow_item = frappe.db.get_single_value("Dairy Settings", "cow_pro")
		g_buf_item = frappe.db.get_single_value("Dairy Settings", "buf_pro")
		g_mix_item = frappe.db.get_single_value("Dairy Settings", "mix_pro")

		s_cow_item = frappe.db.get_single_value("Dairy Settings", "s_cow_milk")
		s_buf_item = frappe.db.get_single_value("Dairy Settings", "s_buf_milk")
		s_mix_item = frappe.db.get_single_value("Dairy Settings", "s_mix_milk")

		c_cow_item = frappe.db.get_single_value("Dairy Settings", "c_cow_milk")
		c_buf_item = frappe.db.get_single_value("Dairy Settings", "c_buf_milk")
		c_mix_item = frappe.db.get_single_value("Dairy Settings", "c_buf_milk")


		doc = frappe.get_all("Van Collection Items", ['name'])


		if self.g_cow_milk > 0:
			self.set_value_depend_milk_type(g_cow_item, stock_entry, self.rmrd_good_cow_milk, self.cow_milk_fat,
											self.cow_milk_snf,self.cow_milk_clr , route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_buf_milk > 0:
			self.set_value_depend_milk_type(g_buf_item, stock_entry, self.rmrd_good_buf_milk, self.buf_milk_fat,
											self.buf_milk_snf,self.buf_milk_clr, route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_mix_milk > 0:
			self.set_value_depend_milk_type(g_mix_item, stock_entry, self.rmrd_good_mix_milk, self.mix_milk_fat,
											self.mix_milk_snf, self.mix_milk_clr,route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)


		if self.g_cow_milk > 0:
			self.set_value_depend_milk_type(s_cow_item, stock_entry, self.s_cow_milk, self.cow_milk_fat,
											self.cow_milk_snf,self.cow_milk_clr , route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_buf_milk > 0:
			self.set_value_depend_milk_type(s_buf_item, stock_entry,self.s_buf_milk,self.buf_milk_fat,
											self.buf_milk_snf,self.buf_milk_clr, route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_mix_milk > 0:
			self.set_value_depend_milk_type(s_mix_item, stock_entry, self.s_mix_milk, self.mix_milk_fat,
											self.mix_milk_snf, self.mix_milk_clr, route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_cow_milk > 0:
			self.set_value_depend_milk_type(c_cow_item, stock_entry, self.c_cow_milk, self.cow_milk_fat,
											self.cow_milk_snf,self.cow_milk_clr, route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_buf_milk > 0:
			self.set_value_depend_milk_type(c_buf_item, stock_entry, self.c_buf_milk, self.buf_milk_fat,
											self.buf_milk_snf,self.buf_milk_clr, route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_mix_milk > 0:
			self.set_value_depend_milk_type(c_mix_item, stock_entry, self.c_mix_milk, self.mix_milk_fat,
											self.mix_milk_snf, self.mix_milk_clr, route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)


		print('clr make stock entry*********************',rmrd.t_cow_m_clr,rmrd.t_buf_m_clr,rmrd.t_mix_m_clr)
		print('stock entry^^^^^^^^^^^^^^^^^^^^^^^',stock_entry.name)
		# stock_entry.insert()
		# stock_entry.db_update()
		
		# if not rmrd.inspection_required:
		# 	stock_entry.submit()
		self.db_set('stock_entry',stock_entry.name)

		# result = frappe.db.sql("""select sed.* from `tabStock Entry` as se 
		# 						join `tabStock Entry Detail` as sed on sed.parent = se.name
		# 						where se.rmrd = '{0}' and posting_date = '{1}'""".format(self.rmrd,self.date), as_dict=True)

		# print('result make stock entry************************',result)
		return stock_entry


	def set_value_depend_milk_type(self, item_name, stock_entry, milk_collected, fat, clr,snf, route, source_warehouse,cost_center, expense_account, dcs,perpetual_inventory=None):
		# doc = frappe.get_all("Van Collection Items",{'dcs':1} ,['dcs'])
		item = frappe.get_doc("Item", item_name)
		if milk_collected > 0:
			rmrd = frappe.get_doc("RMRD", self.rmrd)
			item = frappe.get_doc("Item", item_name)
			print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@',cost_center,clr)
			se_child = stock_entry.append('items')
			se_child.item_code = item.item_code
			se_child.item_name = item.item_name
			se_child.uom = item.stock_uom
			se_child.stock_uom = item.stock_uom
			se_child.qty = milk_collected
			# se_child.fat = (milk_collected * item.weight_per_unit) * (fat/100)
			# se_child.clr = (milk_collected * item.weight_per_unit) * (clr/100)
			se_child.fat = (milk_collected * item.weight_per_unit) * (fat/100)
			se_child.fat_per = fat
			se_child.snf_clr = (milk_collected * item.weight_per_unit) * (snf/100)
			se_child.snf_clr_per = snf
			se_child.snf = (milk_collected * item.weight_per_unit) * (clr/100)
			se_child.snf_per = clr
			if stock_entry.purpose == "Material Transfer":
				se_child.s_warehouse = route.source_warehouse
			se_child.t_warehouse = rmrd.target_warehouse
			se_child.basic_rate = item.valuation_rate
			# in stock uom
			se_child.transfer_qty = milk_collected
			print('Printtttttttttttttttttt',cost_center,clr)
			se_child.cost_center = cost_center
			se_child.expense_account = expense_account if perpetual_inventory else None





	@frappe.whitelist()
	def creatr_stockrmrd(self):
		rmrd = frappe.get_doc("RMRD", self.rmrd)
		print('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!',rmrd.date)
		# if rmrd.t_g_cow_wt > 0 or rmrd.t_g_buf_wt > 0 or rmrd.t_g_mix_wt > 0:
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.purpose = "Material Transfer"
		stock_entry.stock_entry_type = "Material Transfer"
		stock_entry.set_posting_time = 1
		stock_entry.posting_date = self.date
		stock_entry.rmrd = rmrd.name
		stock_entry.rmrd_lines = self.name
		# stock_entry.set_posting_time = 0
		stock_entry.docstatus = 1
		stock_entry.status = "Submited"

		stock_entry.company = rmrd.company
		stock_entry.rmrd = rmrd.name

		route = frappe.get_doc("Route Master", rmrd.route)

		cost_center = frappe.get_cached_value('Company', self.company, 'cost_center')
		print('cost center make stock entry****************',cost_center)
		perpetual_inventory = frappe.get_cached_value('Company', self.company, 'enable_perpetual_inventory')
		expense_account = frappe.get_cached_value('Company', self.company, 'stock_adjustment_account')

		g_cow_item = frappe.db.get_single_value("Dairy Settings", "cow_pro")
		g_buf_item = frappe.db.get_single_value("Dairy Settings", "buf_pro")
		g_mix_item = frappe.db.get_single_value("Dairy Settings", "mix_pro")

		s_cow_item = frappe.db.get_single_value("Dairy Settings", "s_cow_milk")
		s_buf_item = frappe.db.get_single_value("Dairy Settings", "s_buf_milk")
		s_mix_item = frappe.db.get_single_value("Dairy Settings", "s_mix_milk")

		c_cow_item = frappe.db.get_single_value("Dairy Settings", "c_cow_milk")
		c_buf_item = frappe.db.get_single_value("Dairy Settings", "c_buf_milk")
		c_mix_item = frappe.db.get_single_value("Dairy Settings", "c_buf_milk")


		doc = frappe.get_all("Van Collection Items", ['name'])


		if self.g_cow_milk > 0:
			self.set_value_depend_milk_type(g_cow_item, stock_entry, self.rmrd_good_cow_milk, self.cow_milk_fat,
											self.cow_milk_snf,self.cow_milk_clr , route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_buf_milk > 0:
			self.set_value_depend_milk_type(g_buf_item, stock_entry, self.rmrd_good_buf_milk, self.buf_milk_fat,
											self.buf_milk_snf,self.buf_milk_clr, route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_mix_milk > 0:
			self.set_value_depend_milk_type(g_mix_item, stock_entry, self.rmrd_good_mix_milk, self.mix_milk_fat,
											self.mix_milk_snf, self.mix_milk_clr,route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)


		if self.g_cow_milk > 0:
			self.set_value_depend_milk_type(s_cow_item, stock_entry, self.s_cow_milk, self.cow_milk_fat,
											self.cow_milk_snf,self.cow_milk_clr , route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_buf_milk > 0:
			self.set_value_depend_milk_type(s_buf_item, stock_entry,self.s_buf_milk,self.buf_milk_fat,
											self.buf_milk_snf,self.buf_milk_clr, route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_mix_milk > 0:
			self.set_value_depend_milk_type(s_mix_item, stock_entry, self.s_mix_milk, self.mix_milk_fat,
											self.mix_milk_snf, self.mix_milk_clr, route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_cow_milk > 0:
			self.set_value_depend_milk_type(c_cow_item, stock_entry, self.c_cow_milk, self.cow_milk_fat,
											self.cow_milk_snf,self.cow_milk_clr, route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_buf_milk > 0:
			self.set_value_depend_milk_type(c_buf_item, stock_entry, self.c_buf_milk, self.buf_milk_fat,
											self.buf_milk_snf,self.buf_milk_clr, route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)

		if self.g_mix_milk > 0:
			self.set_value_depend_milk_type(c_mix_item, stock_entry, self.c_mix_milk, self.mix_milk_fat,
											self.mix_milk_snf, self.mix_milk_clr, route, rmrd.target_warehouse, cost_center, expense_account, perpetual_inventory,self.dcs)


		print('clr make stock entry*********************',rmrd.t_cow_m_clr,rmrd.t_buf_m_clr,rmrd.t_mix_m_clr)
		print('stock entry^^^^^^^^^^^^^^^^^^^^^^^',stock_entry.name)
		# stock_entry.insert()
		# stock_entry.db_update()
		
		# if not rmrd.inspection_required:
		# 	stock_entry.submit()
		self.db_set('stock_entry',stock_entry.name)

		# result = frappe.db.sql("""select sed.* from `tabStock Entry` as se 
		# 						join `tabStock Entry Detail` as sed on sed.parent = se.name
		# 						where se.rmrd = '{0}' and posting_date = '{1}'""".format(self.rmrd,self.date), as_dict=True)

		# print('result make stock entry************************',result)
		stock_entry.save()
		return stock_entry


	def set_value_depend_milk_type(self, item_name, stock_entry, milk_collected, fat, clr,snf, route, source_warehouse,cost_center, expense_account, dcs,perpetual_inventory=None):
		# doc = frappe.get_all("Van Collection Items",{'dcs':1} ,['dcs'])
		item = frappe.get_doc("Item", item_name)
		if milk_collected > 0:
			rmrd = frappe.get_doc("RMRD", self.rmrd)
			item = frappe.get_doc("Item", item_name)
			print('@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@',cost_center,clr)
			se_child = stock_entry.append('items')
			se_child.item_code = item.item_code
			se_child.item_name = item.item_name
			se_child.uom = item.stock_uom
			se_child.stock_uom = item.stock_uom
			se_child.qty = milk_collected
			# se_child.fat = (milk_collected * item.weight_per_unit) * (fat/100)
			# se_child.clr = (milk_collected * item.weight_per_unit) * (clr/100)
			se_child.fat = (milk_collected * item.weight_per_unit) * (fat/100)
			se_child.fat_per = fat
			se_child.snf_clr = (milk_collected * item.weight_per_unit) * (snf/100)
			se_child.snf_clr_per = snf
			se_child.snf = (milk_collected * item.weight_per_unit) * (clr/100)
			se_child.snf_per = clr
			if stock_entry.purpose == "Material Transfer":
				se_child.s_warehouse = route.source_warehouse
			se_child.t_warehouse = rmrd.target_warehouse
			se_child.basic_rate = item.valuation_rate
			# in stock uom
			se_child.transfer_qty = milk_collected
			print('Printtttttttttttttttttt',cost_center,clr)
			se_child.cost_center = cost_center
			se_child.expense_account = expense_account if perpetual_inventory else None