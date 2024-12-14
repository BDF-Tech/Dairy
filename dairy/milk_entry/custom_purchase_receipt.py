from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt,cint, cstr, getdate

def change_milk_entry_status(pc,method):
    if pc.milk_entry:
        doc = frappe.get_doc("Milk Entry",pc.milk_entry)
        res = frappe.db.sql(""" select docstatus from `tabRaw Milk Sample` where name in 
                                (Select distinct(parent) from `tabSample lines`  where milk_entry =%s) limit 1""",(doc.name))
        print('ressssssssssssssssssssssssssss',res)
        if res:
            if res[0][0] ==1 and doc.sample_created:
                doc.status = "To Post"
            elif res[0][0] ==0 and doc.sample_created:
                doc.status ="To Post and Sample"
            else:
                doc.status = "To Post and Sample"
        else:
            doc.status = "To Post and Sample"
        doc.db_update()

def change_milk_status(pc,method):
    if pc.milk_entry:
        doc = frappe.get_doc("Milk Entry",pc.milk_entry)
        res = frappe.db.sql("""select docstatus from `tabRaw Milk Sample` where name in 
                                (Select distinct(parent) from `tabSample lines`  where milk_entry =%s) limit 1""",(doc.name))
        if res:
            if res[0][0] ==1 and doc.sample_created:
                doc.status = "To Sample and Bill"
            elif res[0][0] == 1 and not doc.sample_created:
                doc.status = "To Bill"
            elif res[0][0] ==1:
                doc.status = "To Bill"
            else:
                doc.status ="To Sample"
        else:
            doc.status = "To Sample and Bill"
        doc.db_update()



def update_snf(pc,method):
    for itm in pc.items:
        query = """ select name from `tabStock Ledger Entry` where voucher_type = "Purchase Receipt"
                            and voucher_no = %(name)s and voucher_detail_no = %(c_name)s and is_cancelled != 1 """
        if itm.batch_no:
            query += """ and batch_no = %(batch_no)s """
        if itm.serial_no:
            query += """ and serial_no = %(serial_no)s """

        query += """ order by modified desc """
        sle = frappe.db.sql(query,{'name': pc.name,'c_name': itm.name,'batch_no':itm.batch_no, 'serial_no':itm.serial_no},as_dict=True)
        if sle[0]['name']:
            doc = frappe.get_doc("Stock Ledger Entry",sle[0]['name'])
            doc.actual_snf = itm.clr
            query2 = """ select actual_snf_after_transaction from `tabStock Ledger Entry` where voucher_type = "Purchase Receipt"
                                     and item_code = %(item_code)s and warehouse = %(warehouse)s and name != %(name)s
                                     """
            if itm.batch_no:
                query2 += """ and batch_no = %(batch_no)s """
            if itm.serial_no:
                query2 += """ and serial_no = %(serial_no)s """

            query2 += """ order by modified desc """
            f_slv = frappe.db.sql(query2,{'item_code': itm.item_code,"warehouse": itm.warehouse,'name':sle[0]['name'],'batch_no':itm.batch_no, 'serial_no':itm.serial_no}
                                  , as_dict=True)


            if f_slv:
                if float(f_slv[0]['actual_snf_after_transaction']) > 0.0:
                    doc.actual_snf_after_transaction = f_slv[0]['actual_snf_after_transaction'] + itm.clr
                else:
                    doc.actual_snf_after_transaction = itm.clr
            doc.save(ignore_permissions=True)


def update_fat(pc,method):
    for itm in pc.items:
        query = """ select name from `tabStock Ledger Entry` where voucher_type = "Purchase Receipt"
                                    and voucher_no = %(name)s and voucher_detail_no = %(c_name)s and is_cancelled != 1 """
        if itm.batch_no:
            query += """ and batch_no = %(batch_no)s """
        if itm.serial_no:
            query += """ and serial_no = %(serial_no)s """

        query += """ order by modified desc """
        sle = frappe.db.sql(query,
                            {'name': pc.name, 'c_name': itm.name, 'batch_no': itm.batch_no, 'serial_no': itm.serial_no},
                            as_dict=True)
        if sle[0]['name']:
            doc = frappe.get_doc("Stock Ledger Entry",sle[0]['name'])
            doc.actual_fat = itm.fat
            query2 = """ select actual_fat_after_transaction from `tabStock Ledger Entry` where voucher_type = "Purchase Receipt"
                                     and item_code = %(item_code)s and warehouse = %(warehouse)s and name != %(name)s
                                    """
            if itm.batch_no:
                query2 += """ and batch_no = %(batch_no)s """
            if itm.serial_no:
                query2 += """ and serial_no = %(serial_no)s """

            query2 += """ order by modified desc """
            f_slv = frappe.db.sql(query2,{'item_code': itm.item_code,"warehouse": itm.warehouse,'name':sle[0]['name'],
                                          'batch_no':itm.batch_no, 'serial_no':itm.serial_no}, as_dict=True)


            if f_slv:
                if float(f_slv[0]['actual_fat_after_transaction']) > 0.0:
                    doc.actual_fat_after_transaction = f_slv[0]['actual_fat_after_transaction'] + itm.fat
                else:
                    doc.actual_fat_after_transaction = itm.fat
            doc.save(ignore_permissions=True)

