frappe.ui.form.on("Supplier", {
    onload:function(frm){
        frm.set_query('dcs_id', function(frm) {
            return {
                filters: {
                    "is_dcs":1,
                    "is_group":0,
                    "company":frappe.defaults.get_user_default("Company"),
                    "disabled":0
                }
            };
        });
    }
})