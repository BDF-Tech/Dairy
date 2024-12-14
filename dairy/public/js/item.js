// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.item");

frappe.ui.form.on("Item", {
    refresh: function(frm){
        frm.set_query("leakage_variant", function() {
		    return {
               filters: {
					"variant_of":frm.doc.variant_of,
				}
            }
        });
    },

    has_variants:function(frm){
        if (frm.doc.has_variants == 1){
             frm.doc.leakage_applicable = 0;
            frm.set_df_property("leakage_applicable","hidden",1);
        }else{
            frm.set_df_property("leakage_applicable","hidden",0);
        }
    }
});

frappe.ui.form.on("Crate", {
	crate_quantity: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		frappe.model.set_value(cdt, cdn, "uom", frm.doc.stock_uom);
	}
})
