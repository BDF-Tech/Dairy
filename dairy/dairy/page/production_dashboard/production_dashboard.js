frappe.pages['production-dashboard'].on_page_load = function (wrapper) {

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Production Dashboard',
		single_column: true
	});

	// ======================
	// LOADER & THEME-AWARE STYLES
	// All colours come from Frappe CSS variables so contrast stays correct in
	// both the light and dark desk themes (no hardcoded white/grey).
	// ======================
	$(`
		<div id="prod-dash-loader" style="
			position:fixed; top:0; left:0; width:100%; height:100%;
			background: rgba(127,127,127,0.25); backdrop-filter: blur(3px);
			display:none; align-items:center; justify-content:center; z-index:10001;">
			<div class="prod-spinner"><div></div><div></div><div></div><div></div></div>
		</div>
	`).appendTo('body');

	if ($('#prod-dash-styles').length === 0) {
		$(`<style id="prod-dash-styles">
		.prod-spinner { display:inline-block; position:relative; width:64px; height:64px; }
		.prod-spinner div { box-sizing:border-box; display:block; position:absolute; width:51px; height:51px; margin:6px; border:4px solid var(--primary, #2563eb); border-radius:50%; animation:prod-spin 1.2s linear infinite; border-color:var(--primary, #2563eb) transparent transparent transparent; }
		.prod-spinner div:nth-child(1){ animation-delay:-0.45s; }
		.prod-spinner div:nth-child(2){ animation-delay:-0.3s; }
		.prod-spinner div:nth-child(3){ animation-delay:-0.15s; }
		@keyframes prod-spin { 0%{ transform:rotate(0deg);} 100%{ transform:rotate(360deg);} }

		.prod-summary-bar { display:flex; flex-wrap:wrap; gap:20px; padding:14px 18px; background:var(--subtle-fg, var(--control-bg)); border:1px solid var(--border-color); border-radius:var(--border-radius-lg, 12px); }
		.prod-stat { flex:1; min-width:150px; }
		.prod-stat .l, .prod-hstat .l { font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600; letter-spacing:.3px; }
		.prod-stat .v { font-size:22px; font-weight:700; }
		.prod-hstat { line-height:1.15; }
		.prod-hstat .v { font-size:15px; font-weight:700; }

		.prod-chart-wrap { background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-lg, 12px); padding:10px 15px; }
		#prod-chart text { fill:var(--text-muted) !important; }
		#prod-chart .title { fill:var(--text-color) !important; font-weight:600; }

		.prod-card { background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-lg, 12px); padding:16px; box-shadow:var(--card-shadow, none); }
		.prod-card table { width:100%; border-collapse:collapse; margin-top:6px; }
		.prod-card th { text-align:left; font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:600; padding:4px 6px; border-bottom:1px solid var(--border-color); }
		.prod-card td { font-size:12.5px; color:var(--text-color); padding:4px 6px; border-bottom:1px solid var(--border-color); }
		.prod-card tr:last-child td { border-bottom:none; }

		.prod-title { font-weight:600; font-size:15px; color:var(--heading-color, var(--text-color)); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
		.prod-sub { font-size:12px; color:var(--text-muted); }
		.prod-label { font-size:11px; text-transform:uppercase; color:var(--text-muted); font-weight:600; letter-spacing:.3px; }
		.prod-strong { color:var(--text-color); font-weight:500; }
		.prod-muted { color:var(--text-muted); }
		.prod-green { color:var(--green-600, #16a34a); }
		.prod-red { color:var(--red-600, #dc2626); }
		.prod-blue { color:var(--blue-600, #2563eb); }
		.prod-cyan { color:var(--cyan-600, #0891b2); }
		.prod-orange { color:var(--orange-600, #ea580c); }

		/* High-contrast, unmistakably clickable Stock Entry links. */
		.prod-link { color:var(--text-color); text-decoration:underline; text-decoration-color:var(--text-muted); text-underline-offset:2px; font-family:var(--font-stack-monospace, monospace); font-weight:500; }
		.prod-link:hover { color:var(--primary, #2563eb); text-decoration-color:var(--primary, #2563eb); }

		.prod-loss-box { margin-top:12px; padding:8px 10px; border-radius:var(--border-radius-md, 8px); border:1px solid var(--border-color); background:var(--subtle-fg, var(--control-bg)); }
		.prod-se-row { display:flex; justify-content:space-between; gap:8px; font-size:12px; padding:5px 0; border-bottom:1px solid var(--border-color); }
		.prod-se-row:last-child { border-bottom:none; }
		</style>`).appendTo('head');
	}

	const fmt = (v) => parseFloat((Number(v) || 0).toFixed(2)).toLocaleString('en-IN');
	const esc = frappe.utils.escape_html;

	function show_loader() { $("#prod-dash-loader").css('display', 'flex'); }
	function hide_loader() { $("#prod-dash-loader").hide(); }

	// ======================
	// FILTERS
	// ======================
	let company = page.add_field({
		label: 'Company', fieldtype: 'Link', options: 'Company',
		default: frappe.defaults.get_user_default('Company')
	});

	let period = page.add_field({
		label: 'Period', fieldtype: 'Select',
		options: ['Today', 'Weekly', 'Monthly', 'Quarterly', 'Half Yearly', 'Yearly', 'Custom'],
		default: 'Today',
		change() { on_period_change(); }
	});

	// Dependent selectors that "extend" from Period (shown only when relevant).
	let year_sel = page.add_field({ label: 'Year', fieldtype: 'Select', change() { apply_period(); } });
	let sub_sel = page.add_field({ label: 'Sub Period', fieldtype: 'Select', change() { apply_period(); } });
	$(year_sel.wrapper).hide();
	$(sub_sel.wrapper).hide();

	let from_date = page.add_field({ label: 'From Date', fieldtype: 'Date' });
	let to_date = page.add_field({ label: 'To Date', fieldtype: 'Date' });

	let item_group = page.add_field({ label: 'Item Group', fieldtype: 'Link', options: 'Item Group' });

	let item_code = page.add_field({ label: 'Item', fieldtype: 'Link', options: 'Item' });

	// Stock Entry picker limited to Manufacture entries inside the chosen date range.
	let stock_entry = page.add_field({
		label: 'Stock Entry', fieldtype: 'Link', options: 'Stock Entry',
		get_query() {
			return {
				filters: {
					stock_entry_type: 'Manufacture',
					docstatus: 1,
					posting_date: ['between', [from_date.get_value(), to_date.get_value()]]
				}
			};
		}
	});

	let group_by = page.add_field({
		label: 'Group By', fieldtype: 'Select',
		options: ['Stock Entry', 'Item'], default: 'Stock Entry'
	});

	let show = page.add_field({
		label: 'Show', fieldtype: 'Select',
		options: ['50', '100', '250', 'All'], default: '50'
	});

	const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
		'July', 'August', 'September', 'October', 'November', 'December'];

	function year_options() {
		let y = moment().year(), arr = [];
		for (let i = 0; i < 6; i++) arr.push(String(y - i));
		return arr;
	}

	// Reveal + populate the Year / Sub-period selectors based on the Period type.
	function on_period_change() {
		let p = period.get_value();
		let today = frappe.datetime.get_today();
		$(year_sel.wrapper).hide();
		$(sub_sel.wrapper).hide();

		if (p === 'Today') { from_date.set_value(today); to_date.set_value(today); return; }
		if (p === 'Weekly') { from_date.set_value(frappe.datetime.add_days(today, -7)); to_date.set_value(today); return; }
		if (p === 'Custom') { return; }

		let yopts = p === 'Yearly' ? year_options().concat(['All']) : year_options();
		year_sel.df.options = yopts.join('\n');
		year_sel.refresh();
		if (yopts.indexOf(year_sel.get_value()) < 0) year_sel.set_value(String(moment().year()));
		$(year_sel.wrapper).show();

		if (p === 'Monthly') {
			sub_sel.df.label = __('Month'); sub_sel.df.options = MONTHS.join('\n'); sub_sel.refresh();
			if (MONTHS.indexOf(sub_sel.get_value()) < 0) sub_sel.set_value(MONTHS[moment().month()]);
			$(sub_sel.wrapper).show();
		} else if (p === 'Quarterly') {
			sub_sel.df.label = __('Quarter'); sub_sel.df.options = ['Q1', 'Q2', 'Q3', 'Q4'].join('\n'); sub_sel.refresh();
			if (!/^Q[1-4]$/.test(sub_sel.get_value() || '')) sub_sel.set_value('Q' + (Math.floor(moment().month() / 3) + 1));
			$(sub_sel.wrapper).show();
		} else if (p === 'Half Yearly') {
			sub_sel.df.label = __('Half'); sub_sel.df.options = ['HY1', 'HY2'].join('\n'); sub_sel.refresh();
			if (!/^HY[12]$/.test(sub_sel.get_value() || '')) sub_sel.set_value(moment().month() < 6 ? 'HY1' : 'HY2');
			$(sub_sel.wrapper).show();
		}
		apply_period();
	}

	// Resolve Period + Year + Sub-period into an actual from/to date range.
	function apply_period() {
		let p = period.get_value();
		let y = parseInt(year_sel.get_value(), 10) || moment().year();

		if (p === 'Monthly') {
			let m = MONTHS.indexOf(sub_sel.get_value()); if (m < 0) m = moment().month();
			let start = moment({ year: y, month: m, day: 1 });
			from_date.set_value(start.format('YYYY-MM-DD'));
			to_date.set_value(start.clone().endOf('month').format('YYYY-MM-DD'));
		} else if (p === 'Quarterly') {
			let q = parseInt((sub_sel.get_value() || 'Q1').replace('Q', ''), 10) || 1;
			let start = moment({ year: y, month: (q - 1) * 3, day: 1 });
			from_date.set_value(start.format('YYYY-MM-DD'));
			to_date.set_value(start.clone().add(2, 'months').endOf('month').format('YYYY-MM-DD'));
		} else if (p === 'Half Yearly') {
			let start = moment({ year: y, month: sub_sel.get_value() === 'HY2' ? 6 : 0, day: 1 });
			from_date.set_value(start.format('YYYY-MM-DD'));
			to_date.set_value(start.clone().add(5, 'months').endOf('month').format('YYYY-MM-DD'));
		} else if (p === 'Yearly') {
			if (year_sel.get_value() === 'All') {
				from_date.set_value('2000-01-01');
				to_date.set_value(frappe.datetime.get_today());
			} else {
				from_date.set_value(`${y}-01-01`);
				to_date.set_value(`${y}-12-31`);
			}
		}
	}

	on_period_change();

	// ======================
	// LAYOUT
	// ======================
	let summary_bar = $(`<div id="prod-summary" style="margin-top:15px;"></div>`).appendTo(page.body);
	let chart_wrap = $(`
		<div class="prod-chart-wrap" style="margin-top:20px; display:none;"><div id="prod-chart"></div></div>
	`).appendTo(page.body);
	let cards_wrap = $(`
		<div id="prod-cards" style="margin-top:20px; display:grid; grid-template-columns:repeat(auto-fill, minmax(360px, 1fr)); gap:15px;"></div>
	`).appendTo(page.body);

	let prod_chart = null;

	// Top-right header stats (Total Finished Product / Total Handling Loss).
	let header_stats = $(`<div id="prod-header-stats" style="display:flex; gap:22px; align-items:center; margin-right:14px;"></div>`);
	page.page_actions.prepend(header_stats);

	// ======================
	// LOAD
	// ======================
	page.set_primary_action('Load Data', () => {
		let f = from_date.get_value(), t = to_date.get_value();
		if (!f || !t) { frappe.msgprint('Please select From Date and To Date.'); return; }

		show_loader();
		frappe.call({
			method: 'dairy.dairy.page.production_dashboard.production_dashboard.get_dashboard_data',
			args: {
				from_date: f, to_date: t,
				company: company.get_value() || null,
				item_group: item_group.get_value() || null,
				item_code: item_code.get_value() || null,
				stock_entry: stock_entry.get_value() || null,
				limit: show.get_value(),
				group_by: group_by.get_value()
			},
			callback: (r) => {
				let d = (r && r.message) || { summary: {}, chart: {}, cards: [] };
				render_summary(d.summary || {});
				render_chart(d.chart || {});
				render_cards(d.cards || []);
				hide_loader();
			},
			error: () => hide_loader()
		});
	}, 'refresh');

	// ======================
	// RENDERERS
	// ======================
	function stat(value, label, cls) {
		return `<div class="prod-stat"><div class="l">${label}</div><div class="v ${cls}">${value}</div></div>`;
	}

	function render_summary(s) {
		let uoms = s.produced_by_uom || [];
		let wts = s.weight_by_uom || [];
		let weight_inline = wts.map(x => `${fmt(x.qty)} <span class="prod-muted" style="font-weight:600;">${esc(x.uom)}</span>`).join('<span class="prod-muted"> · </span>');

		// Compact inline breakdown for the header (e.g. "4,800 Nos · 2,400 Litre").
		let header_produced = uoms.length
			? uoms.map(x => `${fmt(x.qty)} <span class="prod-muted" style="font-weight:600;">${esc(x.uom)}</span>`).join('<span class="prod-muted"> · </span>')
			: fmt(s.total_produced_qty || 0);

		header_stats.html(`
			<div class="prod-hstat"><div class="v prod-green" style="font-size:14px; max-width:340px;">${header_produced}</div><div class="l">Total Finished Product</div></div>
			${weight_inline ? `<div class="prod-hstat"><div class="v prod-blue" style="font-size:14px; max-width:240px;">${weight_inline}</div><div class="l">Total Weight</div></div>` : ''}
			<div class="prod-hstat"><div class="v prod-red">${fmt(s.total_handling_loss_qty || 0)}</div><div class="l">Total Handling Loss</div></div>
		`);

		// Stacked breakdown in the summary banner cell.
		let produced_cell = `<div class="prod-stat"><div class="l">Produced Qty</div>` + (uoms.length
			? uoms.map(x => `<div class="v prod-green" style="font-size:16px;">${fmt(x.qty)} <span class="prod-muted" style="font-size:11px; font-weight:600;">${esc(x.uom)}</span></div>`).join('')
			: `<div class="v prod-green">${fmt(s.total_produced_qty || 0)}</div>`) + `</div>`;

		summary_bar.html(`
			<div class="prod-summary-bar">
				${stat(fmt(s.production_runs || 0), 'Production Runs', 'prod-blue')}
				${stat(fmt(s.distinct_items || 0), 'Distinct Items', 'prod-cyan')}
				${produced_cell}
				${wts.length ? `<div class="prod-stat"><div class="l">Total Weight</div>${wts.map(x => `<div class="v prod-blue" style="font-size:16px;">${fmt(x.qty)} <span class="prod-muted" style="font-size:11px; font-weight:600;">${esc(x.uom)}</span></div>`).join('')}</div>` : ''}
				${stat(fmt(s.total_handling_loss_qty || 0), 'Handling Loss', 'prod-red')}
				${stat(fmt(s.runs_with_loss || 0), 'Runs With Loss', 'prod-orange')}
			</div>
		`);
	}

	function render_chart(c) {
		if (!c.labels || !c.labels.length) {
			chart_wrap.hide();
			if (prod_chart) { prod_chart.destroy(); prod_chart = null; }
			return;
		}
		chart_wrap.show();
		let data = {
			labels: c.labels.map(l => l.length > 16 ? l.substring(0, 16) + '…' : l),
			datasets: [
				{ name: 'Produced', values: c.produced },
				{ name: 'Handling Loss', values: c.loss }
			]
		};
		if (prod_chart) { prod_chart.update(data); }
		else {
			prod_chart = new frappe.Chart('#prod-chart', {
				title: 'Top Produced Items (Qty vs Handling Loss)',
				data: data, type: 'bar', height: 300,
				colors: ['#16a34a', '#dc2626'],
				axisOptions: { xAxisMode: 'tick', shortenYAxisNumbers: 1 },
				barOptions: { spaceRatio: 0.4 }
			});
		}
	}

	function render_cards(cards) {
		if (!cards.length) {
			cards_wrap.html(`<div class="text-muted" style="grid-column:1/-1; text-align:center; padding:40px;">No production entries found for the selected filters.</div>`);
			return;
		}

		let html = '';
		cards.forEach(d => {
			let inputs = (d.inputs || []).map(it => `
				<tr>
					<td>${esc(it.item_name || it.item_code || '')}</td>
					<td style="text-align:right; white-space:nowrap;">${fmt(it.qty)}</td>
					<td>${esc(it.uom || '')}</td>
					<td>${esc(it.source_warehouse || '')}</td>
				</tr>`).join('') || `<tr><td colspan="4" class="prod-muted">No inputs recorded</td></tr>`;

			let grouped = d.run_count != null;
			let runs_badge = grouped
				? `<span class="indicator-pill blue" style="margin-left:8px;">${d.run_count}×</span>`
				: '';

			let footer = grouped
				? `<span class="prod-strong">${d.run_count} production run${d.run_count > 1 ? 's' : ''}</span> · ${esc(String(d.posting_date || ''))}`
				: `<a href="/app/stock-entry/${encodeURIComponent(d.stock_entry)}" target="_blank" class="prod-link">${esc(d.stock_entry || '')}</a>${d.work_order ? ' <span class="prod-muted">· ' + esc(d.work_order) + '</span>' : ''} <span class="prod-muted">· ${frappe.datetime.str_to_user(d.posting_date)}</span>`;

			let entries_html = '';
			if (grouped && (d.entries || []).length) {
				let rows = d.entries.map(e => `
					<div class="prod-se-row">
						<a href="/app/stock-entry/${encodeURIComponent(e.stock_entry)}" target="_blank" class="prod-link">${esc(e.stock_entry || '')}</a>
						<span class="prod-strong" style="white-space:nowrap;">
							${fmt(e.produced_qty)} ${esc(e.uom || '')}
							${Number(e.handling_loss_qty) > 0 ? `<span class="prod-red">· loss ${fmt(e.handling_loss_qty)}</span>` : ''}
							<span class="prod-muted">· ${frappe.datetime.str_to_user(e.posting_date)}</span>
						</span>
					</div>`).join('');
				entries_html = `<div style="margin-top:12px;"><div class="prod-label" style="margin-bottom:4px;">Stock Entries (${d.entries.length})</div>${rows}</div>`;
			}

			let has_loss = Number(d.handling_loss_qty) > 0;
			let loss_detail = (d.handling_loss_items || [])
				.map(l => `${esc(l.item_name || l.item_code)} <b>${fmt(l.qty)}</b> ${esc(l.uom || '')}`)
				.join(' &nbsp;·&nbsp; ');

			html += `
				<div class="prod-card">
					<div style="display:flex; justify-content:space-between; align-items:flex-start; gap:10px;">
						<div style="min-width:0;">
							<div class="prod-title">${esc(d.fg_item_name || d.fg_item_code || '')}${runs_badge}</div>
							<div class="prod-sub">${esc(d.fg_item_code || '')}${d.fg_item_group ? ' · ' + esc(d.fg_item_group) : ''}</div>
						</div>
						<div style="text-align:right; white-space:nowrap;">
							<span class="prod-green" style="font-size:20px; font-weight:700;">${fmt(d.produced_qty)}</span>
							<span class="prod-muted" style="font-size:12px;">${esc(d.uom || '')}</span>
							${d.produced_weight ? `<div class="prod-blue" style="font-size:13px; font-weight:600;">${fmt(d.produced_weight)} <span class="prod-muted">${esc(d.weight_uom || '')}</span></div>` : ''}
						</div>
					</div>

					<div style="margin-top:8px; font-size:12px;">
						<span class="prod-strong">${esc(d.source_warehouse || '—')}</span>
						<span class="prod-muted"> → </span>
						<span class="prod-strong">${esc(d.target_warehouse || '—')}</span>
					</div>

					<div class="prod-label" style="margin-top:12px;">Made From</div>
					<table>
						<thead><tr><th>Item</th><th style="text-align:right;">Qty</th><th>UOM</th><th>Source Warehouse</th></tr></thead>
						<tbody>${inputs}</tbody>
					</table>

					<div class="prod-loss-box">
						<span class="indicator-pill ${has_loss ? 'red' : 'green'}">Handling Loss ${fmt(d.handling_loss_qty)}</span>
						${loss_detail ? `<div class="prod-muted" style="font-size:11.5px; margin-top:6px;">${loss_detail}</div>` : ''}
					</div>

					${entries_html}

					<div style="margin-top:10px; font-size:11px;" class="prod-muted">${footer}</div>
				</div>`;
		});
		cards_wrap.html(html);
	}

	// Auto-load on open.
	setTimeout(() => { if (page.btn_primary) page.btn_primary.trigger('click'); }, 150);
};
