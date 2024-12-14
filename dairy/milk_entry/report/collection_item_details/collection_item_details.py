# Copyright (c) 2013, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from itertools import zip_longest


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	return columns, data

def get_columns(filters):
    columns = [
        {
            "label": _("Name"),
            "fieldname": "name",
            "fieldtype": "Data",
            "width": 120
        },
		{
            "label": _("DCS"),
            "options": "Warehouse",
            "fieldname": "dcs_id",
            "fieldtype": "Link",
            "width": 160
        },
#         {
#             "label": _("Cow Milk Volume"),
#             "fieldname": "cow_milk_vol",
#             "fieldtype": "Float",
#             "width": 100
#         },
#         {
#             "label": _("Buffalow Milk Volume"),
#             "fieldname": "buf_milk_vol",
#             "fieldtype": "Float",
#             "width": 100            
#         },
# 		{
#             "label": _("Mix Milk Volume"),
#             "fieldname": "mix_milk_vol",
#             "fieldtype": "Float",
#             "width": 100
#         },
		
		
		{
            "label": _("Cow Milk Cans"),
            "fieldname": "cow_milk_cans",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": _("Buffalo Milk Cans"),
            "fieldname": "buf_milk_cans",
            "fieldtype": "Float",
            "width": 100
        },
		{
            "label": _("Mix Milk Cans"),
            "fieldname": "mix_milk_cans",
            "fieldtype": "Float",
            "width": 100
        },
		
		
		{
            "label": _("Cow Sample Number"),
            "fieldname": "cow_milk_sam",
            "fieldtype": "Link",
            "options" : "Raw Milk Sample",
            "width": 100
        },
        {
            "label": _("Buffalo Sample Number"),
            "fieldname": "buf_milk_sam",
            "fieldtype": "Link",
            "options" : "Raw Milk Sample",
            "width": 100
        },
		{
            "label": _("Mix Sample Number"),
            "fieldname": "mix_milk_sam",
            "fieldtype": "Link",
            "options" : "Raw Milk Sample",
            "width": 100
        },
		
		
#         {
#             "label": _("Gate Pass"),
#             "fieldname": "gate_pass",
#             "fieldtype": "Link",
#             ""
#             "width": 80
#         },
        {
            "label": _("Time"),
            "fieldname": "time",
            "fieldtype": "Time",
            "width": 80
        },
		{
            "label": _("Van Collection"),
            "fieldname": "van_col",
            "fieldtype": "Link",
            "options":"Van Collection",
            "width": 120
        }
        
    ]
    return columns

