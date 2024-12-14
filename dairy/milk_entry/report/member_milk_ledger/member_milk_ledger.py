# Copyright (c) 2023, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

import calendar
import frappe
from frappe import _, _dict

TRANSLATIONS = frappe._dict()

def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters, columns)
	# chart = get_chart_data(data,filters)
	update_total()

	return columns, data 


def update_translations():
	TRANSLATIONS.update(
		dict(OPENING=_("Opening"), TOTAL=_("Total"), CLOSING_TOTAL=_("Closing (Opening + Total)"))
	)



def get_columns(filters):
	columns = [
			{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 150},
			{"label": _("Shift"), "fieldname": "shift", "fieldtype": "Data", "width": 150},
			{"label": _("Member"), "fieldname": "member", "fieldtype": "Data", "width": 150},
			# {"label": _("Name"), "fieldname": "name", "fieldtype": "Link","options":"Milk Entry","width": 150},
			{"label": _("DCS"), "fieldname": "dcs_id", "fieldtype": "Data", "width": 150},
			{"label": _("Ltr"), "fieldname": "volume", "fieldtype": "Float", "width": 150},
			{"label": _("Fat%"), "fieldname": "fat", "fieldtype": "Percent", "width": 150},
			{"label": _("Fat(in kg)"), "fieldname": "fat_kg", "fieldtype": "Float", "width": 150},
			{"label": _("SNF%"), "fieldname": "snf", "fieldtype": "Percent", "width": 150},
			{"label": _("SNF(in kg)"), "fieldname": "snf_kg", "fieldtype": "Float", "width": 150},
			{"label": _("CLR%"), "fieldname": "clr", "fieldtype": "Percent", "width": 150},
			{"label": _("CLR(in kg)"), "fieldname": "clr_kg", "fieldtype": "Float", "width": 150},
			{"label": _("Weight(in kg)"), "fieldname": "litre", "fieldtype": "Float", "width": 150},
			{"label": _("Rate"), "fieldname": "unit_price", "fieldtype": "Currency", "width": 150},
			{"label": _("Amount"), "fieldname": "total", "fieldtype": "Currency", "width": 150},
			{"label": _("SNF Deduction"), "fieldname": "snf_deduction", "fieldtype": "Currency", "width": 150},
			{"label": _("FAT Deduction"), "fieldname": "fat_deduction", "fieldtype": "Currency", "width": 150},
			{"label": _("Incentive"), "fieldname": "incentive", "fieldtype": "Currency", "width": 150},
			{"label": _("Purchase Invoice"), "fieldname": "parent", "fieldtype": "Link","options":"Purchase Invoice", "width": 150},
			{"label": _("Purchase Invoice status"), "fieldname": "status", "fieldtype": "Link","options":"Purchase Invoice", "width": 150},
			# {"label": _("SNF Deduction"), "fieldname": "snf_deduction", "fieldtype": "Currency", "width": 150},
	]
	return columns


