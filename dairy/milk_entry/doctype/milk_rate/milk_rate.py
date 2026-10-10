# -*- coding: utf-8 -*-
# Copyright (c) 2019, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

import csv
from pydoc import doc

import frappe
from frappe.model.document import Document
from frappe.utils import flt
import pandas as pd
import frappe
import openpyxl
from frappe.utils.file_manager import get_file_path
import frappe
import csv
from frappe.model.document import Document
from frappe.utils import flt

# --- ADD THIS LINE BELOW ---
from frappe.utils.file_manager import get_file_path


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
			fat_min_cow_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "fat_min_cow_milk"))
			fat_min_buf_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "fat_min_buf_milk"))
			fat_min_mix_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "fat_min_mix_milk"))

			fat_max_cow_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "fat_max_cow_milk"))
			fat_max_buf_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "fat_max_buf_milk"))
			fat_max_mix_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "fat_max_mix_milk"))

			fat_interval_cow_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "fat_interval_cow_milk"))
			fat_interval_buf_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "fat_interval_buf_milk"))
			fat_interval_mix_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "fat_interval_mix_milk"))

			snf_min_cow_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "snf_min_cow_milk"))
			snf_min_buf_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "snf_min_buf_milk"))
			snf_min_mix_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "snf_min_mix_milk"))

			snf_max_cow_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "snf_max_cow_milk"))
			snf_max_buf_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "snf_max_buf_milk"))
			snf_max_mix_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "snf_max_mix_milk"))

			snf_interval_cow_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "snf_interval_cow_milk"))
			snf_interval_buf_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "snf_interval_buf_milk"))
			snf_interval_mix_milk = flt(frappe.db.get_single_value(
			    "Dairy Settings", "snf_interval_mix_milk"))
			if self.milk_type == 'Cow':
				fat_min = fat_min_cow_milk
				while snf_min_cow_milk <= snf_max_cow_milk:
					fat_min_cow_milk = fat_min
					while fat_min_cow_milk <= fat_max_cow_milk:
						row = self.append("milk_rate_chart", {})
						row.snf_clr = snf_min_cow_milk
						row.fat = fat_min_cow_milk
						fat_min_cow_milk += fat_interval_cow_milk
					snf_min_cow_milk += snf_interval_cow_milk

			if self.milk_type == 'Buffalo':
				fat_min = fat_min_buf_milk
				while snf_min_buf_milk <= snf_max_buf_milk:
					fat_min_buf_milk = fat_min
					while fat_min_buf_milk <= fat_max_buf_milk:
						row = self.append("milk_rate_chart", {})
						row.snf_clr = snf_min_buf_milk
						row.fat = fat_min_buf_milk
						fat_min_buf_milk += fat_interval_buf_milk
					snf_min_buf_milk += snf_interval_buf_milk

			if self.milk_type == 'Mix':
				fat_min = fat_min_mix_milk
				while snf_min_mix_milk <= snf_max_mix_milk:
					fat_min_mix_milk = fat_min
					while fat_min_mix_milk <= fat_max_mix_milk:
						row = self.append("milk_rate_chart", {})
						row.snf_clr = snf_min_mix_milk
						row.fat = fat_min_mix_milk
						fat_min_mix_milk += fat_interval_mix_milk
					snf_min_mix_milk += snf_interval_mix_milk

	@frappe.whitelist()
	def upload_the_file(self):
		if not self.attach_file:
			frappe.throw("Please attach the Excel file first.")

        # 1. Get the physical path of the file
		file_path = get_file_path(self.attach_file)

		try:
            # 2. Load the Excel Workbook
            # data_only=True ensures we get the calculated values, not formulas
			wb = openpyxl.load_workbook(file_path, data_only=True)
			sheet = wb.active  # Uses the first visible tab in the Excel file

            # 3. Clear existing child table rows
			self.set("milk_rate_chart", [])

            # 4. Extract SNF Headers (First Row, skipping the first cell)
            # We use a list comprehension to get all values in row 1 starting from column 2
			snf_headers = [cell.value for cell in sheet[1][1:]]

            # 5. Iterate through Data Rows (Starting from Row 2)
            # min_row=2 skips the header row
			for row in sheet.iter_rows(min_row=2, values_only=True):
                # row[0] is the FAT value (first column)
				fat_value = row[0]

                # If the FAT cell is empty, stop or skip
				if fat_value is None:
					continue

                # row[1:] are the Rates for each SNF column
				rates = row[1:]

				for index, rate_value in enumerate(rates):
                    # Only add if there is a valid rate and a matching SNF header
					if rate_value is not None and index < len(snf_headers):
						snf_val = snf_headers[index]
                        
						if snf_val is not None:
							self.append("milk_rate_chart", {
                                "fat": flt(fat_value),
                                "snf_clr": flt(snf_val),
                                "rate": flt(rate_value)
                            })

            # 6. Save the document
			self.save()
			frappe.msgprint("Rate chart successfully imported from Excel matrix.")

		except Exception as e:
			frappe.log_error(frappe.get_traceback(), "Milk Rate Excel Upload Failed")
			frappe.throw(f"Error reading Excel file: {str(e)}")