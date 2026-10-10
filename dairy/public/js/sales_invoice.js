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

