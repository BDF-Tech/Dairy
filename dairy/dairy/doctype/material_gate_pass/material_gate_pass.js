frappe.ui.form.on('Material Gate Pass', {

    refresh: function(frm) {
        if (frm.doc.docstatus !== 1) return;

        const status = frm.doc.status;
        const isReturn = frm.doc.trip_type === 'Return Trip';

        if (status === 'Draft' || status === 'Checked Out') {
            frm.add_custom_button(__('Mark In Transit'), function() {
                frm.set_value('status', 'In Transit');
                frm.save();
            }, __('Actions'));
        }

        if (isReturn && (status === 'In Transit' || status === 'Checked Out')) {
            frm.add_custom_button(__('Mark Returned'), function() {
                frm.set_value('status', 'Returned');
                frm.set_value('return_checked_in_time', frappe.datetime.now_datetime());
                frm.save();
            }, __('Actions'));
        }

        if (status !== 'Completed' && status !== 'Rejected') {
            frm.add_custom_button(__('Mark Completed'), function() {
                frm.set_value('status', 'Completed');
                frm.save();
            }, __('Actions'));
        }
    },

    gate_pass_type: function(frm) {
        frm.set_value('supplier', '');
        frm.set_value('supplier_name', '');
        frm.set_value('purchase_order', '');
        frm.set_value('from_location', '');
        frm.set_value('to_location', '');
        frm.set_value('to_warehouse', '');
    },

    trip_type: function(frm) {
        if (frm.doc.trip_type === 'One Way') {
            frm.set_value('return_items', []);
            frm.set_value('return_security_guard', '');
            frm.set_value('return_checked_in_time', '');
            frm.set_value('return_accepted_by', '');
            frm.set_value('return_verified_by', '');
            frm.set_value('return_remarks', '');
        }
    },

    onload: function(frm) {
        if (frm.is_new()) {
            if (!frm.doc.company) {
                frm.set_value('company', frappe.defaults.get_default('company'));
            }
            frm.set_value('checked_out_time', frappe.datetime.now_datetime());
        }
    },
});
