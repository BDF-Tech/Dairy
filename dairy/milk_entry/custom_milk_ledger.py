# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

from __future__ import unicode_literals
from itertools import count

import frappe
from frappe.utils import cint, flt
from erpnext.stock.utils import update_included_uom_in_report
from frappe import _


def execute(filters=None):
	include_uom = filters.get("include_uom")
	columns = get_columns()
	items = get_items(filters)
	sl_entries = get_stock_ledger_entries(filters, items)
	item_details = get_item_details(items, sl_entries, include_uom)
	opening_row = get_opening_balance(filters, columns)
	precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))
	
	data = []
	conversion_factors = []
	if opening_row:
		data.append(opening_row)

	# actual_qty = stock_value = 0
	print('item details-----------------------',item_details)

	for sle in sl_entries:
		
		item_detail = item_details[sle.item_code]

		sle.update(item_detail)

		if filters.get("batch_no"):
			actual_qty += flt(sle.actual_qty, precision)
			# stock_value += sle.stock_value_difference

			if sle.voucher_type == 'Stock Reconciliation' and not sle.actual_qty:
				actual_qty = sle.qty_after_transaction
				# stock_value = sle.stock_value

			sle.update({
				"qty_after_transaction": abs(actual_qty)
				# "stock_value": stock_value
			})
		a = max(sle.mle_act_qty, 0)
		b =  min(sle.mle_act_qty, 0)
		sle.update({
			"in_wt": abs(a),
			"out_wt": abs(b)
		})
		e = max(sle.fat, 0)
		f = min(sle.fat, 0)
		sle.update({
			"in_fat": abs(e),
			"out_fat": abs(f)
		})
		c =  max(sle.snf, 0)
		d = min(sle.snf, 0)
		sle.update({
			"in_snf": abs(c),
			"out_snf": abs(d)
		})
		
		h =  max(sle.sle_act_qty ,0)
		i = min(sle.sle_act_qty,0)
		sle.update({
			"in_qty": abs(h),
			"out_qty": abs(i)
		})
		if sle.voucher_type == 'Purchase Receipt':
			purchase = frappe.db.get_value('Purchase Receipt',{'name':sle.voucher_no},['shift'])
			sle.update({
				"shift":purchase
			})

		if sle.voucher_type == 'Stock Entry':
			van_shift= frappe.db.get_value('Van Collection Items',{'gate_pass':sle.voucher_no},['shift'])
			if van_shift:
				sle.update({
					"shift":van_shift
				})
				
			rmrd_shift= frappe.db.get_all('RMRD Lines',{'stock_entry':sle.voucher_no},['shift'])
			if rmrd_shift:
				sle.update({
					"shift":rmrd_shift
				})

		if sle.voucher_type == 'Purchase Invoice':
			p_invoice = frappe.db.get_value('Purchase Invoice',{'name':sle.voucher_no},['shift'])
			sle.update({
				"shift":p_invoice
			})	
			
		if sle.voucher_type == 'Sales Invoice':
			s_invoice = frappe.db.get_value('Sales Invoice',{'name':sle.voucher_no},['shift'])
			sle.update({
				"shift":s_invoice
			})

		if sle.voucher_type == 'Delivery Note':
			d_note = frappe.db.get_value('Delivery Note',{'name':sle.voucher_no},['shift'])
			sle.update({
				"shift":d_note
			})
	
		data.append(sle)
		if include_uom:
			conversion_factors.append(item_detail.conversion_factor)

	update_included_uom_in_report(columns, data, include_uom, conversion_factors)
	return columns, data


