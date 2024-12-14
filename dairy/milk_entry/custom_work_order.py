# from dairy.milk_entry.custom_milk_ledger import get_columns, get_item_details, get_items, get_opening_balance, get_stock_ledger_entries
from dairy.milk_entry.custom_milk_ledger import get_columns, get_item_details, get_items, get_opening_balance, get_stock_ledger_entries
from erpnext.manufacturing.doctype.bom.bom import validate_bom_no
from erpnext.manufacturing.doctype.work_order.work_order import CapacityError, WorkOrder
from erpnext.stock.utils import update_included_uom_in_report
from erpnext.utilities.transaction_base import validate_uom_is_integer
import frappe
from frappe.utils.data import cint, date_diff, flt, get_link_to_form, getdate, nowdate, today



@frappe.whitelist()
def get_required_fat_snf(production_item, quantity):  
    reqd_fat = frappe.get_doc("Item",{'name' : production_item})
    
    if reqd_fat.maintain_fat_snf_clr == 1:
        if reqd_fat.standard_fat > 0 or reqd_fat.standard_snf > 0 : 

            item_fat = (flt(quantity) * flt(reqd_fat.weight_per_unit)) * (flt(reqd_fat.standard_fat) / 100)
            item_snf = (flt(quantity) * flt(reqd_fat.weight_per_unit)) * (flt(reqd_fat.standard_snf) / 100)
        

            return [reqd_fat.standard_fat, reqd_fat.standard_snf, item_fat, item_snf]


def bom_item_child_table(self, method):
    fat=[]
    snf=[]
    date=""
    if self.actual_start_date:
        date=getdate(self.actual_start_date)
    else:
        date=getdate(self.planned_start_date)
    item=remove_fat_item(self.company,self.source_warehouse,date,self.required_items)
    for i in item:
        for j in self.required_items:
            if i.get("item")==j.item_code:
                j.fat_per=i.get("fatper")
                j.snf_per=i.get("snfper")
                j.fat_per_in_kg=(i.get("fatper")/100)*j.required_qty
                j.snf_in_kg=(i.get("snfper")/100)*j.required_qty
    for j in self.required_items:
        fat.append(flt(j.fat_per_in_kg))
        snf.append(flt(j.snf_in_kg))
    if len(fat)>=1:
        self.rm_fat_in_kg=sum(fat)
        self.diff_fat_in_kg=self.required_fat_in_kg-sum(fat)

    if len(snf)>=1:
        self.rm_snf_in_kg=sum(snf)
        self.diff_snf_in_kg=self.required_snt_in_kg-sum(snf)

    ds=frappe.get_doc("Dairy Settings")
    if self.required_fat>0:
        if abs(self.diff_fat_in_kg)>ds.threshold_for_fat_separation:
            item=frappe.get_doc("Item",self.production_item)
            if item.weight_per_unit>0:
                self.sepration_fat=(abs(self.diff_fat_in_kg)*100)/(self.required_fat*item.weight_per_unit)
            else:
                frappe.throw("Production Item Weight Should More Than 0")
   
    # result = {}
    # for d in self.required_items:
    #     if d["item_code"] in result:
    #         result[d["item_code"]] += d["required_qty"]
    #     else:
    #         result[d["item_code"]] = d["required_qty"]

    # for k, v in result.items():
    #     {"item": k, "qty": v}


        



def get_required_fat_snf_item(self, method):  
    reqd_fat = frappe.get_doc("Item",{'name' : self.production_item})
    
    if reqd_fat.maintain_fat_snf_clr == 1:
        if reqd_fat.standard_fat > 0 or reqd_fat.standard_snf > 0 : 
            self.required_fat=reqd_fat.standard_fat
            self.required_snf_=reqd_fat.standard_snf
            self.required_fat_in_kg = (flt(self.qty) * flt(reqd_fat.weight_per_unit)) * (flt(reqd_fat.standard_fat) / 100)
            self.required_snt_in_kg = (flt(self.qty) * flt(reqd_fat.weight_per_unit)) * (flt(reqd_fat.standard_snf) / 100)


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
            # stock_value += sle.stock_value_difference

            if sle.voucher_type == 'Stock Reconciliation' and not sle.actual_qty:
                actual_qty = sle.qty_after_transaction
                # stock_value = sle.stock_value

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
        # print('data*************************8',sle)

        if include_uom:
            conversion_factors.append(item_detail.conversion_factor)

    update_included_uom_in_report(columns, data, include_uom, conversion_factors)
    return data



