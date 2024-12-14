# Copyright (c) 2013, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from erpnext.controllers.trends	import get_columns,get_data
from frappe.utils import getdate


# *******************************************************
def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters):
    columns = [
        {
            "label": _("Item Group"),
            "fieldname": "item_group",
            "options": "Item Group",
            "fieldtype": "Link",
            "width": 140
        },
        {
            "label": _("Item"),
            # "options": "Item",
            "fieldname": "item_code",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "label": _("Warehouse"),
            "options": "Warehouse",
            "fieldname": "warehouse",
            "fieldtype": "Link",
            "width": 140
        },

        {
            "label": _("Delivery Shift"),
            "fieldname": "delivery_shift",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Qty"),
            "fieldname": "qty",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("UOM"),
            "options": "UOM",
            "fieldname": "uom",
            "fieldtype": "Link",
            "width": 100
        },
        {
            "label": _("Qty As Per Stock UOM"),
            "fieldname": "stock_qty",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("Stock UOM"),
            "options": "UOM",
            "fieldname": "stock_uom",
            "fieldtype": "Link",
            "width": 100
        },
        {
            "label": _("Total Weight"),
            "fieldname": "total_weight",
            "fieldtype": "Float",
            "width": 100
        },
		{
			"label": _(" Weight UOM"),
			"options": "UOM",
			"fieldname": "weight_uom",
			"fieldtype": "Link",
			"width": 100
		},
        {
            "label": _("Amount"),
            "fieldname": "amount",
            "fieldtype": "Float",
            "width": 120
        },
        {
            "label": _("Customer"),
            "fieldname": "customer",
            "options": "Customer",
            "fieldtype": "Link",
            "width": 120
        },
        {
            "label": _("Territory"),
            "fieldname": "territory",
            "options": "Territory",
            "fieldtype": "Link",
            "width": 120
        }

    ]
    return columns

def get_data(filters):
    print("======")

    # if filters:
    #     if filters.get('based_on'):
    #         q_data = frappe.db.sql( """
    #                 select
    #                     distinct( SOI.%s)
    #                 from
    #                     `tabSales Order` SO, `tabSales Order Item` SOI
    #                 where
    #                     SO.docstatus =1 and SO.name = SOI.parent
    #                     """%filters.based_on)
    #         print("********************************************", q_data)
    #         field = filters.based_on
    #         print("*****************",field)
    #         data = []
    #         for q in q_data:
    #             print("************",q)
    #             if field == "item_group":
    #                 row = {
    #                     "item_group": q[0]
    #                 }
    #                 data.append(row)
    #
    #                 p_data = frappe.db.sql(""" select SOI.item_group, SOI.item_code, SOI.item_name, SO.set_warehouse,
    #                 SO.delivery_shift, SOI.qty, SOI.stock_uom, SOI.total_weight,SOI.weight_uom, SOI.amount, SO.customer
    #                 from `tabSales Order` SO, `tabSales Order Item` SOI
    #                 where
    #                 SO.docstatus =1 and SO.name = SOI.parent and SOI.item_group = %(item_group)s
    #                  group by SOI.item_code """,{'item_group':q[0]})
    #                 for p in p_data:
    #                     row = {
    #                         # "item_group": q[0],
    #                         "item": p[1],
    #                         "item_name": p[2],
    #                         "warehouse": p[3],
    #                         "delivery_shift": p[4],
    #                         "qty": p[5],
    #                         "stock_uom": p[6],
    #                         "total_weight": p[7],
    #                         "weight_uom": p[8],
    #                         "amount":p[9],
    #                         "customer":p[10]
    #                     }
    #                     data.append(row)
    #
    #         return data

    # p_data = frappe.db.sql("""
    #                     select
    #                         distinct SOI.item_group, sum(SOI.qty),sum(SOI.total_weight), sum(SOI.amount)
    #                     from
    #                         `tabSales Order` SO, `tabSales Order Item` SOI
    #                     where
    #                         SO.docstatus =1 and SO.name = SOI.parent """)
    #
    # data = []
    # for p in p_data:
    #     row = {
    #         "item_group": p[0],
    #         "qty": p[1],
    #         "total_weight": p[2],
    #         "amount": p[3],
    #     }
    #     data.append(row)
    # ****************************************************************
    query = """
        select
            SOI.item_group, SOI.item_code, SOI.item_name, SO.set_warehouse, SO.delivery_shift, sum(SOI.qty),SOI.uom,
             sum(SOI.stock_qty), SOI.stock_uom,
            sum(SOI.total_weight),SOI.weight_uom, sum(SOI.amount), SO.customer, SO.territory
        from
            `tabSales Order` SO, `tabSales Order Item` SOI
        where
            SO.docstatus =1 
            """
    conditions = get_conditions(filters)
    grp_by = """ group by SOI.item_code """
    q_data = frappe.db.sql(query + conditions + grp_by)

    data = []
    for q in q_data:
        row = {
            "item_group": q[0],
            "item_code": q[1],
            "item_name": q[2],
            "warehouse": q[3],
            "delivery_shift": q[4],
            "qty": q[5],
            "uom":q[6],
            "stock_qty":q[7],
            "stock_uom": q[8],
            "total_weight": q[9],
            "weight_uom": q[10],
            "amount":q[11],
            "customer":q[12],
            "territory":q[13]
        }
        data.append(row)

    return data


def get_conditions(filters):
    query = """ and SO.name = SOI.parent """
    if filters:
        # query = """   and  date >= '{0}' and  date <= '{1}'  """.format(filters.from_date,filters.to_date)
        if filters.get('company'):
            query += """ and  SO.company = '%s'  """%filters.company
        if filters.get('shift'):
            query += """ and  SO.delivery_shift = '%s' """%filters.shift
        if filters.get('warehouse'):
            query += """ and  SO.set_warehouse = '%s' """%filters.warehouse
        if filters.get('from_date'):
            query += """ and  SO.delivery_date >= '%s' """%filters.from_date
        if filters.get('to_date'):
            query += """ and  SO.delivery_date <= '%s' """%filters.to_date
        if filters.get('territory'):
            query += """ and  SO.territory = '%s' """%filters.territory
        if filters.get('item_group'):
            query += """ and  SOI.item_group = '%s' """%filters.item_group

    return query