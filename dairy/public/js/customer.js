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
    food_license_number: function(frm) {
        // Instant feedback; the hard check is server-side (custom_customer.validate_food_license)
        let val = (frm.doc.food_license_number || '').replace(/[\s-]/g, '');
        if (val !== frm.doc.food_license_number) {
            frm.set_value('food_license_number', val);
            return;
        }
        if (val && !/^[12]\d{13}$/.test(val)) {
            frappe.show_alert({
                message: __('FSSAI number must be 14 digits starting with 1 or 2 — you entered {0}.', [val.length]),
                indicator: 'red',
            }, 7);
        }
    },
    refresh: function(frm,cdt,cdn){
        frm.set_df_property('food_license_number', 'description',
            __('14-digit FSSAI number, starting with 1 (Licence) or 2 (Registration)'));
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
