// Copyright (c) 2023, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Crate Opening Entry', {
	refresh: function(frm) {
		frm.disable_save();
		!frm.doc.import_in_progress && frm.trigger("make_dashboard");
		frm.page.set_primary_action(__('Create Crate Log'), () => {
			
			let btn_primary = frm.page.btn_primary.get(0);
			return frm.call({
				doc: frm.doc,
				btn: $(btn_primary),
				method: "make_crate_log",
				// freeze: 1,
				// freeze_message: __("Creating {0} Crate Log", [frm.doc.invoice_type]),
			});
		});

		
	},
	
});
frappe.ui.form.on('Party Crate Opening', {
	customer : function(frm,cdt,cdn){
		var child = locals[cdt][cdn];
		if (child.customer){
			frappe.db.get_doc('Customer',child.customer).then(cust => {
				var dl = cust.links
				for (let d in dl){
					frappe.model.set_value(cdt,cdn,"route",dl[d]["link_name"])
				}
			})
		}
	}

});