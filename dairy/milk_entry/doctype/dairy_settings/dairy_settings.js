// Copyright (c) 2019, Dexciss Technology by Sid and contributors
// For license information, please see license.txt

frappe.ui.form.on('Dairy Settings', {
    onload: function(frm) {
        frm.trigger('set_property');
        if(frm.doc.__islocal){
            frm.set_value("get_territory","Customer");

        }
        if(! frm.doc.leakage_calculated_on)
        {
        frm.set_value("leakage_calculated_on","Sales Order");
        }

        if(! frm.doc.crate_reconciliation_based_on){
            frm.set_value("crate_reconciliation_based_on","Delivery Note");
        }

    },

    setup:function(frm){
        frm.set_query("item","items_to_add_fat",function(frm){
            return{
                filters:{
                    'maintain_fat_snf_clr' : 1,
                    'disabled' : 0
                }
            }
        }
    ),
    frm.set_query("items_to_remove_snf_fat",function(frm){
        return{
            filters:{
                'maintain_fat_snf_clr' : 1,
                'disabled' : 0
            }
        }
    }
    ),
    frm.set_query("item","items_to_add_snf",function(frm){
        return{
            filters:{
                'maintain_fat_snf_clr' : 1,
                'disabled' : 0
            }
        }
    }
    )

    },

       
  
    set_property: function(frm) {
        
         if(frm.doc.default_payment_type =="Days")
         {
            frm.set_df_property("days", "reqd", 1);
            
         }
         else
         {
            frm.set_df_property("days", "reqd", 0);
         }
         
    },
    default_payment_type :function(frm){
        

        frm.trigger('set_property');
        
    },
	validate: function(frm) {
		if(frm.doc.max_allowed > frm.doc.can_volume)
		{
			frappe.throw(__(" 'Max Allowed Capacity' should be equal to or less than 'Can Volume' "));
		}
		if(frm.doc.default_payment_type =="Days" && frm.doc.days ==0)
		{
		    frappe.throw(__("Set Days greater than the Zero!"));
		}
	},
    refresh : function(frm){
        frm.add_custom_button(__('Custom Payment'),function() {
            return frappe.call({
                method: 'custom_po',
                doc: frm.doc,
                callback: function(r) {
            }
        })
        });
    }
});