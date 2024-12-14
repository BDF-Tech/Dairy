from __future__ import unicode_literals
from erpnext.accounts.party import get_dashboard_info
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt,cint, cstr, getdate

def before_submit(self,method):
    qty=[]
    for i in self.items:
        item=frappe.get_doc("Item",i.item_code)
        for k in item.crate:
            if k.uom=="Crate" and k.warehouse==i.warehouse:
                qty=0
                for crate in self.crate_count:
                    if k.crate_type==crate.crate_type:
                        qty+=i.stock_qty
                        aqty=(qty/(k.crate_quantity*(1+item.crate_overage/100)))
                        crate.db_set("outgoing_count",aqty)
                        crate.db_set("qty",qty)
    for k in self.items:
        price_list=frappe.db.get_value("Item Price",{"item_code":k.item_code,"price_list":self.selling_price_list},["price_list_rate"])
        if price_list:
            itemd=frappe.get_doc("Item",k.item_code)
            if itemd.custom_disable_validation_for_price==0:
                if price_list*(k.stock_qty/k.qty) !=k.rate:
                    frappe.throw("You can't save Invoice because Orf Rate Not Match In Row '{0}'".format(k.idx))
    if frappe.db.get_single_value("Dairy Settings", "crate_reconciliation_based_on") == "Sales Invoice":
        dist_cratetype = frappe.db.sql(""" select distinct(crate_type) 
                                           from `tabCrate Count Child` 
    	                                   where parent = %(name)s""", {'name': self.name})

        for crate in dist_cratetype:
            dist_warehouse = frappe.db.sql("""select distinct(warehouse) 
                                               from `tabCrate Count Child` 
    					                        where parent = %(name)s and crate_type = %(crate_type)s """,
                                                       {'name': self.name, 'crate_type': crate})

            for warehouse in dist_warehouse:
                sums = frappe.db.sql(""" select 
                                            sum(outgoing_count) as crate, sum(incoming_count) as crate_ret, sum(damaged_count) as damaged_crate
    			                          from 
    			                            `tabCrate Count Child` 
    			                          where 
    			                                crate_type = %(crate)s and parent = %(name)s and warehouse = %(warehouse)s""",
                                                {'crate': crate, 'name': self.name, 'warehouse': warehouse}, as_dict=1)
                log = frappe.new_doc("Crate Log")
                log.customer = self.customer
                # log.vehicle = self.vehicle
                log.route = self.route
                log.date = frappe.utils.nowdate()
                log.company = self.company
                log.voucher_type = "Sales Invoice"
                log.voucher = self.name
                log.damaged = sums[0]['damaged_crate']
                log.crate_issue = sums[0]['crate']
                log.crate_return = sums[0]['crate_ret']
                log.crate_type = crate[0]
                log.source_warehouse = warehouse[0]
                log.note = "Entry Created From Sales Invoice"

                openning_cnt = frappe.db.sql(""" select count(*) 
                                                 from `tabCrate Log`  
                                                 where crate_type = %(crate)s and source_warehouse = %(warehouse)s and company = %(company)s and  docstatus = 1	 order by date desc  """,
                                                 {'crate': crate, 'warehouse': warehouse,'company': self.company}, as_dict=1)

                if openning_cnt[0]['count(*)'] > 0:
                    openning = frappe.db.sql(""" select crate_balance 
                                                 from `tabCrate Log`  
                                                 where crate_type = %(crate)s and source_warehouse = %(warehouse)s and
    				                                    company = %(company)s and  docstatus = 1 order by date desc limit 1 """,
                                                        {'crate': crate, 'warehouse': warehouse, 'company': self.company},as_dict=1)

                    log.crate_opening = int(openning[0]['crate_balance'])
                    log.crate_balance = openning[0]['crate_balance'] - (sums[0]['crate'] + sums[0]['crate_ret'])

                else:
                    log.crate_opening = int(0)
                    log.crate_balance = int(0) - (sums[0]['crate'] + sums[0]['crate_ret'])

                log.save(ignore_permissions=True)
                log.submit()


