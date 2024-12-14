// Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Route Master', {
	 refresh: function(frm){
	    frappe.dynamic_link = {doc: frm.doc, fieldname: 'name', doctype: 'Route Master'};
	    frm.toggle_display(['vehicle_html','address_html'], !frm.doc.__islocal);
		if(!frm.doc.__islocal)
		{
			dairy.vehicle_dynamic_link.render_vehicle_and_customer(frm);
			frappe.contacts.render_address_and_contact(frm);

		}
		else
		{
			dairy.vehicle_dynamic_link.clear_vehicle_and_customer(frm);
			frappe.contacts.clear_address_and_contact(frm);
		}
	 },
	 onload: function(frm){
        frm.set_query('dest_warehouse', function(doc) {
            return {
                filters: {
                    "is_dcs":0,
                    "is_group":0,
                    "company":frappe.defaults.get_user_default("Company"),
                    "disabled":0
                }
            };
        });
        frm.set_query('source_warehouse', function(doc) {
            return {
                filters: {
                    "is_dcs":0,
                    "is_group":0,
                    "company":frappe.defaults.get_user_default("Company"),
                    "disabled":0
                }
            };
        });


        frm.set_query('driver', function(doc) {
            return {
                filters: {
                    "status":["=","Active"]
                }
            };
        });

        frm.set_query('transporter', function(doc) {
            return {
                filters: {
                    "is_transporter":1
                }
            };
        });

        frm.trigger('set_property');

    },
    set_property: function(frm) {
         if(frm.doc.route_type =="Buying")
         {
            frm.set_df_property("dest_warehouse", "reqd", 1);
            frm.set_df_property("dest_warehouse", "hidden",0);

            frm.set_df_property("source_warehouse", "reqd", 0);
            frm.set_df_property("source_warehouse", "hidden",1);

            frm.set_df_property("price_list", "reqd", 0);
            frm.set_df_property("price_list", "hidden",1);

            frm.set_df_property("customer", "reqd", 0);
            frm.set_df_property("customer", "hidden",1);
         }
         else
         {
            frm.set_df_property("dest_warehouse", "reqd", 0);
            frm.set_df_property("dest_warehouse", "hidden",1);

            frm.set_df_property("source_warehouse", "reqd", 1);
            frm.set_df_property("source_warehouse", "hidden",0);

            // frm.set_df_property("price_list", "reqd", 1);
            // frm.set_df_property("price_list", "hidden",0);

            frm.set_df_property("customer", "reqd", 1);
            frm.set_df_property("customer", "hidden",0);
         }
         if(frm.doc.route_type == "Milk Procurement"){
            frm.set_df_property("price_list", "reqd", 0);
            // frm.set_df_property("price_list", "hidden",1);

            frm.set_df_property("source_warehouse", "reqd", 0);
            // frm.set_df_property("source_warehouse", "hidden",1);
         }
         else{
            frm.set_df_property("price_list", "reqd", 1);
            frm.set_df_property("price_list", "hidden",0);
         }
    },
    route_type :function(frm){
        frm.trigger('set_property');
    },

//	refresh: function(frm) {
//	    if (frm.doc.docstatus===1) {
//            frm.add_custom_button(__("Add / Edit Prices"), function() {
//                frappe.route_options = {
//                    "price_list": frm.doc.name
//                };
//                frappe.set_route("Report", "Item Price");
//            }, "fa fa-money");
//		},
//	}




    company : function(frm){
        frm.set_query('source_warehouse', function(doc) {
            return {
                filters: {
                    "company":doc.company,
                }
            };
        });


    }

});
