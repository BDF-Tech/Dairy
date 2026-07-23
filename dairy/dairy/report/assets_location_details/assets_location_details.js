frappe.query_reports["Assets location details"] = {
    "filters": [
        {
            "fieldname": "location",
            "label": "Location",
            "fieldtype": "Link",
            "options": "Location"
        },
        {
            "fieldname": "asset_category",
            "label": "Asset Category",
            "fieldtype": "Link",
            "options": "Asset Category"
        }
    ]
};
