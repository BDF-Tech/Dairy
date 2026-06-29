import frappe
from frappe import _

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {"label": "Asset Code", "fieldname": "assets_code", "fieldtype": "Data", "width": 150},
        {"label": "Asset Category", "fieldname": "asset_category", "fieldtype": "Data", "width": 150},
        {"label": "Asset Serial No", "fieldname": "aseet_sn", "fieldtype": "Data", "width": 150},
        {"label": "Location", "fieldname": "location", "fieldtype": "Data", "width": 150},
        {"label": "Purchase Date", "fieldname": "purchase_date", "fieldtype": "Date", "width": 120},
        {"label": "Custodian", "fieldname": "custodian", "fieldtype": "Data", "width": 150},
        {"label": "Custodian Name", "fieldname": "custodian_name", "fieldtype": "Data", "width": 150},
        {"label": "Net Price", "fieldname": "net_price", "fieldtype": "Currency", "width": 120},
    ]


def get_data(filters):
    conditions = ""
    
    if filters.get("location"):
        conditions += " AND location = %(location)s"
        
    if filters.get("asset_category"):
        conditions += " AND asset_category = %(asset_category)s"

    return frappe.db.sql(f"""
        SELECT
            assets_code,
            asset_category,
            aseet_sn,
            location,
            purchase_date,
            custodian,
            custodian_name,
            net_price
        FROM `tabAssets Location`
        WHERE docstatus < 2
        {conditions}
        ORDER BY purchase_date DESC
    """, filters, as_dict=True)
