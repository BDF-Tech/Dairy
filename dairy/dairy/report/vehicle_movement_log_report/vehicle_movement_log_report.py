# Copyright (c) 2026, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import time_diff_in_seconds, now_datetime

def execute(filters=None):
    # 1. Define the Columns (The Header)
    columns = get_columns()
    
    # 2. Fetch and Process the Data (The Rows)
    data = get_data(filters)
    
    # 3. Return both to Frappe to render the grid
    return columns, data

def get_columns():
    """
    Defines the structure of the report table.
    """
    return [
        {
            "label": "Trip ID",
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Vehicle Movement Log",
            "width": 140
        },
        {
            "label": "Vehicle",
            "fieldname": "vehicle",
            "fieldtype": "Link",
            "options": "Vehicle",
            "width": 120
        },
        {
            "label": "Driver",
            "fieldname": "driver_name",
            "fieldtype": "Data",
            "width": 150
        },
        {
            "label": "Route",
            "fieldname": "route",
            "fieldtype": "Link",
            "options": "Route Master",
            "width": 120
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data", 
            "width": 100
        },
        {
            "label": "Out Time",
            "fieldname": "out_time",
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "label": "In Time",
            "fieldname": "in_time",
            "fieldtype": "Datetime",
            "width": 150
        },
        {
            "label": "Duration",
            "fieldname": "duration",
            "fieldtype": "Data",
            "width": 150
        }
    ]

def get_data(filters):
    """
    Fetches raw data from DB and calculates Duration in Python.
    """
    conditions = get_conditions(filters)
    
    # Fetch raw data using SQL
    # Note: We alias 'datetime_xacd' to 'out_time' for clarity
    sql = f"""
        SELECT
            name,
            vehicle,
            driver_name,
            route,
            status,
            datetime_xacd as out_time,
            vehicle_in_time as in_time
        FROM
            `tabVehicle Movement Log`
        WHERE
            docstatus < 2
            {conditions}
        ORDER BY
            datetime_xacd DESC
    """
    
    # Run Query
    data = frappe.db.sql(sql, filters, as_dict=True)
    
    # Loop through rows to calculate Duration using Python logic
    for row in data:
        row["duration"] = calculate_duration(row.out_time, row.in_time)
        
    return data

def get_conditions(filters):
    """
    Builds the SQL WHERE clause based on User Filters
    """
    conditions = []
    
    # 1. Date Filter (Filters based on when the vehicle went OUT)
    if filters.get("from_date") and filters.get("to_date"):
        conditions.append("AND DATE(datetime_xacd) BETWEEN %(from_date)s AND %(to_date)s")
        
    # 2. Vehicle Filter
    if filters.get("vehicle"):
        conditions.append("AND vehicle = %(vehicle)s")
        
    # 3. Status Filter
    if filters.get("status"):
        conditions.append("AND status = %(status)s")

    # 4. Driver Filter
    if filters.get("driver"):
        conditions.append("AND driver = %(driver)s")

    # 5. Route Filter
    if filters.get("route"):
        conditions.append("AND route = %(route)s")
        
    return " ".join(conditions)

def calculate_duration(out_time, in_time):
    """
    Helper function to format seconds into "X Hr Y Min"
    """
    if not out_time:
        return ""
        
    # If vehicle is still OUT (no In Time), calculate duration until NOW
    if not in_time:
        end_time = now_datetime()
        is_ongoing = True
    else:
        end_time = in_time
        is_ongoing = False
        
    # Calculate difference in seconds
    total_seconds = time_diff_in_seconds(end_time, out_time)
    
    if total_seconds < 0:
        return "Time Error"
        
    # Math to extract Hours and Minutes
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    
    duration_str = f"{hours} Hr {minutes} Min"
    
    # Add an indicator if the trip is still active
    if is_ongoing:
        return f"{duration_str} (Ongoing)"
    
    return duration_str