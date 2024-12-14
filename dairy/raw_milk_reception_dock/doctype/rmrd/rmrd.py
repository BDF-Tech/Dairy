# -*- coding: utf-8 -*-
# Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class RMRD(Document):

	@frappe.whitelist()
	def submit_rmrd(self):
		self.db_set('status','Submitted')

	def before_cancel(self):
		rl = frappe.get_all('RMRD Lines',{'rmrd':self.name},['name'])
		for dl in rl:
			dlt = frappe.delete_doc('RMRD Lines',dl.name)
			print('dlt**************',dlt)
		stock = frappe.get_all('Stock Entry',{'rmrd':self.name},['name'])
		for se in stock:
			stock_dlt = frappe.delete_doc('Stock Entry',se.name)
			print('stock_dlt^^^^^^^^^^^^^^^^',stock_dlt)
			

	@frappe.whitelist()
	def start_rmrd(self):
		entry = frappe.get_doc('Dairy Settings')
		# result1 = frappe.db.sql("""select sum(cow_milk_collected) as cow_collected,
		# 						sum(buffalow_milk_collected) as buf_collected,
		# 						sum(mix_milk_collected) as mix_collected,
		# 						sum(cow_milk_cans) as cow_m_cans,
		# 						sum(buf_milk_cans) as buf_m_cans,
		# 						sum(mix_milk_cans) as mix_m_cans,

		# 						dcs 
		# 						from `tabVan Collection Items` 
		# 						where route =%s and shift =%s and date =%s and gate_pass is not null
		# 						group by dcs
		# 						""", (self.route, self.shift, self.date), as_dict=True)

		result1 = frappe.db.sql("""select sum(cow_milk_collected) as cow_collected,
								sum(buffalow_milk_collected) as buf_collected,
								sum(mix_milk_collected) as mix_collected,
								dcs 
								from `tabVan Collection Items` 
								where route =%s and shift =%s and to_shift= %s and date =%s and to_date = %s and gate_pass is not null
								group by dcs
								""", (self.route, self.shift,self.to_shift,self.date ,self.to_date), as_dict=True)

		print('result1****************************************',result1)
					
		if not result1:
			frappe.throw("Collection Not found!")

		

		for res in result1:
			clrs = frappe.db.sql("""select 
								(sed.fat_per) ,
								(sed.snf),
								(sed.fat),
								(sed.snf_clr),
								(sed.snf_clr_per),
								(sed.snf_per),
								itm.name,
								sed.s_warehouse
								from `tabStock Entry Detail` as sed 
								join `tabStock Entry` as se on se.name = sed.parent 
								join `tabItem` as itm on itm.name = sed.item_code
								where se.posting_date =%s and sed.s_warehouse = %s and se.docstatus = 1
								""", ( self.date ,res.get('dcs')), as_dict=True)
			
			print('clrs**************************************',clrs)
			doc = frappe.new_doc("RMRD Lines")
			doc.g_cow_milk = res.get('cow_collected')
			doc.g_buf_milk = res.get('buf_collected')
			doc.g_mix_milk = res.get('mix_collected')
			# doc.g_cow_milk_can = res.get('cow_m_cans')
			# doc.g_buf_milk_can = res.get('buf_m_cans')
			# doc.g_mix_milk_can = res.get('mix_m_cans')

			doc.dcs = res.get('dcs')
			print("dcssss***************************",res.get('dcs'))
			doc.rmrd = self.name
			for c in clrs:
				if doc.dcs == c.get('s_warehouse'):
					print('c warehouse********************',c.get('s_warehouse'),c.get('name'))
					if c.get('name') == entry.cow_pro:
						doc.cow_milk_fat = c.get('fat_per')
						doc.cow_milk_fat_kg = c.get('fat')
						doc.cow_milk_snf_kg = c.get('snf_clr')
						doc.cow_milk_snf = c.get('snf_clr_per')
						doc.cow_milk_clr = c.get('snf_per')
						doc.cow_milk_clr_kg = c.get('snf') 
					

					if c.get('name') == entry.buf_pro:
						doc.buf_milk_fat = c.get('fat_per')
						doc.buf_milk_fat_kg = c.get('fat')
						doc.buf_milk_snf_kg = c.get('snf')
						doc.buf_milk_snf = c.get('snf_per')
						doc.buf_milk_clr = c.get('snf_clr_per') 
						doc.buffalo_milk_clr_kg = c.get('snf_clr')


					if c.get('name') == entry.mix_pro:
						doc.mix_milk_fat = c.get('fat_per')
						doc.mix_milk_fat_kg = c.get('fat')
						doc.mix_milk_snf_kg = c.get('snf_clr')
						doc.mix_milk_snf = c.get('snf_clr_per')
						doc.mix_milk_clr = c.get('snf_per')
						doc.mix_milk_clr_kg = c.get('snf')

			result2 = frappe.db.sql("""select count(*) as sam_count,milk_type from `tabMulti Row Milk Sample` where parent in
									(select name from `tabVan Collection Items`
									where route =%s and shift =%s and to_shift = %s and date =%s and to_date = %s and dcs =%s) group by milk_type""",
									(self.route, self.shift,self.to_shift, self.date,self.to_date,res.get('dcs')), as_dict=True)
			for res in result2:
				if res.get('milk_type') == 'Cow':
					doc.cow_milk_sam = res.get('sam_count')
				if res.get('milk_type') == 'Buffalo':
					doc.buf_milk_sam = res.get('sam_count')
				if res.get('milk_type') == 'Mix':
					doc.mix_milk_sam = res.get('sam_count')
			doc.insert(ignore_permissions=True)
			# doc.calculate_total_cans_wt()
			self.db_update()
			self.db_set('status', 'In-Progress')
			self.flags.ignore_validate_update_after_submit = True  # ignore after submit permission
			self.save(ignore_permissions=True)
		# self.hide_start_rmrd_button = 1
		return True
		# self.db_update()

	@frappe.whitelist()
	def change_status_complete1(self):
		result = frappe.db.sql("""select sum(rmrd_good_cow_milk) as g_cow,
								sum(rmrd_good_buf_milk) as g_buf,
								sum(rmrd_good_mix_milk) as g_mix, 
								sum(g_cow_milk_can) as g_cow_can, 
								sum(g_buf_milk_can) as g_buf_can, 
								sum(g_mix_milk_can) as g_mix_can,
								
								sum(s_cow_milk) as s_cow,
								sum(s_buf_milk) as s_buf,
								sum(s_mix_milk) as s_mix,
								sum(s_cow_milk_can) as s_cow_can,
								sum(s_buf_milk_can) as s_buf_can,
								sum(s_mix_milk_can) as s_mix_can,
								
								sum(c_cow_milk) as c_cow,
								sum(c_buf_milk) as c_buf,
								sum(c_mix_milk) as c_mix,
								sum(c_cow_milk_can) as c_cow_can,
								sum(c_buf_milk_can) as c_buf_can,
								sum(c_mix_milk_can) as c_mix_can,
								
								sum(cow_milk_sam) as cow_milk_sam,
								sum(buf_milk_sam) as buf_milk_sam,
								sum(mix_milk_sam) as mix_milk_sam,
								
								sum(cow_milk_fat) as cow_milk_fat,
								sum(buf_milk_fat) as buf_milk_fat,
								sum(mix_milk_fat) as mix_milk_fat,
								
								sum(cow_milk_clr) as cow_milk_clr,
								sum(buf_milk_clr) as buf_milk_clr,
								sum(mix_milk_clr) as mix_milk_clr,

								sum(cow_milk_clr_kg) as cow_milk_clr_kg,
								sum(cow_milk_fat_kg) as cow_milk_fat_kg,
								sum(buffalo_milk_clr_kg) as buf_milk_clr_kg,
								sum(buf_milk_fat_kg) as buf_milk_fat_kg,
								sum(mix_milk_clr_kg) as mix_milk_clr_kg,
								sum(mix_milk_fat_kg) as mix_milk_fat_kg,

								rmrd
								from `tabRMRD Lines` where rmrd =%s
								group by rmrd""",(self.name), as_dict=True)

		print('result*******************',result)
		for res in result:
			self.t_g_cow_wt = res.get('g_cow')
			self.t_g_buf_wt = res.get('g_buf')
			self.t_g_mix_wt = res.get('g_mix')

			self.t_g_cow_can = res.get('g_cow_can')
			self.t_g_buf_can = res.get('g_buf_can')
			self.t_g_mix_can = res.get('g_mix_can')

			self.t_s_cow_wt = res.get('s_cow')
			self.t_s_buf_wt = res.get('s_buf')
			self.t_s_mix_wt = res.get('s_mix')

			self.t_s_cow_can = res.get('s_cow_can')
			self.t_s_buf_can = res.get('s_buf_can')
			self.t_s_mix_can = res.get('s_mix_can')

			self.t_c_cow_wt = res.get('c_cow')
			self.t_c_buf_wt = res.get('c_buf')
			self.t_c_mix_wt = res.get('c_mix')

			self.t_c_cow_can = res.get('c_cow_can')
			self.t_c_buf_can = res.get('c_buf_can')
			self.t_c_mix_can = res.get('c_mix_can')

			self.t_cow_sam = res.get('cow_milk_sam')
			self.t_buf_sam = res.get('buf_milk_sam')
			self.t_mix_sam = res.get('mix_milk_sam')

			self.t_cow_m_fat = res.get('cow_milk_fat')
			self.t_cow_m_fat_kg = res.get('cow_milk_fat_kg')
			self.t_buf_m_fat = res.get('buf_milk_fat')
			self.t_buf_m_fat_kg = res.get('buf_milk_fat_kg')
			self.t_mix_m_fat = res.get('mix_milk_fat')
			self.t_mix_m_fat_kg = res.get('mix_milk_fat_kg')

			self.t_cow_m_clr = res.get('cow_milk_clr')
			self.t_cow_m_clr_kg = res.get('cow_milk_clr_kg')
			self.t_buf_m_clr = res.get('buf_milk_clr')
			self.t_buf_m_clr_kg = res.get('buf_milk_clr_kg')
			self.t_mix_m_clr = res.get('mix_milk_clr')
			self.t_mix_m_clr_kg = res.get('mix_milk_clr_kg')
			self.db_update()
			self.db_set('status', 'Completed')
			self.flags.ignore_validate_update_after_submit = True  # ignore after submit permission
			self.save(ignore_permissions=True)

		line_ids = frappe.db.sql("""select name from `tabRMRD Lines` where rmrd =%s""", (self.name), as_dict =True)
		print('line****************************************',line_ids)
		for res in line_ids:
		
			doc =frappe.get_doc("RMRD Lines",res.get("name"))
			if doc:
				doc.submit()	


