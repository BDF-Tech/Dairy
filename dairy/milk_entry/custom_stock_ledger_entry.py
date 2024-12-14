import frappe
from datetime import datetime
from frappe.utils import cint, flt

@frappe.whitelist()
def create_milk_ledger_entry(self, method):
        
    if self.is_cancelled == 1:
        doc=frappe.db.get_all("Milk Ledger Entry",{"name":self.voucher_no,"is_cancelled":0},["name"])
        for i in doc:
            can = frappe.get_doc("Milk Ledger Entry",i.name)
            can.is_cancelled = 1
            can.save(ignore_permissions=True)

    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")
    
    itm = frappe.get_doc("Item", self.item_code)    
# ----------------------------------------------------------------------------------------------------------------------------

    if itm.maintain_fat_snf_clr == 1:
        if self.voucher_type == "Sales Invoice":
            lst = frappe.db.get_list("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse})
            if lst:
                fat = frappe.db.get_value("Milk Ledger Entry", lst[0], ["fat_after_transaction"])
                snf = frappe.db.get_value("Milk Ledger Entry", lst[0], ["snf_after_transaction"])
            else:
                fat = 0.0
                snf = 0.0
            if frappe.db.get_value("Sales Invoice", {"name":self.voucher_no},["name"]):
                doc = frappe.get_doc("Sales Invoice", {"name":self.voucher_no})
    
                for itm in doc.items:
                    if itm.name == self.voucher_detail_no and itm.item_code == self.item_code:
                        si_item = itm.item_code
            
                if si_item == self.item_code:
                    item = frappe.db.get_all("Sales Invoice Item", {"parent": self.voucher_no, "item_code":self.item_code}, ["*"])


                    for i in item:

                        # fat and snf for after transaction fields
                        if self.actual_qty >= 0:
                            fat_after_transaction = round(fat + i.fat, 3)
                            snf_after_transaction = round(snf + i.snf, 3)

                        if self.actual_qty <= 0:
                            fat_after_transaction = round(fat - i.fat, 3)
                            snf_after_transaction = round(snf - i.snf, 3)

                        milk_le = frappe.db.get_value("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse, "voucher_no": self.voucher_no, "batch_no":self.batch_no}, ["name"])                  
                        if milk_le:
                            mle = frappe.get_doc("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse, "voucher_no": self.voucher_no, "batch_no":self.batch_no}) 

                            mle.update(
                                {
                                    "batch_no" : i.batch_no,
                                    "posting_date" : today,
                                    "posting_time" : current_time,
                                    "actual_qty" : self.actual_qty,
                                    "fat" : i.fat,
                                    "fat_per" : i.fat_per,
                                    "snf" : i.snf,
                                    "snf_per" : i.snf_per,
                                    "stock_uom" : self.stock_uom,
                                    "qty_after_transaction" : self.qty_after_transaction,
                                    "fat_after_transaction" : fat_after_transaction,
                                    "snf_after_transaction" : snf_after_transaction
                                }
                            )
                            mle.save(ignore_permissions=True)

                        else:
                            milk_ledger = frappe.new_doc("Milk Ledger Entry")
                            milk_ledger.item_code = i.item_code
                            milk_ledger.batch_no = i.batch_no
                            milk_ledger.warehouse = i.warehouse
                            milk_ledger.posting_date = today
                            milk_ledger.posting_time = current_time
                            milk_ledger.voucher_type = self.voucher_type
                            milk_ledger.voucher_no = self.voucher_no
                            milk_ledger.voucher_detail_no = self.voucher_detail_no
                            milk_ledger.actual_qty = self.actual_qty
                            milk_ledger.fat = i.fat
                            milk_ledger.fat_per = i.fat_per
                            milk_ledger.snf = i.snf
                            milk_ledger.snf_per = i.snf_per
                            milk_ledger.stock_uom = self.stock_uom
                            milk_ledger.qty_after_transaction = self.qty_after_transaction
                            milk_ledger.fat_after_transaction = fat_after_transaction
                            milk_ledger.snf_after_transaction = snf_after_transaction
                            milk_ledger.company = self.company
                            milk_ledger.insert(ignore_permissions=True)

# ----------------------------------------------------------------------------------------------------------------------------
        
        if self.voucher_type == "Purchase Invoice":
            lst = frappe.db.get_list("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse})
            if lst:
                fat = frappe.db.get_value("Milk Ledger Entry", lst[0], ["fat_after_transaction"])
                snf = frappe.db.get_value("Milk Ledger Entry", lst[0], ["snf_after_transaction"])
            else:
                fat = 0.0
                snf = 0.0
            if frappe.db.get_value("Purchase Invoice", {"name":self.voucher_no},["name"]):
                doc = frappe.get_doc("Purchase Invoice", {"name":self.voucher_no})
        
                for itm in doc.items:
                    if itm.name == self.voucher_detail_no and itm.item_code == self.item_code:
                        si_item = itm.item_code
            
                if si_item == self.item_code:
                    item = frappe.db.get_all("Purchase Invoice Item", {"parent": self.voucher_no, "item_code":self.item_code}, ["*"])
                    for i in item:

                        # fat and snf for after transaction fields
                        if self.actual_qty >= 0:
                            fat_after_transaction = round(fat + i.fat, 3)
                            snf_after_transaction = round(snf + i.snf, 3)

                        if self.actual_qty <= 0:
                            fat_after_transaction = round(fat - i.fat, 3)
                            snf_after_transaction = round(snf - i.snf, 3)

                        milk_le = frappe.db.get_value("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse, "voucher_no": self.voucher_no, "batch_no":self.batch_no}, ["name"])  
                        if milk_le:
                            mle = frappe.get_doc("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse, "voucher_no": self.voucher_no, "batch_no":self.batch_no})

                            mle.update(
                                {
                                    "batch_no" : i.batch_no,
                                    "posting_date" : today,
                                    "posting_time" : current_time,
                                    "actual_qty" : self.actual_qty,
                                    "fat" : i.fat,
                                    "fat_per" : i.fat_per,
                                    "snf" : i.snf,
                                    "snf_per" : i.snf_per,
                                    "stock_uom" : self.stock_uom,
                                    "qty_after_transaction" : self.qty_after_transaction,
                                    "fat_after_transaction" : fat_after_transaction,
                                    "snf_after_transaction" : snf_after_transaction
                                }
                            )
                            mle.save(ignore_permissions=True)

                        else:
                            milk_ledger = frappe.new_doc("Milk Ledger Entry")
                            milk_ledger.item_code = i.item_code
                            milk_ledger.batch_no = i.batch_no
                            milk_ledger.warehouse = self.warehouse
                            milk_ledger.posting_date = today
                            milk_ledger.posting_time = current_time
                            milk_ledger.voucher_type = self.voucher_type
                            milk_ledger.voucher_no = self.voucher_no
                            milk_ledger.voucher_detail_no = self.voucher_detail_no
                            milk_ledger.actual_qty = self.actual_qty
                            milk_ledger.fat = i.fat
                            milk_ledger.fat_per = i.fat_per
                            milk_ledger.snf = i.snf
                            milk_ledger.snf_per = i.snf_per
                            milk_ledger.stock_uom = self.stock_uom
                            milk_ledger.qty_after_transaction = self.qty_after_transaction
                            milk_ledger.fat_after_transaction = fat_after_transaction
                            milk_ledger.snf_after_transaction = snf_after_transaction
                            milk_ledger.company = self.company
                            milk_ledger.insert(ignore_permissions=True)

# -------------------------------------------------------------------------------------------------------------------------------

        if self.voucher_type == "Stock Reconciliation":
            lst = frappe.db.get_list("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse})
            if lst:
                fat = frappe.db.get_value("Milk Ledger Entry", lst[0], ["fat_after_transaction"])
                snf = frappe.db.get_value("Milk Ledger Entry", lst[0], ["snf_after_transaction"])
            else:
                fat = 0.0
                snf = 0.0
            if frappe.db.get_value("Stock Reconciliation", {"name":self.voucher_no},["name"]):
                doc = frappe.get_doc("Stock Reconciliation", {"name":self.voucher_no})
        
                for itm in doc.items:
                    if itm.name == self.voucher_detail_no and itm.item_code == self.item_code:
                        si_item = itm.item_code
            
                if si_item == self.item_code:
                    item = frappe.db.get_all("Stock Reconciliation Item", {"parent": self.voucher_no, "item_code":self.item_code}, ["*"])
                    for i in item:

                        # fat and snf for after transaction fields
                        if self.actual_qty >= 0:
                            fat_after_transaction = round(fat + i.fat, 3)
                            snf_after_transaction = round(snf + i.snf, 3)

                        if self.actual_qty <= 0:
                            fat_after_transaction = round(fat - i.fat, 3)
                            snf_after_transaction = round(snf - i.snf, 3)

                        milk_le = frappe.db.get_value("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse, "voucher_no": self.voucher_no, "batch_no":self.batch_no}, ["name"])  
                        if milk_le:
                            mle = frappe.get_doc("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse, "voucher_no": self.voucher_no, "batch_no":self.batch_no})

                            mle.update(
                                {
                                    "batch_no" : i.batch_no,
                                    "posting_date" : today,
                                    "posting_time" : current_time,
                                    "actual_qty" : self.actual_qty,
                                    "fat" : i.fat,
                                    "fat_per" : i.fat_per,
                                    "snf" : i.snf,
                                    "snf_per" : i.snf_per,
                                    "stock_uom" : self.stock_uom,
                                    "qty_after_transaction" : self.qty_after_transaction,
                                    "fat_after_transaction" : fat_after_transaction,
                                    "snf_after_transaction" : snf_after_transaction
                                }
                            )
                            mle.save(ignore_permissions=True)

                        else:
                            milk_ledger = frappe.new_doc("Milk Ledger Entry")
                            milk_ledger.item_code = i.item_code
                            milk_ledger.batch_no = i.batch_no
                            milk_ledger.warehouse = self.warehouse
                            milk_ledger.posting_date = today
                            milk_ledger.posting_time = current_time
                            milk_ledger.voucher_type = self.voucher_type
                            milk_ledger.voucher_no = self.voucher_no
                            milk_ledger.voucher_detail_no = self.voucher_detail_no
                            milk_ledger.actual_qty = self.actual_qty
                            milk_ledger.fat = i.fat
                            milk_ledger.fat_per = i.fat_per
                            milk_ledger.snf = i.snf
                            milk_ledger.snf_per = i.snf_per
                            milk_ledger.stock_uom = self.stock_uom
                            milk_ledger.qty_after_transaction = self.qty_after_transaction
                            milk_ledger.fat_after_transaction = fat_after_transaction
                            milk_ledger.snf_after_transaction = snf_after_transaction
                            milk_ledger.company = self.company
                            milk_ledger.insert(ignore_permissions=True)

# -------------------------------------------------------------------------------------------------------------------------------

        if self.voucher_type == "Stock Entry":
            lst = frappe.db.get_list("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse})
            if lst:
                fat = frappe.db.get_value("Milk Ledger Entry", lst[0], ["fat_after_transaction"])
                snf = frappe.db.get_value("Milk Ledger Entry", lst[0], ["snf_after_transaction"])
            else:
                fat = 0.0
                snf = 0.0
            if frappe.db.get_value("Stock Entry", {"name":self.voucher_no},["name"]):
                doc = frappe.get_doc("Stock Entry", {"name":self.voucher_no})
    
            for itm in doc.items:
                if itm.name == self.voucher_detail_no and itm.item_code == self.item_code:
                    si_item = itm.item_code
        
            if si_item == self.item_code:
                item = frappe.db.get_all("Stock Entry Detail", {"parent": self.voucher_no, "item_code":self.item_code}, ["*"])

                for i in item:

                    # fat and snf for after transaction fields
                    if self.actual_qty >= 0:
                        fat_after_transaction = round(fat + i.fat, 3)
                        snf_after_transaction = round(snf + i.snf, 3)

                    if self.actual_qty <= 0:
                        fat_after_transaction = round(fat - i.fat, 3)
                        snf_after_transaction = round(snf - i.snf, 3)

                    milk_le = frappe.db.get_value("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse, "voucher_no": self.voucher_no, "batch_no":self.batch_no}, ["name"])            
                    if milk_le:
                        mle = frappe.get_doc("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse, "voucher_no": self.voucher_no, "batch_no":self.batch_no})

                        mle.update(
                            {
                                "batch_no" : i.batch_no,
                                "posting_date" : today,
                                "posting_time" : current_time,
                                "actual_qty" : self.actual_qty,
                                "fat" : i.fat,
                                "fat_per" : i.fat_per,
                                "snf" : i.snf,
                                "snf_per" : i.snf_per,
                                "stock_uom" : self.stock_uom,
                                "qty_after_transaction" : self.qty_after_transaction,
                                "fat_after_transaction" : fat_after_transaction,
                                "snf_after_transaction" : snf_after_transaction
                            }
                        )
                        mle.save(ignore_permissions=True)

                    else:
                        milk_ledger = frappe.new_doc("Milk Ledger Entry")
                        milk_ledger.item_code = i.item_code
                        milk_ledger.batch_no = i.batch_no
                        milk_ledger.warehouse = self.warehouse
                        milk_ledger.posting_date = today
                        milk_ledger.posting_time = current_time
                        milk_ledger.voucher_type = self.voucher_type
                        milk_ledger.voucher_no = self.voucher_no
                        milk_ledger.voucher_detail_no = self.voucher_detail_no
                        milk_ledger.actual_qty = self.actual_qty
                        milk_ledger.fat = i.fat
                        milk_ledger.fat_per = i.fat_per
                        milk_ledger.snf = i.snf
                        milk_ledger.snf_per = i.snf_per
                        milk_ledger.stock_uom = self.stock_uom
                        milk_ledger.qty_after_transaction = self.qty_after_transaction
                        milk_ledger.fat_after_transaction = fat_after_transaction
                        milk_ledger.snf_after_transaction = snf_after_transaction
                        milk_ledger.company = self.company
                        milk_ledger.insert(ignore_permissions=True)

# -------------------------------------------------------------------------------------------------------------------------------

        if self.voucher_type == "Purchase Receipt":
            lst = frappe.db.get_list("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse})
            if lst:
                fat = frappe.db.get_value("Milk Ledger Entry", lst[0], ["fat_after_transaction"])
                snf = frappe.db.get_value("Milk Ledger Entry", lst[0], ["snf_after_transaction"])
            else:
                fat = 0.0
                snf = 0.0
            if frappe.db.get_value("Purchase Receipt", {"name":self.voucher_no},["name"]):
                doc = frappe.get_doc("Purchase Receipt", {"name":self.voucher_no})
                
                for itm in doc.items:
                    if itm.name == self.voucher_detail_no and itm.item_code == self.item_code:
                        si_item = itm.item_code
            
                if si_item == self.item_code:
                    item = frappe.db.get_all("Purchase Receipt Item", {"parent": self.voucher_no, "item_code":self.item_code, "warehouse": self.warehouse}, ["*"])


                    for i in item:

                        # fat and snf for after transaction fields
                        if self.actual_qty >= 0:
                            fat_after_transaction = round(fat + i.fat, 3)
                            snf_after_transaction = round(snf + i.clr, 3)

                        if self.actual_qty <= 0:
                            fat_after_transaction = round(fat - i.fat, 3)
                            snf_after_transaction = round(snf - i.clr, 3)

                        milk_le = frappe.db.get_value("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse, "voucher_no": self.voucher_no, "batch_no":self.batch_no}, ["name"])    
                        if milk_le:
                            mle = frappe.get_doc("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse, "voucher_no": self.voucher_no, "batch_no":self.batch_no})
                            
                            mle.update(
                                {
                                    "batch_no" : i.batch_no,
                                    "posting_date" : today,
                                    "posting_time" : current_time,
                                    "actual_qty" : self.actual_qty,
                                    "fat" : i.fat,
                                    "fat_per" : i.fat_per,
                                    "snf" : i.clr,
                                    "snf_per" : i.snf_clr_per,
                                    "stock_uom" : self.stock_uom,
                                    "qty_after_transaction" : self.qty_after_transaction,
                                    "fat_after_transaction" : fat_after_transaction,
                                    "snf_after_transaction" : snf_after_transaction
                                }
                            )
                            mle.save(ignore_permissions=True)

                        else:
                            milk_ledger = frappe.new_doc("Milk Ledger Entry")
                            milk_ledger.item_code = i.item_code
                            milk_ledger.batch_no = i.batch_no
                            milk_ledger.warehouse = self.warehouse
                            milk_ledger.posting_date = today
                            milk_ledger.posting_time = current_time
                            milk_ledger.voucher_type = self.voucher_type
                            milk_ledger.voucher_no = self.voucher_no
                            milk_ledger.voucher_detail_no = self.voucher_detail_no
                            milk_ledger.actual_qty = self.actual_qty
                            milk_ledger.fat = i.fat
                            milk_ledger.fat_per = i.fat_per_
                            milk_ledger.snf = i.clr
                            milk_ledger.snf_per = i.snf_clr_per
                            milk_ledger.stock_uom = self.stock_uom
                            milk_ledger.qty_after_transaction = self.qty_after_transaction
                            milk_ledger.fat_after_transaction = fat_after_transaction
                            milk_ledger.snf_after_transaction = snf_after_transaction
                            milk_ledger.company = self.company
                            milk_ledger.insert(ignore_permissions=True)

# -------------------------------------------------------------------------------------------------------------------------------

        if self.voucher_type == "Delivery Note":
            lst = frappe.db.get_list("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse})
            if lst:
                fat = frappe.db.get_value("Milk Ledger Entry", lst[0], ["fat_after_transaction"])
                snf = frappe.db.get_value("Milk Ledger Entry", lst[0], ["snf_after_transaction"])
            else:
                fat = 0.0
                snf = 0.0
            if frappe.db.get_value("Delivery Note", {"name":self.voucher_no},["name"]):
 
                doc = frappe.get_doc("Delivery Note", {"name":self.voucher_no})
        
                for itm in doc.items:
                    if itm.name == self.voucher_detail_no and itm.item_code == self.item_code:
                        si_item = itm.item_code
            
                if si_item == self.item_code:
                    item = frappe.db.get_all("Delivery Note Item", {"parent": self.voucher_no, "item_code":self.item_code, "warehouse": self.warehouse}, ["*"])
                    for i in item:

                        # fat and snf for after transaction fields
                        if self.actual_qty >= 0:
                            fat_after_transaction = round(fat + i.fat, 3)
                            snf_after_transaction = round(snf + i.snf, 3)

                        if self.actual_qty <= 0:
                            fat_after_transaction = round(fat - i.fat, 3)
                            snf_after_transaction = round(snf - i.snf, 3)

                        milk_le = frappe.db.get_value("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse, "voucher_no": self.voucher_no, "batch_no":self.batch_no}, ["name"])                    
                        if milk_le:
                            mle = frappe.get_doc("Milk Ledger Entry", {"item_code":self.item_code, "warehouse": self.warehouse, "voucher_no": self.voucher_no, "batch_no":self.batch_no})

                            mle.update(
                                {
                                    "batch_no" : i.batch_no,
                                    "posting_date" : today,
                                    "posting_time" : current_time,
                                    "actual_qty" : self.actual_qty,
                                    "fat" : i.fat,
                                    "fat_per" : i.fat_per,
                                    "snf" : i.snf,
                                    "snf_per" : i.snf_per,
                                    "stock_uom" : self.stock_uom,
                                    "qty_after_transaction" : self.qty_after_transaction,
                                    "fat_after_transaction" : fat_after_transaction,
                                    "snf_after_transaction" : snf_after_transaction
                                }
                            )
                            mle.save(ignore_permissions=True)

                        else:
                            milk_ledger = frappe.new_doc("Milk Ledger Entry")
                            milk_ledger.item_code = i.item_code
                            milk_ledger.batch_no = i.batch_no
                            milk_ledger.warehouse = self.warehouse
                            milk_ledger.posting_date = today
                            milk_ledger.posting_time = current_time
                            milk_ledger.voucher_type = self.voucher_type
                            milk_ledger.voucher_no = self.voucher_no
                            milk_ledger.voucher_detail_no = self.voucher_detail_no
                            milk_ledger.actual_qty = self.actual_qty
                            milk_ledger.fat = i.fat
                            milk_ledger.fat_per = i.fat_per
                            milk_ledger.snf = i.clr
                            milk_ledger.snf_per = i.snf_clr_per
                            milk_ledger.stock_uom = self.stock_uom
                            milk_ledger.qty_after_transaction = self.qty_after_transaction
                            milk_ledger.fat_after_transaction = fat_after_transaction
                            milk_ledger.snf_after_transaction = snf_after_transaction
                            milk_ledger.company = self.company
                            milk_ledger.insert(ignore_permissions=True)

# -------------------------------------------------------------------------------------------------------------------------------