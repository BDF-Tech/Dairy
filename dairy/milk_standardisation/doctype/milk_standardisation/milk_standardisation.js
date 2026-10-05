// Copyright (c) 2026, BDF and contributors
// For license information, please see license.txt

const MILK_BASE_ITEM_GROUP = "Semi-Finished Goods";

frappe.ui.form.on("Milk Standardisation", {
	setup(frm) {
		// Only semi-finished items (milk bases) can be standardised.
		frm.set_query("finished_item", function () {
			return { filters: { item_group: MILK_BASE_ITEM_GROUP, disabled: 0 } };
		});
		// Only show BOMs for the chosen finished item.
		frm.set_query("bom", function () {
			return { filters: { item: frm.doc.finished_item, is_active: 1, docstatus: 1 } };
		});
	},

	refresh(frm) {
		if (frm.doc.finished_item && !frm.doc.__kg_per_base_unit) {
			frappe.call({
				method: "dairy.milk_standardisation.doctype.milk_standardisation.milk_standardisation.get_item_row_defaults",
				args: { item: frm.doc.finished_item },
				callback(r) { frm.doc.__kg_per_base_unit = (r.message || {}).kg_per_stock_unit || 1; },
			});
		}
		if (frm.doc.docstatus === 0) {
			frm.add_custom_button(__("Get Silo Milk"), () => get_silo_milk(frm));
		}
		if (frm.doc.docstatus === 0 && frm.doc.calculation_mode === "Auto") {
			frm.add_custom_button(__("Suggest Quantities"), () => suggest_quantities(frm));
		}
		render_spec_banner(frm);
	},

	finished_item(frm) {
		// A BOM belongs to one item, so a BOM picked for the previous item no longer applies.
		frm.set_value("bom", "");
		frm.doc.__kg_per_base_unit = 1;
		if (!frm.doc.finished_item) return;
		// Kg per unit of the milk base, to show how much will be posted to stock.
		frappe.call({
			method: "dairy.milk_standardisation.doctype.milk_standardisation.milk_standardisation.get_item_row_defaults",
			args: { item: frm.doc.finished_item },
			callback(r) {
				frm.doc.__kg_per_base_unit = (r.message || {}).kg_per_stock_unit || 1;
				recompute(frm);
			},
		});
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
	tested_fat: record_lab_test,
	tested_snf: record_lab_test,
});

function record_lab_test(frm) {
	// Each new lab reading is a (re)test: stamp who entered it and when.
	frm.set_value("tested_by", frappe.session.user);
	frm.set_value("test_datetime", frappe.datetime.now_datetime());
	recompute(frm);
}

function compute_lab_result(frm) {
	const tf = flt(frm.doc.tested_fat);
	const ts = flt(frm.doc.tested_snf);
	if (!(tf && ts)) {
		frm.set_value("tested_fat_deviation", 0);
		frm.set_value("tested_snf_deviation", 0);
		frm.set_value("lab_in_spec", 0);
		return;
	}
	const fd = tf - flt(frm.doc.target_fat);
	const sd = ts - flt(frm.doc.target_snf);
	frm.set_value("tested_fat_deviation", fd);
	frm.set_value("tested_snf_deviation", sd);
	frm.set_value("lab_in_spec",
		Math.abs(fd) <= flt(frm.doc.fat_tolerance) + 1e-9
		&& Math.abs(sd) <= flt(frm.doc.snf_tolerance) + 1e-9 ? 1 : 0);
}

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
			method: "dairy.milk_standardisation.doctype.milk_standardisation.milk_standardisation.get_item_row_defaults",
			args: { item: row.item },
			callback(r) {
				const d = r.message || {};
				frappe.model.set_value(cdt, cdn, "uom", d.uom || d.stock_uom);
				frappe.model.set_value(cdt, cdn, "kg_per_stock_unit", d.kg_per_stock_unit || 1);
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
	const qty_kg = stock_qty * (flt(row.kg_per_stock_unit) || 1);
	frappe.model.set_value(cdt, cdn, "stock_qty", stock_qty);
	frappe.model.set_value(cdt, cdn, "qty_kg", qty_kg);
	frappe.model.set_value(cdt, cdn, "kg_fat", qty_kg * flt(row.fat) / 100);
	frappe.model.set_value(cdt, cdn, "kg_snf", qty_kg * flt(row.snf) / 100);
	recompute(frm);
}

function recompute(frm) {
	let q = 0, kf = 0, ks = 0;
	(frm.doc.ingredients || []).forEach((r) => {
		const kg = flt(r.qty) * (flt(r.conversion_factor) || 1) * (flt(r.kg_per_stock_unit) || 1);
		q += kg;
		kf += kg * flt(r.fat) / 100;
		ks += kg * flt(r.snf) / 100;
	});
	const af = q > 0 ? kf / q * 100 : 0;
	const as = q > 0 ? ks / q * 100 : 0;
	frm.set_value("total_qty", q);
	// What gets posted to stock, in the milk base's own unit.
	frm.set_value("output_qty", q / (flt(frm.doc.__kg_per_base_unit) || 1));
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
	compute_lab_result(frm);
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
	} else if (!(flt(frm.doc.tested_fat) && flt(frm.doc.tested_snf))) {
		frm.dashboard.set_headline(
			__("Blend in spec — achieved {0}% FAT / {1}% SNF. Mix the batch, then enter the lab result to submit.",
				[format_number(frm.doc.achieved_fat, null, 3), format_number(frm.doc.achieved_snf, null, 3)]),
			"blue"
		);
	} else if (!frm.doc.lab_in_spec) {
		frm.dashboard.set_headline(
			__("Lab result out of tolerance — tested {0}% FAT / {1}% SNF vs target {2} / {3}. Adjust quantities, mix and retest.",
				[format_number(frm.doc.tested_fat, null, 3), format_number(frm.doc.tested_snf, null, 3),
					frm.doc.target_fat, frm.doc.target_snf]),
			"red"
		);
	} else {
		const suffix = target ? __(" · total {0} / target {1}", [format_number(frm.doc.total_qty, null, 2), format_number(target, null, 2)]) : "";
		frm.dashboard.set_headline(
			__("In spec — lab tested {0}% FAT / {1}% SNF.",
				[format_number(frm.doc.tested_fat, null, 3), format_number(frm.doc.tested_snf, null, 3)]) + suffix,
			"green"
		);
	}
}

