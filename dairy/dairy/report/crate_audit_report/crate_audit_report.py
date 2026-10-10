import frappe
from frappe.utils import flt


def execute(filters=None):
    filters = filters or {}
    if not filters.get("from_date") or not filters.get("to_date"):
        frappe.throw("From Date and To Date are required")
    columns = _columns()
    data    = _build(filters)
    summary = _summary(data)
    return columns, data, None, None, summary


# ─────────────────────────────────────────────────────────────
# COLUMNS
# ─────────────────────────────────────────────────────────────

def _columns():
    return [
        {"label": "Date",                  "fieldname": "date",            "fieldtype": "Date",  "width": 100},
        {"label": "Trip (VML)",            "fieldname": "vml",             "fieldtype": "Link",  "options": "Vehicle Movement Log", "width": 185},
        {"label": "Customer",              "fieldname": "customer",        "fieldtype": "Link",  "options": "Customer",             "width": 160},
        {"label": "Invoice / Stock Entry", "fieldname": "reference",       "fieldtype": "Data",  "width": 180},
        {"label": "Assigned to Driver",    "fieldname": "crates_assigned", "fieldtype": "Float", "width": 130},
        {"label": "Given to Customer",     "fieldname": "crates_given",    "fieldtype": "Float", "width": 130},
        {"label": "Taken from Customer",   "fieldname": "crates_taken",    "fieldtype": "Float", "width": 135},
    ]


# ─────────────────────────────────────────────────────────────
# TOP-LEVEL BUILDER
# ─────────────────────────────────────────────────────────────

def _build(filters):
    view = filters.get("view_by") or "Both"
    rows = []

    if view in ("Both", "Trip Wise"):
        rows += _trip_section(filters)

    if view in ("Both", "Customer Wise"):
        if rows:
            rows.append({})   # blank separator
        rows += _customer_section(filters)

    return rows


# ─────────────────────────────────────────────────────────────
# TRIP-WISE SECTION
# ─────────────────────────────────────────────────────────────

def _trip_section(filters):
    vmls = _fetch_vmls(filters)
    rows = [_section_header("TRIP-WISE CRATE AUDIT")]

    for vml in vmls:
        detail_rows = _vml_detail_rows(vml)
        if not detail_rows:
            continue
        rows.append({"date": vml.date, "vml": vml.name, "bold": 1})
        rows.extend(detail_rows)

    return rows


def _vml_detail_rows(vml):
    summary = frappe.db.get_all(
        "Vehicle Invoice Crate Detail",
        filters={"parent": vml.name},
        fields=["sales_invoice", "stock_entry", "total_crate_out"],
        order_by="idx asc",
    )

    rows = []
    for row in summary:
        ref = row.sales_invoice or row.stock_entry
        if not ref:
            continue

        cd, customer = _get_cd_and_customer(row)

        rows.append({
            "vml":             vml.name,
            "customer":        customer,
            "reference":       ref,
            "crates_assigned": flt(row.total_crate_out) or None,
            "crates_given":    flt(cd.crates_delivered) if cd else None,
            "crates_taken":    flt(cd.crates_returned)  if cd else None,
            "indent":          1,
        })

    return rows


# ─────────────────────────────────────────────────────────────
# CUSTOMER-WISE SECTION
# ─────────────────────────────────────────────────────────────

