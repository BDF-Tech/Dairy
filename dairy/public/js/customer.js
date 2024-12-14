// Copyright (c) 2016, Frappe Technologies and contributors
// For license information, please see license.txt

frappe.ui.form.on("Customer", {
    onload: function(frm){
        frm.set_query('route', function(doc) {
            return {
                filters: {
                    "company":doc.company,
                    "route_type":"Milk Marketing",
                    // "docstatus":1
                }
            };
        });
    },
    refresh: function(frm,cdt,cdn){
        frm.fields_dict['links'].grid.get_field('link_name').get_query = function(doc, cdt, cdn) {
            var child = locals[cdt][cdn]
            return {    
                filters:[
                    ['docstatus', '!=', 2]
                   
                ]
            }

        }
    }
});
