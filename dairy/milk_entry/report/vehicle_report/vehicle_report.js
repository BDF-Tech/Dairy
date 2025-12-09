frappe.query_reports["Vehicle Report"] = {
    "filters": [
        {
            "fieldname": "vehicle",
            "label": "Vehicle No",
            "fieldtype": "Link",
            "options": "Vehicle",
            "reqd": 0
        },
        {
            "fieldname": "type",
            "label": "Vehicle Type",
            "fieldtype": "Select",
            "options": "\nTanker\nTempo\nTruck\nOther",
            "default": ""
        },
        {
            "fieldname": "make",
            "label": "Make",
            "fieldtype": "Select",
            "options": "\nTata\nMahindra\nAshok Leyland\nOther",
            "default": ""
        },
        {
            "fieldname": "entry_type",
            "label": "Entry Type",
            "fieldtype": "Select",
            "options": "\nFuel Refill\nService\nPUC\nFitness\nInsurance",
            "default": ""
        }
    ]
};
