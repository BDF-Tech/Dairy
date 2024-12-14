frappe.ui.form.on("Delivery Note", {
    setup: function(frm) {
		frm.add_fetch("route", "source_warehouse", "set_warehouse");
		// frm.add_fetch("route", "price_list", "selling_price_list");
		frm.add_fetch("route", "transporter", "transporter");
	},
    after_save:function(frm,cdt,cdn){
        var d = locals[cdt][cdn];
        $.each(d.items, function(index, row)
        {   
            var a = ((row.amount)/row.total_weight) 
            row.rate_of_stock_uom=a;
            let amt = frm.snf_clr_rate * d.fat
            row.fat_amount = amt
            frm.refresh_field('fat_amount')
            frm.refresh_field("rate_of_stock_uom")
        });
    },
//	calculate_crate: function(frm){
//	console.log("******************************************");
////	    cur_frm.cscript.calculate_crate()
//	    frm.call({
//        method:"dairy.milk_entry.custom_delivery_note.calculate_crate",
//        args: {
//                doc: cur_frm
//              },
//        callback: function(r)
//            {
//               cur_frm.reload_doc();
//            }
//        });
//
//	},
	refresh: function(frm){
        if (frm.doc.docstatus==1) {
				frm.remove_custom_button("Delivery Trip", 'Create');
			}
        frm.add_custom_button(__("Milk Ledger"), function() {
            frappe.route_options = {
                voucher_no: frm.doc.name,
                from_date: frm.doc.posting_date,
                to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
                company: frm.doc.company
            };
            frappe.set_route("query-report", "Milk Ledger");
            }, __("View"));
	},
	onload: function(frm){
	    if(frm.doc.__islocal){
//	         frm.set_df_property("calculate_crate", "hidden",1);
	         frm.set_df_property("crate_count", "hidden",1);
	         frm.set_df_property("loose_crate_", "hidden",1);
	    }
	    frm.trigger('set_property');
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


    after_save: function(frm){
            frm.set_df_property("crate_count", "hidden",0);
	        frm.set_df_property("loose_crate_", "hidden",0);
	        cur_frm.reload_doc();
      },

	customer:function(frm){
        frappe.call({
            method: 'dairy.milk_entry.doctype.bulk_milk_price_list.bulk_milk_price_list.fetch_data',
            args: {
                'doctype': 'Bulk Milk Price List',
                'customer': frm.doc.customer
            },
            callback: function(r) {
                if (!r.exc) {
                    // code snippet
                    frm.set_value('fat_rate', r.message.rate)
                    frm.set_value('snf_clr_rate', r.message.snf)
                }
            }
        });
        return cur_frm.call({
            method:"dairy.milk_entry.custom_delivery_note.get_route_price_list",
            args: {
                    doc_name: cur_frm.doc.customer
                  },
            callback: function(r)
                {
                   if(r.message)
                   {
                    frm.set_value("route",r.message.route);
                    //  frm.set_value("selling_price_list",r.message.p_list);
                     frm.set_value("set_warehouse",r.message.warehouse);
                   }
                }
        });
    },

    route: function(frm){
        frm.add_fetch("route", "transporter", "transporter");
    },

    // customer: function(frm){
    //     frappe.call({
    //         method: 'dairy.milk_entry.doctype.bulk_milk_price_list.bulk_milk_price_list.fetch_data',
    //         args: {
    //             'doctype': 'Bulk Milk Price List',
    //             'customer': frm.doc.customer
    //         },
    //         callback: function(r) {
    //             if (!r.exc) {
    //                 // code snippet
    //                 frm.set_value('fat_rate', r.message.rate)
    //                 frm.set_value('snf_clr_rate', r.message.snf)
    //             }
    //         }
    //     });
    // }
});
 
frappe.ui.form.on("Delivery Note Item", {
//    item_code: function(frm,cdt,cdn){
//        let item = locals[cdt][cdn]
//        frappe.call({
//            method: "dairy.milk_entry.doctype.bulk_milk_price_list.bulk_milk_price_list.fetch_snf_and_fat",
//            args: {
//                "item": item.item_code,
//                "customer": frm.doc.customer
//            },
//            callback: function(resp){
//                if(resp.message){
//                    let d = resp.message
//
//                    item.fat_amount = d.rate * item.fat
//                    item.snf_clr_amount = d.snf_clr_rate * item.snf_clr
//                    frm.refresh_field('fat_amount')
//                    frm.refresh_field('snf_clr_amount')
//                }
//            }
//        })
//    }

    fat: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        console.log("--------------fat------------")
        if(d.fat){
            var weight = d.total_weight
            var per = ((d.fat / weight) * 100)
            frappe.model.set_value(cdt, cdn, "fat_per", per);
        }
    },

    fat_per: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        if(d.fat_per){
            var weight = d.total_weight
            var fat = ((d.fat_per / 100) * weight)
            frappe.model.set_value(cdt, cdn, "fat", fat);
        }
    },

    snf_clr: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        if(d.snf_clr){
            var weight = d.total_weight
            var per = ((d.snf_clr / weight) * 100)
            frappe.model.set_value(cdt, cdn, "clr_per", per);
        }
    },

    clr_per: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        if(d.clr_per){
            var weight = d.total_weight
            var snf_clr = ((d.clr_per / 100) * weight)
            frappe.model.set_value(cdt, cdn, "snf_clr", snf_clr);
        }
    },

    snf_per: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        if(d.snf_per){
            var weight = d.total_weight
            var snf = ((d.snf_per / 100) * weight)
            frappe.model.set_value(cdt, cdn, "snf", snf);
        }
    },

    snf: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        if(d.snf){
            var weight = d.total_weight
            var s_per = ((d.snf / weight) * 100)
            frappe.model.set_value(cdt, cdn, "snf_per", s_per);
            
            
        }
    },

    qty : function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        if(d.qty){
            frappe.db.get_value("Item", d.item_code, ["weight_per_unit"]).then((r) => {
                console.log('rrrrrrrrrrrrrrrrrrrrr',r.message,d.qty)
        
                if(d.snf_per){
                    var weight = d.total_weight
                    var snf = ((d.snf_per / 100) * weight)
                    console.log('snffffffffffffffffffff',snf)
                    frappe.model.set_value(cdt, cdn, "snf", snf);
                }
                    

            
                if(d.clr_per){
                    var weight = d.total_weight
                    var snf_clr = ((d.clr_per / 100) * weight)
                    frappe.model.set_value(cdt, cdn, "snf_clr", snf_clr);
                }
                

                
                if(d.fat_per){
                    var weight = d.total_weight
                    var fat = ((d.fat_per / 100) * weight)
                    frappe.model.set_value(cdt, cdn, "fat", fat);
                }
            })           
        }
    },

})

