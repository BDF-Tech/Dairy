frappe.ui.form.on("Sales Invoice", {
    refresh: function(frm) {
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
        // frm.set_df_property("crate_count", "hidden",1);
        // frm.set_df_property("loose_crate_", "hidden",1);

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
    after_save:function(frm){
        if(frm.doc.custom_crate_calculate==0){
            frm.set_value("custom_crate_calculate",1)
            frm.refresh_field("custom_crate_calculate")
            frm.save()
        }
    },
    // before_submit:function(frm){
    //     frm.call({
    //         method:"dairy.milk_entry.custom_sales_invoice.calculate_crate_save",
    //         args: {
    //                 name:frm.doc.name
    //               },
    //         callback: function(r)
    //             {
    //                 // $.each(r.message, function(index, row)
    //                 // {   
                       
    //                 // });
    //                 frm.set_value("crate_count",r.message)
    //                frm.refresh_fields("crate_count")
    //             //    frm.save()
    //             }
    //         });
    // },
    update_party_balance: function(frm){
		frappe.call({
			method:'dairy.milk_entry.custom_sales_invoice.get_party_bal',
            args:{
                customer:frm.doc.customer,
                company:frm.doc.company
            },
			callback: function(r) {
				if (r.message){

					frm.set_value("party_balance", r.message)
					frm.refresh_field("party_balance")
				}
			}
		})
	},
    before_save:function(frm,cdt,cdn){
        var d = locals[cdt][cdn];
        console.log(d);
        $.each(d.items, function(index, row)
        {   
            var a = ((row.amount)/row.total_weight) 
            row.rate_of_stock_uom=a;
            console.log("Rate of stock uom",a)
            frm.refresh_field("rate_of_stock_uom")
        });
        if(!frm.doc.__islocal && !frm.doc.is_return){
        frm.call({
            method:"dairy.milk_entry.custom_sales_invoice.calculate_crate_save",
            args: {
                    name:frm.doc.name
                  },
            callback: function(r)
                {
                    // $.each(r.message, function(index, row)
                    // {   
                       
                    // });
                    frm.set_value("crate_count",r.message)
                   frm.refresh_fields("crate_count")
                //    frm.save()
                }
            });
        }
        // frm.set_df_property("crate_count", "hidden",0);
        // frm.set_df_property("loose_crate_", "hidden",0);
        // cur_frm.reload_doc();
      
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
                    frm.refresh_field("route")
                    //  frm.set_value("selling_price_list",r.message.p_list);
                    //  frm.refresh_field("selling_price_list")

                   }
                }
        });
    },
    route:function(frm){
        frm.add_fetch("route", "transporter", "transporter");
	         return cur_frm.call({
            method:"dairy.milk_entry.custom_sales_order.set_territory",
            args: {

                  },
            callback: function(r)
                {
                   if(r.message)
                   {
                    console.log(r.message);
                    if(r.message == "Route"){
                        frm.set_value("territory",frm.doc.route_territory);
                    }
                   }
                }
        });
    
    },

    // customer: function(frm){
        
    // },
   
})

frappe.ui.form.on("Sales Invoice Item", {
	item_code: function(frm,cdt,cdn) {
		var row = locals[cdt][cdn];
		frm.call({
            method:"dairy.milk_entry.custom_sales_order.defsellinguom",
            args: {
                    doc_name: row.item_code
                  },
            callback: function(r)
                {
                   if(r.message)
                   {
                    var array = r.message
                    if (array != 1){
                    row.uom = array["uom"];
                    row.conversion_factor = array["conversion_factor"];
                    }
                   }
                }
        });
	},

    fat: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
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
            frappe.model.set_value(cdt, cdn, "snf_clr_per", per);
        }
	},

    snf_clr_per: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        if(d.snf_clr_per){
            var weight = d.total_weight
            var snf_clr = ((d.snf_clr_per / 100) * weight)
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
                    

            
                if(d.snf_clr_per){
                    var weight = d.total_weight
                    var snf_clr = ((d.snf_clr_per / 100) * weight)
                    frappe.model.set_value(cdt, cdn, "snf_clr", snf_clr);
                }
                

                
                if(d.fat_per){
                    var weight = d.total_weight
                    var fat = ((d.fat_per / 100) * weight)
                    frappe.model.set_value(cdt, cdn, "fat", fat);
                }
            })           
		}
	}
});
