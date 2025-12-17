# Copyright (c) 2025, Sanskar Shukla and contributors
# Please Contact on @Sanskar199(sanskar19shukla@gmail.com)  for more info

import frappe
from frappe.utils import flt

def execute(filters=None):
    if not filters:
        filters = {}

    filters.setdefault("from_date", None)
    filters.setdefault("to_date", None)
    filters.setdefault("item_code", None)
    filters.setdefault("warehouse", None)

    columns = get_columns()
    data = get_data(filters)

    return columns, data


# -----------------------------------------------------------
# COLUMNS
# -----------------------------------------------------------
def get_columns():
    return [
        {"label": "Row Type", "fieldname": "row_type", "fieldtype": "Data", "width": 130},
        {"label": "Posting Date", "fieldname": "posting_date", "fieldtype": "Date", "width": 100},
        {"label": "Posting Time", "fieldname": "posting_time", "fieldtype": "Time", "width": 80},
        
        {"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": 150},
        {"label": "Warehouse", "fieldname": "warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},

        {"label": "Voucher Type", "fieldname": "voucher_type", "fieldtype": "Data", "width": 120},
        {"label": "Voucher No", "fieldname": "voucher_no", "fieldtype": "Dynamic Link",
            "options": "voucher_type", "width": 140},

        {"label": "In Qty", "fieldname": "in_qty", "fieldtype": "Float", "width": 90},
        {"label": "Out Qty", "fieldname": "out_qty", "fieldtype": "Float", "width": 90},
        {"label": "Balance Qty", "fieldname": "balance_qty", "fieldtype": "Float", "width": 110},

        {"label": "Incoming Rate", "fieldname": "incoming_rate", "fieldtype": "Currency", "width": 110},
        {"label": "Valuation Rate", "fieldname": "valuation_rate", "fieldtype": "Currency", "width": 110},
        {"label": "Stock Value Diff", "fieldname": "stock_value_difference", "fieldtype": "Currency", "width": 140},

        {"label": "Batch No", "fieldname": "batch_no", "fieldtype": "Link", "options": "Batch", "width": 120},
        {"label": "Serial No", "fieldname": "serial_no", "fieldtype": "Data", "width": 200},
    ]


# -----------------------------------------------------------
# DATA BUILDING
# -----------------------------------------------------------
def get_data(filters):

    # ---------------------------------
    # 1️⃣ OPENING BALANCE
    # ---------------------------------
    opening_qty = frappe.db.sql("""
        SELECT SUM(actual_qty) AS qty
        FROM `tabStock Ledger Entry`
        WHERE posting_date < %(from_date)s
        AND (%(item_code)s IS NULL OR %(item_code)s='' OR item_code=%(item_code)s)
        AND (%(warehouse)s IS NULL OR %(warehouse)s='' OR warehouse=%(warehouse)s)
    """, filters, as_dict=True)[0].qty or 0

    opening_qty = flt(opening_qty)

    # ---------------------------------
    # 2️⃣ GET SLE MOVEMENTS IN DATE RANGE
    # ---------------------------------
    sle_rows = frappe.db.sql("""
        SELECT
            posting_date,
            posting_time,
            item_code,
            warehouse,
            actual_qty,
            incoming_rate,
            valuation_rate,
            stock_value_difference,
            voucher_type,
            voucher_no,
            batch_no,
            serial_no
        FROM `tabStock Ledger Entry`
        WHERE posting_date BETWEEN %(from_date)s AND %(to_date)s
        AND (%(item_code)s IS NULL OR %(item_code)s='' OR item_code=%(item_code)s)
        AND (%(warehouse)s IS NULL OR %(warehouse)s='' OR warehouse=%(warehouse)s)
        ORDER BY posting_date ASC, posting_time ASC, name ASC
    """, filters, as_dict=True)

    # ---------------------------------
    # 3️⃣ CALCULATE SUMMARY TOTAL IN & OUT
    # ---------------------------------
    total_in = 0
    total_out = 0

    for r in sle_rows:
        if r.actual_qty > 0:
            total_in += r.actual_qty
        else:
            total_out += abs(r.actual_qty)

    closing_qty = opening_qty + total_in - total_out

    data = []

    # ---------------------------------
    # 4️⃣ ADD OPENING BALANCE ROW AT TOP
    # ---------------------------------
    data.append({
        "row_type": "OPENING BALANCE",
        "posting_date": None,
        "posting_time": None,
        "item_code": filters.item_code,
        "warehouse": filters.warehouse,
        "voucher_type": "",
        "voucher_no": "",
        "in_qty": 0,
        "out_qty": 0,
        "balance_qty": opening_qty,
        "incoming_rate": "",
        "valuation_rate": "",
        "stock_value_difference": "",
        "batch_no": "",
        "serial_no": ""
    })

    # ---------------------------------
    # 5️⃣ TRANSACTIONS + RUNNING BALANCE
    # ---------------------------------
    running = opening_qty

    for r in sle_rows:

        if r.actual_qty > 0:
            in_qty = r.actual_qty
            out_qty = 0
        else:
            in_qty = 0
            out_qty = abs(r.actual_qty)

        running = running + in_qty - out_qty

        data.append({
            "row_type": "LEDGER",
            "posting_date": r.posting_date,
            "posting_time": r.posting_time,
            "item_code": r.item_code,
            "warehouse": r.warehouse,
            "voucher_type": r.voucher_type,
            "voucher_no": r.voucher_no,
            "in_qty": in_qty,
            "out_qty": out_qty,
            "balance_qty": running,
            "incoming_rate": r.incoming_rate,
            "valuation_rate": r.valuation_rate,
            "stock_value_difference": r.stock_value_difference,
            "batch_no": r.batch_no,
            "serial_no": r.serial_no
        })

    # ---------------------------------
    # 6️⃣ CLOSING BALANCE ROW AT BOTTOM
    # ---------------------------------
    data.append({
        "row_type": "CLOSING BALANCE",
        "posting_date": None,
        "posting_time": None,
        "item_code": filters.item_code,
        "warehouse": filters.warehouse,
        "voucher_type": "",
        "voucher_no": "",
        "in_qty": total_in,
        "out_qty": total_out,
        "balance_qty": closing_qty,
        "incoming_rate": "",
        "valuation_rate": "",
        "stock_value_difference": "",
        "batch_no": "",
        "serial_no": ""
    })

    return data
