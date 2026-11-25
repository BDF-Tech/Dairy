frappe.ui.form.on("Franchise Stock Receipt", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.set_intro(__("Enter only what did not arrive (Short) or cannot be sold (Damaged), then Submit. The rest goes into the franchise stock."), "blue");
		}
	},
});

frappe.ui.form.on("Franchise Stock Receipt Item", {
	short_qty: (frm, cdt, cdn) => set_received(frm, cdt, cdn),
	damaged_qty: (frm, cdt, cdn) => set_received(frm, cdt, cdn),
});

function set_received(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const lost = flt(row.short_qty) + flt(row.damaged_qty);
	row.received_qty = flt(row.invoiced_qty) - lost;
	row.loss_amount = lost * flt(row.rate);
	frm.refresh_field("items");
}
