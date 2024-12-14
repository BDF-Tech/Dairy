from __future__ import unicode_literals
from frappe import _

def get_data():
	return [
        {
          "label": _("Reports"),
            "icon": "fa fa-table",
            "items": [
                {
                    "type": "report",
                    "is_query_report": True,
                    "name": "Milk Entry Detail",
                    "reference_doctype": "Milk Entry",
                    "onboard": 1
                },
                {
                    "type": "report",
                    "is_query_report": True,
                    "name": "Vehicle Wise Crate Summary",
                    "reference_doctype": "Delivery Note",
                    "onboard": 1
                },
                {
                    "type": "report",
                    "is_query_report": True,
                    "name": "Sales Analysis",
                    "reference_doctype": "Sales Order",
                    "onboard": 1
                }
            ]
        }
    ]