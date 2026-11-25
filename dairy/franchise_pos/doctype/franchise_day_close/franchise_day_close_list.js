frappe.listview_settings["Franchise Day Close"] = {
	add_fields: ["auto_closed", "docstatus"],
	get_indicator(doc) {
		if (doc.docstatus === 2) return [__("Cancelled"), "red", "docstatus,=,2"];
		if (doc.docstatus === 0) return [__("Draft"), "orange", "docstatus,=,0"];
		if (doc.auto_closed) return [__("Auto Closed"), "yellow", "auto_closed,=,1"];
		return [__("Closed"), "green", "auto_closed,=,0"];
	},
};
