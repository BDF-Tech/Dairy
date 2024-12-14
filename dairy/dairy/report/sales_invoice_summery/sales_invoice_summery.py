# Import necessary modules
import frappe
from dateutil.relativedelta import relativedelta
from datetime import datetime
import calendar

# Define your function to fetch data
def get_data(filters):
    # Extract filters
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    interval = filters.get("interval")

    # Convert from_date and to_date to datetime objects
    from_date = datetime.strptime(from_date, '%Y-%m-%d')
    to_date = datetime.strptime(to_date, '%Y-%m-%d')

    # Define date format based on interval
    date_format = "%Y-%m-%d"
    if interval == "Monthly":
        date_format = "%Y-%m"
    elif interval == "Quarterly":
        date_format = "%Y-Q%q"

    # Generate date range based on interval
    # Generate date range based on interval
    date_range = []
    start_date = from_date
    while start_date <= to_date:
        if interval == "Weekly":
            end_date = start_date + relativedelta(weeks=1, days=-1)
        elif interval == "Monthly":
            end_date = start_date + relativedelta(months=1, days=-1)
        elif interval == "Quarterly":
            end_date = start_date + relativedelta(months=3, days=-1)
        elif interval == "Yearly":
            end_date = start_date + relativedelta(years=1, days=-1)
  
        # date_range.append((start_date.strftime(date_format), end_date.strftime(date_format)))

        if interval == "Weekly":
            start_date += relativedelta(weeks=1)
        elif interval == "Monthly":
            start_date += relativedelta(months=1)
        # elif interval == "Quarterly":
        #     start_date += relativedelta(months=3)
        elif interval == "Yearly":
            start_date += relativedelta(years=1)

    # Write your SQL query to fetch the required data
    sql_query = """
        SELECT  si.name, si.customer, si.customer_name, si.route, si.set_warehouse, sii.item_code, sii.item_name, sii.base_rate, SUM(sii.base_rate) as total_item_rate, sii.qty,  SUM(sii.qty) as total_qty, DATE_FORMAT(si.posting_date, %s) as date_range
        FROM `tabSales Invoice` si
        LEFT JOIN `tabSales Invoice Item` sii ON si.name = sii.parent
        WHERE si.posting_date BETWEEN %s AND %s
        GROUP BY si.customer, si.route, si.set_warehouse,sii.item_code, date_range
            """
    # Fetch data using Frappe's database API
    data = frappe.db.sql(sql_query, (date_format, from_date, to_date), as_dict=True)
    return data



# Define your report function
def execute(filters=None):
    # Extract filters
    filters = frappe._dict(filters or {})
    interval = filters.get("interval")
    
    # Convert from_date and to_date to datetime objects
    from_date = datetime.strptime(filters.get("from_date"), '%Y-%m-%d')
    to_date = datetime.strptime(filters.get("to_date"), '%Y-%m-%d')

    # Define common columns
    columns = [
        {"label": "Customer", "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": "100"},
        {"label": "Customer Name", "fieldname": "customer_name", "fieldtype": "Link", "options": "Customer", "width": "100"},
        {"label": "Item", "fieldname": "item_code", "fieldtype": "Link", "options": "Item", "width": "100"},
        {"label": "Item Name", "fieldname": "item_name", "fieldtype": "Link", "options": "Item", "width": "100"},
        {"label": "Route", "fieldname": "route", "fieldtype": "Link", "options": "Route Master", "width": "100"},
        {"label": "Warehouse", "fieldname": "set_warehouse", "fieldtype": "Link", "options": "Warehouse", "width": "100"},
        {"label": "Item Rate", "fieldname": "base_rate", "fieldtype": "Float", "width": "100"},
        {"label": "Total Quantity", "fieldname": "total_qty", "fieldtype": "Float", "width": "200"},
        {"label": "Total Item Rate", "fieldname": "total_item_rate", "fieldtype": "Float", "width": "100"},
    ]

    # Add columns based on the interval
    if interval == "Weekly":
        # Add weekly columns
        start_date = from_date
        while start_date <= to_date:
            week_label = start_date.strftime("%Y-%W")
            columns.append({"label": f"Week {week_label}", "fieldname": f"week_{week_label}", "fieldtype": "Data"})
            start_date += relativedelta(weeks=1)

    elif interval == "Monthly":
        # Add monthly columns
        start_date = from_date
        while start_date <= to_date:
            month_name = start_date.strftime("%B")
            year = start_date.strftime("%Y")
            month_year_label = f"{month_name} {year}"
            columns.append({"label": month_year_label, "fieldname": month_year_label.lower().replace(" ", "_"), "fieldtype": "Data"})
            start_date += relativedelta(months=1)

    elif interval == "Quarterly":
        # Add quarterly columns
        start_date = from_date
        while start_date <= to_date:
            quarter_number = (start_date.month - 1) // 3 + 1  # Calculate quarter number
            month_name_short = start_date.strftime("%b")  # Short form of month name
            year = start_date.strftime("%Y")
            quarter_month_year_label = f"Quarter-{quarter_number}, {month_name_short} {year}"
            columns.append({"label": quarter_month_year_label, "fieldname": f"quarter_{quarter_number}_{month_name_short}_{year}", "fieldtype": "Data"})
            start_date += relativedelta(months=3)

    elif interval == "Yearly":
        # Add yearly columns
        start_date = from_date
        while start_date <= to_date:
            year_label = start_date.strftime("%Y")
            columns.append({"label": f"Year {year_label}", "fieldname": f"year_{year_label}", "fieldtype": "Data"})
            start_date += relativedelta(years=1)

    # Add Date Range column
    columns.append({"label": "Date Range", "fieldname": "date_range", "fieldtype": "Data"})

    # Fetch data
    data = get_data(filters)

    return columns, data


