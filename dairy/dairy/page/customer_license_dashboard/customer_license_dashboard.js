frappe.pages['customer-license-dashboard'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Customer License Dashboard'),
		single_column: true,
	});

	const METHOD = 'dairy.dairy.page.customer_license_dashboard.customer_license_dashboard';

	// Status -> Frappe indicator colour + section copy. Order = display order.
	const STATUS = {
		'Expired':       { color: 'red',    title: __('Expired'),                    hint: __('Licence has lapsed — renew immediately') },
		'Expiring Soon': { color: 'yellow', title: __('Expiring in next 3 months'),  hint: __('Start the renewal process') },
		'Valid':         { color: 'green',  title: __('Valid'),                      hint: __('More than 3 months remaining') },
		'Not Set':       { color: 'gray',   title: __('Validity not set'),           hint: __('Licence number recorded without a validity date') },
	};
	const ORDER = Object.keys(STATUS);
	const esc = frappe.utils.escape_html;

	// ---------------------------------------------------------------
	// Styles — only Frappe theme variables, so light/dark both work
	// ---------------------------------------------------------------
	if ($('#cld-styles').length === 0) {
		$(`<style id="cld-styles">
		.cld { padding: var(--padding-md, 15px) 0 var(--padding-xl, 30px); }

		/* KPI number cards */
		.cld-kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:var(--margin-md,12px); margin-bottom:var(--margin-lg,20px); }
		.cld-kpi { position:relative; background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-md); box-shadow:var(--card-shadow); padding:var(--padding-md,15px); cursor:pointer; transition:border-color .15s, box-shadow .15s; }
		.cld-kpi:hover { border-color:var(--gray-400); }
		.cld-kpi.active { border-color:var(--primary); box-shadow:0 0 0 1px var(--primary); }
		.cld-kpi-title { display:flex; align-items:center; gap:6px; font-size:var(--text-tiny,11px); font-weight:var(--weight-medium,500); color:var(--text-muted); text-transform:uppercase; letter-spacing:.4px; }
		.cld-kpi-num { font-size:var(--text-2xl,24px); font-weight:var(--weight-semibold,600); color:var(--text-color); line-height:1.2; margin-top:var(--margin-sm,8px); font-variant-numeric:tabular-nums; }
		.cld-kpi-sub { font-size:var(--text-xs,11px); color:var(--text-muted); margin-top:2px; }
		.cld-kpi-bar { height:4px; border-radius:2px; background:var(--gray-100, var(--control-bg)); margin-top:var(--margin-sm,8px); overflow:hidden; }
		.cld-kpi-bar > span { display:block; height:100%; border-radius:2px; }
		.cld-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; }

		/* toolbar */
		.cld-toolbar { display:flex; justify-content:space-between; align-items:center; gap:var(--margin-md,12px); margin-bottom:var(--margin-md,12px); flex-wrap:wrap; }
		.cld-asof { font-size:var(--text-sm,12px); color:var(--text-muted); }
		.cld-asof b { color:var(--text-color); font-weight:var(--weight-medium,500); }

		/* sections */
		.cld-section { margin-bottom:var(--margin-xl,24px); }
		.cld-section-head { display:flex; align-items:baseline; gap:10px; padding-bottom:var(--padding-sm,8px); margin-bottom:var(--margin-md,12px); border-bottom:1px solid var(--border-color); }
		.cld-section-head h5 { margin:0; font-size:var(--text-md,13px); font-weight:var(--weight-semibold,600); color:var(--text-color); display:flex; align-items:center; gap:8px; }
		.cld-section-head .cld-count { font-size:var(--text-xs,11px); color:var(--text-muted); background:var(--control-bg); border-radius:var(--border-radius-full,999px); padding:1px 8px; font-weight:var(--weight-medium,500); }
		.cld-section-head .cld-hint { font-size:var(--text-sm,12px); color:var(--text-muted); }

		/* customer cards */
		.cld-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); gap:var(--margin-md,12px); }
		.cld-card { position:relative; display:flex; flex-direction:column; background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-md); box-shadow:var(--card-shadow); overflow:hidden; cursor:pointer; transition:border-color .15s, box-shadow .15s, transform .15s; }
		.cld-card:hover { border-color:var(--gray-400); box-shadow:var(--shadow-md, var(--card-shadow)); }
		.cld-card::before { content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--cld-accent); }
		.cld-card-body { padding:var(--padding-md,14px) var(--padding-md,14px) var(--padding-sm,10px) calc(var(--padding-md,14px) + 3px); flex:1; }
		.cld-card-head { display:flex; justify-content:space-between; align-items:flex-start; gap:8px; }
		.cld .indicator-pill { white-space:nowrap; flex-shrink:0; }
		.cld-name {font-size:var(--text-base,13px); font-weight:var(--weight-semibold,600); color:var(--text-color); line-height:1.35; }
		.cld-sub { font-size:var(--text-xs,11px); color:var(--text-muted); margin-top:2px; }
		.cld-fields { display:grid; grid-template-columns:1fr 1fr; gap:10px 12px; margin-top:var(--margin-md,12px); }
		.cld-field .k { font-size:var(--text-tiny,10.5px); color:var(--text-muted); text-transform:uppercase; letter-spacing:.3px; }
		.cld-field .v { font-size:var(--text-sm,12.5px); color:var(--text-color); font-weight:var(--weight-medium,500); margin-top:1px; font-variant-numeric:tabular-nums; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
		.cld-card-foot { display:flex; justify-content:space-between; align-items:center; gap:8px; padding:8px var(--padding-md,14px) 8px calc(var(--padding-md,14px) + 3px); border-top:1px solid var(--border-color); background:var(--subtle-fg, var(--control-bg)); font-size:var(--text-sm,12px); }
		.cld-days { font-weight:var(--weight-semibold,600); color:var(--cld-text); }
		.cld-open { color:var(--text-muted); font-size:var(--text-xs,11px); }
		.cld-card:hover .cld-open { color:var(--text-color); }
		.cld-flag { display:inline-flex; align-items:center; gap:4px; font-size:var(--text-tiny,10.5px); color:var(--text-on-orange); background:var(--bg-orange); border-radius:var(--border-radius-sm,4px); padding:0 6px; margin-left:6px; vertical-align:middle; font-weight:var(--weight-medium,500); }

		/* list view */
		.cld-table-wrap { background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-md); box-shadow:var(--card-shadow); overflow:auto; }
		table.cld-table { width:100%; border-collapse:collapse; font-size:var(--text-sm,12.5px); }
		table.cld-table th { position:sticky; top:0; background:var(--subtle-fg, var(--card-bg)); text-align:left; font-size:var(--text-tiny,11px); font-weight:var(--weight-medium,500); color:var(--text-muted); text-transform:uppercase; letter-spacing:.3px; padding:10px 12px; border-bottom:1px solid var(--border-color); white-space:nowrap; }
		table.cld-table td { padding:10px 12px; border-bottom:1px solid var(--border-color); color:var(--text-color); white-space:nowrap; }
		table.cld-table tr:last-child td { border-bottom:none; }
		table.cld-table tbody tr { cursor:pointer; }
		table.cld-table tbody tr:hover { background:var(--highlight-color, var(--control-bg)); }
		table.cld-table .num { text-align:right; font-variant-numeric:tabular-nums; }
		table.cld-table td.first { box-shadow:inset 3px 0 0 var(--cld-accent); }

		.cld-empty { display:flex; flex-direction:column; align-items:center; justify-content:center; gap:6px; padding:60px 20px; color:var(--text-muted); font-size:var(--text-sm,12px); background:var(--card-bg); border:1px dashed var(--border-color); border-radius:var(--border-radius-md); }
		.cld-empty b { color:var(--text-color); font-size:var(--text-base,13px); font-weight:var(--weight-medium,500); }

		/* tones */
		.cld-t-red    { --cld-accent:var(--red-500);    --cld-text:var(--text-on-red); }
		.cld-t-yellow { --cld-accent:var(--yellow-500); --cld-text:var(--text-on-yellow); }
		.cld-t-green  { --cld-accent:var(--green-500);  --cld-text:var(--text-on-green); }
		.cld-t-gray   { --cld-accent:var(--gray-400);   --cld-text:var(--text-muted); }
		.cld-t-blue   { --cld-accent:var(--primary);    --cld-text:var(--text-color); }
		.cld-dot.bg, .cld-kpi-bar > span.bg { background:var(--cld-accent); }
		</style>`).appendTo('head');
	}

	// ---------------------------------------------------------------
	// Standard page filter bar
	// ---------------------------------------------------------------
	const f = {
		search: page.add_field({ fieldname: 'search', label: __('Search customer / licence no'), fieldtype: 'Data', change: () => render() }),
		status: page.add_field({ fieldname: 'status', label: __('Status'), fieldtype: 'Select', options: ['', ...ORDER].join('\n'), change: () => render() }),
		group: page.add_field({
			fieldname: 'customer_group', label: __('Customer Group'), fieldtype: 'MultiSelectList',
			get_data: (txt) => frappe.db.get_link_options('Customer Group', txt),
			change: () => render(),
		}),
		territory: page.add_field({ fieldname: 'territory', label: __('Territory'), fieldtype: 'Link', options: 'Territory', change: () => render() }),
		unlicensed: page.add_field({ fieldname: 'include_unlicensed', label: __('Include without licence'), fieldtype: 'Check', change: () => load() }),
		disabled: page.add_field({ fieldname: 'include_disabled', label: __('Include disabled'), fieldtype: 'Check', change: () => load() }),
	};
	f.search.$input.on('input', frappe.utils.debounce(() => render(), 250));

	let VIEW = 'card';
	try { VIEW = localStorage.getItem('cld-view') || 'card'; } catch (e) { /* storage blocked */ }

	page.set_primary_action(__('Refresh'), () => load(), 'refresh');
	page.add_menu_item(__('Customer List'), () => frappe.set_route('List', 'Customer'));

	// ---------------------------------------------------------------
	// Layout
	// ---------------------------------------------------------------
	const $body = $(`
		<div class="cld">
			<div class="cld-kpis"></div>
			<div class="cld-toolbar">
				<div class="cld-asof"></div>
				<div class="btn-group btn-group-sm cld-view" role="group">
					<button class="btn btn-default" data-view="card">${frappe.utils.icon('image-view', 'sm')} ${__('Cards')}</button>
					<button class="btn btn-default" data-view="list">${frappe.utils.icon('list', 'sm')} ${__('List')}</button>
				</div>
			</div>
			<div class="cld-content"></div>
		</div>
	`).appendTo(page.body);

	let DATA = { rows: [] };

	// ---------------------------------------------------------------
	// Data
	// ---------------------------------------------------------------
	function load() {
		$body.find('.cld-content').html(empty_state(__('Loading…')));
		frappe.call({
			method: `${METHOD}.get_license_overview`,
			args: {
				include_disabled: f.disabled.get_value() ? 1 : 0,
				include_unlicensed: f.unlicensed.get_value() ? 1 : 0,
			},
			callback: (r) => {
				DATA = r.message || { rows: [] };
				$body.find('.cld-asof').html(
					`${__('As of')} <b>${frappe.datetime.str_to_user(DATA.today)}</b> &middot; ` +
					`${__('Expiring window until')} <b>${frappe.datetime.str_to_user(DATA.cutoff)}</b>`
				);
				render();
			},
		});
	}

	// Search / group / territory narrow the set; KPIs count this set so they
	// always agree with the filters. Status is applied on top of it.
	function base_rows() {
		const q = (f.search.get_value() || '').toLowerCase().trim();
		const groups = f.group.get_value() || [];
		const ter = f.territory.get_value();
		return (DATA.rows || []).filter((r) => {
			if (groups.length && !groups.includes(r.customer_group)) return false;
			if (ter && r.territory !== ter) return false;
			if (!q) return true;
			return `${r.customer} ${r.customer_name || ''} ${r.food_license_number || ''}`.toLowerCase().includes(q);
		});
	}

	function render() {
		const rows = base_rows();
		render_kpis(rows);
		const st = f.status.get_value();
		const shown = st ? rows.filter((r) => r.status === st) : rows;
		$body.find('.cld-view .btn').removeClass('active btn-primary').addClass('btn-default')
			.filter(`[data-view="${VIEW}"]`).addClass('active');
		if (!shown.length) {
			$body.find('.cld-content').html(empty_state(__('No customers match these filters'), __('Try clearing a filter or include customers without a licence.')));
			return;
		}
		$body.find('.cld-content').html(VIEW === 'list' ? list_html(shown) : sections_html(shown));
	}

	// ---------------------------------------------------------------
	// KPIs
	// ---------------------------------------------------------------
	function render_kpis(rows) {
		const counts = {};
		rows.forEach((r) => { counts[r.status] = (counts[r.status] || 0) + 1; });
		const total = rows.length;
		const active = f.status.get_value() || '';
		const pct = (n) => (total ? Math.round((n / total) * 100) : 0);

		const cards = [{ key: '', color: 'blue', label: __('Total Customers'), n: total, sub: f.unlicensed.get_value() ? __('incl. without licence') : __('with licence on record') }]
			.concat(ORDER.map((s) => ({ key: s, color: STATUS[s].color, label: s === 'Expiring Soon' ? __('Expiring ≤ 3 Months') : __(s), n: counts[s] || 0, sub: `${pct(counts[s] || 0)}% ${__('of total')}` })));

		$body.find('.cld-kpis').html(cards.map((c) => `
			<div class="cld-kpi cld-t-${c.color}${active === c.key ? ' active' : ''}" data-status="${c.key}" title="${c.key ? __('Click to filter') : __('Click to clear status filter')}">
				<div class="cld-kpi-title"><span class="cld-dot bg"></span>${c.label}</div>
				<div class="cld-kpi-num">${c.n}</div>
				<div class="cld-kpi-sub">${c.sub}</div>
				${c.key ? `<div class="cld-kpi-bar"><span class="bg" style="width:${pct(c.n)}%"></span></div>` : ''}
			</div>`).join(''));
	}

	// ---------------------------------------------------------------
	// Card view — grouped by status
	// ---------------------------------------------------------------
	function sections_html(rows) {
		return ORDER.map((s) => {
			const list = rows.filter((r) => r.status === s);
			if (!list.length) return '';
			const meta = STATUS[s];
			return `
				<div class="cld-section">
					<div class="cld-section-head cld-t-${meta.color}">
						<h5><span class="cld-dot bg"></span>${meta.title}</h5>
						<span class="cld-count">${list.length}</span>
						<span class="cld-hint">${meta.hint}</span>
					</div>
					<div class="cld-grid">${list.map(card_html).join('')}</div>
				</div>`;
		}).join('');
	}

	function card_html(r) {
		const meta = STATUS[r.status];
		return `
			<div class="cld-card cld-t-${meta.color}" data-customer="${esc(r.customer)}">
				<div class="cld-card-body">
					<div class="cld-card-head">
						<div style="min-width:0">
							<div class="cld-name">${esc(r.customer_name || r.customer)}</div>
							<div class="cld-sub">${esc(r.customer)}${r.disabled ? ` &middot; ${__('Disabled')}` : ''}</div>
						</div>
						<span class="indicator-pill ${meta.color}">${__(r.status)}</span>
					</div>
					<div class="cld-fields">
						<div class="cld-field"><div class="k">${__('FSSAI Licence No')}</div><div class="v">${r.food_license_number ? esc(r.food_license_number) : '—'}${dup_flag(r)}</div></div>
						<div class="cld-field"><div class="k">${__('Valid Till')}</div><div class="v">${r.food_license_validity ? frappe.datetime.str_to_user(r.food_license_validity) : '—'}</div></div>
						<div class="cld-field"><div class="k">${__('Customer Group')}</div><div class="v">${esc(r.customer_group || '—')}</div></div>
						<div class="cld-field"><div class="k">${__('Territory')}</div><div class="v">${esc(r.territory || '—')}</div></div>
					</div>
				</div>
				<div class="cld-card-foot">
					<span class="cld-days">${days_text(r)}</span>
					<span class="cld-open">${__('Open')} &rarr;</span>
				</div>
			</div>`;
	}

	// ---------------------------------------------------------------
	// List view
	// ---------------------------------------------------------------
	function list_html(rows) {
		const sorted = rows.slice().sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status));
		return `
			<div class="cld-table-wrap">
				<table class="cld-table">
					<thead><tr>
						<th>${__('Customer')}</th>
						<th>${__('FSSAI Licence No')}</th>
						<th>${__('Valid Till')}</th>
						<th class="num">${__('Days')}</th>
						<th>${__('Status')}</th>
						<th>${__('Customer Group')}</th>
						<th>${__('Territory')}</th>
					</tr></thead>
					<tbody>${sorted.map((r) => {
						const meta = STATUS[r.status];
						const days = r.days_left === null || r.days_left === undefined ? '—' : r.days_left;
						return `<tr class="cld-t-${meta.color}" data-customer="${esc(r.customer)}">
							<td class="first"><div style="font-weight:var(--weight-medium,500)">${esc(r.customer_name || r.customer)}</div><div class="cld-sub">${esc(r.customer)}</div></td>
							<td>${r.food_license_number ? esc(r.food_license_number) : '—'}${dup_flag(r)}</td>
							<td>${r.food_license_validity ? frappe.datetime.str_to_user(r.food_license_validity) : '—'}</td>
							<td class="num"><span class="cld-days">${days}</span></td>
							<td><span class="indicator-pill ${meta.color}">${__(r.status)}</span></td>
							<td>${esc(r.customer_group || '—')}</td>
							<td>${esc(r.territory || '—')}</td>
						</tr>`;
					}).join('')}</tbody>
				</table>
			</div>`;
	}

	// ---------------------------------------------------------------
	// Helpers
	// ---------------------------------------------------------------
	function days_text(r) {
		const d = r.days_left;
		if (d === null || d === undefined) return __('No validity date');
		if (d < 0) return __('Expired {0} days ago', [-d]);
		if (d === 0) return __('Expires today');
		return __('{0} days remaining', [d]);
	}

	function dup_flag(r) {
		return r.duplicate ? `<span class="cld-flag" title="${__('This licence number is also used on another customer')}">${__('Duplicate')}</span>` : '';
	}

	function empty_state(title, sub) {
		return `<div class="cld-empty"><b>${title}</b>${sub ? `<span>${sub}</span>` : ''}</div>`;
	}

	// ---------------------------------------------------------------
	// Events
	// ---------------------------------------------------------------
	$body.on('click', '.cld-kpi', function () {
		const s = $(this).data('status') || '';
		f.status.set_value(f.status.get_value() === s ? '' : s);  // click again to clear
	});
	$body.on('click', '.cld-card, table.cld-table tbody tr', function () {
		frappe.set_route('Form', 'Customer', $(this).data('customer'));
	});
	$body.on('click', '.cld-view .btn', function () {
		VIEW = $(this).data('view');
		try { localStorage.setItem('cld-view', VIEW); } catch (e) { /* storage blocked */ }
		render();
	});

	load();
};
