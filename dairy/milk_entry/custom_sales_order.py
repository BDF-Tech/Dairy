from __future__ import unicode_literals
from erpnext.accounts.party import get_dashboard_info
import frappe
import json
import frappe.utils
from frappe.utils import cstr, flt, getdate, cint, nowdate, add_days, get_link_to_form
from frappe.model.utils import get_fetch_values
from frappe.model.mapper import get_mapped_doc
from frappe.contacts.doctype.address.address import get_company_address
from erpnext.stock.doctype.item.item import get_item_defaults
from erpnext.setup.doctype.item_group.item_group import get_item_group_defaults

def before_submit(sales, method):
    validate_multiple_orders(sales.customer,sales.delivery_shift,sales.route,sales.delivery_date)
    for k in sales.items:
        price_list=frappe.db.get_value("Item Price",{"item_code":k.item_code,"price_list":sales.selling_price_list},["price_list_rate"])
        if price_list:
            itemd=frappe.get_doc("Item",k.item_code)
            if itemd.custom_disable_validation_for_price==0:
                if price_list*(k.stock_qty/k.qty) !=k.rate:
                    frappe.throw("You can't save Invoice because Orf Rate Not Match In Row '{0}'".format(k.idx))
    if frappe.db.get_single_value("Dairy Settings", "leakage_calculated_on") == "Sales Order":
        if frappe.db.get_single_value("Dairy Settings", "leakage_percentage") and frappe.db.get_single_value("Dairy Settings", "leakage_qty"):
            leakage_perc = float(frappe.db.get_single_value("Dairy Settings", "leakage_percentage"))
            leakage_qty = float(frappe.db.get_single_value("Dairy Settings", "leakage_qty"))
            applicable_on = (frappe.db.get_single_value("Dairy Settings", "applicable_on"))
            lst = []
            for line in sales.items:
                lst.append(line)
            for line in lst:
                item = frappe.get_doc("Item",line.item_code)
                weight_uom = item.weight_uom
                weight_per_unit = item.weight_per_unit
                if item.leakage_applicable and applicable_on == "Stock UOM" and line.stock_qty > leakage_qty:
                    qty = (line.stock_qty * leakage_perc)/100
                    uom = frappe.get_doc("UOM",line.stock_uom)
                    if uom.must_be_whole_number:
                        qty = round((line.stock_qty * leakage_perc) / 100)
                    if qty == 0:
                        qty = 1
                    sales.append("items",{
                        "item_code": line.item_code,
                        "item_name": line.item_name,
                        "delivery_date": line.delivery_date,
                        "description": str(line.description)+" Leakage Scheme applied",
                        # "gst_hsn_code": line.gst_hsn_code,
                        "is_nil_exempt": line.is_nil_exempt,
                        "qty": qty,
                        "uom": line.stock_uom,
                        "stock_uom": line.stock_uom,
                        "rate": 0.0,
                        "warehouse": line.warehouse,
                        "is_free_item": 1,
                        "price_list_rate": 0,
                        "weight_uom": weight_uom,
                        "weight_per_unit": weight_per_unit,
                        "total_weight": qty * weight_per_unit

                    })
                    sales.validate()
                    
                   

                if item.leakage_applicable and applicable_on == "Order UOM" and line.qty > leakage_qty:
                    qty = (line.qty * leakage_perc)/100
                    uom1 = frappe.get_doc("UOM", line.stock_uom)
                    uom2 = frappe.get_doc("UOM", line.uom)
                    if uom1.must_be_whole_number or uom2.must_be_whole_number:
                        qty = round((line.qty * leakage_perc) / 100)
                    if qty == 0:
                        qty = 1
                    sales.append("items",{
                        "item_code": line.item_code,
                        "item_name": line.item_name,
                        "delivery_date": line.delivery_date,
                        "description": str(line.description)+" Leakage Scheme applied",
                        # "gst_hsn_code": line.gst_hsn_code,
                        "is_nil_exempt": line.is_nil_exempt,
                        "qty": qty,
                        "uom": line.uom,
                        "stock_uom": line.stock_uom,
                        "rate": 0.0,
                        "warehouse": line.warehouse,
                        "is_free_item": 1,
                        "price_list_rate": 0,
                        "weight_uom": weight_uom,
                        "weight_per_unit": weight_per_unit,
                        "total_weight": qty * weight_per_unit
                    })
                    sales.validate()

@frappe.whitelist()
def validate_multiple_orders(customer,delivery_shift,route,delivery_date):
    if frappe.db.get_single_value("Dairy Settings", "restrict_multiple_orders_in_single_shift"):
        result = 0
        pre_sale_order = frappe.db.sql("""select count(*) from `tabSales Order` where customer = %(customer)s and
          delivery_shift = %(delivery_shift)s and route = %(route)s and delivery_date = %(delivery_date)s and docstatus = 1 """,
         {'customer': customer, 'delivery_shift': delivery_shift, 'route':route,'delivery_date':delivery_date})
        result = pre_sale_order[0][0]
        if (result > 0):
            frappe.throw("Multiple Orders In Single Shift Not Allowed")
            return 1
            



