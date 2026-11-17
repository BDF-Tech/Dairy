frappe.listview_settings["Franchise Sale"] = {
	add_fields: ["is_return", "docstatus"],
	get_indicator(doc) {
		if (doc.docstatus === 2) return [__("Cancelled"), "red", "docstatus,=,2"];
		if (doc.docstatus === 0) return [__("Draft"), "orange", "docstatus,=,0"];
		if (doc.is_return) return [__("Return"), "grey", "is_return,=,1"];
		return [__("Billed"), "green", "is_return,=,0"];
	},
};