@frappe.whitelist()
def get_data_fat(name):
    doc=frappe.get_doc("Dairy Settings")
    wo=frappe.get_doc("Work Order",name)
    items_to_add_fat=frappe.db.sql("Select item from `tabfatsnf table` where parent='Dairy Settings' order by priority1 asc ",as_dict=1)
    date=""
    if wo.actual_start_date:
        date=getdate( wo.actual_start_date)
    else:
        date=getdate( wo.planned_start_date)
    list=[]
    if wo.diff_fat_in_kg >0:
        list=add_fat_item(abs(wo.diff_fat_in_kg),wo.company,wo.source_warehouse,date,items_to_add_fat)
        for k in list:
            if len(wo.fg_item_scrap)==0:
                    wo.append("fg_item_scrap",{
                        "item":wo.production_item,
                        "qty":k.get("pickedqty")
                    })
            else:
                for j in wo.fg_item_scrap:
                    j.qty=flt(j.qty)+k.get("pickedqty")
        return list
    else:
        if abs(wo.diff_fat_in_kg)>0:
            if doc.threshold_for_fat_separation<abs(wo.diff_fat_in_kg):
                list.append({"operation":doc.operation,"workstation":doc.workstation,"workstation_type":doc.workstation_type,
                            "completed_qty":wo.separation_fat,"time_in_mins":doc.operation_time,"bom":wo.bom_no,"threshhold":1})
                return list
            elif doc.threshold_for_fat_separation>abs(wo.diff_fat_in_kg):
                rmfatkg=[]
                rm_weight=[]
                for j in wo.required_items:
                    rmfatkg.append(j.fat_per_in_kg)
                    item=frappe.get_doc("Item",j.item_code)
                    rm_weight.append(j.required_qty*item.weight_per_unit)
                rmweight=(sum(rmfatkg)*100)/4
                water=rmweight-sum(rm_weight)+wo.process_loss_qty
                list.append({"item":doc.item_to_add_snf_fat,"warehouse":wo.source_warehouse,"pickedqty":abs(water),"threshhold":0})
                if len(wo.fg_item_scrap)==0:
                    wo.append("fg_item_scrap",{
                        "item":wo.production_item,
                        "qty":abs(water)

                    })
                else:
                    for j in wo.fg_item_scrap:
                        j.qty=flt(j.qty)+abs(water)
                return list


@frappe.whitelist()
def get_data_snf(name):
    doc=frappe.get_doc("Dairy Settings")
    wo=frappe.get_doc("Work Order",name)
    items_to_add_snf=frappe.db.sql("Select item from `tabAdd Snf Table` where parent='Dairy Settings' order by priority1 asc ",as_dict=1)
    date=""
    if wo.actual_start_date:
        date=getdate( wo.actual_start_date)
    else:
        date=getdate( wo.planned_start_date)
    list=[]
    jlist=[]
    if wo.diff_snf_in_kg >0:
        list=add_snf_item(abs(wo.diff_snf_in_kg),wo.company,wo.source_warehouse,date,items_to_add_snf)
        for i in list:
            jlist.append(i)
        for i in list:
            for k in doc.items_to_add_snf:
                if k.part_of_water>0:
                    if i.get("item")==k.item:
                        j={"item":k.water_item,"pickedqty":flt(i.get("pickedqty"))*flt(k.part_of_water),"warehouse":i.get("warehouse")}
                        jlist.append(j)
        for k in jlist:
            if len(wo.fg_item_scrap)==0:
                    wo.append("fg_item_scrap",{
                        "item":wo.production_item,
                        "qty":k.get("pickedqty")
                    })
            else:
                for j in wo.fg_item_scrap:
                    j.qty=flt(j.qty)+k.get("pickedqty")
        return jlist
    else:
        if wo.diff_snf_in_kg<0:
            rmsnfkg=[]
            rm_weight=[]
            for j in wo.required_items:
                rmsnfkg.append(j.snf_in_kg)
                item=frappe.get_doc("Item",j.item_code)
                rm_weight.append(j.required_qty*item.weight_per_unit)
            rmweight=(sum(rmsnfkg)*100)/wo.required_fat
            water=rmweight-sum(rm_weight)+wo.process_loss_qty
            # wo.db_set("qty",flt(wo.qty)+flt(water))
            list.append({"item":doc.item_to_add_snf_fat,"warehouse":wo.source_warehouse,"pickedqty":abs(water),"threshhold":0})
            if len(wo.fg_item_scrap)==0:
                wo.append("fg_item_scrap",{
                    "item":wo.production_item,
                    "qty":abs(water)

                })
            else:
                for j in wo.fg_item_scrap:
                    j.qty=flt(j.qty)+abs(water)
            return list

    


