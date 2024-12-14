frappe.ui.form.on('Warehouse', {
	onload: function(frm){
        frm.set_query('route', function(doc) {
            return {
                filters: {
                
                    "company":doc.company,
                    "route_type":"Milk Procurement",
                    // "docstatus":1
                }
            };
        });
    },
})