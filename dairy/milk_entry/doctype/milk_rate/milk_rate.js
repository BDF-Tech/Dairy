// Copyright (c) 2019, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Milk Rate', {
    setup:function(frm){
        frm.set_query('dsc_name', function(doc) {
            return {
                filters: {
                    "is_dcs":1,
                    "is_group":0
                }
            };
        });
           
    },
	milk_type: function(frm) {
        if(!frm.doc.simplified_milk_rate){
	    return frm.call('get_snf_lines').then(() => {
            frm.refresh_field('milk_rate_chart');
        });
    }
	},
	onload(frm) {
        if(frm.doc.__islocal && !frm.doc.simplified_milk_rate) {
            return frm.call('get_snf_lines').then(() => {
                frm.refresh_field('milk_rate_chart');
            });
        }
    },
    validate: function(frm) {
        if(!frm.doc.milk_rate_chart && !frm.doc.simplified_milk_rate) {
            frappe.throw(__('Cant Submit without Rate Chart.'));
        };
        // if(frm.doc.simplified_milk_rate == 1){
        //     frm.set_df_property('milk_rate_chart', 'hidden', 0);
        // }
    },
    // refresh:function(frm){
    //     if(frm.doc.simplified_milk_rate == 1){
    //         frm.set_df_property(frm.doc.milk_rate_chart, 'hidden', 1);
    //     }
    //     else{
    //         frm.set_df_property(frm.doc.milk_rate_chart, 'hidden', 0); 
    //     }
    // },

    before_submit : function (frm) {
        if(frm.doc.simplified_milk_rate == 0){
            for(let i in frm.doc.milk_rate_chart){
                if (frm.doc.milk_rate_chart[i].rate <= 0){
                    frappe.throw(__('Rate must be greater then zero on row '+(parseInt(i,10)+1)));
                }
            }
        }
    },
});

