// Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Milk Price List', {
	setup: function(frm){
		apply_filter(frm)
	},
	milk_type:function(frm){
		apply_filter(frm)
	}
});

function apply_filter(frm){
    frm.fields_dict['items'].grid.get_field("item").get_query = function(doc, cdt, cdn) {
        var child = locals[cdt][cdn];
        return {
            filters:[
               ['maintain_fat_snf_clr', '=', 1],
               ['milk_type', '=', frm.doc.milk_type]
            ]
        }
    }
}