def get_columns():
	columns = [
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Datetime", "width": 150},
		{"label": _("Item"), "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 100},
		{"label": _("Item Name"), "fieldname": "item_name", "width": 100},
		{"label": _("Shift") , "fieldname": "shift" , "width": 100},
		{"label": _("Stock UOM"), "fieldname": "stock_uom", "fieldtype": "Link", "options": "UOM", "width": 90},
		{"label": _("Fat%"), "fieldname": "fat_per", "fieldtype": "float", "width": 90},
		{"label": _("In Fat"), "fieldname": "in_fat", "fieldtype": "float", "width": 90},
		{"label": _("Out Fat"), "fieldname": "out_fat", "fieldtype": "float", "width": 90},
		{"label": _("Balance Fat (in Kg)"), "fieldname": "fat_after_transaction", "fieldtype": "float", "width": 120},
		{"label": _("SNF%"), "fieldname": "snf_per", "fieldtype": "float", "width": 90},
		{"label": _("In SNF"), "fieldname": "in_snf", "fieldtype": "float", "width": 90},
		{"label": _("Out SNF"), "fieldname": "out_snf", "fieldtype": "float", "width": 90},
		{"label": _("Balance SNF (in Kg)"), "fieldname": "snf_after_transaction", "fieldtype": "float", "width": 120},
		{"label": _("In wt"), "fieldname": "in_wt", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Out wt"), "fieldname": "out_wt", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Balance wt"), "fieldname": "qty_after_transaction", "fieldtype": "Float", "width": 100, "convertible": "qty"},
		{"label": _("In Qty"), "fieldname": "in_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Out Qty"), "fieldname": "out_qty", "fieldtype": "Float", "width": 80, "convertible": "qty"},
		{"label": _("Balance Qty"), "fieldname": "balance_qty", "fieldtype": "Float", "width": 100, "convertible": "qty"},
		{"label": _("Voucher #"), "fieldname": "voucher_no", "fieldtype": "Dynamic Link", "options": "voucher_type", "width": 150},
		{"label": _("Warehouse"), "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
		{"label": _("Item Group"), "fieldname": "item_group", "fieldtype": "Link", "options": "Item Group", "width": 100},
		{"label": _("Description"), "fieldname": "description", "width": 200},
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "width": 110},
		{"label": _("Batch"), "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 100},
		{"label": _("Serial #"), "fieldname": "serial_no", "fieldtype": "Link", "options": "Serial No", "width": 100},
		{"label": _("Project"), "fieldname": "project", "fieldtype": "Link", "options": "Project", "width": 100},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 110}
	]

	return columns


def get_stock_ledger_entries(filters, items):
	item_conditions_sql = ''
	if items:
		item_conditions_sql = 'and sle.item_code in ({})'\
			.format(', '.join([frappe.db.escape(i) for i in items]))

	sl_entries = frappe.db.sql("""
		SELECT mle.voucher_no,
			concat_ws(" ", mle.posting_date, mle.posting_time) AS date,
			mle.item_code,
			mle.warehouse,
			mle.actual_qty as mle_act_qty,
			sle.qty_after_transaction,
			# stock_value,
			mle.voucher_type,
			mle.fat_per,
			mle.snf_per,
			mle.batch_no,
			mle.serial_no,
			mle.company,
			mle.project,
			mle.fat,
			mle.snf,
			mle.fat_after_transaction,
			sle.qty_after_transaction,
			mle.snf_after_transaction,
			sle.actual_qty as sle_act_qty,
			sle.qty_after_transaction as balance_qty
		FROM
			`tabMilk Ledger Entry` as mle
		join `tabStock Ledger Entry` as sle
		WHERE
			mle.company = %(company)s
				AND mle.posting_date BETWEEN %(from_date)s AND %(to_date)s
				{sle_conditions}
				{item_conditions_sql} and sle.warehouse = mle.warehouse and sle.item_code = mle.item_code and sle.posting_date = mle.posting_date 
				and  sle.voucher_no = mle.voucher_no
		ORDER BY
			mle.posting_date asc, mle.posting_time asc, mle.creation asc
		""".format(sle_conditions=get_sle_conditions(filters), item_conditions_sql=item_conditions_sql),
		filters, as_dict=1)

	
	return sl_entries


def get_items(filters):
	conditions = []
	if filters.get("item_code"):
		conditions.append("item.name=%(item_code)s")
	else:
		# if filters.get("brand"):
		# 	conditions.append("item.brand=%(brand)s")
		if filters.get("item_group"):
			conditions.append(get_item_group_condition(filters.get("item_group")))

	items = []
	if conditions:
		items = frappe.db.sql_list("""select name from `tabItem` item where {}"""
			.format(" and ".join(conditions)), filters)
	# print('items********************************',items)
	return items


