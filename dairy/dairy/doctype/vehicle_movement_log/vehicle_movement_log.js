frappe.ui.form.on('Vehicle Movement Log', {
    refresh: function(frm) {
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Get Invoices'), function() {
                frm.call({
                    doc: frm.doc,
                    method: 'get_invoices',
                    callback: function(r) {
                        if (!r.exc) {
                            frm.reload_doc(); 
                            frappe.show_alert({
                                message: __('Invoices fetched and saved'),
                                indicator: 'green'
                            });
                        }
                    }
                });
            });
        }
    }
});