function get_silo_milk(frm) {
	// One row per silo holding milk, with the lab's latest quality (or the ledger's).
	frappe.call({
		method: "dairy.milk_standardisation.doctype.milk_standardisation.milk_standardisation.get_silo_milk_rows",
		args: { company: frm.doc.company },
		freeze: true,
		freeze_message: __("Reading the silos..."),
		callback(r) {
			if (!r.message || !r.message.length) return;
			// Replace milk rows only; additives already on the sheet stay.
			const additives = (frm.doc.ingredients || []).filter((x) => !x.available_qty_kg && !x.quality_source);
			frm.clear_table("ingredients");
			r.message.forEach((x) => add_row(frm, x));
			additives.forEach((x) => add_row(frm, x));
			frm.refresh_field("ingredients");
			recompute(frm);
			const stale = r.message.filter((x) => x.quality_source !== "Silo Quality Test").length;
			frappe.show_alert({
				message: stale
					? __("{0} silo(s) loaded. {1} used the ledger's quality — no recent lab test.", [r.message.length, stale])
					: __("{0} silo(s) loaded with the lab's latest test.", [r.message.length]),
				indicator: stale ? "orange" : "green",
			});
		},
	});
}

function add_row(frm, x) {
	const row = frm.add_child("ingredients");
	Object.assign(row, x);
	const sq = flt(x.qty) * (flt(x.conversion_factor) || 1);
	const kg = sq * (flt(x.kg_per_stock_unit) || 1);
	row.stock_qty = sq;
	row.qty_kg = kg;
	row.kg_fat = kg * flt(x.fat) / 100;
	row.kg_snf = kg * flt(x.snf) / 100;
	return row;
}

function suggest_quantities(frm) {
	frappe.call({
		method: "dairy.milk_standardisation.doctype.milk_standardisation.milk_standardisation.suggest_quantities",
		args: { doc: frm.doc },
		freeze: true,
		freeze_message: __("Solving additive quantities..."),
		callback(r) {
			if (!r.message || !r.message.length) return;
			// Auto solves the whole recipe (scaled milk + additives) to hit the target
			// batch quantity exactly, so replace the entire table with the result.
			frm.clear_table("ingredients");
			r.message.forEach((x) => add_row(frm, x));
			frm.refresh_field("ingredients");
			recompute(frm);
			frappe.show_alert({ message: __("Recipe solved to the target batch quantity."), indicator: "green" });
		},
	});
}
