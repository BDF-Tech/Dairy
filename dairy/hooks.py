# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "dairy"
app_title = "Dairy"
app_publisher = "Dexciss Technology Pvt Ltd"
app_description = "Dairy modules"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "dexciss"
app_license = "Dexciss"



# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/dairy/css/dairy.css"



# -----------------------quick entry temporay removed  -sid----------------------
app_include_js = "/assets/js/vehicle.min.js"


fixtures = fixtures = [
		{"dt":"Custom Field", "filters": [["name", "in",(
            "BOM-standard_fat" ,
            "BOM-standard_snf",
            "BOM-item_fat" ,
            "BOM-item_snf",
            "BOM-weight_details",
            "BOM-fg_weight",
            "BOM-total_rm_weight",
            "BOM-total_rm_fat",
            "BOM-total_rm_snf",
            "Item-standard_fat",
            "Item-standard_snf",
            "BOM Item-weight",
            "BOM Item-standard_fat",
            "BOM Item-bom_fat",
            "BOM Item-standard_snf",
            "BOM Item-bom_snf",
            "Work Order-required_fat",
            "Work Order-required_fat_in_kg",
            "Work Order-sepration_fat",
            "Work Order-required_snf_",
            "Work Order-required_snt_in_kg",
            "Work Order Item-fat_per",
            "Work Order Item-fat_per_in_kg",
            "Work Order Item-snf_per",
            "Work Order Item-snf_in_kg",
            "Work Order-fg_item_scrap",
            "Work Order-rm_fat_in_kg",
            "Work Order-rm_snf_in_kg",
            "Work Order-diff_fat_in_kg",
            "Work Order-diff_snf_in_kg",
            "Work Order-fat_snf_section",
            "Work Order-column_break_qmtum",
            "Sales Order-party_balance",
            "Sales Order-update_party_balance",
            "Sales Invoice-party_balance",
            "Sales Invoice-update_party_balance",
            "Item Tax Template-tax_rate",
            "Address-fssai_lic_no"
        )]]}
]

# include js, css files in header of web template
# web_include_css = "/assets/dairy/css/dairy.css"
# web_include_js = "/assets/dairy/js/dairy.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
    "Warehouse": "public/js/utils/warehouse.js",
    "Sales Order": "public/js/sales_order.js",
    "Quotation": "public/js/quotation.js",
    "Delivery Note": "public/js/delivery_note.js",
    "Vehicle": "public/js/vehicle.js",
    "Customer": "public/js/customer.js",
    "Sales Invoice": "public/js/sales_invoice.js",
    # "Supplier": "public/js/supplier.js",
    "Item": "public/js/item.js",
    "Stock Entry": "public/js/stock_entry.js",
    "Purchase Receipt": "public/js/purchase_receipt.js",
    "BOM":"public/js/custom_bom.js",
    "Work Order":"public/js/work_order.js",
    "Purchase Invoice":"public/js/purchase_invoice.js",
    "Stock Reconciliation":"public/js/stock_reconciliation.js",
    }