# # Copyright (c) 2024, Dexciss Technology Pvt Ltd and contributors
# # For license information, please see license.txt

# import copy
# from collections import OrderedDict

# import frappe
# from frappe import _, qb
# from frappe.query_builder import CustomFunction
# from frappe.query_builder.functions import Max
# from frappe.utils import date_diff, flt, getdate

# def execute(filters=None):
# 	if not filters:
# 		return [], [], None

# 	validate_filters(filters)

# 	columns = get_columns(filters)
# 	conditions = get_conditions(filters)
# 	data = get_data("month",conditions, filters)
	

# 	if not data:
# 		return [], [], None

# 	# frappe.throw(str(data))
# 	return columns, data

# # def _(text):
# #     return text

# def validate_filters(filters):
# 	from_date, to_date = filters.get("from_date"), filters.get("to_date")

# 	if not from_date and to_date:
# 		frappe.throw(_("From and To Dates are required."))
# 	elif date_diff(to_date, from_date) < 0:
# 		frappe.throw(_("To Date cannot be before From Date."))

# def get_conditions(filters):
# 	conditions = ""
# 	if filters.get("from_date") and filters.get("to_date"):
# 		conditions += " and si.posting_date between %(from_date)s and %(to_date)s"
	
# 	if filters.get("set_warehouse"):
# 		conditions += " and si.set_warehouse in %(set_warehouse)s"
	
# 	if filters.get("route"):
# 		conditions += " and si.route = %(route)s"

    
		
# 	return conditions

# def get_columns(filters):
#     return [
#         {
#             "label": _("Sales Invoice"),
#             "fieldname": "name",
#             "fieldtype": "Link",
#             "options": "Sales Invoice",
#             "width": 200,
# 			"align": 'left'
#         },
#        {
# 			"label": _("Customer"),
# 			"fieldname": "customer",
# 			"fieldtype": "Link",
# 			"options" : "Customer",
# 			"width": 100,
# 			"align": 'center'
# 		},
# 		{
# 			"label": _("Customer Name"),
# 			"fieldname": "customer_name",
# 			"fieldtype": "Data",
# 			"width": 200
# 		},
# 		 {
#             "label": _("Item"),
#             "fieldname": "item_code",
#             "fieldtype": "Data",
# 		    "width": 80,
# 			"align": 'center'
#         },
#         {
#             "label": _("Item Name"),
#             "fieldname": "item_name",
#             "fieldtype": "Data",
#             "width": 150,
# 			"align": 'left'
#         },
# 		{
#             "label": _("Route"),
#             "fieldname": "route",
#             "fieldtype": "Data",
#             "width": 100,
#             "align": 'center'
#         },
# 		{
#             "label": _("Warehouse"),
#             "fieldname": "set_warehouse",
#             "fieldtype": "Data",
#             "width": 200,
#             "align": 'center'
#         },
# 		{
#             "label": _("Item Rate"),
#             "fieldname": "base_rate",
#             "fieldtype": "float",
#             "width": 200,
#             "align": 'left'
#         },
# 		{
#             "label": _("Grand Total"),
#             "fieldname": "total_grand_total",
#             "fieldtype": "float",
#             "width": 200,
#             "align": 'left'
#         }
		
       
#     ]


  

# def get_data(time_interval, conditions=None, filters=None):
#     date_field = "si.posting_date"  # Assuming the posting_date field in Sales Invoice table
    
