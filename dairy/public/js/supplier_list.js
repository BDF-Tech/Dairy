frappe.listview_settings['Supplier'] = {
    onload: function(frm){
 	    frappe.route_options = {
			"is_member":1
		};
 	}
}