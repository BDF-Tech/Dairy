from __future__ import unicode_literals
import datetime
import json
from dairy.milk_entry.custom_milk_ledger import get_columns, get_item_details, get_items, get_opening_balance, get_stock_ledger_entries
# from dairy.milk_entry.custom_milk_ledger import get_columns, get_item_details, get_items, get_opening_balance, get_stock_ledger_entries
from erpnext.stock.utils import update_included_uom_in_report
import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import flt,cint, cstr, getdate
from frappe.utils.data import get_time, today

def milk_ledger_stock_entry(self,method):
    if not self.get("__islocal"):
        if not self.van_collection and not self.van_collection_item:

            good_cow_milk = frappe.db.get_single_value("Dairy Settings", "cow_pro")
            good_buff_milk = frappe.db.get_single_value("Dairy Settings", "buf_pro")
            good_mix_milk = frappe.db.get_single_value("Dairy Settings", "mix_pro")
            milk_type = ""
            for itm in self.items:
                if itm.s_warehouse:
                    itm_obj = frappe.get_doc("Item",itm.item_code)
                    itm_weight = float(itm_obj.weight_per_unit)
                    weight_uom = itm_obj.weight_uom
                    maintain_snf_fat = itm_obj.maintain_fat_snf_clr
                    itm_milk_type = itm_obj.milk_type
                
                    if itm.item_code == good_cow_milk or itm.item_code == good_buff_milk or itm.item_code == good_mix_milk or maintain_snf_fat == 1:
                        if itm.item_code == good_cow_milk:
                            milk_type = "Cow"
                        elif itm.item_code == good_buff_milk:
                            milk_type = "Buffalo"
                        elif itm.item_code == good_mix_milk:
                            milk_type = "Mix"
                        elif maintain_snf_fat == 1:
                            milk_type = itm_milk_type
                            
                        query = """ select name from `tabMilk Ledger Entry` where item_code = %(item_code)s 
                        and warehouse = %(warehouse)s """
                        if itm.batch_no:
                            query += """ and batch_no = %(batch_no)s """
                        if itm.serial_no:
                            query += """ and serial_no = %(serial_no)s """

                        query += """ order by modified desc limit 1 """
                        mle = frappe.db.sql(query,
                                            {'warehouse': itm.s_warehouse, 'item_code': itm.item_code, 'batch_no': itm.batch_no,
                                            'serial_no': itm.serial_no}, as_dict=True)
       

def before_save(self,method):
    if self.stock_entry_type in ["Material Transfer","Material Issue","Material Transfer for Manufacture","Repack"]:
        for s in self.items:
            item = frappe.get_doc('Item',s.item_code)
            filters={'from_date':getdate(self.posting_date),'to_date':getdate(self.posting_date),'warehouse':s.s_warehouse,'item_code':s.item_code,'company':self.company}
            filters=frappe._dict(filters)
            ml=exec(filters)
           
            if (len(ml)) > 1:
                ml = ml[-1]
                if flt(ml.get("qty_after_transaction"))>0:
                    s.fat_per = (ml.get("fat_after_transaction")/ml.get("qty_after_transaction"))*100
                    s.snf_per = (ml.get("fat_after_transaction")/ml.get("qty_after_transaction"))*100
                    s.fat = ((s.qty*flt(s.fat_per))/100) * flt(item.weight_per_unit)
                    s.snf = ((s.qty*flt(s.snf_per))/100) * flt(item.weight_per_unit)
            if (len(ml)) ==1:
                ml = ml[0]
                if flt(ml.get("qty_after_transaction"))>0:
                    s.fat_per = (ml.get("fat_after_transaction")/ml.get("qty_after_transaction"))*100
                    s.snf_per = (ml.get("fat_after_transaction")/ml.get("qty_after_transaction"))*100
                    s.fat = ((s.qty*flt(s.fat_per))/100) * flt(item.weight_per_unit)
                    s.snf = ((s.qty*flt(s.snf_per))/100) * flt(item.weight_per_unit)

    if self.stock_entry_type=="Material Receipt":
        for j in self.items:
            if flt(j.fat_per)>0 or flt(j.snf_per)>0:
                frappe.throw("Fat and Snf Not defined")
    if self.stock_entry_type in ["Manufacture","Material Consumption for Manufacture"]:
        for s in self.items:
            item = frappe.get_doc('Item',s.item_code)
            filters={'from_date':getdate(self.posting_date),'to_date':getdate(self.posting_date),'warehouse':s.t_warehouse,'item_code':s.item_code,'company':self.company}
            filters=frappe._dict(filters)
            ml=exec(filters)
          
            if (len(ml)) > 1:
                ml = ml[-1]
                if flt(ml.get("qty_after_transaction"))>0:
                    s.fat_per = (ml.get("fat_after_transaction")/ml.get("qty_after_transaction"))*100
                    s.snf_per = (ml.get("fat_after_transaction")/ml.get("qty_after_transaction"))*100
                    s.fat = ((s.qty*flt(s.fat_per))/100) * flt(item.weight_per_unit)
                    s.snf = ((s.qty*flt(s.snf_per))/100) * flt(item.weight_per_unit)
            else:
                if ml:
                    ml = ml[0]
                    if flt(ml.get("qty_after_transaction"))>0:
                        s.fat_per = (ml.get("fat_after_transaction")/ml.get("qty_after_transaction"))*100
                        s.snf_per = (ml.get("fat_after_transaction")/ml.get("qty_after_transaction"))*100
                        s.fat = ((s.qty*flt(s.fat_per))/100) * flt(item.weight_per_unit)
                        s.snf = ((s.qty*flt(s.snf_per))/100) * flt(item.weight_per_unit)





