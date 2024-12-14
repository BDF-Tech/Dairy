# -*- coding: utf-8 -*-
# Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from dairy.vehicle_dynamic_link import load_vehicle_dynamic_link
from frappe.contacts.address_and_contact import load_address_and_contact

class RouteMaster(Document):
	pass
	def onload(self):
		"""Load address and contacts in `__onload`"""
		load_vehicle_dynamic_link(self)
		load_address_and_contact(self)
