# Copyright (c) 2026, BDF and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from dairy.milk_standardisation.silo import get_quality, is_silo


class SiloQualityTest(Document):
	def validate(self):
		if not is_silo(self.silo):
			frappe.throw(
				_("{0} is not a milk silo. Tick <b>Is Milk Silo</b> on the warehouse first.").format(
					frappe.bold(self.silo)
				)
			)
		if not frappe.db.get_value("Item", self.item, "maintain_fat_snf_clr"):
			frappe.throw(
				_("{0} does not track FAT/SNF. Tick <b>Maintain Fat, CLR</b> on the item first.").format(
					frappe.bold(self.item)
				)
			)
		if not self.tested_by:
			self.tested_by = frappe.session.user

		self.compare_with_book()

	def compare_with_book(self):
		"""Put the lab's reading next to what the ERP believes the silo holds."""
		book = get_quality(self.silo, self.item)
		self.book_qty = book.qty
		self.book_fat = book.fat
		self.book_snf = book.snf
		self.fat_difference = flt(self.fat) - flt(book.fat)
		self.snf_difference = flt(self.snf) - flt(book.snf)
		self.qty_difference = (flt(self.tested_qty) - flt(book.qty)) if self.tested_qty else 0.0
