from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils.data import format_date, getdate

@frappe.whitelist()
def get_jinja_data(doc):
	res =frappe.db.sql("""
	select 
            ds.customer,ds.delivery_note,
            dn.route,
            dni.item_code,dni.item_name,dni.qty,dni.uom,dni.total_weight,dni.crate_count
        from
            `tabDelivery Trip` dt, `tabDelivery Stop` ds, `tabDelivery Note` dn, `tabDelivery Note Item` dni
        where 
            dt.docstatus =1 and dt.name = %(name)s and ds.parent = %(name)s and dn.name = ds.delivery_note and dni.parent = ds.delivery_note
             
             """,{"name":doc.name}, as_dict=True)

	return res

# *******************  Following Methods Use in gate pass print format  *******************************

@frappe.whitelist()
def get_jinja_data_del_note(doc):
	res = frappe.db.sql("""
	select distinct(delivery_note) from `tabGate Pass Item` where parent = %(name)s """, {"name": doc.name}, as_dict=True)
	return res

@frappe.whitelist()
def get_jinja_data_si(doc):
	res = frappe.db.sql("""
	select distinct(sales_invoice) from `tabGate Pass Item` where parent = %(name)s """, {"name": doc.name}, as_dict=True)
	return res

@frappe.whitelist()
def del_note_details(del_note):
	res = frappe.db.sql("""
	select 
		name,customer_name,route
	from 
		`tabDelivery Note` where name = %(name)s """, {"name": del_note}, as_dict=True)
	return res

@frappe.whitelist()
def si_note_details(del_note):
	res = frappe.db.sql("""
	select 
		name,customer,customer_name,route
	from 
		`tabSales Invoice` where name = %(name)s """, {"name": del_note}, as_dict=True)
	return res

@frappe.whitelist()
def get_jinja_data_del_note_item(del_note):
	res = frappe.db.sql("""
	select 
		A.item_code,A.item_name,A.batch_no,A.stock_uom,A.stock_qty,B.free_qty,B.outgoing_count,B.incoming_count,B.crate_type
	from 
		`tabDelivery Note Item` A
	right outer Join `tabCrate Count Child` B
	on A.item_code = B.item_code
	where 
		A.parent = %(name)s and B.parent = %(name)s and A.is_free_item = 0 """, {"name": del_note}, as_dict=True)

	dist_itm = frappe.db.sql(""" select distinct(item_code) from `tabDelivery Note Item` where parent = %(name)s """,
							 {'name':del_note})
	for itm in dist_itm:
		obj = frappe.get_doc("Item",itm[0])
		if len(obj.crate) == 0:
			res2 = frappe.db.sql(""" select item_code,item_name,batch_no,stock_uom,sum(stock_qty) as stock_qty
									from `tabDelivery Note Item` where parent = %(name)s and item_code = %(item_code)s""",
								{'name':del_note,'item_code':obj.item_code}, as_dict=True)

			for i in range(0, len(res2)):
				res.append(res2[i])

		else:
			res2 = frappe.db.sql(""" select item_code,item_name,batch_no,stock_uom,sum(stock_qty) as stock_qty
									from `tabDelivery Note Item` where parent = %(name)s and item_code = %(item_code)s""",
								{'name':del_note,'item_code':obj.item_code}, as_dict=True)

			for i in range(0, len(res2)):
				res.append(res2[i])

	return res

