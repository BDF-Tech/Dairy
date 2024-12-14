// Copyright (c) 2019, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt
frappe.ui.form.on("Milk Entry", {
    click_refresh: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        var total = 0;
        if(d.contracted_qty >= 0 && d.local_transp_dpds_fob >= 0){
        total = ((d.local_transp_dpds_fob / d.contracted_qty)).toFixed(2);
        frm.set_value('local_transp_dpds', total);
        }
    }
});


frappe.ui.form.on('Milk Entry', {
	get_quality: function (frm) {
		frm.call({
			method: 'get_quality',//function name defined in python
			doc: frm.doc, //current document
		});
	}
});

frappe.ui.form.on('Milk Entry', {
	get_weight: function (frm) {
		frm.call({
			method: 'get_weight',//function name defined in python
			doc: frm.doc, //current document
		});
	}
});

frappe.ui.form.on('Milk Entry', {
    member: function (frm) {
        frm.call({
            method: 'get_dcs', // function name defined in Python
            doc: frm.doc, // current document
            callback: function(r) {
                if (r.message) {
                    frm.set_value('dcs_id', r.message.dcs_id);
                    refresh_field('dcs_id');
                }
            }
        });
    }
});



frappe.ui.form.on('Milk Entry', {
    onload: function(frm){
        frm.set_query('dcs_id', function(doc) {
            return {
                filters: {
                    "is_dcs":1,
                    "is_group":0,
                    "company":frappe.defaults.get_user_default("Company"),
                    "disabled":0,
                    
                }
            };
        });
        return frm.call('stock_data').then(() => {
            frm.refresh();

        });

    },
 
    validate: function(frm) {

        if(!frm.doc.dcs_id) {
            frappe.throw(__('Please provide DCS.'));
        }
        if(!frm.doc.member) {
            frappe.throw(__('Please provide Member.'));
        }

        if(!frm.doc.volume) {
            frappe.throw(__('Please provide Volume.'));
        }
        if(!frm.doc.fat) {
            frappe.throw(__('Please provide FAT.'));
        }
        // if(!frm.doc.clr) {
        //     frappe.throw(__('Please provide CLR.'));
        // }

        if(frm.doc.volume <= 0) {
            frappe.throw(__('Milk Volume less than or equal to zero is not allowed.'));
        }
        if(frm.doc.fat <= 0) {
            frappe.throw(__('Milk FAT less than or equal to zero is not allowed.'));
        }
        // if(frm.doc.clr <= 0) {
        //     frappe.throw(__('Milk CLR less than or equal to zero is not allowed.'));
        // }
    },

    dcs_id: function(frm) {
    
        frm.set_query('member', function(doc) {
            return {
                filters: {
                    "dcs_id": doc.dcs_id,
                }
            };
        });

    },

    refresh: function(frm) {
         if (frm.doc.status=='Draft' && frm.doc.member != undefined)
         {
            frm.add_custom_button(__('Accounting Ledger'), function () {
				frappe.set_route('query-report', 'General Ledger',
					{ party_type: 'Supplier', party: frm.doc.member,'company':frm.doc.company });
			}, __("View"));

			frm.add_custom_button(__('Accounts Payable'), function () {
				frappe.set_route('query-report', 'Accounts Payable',
				{supplier: frm.doc.member,'company':frm.doc.company });
			}, __("View"));

         }
        if (frm.doc.status=="To Bill" || frm.doc.status=="Submitted" || frm.doc.status=="To Sample" || frm.doc.status=="To Post and Sample") {
            frappe.model.with_doc("Warehouse",frm.doc.dcs_id, () => {
                let dcs = frappe.model.get_doc("Warehouse",frm.doc.dcs_id);
                let is_collector = dcs.sample_collector
                if (is_collector == 1) {
                    frm.add_custom_button(__('Raw Milk Sample'), function () {
                        frappe.model.open_mapped_doc({
                            method: "dairy.milk_entry.doctype.milk_entry.milk_entry.create_raw_sample",
                            frm: cur_frm,
                        })
                    }, __('Create'));
                }

                // if (frm.doc.docstatus == 1 && is_collector == 0){
                //     frm.doc.status=="To Sample and Bill"
                // }
                


            });
//            frm.add_custom_button(__('Purchase Receipt'),function() {
//                return frappe.call({
//                    doc: frm.doc,
//                    method: 'create_purchase_receipt',
//                    callback: function(r) {
//                        var doc = frappe.model.sync(r.message);
//                        frappe.set_route("Form", doc[0].doctype, doc[0].name);
//                    }
//                });
//            },__('Create'));
            frm.page.set_inner_btn_group_as_primary(__('Create'));
        }
        if(frm.doc.__islocal){
            let currentDate = new Date();
            let time = currentDate.getHours() + ":" + currentDate.getMinutes() + ":" + currentDate.getSeconds();
            frm.set_value("time",time)
        }

        // frappe.db.get_value("Van Collection",frm.doc.date,["status"]).then((r) => {
		// 		console.log('status^^^^^^^^^^^^^^^^^^',r.status)
		// 		if(r.status == "Completed"){
		// 			frm.set_df_property("van_collection_completed","hidden",0)
		// 		}
        //             frm.set_df_property("van_collection_completed","hidden",1)
		// })

    },
    // before_save: function(frm) {
    //     return frm.call('get_pricelist').then(() => {
    //         frm.refresh();

    //     });
    // },
    // on_submit: function(frm){
    //     cur_frm.cscript.submit_purchase_rec()
    //     frappe.model.get_value('Dairy Settings', {'name': 'Dairy Settings'}, 'auto_print_milk_receipt', function(d)
    //     {
    //         if(d.auto_print_milk_receipt == 1)
    //         {
                
    //             // frappe.set_route('List',"Print Format","");
    //             frm.print_doc('Milk Entry Invoice');
    //         }
    //     });
    // }
});

cur_frm.cscript.submit_purchase_rec = function(){
    return frappe.call({
        doc: cur_frm.doc,
        method: 'create_purchase_receipt',
        callback: function(r) {
            cur_frm.refresh();
            // frappe.call({
            //     method: 'dairy.milk_entry.doctype.dairy_settings.dairy_settings.purchase_invoice',
            //     // args:{'name':frm.doc.name,'dsc_id':frm.doc.dcs_id,'member':frm.doc.member}
            //     // args: {employee: frm.doc.employee, fieldname: property},
            // });
        }
    });

}