def cancel_update_snf(pc,method):
    for itm in pc.items:

        query = """ select name from `tabStock Ledger Entry` where voucher_type = "Purchase Receipt"
                            and voucher_no = %(name)s and voucher_detail_no = %(c_name)s and is_cancelled = 1 """
        if itm.batch_no:
            query += """ and batch_no = %(batch_no)s """
        if itm.serial_no:
            query += """ and serial_no = %(serial_no)s """

        query += """ order by modified desc """

        sle = frappe.db.sql(query,{'name': pc.name,'c_name': itm.name,'batch_no':itm.batch_no, 'serial_no':itm.serial_no},as_dict=True)


        if sle[1]['name']:
            doc = frappe.get_doc("Stock Ledger Entry",sle[1]['name'])
            new_actual_snf = 0 - float(doc.actual_snf)
            new_tran_snf = float(doc.actual_snf_after_transaction) - float(doc.actual_snf)

            query2 = """ select name from `tabStock Ledger Entry` where voucher_type = "Purchase Receipt"
                                         and voucher_no = %(name)s and voucher_detail_no = %(c_name)s and is_cancelled = 1
                                          """
            if itm.batch_no:
                query2 += """ and batch_no = %(batch_no)s """
            if itm.serial_no:
                query2 += """ and serial_no = %(serial_no)s """

            query2 += """ order by modified desc limit 1 """
            u_sle = frappe.db.sql(query2,{'name': pc.name, 'c_name': itm.name,'batch_no':itm.batch_no, 'serial_no':itm.serial_no}, as_dict=True)

            if u_sle:
                if u_sle[0]['name']:
                    u_doc = frappe.get_doc("Stock Ledger Entry", u_sle[0]['name'])
                    u_doc.actual_snf = new_actual_snf
                    u_doc.actual_snf_after_transaction = new_tran_snf
                    u_doc.save(ignore_permissions=True)

def cancel_update_fat(pc,method):
    for itm in pc.items:

        query = """ select name from `tabStock Ledger Entry` where voucher_type = "Purchase Receipt"
                  and voucher_no = %(name)s and voucher_detail_no = %(c_name)s and is_cancelled = 1 """
        if itm.batch_no:
            query += """ and batch_no = %(batch_no)s """
        if itm.serial_no:
            query += """ and serial_no = %(serial_no)s """

        query += """ order by modified desc"""
        sle = frappe.db.sql(query,{'name': pc.name,'c_name': itm.name,'batch_no':itm.batch_no, 'serial_no':itm.serial_no},as_dict=True)
        print("******************************************************",sle)
        if sle[1]['name']:
            doc = frappe.get_doc("Stock Ledger Entry",sle[1]['name'])
            new_actual_fat = 0 - float(doc.actual_fat)
            new_tran_fat = float(doc.actual_fat_after_transaction) - float(doc.actual_fat)

            query2 = """ select name from `tabStock Ledger Entry` where voucher_type = "Purchase Receipt"
                                         and voucher_no = %(name)s and voucher_detail_no = %(c_name)s and is_cancelled = 1
                                          """
            if itm.batch_no:
                query2 += """ and batch_no = %(batch_no)s """
            if itm.serial_no:
                query2 += """ and serial_no = %(serial_no)s """

            query2 += """ order by modified desc limit 1 """
            u_sle = frappe.db.sql(query2,{'name': pc.name, 'c_name': itm.name,'batch_no':itm.batch_no, 'serial_no':itm.serial_no}, as_dict=True)
            print("*****************************************u_sale*************", u_sle)
            if u_sle:
                if u_sle[0]['name']:
                    u_doc = frappe.get_doc("Stock Ledger Entry", u_sle[0]['name'])
                    u_doc.actual_fat = new_actual_fat
                    u_doc.actual_fat_after_transaction = new_tran_fat
                    u_doc.save(ignore_permissions=True)