@frappe.whitelist()
def get_jinja_data_si_item(del_note,gate_pass):
	
	res=[]
	dist_itm = frappe.db.sql(""" select distinct(item_code) as it from `tabSales Invoice Item`  where parent = %(name)s """,
							 {'name':del_note},as_dict=1)
	for itm in dist_itm:
		obj = frappe.get_doc("Item",itm.get("it"))
		res2 = frappe.db.sql(""" select s.name,si.customer,s.item_code,s.item_name,s.warehouse,s.batch_no,s.uom,sum(s.stock_qty) as stock_qty,
								s.parent,
								Case
								WHEN s.uom = "Crate"
								THEN	
								s.qty
								ELSE 0
								END as crate_issue,Case WHEN s.uom ="Crate" and si.is_return=1
								THEN	
								s.qty
								ELSE 0
								END as crate_return
								from `tabSales Invoice Item` as s Join
								`tabSales Invoice` si On si.name=s.parent
								where s.parent = %(name)s and s.item_code = %(item_code)s and is_free_item = 0""",
							{'name':del_note,'item_code':obj.item_code}, as_dict=True)
		frappe.msgprint(str(res2))

		for i in res2:
			if not i.crate_issue:
				item=frappe.get_doc("Item",i.item_code)
				for k in item.crate:
					if k.warehouse==i.x:
						if (i.stock_qty/k.crate_quantity) > 0:
							i.update({"crate_issue":int(i.stock_qty/k.crate_quantity),
				                   "crate_type":k.crate_type})
			free_qty_list = frappe.db.sql(""" select 
							sum(stock_qty) as qty
						from 
							`tabSales Invoice Item` 
						where
							is_free_item = 1 and warehouse = %(warehouse)s and item_code = %(item_code)s and parent = %(doc_name)s and batch_no = %(batch_no)s""",
							{'warehouse':i.get("warehouse"), 'item_code': obj.item_code,'doc_name': i.get("name"), 'batch_no': i.get("batch_no")},as_dict=1)
			if len(free_qty_list)>0:
				if free_qty_list[0].get("qty"):
					i.update({
						"free_qty":free_qty_list[0].get("qty")
					})
				else:
					i.update({
						"free_qty":0.0
					})
			gate_pass=frappe.get_doc("Gate Pass",gate_pass)
			cratelog=frappe.db.get_value("Crate Log",{"creation":["<=",gate_pass.creation],"customer":i.get("customer"),"crate_type":i.crate_type},["name"],order_by="creation desc")
			if cratelog:
				bal=frappe.get_doc("Crate Log",cratelog)
				i.update({
					"crate_bal":bal.crate_balance
				})
			res.append(i)

	return res

@frappe.whitelist()
def get_crate_bal(gate_pass):
	res=[]
	gate_pass=frappe.get_doc("Gate Pass",gate_pass)
	for j in  gate_pass.crate_summary:
		if j.voucher:
			party = frappe.get_doc("Sales Invoice",j.voucher)
			j.update({"customer_name":party.customer_name,"amount":party.grand_total})
			cratelog=frappe.db.get_value("Crate Log",{"creation":["<=",gate_pass.creation],"customer":party.get("customer")},["name"],order_by="creation desc")
			if cratelog:
				bal=frappe.get_doc("Crate Log",cratelog)
				j.update({
					"crate_bal":bal.crate_balance
				})
			res.append(j)
	return res

@frappe.whitelist()
def get_crate_gate(gate_pass):
	res=[]
	gate_pass=frappe.get_doc("Gate Pass",gate_pass)
	for j in  gate_pass.merge_item:
		x={"creation":["<=",gate_pass.creation],"customer":gate_pass.customer}
		if j.crate_type:
			x.update({"crate_type":j.crate_type})
		cratelog=frappe.db.get_value("Crate Log",x,["name"],order_by="creation desc")
		if cratelog:
			bal=frappe.get_doc("Crate Log",cratelog)
			j.update({
				
				"crate_bal":bal.crate_balance
			})
		res.append(j)
	return res

@frappe.whitelist()
def del_note_total(del_note):
	f_res = []
	res = {}

	supp_qty = frappe.db.sql(""" select sum(stock_qty) as stock_qty  from `tabDelivery Note Item` 
								 where parent = %(name)s and is_free_item = 0""",{'name':del_note},as_dict=True)
	res["stock_qty"] = supp_qty[0]["stock_qty"]

	free_qty = frappe.db.sql(""" select sum(stock_qty) as fre_qty from `tabDelivery Note Item` 
								 where parent = %(name)s and is_free_item = 1""",{'name':del_note},as_dict=True)
	res["fre_qty"] = free_qty[0]["fre_qty"]

	crate_qty = frappe.db.sql(""" select sum(outgoing_count) as crate_qty from `tabCrate Count Child` 
								  where parent = %(name)s """,{'name':del_note},as_dict=True)
	res["crate_qty"] = crate_qty[0]["crate_qty"]

	crate_qty = frappe.db.sql(""" select item_code,warehouse,sum(stock_qty) as stock_qty,Case
								WHEN uom = "Crate"
								THEN	
								qty
								ELSE 0
								END as crate_qty from `tabSales Invoice Item` 
								  where parent = %(name)s """,{'name':del_note},as_dict=True)
	x=[]
	for i in crate_qty:
		if i.crate_qty==0:
		
			item=frappe.get_doc("Item",i.item_code)
			for k in item.crate:
				if k.warehouse==i.warehouse:
					if (i.stock_qty/k.crate_quantity) >1:
						x.append(int(i.stock_qty/k.crate_quantity))
		else:
			x.append(i.crate_qty)

	if len(x)>1:
		res["crate_qty"] = sum(x)
	if len(x)==1:
		res["crate_qty"] = x[0]



	f_res.append(res)
	return f_res

