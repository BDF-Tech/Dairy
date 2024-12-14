// Copyright (c) 2019, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt
// frappe.provide("dairy.milk_entry");

frappe.ui.form.on('Raw Milk Sample', {
    // refresh: function(frm) {
    
    onload: function(frm){
        frm.set_query('dcs_id', function(doc) {
            return {
                filters: {
                    "is_dcs":1,
                    "sample_collector":1,
                }
            };
        });
    },
    dcs_id:function(frm){
        frm.set_query("milk_entry","sample_lines", function() {
            return {
                filters: {
                    "dcs_id": frm.doc.dcs_id,
                    "docstatus": 1,
                    "date":["=",frm.doc.date]
                }
            }
        });
    },
    refresh: function(frm, cdt, cdn) {
        var me = this;
        if (frm.doc.docstatus==0) {
            frm.add_custom_button(__('Milk Entry'),function() {
                if (frm.doc.dcs_id==undefined)
                {
                    frappe.throw(__("Please Provide DCS"));
                }
                erpnext.utils.map_current_doc({
                    method: "dairy.milk_entry.doctype.milk_entry.milk_entry.make_sample",
                    source_doctype: "Milk Entry",
                    target: frm,
                    date_field: "date",
                    setters: {
                        dcs_id: frm.doc.dcs_id || undefined,
                        date :frm.doc.date || undefined,
                    },
                    get_query_filters: {
                        docstatus: 1,
                        sample_created:0
                    }
                })
            }, __("Get items from"));
        }
    }
});