# //*****************************************************************************
# def create_milk_stock_ledger(self,method):
#     for itm in self.items:
#         itm_obj = frappe.get_doc("Item",itm.item_code)
#         maintain_snf_fat = itm_obj.maintain_fat_snf_clr
#         good_cow_milk = frappe.db.get_single_value("Dairy Settings", "cow_pro")
#         good_buff_milk = frappe.db.get_single_value("Dairy Settings", "buf_pro")
#         good_mix_milk = frappe.db.get_single_value("Dairy Settings", "mix_pro")
#         if itm.item_code == good_cow_milk or itm.item_code == good_buff_milk or itm.item_code == good_mix_milk or maintain_snf_fat == 1:
#             print("************************************************************************snffatmaintain")
#             query = """ select count(*) from `tabMilk Ledger Entry` where item_code = %(item_code)s and warehouse = %(warehouse)s 
#                         """
#             if itm.batch_no:
#                 query += """ and batch_no = %(batch_no)s """
#             if itm.serial_no:
#                 query += """ and serial_no = %(serial_no)s """

#             query += """ order by modified desc"""

#             total_count = frappe.db.sql(query,{'warehouse':itm.warehouse,'item_code':itm.item_code,'batch_no':itm.batch_no,
#                                                'serial_no':itm.serial_no})

#             if total_count[0][0] == 0:
#                 pr_qty = flt(itm.qty) * flt(itm.conversion_factor)
#                 new_mle = frappe.new_doc("Milk Ledger Entry")
#                 new_mle.item_code = itm.item_code
#                 new_mle.serial_no = cstr(itm.serial_no).strip()
#                 new_mle.batch_no = itm.batch_no
#                 new_mle.warehouse = itm.warehouse
#                 new_mle.posting_date = self.posting_date
#                 new_mle.posting_time = self.posting_time
#                 new_mle.voucher_type = "Purchase Receipt"
#                 new_mle.voucher_no = self.name
#                 new_mle.voucher_detail_no = itm.name
#                 new_mle.actual_qty = itm.total_weight
#                 new_mle.fat = itm.fat
#                 new_mle.snf = itm.clr
#                 new_mle.stock_uom = itm.weight_uom
#                 new_mle.qty_after_transaction = itm.total_weight
#                 new_mle.fat_after_transaction = itm.fat
#                 new_mle.snf_after_transaction = itm.clr
#                 new_mle.fat_per = (itm.fat / itm.total_weight) * 100
#                 new_mle.snf_per = (itm.clr / itm.total_weight) * 100
#                 new_mle.save()
#                 # new_mle.submit()
#             else:
#                 query = """ select name from `tabMilk Ledger Entry` where item_code = %(item_code)s and warehouse = %(warehouse)s 
#                                     """
#                 if itm.batch_no:
#                     query += """ and batch_no = %(batch_no)s """
#                 if itm.serial_no:
#                     query += """ and serial_no = %(serial_no)s """

#                 query += """ order by modified desc limit 1 """
#                 mle = frappe.db.sql(query, {'warehouse':itm.warehouse,'item_code':itm.item_code,'batch_no':itm.batch_no,
#                                                'serial_no':itm.serial_no}, as_dict=True)
#                 if len(mle) > 0:
#                     if mle[0]['name']:
#                         mle_obj = frappe.get_doc("Milk Ledger Entry",mle[0]['name'])
#                         new_mle = frappe.new_doc("Milk Ledger Entry")
#                         new_mle.item_code = mle_obj.item_code
#                         new_mle.serial_no = cstr(mle_obj.serial_no).strip()
#                         new_mle.batch_no = mle_obj.batch_no
#                         new_mle.warehouse = mle_obj.warehouse
#                         new_mle.posting_date = self.posting_date
#                         new_mle.posting_time = self.posting_time
#                         new_mle.voucher_type = "Purchase Receipt"
#                         new_mle.voucher_no = self.name
#                         new_mle.voucher_detail_no = itm.name
#                         new_mle.actual_qty = itm.total_weight
#                         new_mle.fat = itm.fat
#                         new_mle.snf = itm.clr
#                         new_mle.stock_uom = itm.weight_uom
#                         new_mle.qty_after_transaction = itm.total_weight + mle_obj.qty_after_transaction
#                         new_mle.fat_after_transaction = mle_obj.fat_after_transaction + itm.fat
#                         new_mle.snf_after_transaction = mle_obj.snf_after_transaction + itm.clr
#                         new_mle.fat_per = ((mle_obj.fat_after_transaction + itm.fat) / (itm.total_weight + mle_obj.qty_after_transaction)) * 100
#                         new_mle.snf_per = ((mle_obj.snf_after_transaction + itm.clr) / (itm.total_weight + mle_obj.qty_after_transaction)) * 100
#                         new_mle.save(ignore_permissions=True)
                        # new_mle.submit()