@frappe.whitelist()
def calculate_crate_save(name):
    
    c_count=[]
    
    doc_name = name
    if doc_name:
        doc = frappe.get_doc("Sales Invoice",doc_name)
        # add_crate_count_item_line(doc)
        frappe.db.sql("delete from `tabCrate Count Child` where parent = %s",(doc.name))
        frappe.db.sql("delete from `tabLoose Crate` where parent = %s", (doc.name))
        dict_create_type = dict()
        dist_itm = list(frappe.db.sql("""select 
                                            distinct(item_code) 
                                        from 
                                            `tabSales Invoice Item` 
                                        where 
                                            parent= %(parent)s """,{'parent':doc.name}))
        total_supp_qty = 0
        total_crate_qty = 0
        total_free_qty = 0

        for i in range(0,len(dist_itm)):
            overage_details = frappe.get_doc("Item",dist_itm[i][0])
            overage = overage_details.crate_overage
            has_batch_no = overage_details.has_batch_no
            dist_warehouse = list(frappe.db.sql("""select 
                                                        distinct(warehouse) 
                                                    from 
                                                        `tabSales Invoice Item` 
                                                    where 
                                                        item_code= %(item_code)s and parent=%(parent)s """,{'item_code':dist_itm[i],"parent":doc.name}))
            

            for j in range(0,len(dist_warehouse)):
                if has_batch_no == 1:
                    dist_batch_no = list(frappe.db.sql("""select 
                                                            distinct(batch_no) 
                                                            from 
                                                            `tabSales Invoice Item` 
                                                            where 
                                                            warehouse = %(warehouse)s and item_code = %(item_code)s and parent = %(doc_name)s """,
                                                            {'warehouse':dist_warehouse[j],'item_code':dist_itm[i],'doc_name':doc_name}))
                    for k in range(0, len(dist_batch_no)):
                        total_qty = frappe.db.sql(""" select 
                                                            sum(stock_qty) 
                                                        from 
                                                            `tabSales Invoice Item` 
                                                        where
                                                            is_free_item = 0 and warehouse = %(warehouse)s and item_code = %(item_code)s and parent = %(doc_name)s and batch_no = %(batch_no)s""",
                                                            {'warehouse':dist_warehouse[j],'item_code':dist_itm[i],'doc_name':doc_name,'batch_no':dist_batch_no[k]})
                        free_qty = 0

                        free_qty_list = frappe.db.sql(""" select 
                                                                sum(stock_qty) 
                                                            from 
                                                                `tabSales Invoice Item` 
                                                            where
                                                                is_free_item = 1 and warehouse = %(warehouse)s and item_code = %(item_code)s and parent = %(doc_name)s and batch_no = %(batch_no)s""",
                                                                {'warehouse': dist_warehouse[j], 'item_code': dist_itm[i],'doc_name': doc_name, 'batch_no': dist_batch_no[k]})
                        if str(free_qty_list[0][0]) != "None":
                            free_qty = int(free_qty_list[0][0])

                        ttl_qty = str(total_qty[0][0])
                        if flt(ttl_qty)>0:
                            crate_details = frappe.db.sql(""" select 
                                                                    crate_quantity,crate_type 
                                                                from 
                                                                    `tabCrate` 
                                                                where 
                                                                    parent = %(item_code)s and warehouse = %(warehouse)s limit 1 """,
                                                                    {'item_code':dist_itm[i],'warehouse':dist_warehouse[j]})


                            if len(crate_details) > 0:
                                c_count.append( {
                                                    'crate_type': crate_details[0][1],
                                                    'outgoing_count': int(round(((total_qty[0][0] + free_qty) / int((crate_details[0][0])* (1 + overage/100))), 2)),
                                                    'item_code': dist_itm[i][0],
                                                    'item_name': overage_details.item_name,
                                                    'qty': total_qty[0][0],
                                                    'batch_no': dist_batch_no[k][0],
                                                    'uom': overage_details.stock_uom,
                                                    'free_qty': free_qty,
                                                    'warehouse': dist_warehouse[j][0]
                                                })
                                
                                total_supp_qty += total_qty[0][0]
                                total_crate_qty += int(round(((total_qty[0][0] + free_qty) / int((crate_details[0][0])* (1 + overage/100))), 2))
                                str_free_qty = str(free_qty)

                                if (str_free_qty != "None"):
                                    total_free_qty += int(free_qty)

                                qty = int(round(((total_qty[0][0] + free_qty) % int(((crate_details[0][0]) * (1 + overage/100)))), 2))

                                if qty > 0:
                                    doc.append('loose_crate', {
                                        'item_code': dist_itm[i][0],
                                        'crate_type': crate_details[0][1],
                                        'qty': int(round(((total_qty[0][0] + free_qty) % int(((crate_details[0][0]) * (1 + overage/100)))), 2))
                                    })
                    

                elif has_batch_no == 0:
                    free_qty = 0
                    free_qty_list = frappe.db.sql(""" select 
                                                            sum(stock_qty) 
                                                        from 
                                                            `tabSales Invoice Item` 
                                                        where 
                                                            is_free_item = 1 and warehouse = %(warehouse)s and item_code = %(item_code)s and parent = %(doc_name)s""",
                                                            {'warehouse': dist_warehouse[j], 'item_code': dist_itm[i], 'doc_name': doc_name})

                    if str(free_qty_list[0][0]) != "None":
                        free_qty = free_qty_list[0][0]

                    total_qty = frappe.db.sql(""" select 
                                                        sum(stock_qty) 
                                                    from 
                                                        `tabSales Invoice Item` 
                                                    where
                                                    is_free_item = 0 and warehouse = %(warehouse)s and item_code = %(item_code)s and parent = %(doc_name)s""",
                                                    {'warehouse': dist_warehouse[j], 'item_code': dist_itm[i],'doc_name': doc_name})

                    ttl_qty = str(total_qty[0][0])

                    if ttl_qty != "None":
                        crate_details = frappe.db.sql(""" select 
                                                                crate_quantity,crate_type 
                                                            from 
                                                                `tabCrate` 
                                                            where 
                                                                    parent = %(item_code)s and warehouse = %(warehouse)s limit 1 """,
                                                                {'item_code': dist_itm[i],'warehouse': dist_warehouse[j]})
                        if len(crate_details) > 0:
                            c_count.append( {
                                'crate_type': crate_details[0][1],
                                'outgoing_count': int(round(((total_qty[0][0] + free_qty) / int((crate_details[0][0]) * (1 + overage / 100))),2)),
                                'item_code': dist_itm[i][0],
                                'item_name': overage_details.item_name,
                                'qty': total_qty[0][0],
                                'uom': overage_details.stock_uom,
                                'free_qty': free_qty,
                                'warehouse': dist_warehouse[j][0]
                            })
                            total_supp_qty += total_qty[0][0]
                            total_crate_qty += int(round(((total_qty[0][0] + free_qty) / int((crate_details[0][0]) * (1 + overage / 100))), 2))
                            str_free_qty = str(free_qty)

                            if (str_free_qty != "None"):
                                total_free_qty += int(free_qty)
                            qty = int(round(((total_qty[0][0] + free_qty) % int(((crate_details[0][0]) * (1 + overage / 100)))), 2))

                            if qty > 0:
                                doc.append('loose_crate', {
                                    'item_code': dist_itm[i][0],
                                    'crate_type': crate_details[0][1],
                                    'qty': int(round(((total_qty[0][0] + free_qty) % int(((crate_details[0][0]) * (1 + overage / 100)))), 2))
                                })
        doc.crate_count=c_count
        doc.total_supp_qty = total_supp_qty
        doc.total_crate_qty = total_crate_qty
        doc.total_free_qty = total_free_qty
        doc.crate_cal_done = "Done"
        
            
        return c_count