def get_data(filters):
    # print("======")
    conditions = get_conditions(filters)
    
    my_list = []
    vci = frappe.get_all('Van Collection Items',{'company':filters.get('company')},['name'])
    # print('vciiiiiiiiiiiiiiiiiiiiiiiiiiii',len(vci))
    for i in vci:
        my_dict = {
        'parent': '',
        'cow_milk_sam':[],
        'buf_milk_sam':[],
        'mix_milk_sam':[]
    }
        doc = frappe.get_doc('Van Collection Items',i.name)
        my_dict.update({
            'parent' : doc.name
        })
        if doc.cow_milk_sam:
            clist = []
            for cms in doc.cow_milk_sam:
                clist.append(cms.get('sample_lines'))
            my_dict.update({'cow_milk_sam':clist})

        if doc.buf_milk_sam:
            blist = []
            for bms in doc.buf_milk_sam:
                blist.append(bms.get('sample_lines'))
            my_dict.update({'buf_milk_sam':blist})

        if doc.mix_milk_sam:
            mlist = []
            for mms in doc.mix_milk_sam:
                mlist.append(mms.get('sample_lines'))
            my_dict.update({'mix_milk_sam':mlist})

        if my_dict.get('parent') == doc.name and {
                            doc.name : my_dict
                            } not in my_list: 
            my_list.append({
                            doc.name : my_dict
                            })

    # print('my_dict------------------------------',len(my_list))
    
        
        
    query = """ select vci.name,vci.dcs,vci.cow_milk_vol,vci.buf_milk_vol,vci.mix_milk_vol,vci.cow_milk_cans,vci.buf_milk_cans,
                            vci.mix_milk_cans,vci.time,vci.van_collection 
                            from `tabVan Collection Items` as vci
                        {conditions} """.format(conditions = conditions)

   
    # print('conditions=============',conditions)
    # print('query and conditions===========================',query+conditions)
    q_data = frappe.db.sql(query,as_dict=1)
    
    data = []
    
    for q in q_data:
        
        
    # print('samsssssssssssssssssssssssssssssss',sams)
        if my_list:
            for r in my_list:
                print('rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr',r,q.get('name'))
                if q.get('name') in r:
                    name = q.get("name")
                    print('rrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr22',r.get(name))
                    md = r.get(name)
                    cms = []
                    bms = []
                    mms = []
                    if md.get('cow_milk_sam'):
                        
                        cms = md.get('cow_milk_sam')
                    if md.get('buf_milk_sam'):
                        bms = md.get('buf_milk_sam')
                    if r.get('mix_milk_sam'):
                        mms = md.get('mix_milk_sam')

                    max_length = max(len(cms), len(bms), len(mms))

                    d = [[cms[i] if i < len(cms) else "", bms[i] if i < len(bms) else "", mms[i] if i < len(mms) else ""] for i in range(max_length)]

                    
                    print('dddddddddddddddddddddddddddddddddddddddd',d)
                    if d:
                        for k in d:
                            fd = {}
                            # print('ssssssssssssssssssssssss',s,s+1,s+2)
                            fd.update({
                                    "name": q.get('name'),
                                    "dcs_id": q.get('dcs'),
                                    "cow_milk_vol": q.get('cow_milk_vol'),
                                    "buf_milk_vol": q.get('buf_milk_vol'),
                                    "mix_milk_vol": q.get('mix_milk_vol'),
                                    "cow_milk_cans": q.get('cow_milk_cans'),
                                    "buf_milk_cans": q.get('buf_milk_cans'),
                                    "mix_milk_cans": q.get('mix_milk_cans'),
                                    "cow_milk_sam": k[0],
                                    "buf_milk_sam": k[1],
                                    "mix_milk_sam": k[2],
                                    "time":q.get('time'),
                                    "van_col":q.get('van_collection'),
                                    }

                            )
                            # print('fd-------------------------',fd) 
                    # if fd not in data:  
                            data.append(fd)
                    if not d:
                        fd = {}
                        # print('ssssssssssssssssssssssss',s,s+1,s+2)
                        fd.update({
                                "name": q.get('name'),
                                "dcs_id": q.get('dcs'),
                                "cow_milk_vol": q.get('cow_milk_vol'),
                                "buf_milk_vol": q.get('buf_milk_vol'),
                                "mix_milk_vol": q.get('mix_milk_vol'),
                                "cow_milk_cans": q.get('cow_milk_cans'),
                                "buf_milk_cans": q.get('buf_milk_cans'),
                                "mix_milk_cans": q.get('mix_milk_cans'),
                                "cow_milk_sam": "",
                                "buf_milk_sam": "",
                                "mix_milk_sam": "",
                                "time":q.get('time'),
                                "van_col":q.get('van_collection'),
                                }

                        )
                        # print('fd-------------------------',fd) 
                # if fd not in data:  
                        data.append(fd)



    return data


def get_conditions(filters):
    print("=====filters",filters)
    query = """      """
    if filters:
        if filters.get('parent'):
            query += """ where  vci.van_collection = '%s' """%filters.parent
# 		if filters.get('dcs'):
# 		    query += """ and  dcs_id = '%s'  """%filters.dcs
# 		if filters.get('member'):
# 		    query += """ and  member = '%s'  """%filters.member
# 		if filters.get('pricelist'):
# 		    query += """ and  milk_rate = '%s'  """%filters.pricelist
# 		if filters.get('shift') != 'All':
# 		    query += """ and  shift = '%s' """%filters.shift
# 		if filters.get('milk_type') != 'All':
# 		    query += """ and  milk_type = '%s' """%filters.milk_type
        
    return query