def get_data(filters, columns):
	conditions = get_conditions(filters)
	group_by = get_group_by(filters)
	totals = get_totals_dict()
	data =[]
	from_date = filters.get('from_date')
	to_date = filters.get('to_date')
	result=[]
	if not filters.get('group_by'):
		print('kkkkkkkkkkkkkkkkkkkkkkkkkkkk')
		result = frappe.db.sql("""select pi.parent,
									p.status,
									me.name,
									me.date,
									me.shift,
									me.member,
									me.dcs_id,
									sum(me.volume) as volume,
									sum(me.fat) as fat,
									sum(me.fat_kg) as fat_kg,
									sum(me.snf) as snf,
									sum(me.snf_kg) as snf_kg,
									sum(me.clr) as clr,
									sum(me.clr_kg) as clr_kg,
									sum(me.litre) as litre,
									sum(me.unit_price) as unit_price,
									sum(me.total) as total,
									sum(me.snf_deduction) as snf_deduction,
									sum(me.fat_deduction) as fat_deduction,
									sum(me.incentive) as incentive
									from `tabMilk Entry` as me 
									join `tabPurchase Receipt` as pr on pr.milk_entry = me.name 
									left outer join `tabPurchase Invoice Item` as pi on pi.purchase_receipt = pr.name
									left outer join `tabPurchase Invoice` as p on p.name = pi.parent 
									{conditions} group by me.date , me.member ,me.shift
									order by me.date asc 
									""".format(conditions=conditions), as_dict=True)
		
		return result
	
	if filters.get('group_by'):
		
		gb = filters.get('group_by')
		final_data = []
		if gb == 'DCS':
			dcs = frappe.db.sql(''' select distinct(dcs_id) as dcs_id from `tabMilk Entry` as me {conditions}'''
									.format(conditions=conditions),as_dict=1)
			for d in dcs:
				result = frappe.db.sql("""select pi.parent,
												p.status,
												me.name,
												me.date,
												me.shift,
												me.member,
												me.dcs_id as dcs_w,
												me.volume as volume,
												me.fat as fat,
												me.fat_kg as fat_kg,
												me.snf as snf,
												me.snf_kg as snf_kg,
												me.clr as clr,
												me.clr_kg as clr_kg,
												me.litre as litre,
												me.unit_price as unit_price,
												me.total as total,
												me.snf_deduction as snf_deduction,
												me.fat_deduction as fat_deduction,
												me.incentive as incentive
												from `tabMilk Entry` as me 
												join `tabPurchase Receipt` as pr on pr.milk_entry = me.name 
												join `tabPurchase Invoice Item` as pi on pi.purchase_receipt = pr.name
												join `tabPurchase Invoice` as p on p.name = pi.parent and me.dcs_id="{0}"
												{conditions} group by me.name
												order by me.date asc 
												""".format(d.get("dcs_id"),conditions=conditions), as_dict=True)

				
				dic = []
				volume = 0.0
				fat = 0
				fat_kg = 0.0
				snf = 0
				snf_kg = 0.0
				clr = 0
				clr_kg = 0.0
				litre = 0.0
				rate = 0
				amount= 0
				incentive = 0
				fat_deduction = 0
				snf_deduction = 0
				for j in result:
					
					volume += float(j.get('volume'))
					fat += float(j.get('fat'))
					fat_kg += float(j.get('fat_kg'))
					snf += float(j.get('snf'))
					snf_kg += float(j.get('snf_kg'))
					clr += float(j.get('clr'))
					clr_kg += float(j.get('clr_kg'))
					litre += float(j.get('litre'))
					rate += float(j.get('unit_price'))
					amount += float(j.get('total'))
					incentive += float(j.get('incentive'))
					fat_deduction += float(j.get('fat_deduction'))
					snf_deduction += float(j.get('snf_deduction'))

				for r in result:
					
					if {'dcs_id':r.get('dcs_w') , 'volume' : volume,'fat':fat,'fat_kg':fat_kg,
	 						'snf':snf,'snf_kg':snf_kg,'clr':clr,'clr_kg':clr_kg,'litre':litre,'unit_price':rate,
							'total':amount,'incentive':incentive,
							'fat_deduction':fat_deduction,'snf_deduction':snf_deduction} not in final_data:
						
						final_data.append({'dcs_id':r.get('dcs_w'),'volume':volume,'fat':fat,'fat_kg':fat_kg,
			 									'snf':snf,'snf_kg':snf_kg,'clr':clr,'clr_kg':clr_kg,'litre':litre,'unit_price':rate,
												'total':amount,'incentive':incentive,
												'fat_deduction':fat_deduction,'snf_deduction':snf_deduction})


						
					# for j in final_data:
					if r not in final_data:
						final_data.append(r)

				
			return final_data
				

		if gb == 'Member':
			final_data = []
			memb = frappe.db.sql(''' select distinct(member) as member from `tabMilk Entry` as me {conditions}'''
									.format(conditions=conditions),as_dict=1)
			for m in memb:
			
				result = frappe.db.sql("""select pi.parent,
												p.status,
												me.name,
												me.date,
												me.shift,
												me.member as mem,
												me.dcs_id,
												me.volume as volume,
												me.fat as fat,
												me.fat_kg as fat_kg,
												me.snf as snf,
												me.snf_kg as snf_kg,
												me.clr as clr,
												me.clr_kg as clr_kg,
												me.litre as litre,
												me.unit_price as unit_price,
												me.total as total,
												me.snf_deduction as snf_deduction,
												me.fat_deduction as fat_deduction,
												me.incentive as incentive
												from `tabMilk Entry` as me 
												join `tabPurchase Receipt` as pr on pr.milk_entry = me.name 
												left outer join `tabPurchase Invoice Item` as pi on pi.purchase_receipt = pr.name
												join `tabPurchase Invoice` as p on p.name = pi.parent  and me.member="{0}"
												{conditions} 
												order by me.date asc 
												""".format(m.get("member"),conditions=conditions), as_dict=True)

				volume = 0.0
				fat = 0
				fat_kg = 0.0
				snf = 0
				snf_kg = 0.0
				clr = 0
				clr_kg = 0.0
				litre = 0.0
				rate = 0
				amount= 0
				incentive = 0
				fat_deduction = 0
				snf_deduction = 0
				for j in result:
					
					volume += float(j.get('volume'))
					fat += float(j.get('fat'))
					fat_kg += float(j.get('fat_kg'))
					snf += float(j.get('snf'))
					snf_kg += float(j.get('snf_kg'))
					clr += float(j.get('clr'))
					clr_kg += float(j.get('clr_kg'))
					litre += float(j.get('litre'))
					rate += float(j.get('unit_price'))
					amount += float(j.get('total'))
					incentive += float(j.get('incentive'))
					fat_deduction += float(j.get('fat_deduction'))
					snf_deduction += float(j.get('snf_deduction'))

				for r in result:
					if {'member':r.get('mem'),'volume' : volume,'fat':fat,'fat_kg':fat_kg,
	 						'snf':snf,'snf_kg':snf_kg,'clr':clr,'clr_kg':clr_kg,'litre':litre,'unit_price':rate,
							'total':amount,'incentive':incentive,
							'fat_deduction':fat_deduction,'snf_deduction':snf_deduction} not in final_data:
						
						final_data.append({'member':r.get('mem'),'volume':volume,'fat':fat,'fat_kg':fat_kg,
			 									'snf':snf,'snf_kg':snf_kg,'clr':clr,'clr_kg':clr_kg,'litre':litre,'unit_price':rate,
												'total':amount,'incentive':incentive,
												'fat_deduction':fat_deduction,'snf_deduction':snf_deduction})
						
					# for j in final_data:
					if r not in final_data:
						final_data.append(r)
				
			return final_data
		

		if gb == 'Shift':
			final_data = []
			shift = frappe.db.sql(''' select distinct(shift) as shift from `tabMilk Entry` as me {conditions}'''
									.format(conditions=conditions),as_dict=1)
			for s in shift:
				result = frappe.db.sql("""select pi.parent,
												p.status,
												me.name,
												me.date,
												me.shift as sft,
												me.member,
												me.dcs_id,
												me.volume as volume,
												me.fat as fat,
												me.fat_kg as fat_kg,
												me.snf as snf,
												me.snf_kg as snf_kg,
												me.clr as clr,
												me.clr_kg as clr_kg,
												me.litre as litre,
												me.unit_price as unit_price,
												me.total as total,
												me.snf_deduction as snf_deduction,
												me.fat_deduction as fat_deduction,
												me.incentive as incentive
												from `tabMilk Entry` as me 
												join `tabPurchase Receipt` as pr on pr.milk_entry = me.name 
												join `tabPurchase Invoice Item` as pi on pi.purchase_receipt = pr.name
												join `tabPurchase Invoice` as p on p.name = pi.parent and me.shift = "{0}"
												{conditions} group by me.name
												# order by me.date asc 
												""".format(s.get("shift"),conditions=conditions), as_dict=True)

				volume = 0.0
				fat = 0
				fat_kg = 0.0
				snf = 0
				snf_kg = 0.0
				clr = 0
				clr_kg = 0.0
				litre = 0.0
				rate = 0
				amount= 0
				incentive = 0
				fat_deduction = 0
				snf_deduction = 0
				for j in result:
					
					volume += float(j.get('volume'))
					fat += float(j.get('fat'))
					fat_kg += float(j.get('fat_kg'))
					snf += float(j.get('snf'))
					snf_kg += float(j.get('snf_kg'))
					clr += float(j.get('clr'))
					clr_kg += float(j.get('clr_kg'))
					litre += float(j.get('litre'))
					rate += float(j.get('unit_price'))
					amount += float(j.get('total'))
					incentive += float(j.get('incentive'))
					fat_deduction += float(j.get('fat_deduction'))
					snf_deduction += float(j.get('snf_deduction'))

				for r in result:
					if {'shift':r.get('sft'),'volume' : volume,'fat':fat,'fat_kg':fat_kg,
	 						'snf':snf,'snf_kg':snf_kg,'clr':clr,'clr_kg':clr_kg,'litre':litre,'unit_price':rate,
							'total':amount,'incentive':incentive,
							'fat_deduction':fat_deduction,'snf_deduction':snf_deduction} not in final_data:
						
						final_data.append({'shift':r.get('sft'),'volume':volume,'fat':fat,'fat_kg':fat_kg,
			 									'snf':snf,'snf_kg':snf_kg,'clr':clr,'clr_kg':clr_kg,'litre':litre,'unit_price':rate,
												'total':amount,'incentive':incentive,
												'fat_deduction':fat_deduction,'snf_deduction':snf_deduction})
						
					# for j in final_data:
					if r not in final_data:
						final_data.append(r)
				
			return final_data
			

		if gb == 'Date':
			final_data = []
			dt = frappe.db.sql(''' select distinct(date) as de from `tabMilk Entry` as me {conditions}'''
									.format(conditions=conditions),as_dict=1)
			for da in dt:
				result = frappe.db.sql("""select pi.parent,
												p.status,
												me.name,
												me.date as dt,
												me.shift,
												me.member,
												me.dcs_id,
												me.volume as volume,
												me.fat as fat,
												me.fat_kg as fat_kg,
												me.snf as snf,
												me.snf_kg as snf_kg,
												me.clr as clr,
												me.clr_kg as clr_kg,
												me.litre as litre,
												me.unit_price as unit_price,
												me.total as total,
												me.snf_deduction as snf_deduction,
												me.fat_deduction as fat_deduction,
												me.incentive as incentive
												from `tabMilk Entry` as me 
												join `tabPurchase Receipt` as pr on pr.milk_entry = me.name 
												join `tabPurchase Invoice Item` as pi on pi.purchase_receipt = pr.name
												join `tabPurchase Invoice` as p on p.name = pi.parent and me.date = "{0}"
												{conditions} group by me.name
												order by me.date asc 
												""".format(da.get("de"),conditions=conditions), as_dict=True)

				volume = 0.0
				fat = 0
				fat_kg = 0.0
				snf = 0
				snf_kg = 0.0
				clr = 0
				clr_kg = 0.0
				litre = 0.0
				rate = 0
				amount= 0
				incentive = 0
				fat_deduction = 0
				snf_deduction = 0
				for j in result:
					
					volume += float(j.get('volume'))
					fat += float(j.get('fat'))
					fat_kg += float(j.get('fat_kg'))
					snf += float(j.get('snf'))
					snf_kg += float(j.get('snf_kg'))
					clr += float(j.get('clr'))
					clr_kg += float(j.get('clr_kg'))
					litre += float(j.get('litre'))
					rate += float(j.get('unit_price'))
					amount += float(j.get('total'))
					incentive += float(j.get('incentive'))
					fat_deduction += float(j.get('fat_deduction'))
					snf_deduction += float(j.get('snf_deduction'))

				for r in result:
					if {'date':r.get('dt'),'volume' : volume,'fat':fat,'fat_kg':fat_kg,
	 						'snf':snf,'snf_kg':snf_kg,'clr':clr,'clr_kg':clr_kg,'litre':litre,'unit_price':rate,
							'total':amount,'incentive':incentive,
							'fat_deduction':fat_deduction,'snf_deduction':snf_deduction} not in final_data:
						
						final_data.append({'date':r.get('dt'),'volume':volume,'fat':fat,'fat_kg':fat_kg,
			 									'snf':snf,'snf_kg':snf_kg,'clr':clr,'clr_kg':clr_kg,'litre':litre,'unit_price':rate,
												'total':amount,'incentive':incentive,
												'fat_deduction':fat_deduction,'snf_deduction':snf_deduction})
						
					if r not in final_data:
						final_data.append(r)
				
			return final_data

	# return result