@frappe.whitelist()
def validate_multiple_orders_in_quotation(customer,delivery_shift,route,delivery_date):

    if frappe.db.get_single_value("Dairy Settings", "restrict_multiple_orders_in_single_shift"):
        result = 0
        pre_sale_order = frappe.db.sql("""select count(*) from `tabQuotation` where customer_name = %(customer)s and
          delivery_shift = %(delivery_shift)s and route = %(route)s and delivery_date = %(delivery_date)s and docstatus = 1 """,
         {'customer': customer, 'delivery_shift': delivery_shift, 'route':route,'delivery_date':delivery_date})
        result = pre_sale_order[0][0]
        if(result > 0):
            return 1

@frappe.whitelist()
def order_role():
    role = frappe.get_roles(frappe.session.user)
    fixed_role = frappe.db.get_single_value("Dairy Settings", "order_controller")
    if fixed_role in role:
        return 1

@frappe.whitelist()
def get_customer(doc_name):
    route = list(frappe.db.sql(""" select link_name from `tabDynamic Link` where parent = %(doc_name)s and link_doctype = "Route Master" """,{"doc_name": doc_name}))
    return route

@frappe.whitelist()
def set_territory():
    territory = frappe.db.get_single_value("Dairy Settings", "get_territory")
    return territory

@frappe.whitelist()
def make_delivery_note(source_name, target_doc=None, skip_item_mapping=False):
	def set_missing_values(source, target):
		target.ignore_pricing_rule = 1
		target.run_method("set_missing_values")
		target.run_method("set_po_nos")
		target.run_method("calculate_taxes_and_totals")

		if source.company_address:
			target.update({'company_address': source.company_address})
		else:
			# set company address
			target.update(get_company_address(target.company))

		if target.company_address:
			target.update(get_fetch_values("Delivery Note", 'company_address', target.company_address))

		if source.delivery_shift:
			target.update({'shift': source.delivery_shift})
	def update_item(source, target, source_parent):
		target.base_amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.base_rate)
		target.amount = (flt(source.qty) - flt(source.delivered_qty)) * flt(source.rate)
		target.qty = flt(source.qty) - flt(source.delivered_qty)

		item = get_item_defaults(target.item_code, source_parent.company)
		item_group = get_item_group_defaults(target.item_code, source_parent.company)

		if item:
			target.cost_center = frappe.db.get_value("Project", source_parent.project, "cost_center") \
				or item.get("buying_cost_center") \
				or item_group.get("buying_cost_center")

	mapper = {
		"Sales Order": {
			"doctype": "Delivery Note",
			"validation": {
				"docstatus": ["=", 1]
			}
		},
		"Sales Taxes and Charges": {
			"doctype": "Sales Taxes and Charges",
			"add_if_empty": True
		},
		"Sales Team": {
			"doctype": "Sales Team",
			"add_if_empty": True
		}
	}

	if not skip_item_mapping:
		mapper["Sales Order Item"] = {
			"doctype": "Delivery Note Item",
			"field_map": {
				"rate": "rate",
				"name": "so_detail",
				"parent": "against_sales_order",
			},
			"postprocess": update_item,
			"condition": lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier!=1
		}

	target_doc = get_mapped_doc("Sales Order", source_name, mapper, target_doc, set_missing_values)

	return target_doc

@frappe.whitelist()
def defsellinguom(doc_name=None):
    try:
        doc = frappe.get_doc("Item",doc_name)
        if doc.sales_uom:
            sale_uom = doc.sales_uom
            res = frappe.db.sql(""" select uom,conversion_factor from `tabUOM Conversion Detail` where parent = %(p)s and uom = %(u)s """,
                          {'p':doc_name,'u':sale_uom},as_dict= True)
            return res
        else:
            return 1
    except:
        frappe.throw("select item")


@frappe.whitelist()
def get_party_bal(customer):
	cust_name =customer
	doctype = "Customer"
	loyalty_program = None

	party_bal = get_dashboard_info(doctype, cust_name, loyalty_program)

	if cust_name and party_bal:
		return party_bal[0]['total_unpaid']




@frappe.whitelist()
def get_party_bal(self,method):
	cust_name =self.customer
	doctype = "Customer"
	loyalty_program = None

	party_bal = get_dashboard_info(doctype, cust_name, loyalty_program)

	if cust_name and party_bal:
		self.party_balance=party_bal[0]['total_unpaid']