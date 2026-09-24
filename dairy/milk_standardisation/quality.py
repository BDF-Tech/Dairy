# Copyright (c) 2026, BDF and contributors
# For license information, please see license.txt

"""Keep FAT/SNF on the milk wherever it moves.

The Milk Ledger is built from the FAT/SNF columns on each transaction line, so a line
that leaves them empty silently drops that milk's fat out of the silo's balance. These
hooks fill them in:

* a Purchase Receipt into a silo must state FAT % and SNF %, and the kg follow from it
* a Stock Entry taking milk out of a silo inherits the silo's current quality

Percentages are by weight, so kg FAT = quantity in kg x FAT %. Quantities are converted
to kg with the item's Weight Per Unit (1.03 for milk stocked in litres).
"""

import frappe
from frappe import _
from frappe.utils import flt

from dairy.milk_standardisation.doctype.milk_standardisation.milk_standardisation import kg_per_stock_unit
from dairy.milk_standardisation.silo import get_quality, is_silo


def tracks_quality(item_code):
	return bool(item_code) and bool(frappe.db.get_value("Item", item_code, "maintain_fat_snf_clr"))


def qty_in_kg(item_code, stock_qty):
	return flt(stock_qty) * kg_per_stock_unit(item_code)


def purchase_receipt_quality(doc, method=None):
	"""Milk bought into a silo must carry its FAT/SNF; the kg are worked out here."""
	missing = []
	for row in doc.items:
		if not (tracks_quality(row.item_code) and is_silo(row.warehouse)):
			continue
		fat, snf = flt(row.get("fat_per_")), flt(row.get("snf_clr_per"))
		if not (fat and snf):
			missing.append(f"#{row.idx} {row.item_code}")
			continue
		kg = qty_in_kg(row.item_code, row.stock_qty or row.qty)
		# On Purchase Receipt Item the kg columns are named confusingly: `clr` carries
		# kg SNF (that is the one the Milk Ledger reads) and `snf` carries kg CLR.
		row.fat = kg * fat / 100.0
		row.clr = kg * snf / 100.0
		if flt(row.get("clr_per")):
			row.snf = kg * flt(row.clr_per) / 100.0

	if missing:
		frappe.throw(
			_("Enter FAT % and SNF % for milk going into a silo: {0}.<br>"
			  "Without them the silo's quality cannot be worked out.").format(", ".join(missing))
		)


def stock_entry_quality(doc, method=None):
	"""Milk leaving a silo carries that silo's quality, unless someone typed their own."""
	for row in doc.items:
		if not tracks_quality(row.item_code) or flt(row.get("fat_per")) or flt(row.get("snf_per")):
			continue
		source = row.s_warehouse
		if not (source and is_silo(source)):
			continue

		silo = get_quality(source, row.item_code)
		if not (silo.fat or silo.snf):
			continue

		kg = qty_in_kg(row.item_code, row.transfer_qty or row.qty)
		row.fat_per = silo.fat
		row.snf_per = silo.snf
		row.fat = kg * silo.fat / 100.0
		row.snf = kg * silo.snf / 100.0
