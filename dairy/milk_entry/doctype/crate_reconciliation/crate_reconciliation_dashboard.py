from __future__ import unicode_literals
from frappe import _

def get_data():
    return {
        'fieldname': 'crate_reconciliation',
        'transactions': [
            {
                'label': _('Sales Invoice'),
                'items': ['Sales Invoice']
            },
        ]
    }