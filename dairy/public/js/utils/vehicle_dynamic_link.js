frappe.provide('dairy.vehicle_dynamic_link')

$.extend(dairy.vehicle_dynamic_link, {
	clear_vehicle_and_customer: function(frm) {
		$(frm.fields_dict['vehicle_html'].wrapper).html("");
//		$(frm.fields_dict['customer_html'].wrapper).html("");

	},
	render_vehicle_and_customer: function(frm) {
		// render Vehicle
		if(frm.fields_dict['vehicle_html'] && "vehicle_list" in frm.doc.__onload) {
			$(frm.fields_dict['vehicle_html'].wrapper)
				.html(frappe.render_template("vehicle_list",
					frm.doc.__onload))
				.find(".btn-address").on("click", function() {
					frappe.new_doc("Vehicle");
				});
		}
		// render Customer
//		if(frm.fields_dict['customer_html'] && "customer_list" in frm.doc.__onload) {
//			$(frm.fields_dict['customer_html'].wrapper)
//				.html(frappe.render_template("customer_list",
//					frm.doc.__onload))
//				.find(".btn-address").on("click", function() {
//					frappe.new_doc("Customer");
//				});
//		}

	},
	get_last_doc: function(frm) {
		const reverse_routes = frappe.route_history.reverse();
		const last_route = reverse_routes.find(route => {
			return route[0] === 'Form' && route[1] !== frm.doctype
		})
		let doctype = last_route && last_route[1];
		let docname = last_route && last_route[2];

		if (last_route && last_route.length > 3)
			docname = last_route.slice(2).join("/");

		return {
			doctype,
			docname
		}
	}
})