@frappe.whitelist()
def add_fat_item(required_fat_kg,company,warehouse,date,itemlist):
   
    list=[]
    filters={}
    remaningfatinkg=required_fat_kg
    for i in itemlist:
        item=frappe.get_doc("Item",i.item)
        filters.update({'warehouse':warehouse,"from_date":date,"to_date":date,"company":company,"item_code":item.name})
        filters=frappe._dict(filters)
        td=exec(filters)
        if td:
            if len(td)>1:
                td=td[-1]
                if td.get("qty_after_transaction")>0 and td.get("fat_after_transaction")>=remaningfatinkg:
                    fatper=(td.get("fat_after_transaction")/td.get("qty_after_transaction"))*100
                    pickedwt=(td.get("qty_after_transaction")/td.get("fat_after_transaction"))*remaningfatinkg
                    picked_fat_in_kg=pickedwt*(fatper/100)
                    pickedqty=pickedwt/item.weight_per_unit
                    remaningfatinkg=0
                    list.append({"item":item.name,"warehouse":warehouse,"company":company,"remaining_fat_in_kg":remaningfatinkg,"fatper":fatper,"pickedwt":pickedwt,"picked_fat_in_kg":picked_fat_in_kg,"pickedqty":pickedqty,"threshhold":0})
                    break
                else:
                    if td.get("qty_after_transaction")>0 and td.get("fat_after_transaction")>0:
                        remaningfatinkg=remaningfatinkg-td.get("fat_after_transaction")
                        fatper=(td.get("fat_after_transaction")/td.get("qty_after_transaction"))*100
                        pickedwt=td.get("qty_after_transaction")
                        picked_fat_in_kg=pickedwt*(fatper/100)
                        pickedqty=td.get("balance_qty")
                        list.append({"item":item.name,"warehouse":warehouse,"company":company,"remaining_fat_in_kg":remaningfatinkg,"fatper":fatper,"pickedwt":pickedwt,"picked_fat_in_kg":picked_fat_in_kg,"pickedqty":pickedqty,"threshhold":0})

            
            else:
                td=td[0]
                if td.get("qty_after_transaction")>0 and td.get("fat_after_transaction")>remaningfatinkg:
                    fatper=(td.get("fat_after_transaction")/td.get("qty_after_transaction"))*100
                    pickedwt=(td.get("qty_after_transaction")/td.get("fat_after_transaction"))*remaningfatinkg
                    picked_fat_in_kg=pickedwt*(fatper/100)
                    pickedqty=pickedwt/item.weight_per_unit
                    remaningfatinkg=0
                    list.append({"item":item.name,"warehouse":warehouse,"company":company,"remaining_fat_in_kg":remaningfatinkg,"fatper":fatper,"pickedwt":pickedwt,"picked_fat_in_kg":picked_fat_in_kg,"pickedqty":pickedqty,"threshhold":0})
                    break
                else:
                    if td.get("qty_after_transaction")>0 and td.get("fat_after_transaction")>0:
                        remaningfatinkg=remaningfatinkg-td.get("fat_after_transaction")
                        fatper=td.get("fat_after_transaction")/td.get("qty_after_transaction")*100
                        pickedwt=td.get("qty_after_transaction")
                        picked_fat_in_kg=pickedwt*(fatper/100)
                        pickedqty=td.get("balance_qty")
                        list.append({"item":item.name,"warehouse":warehouse,"company":company,"remaining_fat_in_kg":remaningfatinkg,"fatper":fatper,"pickedwt":pickedwt,"picked_fat_in_kg":picked_fat_in_kg,"pickedqty":pickedqty,"threshhold":0})
        if remaningfatinkg<=0:
            break
    if len(list)==0:
        frappe.throw("Item Not Available")

    return list

