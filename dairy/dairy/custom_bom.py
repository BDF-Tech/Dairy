import frappe
from frappe.utils.data import flt


@frappe.whitelist()
def get_required_fat_snf(item_code, quantity):  
    reqd_fat = frappe.get_doc("Item",{'name' : item_code})
    
    if reqd_fat.maintain_fat_snf_clr == 1:
        if reqd_fat.standard_fat > 0 or reqd_fat.standard_snf > 0 : 
            print("==========================================")
            print("Document Fetched = ",reqd_fat)
            print("Quantity from BOM",quantity,reqd_fat.weight_per_unit)
            print("STD FAT from fetched",reqd_fat.standard_fat) 
            print("STD SNF from fetched",reqd_fat.standard_snf)

            #(Quantity* wt. on item) * (Standard Fat% / 100)

            item_fat = (flt(quantity) * flt(reqd_fat.weight_per_unit)) * (flt(reqd_fat.standard_fat) / 100)
            item_snf = (flt(quantity) * flt(reqd_fat.weight_per_unit)) * (flt(reqd_fat.standard_snf) / 100)
            print("ITEM FAT IN KG = ",item_fat)
            print("ITEM SNF IN KG = ",item_snf)
            print("==========================================")

            return [reqd_fat.standard_fat, reqd_fat.standard_snf, item_fat, item_snf]

        else:
            return ""
    else:
        return ""

@frappe.whitelist()
def bom_item_child_table(item_code, qty):
    if not qty:
        qty=1
    print("QTY ===============================",qty)
    reqd_fat = frappe.get_doc("Item",{'name' : item_code})
    if reqd_fat.maintain_fat_snf_clr == 1:
        if reqd_fat.standard_fat > 0 or reqd_fat.standard_snf > 0 : 

            weight = flt(reqd_fat.weight_per_unit) * flt(qty)
            BOM_fat = (flt(qty) * flt(reqd_fat.weight_per_unit)) * (flt(reqd_fat.standard_fat) / 100)
            BOM_snf = (flt(qty) * flt(reqd_fat.weight_per_unit)) * (flt(reqd_fat.standard_snf) / 100)


            print("ITEM CODE ON CHILD TABLE CODE =========",item_code)
            print("ITEM FAT ON TABLE = ",BOM_fat)
            print("ITEM SNF ON TABLE = ",BOM_snf)

            return [weight,reqd_fat.standard_fat, BOM_fat, reqd_fat.standard_snf, BOM_snf]



@frappe.whitelist()
def bom_item_child(item_code,qty=None):
    if not qty:
        qty=1
    print("QTY ===============================",qty)
    reqd_fat = frappe.get_doc("Item",{'name' : item_code})
    if reqd_fat.maintain_fat_snf_clr == 1:
        if reqd_fat.standard_fat > 0 or reqd_fat.standard_snf > 0 : 

            weight = flt(reqd_fat.weight_per_unit) * flt(qty)
            BOM_fat = (flt(qty) * flt(reqd_fat.weight_per_unit)) * (flt(reqd_fat.standard_fat) / 100)
            BOM_snf = (flt(qty) * flt(reqd_fat.weight_per_unit)) * (flt(reqd_fat.standard_snf) / 100)


            print("ITEM CODE ON CHILD TABLE CODE =========",item_code)
            print("ITEM FAT ON TABLE = ",BOM_fat)
            print("ITEM SNF ON TABLE = ",BOM_snf)
            return [weight,reqd_fat.standard_fat, BOM_fat, reqd_fat.standard_snf, BOM_snf]
        

def before_save(self,method):
    reqd_fat = frappe.get_doc("Item",{'name' : self.item})
    print("REQD FAT ON SAVE =============================",reqd_fat)
    total_fg_weight = self.quantity * reqd_fat.weight_per_unit

    total_rm_weight = [] 
    total_rm_fat = []
    total_rm_snf = []

    print("FG WEIGHT = -------",total_fg_weight)
    for item in self.items:
       
        total_rm_weight.append(item.weight)
        total_rm_fat.append(item.bom_fat)
        total_rm_snf.append(item.bom_snf)
    
    print("===============================",sum(total_rm_weight))
    print("===============================",sum(total_rm_fat))
    print("===============================",sum(total_rm_snf))

    self.set("fg_weight",total_fg_weight)
    self.set('total_rm_weight',sum(total_rm_weight))
    self.set('total_rm_fat',sum(total_rm_fat))
    self.set('total_rm_snf',sum(total_rm_snf))



    
# def before_submit(self,method):
#     if self.total_rm_fat!=self.item_fat or  self.total_rm_snf!=self.item_snf:
#         frappe.throw("Total RM Fat or Snf Not Equal To  Prouction Item Fat or snf")
