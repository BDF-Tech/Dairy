// Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Crate Reconciliation', {
	 refresh: function(frm, dt, dn) {
        
	 frappe.db.get_value("Dairy Settings", "Dairy Settings", "crate_reconciliation_based_on", (r) => {
        if (r && r.crate_reconciliation_based_on == "Delivery Note" || r.crate_reconciliation_based_on == ""||r.crate_reconciliation_based_on == "Sales Invoice") {
            frm.set_df_property("transporter","hidden",1);
            frm.set_df_property("customer","reqd",1);
            }else {
                frm.set_df_property("customer","hidden",1);
                frm.set_df_property("transporter","reqd",1);
            }
        })


        if (frm.doc.docstatus ==0)
        {
        frm.add_custom_button(__('Crate Log'),function() {
                erpnext.utils.map_current_doc({
                    method: "dairy.milk_entry.doctype.crate_reconciliation.crate_reconciliation.make_crate_log",
                    source_doctype: "Crate Log",
                    target: frm,
                    date_field: "posting_date",
                    setters: {
                            customer: frm.doc.customer || undefined,
                            transporter: frm.doc.transporter || undefined,
                            route: frm.doc.route || undefined
                        },
                    get_query_filters: {
                        company: frm.doc.company,
                        route: frm.doc.route,
                        crate_reconsilliation_done:0,
                        docstatus: 1
                            }
                        })
                    }, __("Get items from"));

//            frappe.db.get_value("Dairy Settings", "Dairy Settings", "crate_reconciliation_based_on", (r) => {
//			if (r && r.crate_reconciliation_based_on == "Delivery Note" || r.crate_reconciliation_based_on == "") {
//                frm.add_custom_button(__('Delivery Note'),function() {
//                erpnext.utils.map_current_doc({
//                    method: "dairy.milk_entry.doctype.crate_reconciliation.crate_reconciliation.make_delivery_note",
//                    source_doctype: "Delivery Note",
//                    target: frm,
//                    date_field: "posting_date",
//                    setters: {
//                            customer: frm.doc.customer || undefined,
//                            route: frm.doc.route || undefined
//                        },
//                    get_query_filters: {
//                        company: frm.doc.company,
//                        route: frm.doc.route,
//                        crate_reconcilation_done:0,
//                        docstatus: 1
//                            }
//                        })
//                    }, __("Get items from"));
//                }
//                else {
//                frm.add_custom_button(__('Gate Pass'),function() {
//                erpnext.utils.map_current_doc({
//                    method: "dairy.milk_entry.doctype.crate_reconciliation.crate_reconciliation.make_gate_pass",
//                    source_doctype: "Gate Pass",
//                    target: frm,
//                    date_field: "posting_date",
//                    setters: {
//                            transporter: frm.doc.transporter || undefined,
//                            route: frm.doc.route || undefined
//                        },
//                    get_query_filters: {
//                        company: frm.doc.company,
//                        route: frm.doc.route,
//                        crate_reconcilation_done:0,
//                        docstatus: 1
//                            }
//                        })
//                    }, __("Get items from"));
//                }
//            })
            
        }
        if (frm.doc.docstatus ==1 && frm.doc.difference>0)
        {
            frm.add_custom_button(__('Create Invoice'),function() {
                return frappe.call({
                    doc: frm.doc,
                    method: 'make_sales_invoice',
                    callback: function(r) {
                        var doc = frappe.model.sync(r.message);
                        frappe.set_route("Form", doc[0].doctype, doc[0].name);
                    }
                });
            }).addClass('btn-primary');
        }
        frm.set_df_property("myfield", "read_only", frm.is_new() ? 0 : 1);
	 },
	 onload: function(frm){
        frm.set_query('route', function(doc) {
            return {
                filters: {
                    "company":frappe.defaults.get_user_default("Company"),
                }
            };
        });
        frm.set_query('transporter', function() {
			return {
				filters: {
					'is_transporter': 1
				}
			}
		});
     },
//      before_submit: function(frm)
//      {
//          return frappe.call({
//             doc: frm.doc,
//             method: 'calculate_crate_type_summary',
//             callback: function(r) {
// //                frm.refresh_field('crate_type_summary_section');
// //                frm.refresh_field('crate_type_summary');
//             }
//         });
//      }
});

frappe.ui.form.on("Crate Reconciliation Child", {
	outgoing: function(frm,cdt,cdn) {
		var row = locals[cdt][cdn];
			row.difference = row.outgoing -row.incoming
	},
	incoming: function(frm,cdt,cdn) {
		var row = locals[cdt][cdn];
			row.difference = row.outgoing -row.incoming
	}
});
