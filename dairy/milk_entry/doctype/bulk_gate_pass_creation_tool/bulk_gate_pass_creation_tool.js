// Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Gate Pass Creation Tool', {
        onload: function(frm){
             frappe.call({
                method: "get_options",
                doc: frm.doc,
                callback: function(r) {
                    frm.set_df_property("name_series", "options", r.message);
                }
            });
        },
		 refresh: function(frm) {
        if (frm.doc.docstatus == 0) {
			if(!frm.is_new()) {
				frm.page.clear_primary_action();
				frm.add_custom_button(__("Get Delivery Note"),
					function() {
						frm.events.fill_details(frm);
					}
				).toggleClass('btn-primary', !(frm.doc.items || []).length);
			}
		}

        frm.set_query('transporter', function() {
			return {
				filters: {
					'is_transporter': 1
				}
                }
        });

        frm.add_custom_button(__('Go to Gate Pass'),function() {
            frappe.set_route("List", "Gate Pass");
        });

//        if (frm.doc.docstatus===0) {
//				frm.add_custom_button(__('Delivery Note'),
//					function() {
//						erpnext.utils.map_current_doc({
//							method: "dairy.milk_entry.doctype.bulk_gate_pass_creation_tool.bulk_gate_pass_creation_tool.make_delivery_note",
//							source_doctype: "Delivery Note",
//							target: me.frm,
//                        setters: {
//                                posting_date: frm.doc.date || undefined,
//                                route: frm.doc.route || undefined,
//                                shift: frm.doc.shift || undefined,
//                                transporter: frm.doc.transporter || undefined,
//                                set_warehouse: frm.doc.warehouse || undefined
//                            },
//							get_query_filters: {
//								docstatus: 1,
//								status: ["=", ["To Bill"]],
//                                crate_gate_pass_done:0
//							}
//						})
//					}, __("Get items from"));
//			}

           frm.disable_save();
            frm.page.set_primary_action(__('Create Gate Pass'), () => {
                let btn_primary = frm.page.btn_primary.get(0);
                return frm.call({
                    doc: frm.doc,
                    freeze: true,
                    btn: $(btn_primary),
                    method: "create_delivery_note",
                    freeze_message: __("Creating Gate Pass "),
                    callback: (r) => {
                        if(!r.exc){
                            frappe.msgprint(__(" Gate Pass Created"));
                            frm.clear_table("items");
                            frm.refresh_fields();
                            frm.reload_doc();
                        }
                    }
                });
            });
	 },

    date: function(frm){
        frm.set_value("posting_date",frm.doc.date);
    },
    warehouse:function(frm){
        frm.set_value("set_warehouse",frm.doc.warehouse);
    },

	 fill_details: function(frm){
	    return frappe.call({
			doc: frm.doc,
			method: 'fill_details',
		}).then(r => {
			if (r.docs){
//				console.log("hey");
				frm.refresh_field("items");
			}
		})
	 }
});
