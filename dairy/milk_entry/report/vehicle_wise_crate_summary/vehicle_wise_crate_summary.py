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
            "fieldname": "crate_type",
            "fieldtype": "Link",
            "label": "Crate Type",
            "options": "Crate Type",
            "width": 100
        },
        {
            "fieldname": "crate_opening",
            "fieldtype": "Int",
            "label": "Crate Opening",
            "width": 80
        },
        {
            "fieldname": "crate_issue",
            "fieldtype": "Int",
            "label": "Crate Issue",
            "width": 80
        },
        {
            "fieldname": "crate_return",
            "fieldtype": "Int",
            "label": "Crate Return",
            "width": 80
        },
        {
            "fieldname": "crate_balance",
            "fieldtype": "Int",
            "label": "Crate Balance",
            "width": 80
        },
        {
            "fieldname": "transporter",
            "fieldtype": "Link",
            "label": "Transporter",
            "options": "Supplier",
            "width": 80
        },
        {
            "fieldname": "customer",
            "fieldtype": "Link",
            "label": "Customer",
            "options": "Customer",
            "width": 80
        },
        {
            "fieldname": "vehicle",
            "fieldtype": "Link",
            "label": "Vehicle",
            "options": "Vehicle",
            "width": 80
        },
        {
            "fieldname": "route",
            "fieldtype": "Link",
            "label": "Route",
            "options": "Route Master",
            "width": 80
        },
        {
            "fieldname": "date",
            "fieldtype": "Date",
            "label": "Date",
            "width": 80
        },
        {
            "fieldname": "voucher_type",
            "fieldtype": "Link",
            "label": "Voucher Type",
            "options": "DocType",
            "width": 80
        },
        {
            "fieldname": "voucher",
            "fieldtype": "Dynamic Link",
            "label": "Voucher",
            "options": "voucher_type",
            "width": 80
        },
        {
            "fieldname": "company",
            "fieldtype": "Link",
            "label": "Company",
            "options": "Company",
            "width": 80
        },
        {
            "fieldname": "source_warehouse",
            "fieldtype": "Link",
            "label": "Source Warehouse",
            "options": "Warehouse",
            "width": 120
        },
        {
            "fieldname": "damaged",
            "fieldtype": "Int",
            "label": "Damaged",
            "width": 80
        },

        {
            "fieldname": "note",
            "fieldtype": "Data",
            "label": "Note",
            "width": 150
        }
    ]
    return columns

def get_data(filters):
    data =[]

    # result = frappe.db.sql("""select TDN.customer,TDN.route,TDN.name,TDN.posting_date,TR.vehicle,TDNI.item_code,TDNI.crate_count
    #                         from `tabDelivery Note` TDN
    #                         inner join `tabDelivery Note Item` TDNI on TDNI.parent =TDN.name
    #                         inner join `tabRoute Master` TR on TR.name = TDN.route""",as_dict =True)
    result = frappe.db.sql("""select crate_type,crate_opening,crate_issue,crate_return,crate_balance,transporter,customer,vehicle,
                                route,date,voucher_type,voucher,company,source_warehouse,damaged,note from `tabCrate Log` """, as_dict=True)
    for res in result:
        data.append({
            "crate_type":res.get('crate_type'),
            "crate_opening":res.get('crate_opening'),
            "crate_issue":res.get('crate_issue'),
            "crate_return":res.get('crate_return'),
            "crate_balance":res.get('crate_balance'),
            "transporter":res.get('transporter'),
            "customer":res.get('customer'),
            "vehicle": res.get('vehicle'),
            "route": res.get('route'),
            "date": res.get('date'),
            "voucher_type": res.get('voucher_type'),
            "voucher": res.get('voucher'),
            "company": res.get('company'),
            "source_warehouse": res.get('source_warehouse'),
            "damaged": res.get('damaged'),
            "note": res.get('note'),

        })
    return data