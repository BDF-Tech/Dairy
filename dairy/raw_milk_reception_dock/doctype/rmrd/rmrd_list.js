frappe.listview_settings['RMRD'] = {
	add_fields: [ "status"],
	get_indicator: function (doc) {
		if (doc.status === "In-Progress") {
			return [__("In-Progress"), "orange", "status,=,In-Progress"];
		}
		else if (doc.status === "Completed") {
			return [__("Completed"), "green", "status,=,Completed"];
		}
	},
}