@frappe.whitelist()
def add_snf_item(required_snf_kg,company,warehouse,date,itemlist):
   
    list=[]
    filters={}
    remaningsnfinkg=required_snf_kg
    for i in itemlist:
        item=frappe.get_doc("Item",i.item)
        filters.update({'warehouse':warehouse,"from_date":date,"to_date":date,"company":company,"item_code":item.name})
        filters=frappe._dict(filters)
        td=exec(filters)
        if td:
            if len(td)>1:
                td=td[-1]
                if td.get("qty_after_transaction")>0 and td.get("snf_after_transaction")>=remaningsnfinkg:
                    snfper=(td.get("snf_after_transaction")/td.get("qty_after_transaction"))*100
                    pickedwt=(td.get("qty_after_transaction")/td.get("snf_after_transaction"))*remaningsnfinkg
                    picked_snf_in_kg=pickedwt*(snfper/100)
                    pickedqty=pickedwt/item.weight_per_unit
                    remaningsnfinkg=0
                    list.append({"item":item.name,"warehouse":warehouse,"company":company,"remaining_snf_in_kg":remaningsnfinkg,"snfper":snfper,"pickedwt":pickedwt,"picked_snf_in_kg":picked_snf_in_kg,"pickedqty":pickedqty,"threshhold":0})
                    break
                else:
                    if td.get("qty_after_transaction")>0 and td.get("snf_after_transaction")>0:
                        remaningsnfinkg=remaningsnfinkg-td.get("snf_after_transaction")
                        snfper=(td.get("snf_after_transaction")/td.get("qty_after_transaction"))*100
                        pickedwt=td.get("qty_after_transaction")
                        picked_snf_in_kg=pickedwt*(snfper/100)
                        pickedqty=td.get("balance_qty")
                        list.append({"item":item.name,"warehouse":warehouse,"company":company,"remaining_snf_in_kg":remaningsnfinkg,"snfper":snfper,"pickedwt":pickedwt,"picked_snf_in_kg":picked_snf_in_kg,"pickedqty":pickedqty,"threshhold":0})

            
            else:
                td=td[0]
                if td.get("qty_after_transaction")>0 and td.get("snf_after_transaction")>remaningsnfinkg:
                    snfper=(td.get("snf_after_transaction")/td.get("qty_after_transaction"))*100
                    pickedwt=(td.get("qty_after_transaction")/td.get("snf_after_transaction"))*remaningsnfinkg
                    picked_snf_in_kg=pickedwt*(snfper/100)
                    pickedqty=pickedwt/item.weight_per_unit
                    remaningsnfinkg=0
                    list.append({"item":item.name,"warehouse":warehouse,"company":company,"remaining_snf_in_kg":remaningsnfinkg,"snfper":snfper,"pickedwt":pickedwt,"picked_snf_in_kg":picked_snf_in_kg,"pickedqty":pickedqty,"threshhold":0})
                    break
                else:
                    if td.get("qty_after_transaction")>0 and td.get("snf_after_transaction")>0:
                        remaningsnfinkg=remaningsnfinkg-td.get("snf_after_transaction")
                        snfper=td.get("snf_after_transaction")/td.get("qty_after_transaction")*100
                        pickedwt=td.get("qty_after_transaction")
                        picked_snf_in_kg=pickedwt*(snfper/100)
                        pickedqty=td.get("balance_qty")
                        list.append({"item":item.name,"warehouse":warehouse,"company":company,"remaining_snf_in_kg":remaningsnfinkg,"snfper":snfper,"pickedwt":pickedwt,"picked_snf_in_kg":picked_snf_in_kg,"pickedqty":pickedqty,"threshhold":0})
        if remaningsnfinkg<=0:
            break
    if len(list)==0:
        frappe.throw("Item Not Available")

    return list



@frappe.whitelist()
def remove_fat_item(company,warehouse,date,itemlist):
    list=[]
    filters={}
    for i in itemlist:
        item=frappe.get_doc("Item",i.item_code)
        filters.update({'warehouse':warehouse,"from_date":date,"to_date":date,"company":company,"item_code":item.name})
        filters=frappe._dict(filters)
        td=exec(filters)
        if td:
            if len(td)>1:
                td=td[-1]
                if td.get("qty_after_transaction")>0:
                    fat_per=(td.get("fat_after_transaction")/td.get("qty_after_transaction"))*100
                    snf_per=(td.get("snf_after_transaction")/td.get("qty_after_transaction"))*100
                    list.append({"item":item.name,"fatper":fat_per,"snfper":snf_per})
            else:
                td=td[0]
                if td.get("qty_after_transaction")>0:
                    fat_per=(td.get("fat_after_transaction")/td.get("qty_after_transaction"))*100
                    snf_per=(td.get("snf_after_transaction")/td.get("qty_after_transaction"))*100
                    list.append({"item":item.name,"fatper":fat_per,"snfper":snf_per})
    

    return list

