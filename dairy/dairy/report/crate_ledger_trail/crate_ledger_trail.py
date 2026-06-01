import frappe
from frappe.utils import getdate, nowdate


def execute(filters=None):
    filters = filters or {}
    columns = get_columns()
    data = get_data(filters)
    chart = get_chart(data)
    summary = get_summary(data)
    return columns, data, None, chart, summary


def get_columns():
    return [
        {
            "label": "Date",
            "fieldname": "posting_date",
            "fieldtype": "Date",
            "width": 100,
        },
        {
            "label": "VML",
            "fieldname": "vehicle_movement_log",
            "fieldtype": "Link",
            "options": "Vehicle Movement Log",
            "width": 160,
        },
        {
            "label": "Ledger Type",
            "fieldname": "ledger_type",
            "fieldtype": "Data",
            "width": 100,
        },
        {
            "label": "Crate Category",
            "fieldname": "crate_category",
            "fieldtype": "Data",
            "width": 120,
        },
        {
            "label": "Entry Type",
            "fieldname": "entry_type",
            "fieldtype": "Data",
            "width": 80,
        },
        {
            "label": "Driver",
            "fieldname": "driver",
            "fieldtype": "Link",
            "options": "Driver",
            "width": 130,
        },
        {
            "label": "Customer",
            "fieldname": "customer",
            "fieldtype": "Link",
            "options": "Customer",
            "width": 160,
        },
        {
            "label": "Sales Invoice",
            "fieldname": "sales_invoice",
            "fieldtype": "Link",
            "options": "Sales Invoice",
            "width": 150,
        },
        {
            "label": "Stock Entry",
            "fieldname": "stock_entry",
            "fieldtype": "Link",
            "options": "Stock Entry",
            "width": 130,
        },
        {
            "label": "Loose Crate Type",
            "fieldname": "crate_type",
            "fieldtype": "Link",
            "options": "Crate Type",
            "width": 130,
        },
        {
            "label": "Crates Out",
            "fieldname": "crates_out",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": "Crates In",
            "fieldname": "crates_in",
            "fieldtype": "Float",
            "width": 100,
        },
        {
            "label": "Balance",
            "fieldname": "balance_crates",
            "fieldtype": "Float",
            "width": 100,
        },
    ]


def get_data(filters):
    conditions, values = build_conditions(filters)
    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    return frappe.db.sql(
        f"""
        SELECT
            posting_date,
            vehicle_movement_log,
            ledger_type,
            crate_category,
            entry_type,
            driver,
            customer,
            sales_invoice,
            stock_entry,
            crate_type,
            crates_out,
            crates_in,
            balance_crates
        FROM `tabCustomer Crate Ledger`
        {where}
        ORDER BY posting_date ASC, creation ASC
        """,
        values,
        as_dict=True,
    )


def build_conditions(filters):
    conditions = []
    values = {}

    if filters.get("from_date"):
        conditions.append("posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("vehicle_movement_log"):
        conditions.append("vehicle_movement_log = %(vml)s")
        values["vml"] = filters["vehicle_movement_log"]

    if filters.get("driver"):
        conditions.append("driver = %(driver)s")
        values["driver"] = filters["driver"]

    if filters.get("customer"):
        conditions.append("customer = %(customer)s")
        values["customer"] = filters["customer"]

    if filters.get("ledger_type") and filters["ledger_type"] != "Both":
        conditions.append("ledger_type = %(ledger_type)s")
        values["ledger_type"] = filters["ledger_type"]

    if filters.get("crate_category"):
        conditions.append("crate_category = %(crate_category)s")
        values["crate_category"] = filters["crate_category"]

    if filters.get("entry_type"):
        conditions.append("entry_type = %(entry_type)s")
        values["entry_type"] = filters["entry_type"]

    return conditions, values


def get_chart(data):
    # Group by date — sum crates_out and crates_in
    date_map = {}
    for row in data:
        d = str(row.posting_date)
        if d not in date_map:
            date_map[d] = {"out": 0, "in": 0}
        date_map[d]["out"] += row.crates_out or 0
        date_map[d]["in"] += row.crates_in or 0

    dates = sorted(date_map.keys())
    out_values = [date_map[d]["out"] for d in dates]
    in_values = [date_map[d]["in"] for d in dates]

    if not dates:
        return None

    return {
        "data": {
            "labels": dates,
            "datasets": [
                {"name": "Crates Out", "values": out_values},
                {"name": "Crates In", "values": in_values},
            ],
        },
        "type": "line",
        "lineOptions": {"hideDots": 0, "regionFill": 0},
        "title": "Daily Crate Flow",
        "colors": ["#e74c3c", "#27ae60"],
    }


def get_summary(data):
    total_out = sum(r.crates_out or 0 for r in data)
    total_in = sum(r.crates_in or 0 for r in data)
    net = total_out - total_in

    driver_out = sum(
        r.crates_out or 0
        for r in data
        if r.ledger_type == "Driver" and r.entry_type == "OUT"
    )
    driver_in = sum(
        r.crates_in or 0
        for r in data
        if r.ledger_type == "Driver" and r.entry_type == "IN"
    )
    customer_in = sum(
        r.crates_in or 0
        for r in data
        if r.ledger_type == "Customer"
    )

    return [
        {
            "label": "Total Crates Out",
            "datatype": "Float",
            "value": total_out,
            "indicator": "Red",
        },
        {
            "label": "Total Crates In",
            "datatype": "Float",
            "value": total_in,
            "indicator": "Green",
        },
        {
            "label": "Net Outstanding",
            "datatype": "Float",
            "value": net,
            "indicator": "Orange" if net > 0 else "Green",
        },
        {
            "label": "Driver Net Outstanding",
            "datatype": "Float",
            "value": driver_out - driver_in,
            "indicator": "Orange",
        },
        {
            "label": "Returned by Customers",
            "datatype": "Float",
            "value": customer_in,
            "indicator": "Blue",
        },
    ]
