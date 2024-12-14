import frappe
import datetime
import json
from frappe.sessions import clear
from frappe.utils import caching

from frappe.utils.data import today
from frappe.website.utils import clear_cache

def get_context(context):
    user = frappe.db.get_value("User", frappe.session.user, 'first_name')

    context.user = user
    context.naming_series = list(frappe.db.sql("select distinct naming_series from `tabSales Order`;"))
    cache = frappe.cache()
    get_cached_data = cache.get_value("item_list")
    print("$$$$$$$$$4444444444444444",get_cached_data)
    context.item_details = get_cached_data
    print("*****************************",context.item_details)
    context.grand_total = cache.get_value("total_amount")
    context.rounded_up_total = cache.get_value('rounded_up_total')
    context.rounding_adjustment= cache.get_value('rounding_adjustment')
    context.so_num = cache.get_value('so_name')
    # context.delivery_shift = cache.get_value('delivery_shift')

    if cache.get_value('delivery_shift'):
        context.delivery_shift = str(cache.get_value('delivery_shift')).title()
        print("777888888888888888888888888888888888888",context.delivery_shift)

    else:
        context.delivery_shift="Morning"



    

    if cache.get_value('del_date'):

        formated_date = datetime.datetime.strptime(cache.get_value('del_date'), "%Y-%m-%d").strftime("%d-%m-%Y")
        print("$$$$$$$$$$$$$$$$$$$$",formated_date)
        if formated_date:
            context.del_date = formated_date
    else:
        context.del_date=datetime.datetime.strptime(str(today()), "%Y-%m-%d").strftime("%d-%m-%Y")
    context.order_date = datetime.datetime.now().strftime("%d-%m-%Y")
    customer=frappe.db.get_value("Customer",{"customer_name":user},"name")
    filters = [["Dynamic Link", "link_doctype", "=", "Customer"],["Dynamic Link", "link_name", "=", customer],["Dynamic Link", "parenttype", "=", "Address"]]

    address_list=frappe.db.sql("""select a.* from `tabAddress` a join `tabDynamic Link` d on a.name=d.parent 
                               where d.link_name='{0}' and d.link_doctype='Customer' and d.parenttype='Address'""".format(customer),as_dict=1)
    context.address_list = address_list
    default_cust_add_name = cache.get_value("default_cust_add")
    context.default_cust_add = default_cust_add_name
    for add in address_list:
        if(add.get('name') == default_cust_add_name):
            customer_add = {
                "address_line1" : add.get("address_line1"),
                "address_line2" : add.get("address_line2"),
                "city" : add.get("city"),
                "county" : add.get("county"),
                "state" : add.get("state"),
                "country" : add.get("country"),
                "pincode" : add.get("pincode"),
                "gstin" : add.get("gstin")
            }
            if not customer_add:
                frappe.throw("Address not found")
            context.def_cust_add = customer_add


    default_ship_add_name = cache.get_value("default_ship_add")
    context.default_ship_add = default_ship_add_name
    for add in address_list:
        if(add.get('name') == default_ship_add_name):
            customer_add = {
                "address_line1" : add.get("address_line1"),
                "address_line2" : add.get("address_line2"),
                "city" : add.get("city"),
                "county" : add.get("county"),
                "state" : add.get("state"),
                "country" : add.get("country"),
                "pincode" : add.get("pincode"),
                "gstin" : add.get("gstin"),
                "gst_state_number" : add.get("gst_state_number"),
                "gst_state" : add.get("gst_state")
            }
            context.def_ship_add = customer_add
        print("888888888888888888888888888888888888",type(context))

@frappe.whitelist()
def make_so(item_list):
    get_cached_data = frappe.cache()
    so = frappe.get_doc("Sales Order", get_cached_data.get_value("so_name"))
    filters_json = frappe.get_all("Order Warehouse Rule", {"active":'1'},["name1","filters_json", "warehouse", "priority","active"])
    # filter={}
    filter_list = []
    # rule_detail = {}
    order_warehouse = None
    order_warehouse_num = None
    copy_list = []
    for filters in filters_json:
        filter={}
        if(filters.get("filters_json")):
            filter_in_json = json.loads(filters.get("filters_json"))
            for lst in filter_in_json:
                filter[lst[1]] = [lst[2],lst[3]]  
            filter['warehouse'] = filters.get("warehouse")
            filter["priority"] = filters.get("priority")
            filter["rule_name"] = filters.get("name1")
            filter_list.append(filter)

    for fil in filter_list:
        copy = fil.copy()
        if fil.get('warehouse'):
            del fil['warehouse']
        if fil.get('rule_name'):
            del fil['rule_name']
        if fil.get('priority'):
            del fil['priority']
        fil['name'] = ['=', get_cached_data.get_value("so_name")]
        
        get_so = frappe.db.get_value('Sales Order', fil, ['name'])
        if(get_so == get_cached_data.get_value("so_name")):
            copy_list.append(copy)

    #m_p_w = None
    # def get_order_warehouse():
    if(len(filter_list) > 0):
        warehouse_details =  max(copy_list, key=lambda x:x['priority'])
        # return [warehouse_details.get('rule_name'),warehouse_details.get('warehouse')]
        order_warehouse = warehouse_details.get('warehouse')
        order_warehouse_num = warehouse_details.get('rule_name')
    for i in so.get('items'):
        i.warehouse = order_warehouse
        i.conversion_factor=1
        i.stock_qty=i.qty*1

        

    cust_add = get_cached_data.get_value("custom_add")
    ship_add = get_cached_data.get_value("ship_add")
    if(cust_add):
        so.customer_address = cust_add
    if(ship_add):
        so.shipping_address_name = ship_add
    so.order_warehouse_rule_number = order_warehouse_num
    #so.db_update()
    so.order_warehouse_rule_number = order_warehouse_num
    so.save(ignore_permissions=True)
    # so.submit()

    get_cached_data.delete_value("custom_add")
    get_cached_data.delete_value("ship_add")
    
    msg = {
        "so_name" : so.name,
        "warehouse": order_warehouse,
        "rule": order_warehouse_num
    }
    so.db_update()
    get_cached_data.delete_value("so_name")
    get_cached_data.delete_value("del_date")
    get_cached_data.delete_value("delivery_shift")
    frappe.clear_cache()
    
    return msg

@frappe.whitelist()
def handle_address(name):
    name = json.loads(name)
    print("33333333333111111111111111111",name)
    filters = [["Dynamic Link", "link_doctype", "=", "Customer"],["Dynamic Link", "link_name", "=", name],["Dynamic Link", "parenttype", "=", "Address"]]
    address_list = frappe.get_all("Address", filters=filters, fields=["*"])
    for address in address_list:
        if(address.get("name") == name.get("value")):
            frappe.cache().set_value(name.get("key"),name.get("value"))
            return address
        
