import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field


def execute():
	# which delivery shift(s) the customer may order for in the mobile app
	after = "custom_franchise_pos" if frappe.get_meta("Customer").has_field("custom_franchise_pos") else "customer_group"
	create_custom_field("Customer", {
		"fieldname": "custom_order_shift",
		"label": "Order Shift",
		"fieldtype": "Select",
		"options": "Both\nMorning\nEvening",
		"default": "Both",
		"insert_after": after,
		"description": "Shift(s) this customer can order for in the app",
	})
	frappe.db.sql("update `tabCustomer` set custom_order_shift = 'Both' where ifnull(custom_order_shift, '') = ''")