class CustomWorkOrder(WorkOrder):
    def validate(self):
        self.validate_production_item()
        if self.bom_no:
            validate_bom_no(self.production_item, self.bom_no)

        self.validate_sales_order()
        # self.set_default_warehouse()
        self.validate_warehouse_belongs_to_company()
        self.calculate_operating_cost()
        self.validate_qty()
        self.validate_transfer_against()
        self.validate_operation_time()
        self.status = self.get_status()
        self.validate_workstation_type()

        validate_uom_is_integer(self, "stock_uom", ["qty", "produced_qty"])

        # self.set_required_items(reset_only_qty=len(self.get("required_items")))
        if self.source_warehouse:
            if self.required_fat>0:
                for i in self.required_items:
                    i.source_warehouse=self.source_warehouse

    def prepare_data_for_job_card(self, row, index, plan_days, enable_capacity_planning):
        self.set_operation_start_end_time(index, row)

        original_start_time = row.planned_start_time
        job_card_doc = make_job_card(
            self, row, auto_create=True, enable_capacity_planning=enable_capacity_planning
        )

        if enable_capacity_planning and job_card_doc:
            row.planned_start_time = job_card_doc.time_logs[-1].from_time
            row.planned_end_time = job_card_doc.time_logs[-1].to_time

            if date_diff(row.planned_start_time, original_start_time) > plan_days:
                frappe.message_log.pop()
                frappe.throw(
                    frappe._("Unable to find the time slot in the next {0} days for the operation {1}.").format(
                        plan_days, row.operation
                    ),
                    CapacityError,
                )

            row.db_update()


def make_job_card(work_order, row, enable_capacity_planning=False, auto_create=False):
    ds=frappe.get_doc("Dairy Settings")

    if abs(work_order.diff_fat_in_kg)>ds.threshold_for_fat_separation: 
        doc = frappe.new_doc("Job Card")
        doc.update(
            {
                "work_order": work_order.name,
                "workstation_type": row.get("workstation_type"),
                "operation": row.get("operation"),
                "workstation": row.get("workstation"),
                "posting_date": nowdate(),
                "for_quantity": row.job_card_qty or work_order.get("qty", 0),
                "operation_id": row.get("name"),
                "bom_no": work_order.bom_no,
                "project": work_order.project,
                "company": work_order.company,
                "sequence_id": row.get("sequence_id"),
                "wip_warehouse": work_order.wip_warehouse,
                "hour_rate": row.get("hour_rate"),
                "serial_no": row.get("serial_no"),
            }
        )
        item=frappe.get_doc("Item",work_order.production_item)
        qty=(abs(work_order.diff_fat_in_kg)*100)/(4*item.weight_per_unit)
        if ds.cream_item:
            item=frappe.get_doc("Item",ds.cream_item)
            doc.append("scrap_items",{
                "item_code":ds.cream_item,
                "item_name":item.item_name,
                "stock_qty":qty
            })
        if work_order.transfer_material_against == "Job Card" and not work_order.skip_transfer:
            doc.get_required_items()

        if auto_create:
            doc.flags.ignore_mandatory = True
            if enable_capacity_planning:
                doc.schedule_time_logs(row)

            doc.insert()
            frappe.msgprint(
                frappe._("Job card {0} created").format(get_link_to_form("Job Card", doc.name)), alert=True
            )

        if enable_capacity_planning:
            # automatically added scheduling rows shouldn't change status to WIP
            doc.db_set("status", "Open")

        return doc
    else:
        doc = frappe.new_doc("Job Card")
        doc.update(
            {
                "work_order": work_order.name,
                "workstation_type": row.get("workstation_type"),
                "operation": row.get("operation"),
                "workstation": row.get("workstation"),
                "posting_date": nowdate(),
                "for_quantity": row.job_card_qty or work_order.get("qty", 0),
                "operation_id": row.get("name"),
                "bom_no": work_order.bom_no,
                "project": work_order.project,
                "company": work_order.company,
                "sequence_id": row.get("sequence_id"),
                "wip_warehouse": work_order.wip_warehouse,
                "hour_rate": row.get("hour_rate"),
                "serial_no": row.get("serial_no"),
            }
        )
        qty=abs(work_order.diff_fat_in_kg)*100/work_order.required_fat
        if ds.cream_item:
            item=frappe.get_doc("Item",ds.cream_item)
            doc.append("scrap_items",{
                "item_code":ds.cream_item,
                "item_name":item.item_name,
                "stock_qty":qty
            })
        if work_order.transfer_material_against == "Job Card" and not work_order.skip_transfer:
            doc.get_required_items()

        if auto_create:
            doc.flags.ignore_mandatory = True
            if enable_capacity_planning:
                doc.schedule_time_logs(row)

            doc.insert()
            frappe.msgprint(
                frappe._("Job card {0} created").format(get_link_to_form("Job Card", doc.name)), alert=True
            )

        if enable_capacity_planning:
            # automatically added scheduling rows shouldn't change status to WIP
            doc.db_set("status", "Open")

        return doc