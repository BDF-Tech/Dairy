from frappe import _


def get_data():
    return {
        "fieldname": "crate_delivery",
        "transactions": [
            {
                "label": _("Crate Ledger"),
                "items": ["Customer Crate Ledger"],
            },
        ],
    }
