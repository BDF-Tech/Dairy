from __future__ import unicode_literals

from frappe import _

def get_data():
    return {
        'fieldname': 'order_book',
        'transactions': [
            {
                'label': _('Sale Order'),
                'items': ['Sale Order']
            }
        ]
    }