def update_total():
	TRANSLATIONS.update(
		dict( TOTAL=_("Total"))
	)


def get_totals_dict():
	def add_total(label):
		return _dict(
			date = "'{0}'".format(label),
			volume = 0.0,
			fat = 0,
			snf = 0,
			clr = 0,
			litre = 0.0,
			rate = 0,
			amount= 0,
			incentive = 0,
			fat_deduction = 0,
			snf_deduction = 0,
		)

	return _dict(
		opening= add_total(TRANSLATIONS.OPENING),
		total= add_total(TRANSLATIONS.TOTAL),
		closing= add_total(TRANSLATIONS.CLOSING_TOTAL),
	)

def get_group_by(filters):
	query = ""

	if filters.get('group_by') == 'DCS':
		query += """ group by me.dcs_id"""
	if filters.get('group_by') == 'Member':
		query += """ group by me.member"""
	if filters.get('group_by') == 'Shift':
		query += """ group by me.shift"""
	if filters.get('group_by') == 'Date':
		query += """ group by me.date"""
	print('query---------------@@@@@@@@@@@@@@@@@@@@@@@@@',query)
	return query

def get_conditions(filters):
	query=""
	
	if filters.get('from_date') and ('to_date'):
		query  += """  where DATE(me.date) between DATE('{0}') and DATE('{1}')  and me.docstatus = 1""".format(filters.get('from_date'),filters.get('to_date'))
	if filters.get('dcs'):
		query += """ and  me.dcs_id = '%s'  """%filters.dcs
	if filters.get('member'):
		query += """ and  me.member = '%s'  """%filters.member
	if filters.get('shift'):
		query += """ and  me.shift = '%s'  """%filters.shift
	# if filters.get('date'):
	# 	query += """ and  me.date = '%s'  """%filters.date
	print('conditions-----------***********************',query)
	return query