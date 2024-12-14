frappe.listview_settings['Warehouse'] = {
    onload: function(frm){
 	    frappe.route_options = {
			"is_dcs":1
		};
 	}
}