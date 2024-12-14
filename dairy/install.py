from __future__ import print_function, unicode_literals
import frappe

def after_install():
    if not frappe.db.exists("Domain", "Dairy"):
        frappe.db.sql("""INSERT INTO `tabDomain` (name, domain) VALUES ('Dairy', 'Dairy')""")