doctype_list_js = {
                    "Warehouse": "public/js/utils/warehouse_list.js"                  }
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Website user home page (by function)
# get_website_user_home_page = "dairy.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "dairy.install.before_install"
after_install = "dairy.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "dairy.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Delivery Note": {
        # "before_insert": "dairy.milk_entry.custom_delivery_note.calculate_crate_after_insert",
        # "before_save": "dairy.milk_entry.custom_delivery_note.calculate_crate_after_insert",
        "validate": "dairy.milk_entry.custom_delivery_note.route_validation",
        "before_submit": ["dairy.milk_entry.custom_delivery_note.before_submit",
                          "dairy.milk_entry.custom_delivery_note.after_save"],
        # "on_submit": "dairy.milk_entry.custom_delivery_note.on_submit",
        "after_insert": ["dairy.milk_entry.custom_delivery_note.calculate_crate",
                         "dairy.milk_entry.custom_delivery_note.after_save"],
        "before_save": ["dairy.milk_entry.custom_delivery_note.calculate_crate",
                        "dairy.milk_entry.custom_delivery_note.after_save",
                        # "dairy.milk_entry.custom_delivery_note.set_fat_and_snf_rate"
                        ],
        # "on_cancel": "dairy.milk_entry.custom_delivery_note.cancel_milk_stock_ledger"
    },
    "Sales Order": {
        "validate": "dairy.milk_entry.custom_delivery_note.route_validation",
        "before_submit":"dairy.milk_entry.custom_sales_order.before_submit",
         "before_save":"dairy.milk_entry.custom_sales_order.get_party_bal"
    },
    "Quotation": {
        "validate": "dairy.milk_entry.custom_delivery_note.route_validation",
    },
    "Sales Invoice": {
        "validate": "dairy.milk_entry.custom_delivery_note.route_validation",
        "before_submit": ["dairy.milk_entry.custom_sales_invoice.before_submit",
                          ],
        "before_save":["dairy.milk_entry.custom_sales_invoice.get_party_bal_det",
                    #    "dairy.milk_entry.custom_sales_invoice.calculate_crate"
                       ],
        # "after_insert": "dairy.milk_entry.custom_sales_invoice.calculate_crate"
    },
    "Stock Entry":{
        "after_insert": ["dairy.milk_entry.doctype.van_collection.van_collection.change_van_collection_status",
                         "dairy.milk_entry.custom_stock_entry.milk_ledger_stock_entry"],
        "before_save":[ "dairy.milk_entry.custom_stock_entry.milk_ledger_stock_entry"
                        # "dairy.milk_entry.custom_stock_entry.before_save"
        ],
        "before_submit": "dairy.milk_entry.custom_stock_entry.milk_ledger_stock_entry",
        # "on_submit": "dairy.milk_entry.custom_stock_entry.on_submit",
        "on_submit": "dairy.milk_entry.custom_stock_entry.update_vc_status",
        "on_cancel": "dairy.milk_entry.custom_stock_entry.cancel_create_milk_stock_ledger"
    },
    "Purchase Receipt":{
        "after_insert": "dairy.milk_entry.custom_purchase_receipt.change_milk_entry_status",
        # "on_cancel": ["dairy.milk_entry.custom_purchase_receipt.cancel_create_milk_stock_ledger"],
        "on_submit": "dairy.milk_entry.custom_purchase_receipt.change_milk_status"
                    #   "dairy.milk_entry.custom_purchase_receipt.create_milk_stock_ledger",
    },
    "BOM":{
    "before_save": "dairy.dairy.custom_bom.before_save"
    # "before_submit":"dairy.dairy.custom_bom.before_submit"
    },
    "Work Order":{
      "before_save":[
            "dairy.milk_entry.custom_work_order.get_required_fat_snf_item",
            "dairy.milk_entry.custom_work_order.bom_item_child_table"
      ]
    },
    "Stock Ledger Entry":{
      "after_insert": "dairy.milk_entry.custom_stock_ledger_entry.create_milk_ledger_entry"
    },
    # "Milk Entry":{
    #     "before_submit": "dairy.milk_entry.doctype.milk_entry.milk_entry.before_submit",
    #     # "on_submit": "dairy.milk_entry.doctype.milk_entry.milk_entry.status"
    #     # "after_insert": "dairy.milk_entry.custom_purchase_receipt.change_milk_entry_status",
    #     # "_submit": "dairy.milk_entry.custom_purchase_receipt.change_milk_status"
    # },
    # "Dairy Settings":{
    #     "before_save" : "dairy.milk_entry.doctype.dairy_settings.dairy_settings.before_save" 
    # }
  
}

permission_query_conditions = {
    "Vehicle": "dairy.vehicle_dynamic_link.get_permission_query_conditions_for_vehicle"
}

has_permission = {
    "Vehicle": "dairy.vehicle_dynamic_link.has_permission",
}

# doc_events={
#     "Milk Entry": {
#  		"before_save" :"dairy.milk_entry.doctype.dairy_settings.dairy_settings.purchase_invoice"
# 	}
# }


# Scheduled Tasks
# ---------------

scheduler_events = {
# # 	"all": [
# # 		"dairy.tasks.all"
# # 	],
	# "daily": [
	# 	"dairy.milk_entry.doctype.milk_entry.milk_entry.sub"
	# ],
	"daily_long": [
		"dairy.milk_entry.doctype.dairy_settings.dairy_settings.purchase_invoice",
	],
# # 	"weekly": [
# # 		"dairy.tasks.weekly"
# # 	]
# # 	"monthly": [
# # 		"dairy.tasks.monthly"
# # 	]
    "cron":{
        "10 0 * * *": [
        "dairy.milk_entry.custom_stock_entry.set_date"
    ]}
 }

# Testing
# -------

override_doctype_class = {
	'Work Order': 'dairy.milk_entry.custom_work_order.CustomWorkOrder',
}
# before_tests = "dairy.install.before_tests"

# Overriding Methods
# ------------------------------
#

override_whitelisted_methods = {
	"erpnext.selling.doctype.sales_order.sales_order.make_delivery_note": "dairy.milk_entry.custom_sales_order.make_delivery_note",
    "erpnext.manufacturing.doctype.work_order.work_order.create_job_card": "dairy.milk_entry.custom_work_order.make_job_card"


}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
override_doctype_dashboards = {
	"Delivery Note": "dairy.delivery_note_dashboard.get_data"
}

jinja = {
	"methods": [
        "dairy.milk_entry.custom_delivery_trip.warehouse_address",
        "dairy.milk_entry.custom_delivery_trip.get_purchase",
		"dairy.milk_entry.custom_delivery_trip.get_jinja_data",
        "dairy.milk_entry.custom_delivery_trip.get_jinja_data_del_note",
        "dairy.milk_entry.custom_delivery_trip.get_jinja_data_si",
        "dairy.milk_entry.custom_delivery_trip.get_jinja_data_del_note_item",
         "dairy.milk_entry.custom_delivery_trip.get_jinja_data_si_item",
        "dairy.milk_entry.custom_delivery_trip.del_note_total",
         "dairy.milk_entry.custom_delivery_trip.si_note_total",
        "dairy.milk_entry.custom_delivery_trip.del_note_details",
         "dairy.milk_entry.custom_delivery_trip.si_note_details",
        "dairy.milk_entry.custom_delivery_trip.total_supp_qty_based_on_itm_grp",
        "dairy.milk_entry.custom_delivery_trip.get_crate_bal",
        "dairy.milk_entry.custom_delivery_trip.get_crate_gate"
	]
}

