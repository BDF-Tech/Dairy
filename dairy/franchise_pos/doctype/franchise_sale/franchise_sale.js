frappe.ui.form.on("Franchise Sale", {
	setup(frm) {
		frm.set_query("franchise", () => ({ filters: { custom_franchise_pos: 1, disabled: 0 } }));
		frm.set_query("return_against", () => ({
			filters: { franchise: frm.doc.franchise, docstatus: 1, is_return: 0 },
		}));
	},
	refresh(frm) {
		if (frm.doc.docstatus === 1 && !frm.doc.is_return && frm.perm[0].create) {
			frm.add_custom_button(__("Return"), () => {
				frappe.new_doc("Franchise Sale", {
					franchise: frm.doc.franchise,
					is_return: 1,
					return_against: frm.doc.name,
					payment_mode: frm.doc.payment_mode,
					buyer_name: frm.doc.buyer_name,
					buyer_mobile: frm.doc.buyer_mobile,
				}).then(() => {
					cur_frm.clear_table("items");
					(frm.doc.items || []).forEach((d) => {
						const row = cur_frm.add_child("items");
						Object.assign(row, {
							item_code: d.item_code, item_name: d.item_name, uom: d.uom,
							qty: d.qty, rate: d.rate, amount: d.amount,
						});
					});
					cur_frm.refresh_field("items");
					set_totals(cur_frm);
				});
			});
		}
	},
});

frappe.ui.form.on("Franchise Sale Item", {
	item_code(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item_code || !frm.doc.franchise || frm.doc.is_return) return;
		frappe.call({
			method: "dairy.franchise_pos.stock.get_item_info",
			args: { franchise: frm.doc.franchise, item_code: row.item_code },
		}).then((r) => {
			const d = r.message || {};
			row.item_name = d.item_name;
			row.uom = d.uom;
			row.rate = d.rate;
			row.amount = flt(row.qty) * flt(row.rate);
			frm.refresh_field("items");
			set_totals(frm);
			frappe.show_alert({ message: __("In hand: {0} {1}", [d.balance, d.uom]), indicator: d.balance > 0 ? "green" : "red" });
		});
	},
	qty(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		row.amount = flt(row.qty) * flt(row.rate);
		frm.refresh_field("items");
		set_totals(frm);
	},
	items_remove: set_totals,
});

function set_totals(frm) {
	let qty = 0, total = 0;
	(frm.doc.items || []).forEach((d) => { qty += flt(d.qty); total += flt(d.amount); });
	frm.set_value({ total_qty: qty, grand_total: total });
}