def _customer_section(filters):
    from_date = filters["from_date"]
    to_date   = filters["to_date"]

    cond = """
        DATE(v.date_and_time) BETWEEN %(from_date)s AND %(to_date)s
        AND v.workflow_state != 'Cancelled'
        AND cd.docstatus = 1
        AND cd.actual_customer IS NOT NULL
    """
    vals = {"from_date": from_date, "to_date": to_date}

    if filters.get("driver"):
        cond += " AND v.driver = %(driver)s"
        vals["driver"] = filters["driver"]

    if filters.get("vehicle_movement_log"):
        cond += " AND v.name = %(vml)s"
        vals["vml"] = filters["vehicle_movement_log"]

    if filters.get("customer"):
        cond += " AND cd.actual_customer = %(customer)s"
        vals["customer"] = filters["customer"]

    deliveries = frappe.db.sql(f"""
        SELECT
            DATE(v.date_and_time)  AS date,
            v.name                 AS vml,
            cd.actual_customer     AS customer,
            cd.sales_invoice       AS sales_invoice,
            cd.stock_entry         AS stock_entry,
            cd.crates_delivered    AS crates_given,
            cd.crates_returned     AS crates_taken
        FROM `tabCrate Delivery` cd
        JOIN `tabVehicle Movement Log` v ON v.name = cd.vehicle_movement_log
        WHERE {cond}
        ORDER BY cd.actual_customer ASC, v.date_and_time ASC
    """, vals, as_dict=True)

    # Group by customer
    customer_map = {}
    for d in deliveries:
        customer_map.setdefault(d.customer, []).append(d)

    rows = [_section_header("CUSTOMER-WISE CRATE AUDIT")]

    for customer, entries in customer_map.items():
        cname = frappe.db.get_value("Customer", customer, "customer_name") or customer
        rows.append({"customer": customer, "reference": f"Customer: {cname}", "bold": 1})

        for e in entries:
            ref = e.sales_invoice or e.stock_entry or "—"
            rows.append({
                "date":         e.date,
                "vml":          e.vml,
                "customer":     customer,
                "reference":    ref,
                "crates_given": flt(e.crates_given) or None,
                "crates_taken": flt(e.crates_taken) or None,
                "indent":       1,
            })

    return rows


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _fetch_vmls(filters):
    from_date = filters["from_date"]
    to_date   = filters["to_date"]

    cond = "DATE(v.date_and_time) BETWEEN %(from_date)s AND %(to_date)s AND v.workflow_state != 'Cancelled'"
    vals = {"from_date": from_date, "to_date": to_date}

    if filters.get("driver"):
        cond += " AND v.driver = %(driver)s"
        vals["driver"] = filters["driver"]

    if filters.get("vehicle_movement_log"):
        cond += " AND v.name = %(vml)s"
        vals["vml"] = filters["vehicle_movement_log"]

    return frappe.db.sql(f"""
        SELECT v.name, DATE(v.date_and_time) AS date, v.driver
        FROM `tabVehicle Movement Log` v
        WHERE {cond}
        ORDER BY v.date_and_time ASC
    """, vals, as_dict=True)


def _get_cd_and_customer(row):
    if row.sales_invoice:
        cd = frappe.db.get_value(
            "Crate Delivery",
            {"sales_invoice": row.sales_invoice, "docstatus": 1},
            ["crates_delivered", "crates_returned", "actual_customer"],
            as_dict=True,
        )
        customer = cd.actual_customer if cd else frappe.db.get_value("Sales Invoice", row.sales_invoice, "customer")
    else:
        cd = frappe.db.get_value(
            "Crate Delivery",
            {"stock_entry": row.stock_entry, "docstatus": 1},
            ["crates_delivered", "crates_returned", "actual_customer"],
            as_dict=True,
        )
        customer = cd.actual_customer if cd else None

    return cd, customer


def _section_header(label):
    return {"reference": label, "bold": 1, "indent": 0}


# ─────────────────────────────────────────────────────────────
# SUMMARY BAR
# ─────────────────────────────────────────────────────────────

def _summary(data):
    total_assigned = sum(flt(r.get("crates_assigned")) for r in data if r.get("crates_assigned"))
    total_given    = sum(flt(r.get("crates_given"))    for r in data if r.get("crates_given"))
    total_taken    = sum(flt(r.get("crates_taken"))    for r in data if r.get("crates_taken"))

    return [
        {"label": "Total Assigned to Driver",     "datatype": "Float", "value": total_assigned,               "indicator": "Blue"},
        {"label": "Total Given to Customer",       "datatype": "Float", "value": total_given,                  "indicator": "Red"},
        {"label": "Total Taken from Customer",     "datatype": "Float", "value": total_taken,                  "indicator": "Green"},
        {"label": "Net Outstanding (Given-Taken)", "datatype": "Float", "value": total_given - total_taken,    "indicator": "Orange"},
    ]
