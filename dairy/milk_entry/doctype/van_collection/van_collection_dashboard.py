from __future__ import unicode_literals
from frappe import _

def get_data():
    return {
        'fieldname': 'van_collection',
        'transactions': [
            {
                'label': _('Stock Entry'),
                'items': ['Stock Entry']
            },
        ]
    }