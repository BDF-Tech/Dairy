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
	target_batch_qty: recompute,
	fat_tolerance: recompute,
	snf_tolerance: recompute,
	batch_qty_tolerance: recompute,
});

frappe.ui.form.on("Milk Standardisation Ingredient", {
	qty: recompute_row,
	fat: recompute_row,
	snf: recompute_row,
	conversion_factor: recompute_row,
	item(frm, cdt, cdn) {
		const row = locals[cdt][cdn];
		if (!row.item) return;
		// Pull the item's stock UOM and, if it is a configured additive, its
		// FAT/SNF impact + preferred UOM from Dairy Settings.
		frappe.call({
			method: "dairy.milk_entry.doctype.milk_standardisation.milk_standardisation.get_item_row_defaults",
			args: { item: row.item },
			callback(r) {
				const d = r.message || {};
				frappe.model.set_value(cdt, cdn, "uom", d.uom || d.stock_uom);
				if (d.is_lever) {
					frappe.model.set_value(cdt, cdn, "fat", d.fat);
					frappe.model.set_value(cdt, cdn, "snf", d.snf);
				}
				fetch_conversion(cdt, cdn);
			},
		});
	},
	uom(frm, cdt, cdn) {
		fetch_conversion(cdt, cdn);
	},
	ingredients_remove: recompute,
});

function fetch_conversion(cdt, cdn) {
	const row = locals[cdt][cdn];
	if (!row.item || !row.uom) return;
	// Conversion factor from the chosen UOM to the item's stock UOM (kg, gm, litre...).
	frappe.call({
		method: "erpnext.stock.get_item_details.get_conversion_factor",
		args: { item_code: row.item, uom: row.uom },
		callback(r) {
			if (r.message && !r.exc) {
				frappe.model.set_value(cdt, cdn, "conversion_factor", r.message.conversion_factor || 1);
			}
		},
	});
}

function recompute_row(frm, cdt, cdn) {
	const row = locals[cdt][cdn];
	const cf = flt(row.conversion_factor) || 1;
	const stock_qty = flt(row.qty) * cf;
	frappe.model.set_value(cdt, cdn, "stock_qty", stock_qty);
	frappe.model.set_value(cdt, cdn, "kg_fat", stock_qty * flt(row.fat) / 100);
	frappe.model.set_value(cdt, cdn, "kg_snf", stock_qty * flt(row.snf) / 100);
	recompute(frm);
}

function recompute(frm) {
	let q = 0, kf = 0, ks = 0;
	(frm.doc.ingredients || []).forEach((r) => {
		const sq = flt(r.qty) * (flt(r.conversion_factor) || 1);
		q += sq;
		kf += sq * flt(r.fat) / 100;
		ks += sq * flt(r.snf) / 100;
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
	frm.set_value("batch_qty_deviation", q - flt(frm.doc.target_batch_qty));
	const in_spec = q > 0
		&& Math.abs(af - flt(frm.doc.target_fat)) <= flt(frm.doc.fat_tolerance) + 1e-9
		&& Math.abs(as - flt(frm.doc.target_snf)) <= flt(frm.doc.snf_tolerance) + 1e-9;
	frm.set_value("in_spec", in_spec ? 1 : 0);
	render_spec_banner(frm);
}

function render_spec_banner(frm) {
	frm.dashboard.clear_headline();
	if (!frm.doc.total_qty) return;

	const target = flt(frm.doc.target_batch_qty);
	const over = target && frm.doc.total_qty > target + flt(frm.doc.batch_qty_tolerance) + 1e-9;

	if (over) {
		frm.dashboard.set_headline(
			__("Over batch — total {0} exceeds target {1} by {2}. Submit is blocked; reduce quantities or raise the target.",
				[format_number(frm.doc.total_qty, null, 2), format_number(target, null, 2),
					format_number(frm.doc.total_qty - target, null, 2)]),
			"red"
		);
	} else if (!frm.doc.in_spec) {
		frm.dashboard.set_headline(
			__("Out of tolerance — achieved {0}% FAT / {1}% SNF vs target {2} / {3}. Adjust quantities.",
				[format_number(frm.doc.achieved_fat, null, 3), format_number(frm.doc.achieved_snf, null, 3),
					frm.doc.target_fat, frm.doc.target_snf]),
			"orange"
		);
	} else {
		const suffix = target ? __(" · total {0} / target {1}", [format_number(frm.doc.total_qty, null, 2), format_number(target, null, 2)]) : "";
		frm.dashboard.set_headline(
			__("In spec — achieved {0}% FAT / {1}% SNF.",
				[format_number(frm.doc.achieved_fat, null, 3), format_number(frm.doc.achieved_snf, null, 3)]) + suffix,
			"green"
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
			// Auto solves the whole recipe (scaled milk + additives) to hit the target
			// batch quantity exactly, so replace the entire table with the result.
			frm.clear_table("ingredients");
			r.message.forEach((x) => {
				const row = frm.add_child("ingredients");
				Object.assign(row, x);
				const sq = flt(x.qty) * (flt(x.conversion_factor) || 1);
				row.stock_qty = sq;
				row.kg_fat = sq * flt(x.fat) / 100;
				row.kg_snf = sq * flt(x.snf) / 100;
			});
			frm.refresh_field("ingredients");
			recompute(frm);
			frappe.show_alert({ message: __("Recipe solved to the target batch quantity."), indicator: "green" });
		},
	});
}