def cancel_create_milk_stock_ledger(self,method):
    if self.van_collection or self.van_collection_item:
        vci = frappe.get_doc('Van Collection Items',self.van_collection_item)
        if vci.van_collection == self.van_collection:
            vc = frappe.get_doc('Van Collection',self.van_collection)
            vc.db_set('status','In-Progress')
            vc.db_update()
          

    if self.rmrd or self.rmrd_lines:
        r_lines = frappe.get_doc('RMRD Lines',self.rmrd_lines)
        if r_lines.rmrd == self.rmrd:
            rmrd = frappe.get_doc('RMRD',self.rmrd)
            rmrd.db_set('status','In-Progress')
            rmrd.db_update()

                                      
    vci = frappe.get_all('Van Collection Items',{'gate_pass':self.name},['name'])
   
    for i in vci:
        doc=frappe.get_doc("Van Collection Items",i.name)
        se_del = doc.gate_pass
        doc.db_set("gate_pass","")
        self.van_collection_item = ""
        
      

    r_lines = frappe.get_all('RMRD Lines',{'stock_entry':self.name},['name'])
    for rl in r_lines:
        doc1 = frappe.get_doc('RMRD Lines',rl.name)
        se_dlt = doc1.stock_entry
        doc1.db_set('stock_entry',"")
        self.rmrd = ""
       
       


    


@frappe.whitelist()
def get_item_weight(item_code):
    obj = frappe.get_doc("Item",item_code)
    return obj.weight_per_unit


def update_vc_status(self,method):
    if self.van_collection and self.van_collection_item:
        vci = frappe.get_doc('Van Collection Items',self.van_collection_item)
        if vci.van_collection == self.van_collection:
            vc = frappe.get_doc('Van Collection',self.van_collection)
            vc.db_set('status','Completed')
            vc.db_update()
         

    if self.rmrd and self.rmrd_lines:
        r_lines = frappe.get_doc('RMRD Lines',self.rmrd_lines)
        if r_lines.rmrd == self.rmrd:
            rmrd = frappe.get_doc('RMRD',self.rmrd)
            rmrd.db_set('status','Completed')
            rmrd.db_update()
          




    


def exec(filters=None):
    include_uom = filters.get("include_uom")
    columns = get_columns()
    items = get_items(filters)
    sl_entries = get_stock_ledger_entries(filters, items)
    item_details = get_item_details(items, sl_entries, include_uom)
    opening_row = get_opening_balance(filters, columns)
    precision = cint(frappe.db.get_single_value("System Settings", "float_precision"))

    data = []
    conversion_factors = []
    if opening_row:                                     
        data.append(opening_row)


    for sle in sl_entries:
        
        item_detail = item_details[sle.item_code]

        sle.update(item_detail)

        if filters.get("batch_no"):
            actual_qty += flt(sle.actual_qty, precision)
           

            if sle.voucher_type == 'Stock Reconciliation' and not sle.actual_qty:
                actual_qty = sle.qty_after_transaction
               

            sle.update({
                "qty_after_transaction": abs(actual_qty)
                # "stock_value": stock_value
            })
        a = max(sle.mle_act_qty, 0)
        b =  min(sle.mle_act_qty, 0)
        sle.update({
            "in_wt": abs(a),
            "out_wt": abs(b)
        })
        e = max(sle.fat, 0)
        f = min(sle.fat, 0)
        sle.update({
            "in_fat": abs(e),
            "out_fat": abs(f)
        })
        c =  max(sle.snf, 0)
        d = min(sle.snf, 0)
        sle.update({
            "in_snf": abs(c),
            "out_snf": abs(d)
        })
        
        h =  max(sle.sle_act_qty ,0)
        i = min(sle.sle_act_qty,0)
        sle.update({
            "in_qty": abs(h),
            "out_qty": abs(i)
        })
        

        data.append(sle)
      

        if include_uom:
            conversion_factors.append(item_detail.conversion_factor)

    update_included_uom_in_report(columns, data, include_uom, conversion_factors)
    return data



        
@frappe.whitelist()
def add_scrap_item(work_order,stock_entry_type):
    items=[]
    if stock_entry_type=="Manufacture":
        doc=frappe.get_doc("Work Order",work_order)
        for i in doc.fg_item_scrap:
            items.append({"item":i.item,"qty":i.qty})
    return items



@frappe.whitelist()
def set_date():
    shift=frappe.db.get_all("Shift Type",{"docstatus":0},["name"])
    for kj in shift:
        doc=frappe.get_doc("Shift Type",kj.name)
        combined_datetime = datetime.datetime.combine(getdate(today()),get_time("23:59:59"))
        doc.last_sync_of_checkin=combined_datetime
        doc.save(ignore_permissions=True)


