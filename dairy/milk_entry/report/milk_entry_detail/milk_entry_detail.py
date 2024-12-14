# Copyright (c) 2013, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import datetime
import frappe
from frappe import _
from datetime import datetime


def execute(filters=None):
    columns = get_columns(filters)
    data = get_data(filters)
    chart = get_chart_data(filters, columns)
    return columns, data , None, chart

def get_columns(filters):
    columns = [
        {
            "label": _("Milk Entry"),
            "fieldname": "name",
            "fieldtype": "Data",
            "width": 80
        },
        {
            "label": _("Member"),
            "options": "Supplier",
            "fieldname": "member",
            "fieldtype": "Link",
            "width": 100
        },
        {
            "label": _("DCS"),
            "options": "Warehouse",
            "fieldname": "dcs_id",
            "fieldtype": "Link",
            "width": 160
        },
        {
            "label": _("Date"),
            "fieldname": "date",
            "fieldtype": "Date",
            "width": 80
        },
        {
            "label": _("Time"),
            "fieldname": "time",
            "fieldtype": "Time",
            "width": 80
        },
        {
            "label": _("Shift"),
            "fieldname": "shift",
            "fieldtype": "Select",
            "width": 80
        },
        {
            "label": _("Milk Type"),
            "fieldname": "milk_type",
            "fieldtype": "Select",
            "width": 80
        },
        {
            "label": _("Volume"),
            "fieldname": "volume",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("FAT"),
            "fieldname": "fat",
            "fieldtype": "Float",
            "width": 60
        },
        {"label": _("FAT(in kg)"), "fieldname": "fat_kg", "fieldtype": "Float", "width": 60},
        {
            "label": _("CLR"),
            "fieldname": "clr",
            "fieldtype": "Float",
            "width": 60
        },
        {"label": _("CLR(in kg)"), "fieldname": "clr_kg", "fieldtype": "Float", "width": 60},
        {
            "label": _("SNF"),
            "fieldname": "snf",
            "fieldtype": "Float",
            "width": 60
        },
        {"label": _("SNF(in kg)"), "fieldname": "snf_kg", "fieldtype": "Float", "width": 60},
        {
            "label": _("Milk Rate"),
            "options":"Milk Rate",
            "fieldname": "milk_rate",
            "fieldtype": "Link",
            "width": 100
        },
        {
            "label": _("Unit Price"),
            "fieldname": "unit_price",
            "fieldtype": "Float",
            "width": 80
        },
        {
            "label": _("Total"),
            "fieldname": "total",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("Created By"),
            "options": "User",
            "fieldname": "owner",
            "fieldtype": "Link",
            "width": 130
        },
        {
            "label": _("Create Date"),
            "fieldname": "creation",
            "fieldtype": "Datetime",
            "width": 160
        },
        {
            "label": _("Sample Collected"),
            "options":"Raw Milk Sample",
            "fieldname": "sample",
            "fieldtype": "Link",
            "width": 100
        },
        {
            "label": _("Status"),
            "fieldname": "status",
            "fieldtype": "Select",
            "width": 80
        },
        {
            "label": _("Stock Voucher"),
            "options":"Purchase Receipt",
            "fieldname": "purchase_receipt",
            "fieldtype": "Link",
            "width": 100
        },
        {"label": _("Incentive"), "fieldname": "incentive", "fieldtype": "Currency", "width": 100},
		{"label": _("Fat Deduction"), "fieldname": "fat_deduction", "fieldtype": "Currency", "width": 100},
		{"label": _("SNF Deduction"), "fieldname": "snf_deduction", "fieldtype": "Currency", "width": 100},

    ]
    return columns

def get_data(filters):
    
    conditions = get_conditions(filters)

    query = """ select tm.name,tm.member,tm.dcs_id,tm.date,tm.time,tm.shift,tm.milk_type,tm.volume,tm.fat,tm.fat_kg,tm.clr,tm.clr_kg,tm.snf,tm.snf_kg,tm.milk_rate,tm.unit_price,tm.total, 
                tm.owner,tm.creation,tm.sample,tm.status,tp.name,tm.company,tm.incentive,tm.fat_deduction,tm.snf_deduction from  `tabMilk Entry` tm inner join `tabPurchase Receipt` tp where tp.milk_entry = tm.name """

    # print("====query",query+conditions)
    q_data = frappe.db.sql(query+conditions)
    data = []
    for q in q_data:
        row = {
            "name": q[0],
            "member": q[1],
            "dcs_id": q[2],
            "date": q[3],
            "time": q[4],
            "shift": q[5],
            "milk_type": q[6],
            "volume": q[7],
            "fat": q[8],
            "fat_kg":q[9],
            "clr": q[10],
            "clr_kg":q[11],
            "snf":q[12],
            "snf_kg":q[13],
            "milk_rate":q[14],
            "unit_price":q[15],
            "total": q[16],
            "owner":q[17],
            "creation":q[18],
            "sample": q[19],
            "status": q[20],
            "purchase_receipt":q[21],
            "incentive":q[23],
            "fat_deduction":q[24],
            "snf_deduction":q[25]
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


def get_chart_data(filters, columns):
    
    a =[]
    volume = []
    lbl = frappe.db.sql("""select distinct(date) , volume
                                    from `tabMilk Entry` 
                                    where date BETWEEN '{0}' and '{1}'
                                    """.format(filters.get('from_date'),filters.get('to_date')), as_dict=True)
    
    for l in lbl:
        c = l.date.strftime("%d-%m-%Y")
        a.append(c)
        labels = a
        volume.append(l.volume)
    
    b = get_data(filters)
    for vol in b:
        datasets = []
        datasets.append({"name": _("Volume"), "values": volume})
          

        chart = {"data": {"labels": labels, "datasets": datasets}}

        chart["type"] = "line"
        
        return chart