# def cancel_create_milk_stock_ledger(self,method):
#     for itm in self.items:
#         itm_obj = frappe.get_doc("Item", itm.item_code)
#         maintain_snf_fat = itm_obj.maintain_fat_snf_clr
#         good_cow_milk = frappe.db.get_single_value("Dairy Settings", "cow_pro")
#         good_buff_milk = frappe.db.get_single_value("Dairy Settings", "buf_pro")
#         good_mix_milk = frappe.db.get_single_value("Dairy Settings", "mix_pro")
#         if itm.item_code == good_cow_milk or itm.item_code == good_buff_milk or itm.item_code == good_mix_milk or maintain_snf_fat == 1:
#             query = """ select name from `tabMilk Ledger Entry` where item_code = %(item_code)s and warehouse = %(warehouse)s 
#                                             """
#             if itm.batch_no:
#                 query += """ and batch_no = %(batch_no)s """
#             if itm.serial_no:
#                 query += """ and serial_no = %(serial_no)s """

#             query += """ and voucher_type = "Purchase Receipt" and voucher_no = %(voucher_no)s 
#                                 and voucher_detail_no = %(voucher_detail_no)s """

#             query += """ order by modified desc limit 1 """
#             mle = frappe.db.sql(query, {'warehouse': itm.warehouse, 'item_code': itm.item_code, 'batch_no': itm.batch_no,
#                                         'serial_no': itm.serial_no,"voucher_detail_no":itm.name,"voucher_no":itm.parent}, as_dict=True)
#             if len(mle) > 0:
#                 if mle[0]['name']:
#                     mle_obj = frappe.get_doc("Milk Ledger Entry", mle[0]['name'])

#                     new_mle = frappe.new_doc("Milk Ledger Entry")
#                     new_mle.item_code = mle_obj.item_code
#                     new_mle.serial_no = cstr(mle_obj.serial_no).strip()
#                     new_mle.batch_no = mle_obj.batch_no
#                     new_mle.warehouse = mle_obj.warehouse
#                     new_mle.posting_date = self.posting_date
#                     new_mle.posting_time = self.posting_time
#                     new_mle.voucher_type = "Purchase Receipt"
#                     new_mle.voucher_no = self.name
#                     new_mle.voucher_detail_no = itm.name
#                     new_mle.actual_qty = -1 * itm.total_weight
#                     new_mle.fat = -1 * itm.fat
#                     new_mle.snf = -1 * itm.clr
#                     new_mle.stock_uom = itm.weight_uom
#                     new_mle.qty_after_transaction =  mle_obj.qty_after_transaction - itm.total_weight
#                     new_mle.fat_after_transaction = mle_obj.fat_after_transaction - itm.fat
#                     new_mle.snf_after_transaction = mle_obj.snf_after_transaction - itm.clr
#                     new_mle.fat_per = flt((mle_obj.fat_after_transaction - itm.fat) / (mle_obj.qty_after_transaction - itm.total_weight)) * 100
#                     new_mle.snf_per = flt((mle_obj.snf_after_transaction - itm.clr) / (mle_obj.qty_after_transaction - itm.total_weight)) * 100
#                     # new_mle.is_cancelled = 1

#                     frappe.db.sql(""" update `tabMilk Ledger Entry` set is_cancelled = 1 where name = %(name)s """,
#                                   {'name': mle_obj.name})
#                     frappe.db.commit()

#                     new_mle.save(ignore_permissions=True)
#                     # new_mle.submit()
#                     frappe.db.sql(""" update `tabMilk Ledger Entry` set is_cancelled = 1 where name = %(name)s """,
#                                   {'name': new_mle.name})
#                     frappe.db.commit()