def get_item_details(items, sl_entries, include_uom):
	item_details = {}

	if not items:
		items = list(set([d.item_code for d in sl_entries]))
		

	if not items:
		return item_details

	cf_field = cf_join = ""
	if include_uom:
		cf_field = ", ucd.conversion_factor"
		cf_join = "left join `tabUOM Conversion Detail` ucd on ucd.parent=item.name and ucd.uom=%s" \
			% frappe.db.escape(include_uom)
		

	# print('query-----------------------------',"""
	# 	select
	# 		item.name, item.item_name, item.description, item.item_group, item.brand, item.stock_uom {cf_field},item.milk_ledger
	# 	from
	# 		`tabItem` item
	# 		{cf_join}
	# 	where
	# 		item.name in ({item_codes}) and item.milk_ledger = 1
	# """.format(cf_field=cf_field, cf_join=cf_join, item_codes=','.join(['%s'] *len(items))), items)


	res = frappe.db.sql("""
		select
			item.name, item.item_name, item.description, item.item_group, item.brand, item.stock_uom {cf_field},item.milk_ledger
		from
			`tabItem` item
			{cf_join}
		where
			item.name in ({item_codes})
	""".format(cf_field=cf_field, cf_join=cf_join, item_codes=','.join(['%s'] *len(items))), items, as_dict=1)
	print('res-----------------------------------',)
	
	for item in res:
		item_details.setdefault(item.name, item)

	return item_details


def get_sle_conditions(filters):
	conditions = []
	if filters.get("warehouse"):
		warehouse_condition = get_warehouse_condition_mle(filters.get("warehouse"))
		if warehouse_condition:
			conditions.append(warehouse_condition)
	if filters.get("voucher_no"):
		conditions.append("sle.voucher_no=%(voucher_no)s")
	if filters.get("batch_no"):
		conditions.append("sle.batch_no=%(batch_no)s")
	if filters.get("project"):
		conditions.append("sle.project=%(project)s")

	if not filters.get("show_cancelled_entries"):
		conditions.append("sle.is_cancelled = 0")

	return "and {}".format(" and ".join(conditions)) if conditions else ""


def get_opening_balance(filters, columns):
	if not (filters.item_code and filters.warehouse and filters.from_date):
		return

	from erpnext.stock.stock_ledger import get_previous_sle
	last_entry = get_previous_sle({
		"item_code": filters.item_code,
		"warehouse_condition": get_warehouse_condition(filters.warehouse),
		"posting_date": filters.from_date,
		"posting_time": "00:00:00"
	})
	item=frappe.get_doc("Item",filters.item_code)
	a=0
	b=0
	milk_ledger_entry=frappe.db.sql("""select snf_after_transaction,fat_after_transaction  from `tabMilk Ledger Entry`
				    where item_code='{0}' and posting_date < '{1}' and   {warehouse_condition} order by creation 
					desc""".format(filters.item_code,filters.from_date,warehouse_condition=get_warehouse_condition(filters.warehouse)),as_dict=1)
	if milk_ledger_entry:
		a=milk_ledger_entry[0].get("fat_after_transaction")
		b=milk_ledger_entry[0].get("snf_after_transaction")
	row = {
		"item_code": _("'Opening'"),
		"qty_after_transaction": last_entry.get("qty_after_transaction", 0) * item.weight_per_unit ,
		"balance_qty": last_entry.get("qty_after_transaction", 0),
		"fat_after_transaction": a,
		"snf_after_transaction": b,
	}
	
	return row


def get_warehouse_condition(warehouse):
	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)
	if warehouse_details:
		return (
			" exists (select name from `tabWarehouse` wh \
			where wh.lft >= %s and wh.rgt <= %s and warehouse=wh.name)"
			% (warehouse_details.lft, warehouse_details.rgt)
		)

	return ""


def get_warehouse_condition_mle(warehouse):
	warehouse_details = frappe.db.get_value("Warehouse", warehouse, ["lft", "rgt"], as_dict=1)
	if warehouse_details:
		return (
			" exists (select name from `tabWarehouse` wh \
			where wh.lft >= %s and wh.rgt <= %s  and mle.warehouse=wh.name)"
			% (warehouse_details.lft, warehouse_details.rgt)
		)

	return ""

def get_item_group_condition(item_group):
	item_group_details = frappe.db.get_value("Item Group", item_group, ["lft", "rgt"], as_dict=1)
	if item_group_details:
		return "item.item_group in (select ig.name from `tabItem Group` ig \
			where ig.lft >= %s and ig.rgt <= %s and item.item_group = ig.name)"%(item_group_details.lft,
			item_group_details.rgt)

	return ''