@frappe.whitelist()
def route_validation(obj, method):
    doc = frappe.get_doc(obj)
    item_code_lst = ['0000']
    for i in doc.items:
        item_code_lst.append(i.item_code)
    query = """select TIG.route_required,TI.name from `tabItem Group` TIG 
                inner join `tabItem` TI on TIG.name =TI.item_group 
                where route_required != 0 and TI.name in {0} """.format(tuple(item_code_lst))
    result = frappe.db.sql(query)
    if result and not doc.route:
        frappe.throw(_("Please select route is Mandatory"))

@frappe.whitelist()
def get_route_price_list(doc_name=None):
    if doc_name:
        route_name = frappe.db.sql("""select link_name from `tabDynamic Link` 
                                where parenttype ='Customer'  
                                and link_doctype ='Route Master' 
                                and parent =%s limit 1""",(doc_name))
        if route_name:
            dic ={}
            doc = frappe.get_doc("Route Master",route_name[0][0])
            dic['route'] = doc.name
            dic['p_list'] = doc.price_list
            dic['warehouse'] = doc.source_warehouse
            return dic
        return  False

@frappe.whitelist()
def get_route_price_list_route(doc_name=None):
    if doc_name:
        route_name = frappe.db.sql("""select parent from `tabDynamic Link`
                                where parenttype ='Customer'
                                and link_doctype ='Route Master'
                                and link_name =%s limit 1""",(doc_name))
        if route_name:
            dic = {}
            dic['route'] = route_name[0][0]
            return dic
        return False


@frappe.whitelist()
def set_fat_and_snf_rate(obj,method):
    if obj.customer:
        query = frappe.db.sql("""select tbm.name,tbm.milk_type,tbm.rate,tbm.snf_clr_rate from `tabBulk Milk Price List` as tbm inner join 
                `tabBulk Milk Price List Customer` as tbc on tbc.parent = tbm.name
                where tbm.docstatus = 1 and tbm.active = 1 and tbc.customer = %s and tbm.milk_type = %s  
                order by tbm.creation desc limit 1""", (obj.customer,obj.milk_type), as_dict=True)
        if query:
            obj.fat_rate = query[0].rate
            obj.snf_clr_rate = query[0].snf_clr_rate
            #
            for res in obj.items:
                if res.fat and query[0].rate:
                    res.fat_amount = res.fat * query[0].rate
                if res.snf_clr and query[0].snf_clr_rate:
                    res.snf_clr_amount = res.snf_clr * query[0].snf_clr_rate

@frappe.whitelist()
def get_party_bal(customer,company):
    cust_name =customer
    doctype = "Customer"
    loyalty_program = None

    party_bal = get_dashboard_info(doctype, cust_name, loyalty_program)

    if cust_name and party_bal:
        for j in party_bal:
            if company==j.get("company"):
                return j.get("total_unpaid")



@frappe.whitelist()
def get_party_bal_det(self,method):
    cust_name =self.customer
    doctype = "Customer"
    loyalty_program = None

    party_bal = get_dashboard_info(doctype, cust_name, loyalty_program)
    if cust_name and party_bal:
        for j in party_bal:
            if self.company==j.get("company"):
                self.party_balance=j.get("total_unpaid")