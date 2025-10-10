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

def apply_leakage_scheme(sales, method):
    sales.flags.ignore_pricing_rule = 1
    sales.flags.ignore_taxes_and_totals = True
    sales.flags.ignore_validate_update_after_submit = True

    if frappe.db.get_single_value("Dairy Settings", "restrict_multiple_orders_in_single_shift"):
        if frappe.db.exists("Sales Order", {
            "customer": sales.customer,
            "delivery_shift": sales.delivery_shift,
            "route": sales.route,
            "delivery_date": sales.delivery_date,
            "docstatus": 1
        }):
            frappe.throw("Multiple Orders In Single Shift Not Allowed")

    dairy = frappe.get_single("Dairy Settings")
    leakage_calc_on = dairy.leakage_calculated_on
    leakage_perc = dairy.leakage_percentage
    leakage_qty = dairy.leakage_qty
    applicable_on = dairy.applicable_on

    item_codes = [d.item_code for d in sales.items]
    price_list = frappe.get_all("Item Price",
        filters={"price_list": sales.selling_price_list, "item_code": ["in", item_codes]},
        fields=["item_code", "price_list_rate"])
    prices = {d.item_code: d.price_list_rate for d in price_list }

    items = {i.name: i for i in frappe.get_all("Item",
        filters={"name": ["in", item_codes]},
        fields=["name", "custom_disable_validation_for_price", "leakage_applicable", "weight_uom", "weight_per_unit"])}

 #   items= item_codes 

    uom_names = list({d.uom for d in sales.items} | {d.stock_uom for d in sales.items})
    uom_whole_flags = {u.name: u.must_be_whole_number for u in frappe.get_all("UOM",
        filters={"name": ["in", uom_names]},
        fields=["name", "must_be_whole_number"])}

    for row in sales.items:
        item_doc = items.get(row.item_code)
        price = prices.get(row.item_code)
        if not item_doc or not price or item_doc.custom_disable_validation_for_price:
            continue
        expected_rate = price if not row.qty else price * (row.stock_qty / row.qty)
        if abs(flt(row.rate) - flt(expected_rate)) > 0.001:
            frappe.throw(f"Row {row.idx}: Rate mismatch. Expected {expected_rate}, Found {row.rate}")

    if leakage_calc_on == "Sales Order" and leakage_perc and leakage_qty:
        leakage_rows = []
        for line in sales.items:
            item_doc = items.get(line.item_code)
            if not item_doc or not item_doc.leakage_applicable:
                continue
            qty = 0
            if applicable_on == "Stock UOM" and line.stock_qty > leakage_qty:
                qty = (line.stock_qty * leakage_perc) / 100
                if uom_whole_flags.get(line.stock_uom): qty = round(qty)
            elif applicable_on == "Order UOM" and line.qty > leakage_qty:
                qty = (line.qty * leakage_perc) / 100
                if uom_whole_flags.get(line.stock_uom) or uom_whole_flags.get(line.uom): qty = round(qty)

            if qty > 0:
                leakage_rows.append({
                    "item_code": line.item_code,
                    "item_name": line.item_name,
                    "delivery_date": line.delivery_date,
                    "description": f"{line.description} (Leakage Scheme applied)",
                    "qty": max(1, qty),
                    "uom": line.uom if applicable_on == "Order UOM" else line.stock_uom,
                    "stock_uom": line.stock_uom,
                    "rate": 0.0,
                    "warehouse": line.warehouse,
                    "is_free_item": 1,
                    "price_list_rate": 0,
                    "weight_uom": item_doc.weight_uom,
                    "weight_per_unit": item_doc.weight_per_unit,
                    "total_weight": qty * item_doc.weight_per_unit,
                })
        if leakage_rows:
            sales.extend("items", leakage_rows)


@frappe.whitelist()
def validate_multiple_orders(customer, delivery_shift, route, delivery_date):
    if frappe.db.get_single_value("Dairy Settings", "restrict_multiple_orders_in_single_shift"):
        result = frappe.db.count("Sales Order", {
            "customer": customer,
            "delivery_shift": delivery_shift,
            "route": route,
            "delivery_date": delivery_date,
            "docstatus": 1
        })
        if result > 0:
            frappe.throw("Multiple Orders In Single Shift Not Allowed")
            return 1


@frappe.whitelist()
def validate_multiple_orders_in_quotation(customer, delivery_shift, route, delivery_date):
    if frappe.db.get_single_value("Dairy Settings", "restrict_multiple_orders_in_single_shift"):
        result = frappe.db.count("Quotation", {
            "customer_name": customer,
            "delivery_shift": delivery_shift,
            "route": route,
            "delivery_date": delivery_date,
            "docstatus": 1
        })
        if result > 0:
            return 1


@frappe.whitelist()
def order_role():
    role = frappe.get_roles(frappe.session.user)
    fixed_role = frappe.db.get_single_value("Dairy Settings", "order_controller")
    if fixed_role in role:
        return 1


@frappe.whitelist()
def get_customer(doc_name):
    route = frappe.db.sql(
        """select link_name from `tabDynamic Link` 
           where parent = %(doc_name)s and link_doctype = "Route Master" """,
        {"doc_name": doc_name}
    )
    return route


@frappe.whitelist()
def set_territory():
    return frappe.db.get_single_value("Dairy Settings", "get_territory")


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
            target.cost_center = (
                frappe.db.get_value("Project", source_parent.project, "cost_center")
                or item.get("buying_cost_center")
                or item_group.get("buying_cost_center")
            )

    mapper = {
        "Sales Order": {"doctype": "Delivery Note", "validation": {"docstatus": ["=", 1]}},
        "Sales Taxes and Charges": {"doctype": "Sales Taxes and Charges", "add_if_empty": True},
        "Sales Team": {"doctype": "Sales Team", "add_if_empty": True}
    }

    if not skip_item_mapping:
        mapper["Sales Order Item"] = {
            "doctype": "Delivery Note Item",
            "field_map": {"rate": "rate", "name": "so_detail", "parent": "against_sales_order"},
            "postprocess": update_item,
            "condition": lambda doc: abs(doc.delivered_qty) < abs(doc.qty) and doc.delivered_by_supplier != 1,
        }

    target_doc = get_mapped_doc("Sales Order", source_name, mapper, target_doc, set_missing_values)
    return target_doc


@frappe.whitelist()
def defsellinguom(doc_name=None):
    try:
        doc = frappe.get_cached("Item", doc_name)
        if doc.sales_uom:
            res = frappe.db.sql(
                """select uom, conversion_factor from `tabUOM Conversion Detail` 
                   where parent = %(p)s and uom = %(u)s""",
                {"p": doc_name, "u": doc.sales_uom},
                as_dict=True
            )
            return res
        else:
            return 1
    except Exception:
        frappe.throw("Select Item")


@frappe.whitelist()
def get_party_bal(customer):
    cust_name = customer
    doctype = "Customer"
    loyalty_program = None

    party_bal = get_dashboard_info(doctype, cust_name, loyalty_program)
    if cust_name and party_bal:
        return party_bal[0]["total_unpaid"]


@frappe.whitelist()
def get_party_bal(self, method):
    cust_name = self.customer
    doctype = "Customer"
    loyalty_program = None

    party_bal = get_dashboard_info(doctype, cust_name, loyalty_program)
    if cust_name and party_bal:
        self.party_balance = party_bal[0]["total_unpaid"]