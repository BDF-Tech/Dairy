from __future__ import unicode_literals

from frappe import _

def get_data():
	return {
		'fieldname': 'milk_entry',
		'transactions': [
			{
				'label': _('Raw Milk Sample'),
				'items': ['Raw Milk Sample']
			},
			{
				'label': _('Purchase Receipt'),
				'items': ['Purchase Receipt']
			},
		]
	}
