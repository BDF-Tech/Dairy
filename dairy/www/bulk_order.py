import frappe
import json
import math

from frappe.utils.data import flt
# from frappe.utils import getdate
def get_context(context):
    context.items = frappe.get_list("Website Item", filters={'published': 1}, fields=["item_name", "item_code","website_image"],order_by="item_name asc")


@frappe.whitelist()
def make_so(item_list):
    
    customer_name = None
    all_contact_doc_name = frappe.db.get_all("Contact",{"user":frappe.session.user},['user','name'])
    for con in all_contact_doc_name:
        # try:
        contact_doc = frappe.get_doc("Contact", con)
        link_table = contact_doc.get('links')
        if(len(link_table) > 0):
            customer_name = link_table[0].get('link_name')
    item_with_all_data = []
    for item in json.loads(item_list):
        if (item.get("qty")):
            if int(item.get('qty')) > 0:
                fetch_details = frappe.db.get_all("Website Item",{"item_code" : item.get('item_code')},["item_name", "item_code","website_image"])
                print("888888888888888888888888888888888888",fetch_details)
                for i in fetch_details:
                    item['item_name'] = i.item_name
                    item['website_image'] = i.website_image
                    item_with_all_data.append(item)

    cache = frappe.cache()
    print("************************",item_with_all_data)
    saor=frappe.db.get_value("Sales Order",{"name":cache.get_value("so_name"),"docstatus":0,"delivery_shift":cache.get_value("delivery_shift").title() if cache.get_value("delivery_shift") else "Morning"},"name")
    if not saor:
        so = frappe.new_doc("Sales Order")
        so.company = frappe.db.sql("select name from `tabCompany`;")[0][0]
        # get_price_list = frappe.db.get_single_value("Bulk Order Settings", "price_list")
        # if not get_price_list:
        #     frappe.throw('Please select price list in <b> Bulk Order Settings</b>')
        so.customer = customer_name
        cache.set_value('customer_name', customer_name)
        f=frappe.get_doc("Customer", so.customer )
        print("uuuuuuuuuuuuuuuuuuuuuuuu",f)
        so.price_list=f.default_price_list
        # so.price_list = get_price_list
        so.order_type = "Shopping Cart"
        so.transaction_date = frappe.utils.nowdate()
        del_date = None
        del_date = cache.get_value("del_date")
        if not del_date:
            del_date = frappe.utils.nowdate()
        so.delivery_date=del_date
        item_rate=0
        if cache.get_value("delivery_shift"):
            delivery_shift = cache.get_value("delivery_shift").title()

        else:
            delivery_shift="Morning"
        so.delivery_shift=delivery_shift
        website_warehouse = frappe.db.get_single_value("Bulk Order Settings", 'default_warehouse')
        print("item******************************",json.loads(item_list))
        for data in json.loads(item_list):
            print("89999999999999999999111111",data)
            if (data.get("qty")):
                if(int(data.get("qty")) > 0):
                    if not website_warehouse:
                        m = "warehouse not found for item {0} <br> please set default warehouse in bulk order settings ".format(data.get("item_code"))
                        msg = {
                            'status': False,
                            'msg': m
                        }
                        return msg
                
                    # get_price_list = frappe.db.get_single_value("Bulk Order Settings", 'price_list')
                    
                    item_rate = frappe.db.get_value("Item Price", {'item_code':data.get('item_code'),'price_list': f.default_price_list} , "price_list_rate")
                
                    item = {
                    "item_code" : data.get("item_code"),
                    "delivery_date" : del_date,
                    "qty" : data.get("qty"),
                    "rate" : item_rate,
                    "conversion_rate":1,
                    "stock_qty":flt(data.get("qty"))*1,
                    "uom":data.get("uom"),
                    "warehouse" : website_warehouse
                    }
                    so.append("items", item)
        try:
            so.insert(ignore_permissions=True)
            cache.set_value('so_name', so.name)
            # print("$$$$$$$$$$$$$$$$$$$$$$$$$$",item_with_all_data)
            for item in so.items:
                a=0
                for i in item_with_all_data:
                    if (i.get('item_code') == item.get('item_code')) and a==0:
                        a=1
                        doc=frappe.get_doc("Item",i.get('item_code'))
                        item.uom=doc.stock_uom
                        i['rate'] = item.get('rate')
                        i['amount'] = item.get('amount')
                        i['uom']= doc.stock_uom
            so.save(ignore_permissions=True)
            print("$$$$$$$$55555666666666666666",item_with_all_data)
            cache.set_value('item_list', item_with_all_data)
            cache.set_value('rounded_up_total', so.rounded_total)
            cache.set_value('rounding_adjustment', so.rounding_adjustment)
            cache.set_value('total_amount', so.grand_total)
            cache.set_value('default_cust_add', so.customer_address)
            cache.set_value('default_ship_add', so.shipping_address_name)



            return {
                'status': True,
                'so_name': so.name
            }
        except:
            return False
        
    else:
        sal_ord=frappe.get_doc("Sales Order",saor)
        print("5555555555555555222222222222",sal_ord)
        sal_ord.company = frappe.db.sql("select name from `tabCompany`;")[0][0]
        # get_price_list = frappe.db.get_single_value("Bulk Order Settings", "price_list")
        # if not get_price_list:
        #     frappe.throw('Please select price list in <b> Bulk Order Settings</b>')
        sal_ord.customer = customer_name
        print("uuuuuuuuut666666666666666666666667",customer_name)
        cache.set_value('customer_name', customer_name)
        f=frappe.get_doc("Customer", sal_ord.customer )
        print("7777777777777777777777777777777777",f)
        sal_ord.price_list=f.default_price_list
        # so.price_list = get_price_list
        sal_ord.order_type = "Shopping Cart"
        sal_ord.transaction_date = frappe.utils.nowdate()
        del_date = None
        del_date = cache.get_value("del_date")
        if not del_date:
            del_date = frappe.utils.nowdate()
            print("8888888888888888888888888888888888",del_date)
        sal_ord.delivery_date=del_date
        item_rate=0
        if cache.get_value("delivery_shift"):
            delivery_shift = cache.get_value("delivery_shift").title()

        else:
            delivery_shift="Morning"
        sal_ord.delivery_shift=delivery_shift
        website_warehouse = frappe.db.get_single_value("Bulk Order Settings", 'default_warehouse')
        for data in json.loads(item_list):
            print("2111111111111111111111111111",data)
            if (data.get("qty")):
                if(int(data.get("qty")) > 0):
                    if not website_warehouse:
                        m = "warehouse not found for item {0} <br> please set default warehouse in bulk order settings ".format(data.get("item_code"))
                        msg = {
                            'status': False,
                            'msg': m
                        }
                        return msg
                
                    # get_price_list = frappe.db.get_single_value("Bulk Order Settings", 'price_list')
                    
                    item_rate = frappe.db.get_value("Item Price", {'item_code':data.get('item_code'),'price_list': f.default_price_list} , "price_list_rate")
                    k=[]
                    for j in sal_ord.items:
                        k.append(j.item_code)
                    for j in sal_ord.items:
                        if j.item_code==data.get("item_code"):
                            j.qty= data.get("qty")

                            j.rate=item_rate
                        else:
                            if data.get("item_code") not in k:
                                item = {
                                "item_code" : data.get("item_code"),
                                "delivery_date" : del_date,
                                "qty" : data.get("qty"),
                                "rate" : item_rate,
                                "conversion_rate":1,
                                "uom":data.get("uom"),
                                "stock_qty":flt(data.get("qty"))*1,
                                "warehouse" : website_warehouse
                                }
                                sal_ord.append("items", item)
                                print("88888888888888832",item)
        try:
            sal_ord.save(ignore_permissions=True)
            cache.set_value('so_name', sal_ord.name)
            for item in sal_ord.items:
                a=0
                for i in item_with_all_data:
                    if (i.get('item_code') == item.get('item_code')) and a==0:
                        a=1
                        doc=frappe.get_doc("Item",i.get('item_code'))
                        item.uom=doc.stock_uom
                        i['rate'] = item.get('rate')
                        i['amount'] = item.get('amount')
                        i['uom'] = doc.stock_uom
            so.save(ignore_permissions=True)

            cache.set_value('item_list', item_with_all_data)
            cache.set_value('rounded_up_total', sal_ord.rounded_total)
            cache.set_value('rounding_adjustment', sal_ord.rounding_adjustment)
            cache.set_value('total_amount', sal_ord.grand_total)
            cache.set_value('default_cust_add', sal_ord.customer_address)
            cache.set_value('default_ship_add', sal_ord.shipping_address_name)


            return {
                'status': True,
                'so_name': sal_ord.name
            }
        except:
            return False

@frappe.whitelist()
def handle_date(date):
    frappe.cache().set_value("del_date", date)

@frappe.whitelist()
def handle_shift(shift):
    frappe.cache().set_value("delivery_shift",shift) 
    return shift

   

