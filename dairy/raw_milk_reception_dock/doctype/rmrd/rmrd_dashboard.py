from __future__ import unicode_literals
from frappe import _

def get_data():
    return {
        'fieldname': 'rmrd',
        'transactions': [
            {
                'label': _('RMRD Lines'),
                'items': ['RMRD Lines']
            },
            {
                'label': _('Stock Entry'),
                'items': ['Stock Entry']
            },
        ]
    }