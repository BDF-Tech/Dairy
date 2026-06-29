frappe.ui.form.on('Crate Balance Adjustment', {

    party_type: function(frm) {
        frm.set_value('customer', '');
        frm.set_value('driver', '');
    },
});
