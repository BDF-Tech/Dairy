# Copyright (c) 2013, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    return columns, data

def get_columns(filters):
    columns = [
        {
            "label": _("Delivery Trip"),
            "fieldname": "delivery_trip",
            "options": "Delivery Trip",
            "fieldtype": "Link",
            "width": 160
        },
        {
            "label": _("Company"),
            "options": "Company",
            "fieldname": "company",
            "fieldtype": "Link",
            "width": 140
        },
        {
            "label": _("Driver"),
            "options": "Driver",
            "fieldname": "driver",
            "fieldtype": "Link",
            "width": 160
        },
        {
            "label": _("Driver Name"),
            "fieldname": "driver_name",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Vehicle"),
            "options": "Vehicle",
            "fieldname": "vehicle",
            "fieldtype": "Link",
            "width": 160
        },

        {
            "label": _("Departure Time"),
            "fieldname": "departure_time",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": _("Total Estimated Distance"),
            "fieldname": "total_distance",
            "fieldtype": "Float",
            "width": 160
        },
        # {
        #     "label": _("Delivery Note"),
        #     "fieldname": "delivery_stop",
        #     "fieldtype": "Link",
        #     "options": "Delivery Note",
        #     "width": 160
        # },

        {
            "label": _("Customer"),
            "options": "Customer",
            "fieldname": "customer",
            "fieldtype": "Link",
            "width": 160
        },
        {
            "label": _("Delivery Note"),
            "options": "Delivery Note",
            "fieldname": "delivery_note",
            "fieldtype": "Link",
            "width": 160
        },
        {
            "label": _("Route"),
            "options": "Route Master",
            "fieldname": "route",
            "fieldtype": "Link",
            "width": 160
        },
        {
            "label": _("Item Code"),
            "options": "Item",
            "fieldname": "item_code",
            "fieldtype": "Link",
            "width": 160
        },
        {
            "label": _("Item Name"),
            "fieldname": "item_name",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "label": _("Quantity"),
            "fieldname": "qty",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "label": _("UOM"),
            "options": "UOM",
            "fieldname": "uom",
            "fieldtype": "Link",
            "width": 160
        },
        {
            "label": _("Total Weight"),
            "fieldname": "total_weight",
            "fieldtype": "Data",
            "width": 160
        },
        {
            "label": _("Crate Count"),
            "fieldname": "crate_count",
            "fieldtype": "Data",
            "width": 160
        }

    ]
    return columns

def get_data(filters):
    # print("======")


    query = """ 
        select 
            dt.name,dt.company,dt.driver,dt.driver_name,dt.vehicle,dt.departure_time,dt.total_distance,
            ds.customer,ds.delivery_note,
            dn.route,
            dni.item_code,dni.item_name,dni.qty,dni.uom,dni.total_weight,dni.crate_count,
            ds.name
        from
            `tabDelivery Trip` dt, `tabDelivery Stop` ds, `tabDelivery Note` dn, `tabDelivery Note Item` dni
        where 
            dt.docstatus =1 and dt.name = ds.parent and ds.delivery_note = dn.name and dn.name = dni.parent
            """
    # conditions = get_conditions(filters)
    # print("====query",query+conditions)
    q_data = frappe.db.sql(query)
    data = []
    for q in q_data:
        row = {
            "delivery_trip": q[0],
            "company": q[1],
            "vehicle": q[4],
            "driver": q[2],
            "driver_name": q[3],
            "departure_time": q[5],
            "total_distance": q[6],
            "customer": q[7],
            "delivery_note":q[8],
            "route": q[9],
            "item_code":q[10],
            "item_name":q[11],
            "qty":q[12],
            "uom":q[13],
            "total_weight":q[14],
            "crate_count":q[15],
            "delivery_stop":q[16]
        }
        data.append(row)

    return data


def get_conditions(filters):

    if filters:
        query = """   and  date >= '{0}' and  date <= '{1}'  """.format(filters.from_date,filters.to_date)
        if filters.get('company'):
            query += """ and  tm.company = '%s'  """%filters.company
        if filters.get('dcs'):
            query += """ and  dcs_id = '%s'  """%filters.dcs
        if filters.get('member'):
            query += """ and  member = '%s'  """%filters.member
        if filters.get('pricelist'):
            query += """ and  milk_rate = '%s'  """%filters.pricelist
        if filters.get('shift') != 'All':
            query += """ and  shift = '%s' """%filters.shift
        if filters.get('milk_type') != 'All':
            query += """ and  milk_type = '%s' """%filters.milk_type

    return query