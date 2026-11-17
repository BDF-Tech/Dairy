frappe.ui.form.on("Franchise Day Close", {
	setup(frm) {
		frm.set_query("franchise", () => ({ filters: { custom_franchise_pos: 1, disabled: 0 } }));
	},
	get_stock(frm) {
		if (!frm.doc.franchise || !frm.doc.posting_date) {
			frappe.msgprint(__("Choose the franchise and the date first."));
			return;
		}
		frm.call("get_stock").then(() => frm.refresh());
	},
});

frappe.ui.form.on("Franchise Day Close Item", {
	// counted closing follows the book until someone types a count
	wastage_qty(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		row.actual_qty = flt(row.expected_qty) - flt(row.wastage_qty);
		row.difference_qty = 0;
		frm.refresh_field("items");
	},
	actual_qty(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		row.difference_qty = flt(row.actual_qty) - (flt(row.expected_qty) - flt(row.wastage_qty));
		frm.refresh_field("items");
	},
});
