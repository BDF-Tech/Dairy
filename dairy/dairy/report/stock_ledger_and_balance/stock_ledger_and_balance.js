//Copyright (c) 2025, Sanskar Shukla and contributors
//Please Contact on @Sanskar199(sanskar19shukla@gmail.com)  for more info

frappe.query_reports["Stock ledger and balance"] = {
    filters: [
        {
            fieldname: "from_date",
            label: "From Date",
            fieldtype: "Date",
            default: frappe.datetime.month_start()
        },
        {
            fieldname: "to_date",
            label: "To Date",
            fieldtype: "Date",
            default: frappe.datetime.get_today()
        },
        {
            fieldname: "item_code",
            label: "Item",
            fieldtype: "Link",
            options: "Item"
        },
        {
            fieldname: "warehouse",
            label: "Warehouse",
            fieldtype: "Link",
            options: "Warehouse"
        }
    ]
};



