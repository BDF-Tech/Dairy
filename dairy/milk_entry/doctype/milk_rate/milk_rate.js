frappe.ui.form.on('Milk Rate', {
    setup: function(frm) {
        frm.set_query('dsc_name', function(doc) {
            return {
                filters: {
                    "is_dcs": 1,
                    "is_group": 0
                }
            };
        });
    },

    // Triggered by the "Upload the file" button
    upload_the_file: function(frm) {
        if (!frm.doc.attach_file) {
            frappe.msgprint(__('Please attach a file first.'));
            return;
        }

        frappe.call({
            method: "upload_the_file", // Calls the whitelisted method in milk_rate.py
            doc: frm.doc,              // Passes the current document
            callback: function(r) {
                if (!r.exc) {
                    frm.refresh_field("milk_rate_chart");
                }
            }
        });
    },

    milk_type: function(frm) {
        if (!frm.doc.simplified_milk_rate) {
            return frm.call('get_snf_lines').then(() => {
                frm.refresh_field('milk_rate_chart');
            });
        }
    },

    onload: function(frm) {
        if (frm.doc.__islocal && !frm.doc.simplified_milk_rate) {
            return frm.call('get_snf_lines').then(() => {
                frm.refresh_field('milk_rate_chart');
            });
        }
    },

    validate: function(frm) {
        if (!frm.doc.milk_rate_chart && !frm.doc.simplified_milk_rate) {
            frappe.throw(__('Cant Submit without Rate Chart.'));
        }
    },

    before_submit: function(frm) {
        if (frm.doc.simplified_milk_rate == 0) {
            (frm.doc.milk_rate_chart || []).forEach((row, i) => {
                if (flt(row.rate) <= 0) {
                    frappe.throw(__('Rate must be greater than zero on row ' + (i + 1)));
                }
            });
        }
    }
});