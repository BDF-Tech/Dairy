frappe.listview_settings["Franchise Stock Receipt"] = {
	add_fields: ["status", "docstatus"],
	get_indicator(doc) {
		const colour = { Pending: "orange", Received: "green", "Short Received": "red", "Auto Received": "yellow", Cancelled: "grey" };
		return [__(doc.status), colour[doc.status] || "grey", "status,=," + doc.status];
	},
};
