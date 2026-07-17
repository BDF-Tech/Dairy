// Copyright (c) 2026, BDF and contributors
// For license information, please see license.txt

frappe.ui.form.on("Milk Standardisation", {
	setup(frm) {
		// Only show BOMs for the chosen finished item.
		frm.set_query("bom", function () {
			return { filters: { item: frm.doc.finished_item, is_active: 1, docstatus: 1 } };
		});
	},

	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.calculation_mode === "Auto") {
			frm.add_custom_button(__("Suggest Quantities"), () => suggest_quantities(frm));
		}
		render_spec_banner(frm);
	},

	finished_item(frm) {
		if (!frm.doc.finished_item) return;
		// Prefill the default BOM and the target FAT/SNF from the base's BOM standard.
		frappe.db.get_value(
			"BOM",
			{ item: frm.doc.finished_item, is_active: 1, is_default: 1 },
			["name", "standard_fat", "standard_snf"]
		).then((r) => {
			const d = r.message || {};
			if (d.name && !frm.doc.bom) frm.set_value("bom", d.name);
			if (d.standard_fat && !frm.doc.target_fat) frm.set_value("target_fat", d.standard_fat);
			if (d.standard_snf && !frm.doc.target_snf) frm.set_value("target_snf", d.standard_snf);
		});
	},

	calculation_mode(frm) {
		frm.refresh();
	},

	target_fat: recompute,
	target_snf: recompute,
	fat_tolerance: recompute,
	snf_tolerance: recompute,
});

frappe.ui.form.on("Milk Standardisation Ingredient", {
	qty: recompute_row,
	fat: recompute_row,
	snf: recompute_row,
	item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (row.item) {
			frappe.db.get_value("Item", row.item, "stock_uom").then((r) => {
				if (r.message) frappe.model.set_value(cdt, cdn, "uom", r.message.stock_uom);
			});
		}
	},
	ingredients_remove: recompute,
});

function recompute_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	frappe.model.set_value(cdt, cdn, "kg_fat", flt(row.qty) * flt(row.fat) / 100);
	frappe.model.set_value(cdt, cdn, "kg_snf", flt(row.qty) * flt(row.snf) / 100);
	recompute(frm);
}

function recompute(frm) {
	let q = 0, kf = 0, ks = 0;
	(frm.doc.ingredients || []).forEach((r) => {
		q += flt(r.qty);
		kf += flt(r.qty) * flt(r.fat) / 100;
		ks += flt(r.qty) * flt(r.snf) / 100;
	});
	const af = q > 0 ? kf / q * 100 : 0;
	const as = q > 0 ? ks / q * 100 : 0;
	frm.set_value("total_qty", q);
	frm.set_value("total_kg_fat", kf);
	frm.set_value("total_kg_snf", ks);
	frm.set_value("achieved_fat", af);
	frm.set_value("achieved_snf", as);
	frm.set_value("fat_deviation", af - flt(frm.doc.target_fat));
	frm.set_value("snf_deviation", as - flt(frm.doc.target_snf));
	const in_spec = q > 0
		&& Math.abs(af - flt(frm.doc.target_fat)) <= flt(frm.doc.fat_tolerance) + 1e-9
		&& Math.abs(as - flt(frm.doc.target_snf)) <= flt(frm.doc.snf_tolerance) + 1e-9;
	frm.set_value("in_spec", in_spec ? 1 : 0);
	render_spec_banner(frm);
}

function render_spec_banner(frm) {
	frm.dashboard.clear_headline();
	if (!frm.doc.total_qty) return;
	if (frm.doc.in_spec) {
		frm.dashboard.set_headline(
			__("In spec — achieved {0}% FAT / {1}% SNF.",
				[format_number(frm.doc.achieved_fat, null, 3), format_number(frm.doc.achieved_snf, null, 3)]),
			"green"
		);
	} else {
		frm.dashboard.set_headline(
			__("Out of tolerance — achieved {0}% FAT / {1}% SNF vs target {2} / {3}. Adjust quantities.",
				[format_number(frm.doc.achieved_fat, null, 3), format_number(frm.doc.achieved_snf, null, 3),
					frm.doc.target_fat, frm.doc.target_snf]),
			"orange"
		);
	}
}

function suggest_quantities(frm) {
	frappe.call({
		method: "dairy.milk_entry.doctype.milk_standardisation.milk_standardisation.suggest_quantities",
		args: { doc: frm.doc },
		freeze: true,
		freeze_message: __("Solving additive quantities..."),
		callback(r) {
			if (!r.message || !r.message.length) return;
			// Drop existing rows for the same items, then add the fresh suggestions.
			const suggested = new Set(r.message.map((x) => x.item));
			frm.doc.ingredients = (frm.doc.ingredients || []).filter((row) => !suggested.has(row.item));
			r.message.forEach((x) => {
				const row = frm.add_child("ingredients");
				Object.assign(row, x);
				row.kg_fat = flt(x.qty) * flt(x.fat) / 100;
				row.kg_snf = flt(x.qty) * flt(x.snf) / 100;
			});
			frm.refresh_field("ingredients");
			recompute(frm);
			frappe.show_alert({ message: __("Additive quantities suggested."), indicator: "green" });
		},
	});
}
