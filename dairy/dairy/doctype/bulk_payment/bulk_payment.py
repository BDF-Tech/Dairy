# Copyright (c) 2023, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
import csv
import io
import random

import frappe
import json

from frappe.utils.data import format_date

class BulkPayment(Document):
	@frappe.whitelist()
	def get_data(self):
		filters={}
		if self.from_date and self.to_date:
			filters.update({"posting_date":["between",[self.from_date,self.to_date]]})
		if self.mode_of_payment:
			filters.update({"mode_of_payment":self.mode_of_payment})
		if self.party_type:
			filters.update({"party_type":self.party_type})
		filters.update({"docstatus":0})

		f =frappe.get_all('Payment Entry',filters,["*"])
		self.items=[]
		for d in f:
			bank_account_no= frappe.db.get_value("Bank Account",d.party_bank_account,"bank_account_no")
			branch_code=frappe.db.get_value("Bank Account",d.party_bank_account,"branch_code")
			bank=frappe.db.get_value("Bank Account",d.party_bank_account,"bank")

			self.append("items",{
				"bank_account_no":bank_account_no,
				"paid_amount":d.paid_amount,
				"party_name":d.party_name,
				"posting_date":d.posting_date,
				"ifsc":branch_code,
				"bank":bank
			})
	@frappe.whitelist()
	def get_lines(self):
		a = 0
		l =[]
		filters={}
		if self.from_date and self.to_date:
			filters.update({"posting_date":["between",[self.from_date,self.to_date]]})
		# ÷
		# 	filters.update({"posting_date":["<=",self.to_date]})
		if self.mode_of_payment:
			filters.update({"mode_of_payment":self.mode_of_payment})
		if self.party_type:
			filters.update({"party_type":self.party_type})
		filters.update({"docstatus":0})
		f =frappe.get_all('Payment Entry',filters,["*"])
		for d in self.items:
			branch_code=frappe.db.get_value("Bank Account",{"bank_account_no":d.bank_account_no},"branch_code")
			bank=frappe.db.get_value("Bank Account",{"bank_account_no":d.bank_account_no},"bank")

			a = a+1
			x =[]
			x.append("N")
			x.append("           ")
			x.append(str(d.bank_account_no))
			x.append(d.paid_amount)
			x.append(d.party_name)
			x.append("           ")
			x.append("           ")
			x.append("           ")
			x.append("           ")
			x.append("           ")
			x.append("           ")
			x.append("           ")
			pa=str(format_date(d.posting_date))
			pb=str(format_date(d.posting_date))
			x.append(pa.replace("-","")+ "-"+ str("{:03d}".format(a)))
			x.append(pb.replace("-","")+ "-"+ str("{:03d}".format(a)))
			x.append("           ")
			x.append("           ")
			x.append("           ")
			x.append("           ")
			x.append("           ")
			x.append("           ")
			x.append("           ")
			x.append("           ")
			c=str(format_date(d.posting_date))
			x.append(str(c.replace("-","/")))
			x.append("           ")
			x.append(branch_code)
			x.append(bank)
			x.append("           ")
			x.append("bastardairyfarm@gmail.com")
			l.append(x)


		doc=frappe.get_doc("Dairy Settings")
		path = doc.file_path_download_csv
		# ran = random.randint(0,9999999999)
		full_name = path + str(self.name) +".csv"


		with open(full_name, 'w') as file:
			field = ["name", "creation"]
			writer = csv.writer(file)
			# writer.writerow(field)
			for row in  l:
				writer.writerow(row)					

    
@frappe.whitelist(allow_guest=True)
def get_download(name):
	doc=frappe.get_doc("Dairy Settings")
	with open(str(doc.file_path_download_csv)+str(name)+".csv",'rb') as f:
		file=f.read()
		frappe.local.response.filename = str(name)+".csv"
		frappe.local.response.filecontent = file
		frappe.local.response.type = "download"
		

            







    


























































