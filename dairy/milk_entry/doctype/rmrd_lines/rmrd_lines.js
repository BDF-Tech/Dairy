// Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt
frappe.ui.form.on('RMRD Lines', {
	on_submit: function (frm) {
		frm.call({
			method:'creatr_stockrmrd',//function name defined in python
			doc: frm.doc, //current document
		});
	}
});


frappe.ui.form.on('RMRD Lines', {

	after_save: function(frm) {
	    if(frm.doc.__islocal)
	    {
	         cur_frm.cscript.calculate_total_cans_wt()
	    }
		frm.set_df_property("rmrd_good_cow_milk", "read_only", frm.is_new() ? 0 : 1);
		frm.set_df_property("rmrd_good_buf_milk", "read_only", frm.is_new() ? 0 : 1);
		frm.set_df_property("rmrd_good_mix_milk", "read_only", frm.is_new() ? 0 : 1);
		frm.set_df_property("s_cow_milk", "read_only", frm.is_new() ? 0 : 1);
		frm.set_df_property("s_buf_milk", "read_only", frm.is_new() ? 0 : 1);
		frm.set_df_property("s_mix_milk", "read_only", frm.is_new() ? 0 : 1);
		frm.set_df_property("c_cow_milk", "read_only", frm.is_new() ? 0 : 1);
		frm.set_df_property("c_buf_milk", "read_only", frm.is_new() ? 0 : 1);
		frm.set_df_property("c_mix_milk", "read_only", frm.is_new() ? 0 : 1);

		frappe.db.get_doc('Dairy Settings').then((r) => {
		if(r.allow_changing == 1){
			frm.set_df_property("cow_milk_fat", "read_only",0);
			frm.set_df_property("buf_milk_fat", "read_only",0);
			frm.set_df_property("mix_milk_fat", "read_only",0);
			frm.set_df_property("cow_milk_snf", "read_only",0);
			frm.set_df_property("buf_milk_snf", "read_only",0);
			frm.set_df_property("mix_milk_snf", "read_only",0);
		}
		else{
			frm.set_df_property("cow_milk_fat", "read_only",1);
			frm.set_df_property("buf_milk_fat", "read_only",1);
			frm.set_df_property("mix_milk_fat", "read_only",1);
			frm.set_df_property("cow_milk_snf", "read_only",1);
			frm.set_df_property("buf_milk_snf", "read_only",1);
			frm.set_df_property("mix_milk_snf", "read_only",1);
		}
		});


	 },

	
	 
	//  g_cow_milk: function(frm) {
	//      cur_frm.cscript.calculate_total_cans_wt()
	//  },
	//  g_buf_milk: function(frm) {
	//      cur_frm.cscript.calculate_total_cans_wt()
	//  },
	//  g_mix_milk: function(frm) {
	//      cur_frm.cscript.calculate_total_cans_wt()
	//  },
	 rmrd_good_cow_milk: function(frm) {
	    cur_frm.cscript.calculate_total_cans_wt()
	 },

	 rmrd_good_buf_milk: function(frm) {
		cur_frm.cscript.calculate_total_cans_wt()
        
	 },

	 rmrd_good_mix_milk: function(frm) {
	    cur_frm.cscript.calculate_total_cans_wt()
        
	 },

	 g_cow_milk_can: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 g_buf_milk_can: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 g_mix_milk_can: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },

	 s_cow_milk: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 s_buf_milk: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 s_mix_milk: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 s_cow_milk_can: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 s_buf_milk_can: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 s_mix_milk_can: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },

	 c_cow_milk: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 c_buf_milk: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 c_mix_milk: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 c_cow_milk_can: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 c_buf_milk_can: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 c_mix_milk_can: function(frm) {
	     cur_frm.cscript.calculate_total_cans_wt()
	 },
	 

	//  refresh: function(frm) {
		
	// 	console.log('Stock entry',frm.doc.stock_entry)
	// 	if(!frm.doc.__islocal && !frm.doc.stock_entry)
	// 	       {
	// 	           frm.add_custom_button(__('Make Stock Entry'),function() {
	// 	               return frappe.call({
	// 	                   doc: frm.doc,
	// 	                   method: 'make_stock_entry',
	// 	                   callback: function(r) {
	// 	                       var doc = frappe.model.sync(r.message);
	// 	                       frappe.set_route("Form", doc[0].doctype, doc[0].name);
	// 	                   }
	// 	               });
	// 	           }).addClass('btn-primary');
	// 	       }
			
	// },
	onload:function(frm){
        frm.set_query('rmrd', function(doc) {
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

		frappe.db.get_doc('Dairy Settings').then((r) => {
			if(r.allow_changing == 1){
				frm.set_df_property("cow_milk_fat", "read_only",0);
				frm.set_df_property("buf_milk_fat", "read_only",0);
				frm.set_df_property("mix_milk_fat", "read_only",0);
				frm.set_df_property("cow_milk_snf", "read_only",0);
				frm.set_df_property("buf_milk_snf", "read_only",0);
				frm.set_df_property("mix_milk_snf", "read_only",0);
			}
			else{
				frm.set_df_property("cow_milk_fat", "read_only",1);
				frm.set_df_property("buf_milk_fat", "read_only",1);
				frm.set_df_property("mix_milk_fat", "read_only",1);
				frm.set_df_property("cow_milk_snf", "read_only",1);
				frm.set_df_property("buf_milk_snf", "read_only",1);
				frm.set_df_property("mix_milk_snf", "read_only",1);
			}
			});
    },

	cow_milk_fat : function(frm){
		return frappe.call({
			doc: frm.doc,
			method: 'item_weight',
			callback: function(r) {
				if(r.message[1]){
					var d = frm.doc.cow_milk_fat
					var tot = (frm.doc.g_cow_milk * r.message[0]) * (frm.doc.cow_milk_fat/100)
				}
				frappe.model.set_value("RMRD Lines",frm.doc.name,"cow_milk_fat_kg", tot);
		}
	})
	},

	cow_milk_snf : function(frm){
		return frappe.call({
			doc: frm.doc,
			method: 'item_weight',
			callback: function(r) {
				if(r.message[1]){
					var d = frm.doc.cow_milk_snf
					var tot = (frm.doc.g_cow_milk * r.message[0]) * (frm.doc.cow_milk_snf/100)
				}
				frappe.model.set_value("RMRD Lines",frm.doc.name,"cow_milk_snf_kg", tot);
		}
	})
	},

	buf_milk_fat : function(frm){
		return frappe.call({
			doc: frm.doc,
			method: 'item_weight',
			callback: function(r) {
				if(r.message[3]){
					var d = frm.doc.buf_milk_fat
					var tot = (frm.doc.g_buf_milk * r.message[2]) * (frm.doc.buf_milk_fat/100)
				}
				frappe.model.set_value("RMRD Lines",frm.doc.name,"buf_milk_fat_kg", tot);
		}
	})
	},

	buf_milk_snf : function(frm){
		return frappe.call({
			doc: frm.doc,
			method: 'item_weight',
			callback: function(r) {
				if(r.message[3]){
					var d = frm.doc.buf_milk_snf
					var tot = (frm.doc.g_buf_milk * r.message[2]) * (frm.doc.buf_milk_snf/100)
				}
				frappe.model.set_value("RMRD Lines",frm.doc.name,"buf_milk_snf_kg", tot);
		}
	})
	},

	mix_milk_fat : function(frm){
		return frappe.call({
			doc: frm.doc,
			method: 'item_weight',
			callback: function(r) {
				if(r.message[5]){
					var d = frm.doc.mix_milk_fat
					var tot = (frm.doc.g_mix_milk * r.message[4]) * (frm.doc.mix_milk_fat/100)
				}
				frappe.model.set_value("RMRD Lines",frm.doc.name,"mix_milk_fat_kg", tot);
		}
	})
	},

	mix_milk_snf : function(frm){
		return frappe.call({
			doc: frm.doc,
			method: 'item_weight',
			callback: function(r) {
				if(r.message[5]){
					var d = frm.doc.mix_milk_snf
					var tot = (frm.doc.g_mix_milk * r.message[4]) * (frm.doc.mix_milk_snf/100)
				}
				frappe.model.set_value("RMRD Lines",frm.doc.name,"mix_milk_snf_kg", tot);
		}
	})
	},

});


cur_frm.cscript.calculate_total_cans_wt = function(){
    return frappe.call({
            doc: cur_frm.doc,
            method: 'calculate_total_cans_wt',
            callback: function(r) {
               cur_frm.refresh_fields();
            }
    });
}

