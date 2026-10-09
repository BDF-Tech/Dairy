from __future__ import unicode_literals


def get_data():
    # Sales Invoice.crate_reconciliation was removed (never filled, and Sales Invoice is at the
    # MariaDB row-size limit on v16), so there are no linked transactions to show.
    return {"fieldname": "crate_reconciliation", "transactions": []}
