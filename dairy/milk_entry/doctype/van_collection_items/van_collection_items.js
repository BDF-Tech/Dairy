// Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt
frappe.ui.form.on('Van Collection Items', {
	on_submit: function (frm) {
		frm.call({
			method:'creatr_stock',//function name defined in python
			doc: frm.doc, //current document
		});
	}
});



frappe.ui.form.on('Van Collection Items', {
	 after_save: function(frm) {
	    if(frm.doc.__islocal)
	    {
	         cur_frm.cscript.calculate_milk_cans()
	    }
        frm.set_df_property("cow_milk_collected", "read_only", frm.is_new() ? 0 : 1);
        frm.set_df_property("buffalow_milk_collected", "read_only", frm.is_new() ? 0 : 1);
        frm.set_df_property("mix_milk_collected", "read_only", frm.is_new() ? 0 : 1);
	 },
	 cow_milk_collected: function(frm) {
        if(frm.doc. cow_milk_collected){
	     cur_frm.cscript.calculate_milk_cans()
        }
	 },
	 buffalow_milk_collected: function(frm) {
        if(frm.doc. buffalow_milk_collected){
	     cur_frm.cscript.calculate_milk_cans()
        }
	 },
	 mix_milk_collected: function(frm) {
        if(frm.doc. mix_milk_collected){
	     cur_frm.cscript.calculate_milk_cans()
        }
	 },

    
     refresh: function(frm, dt, dn) {
        if(!frm.doc.__islocal && !frm.doc.gate_pass)
        {

            frm.add_custom_button(__('Milk Entry'),function() {
                erpnext.utils.map_current_doc({
                    method: "dairy.milk_entry.doctype.van_collection_items.van_collection_items.get_milk_entry",
                    source_doctype: "Milk Entry",
                    target: frm,
                    date_field: "date",
                    setters: [{
						fieldtype: 'Link',
						label: __('DCS'),
						options: 'Warehouse',
						fieldname: 'dcs_id',
						default: frm.doc.dcs,
					}],
                    get_query_filters: {
                          dcs_id: frm.doc.dcs,
                          shift: frm.doc.shift,
                          date:frm.doc.date,
                          docstatus: 1
                    }
                })
            }, __("Get items from"));

            // frm.add_custom_button(__('Make Gate pass'),function() {
            //     return frappe.call({
            //         doc: frm.doc,
            //         method: 'make_stock_entry',
            //         callback: function(r) {
            //             var doc = frappe.model.sync(r.message);
            //             frappe.set_route("Form", doc[0].doctype, doc[0].name);
            //         }
            //     });
            // }).addClass('btn-primary');
        }
     },
     onload:function(frm){
        frm.set_query('van_collection', function(doc) {
            return {
                filters: {
                    "status":"In-Progress"
                }
            };
        });

        frm.set_query('dcs', function(doc) {
            return {
                filters: {
                     "route": frm.doc.route,
                     "is_dcs": 1
                }
            };
        });
        frm.set_query('buf_milk_sam', function(doc) {
            return {
                filters: {
                     "milk_type": "Buffalo",
                     "dcs": frm.doc.dcs
                }
            };
        });

        frm.set_query('cow_milk_sam', function(doc) {
            return {
                filters: {
                     "milk_type": "Cow"
                }
            };
        });

        frm.set_query('mix_milk_sam', function(doc) {
            return {
                filters: {
                     "milk_type": "Mix"
                }
            };
        });
     }
});

cur_frm.cscript.calculate_milk_cans= function()
 {
      return frappe.call({
            doc: cur_frm.doc,
            method: 'calculate_milk_cans',
            callback: function(r) {
               cur_frm.refresh_fields();
            }
      });
 };