@frappe.whitelist()
def si_note_total(del_note):
	f_res = []
	res = {}

	supp_qty = frappe.db.sql(""" select sum(stock_qty) as stock_qty  from `tabSales Invoice Item` 
								 where parent = %(name)s and is_free_item = 0""",{'name':del_note},as_dict=True)
	res["stock_qty"] = supp_qty[0]["stock_qty"]

	free_qty = frappe.db.sql(""" select sum(stock_qty) as fre_qty from `tabSales Invoice Item` 
								 where parent = %(name)s and is_free_item = 1""",{'name':del_note},as_dict=True)
	res["fre_qty"] = free_qty[0]["fre_qty"]

	crate_qty = frappe.db.sql(""" select item_code,warehouse,stock_qty as stock_qty,uom ,qty as crate_qty from `tabSales Invoice Item` 
								  where parent = %(name)s """,{'name':del_note},as_dict=True)
	print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^",crate_qty)
	x=[]
	for i in crate_qty:
		
		if i.uom=="Crate":
			x.append(i.crate_qty)
			
		else:
			item=frappe.get_doc("Item",i.item_code)
			for k in item.crate:
				if k.warehouse==i.warehouse:
					if (i.stock_qty/k.crate_quantity) >1:
						x.append(int(i.stock_qty/k.crate_quantity))
	print(x)
	if len(x)>1:
		res["crate_qty"] = sum(x)
	if len(x)==1:
		res["crate_qty"] = x[0]



	f_res.append(res)
	return f_res

@frappe.whitelist()
def total_supp_qty_based_on_itm_grp(gate_pass):
	itm_grp = frappe.db.sql(""" select item_group_name from `tabItem Group` where is_total_supplier_quantity_item_group_ = 1 """,as_dict=True)
	if itm_grp:
		based_itm_grp =  itm_grp[0]['item_group_name']
		if total_qty:
			total_qty = frappe.db.sql(""" select sum(total_weight) from `tabMerge Gate Pass Item` where parent = %(gate_pass)s and 
	 								item_group = %(item_group)s """,{'gate_pass':gate_pass,'item_group':based_itm_grp})
			final_total_qty = total_qty[0][0]

			return final_total_qty

@frappe.whitelist()
def warehouse_address(warehouse):
	lst = []
	org_warehouse = warehouse
	address =  frappe.db.sql(""" select address_line_1, address_line_2, city, state, pin, phone_no, mobile_no 
	 				from `tabWarehouse` where name = '{0}' """.format(org_warehouse),as_dict=True)
	if address:
		add = ''
		for f in ['address_line_1', 'address_line_2', 'city', 'state', 'pin']:
			if address[0][f]:
				add += address[0][f] + " "
		lst.append(add)
		cont = ''
		for f in ['phone_no', 'mobile_no']:
			if address[0][f]:
				cont += address[0][f] + "  "
		lst.append(cont)
		return lst


@frappe.whitelist()
def get_purchase(pr):
	doc=frappe.get_doc("Purchase Invoice",pr)
	dlst=[]
	for j in doc.items:
		h={}
		pr_item=frappe.get_doc("Purchase Receipt",j.purchase_receipt)
		milk = frappe.get_doc('Milk Entry',pr_item.milk_entry)
		a = (milk.unit_price) - (milk.snf_deduction_per)
		for k in pr_item.items: 
			h.update({"ltr":k.qty,"fat":k.fat_per_,"snf":k.snf_clr_per,"rate":a,"amount":k.amount,"posting_date":format_date(pr_item.posting_date),"shift":pr_item.shift})
		dlst.append(h)
		
	sorted_data = sorted(dlst, key=lambda x: (x["posting_date"], x["shift"].lower() != "morning"))

	return sorted_data


