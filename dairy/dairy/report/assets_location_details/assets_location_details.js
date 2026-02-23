frappe.query_reports["Assets Location Report"] = {
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
