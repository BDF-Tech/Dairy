# -*- coding: utf-8 -*-
# Copyright (c) 2019, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class MilkRate(Document):
	@frappe.whitelist()
	def get_snf_lines(self):
		if self.simplified_milk_rate == 0:
			to_remove = []
			# if self.get("__islocal"):
			for s in self.get("milk_rate_chart"):
				to_remove.append(s)
			for d in to_remove:
				self.remove(d)
			fat_min_cow_milk = flt(frappe.db.get_single_value("Dairy Settings", "fat_min_cow_milk"))
			fat_min_buf_milk = flt(frappe.db.get_single_value("Dairy Settings", "fat_min_buf_milk"))
			fat_min_mix_milk = flt(frappe.db.get_single_value("Dairy Settings", "fat_min_mix_milk"))

			fat_max_cow_milk = flt(frappe.db.get_single_value("Dairy Settings", "fat_max_cow_milk"))
			fat_max_buf_milk = flt(frappe.db.get_single_value("Dairy Settings", "fat_max_buf_milk"))
			fat_max_mix_milk = flt(frappe.db.get_single_value("Dairy Settings", "fat_max_mix_milk"))

			fat_interval_cow_milk = flt(frappe.db.get_single_value("Dairy Settings", "fat_interval_cow_milk"))
			fat_interval_buf_milk = flt(frappe.db.get_single_value("Dairy Settings", "fat_interval_buf_milk"))
			fat_interval_mix_milk = flt(frappe.db.get_single_value("Dairy Settings", "fat_interval_mix_milk"))

			snf_min_cow_milk = flt(frappe.db.get_single_value("Dairy Settings", "snf_min_cow_milk"))
			snf_min_buf_milk = flt(frappe.db.get_single_value("Dairy Settings", "snf_min_buf_milk"))
			snf_min_mix_milk = flt(frappe.db.get_single_value("Dairy Settings", "snf_min_mix_milk"))

			snf_max_cow_milk = flt(frappe.db.get_single_value("Dairy Settings", "snf_max_cow_milk"))
			snf_max_buf_milk = flt(frappe.db.get_single_value("Dairy Settings", "snf_max_buf_milk"))
			snf_max_mix_milk = flt(frappe.db.get_single_value("Dairy Settings", "snf_max_mix_milk"))

			snf_interval_cow_milk = flt(frappe.db.get_single_value("Dairy Settings", "snf_interval_cow_milk"))
			snf_interval_buf_milk = flt(frappe.db.get_single_value("Dairy Settings", "snf_interval_buf_milk"))
			snf_interval_mix_milk = flt(frappe.db.get_single_value("Dairy Settings", "snf_interval_mix_milk"))
			if self.milk_type =='Cow':
				fat_min = fat_min_cow_milk
				while snf_min_cow_milk <= snf_max_cow_milk:
					fat_min_cow_milk = fat_min
					while fat_min_cow_milk <= fat_max_cow_milk:
						row = self.append("milk_rate_chart", {})
						row.snf_clr = snf_min_cow_milk
						row.fat = fat_min_cow_milk
						fat_min_cow_milk += fat_interval_cow_milk
					snf_min_cow_milk += snf_interval_cow_milk
				

			if self.milk_type =='Buffalo':
				fat_min = fat_min_buf_milk
				while snf_min_buf_milk <= snf_max_buf_milk:
					fat_min_buf_milk = fat_min
					while fat_min_buf_milk <= fat_max_buf_milk:
						row = self.append("milk_rate_chart", {})
						row.snf_clr = snf_min_buf_milk
						row.fat = fat_min_buf_milk
						fat_min_buf_milk += fat_interval_buf_milk
					snf_min_buf_milk += snf_interval_buf_milk

			if self.milk_type =='Mix':
				fat_min = fat_min_mix_milk
				while snf_min_mix_milk <= snf_max_mix_milk:
					fat_min_mix_milk = fat_min
					while fat_min_mix_milk <= fat_max_mix_milk:
						row = self.append("milk_rate_chart", {})
						row.snf_clr = snf_min_mix_milk
						row.fat = fat_min_mix_milk
						fat_min_mix_milk += fat_interval_mix_milk
					snf_min_mix_milk += snf_interval_mix_milk




