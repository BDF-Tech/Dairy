// Copyright (c) 2026, BDF and contributors
// For license information, please see license.txt

frappe.ui.form.on("Milk Fat Reconciliation", {
	refresh(frm) {
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Get Milk Stock"), () => get_milk_stock(frm));
		}
		render_headline(frm);
	},

	scope(frm) {
		frm.set_value("warehouse", "");
	},
});

frappe.ui.form.on("Milk Fat Reconciliation Item", {
	tested_fat: recompute,
	tested_snf: recompute,
	items_remove: recompute,
});

function get_milk_stock(frm) {
	frappe.call({
		method: "dairy.milk_standardisation.doctype.milk_fat_reconciliation.milk_fat_reconciliation.get_milk_stock",
		args: { company: frm.doc.company, scope: frm.doc.scope, warehouse: frm.doc.warehouse },
		freeze: true,
		freeze_message: __("Reading the milk stock..."),
		callback(r) {
			if (!r.message || !r.message.length) {
				frappe.msgprint(__("No warehouse is holding milk stock."));
				return;
			}
			// Replace the table: this is a snapshot of what is standing right now.
			frm.clear_table("items");
			r.message.forEach((row) => {
				const child = frm.add_child("items");
				Object.assign(child, row);
			});
			frm.refresh_field("items");
			recompute(frm);
			frappe.show_alert({
				message: __("{0} line(s) loaded. Enter the lab's FAT/SNF for each.", [r.message.length]),
				indicator: "blue",
			});
		},
	});
}

function recompute(frm) {
	let qty_kg = 0, tested_fat = 0, tested_snf = 0, book_fat = 0, book_snf = 0;
	(frm.doc.items || []).forEach((r) => {
		const kg = flt(r.qty_kg);
		r.tested_kg_fat = kg * flt(r.tested_fat) / 100;
		r.tested_kg_snf = kg * flt(r.tested_snf) / 100;
		r.fat_adjustment = r.tested_kg_fat - flt(r.book_kg_fat);
		r.snf_adjustment = r.tested_kg_snf - flt(r.book_kg_snf);
		qty_kg += kg;
		tested_fat += r.tested_kg_fat;
		tested_snf += r.tested_kg_snf;
		book_fat += flt(r.book_kg_fat);
		book_snf += flt(r.book_kg_snf);
	});
	frm.refresh_field("items");
	frm.set_value("total_qty_kg", qty_kg);
	frm.set_value("total_tested_kg_fat", tested_fat);
	frm.set_value("total_tested_kg_snf", tested_snf);
	frm.set_value("total_book_kg_fat", book_fat);
	frm.set_value("total_book_kg_snf", book_snf);
	frm.set_value("total_fat_adjustment", tested_fat - book_fat);
	frm.set_value("total_snf_adjustment", tested_snf - book_snf);
	render_headline(frm);
}

function render_headline(frm) {
	frm.dashboard.clear_headline();
	if (!(frm.doc.items || []).length) return;

	const missing = (frm.doc.items || []).filter((r) => !flt(r.tested_fat) || !flt(r.tested_snf)).length;
	if (missing) {
		frm.dashboard.set_headline(
			__("{0} line(s) still need the lab's FAT and SNF.", [missing]), "orange");
		return;
	}
	frm.dashboard.set_headline(
		__("Adjustment on submit: FAT {0} kg, SNF {1} kg across {2} line(s).", [
			format_number(frm.doc.total_fat_adjustment, null, 2),
			format_number(frm.doc.total_snf_adjustment, null, 2),
			frm.doc.items.length,
		]), "blue");
}