#     if time_interval == "month":
#         date_filter = "MONTH({}) = MONTH(CURRENT_DATE()) AND YEAR({}) = YEAR(CURRENT_DATE())".format(date_field, date_field)
#     elif time_interval == "quarter":
#         date_filter = "QUARTER({}) = QUARTER(CURRENT_DATE()) AND YEAR({}) = YEAR(CURRENT_DATE())".format(date_field, date_field)
#     elif time_interval == "year":
#         date_filter = "YEAR({}) = YEAR(CURRENT_DATE())".format(date_field)
#     elif time_interval == "daily":
#         date_filter = "DATE({}) = CURRENT_DATE()".format(date_field)
#     else:
#         # Default to current month if no valid time interval provided
#         date_filter = "MONTH({}) = MONTH(CURRENT_DATE()) AND YEAR({}) = YEAR(CURRENT_DATE())".format(date_field, date_field)
    
#     if conditions:
#         conditions += " AND " + date_filter
#     else:
#         conditions = date_filter

#     data = frappe.db.sql(
#         """
#         SELECT
#             si.name,
#             si.customer AS "Customer",
#             si.customer_name AS "Customer Name", 
#             si.route,
#             si.set_warehouse AS "Source Warehouse",
#             sii.item_code AS "Item Code",
#             sii.item_name AS "Item Name",
#             sii.base_rate AS "Item Rate",
#             SUM(sii.base_rate) AS "Item Rate Total",
#             CONCAT(MONTHNAME(si.posting_date), ' ', YEAR(si.posting_date)) AS "Month and year",
#             SUM(CASE WHEN MONTH(si.posting_date) = 1 THEN si.grand_total ELSE 0 END) AS "Jan",
#             SUM(CASE WHEN MONTH(si.posting_date) = 2 THEN si.grand_total ELSE 0 END) AS "Feb",
#             SUM(CASE WHEN MONTH(si.posting_date) = 3 THEN si.grand_total ELSE 0 END) AS "Mar",
#             SUM(CASE WHEN MONTH(si.posting_date) = 4 THEN si.grand_total ELSE 0 END) AS "Apr",
#             SUM(CASE WHEN MONTH(si.posting_date) = 5 THEN si.grand_total ELSE 0 END) AS "May",
#             SUM(CASE WHEN MONTH(si.posting_date) = 6 THEN si.grand_total ELSE 0 END) AS "Jun",
#             SUM(CASE WHEN MONTH(si.posting_date) = 7 THEN si.grand_total ELSE 0 END) AS "Jul",
#             SUM(CASE WHEN MONTH(si.posting_date) = 8 THEN si.grand_total ELSE 0 END) AS "Aug",
#             SUM(CASE WHEN MONTH(si.posting_date) = 9 THEN si.grand_total ELSE 0 END) AS "Sep",
#             SUM(CASE WHEN MONTH(si.posting_date) = 10 THEN si.grand_total ELSE 0 END) AS "Oct",
#             SUM(CASE WHEN MONTH(si.posting_date) = 11 THEN si.grand_total ELSE 0 END) AS "Nov",
#             SUM(CASE WHEN MONTH(si.posting_date) = 12 THEN si.grand_total ELSE 0 END) AS "Dec"
            
#         FROM 
#             `tabSales Invoice` si
#         LEFT JOIN 
#             `tabSales Invoice Item` sii ON si.name = sii.parent

#         GROUP BY 
#             si.customer,
#             si.customer_name,
#             si.route,
#             si.set_warehouse,
#             sii.item_code,
#             sii.item_name,
#             sii.base_rate,
#             """.format(conditions=conditions),
#             filters,
#             as_dict=1,
#         )
#         return data



# # def get_data(conditions, filters):
# #     data = frappe.db.sql(
# #         """
# #         SELECT
# #             si.name, 
# #             si.customer,
# #             si.customer_name,
# #             si.route,
# #             si.set_warehouse,
# #             sii.item_code,
# #             sii.item_name,
# #             sii.base_rate,
# #             SUM(si.grand_total) as total_grand_total,
# #             SUM(si.rounded_total) as total_rounded_total
# #         FROM 
# #             `tabSales Invoice` si
# #         LEFT JOIN 
# #             `tabSales Invoice Item` sii ON si.name = sii.parent
# #         GROUP BY 
# #             si.customer,
# #             si.customer_name,
# #             si.route,
# #             si.set_warehouse,
# #             sii.item_code,
# #             sii.item_name,
# #             sii.base_rate;
# #         """.format(
# #             conditions=conditions
# #         ),
# #         filters,
# #         as_dict=1,
# #     )
# #     return data


