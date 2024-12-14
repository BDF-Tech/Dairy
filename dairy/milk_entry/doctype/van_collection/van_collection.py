# -*- coding: utf-8 -*-
# Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.model.document import Document
from datetime import date
from datetime import datetime
from frappe.utils import add_to_date, get_datetime, now_datetime

from frappe.utils.data import flt

class VanCollection(Document):
    def validate(self):
        self.get_remaining_shift()

    @frappe.whitelist()
    def submit_van_collection(self):
        self.db_set('status','Submitted')

    def on_cancel(self):
        milk_entry = frappe.get_all('Milk Entry',{'date':self.date},['name','van_collection_completed','date'])
        for me in milk_entry:
            if self.date == me.date and self.to_date == me.date:
                vcc = frappe.get_doc('Milk Entry',me.name) 
                vcc.van_collection_completed = 0
                vcc.db_update()
                vci = frappe.get_all('Van Collection Items',{'van_collection':self.name},['name'])
                for dl in vci:
                    dlt = frappe.delete_doc('Van Collection Items',dl.name)
            

        
    @frappe.whitelist()
    def change_status_complete(self):
        self.db_set('status', 'Completed')
        self.flags.ignore_validate_update_after_submit = True  # ignore after submit permission
        milk_entry = frappe.get_all('Milk Entry',{'date':self.date},['name','van_collection_completed','date'])
        for me in milk_entry:
            if self.date == me.date and self.to_date == me.date:
                vcc = frappe.get_doc('Milk Entry',me.name)
                if self.status == "Completed":
                    vcc.van_collection_completed = 1
                    vcc.db_update()
        
        self.save(ignore_permissions=True)


    def get_remaining_shift(self):
        options = []
        rs = frappe.db.sql(""" select df.options from `tabDocType` as dt
                            join `tabDocField` as df on df.parent = dt.name
                            where dt.name = 'Van Collection' 
                            and df.fieldname = 'shift' """,as_dict = 1)
        
        print('rrrrrrrssssssssssssssssssssssss',rs)
        if rs:
            for o in rs:
                sft = o.get('options')
                x = sft.split('\n')
                options = x
            print('options********************************',options)
        return options
    

    @frappe.whitelist()
    def van_start_collection(self):
        
        total_date = []
        sde = []
        state_climatic_factor,state_factor = frappe.db.get_value('Warehouse',{'is_dcs':1},['state_climatic_factor','state_factor'])
        seq =[]
        sequence = frappe.db.get_all('Warehouse',{'is_dcs':1},['sequence'])
        for i in sequence:
            seq.append(i.get('sequence'))
        print('sequence******************',seq,sorted(seq))
        
        tdate = date.today()
        d1 = datetime.strptime(self.date, "%Y-%m-%d")
        d2 = datetime.strptime(self.to_date, "%Y-%m-%d")

        # difference between dates in timedelta
        delta = d2 - d1
        for k in range(0,delta.days+1):
            dt = add_to_date(self.date,days=k)
            total_date.append(dt)
        # print('total date&&&&&&&&&&&&&&&&&&&&&&&&&&&',total_date,k)
        
        if self.shift == self.to_shift:
            remaining_shift = self.get_remaining_shift()
            for rs in remaining_shift:
                # print('length _______________________--',len(total_date)>1)
                if len(total_date) > 1:
                    for d in total_date:
                        
                        if rs != self.shift:
                            sd = {'date':d,'shift':self.shift}
                            sdt = {'date':d,'shift':rs}
                            if sd not in sde:
                                sde.append(sd)
                            if sdt not in sde:
                                sde.append(sdt)
                           

                    for uw in sde:
                        if uw.get('date') == self.to_date and self.to_shift != uw.get('shift'):
                            sde.remove(uw)
                        if self.shift == "Evening" and self.to_shift == "Evening":
                            if uw.get('date') == self.date:
                                if uw.get('shift') != self.shift:
                                    sde.remove(uw)
                            if uw.get('date') == self.to_date:
                                if uw.get('shift') != self.to_shift:
                                    sde.append(uw)
                elif(len(total_date) == 1):
                    sd = {'date':total_date[0],'shift':self.shift}
                    if sd not in sde:
                        sde.append(sd)
                    
            print(' equal sdeeeeeeeeeeee88888888888888888888',sde)

        if self.shift != self.to_shift:
            for d in total_date:

                sd = {'date':d,'shift':self.shift}
                sdt = {'date':d,'shift':self.to_shift}
                if sd not in sde:
                    # print('sd*************************',sd)
                    sde.append(sd)
                if sdt not in sde:
                    # print('sdt************************',sdt)
                    sde.append(sdt)
            for uw in sde:
                if self.shift == "Evening" and self.to_shift == "Morning":
                    if uw.get('date') == self.date:
                        if uw.get('shift') != self.shift:
                            sde.remove(uw)
                    if uw.get('date') == self.to_date:
                        if uw.get('shift') != self.to_shift:
                            sde.remove(uw)

                
            # print('sdeeeeeeeeeeee88888888888888888888',sde)

        if self:
            warehouse = frappe.db.get_all("Warehouse",{
                                            "route": self.route,
                                            "is_dcs": 1
                                        })
            if not warehouse:
                frappe.throw(_("No Warehouse present in this Route"))
            
            final_result = []
            
           
            for res in warehouse:
                milk_type = 'Cow'
                total_volume_cow = 0.0
                fat_cow = 0.0 
                clr_cow = 0.0
                snf_cow = 0.0
                fat_kg_cow =0.0
                snf_kg_cow = 0.0
                clr_kg_cow = 0.0

                milk_type = 'Buffalo'
                total_volume_buf= 0.0
                fat_buf = 0.0 
                clr_buf = 0.0
                snf_buf = 0.0
                fat_kg_buf =0.0
                snf_kg_buf = 0.0
                clr_kg_buf = 0.0

                milk_type = 'Mix'
                total_volume_mix = 0.0
                fat_mix = 0.0 
                clr_mix = 0.0
                snf_mix = 0.0
                fat_kg_mix =0.0
                snf_kg_mix = 0.0
                clr_kg_mix = 0.0
                # for j in sde:
                #     print('dateeeeeeeeeeee************************8',j.get('date'))
                #     result = frappe.db.sql("""select date,name,dcs_id,milk_type,volume as total_volume,fat as fat,clr as clr ,
                #                         fat_kg as fat_kg , snf_kg as snf_kg , clr_kg as clr_kg
                #                         from `tabMilk Entry` 
                #                         where docstatus =1 and dcs_id = '{0}'and date = '{1}' 
                #                         and name = 'E00319'
                #                         """.format(res.name,j.get('date')), as_dict =True)

                #     print('result***************************',result)
                
                for j in sde:
                    result = frappe.db.sql("""select dcs_id,milk_type,sum(volume) as total_volume,sum(fat) as fat,sum(clr) as clr ,
                                        sum(snf) as snf,sum(fat_kg) as fat_kg , sum(snf_kg) as snf_kg , sum(clr_kg) as clr_kg
                                        from `tabMilk Entry` 
                                        where docstatus =1 and dcs_id = '{0}' and shift = '{1}' and date = '{2}' 
                                        group by milk_type""".format(res.name,j.get('shift'),j.get('date')), as_dict =True)


                    if result:
                
                        for sm in result:
                            doc=frappe.get_doc("Dairy Settings")
                            item=0.0
                            if sm.get('milk_type') == 'Cow':
                                total_volume_cow += sm.get('total_volume')
                                fat_cow += sm.get('fat')
                                clr_cow += sm.get('clr')
                                snf_cow += sm.get('snf')
                                fat_kg_cow += sm.get('fat_kg')
                                snf_kg_cow += sm.get('snf_kg')
                                clr_kg_cow += sm.get('clr_kg')
                                item = frappe.db.get_value('Item',{"name":doc.cow_pro},['weight_per_unit'])
                                print('cow item______________________',item)

                            if sm.get('milk_type') == 'Buffalo':
                                total_volume_buf += sm.get('total_volume')
                                fat_buf += sm.get('fat')
                                clr_buf += sm.get('clr')
                                snf_buf += sm.get('snf')
                                fat_kg_buf += sm.get('fat_kg')
                                snf_kg_buf += sm.get('snf_kg')
                                clr_kg_buf += sm.get('clr_kg')
                                item = frappe.db.get_value('Item',{"name":doc.buf_pro},['weight_per_unit'])
                                print('buffalo item ______________________________',item)
                

                            if sm.get('milk_type') == 'Mix':
                                total_volume_mix += sm.get('total_volume')
                                fat_mix += sm.get('fat')
                                clr_mix += sm.get('clr')
                                snf_mix += sm.get('snf')
                                fat_kg_mix += sm.get('fat_kg')
                                snf_kg_mix += sm.get('snf_kg')
                                clr_kg_mix += sm.get('clr_kg')
                                item = frappe.db.get_value('Item',{"name":doc.mix_pro},['weight_per_unit'])
                                print('mix item****************************',item)
                            # print('ooooooooooooooooooooooooooooooooooooooooooooooo',i.get('dcs_id'))

                result = [{'milk_type':'Cow','total_volume':total_volume_cow,'fat':fat_cow,'clr':clr_cow,'fat_kg':fat_kg_cow,'snf_kg':snf_kg_cow,'clr_kg':clr_kg_cow,'snf':snf_cow},
                            {'milk_type':'Buffalo','total_volume':total_volume_buf,'fat':fat_buf,'clr':clr_buf,'fat_kg':fat_kg_buf,'snf_kg':snf_kg_buf,'clr_kg':clr_kg_buf,'snf':snf_buf},
                            {'milk_type':'Mix','total_volume':total_volume_mix,'fat':fat_mix,'clr':clr_mix,'fat_kg':fat_kg_mix,'snf_kg':snf_kg_mix,'clr_kg':clr_kg_mix,'snf':snf_mix}]
                # print('result***************************',result,sm.get('dcs_id'))
                cow_volume = 0.0
                buffalo_volume = 0.0
                mix_volume = 0.0
                cow_milk_fat = buf_milk_fat = mix_milk_fat = 0.0
                cow_milk_clr = buf_milk_clr = mix_milk_clr = 0.0
                cow_milk_snf = buffalow_milk_snf = mix_milk_snf = 0.0
                buffalo_milk_snfin_kg = 0.0
                buffalo_milk_fatin_kg = 0.0
                mix_milk_snfin_kg = 0.0
                mix_milk_fatin_kg = 0.0
                cow_milk_snfin_kg=0.0
                cow_milk_fatin_kg=0.0
                cow_milk_clrin_kg=0.0
                mix_milk_clrin_kg = 0.0
                buffalo_milk_clrin_kg = 0.0

                for i in result:
                    # doc=frappe.get_doc("Dairy Settings")
                    # item=0.0
                    if i.get('milk_type') == 'Cow':
                        cow_volume = i.get('total_volume')
                        cow_milk_fat = i.get('fat')
                        cow_milk_clr = i.get('clr')
                        cow_milk_snf = i.get('snf')
                        cow_milk_snfin_kg = i.get('snf_kg')
                        cow_milk_fatin_kg = i.get('fat_kg')
                        cow_milk_clrin_kg = i.get('clr_kg')
                        # item = frappe.db.get_value('Item',{"name":doc.cow_pro},['weight_per_unit'])
                        # print('cow item______________________',item)

                    if i.get('milk_type') == 'Buffalo':
                        buffalo_volume = i.get('total_volume')
                        buf_milk_fat = i.get('fat')
                        buf_milk_clr = i.get('clr')
                        buffalow_milk_snf = i.get('snf')
                        buffalo_milk_snfin_kg = i.get('snf_kg')
                        buffalo_milk_fatin_kg = i.get('fat_kg')
                        buffalo_milk_clrin_kg = i.get('clr_kg')
                        # item = frappe.db.get_value('Item',{"name":doc.buf_pro},['weight_per_unit'])
                        # print('buffalo item ______________________________',item)
                
                    if i.get('milk_type') == 'Mix':
                        mix_volume =i.get('total_volume')
                        mix_milk_fat = i.get('fat')
                        mix_milk_clr = i.get('clr')
                        mix_milk_snf = i.get('snf')
                        mix_milk_snfin_kg = i.get('snf_kg')
                        mix_milk_fatin_kg = i.get('fat_kg')
                        mix_milk_clrin_kg = i.get('clr_kg')
                        # item = frappe.db.get_value('Item',{"name":doc.mix_pro},['weight_per_unit'])
                        # print('mix item****************************',item)

                    # doc=frappe.get_doc("Dairy Settings")
                    # item=0.0
                    # if i.get("milk_type")=="Cow":
                    #     item = frappe.db.get_value('Item',{"name":doc.cow_pro},['weight_per_unit'])
                    #     print('cow item______________________',item)
                    # if i.get("milk_type")=="Buffalo":
                    #     item = frappe.db.get_value('Item',{"name":doc.buf_pro},['weight_per_unit'])
                    #     print('buffalo item ______________________________',item)
                    # if i.get("milk_type")=="Mix":
                    #     item = frappe.db.get_value('Item',{"name":doc.mix_pro},['weight_per_unit'])
                    #     print('mix item****************************',item)
                
                    print('cow volume****************************',cow_volume)
                if cow_volume > 0 or buffalo_volume > 0 or mix_volume > 0:
                    van_collection = frappe.new_doc("Van Collection Items")
                    van_collection.dcs = res.name
                    # print('rres.name------------------------------------------',sm.get('dcs_id'))
                    # if sm.get('dcs_id'):
                    van_collection.cow_milk_vol = cow_volume
                    van_collection.buf_milk_vol = buffalo_volume
                    van_collection.mix_milk_vol = mix_volume
                    van_collection.van_collection = self.name

                    van_collection.cow_milk_fat = cow_milk_fat
                    van_collection.cow_milk_clr = cow_milk_clr
                    van_collection.cow_milk_snf = cow_milk_snf
                    van_collection.cow_milk_snfin_kg = cow_milk_snfin_kg
                    van_collection.cow_milk_fatin_kg = cow_milk_fatin_kg
                    van_collection.cow_milk_clrin_kg = cow_milk_clrin_kg
                    van_collection.buffalo_milk_snfin_kg = buffalo_milk_snfin_kg
                    van_collection.buffalo_milk_fatin_kg = buffalo_milk_fatin_kg
                    van_collection.buffalo_milk_clrin_kg = buffalo_milk_clrin_kg
                    van_collection.buf_milk_fat = buf_milk_fat
                    van_collection.buf_milk_clr = buf_milk_clr
                    van_collection.buffalow_milk_snf = buffalow_milk_snf
                    van_collection.mix_milk_snfin_kg = mix_milk_snfin_kg
                    van_collection.mix_milk_fatin_kg = mix_milk_fatin_kg
                    van_collection.mix_milk_clrin_kg = mix_milk_clrin_kg
                    van_collection.mix_milk_fat = mix_milk_fat
                    van_collection.mix_milk_clr = mix_milk_clr
                    van_collection.mix_milk_snf = mix_milk_snf
                    
                
                
                    result1 = frappe.db.sql("""Select name,milk_type from `tabSample lines` where milk_entry in
                                                        (select name from `tabMilk Entry` 
                                                        where docstatus =1 and dcs_id = %s and shift =  %s and date = %s
                                                        )""", (res.name, j.get('shift'),j.get('date')), as_dict=True)
                

                    for res in result1:
                        if res.get('milk_type') == 'Cow':
                            van_collection.append("cow_milk_sam", {
                                'sample_lines': res.get('name')
                            })
                    
                        if res.get('milk_type') == 'Buffalo':
                            van_collection.append("buf_milk_sam", {
                                'sample_lines': res.get('name')
                            })

                        if res.get('milk_type') == 'Mix':
                            van_collection.append("mix_milk_sam", {
                                'sample_lines': res.get('name')
                            })     
                   

                    # doc=frappe.get_doc("Dairy Settings")
                    # item=0.0
                    # if i.get("milk_type")=="Cow":
                    #     item = frappe.db.get_value('Item',{"name":doc.cow_pro},['weight_per_unit'])
                    #     print('cow item______________________',item)
                    # elif i.get("milk_type")=="Buffalo":
                    #     item = frappe.db.get_value('Item',{"name":doc.buf_pro},['weight_per_unit'])
                    #     print('buffalo item ______________________________',item)
                    # elif i.get("milk_type")=="Mix":
                    #     item = frappe.db.get_value('Item',{"name":doc.mix_pro},['weight_per_unit'])
                    #     print('mix item****************************',item)
                    # # print('cow_volume*********************************',cow_volume,cow_milk_fatin_kg,item)
                    if flt(cow_volume) > 0:
                        # print('cow_volume*********************************',cow_volume,cow_milk_fatin_kg,item)

                        van_collection.cow_milk_fat = (flt(cow_milk_fatin_kg) /flt((cow_volume * item))) * 100 
                        van_collection.cow_milk_clr = (flt(cow_milk_clrin_kg) /flt((cow_volume * item))) * 100 
                        van_collection.cow_milk_snf = (flt(cow_milk_snfin_kg) /flt((cow_volume * item))) * 100
                    if flt(buffalo_volume) > 0:
                        van_collection.buf_milk_fat = flt(buffalo_milk_fatin_kg /(buffalo_volume  * item)) * 100 
                        van_collection.buf_milk_clr = flt(buffalo_milk_clrin_kg /(buffalo_volume  * item)) * 100
                        van_collection.buffalow_milk_snf = flt(buffalo_milk_snfin_kg /(buffalo_volume  * item)) * 100
                    
                    if flt(mix_volume) > 0:
                        van_collection.mix_milk_fat = flt(mix_milk_fatin_kg /(mix_volume * item)) * 100 
                        van_collection.mix_milk_snf = flt(mix_milk_snfin_kg /(mix_volume * item)) * 100
                        van_collection.cow_milk_clr = flt(mix_milk_clrin_kg /(mix_volume * item)) * 100 
                    van_collection.insert(ignore_permissions = True)
                    

            self.db_set('status', 'In-Progress')
            self.flags.ignore_validate_update_after_submit = True  # ignore after submit permission
            self.save(ignore_permissions=True)

        return True



#---------------------stock entry method---------------

def change_van_collection_status(st,method):
    if st.van_collection_item:
        doc = frappe.get_doc("Van Collection Items", st.van_collection_item)
        doc.gate_pass =st.name
        doc.db_update()
    # print('st******************************8', st.rmrd_lines)
    if st.rmrd_lines:
        doc = frappe.get_doc("RMRD Lines", st.rmrd_lines)
        doc.stock_entry = st.name
        doc.db_update()