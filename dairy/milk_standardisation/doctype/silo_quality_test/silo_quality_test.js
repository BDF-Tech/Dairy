// Copyright (c) 2026, BDF and contributors
// For license information, please see license.txt

frappe.ui.form.on("Silo Quality Test", {
	setup(frm) {
		frm.set_query("silo", () => ({ filters: { custom_is_milk_silo: 1, is_group: 0, disabled: 0 } }));
		frm.set_query("item", () => ({ filters: { maintain_fat_snf_clr: 1, disabled: 0 } }));
	},

	refresh(frm) {
		show_difference(frm);
	},

	silo: fetch_book,
	item: fetch_book,
	fat: show_difference,
	snf: show_difference,
});

function fetch_book(frm) {
	// What the ERP believes is in the silo, so the lab sees both figures side by side.
	if (!(frm.doc.silo && frm.doc.item)) return;
	frappe.call({
		method: "dairy.milk_standardisation.silo.get_quality",
		args: { warehouse: frm.doc.silo, item_code: frm.doc.item },
		callback(r) {
			const d = r.message || {};
			frm.set_value("book_qty", d.qty || 0);
			frm.set_value("book_fat", d.fat || 0);
			frm.set_value("book_snf", d.snf || 0);
			show_difference(frm);
		},
	});
}

function show_difference(frm) {
	frm.dashboard.clear_headline();
	if (!(frm.doc.fat && frm.doc.book_fat)) return;

	const fd = flt(frm.doc.fat) - flt(frm.doc.book_fat);
	const sd = flt(frm.doc.snf) - flt(frm.doc.book_snf);
	frm.set_value("fat_difference", fd);
	frm.set_value("snf_difference", sd);

	// A small gap is normal sampling spread; a big one means an entry is wrong.
	const off = Math.abs(fd) > 0.2 || Math.abs(sd) > 0.3;
	frm.dashboard.set_headline(
		__("Tested {0}% FAT / {1}% SNF · ERP says {2} / {3} · difference {4} / {5}",
			[format_number(frm.doc.fat, null, 2), format_number(frm.doc.snf, null, 2),
				format_number(frm.doc.book_fat, null, 2), format_number(frm.doc.book_snf, null, 2),
				format_number(fd, null, 2), format_number(sd, null, 2)]),
		off ? "orange" : "green"
	);
}