# # def get_data(conditions, filters):
# #     invoices = frappe.db.sql(
# # 		"""
# #         SELECT 
# #             si.name, si.posting_date,
# #             si.customer,
# #             si.customer_name,
# #             si.route,
# #             si.set_warehouse,
# #             sii.item_code,
# #             sii.item_name,
# #             SUM(sii.base_rate) AS item_rate,
# # 			SUM(si.grand_table) AS grand_total
# #         FROM 
# #             `tabSales Invoice` AS si
# #         INNER JOIN 
# #             `tabSales Invoice Item` AS sii ON si.name = sii.parent
# #         WHERE 
# #             si.docstatus = 1 
# #             AND DATE_FORMAT(si.posting_date, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m') 
# #         GROUP BY 
# #             si.customer,
# #             si.customer_name,
# #             si.route,
# #             si.set_warehouse,
# #             sii.item_code,
# #             sii.item_name,
# # 		""", as_dict=True)

# #     # Prepare report table
# #     data = []
# #     for invoice in invoices:
# #         data.append({
# #             "Customer": invoice.get("customer"),
# # 			"Customer Name": invoice.get("customer_name"),
# #             "Item Code": invoice.get("item_code"),
# #             "Item Name": invoice.get("item_name"),
# # 			"Route": invoice.get("route"),
# # 			"Warehouse": invoice.get("set_warehouse"),
# # 			"Item Rate": invoice.get("item_rate"),
# #             "Grand Total": invoice.get("grand_total")
# #         })

# #     return data


# # def get_data(filters):
# # 	from_date = filters.get('from_date', '2001-01-01')
# # 	to_date = filters.get('to_date', '2100-01-01')

# # 	data = frappe.db.sql("""
# # 							SELECT
# # 								a.name,
# # 								a.customer ,
# # 								a.customer_name , 
# # 								a.route,
# # 								a.set_warehouse ,
# # 								b.item_code ,
# # 								b.item_name 								
# # 							FROM 
# # 								`tabSales Invoice` a
# # 							LEFT JOIN 
# # 								`tabSales Invoice Item` b ON a.name = b.parent
# # 							WHERE 
# # 								a.posting_date BETWEEN %s AND %s
# # 							GROUP BY 
# # 							    a.customer,
# # 								a.route,
# # 								a.set_warehouse,
# # 								b.item_code
								
# # 							""",(from_date ,to_date ),as_dict="True")

# # 	return data


# # def generate_monthly_sales_invoice_report():
# #     # Query to fetch monthly sales invoices data
# #     invoices = frappe.db.sql("""
# #         SELECT 
# #             si.name, si.posting_date,
# #             si.customer,
# #             si.customer_name,
# #             si.route,
# #             si.set_warehouse,
# #             sii.item_code,
# #             sii.item_name,
# #             SUM(sii.base_rate) AS item_rate,
# # 			SUM(sii.base_rate) AS grand_total
# #         FROM 
# #             `tabSales Invoice` AS si
# #         INNER JOIN 
# #             `tabSales Invoice Item` AS sii ON si.name = sii.parent
# #         WHERE 
# #             si.docstatus = 1  # Filter for submitted invoices
# #             AND DATE_FORMAT(si.posting_date, '%Y-%m') = DATE_FORMAT(CURDATE(), '%Y-%m')  # Filter for current month
# #         GROUP BY 
# #             si.customer,
# #             si.customer_name,
# #             si.route,
# #             si.set_warehouse,
# #             sii.item_code,
# #             sii.item_name,
# # 			item_rate,
# # 			grand_total
# #         ORDER BY 
# #             si.customer, sii.item_code, sii.item_name
# #     """, as_dict=True)

# #     # Prepare report table
# #     report_data = []
# #     for invoice in invoices:
# #         report_data.append({
# #             "Customer": invoice.get("customer"),
# # 			"Customer Name": invoice.get("customer_name"),
# #             "Item Code": invoice.get("item_code"),
# #             "Item Name": invoice.get("item_name"),
# # 			"Route": invoice.get("route"),
# # 			"Warehouse": invoice.get("set_warehouse"),
# #             "Grand Total": invoice.get("grand_total")
# #         })

# #     # Print or return report
# #     return report_data




# # def get_data(conditions, filters):
# #     data = frappe.db.sql(
# #         """
# #         SELECT
# #             si.name, si.posting_date,
# #             si.customer,
# #             si.customer_name,
# #             si.route,
# #             si.set_warehouse,
# #             sii.item_code,
# #             sii.item_name,
# #             SUM(si.grand_total) as total_grand_total,
# #             SUM(si.rounded_total) as total_rounded_total
# #         FROM 
# #             `tabSales Invoice` si
# #         LEFT JOIN 
# #             `tabSales Invoice Item` sii ON si.name = sii.parent
# #         GROUP BY 
# #             si.customer,
# #             si.customer_name,
# #             si.route,
# #             si.set_warehouse,
# #             sii.item_code,
# #             sii.item_name;
			
# #         """.format(
# #             conditions=conditions
# #         ),
# #         filters,
# #         as_dict=1,
# #     )
# #     return data

	
	