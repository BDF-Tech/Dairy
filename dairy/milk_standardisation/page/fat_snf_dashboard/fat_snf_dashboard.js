// Copyright (c) 2026, BDF and contributors
// For license information, please see license.txt

frappe.pages["fat-snf-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("FAT & SNF Dashboard"),
		single_column: true,
	});

	// Colours come from the desk's CSS variables, so both themes stay readable.
	if (!$("#fsd-styles").length) {
		$(`<style id="fsd-styles">
			.fsd-wrap { padding: 0 0 2rem; }
			.fsd-section { margin-top: 1.5rem; }
			.fsd-section > h5 { margin-bottom: .75rem; font-size: var(--text-md); color: var(--text-light); }
			.fsd-cards { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); }
			.fsd-card { background: var(--card-bg); border: 1px solid var(--border-color);
				border-radius: var(--border-radius-md); padding: 14px 16px; }
			.fsd-card .fsd-title { font-weight: 600; margin-bottom: 2px; }
			.fsd-card .fsd-sub { color: var(--text-muted); font-size: var(--text-sm); margin-bottom: 10px; }
			.fsd-big { font-size: 1.45rem; font-weight: 600; line-height: 1.2; }
			.fsd-row { display: flex; justify-content: space-between; font-size: var(--text-sm);
				padding: 2px 0; color: var(--text-light); }
			.fsd-row span:last-child { font-weight: 600; color: var(--text-color); }
			.fsd-bar { height: 6px; border-radius: 3px; background: var(--bg-light-gray); margin-top: 10px; overflow: hidden; }
			.fsd-bar > div { height: 100%; background: var(--blue-500); }
			.fsd-flow { display: grid; gap: 12px; grid-template-columns: repeat(auto-fill, minmax(195px, 1fr)); }
			.fsd-flow .fsd-card .fsd-sub { margin-bottom: 6px; }
			.fsd-sep { border-top: 1px dashed var(--border-color); margin: 8px 0 4px; }
			.fsd-muted { color: var(--text-muted); }
			.fsd-pos { color: var(--green-600); }
			.fsd-neg { color: var(--red-600); }
			.fsd-warn { color: var(--orange-600); }
			.fsd-table { width: 100%; font-size: var(--text-sm); }
			.fsd-table th { text-align: left; color: var(--text-muted); font-weight: 500;
				padding: 6px 10px; border-bottom: 1px solid var(--border-color); white-space: nowrap; }
			.fsd-table td { padding: 6px 10px; border-bottom: 1px solid var(--border-color); white-space: nowrap; }
			.fsd-table td.num, .fsd-table th.num { text-align: right; }
			.fsd-empty { color: var(--text-muted); padding: 1rem 0; }
			.fsd-tabs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 10px; }
			.fsd-tab { border: 1px solid var(--border-color); background: var(--card-bg);
				border-radius: var(--border-radius-full); padding: 4px 12px; font-size: var(--text-sm);
				cursor: pointer; color: var(--text-light); }
			.fsd-tab.active { background: var(--bg-blue); border-color: var(--blue-300); color: var(--blue-600);
				font-weight: 600; }
			.fsd-tab .fsd-count { color: var(--text-muted); font-weight: 400; margin-left: 4px; }
			.fsd-scroll { overflow-x: auto; }
		</style>`).appendTo("body");
	}

	const body = $(`<div class="fsd-wrap">
		<div id="fsd-silos" class="fsd-section"></div>
		<div id="fsd-flow" class="fsd-section"></div>
		<div id="fsd-checks" class="fsd-section"></div>
		<div id="fsd-stages" class="fsd-section"></div>
		<div id="fsd-trail" class="fsd-section"></div>
	</div>`).appendTo(page.body);

	const company = page.add_field({
		fieldname: "company", label: __("Company"), fieldtype: "Link", options: "Company",
		default: frappe.defaults.get_user_default("Company"), reqd: 1,
		change: () => load(),
	});
	const from_date = page.add_field({
		fieldname: "from_date", label: __("From Date"), fieldtype: "Date",
		default: frappe.datetime.month_start(), change: () => load(),
	});
	const to_date = page.add_field({
		fieldname: "to_date", label: __("To Date"), fieldtype: "Date",
		default: frappe.datetime.get_today(), change: () => load(),
	});
	page.set_primary_action(__("Refresh"), () => load(), "refresh");

	const num = (v, d = 1) => format_number(flt(v), null, d);
	const pct = (v) => `${format_number(flt(v), null, 3)}%`;
	const esc = (v) => frappe.utils.escape_html(v || "");
	const link = (doctype, name) =>
		`<a href="/app/${frappe.router.slug(doctype)}/${encodeURIComponent(name)}">${esc(name)}</a>`;

	let trail = {};
	let stage = "inward";

	function load() {
		const args = {
			company: company.get_value(),
			from_date: from_date.get_value(),
			to_date: to_date.get_value(),
		};
		if (!args.company || !args.from_date || !args.to_date) return;

		frappe.call({
			method: "dairy.milk_standardisation.page.fat_snf_dashboard.fat_snf_dashboard.get_dashboard_data",
			args,
			freeze: true,
			freeze_message: __("Reading the milk ledger..."),
			callback(r) {
				if (!r.message) return;
				trail = r.message.trail || {};
				render_silos(r.message.silos);
				render_flow(r.message.flow);
				render_checks(r.message.checks);
				render_stages(r.message.stages);
				render_trail();
			},
		});
	}

	function render_silos(silos) {
		const el = body.find("#fsd-silos").empty();
		$(`<h5>${__("Silos now")}</h5>`).appendTo(el);
		if (!silos || !silos.length) {
			$(`<div class="fsd-empty">${__("No warehouse has 'Is Milk Silo' ticked.")}</div>`).appendTo(el);
			return;
		}
		const cards = $('<div class="fsd-cards"></div>').appendTo(el);
		silos.forEach((s) => {
			const full = Math.min(flt(s.full_pct), 100);
			// A lab reading that has drifted from the book figure is the thing to look at.
			const gap = s.fat_gap === null || s.fat_gap === undefined
				? `<span class="fsd-muted">${__("no test")}</span>`
				: `<span class="${Math.abs(flt(s.fat_gap)) > 0.2 ? "fsd-warn" : "fsd-pos"}">${num(s.fat_gap, 3)}</span>`;
			$(`<div class="fsd-card">
				<div class="fsd-title">${esc(s.silo)}</div>
				<div class="fsd-sub">${s.item ? esc(s.item) : __("empty")}</div>
				<div class="fsd-big">${num(s.qty_kg)} <span class="fsd-sub">kg</span></div>
				<div class="fsd-row"><span>${__("Litres")}</span><span>${num(s.qty_litre)} L</span></div>
				<div class="fsd-row"><span>${__("FAT / SNF")}</span><span>${pct(s.fat)} / ${pct(s.snf)}</span></div>
				<div class="fsd-row"><span>${__("Kg FAT / SNF")}</span><span>${num(s.kg_fat)} / ${num(s.kg_snf)}</span></div>
				<div class="fsd-row"><span>${__("Lab FAT")}</span><span>${s.tested_fat ? pct(s.tested_fat) : "&mdash;"}</span></div>
				<div class="fsd-row"><span>${__("Lab vs book")}</span><span>${gap}</span></div>
				<div class="fsd-bar"><div style="width:${full}%"></div></div>
				<div class="fsd-row"><span>${__("Capacity")}</span><span>${num(s.capacity, 0)} kg &middot; ${num(full, 0)}%</span></div>
			</div>`).appendTo(cards);
		});
	}

	function render_flow(f) {
		const el = body.find("#fsd-flow").empty();
		$(`<h5>${__("Milk and fat in the period")}</h5>`).appendTo(el);
		const cards = $('<div class="fsd-flow"></div>').appendTo(el);
		(f.tiles || []).forEach((t) => {
			$(`<div class="fsd-card">
				<div class="fsd-title">${esc(t.label)}</div>
				<div class="fsd-sub">${esc(t.sub)}</div>
				<div class="fsd-big">${num(t.kg)} <span class="fsd-sub">kg</span></div>
				<div class="fsd-row"><span>${__("Litres")}</span><span>${num(t.litre)} L</span></div>
				<div class="fsd-sep"></div>
				<div class="fsd-row"><span>${__("Kg FAT")}</span><span>${num(t.fat, 2)}</span></div>
				<div class="fsd-row"><span>${__("Kg SNF")}</span><span>${num(t.snf, 2)}</span></div>
				<div class="fsd-row"><span>${__("FAT / SNF")}</span><span>${pct(t.fat_pct)} / ${pct(t.snf_pct)}</span></div>
			</div>`).appendTo(cards);
		});
	}

	function render_checks(c) {
		const el = body.find("#fsd-checks").empty();
		if (!c) return;
		$(`<h5>${__("Can these figures be trusted?")}</h5>`).appendTo(el);
		const cards = $('<div class="fsd-cards"></div>').appendTo(el);

		const bad = flt(c.untracked_pct) > 1;
		$(`<div class="fsd-card">
			<div class="fsd-title">${__("Milk moved with no FAT recorded")}</div>
			<div class="fsd-sub">${__("the holes in the fat book")}</div>
			<div class="fsd-big ${bad ? "fsd-neg" : "fsd-pos"}">${num(c.untracked_pct, 1)}%</div>
			<div class="fsd-row"><span>${__("Quantity")}</span><span>${num(c.untracked_kg)} kg</span></div>
			<div class="fsd-row"><span>${__("Rows")}</span><span>${num(c.untracked_rows, 0)} / ${num(c.untracked_of_rows, 0)}</span></div>
		</div>`).appendTo(cards);

		$(`<div class="fsd-card">
			<div class="fsd-title">${__("Ledger quantity vs stock")}</div>
			<div class="fsd-sub">${__("closed by a reconciliation")}</div>
			<div class="fsd-big ${flt(c.ledger_off_warehouses) ? "fsd-warn" : "fsd-pos"}">${num(c.ledger_off_kg)} <span class="fsd-sub">kg</span></div>
			<div class="fsd-row"><span>${__("Warehouses out of step")}</span><span>${num(c.ledger_off_warehouses, 0)}</span></div>
		</div>`).appendTo(cards);

		$(`<div class="fsd-card">
			<div class="fsd-title">${__("Fat with no milk under it")}</div>
			<div class="fsd-sub">${__("booked where stock is nil")}</div>
			<div class="fsd-big ${flt(c.stranded_fat) ? "fsd-warn" : "fsd-pos"}">${num(c.stranded_fat)} <span class="fsd-sub">kg</span></div>
			<div class="fsd-row"><span>${__("Warehouses")}</span><span>${num(c.stranded_rows, 0)}</span></div>
		</div>`).appendTo(cards);

		if ((c.untracked || []).length) {
			const t = $(`<div class="fsd-scroll" style="margin-top:12px"><table class="fsd-table"><thead><tr>
				<th>${__("Document Type")}</th><th class="num">${__("Rows With No FAT")}</th>
				<th class="num">${__("Kg")}</th><th class="num">${__("Litre")}</th>
				<th class="num">${__("Share Of Its Movement")}</th>
				</tr></thead><tbody></tbody></table></div>`).appendTo(el);
			c.untracked.forEach((u) => {
				t.find("tbody").append(`<tr>
					<td>${esc(u.voucher_type)}</td>
					<td class="num">${num(u.blank_rows, 0)} / ${num(u.all_rows, 0)}</td>
					<td class="num">${num(u.blank_kg)}</td>
					<td class="num">${num(u.blank_litre)}</td>
					<td class="num ${flt(u.pct) > 1 ? "fsd-neg" : "fsd-pos"}">${num(u.pct, 1)}%</td></tr>`);
			});
		}
	}

	function render_stages(stages) {
		const el = body.find("#fsd-stages").empty();
		$(`<h5>${__("Where fat is lost")}</h5>`).appendTo(el);
		if (!stages || !stages.length) {
			$(`<div class="fsd-empty">${__("Nothing moved in this period.")}</div>`).appendTo(el);
			return;
		}
		const t = $(`<div class="fsd-scroll"><table class="fsd-table"><thead><tr>
			<th>${__("Stage")}</th><th class="num">${__("Kg In")}</th><th class="num">${__("Litre In")}</th>
			<th class="num">${__("Kg Out")}</th><th class="num">${__("Litre Out")}</th>
			<th class="num">${__("Kg FAT In")}</th>
			<th class="num">${__("Kg FAT Out")}</th><th class="num">${__("Gap")}</th>
			<th class="num">${__("Gap %")}</th></tr></thead><tbody></tbody></table></div>`).appendTo(el);
		stages.forEach((s) => {
			const cls = Math.abs(flt(s.gap_pct)) > 1 ? "fsd-neg" : "fsd-muted";
			t.find("tbody").append(`<tr>
				<td>${esc(s.stage)}</td>
				<td class="num">${num(s.kg_in)}</td>
				<td class="num">${num(s.litre_in)}</td>
				<td class="num">${num(s.kg_out)}</td>
				<td class="num">${num(s.litre_out)}</td>
				<td class="num">${num(s.fat_in, 2)}</td>
				<td class="num">${num(s.fat_out, 2)}</td>
				<td class="num ${cls}">${num(s.gap, 2)}</td>
				<td class="num ${cls}">${num(s.gap_pct, 2)}%</td></tr>`);
		});
		$(`<div class="fsd-sub" style="margin-top:6px">${__(
			"Fat that came in against fat that went out, within the period only. Opening and closing stock are not in these two columns, so read the gap beside the stage's own balance."
		)}</div>`).appendTo(el);
	}

	// ------------------------------------------------------------ the stage trail
	const STAGES = [
		["inward", __("Inward")],
		["quality", __("Quality Test")],
		["standardisation", __("Standardisation")],
		["manufacture", __("Manufacturing")],
		["outward", __("Outward")],
		["left", __("Left")],
	];

	function render_trail() {
		const el = body.find("#fsd-trail").empty();
		$(`<h5>${__("Every batch, stage by stage")}</h5>`).appendTo(el);
		const tabs = $('<div class="fsd-tabs"></div>').appendTo(el);
		STAGES.forEach(([key, label]) => {
			const n = (trail[key] || []).length;
			$(`<div class="fsd-tab ${key === stage ? "active" : ""}" data-stage="${key}">
				${label}<span class="fsd-count">${n}</span></div>`).appendTo(tabs);
		});
		tabs.find(".fsd-tab").on("click", function () {
			stage = $(this).data("stage");
			render_trail();
		});

		const rows = trail[stage] || [];
		const holder = $('<div class="fsd-scroll"></div>').appendTo(el);
		if (!rows.length) {
			$(`<div class="fsd-empty">${__("Nothing at this stage in the period.")}</div>`).appendTo(holder);
			return;
		}
		({
			quality: render_quality,
			standardisation: render_batches,
			left: render_left,
		}[stage] || render_docs)(holder, rows);
	}

	function render_docs(holder, rows) {
		const t = $(`<table class="fsd-table"><thead><tr>
			<th>${__("Document")}</th><th>${__("Date")}</th><th>${__("Item / Source")}</th>
			<th>${__("Warehouse")}</th><th class="num">${__("Kg")}</th><th class="num">${__("Litre")}</th>
			<th class="num">${__("Kg FAT")}</th><th class="num">${__("Kg SNF")}</th>
			<th class="num">${__("FAT")}</th><th class="num">${__("SNF")}</th>
			</tr></thead><tbody></tbody></table>`).appendTo(holder);
		rows.forEach((r) => {
			const fat = flt(r.kg_fat)
				? `${num(r.fat, 2)}%`
				: `<span class="fsd-warn" title="${__("No fat recorded on this document")}">&mdash;</span>`;
			t.find("tbody").append(`<tr>
				<td>${link(r.doctype, r.doc)}</td>
				<td>${r.date ? frappe.datetime.str_to_user(r.date) : ""}</td>
				<td>${esc(r.what)}${r.note ? ` <span class="fsd-muted">${esc(r.note)}</span>` : ""}</td>
				<td class="fsd-muted">${esc(r.where)}</td>
				<td class="num">${num(r.kg)}</td>
				<td class="num">${num(r.litre)}</td>
				<td class="num">${num(r.kg_fat, 2)}</td>
				<td class="num">${num(r.kg_snf, 2)}</td>
				<td class="num">${fat}</td>
				<td class="num">${flt(r.kg_snf) ? num(r.snf, 2) + "%" : "&mdash;"}</td></tr>`);
		});
	}

	function render_quality(holder, rows) {
		const t = $(`<table class="fsd-table"><thead><tr>
			<th>${__("Test")}</th><th>${__("When")}</th><th>${__("Silo")}</th><th>${__("Item")}</th>
			<th class="num">${__("Kg")}</th><th class="num">${__("Litre")}</th>
			<th class="num">${__("Lab FAT / SNF")}</th><th class="num">${__("Book FAT / SNF")}</th>
			<th class="num">${__("FAT Diff")}</th><th class="num">${__("Kg FAT")}</th>
			</tr></thead><tbody></tbody></table>`).appendTo(holder);
		rows.forEach((r) => {
			const cls = Math.abs(flt(r.fat_difference)) > 0.2 ? "fsd-warn" : "fsd-pos";
			t.find("tbody").append(`<tr>
				<td>${link("Silo Quality Test", r.name)}</td>
				<td>${frappe.datetime.str_to_user(r.posting_datetime)}</td>
				<td>${esc(r.silo)}</td>
				<td>${esc(r.item)}</td>
				<td class="num">${num(r.tested_qty)}</td>
				<td class="num">${num(r.qty_litre)}</td>
				<td class="num">${num(r.fat, 2)} / ${num(r.snf, 2)}</td>
				<td class="num fsd-muted">${num(r.book_fat, 2)} / ${num(r.book_snf, 2)}</td>
				<td class="num ${cls}">${num(r.fat_difference, 3)}</td>
				<td class="num">${num(r.kg_fat, 2)}</td></tr>`);
		});
	}

	function render_batches(holder, rows) {
		const t = $(`<table class="fsd-table"><thead><tr>
			<th>${__("Batch")}</th><th>${__("When")}</th><th>${__("Milk Base")}</th>
			<th class="num">${__("Kg")}</th><th class="num">${__("Litre")}</th>
			<th class="num">${__("Kg FAT")}</th><th class="num">${__("Target")}</th>
			<th class="num">${__("Achieved")}</th><th class="num">${__("Lab")}</th>
			<th class="num">${__("Lab vs blend")}</th><th>${__("Made")}</th>
			</tr></thead><tbody></tbody></table>`).appendTo(holder);
		rows.forEach((b) => {
			const cls = Math.abs(flt(b.fat_gap)) > 0.1 ? "fsd-warn" : "fsd-pos";
			const made = [
				b.work_order ? link("Work Order", b.work_order) : "",
				b.stock_entry ? link("Stock Entry", b.stock_entry) : "",
			].filter(Boolean).join(" &middot; ");
			t.find("tbody").append(`<tr>
				<td>${link("Milk Standardisation", b.name)}</td>
				<td>${frappe.datetime.str_to_user(b.posting_datetime)}</td>
				<td>${esc(b.finished_item)}</td>
				<td class="num">${num(b.total_qty)}</td>
				<td class="num">${num(b.qty_litre)}</td>
				<td class="num">${num(b.kg_fat, 2)}</td>
				<td class="num">${num(b.target_fat, 2)} / ${num(b.target_snf, 2)}</td>
				<td class="num">${num(b.achieved_fat, 3)} / ${num(b.achieved_snf, 3)}</td>
				<td class="num">${b.tested_fat ? num(b.tested_fat, 2) + " / " + num(b.tested_snf, 2) : "&mdash;"}</td>
				<td class="num ${cls}">${b.tested_fat ? num(b.fat_gap, 3) : "&mdash;"}</td>
				<td class="fsd-muted">${made || "&mdash;"}</td></tr>`);
		});
	}

	function render_left(holder, rows) {
		const t = $(`<table class="fsd-table"><thead><tr>
			<th>${__("Warehouse")}</th><th>${__("Item")}</th><th class="num">${__("Stock Qty")}</th>
			<th class="num">${__("Kg")}</th><th class="num">${__("Litre")}</th>
			<th class="num">${__("Ledger Qty")}</th><th class="num">${__("Difference")}</th>
			<th class="num">${__("Kg FAT")}</th><th class="num">${__("Kg SNF")}</th>
			<th class="num">${__("FAT")}</th><th class="num">${__("SNF")}</th>
			</tr></thead><tbody></tbody></table>`).appendTo(holder);
		rows.forEach((r) => {
			// A percentage far outside 0-15 means that warehouse's ledger needs a
			// reconciliation, not that the milk is unusual.
			const odd = flt(r.fat) < 0 || flt(r.fat) > 15;
			const diff = Math.abs(flt(r.qty_diff)) > 1 ? "fsd-warn" : "fsd-muted";
			t.find("tbody").append(`<tr>
				<td>${link("Warehouse", r.doc)}</td>
				<td>${esc(r.what)}${r.stranded ? ` <span class="fsd-warn">${__("no stock")}</span>` : ""}</td>
				<td class="num">${num(r.qty)}</td>
				<td class="num">${num(r.kg)}</td>
				<td class="num">${num(r.litre)}</td>
				<td class="num fsd-muted">${num(r.ledger_qty)}</td>
				<td class="num ${diff}">${num(r.qty_diff)}</td>
				<td class="num">${num(r.kg_fat, 2)}</td>
				<td class="num">${num(r.kg_snf, 2)}</td>
				<td class="num ${odd ? "fsd-neg" : ""}">${num(r.fat, 2)}%</td>
				<td class="num ${odd ? "fsd-neg" : ""}">${num(r.snf, 2)}%</td></tr>`);
		});
	}

	load();
};
