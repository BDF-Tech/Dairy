frappe.pages['logged-in-details'].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('Logged In Details'),
		single_column: true,
	});

	const METHOD = 'dairy.dairy.page.logged_in_details.logged_in_details';
	const esc = (v) => frappe.utils.escape_html(v == null ? '' : String(v));

	// Status -> indicator colour + label. Order = display order.
	const STATUS = {
		'Online':     { color: 'green',  label: __('Online'),          hint: 'Active in the last {0} min' },
		'Logged In':  { color: 'blue',   label: __('Signed In · Idle'), hint: 'Open session, no recent activity' },
		'Logged Out': { color: 'gray',   label: __('Signed Out'),      hint: 'No open session' },
		'Never':      { color: 'orange', label: __('Never Signed In'), hint: 'No login on record' },
	};
	// User types + colours come from Logged In Details Settings (sent with the data)
	let TYPE_COLOR = {};
	const cvar = (c) => `var(--${c || 'gray'}-500)`;

	// ---------------------------------------------------------------
	// Styles — only Frappe theme variables, so light/dark both work
	// ---------------------------------------------------------------
	if ($('#lid-styles').length === 0) {
		$(`<style id="lid-styles">
		.lid { padding: var(--padding-md, 15px) 0 var(--padding-xl, 30px); }

		.lid-toolbar { display:flex; justify-content:space-between; align-items:center; gap:12px; margin-bottom:var(--margin-md,12px); flex-wrap:wrap; font-size:var(--text-sm,12px); color:var(--text-muted); }
		.lid-toolbar b { color:var(--text-color); font-weight:var(--weight-medium,500); }
		.lid-live { display:inline-flex; align-items:center; gap:6px; }
		.lid-pulse { width:8px; height:8px; border-radius:50%; background:var(--green-500); box-shadow:0 0 0 0 var(--green-500); animation:lid-pulse 2s infinite; }
		@keyframes lid-pulse { 0%{box-shadow:0 0 0 0 rgba(34,197,94,.5)} 70%{box-shadow:0 0 0 6px rgba(34,197,94,0)} 100%{box-shadow:0 0 0 0 rgba(34,197,94,0)} }

		/* KPI cards */
		.lid-kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:var(--margin-md,12px); margin-bottom:var(--margin-lg,20px); }
		.lid-kpi { background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-md); box-shadow:var(--card-shadow); padding:14px 16px; transition:border-color .15s, box-shadow .15s; }
		.lid-kpi.click { cursor:pointer; }
		.lid-kpi.click:hover { border-color:var(--gray-400); }
		.lid-kpi.active { border-color:var(--primary); box-shadow:0 0 0 1px var(--primary); }
		.lid-kpi-title { display:flex; align-items:center; gap:6px; font-size:var(--text-tiny,11px); font-weight:var(--weight-medium,500); color:var(--text-muted); text-transform:uppercase; letter-spacing:.4px; }
		.lid-kpi-num { font-size:var(--text-2xl,24px); font-weight:var(--weight-semibold,600); color:var(--text-color); line-height:1.2; margin-top:8px; font-variant-numeric:tabular-nums; }
		.lid-kpi-sub { font-size:var(--text-xs,11px); color:var(--text-muted); margin-top:2px; }
		.lid-kpi-bar { height:4px; border-radius:2px; background:var(--control-bg); margin-top:10px; overflow:hidden; }
		.lid-kpi-bar > span { display:block; height:100%; border-radius:2px; }
		.lid-dot { width:8px; height:8px; border-radius:50%; flex-shrink:0; display:inline-block; }

		/* layout */
		.lid-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:var(--margin-lg,20px); align-items:stretch; }
		@media (max-width: 991px) { .lid-grid { grid-template-columns:1fr; } }

		/* cards */
		.lid-card { background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-md); box-shadow:var(--card-shadow); overflow:hidden; margin-bottom:var(--margin-lg,20px); }
		.lid-card-head { display:flex; justify-content:space-between; align-items:center; gap:10px; padding:12px 16px; border-bottom:1px solid var(--border-color); flex-wrap:wrap; }
		.lid-card-head h5 { margin:0; font-size:var(--text-md,13px); font-weight:var(--weight-semibold,600); color:var(--text-color); display:flex; align-items:center; gap:8px; }
		.lid-count { font-size:var(--text-xs,11px); color:var(--text-muted); background:var(--control-bg); border-radius:999px; padding:1px 8px; font-weight:var(--weight-medium,500); }
		.lid-search { width:240px !important; flex:none; }

		/* segmented status switch */
		.lid-seg { display:inline-flex; background:var(--control-bg); border-radius:var(--border-radius-md); padding:2px; gap:2px; }
		.lid-seg button { border:0; background:transparent; font-size:var(--text-sm,12px); color:var(--text-muted); padding:4px 10px; border-radius:calc(var(--border-radius-md) - 2px); white-space:nowrap; }
		.lid-seg button.active { background:var(--card-bg); color:var(--text-color); box-shadow:var(--shadow-sm, 0 1px 2px rgba(0,0,0,.08)); font-weight:var(--weight-medium,500); }

		/* table */
		.lid-table-wrap { overflow:auto; max-height:640px; }
		table.lid-table { width:100%; border-collapse:collapse; font-size:var(--text-sm,12.5px); }
		table.lid-table th { position:sticky; top:0; z-index:1; background:var(--subtle-fg, var(--card-bg)); text-align:left; font-size:var(--text-tiny,11px); font-weight:var(--weight-medium,500); color:var(--text-muted); text-transform:uppercase; letter-spacing:.3px; padding:9px 10px; border-bottom:1px solid var(--border-color); white-space:nowrap; }
		table.lid-table td { padding:9px 10px; border-bottom:1px solid var(--border-color); color:var(--text-color); white-space:nowrap; vertical-align:middle; }
		table.lid-table tr:last-child td { border-bottom:none; }
		table.lid-table tbody tr { cursor:pointer; }
		table.lid-table tbody tr:hover { background:var(--highlight-color, var(--control-bg)); }
		table.lid-table .num { text-align:right; font-variant-numeric:tabular-nums; }
		table.lid-table .muted, .lid .muted { color:var(--text-muted); }
		.lid-user { display:flex; align-items:center; gap:10px; min-width:200px; }
		.lid-user .nm { font-weight:var(--weight-medium,500); color:var(--text-color); line-height:1.3; }
		.lid-user .em { font-size:var(--text-xs,11px); color:var(--text-muted); max-width:210px; overflow:hidden; text-overflow:ellipsis; }
		table.lid-table td > .lid-type { margin-left:0; }
		.lid-avatar { position:relative; flex-shrink:0; }
		.lid-avatar .lid-presence { position:absolute; right:-1px; bottom:-1px; width:9px; height:9px; border-radius:50%; border:2px solid var(--card-bg); }
		.lid-time { line-height:1.3; }
		.lid-time .rel { font-size:var(--text-xs,11px); color:var(--text-muted); }
		.lid-fail { color:var(--red-600); font-weight:var(--weight-semibold,600); }
		.lid .indicator-pill { white-space:nowrap; }
		.lid-type { display:inline-block; font-size:10px; font-weight:var(--weight-medium,500); text-transform:uppercase; letter-spacing:.3px; padding:0 6px; margin-left:6px; border-radius:4px; color:var(--lid-type); border:1px solid var(--lid-type); line-height:15px; vertical-align:middle; }
		.lid-types { display:flex; gap:14px; flex-wrap:wrap; font-size:var(--text-sm,12px); color:var(--text-muted); }
		.lid-types span b { color:var(--text-color); font-weight:var(--weight-semibold,600); font-variant-numeric:tabular-nums; }
		table.lid-table td.lid-dept { white-space:normal; min-width:110px; max-width:170px; }

		/* signed-in now list */
		.lid-now { min-height:120px; max-height:340px; overflow:auto; }
		.lid-now-row { display:flex; align-items:center; justify-content:space-between; gap:10px; padding:10px 16px; border-bottom:1px solid var(--border-color); cursor:pointer; }
		.lid-now-row:last-child { border-bottom:none; }
		.lid-now-row:hover { background:var(--highlight-color, var(--control-bg)); }
		.lid-now-meta { text-align:right; font-size:var(--text-xs,11px); color:var(--text-muted); white-space:nowrap; }

		/* activity timeline */
		.lid-feed { min-height:120px; max-height:340px; overflow:auto; }
		.lid-day { position:sticky; top:0; background:var(--subtle-fg, var(--card-bg)); font-size:var(--text-tiny,11px); text-transform:uppercase; letter-spacing:.3px; color:var(--text-muted); font-weight:var(--weight-medium,500); padding:6px 16px; border-bottom:1px solid var(--border-color); }
		.lid-ev { display:flex; gap:10px; padding:9px 16px; border-bottom:1px solid var(--border-color); font-size:var(--text-sm,12.5px); }
		.lid-ev:last-child { border-bottom:none; }
		.lid-ev .tm { width:72px; white-space:nowrap; flex-shrink:0; color:var(--text-muted); font-variant-numeric:tabular-nums; }
		.lid-ev .bd { flex:1; min-width:0; }
		.lid-ev .who { color:var(--text-color); font-weight:var(--weight-medium,500); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
		.lid-ev .what { font-size:var(--text-xs,11px); color:var(--text-muted); display:flex; align-items:center; gap:6px; margin-top:1px; }

		.lid-empty { color:var(--text-muted); font-size:var(--text-sm,12px); padding:36px 16px; text-align:center; }
		.lid-foot { padding:8px 16px; font-size:var(--text-xs,11px); color:var(--text-muted); border-top:1px solid var(--border-color); }
		</style>`).appendTo('head');
	}

	// ---------------------------------------------------------------
	// Filters (standard Frappe page form)
	// ---------------------------------------------------------------
	const today = frappe.datetime.get_today();
	const f = {};
	f.from_date = page.add_field({ fieldname: 'from_date', label: __('From Date'), fieldtype: 'Date', default: today, change: () => load() });
	f.to_date = page.add_field({ fieldname: 'to_date', label: __('To Date'), fieldtype: 'Date', default: today, change: () => load() });
	f.user_category = page.add_field({ fieldname: 'user_category', label: __('User Type'), fieldtype: 'Select', options: '', placeholder: __('User Type'), change: () => render() });
	f.department = page.add_field({ fieldname: 'department', label: __('Department'), fieldtype: 'Link', options: 'Department', change: () => render() });
	f.include_disabled = page.add_field({ fieldname: 'include_disabled', label: __('Include Disabled'), fieldtype: 'Check', change: () => load() });

	page.set_primary_action(__('Refresh'), () => load(), 'refresh');
	page.add_menu_item(__('User Type Rules'), () => frappe.set_route('Form', 'Logged In Details Settings'));
	page.add_menu_item(__('Export Users (CSV)'), () => export_users());
	page.add_menu_item(__('Export Activity Log (CSV)'), () => export_events());

	// ---------------------------------------------------------------
	// Layout
	// ---------------------------------------------------------------
	const $root = $(`
		<div class="lid">
			<div class="lid-toolbar">
				<span style="display:flex; gap:18px; flex-wrap:wrap; align-items:center;"><span class="lid-period"></span><span class="lid-types"></span></span>
				<span class="lid-live"><span class="lid-pulse"></span><span class="lid-updated"></span></span>
			</div>
			<div class="lid-kpis"></div>
			<div class="lid-grid">
				<div class="lid-card">
					<div class="lid-card-head"><h5><span class="lid-dot" style="background:${cvar('green')}"></span>${__('Signed In Now')} <span class="lid-count lid-now-count">0</span></h5></div>
					<div class="lid-now"><div class="lid-empty">${__('Loading…')}</div></div>
				</div>
				<div class="lid-card">
					<div class="lid-card-head"><h5>${__('Login / Logout Activity')} <span class="lid-count lid-ev-count">0</span></h5></div>
					<div class="lid-feed"><div class="lid-empty">${__('Loading…')}</div></div>
					<div class="lid-foot lid-feed-foot" style="display:none"></div>
				</div>
			</div>
			<div class="lid-card lid-users">
				<div class="lid-card-head">
					<h5>${__('Users')} <span class="lid-count lid-users-count">0</span></h5>
					<div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
						<div class="lid-seg"></div>
						<input type="text" class="form-control input-sm lid-search" placeholder="${__('Search name, email, department…')}">
					</div>
				</div>
				<div class="lid-table-wrap"><div class="lid-empty">${__('Loading…')}</div></div>
			</div>
		</div>
	`).appendTo(page.body);

	let DATA = { rows: [], summary: {}, events: [] };
	let status_filter = '';

	const segs = [['', __('All')]].concat(Object.keys(STATUS).map((k) => [k, STATUS[k].label]));
	$root.find('.lid-seg').html(segs.map(([v, l]) => `<button data-status="${esc(v)}" class="${v ? '' : 'active'}">${esc(l)}</button>`).join(''));

	// ---------------------------------------------------------------
	// Helpers
	// ---------------------------------------------------------------
	function avatar(user, full_name, status) {
		const dot = status === 'Online' || status === 'Logged In'
			? `<span class="lid-presence" style="background:${cvar(STATUS[status].color)}"></span>` : '';
		return `<span class="lid-avatar">${frappe.avatar(user, 'avatar-small', full_name)}${dot}</span>`;
	}
	function pill(status) {
		const s = STATUS[status];
		return `<span class="indicator-pill ${s.color}">${esc(s.label)}</span>`;
	}
	function type_tag(t) {
		return t ? `<span class="lid-type" style="--lid-type:${cvar(TYPE_COLOR[t])}">${esc(__(t))}</span>` : '';
	}
	function when(v) {
		if (!v) return `<span class="muted">—</span>`;
		return `<div class="lid-time" title="${esc(frappe.datetime.str_to_user(v))}">${esc(moment(v).format('DD MMM, hh:mm A'))}<div class="rel">${esc(frappe.datetime.prettyDate(v))}</div></div>`;
	}
	// "Dispatch - BDF" -> "Dispatch" (company abbreviation adds nothing here)
	const dept_label = (d) => (d || '').replace(/\s+-\s+[^-]+$/, '');
	function open_user(user) { frappe.set_route('Form', 'User', user); }

	// ---------------------------------------------------------------
	// Load
	// ---------------------------------------------------------------
	function load() {
		const from_date = f.from_date.get_value() || today;
		const to_date = f.to_date.get_value() || today;
		if (from_date > to_date) {
			frappe.show_alert({ message: __('From Date cannot be after To Date'), indicator: 'orange' });
			return;
		}
		frappe.call({
			method: `${METHOD}.get_login_activity`,
			args: { from_date, to_date, include_disabled: f.include_disabled.get_value() ? 1 : 0 },
			freeze: !DATA.rows.length,
			callback: (r) => {
				DATA = r.message || { rows: [], summary: {}, events: [], user_types: [] };
				set_user_types(DATA.user_types || []);
				const period = from_date === to_date
					? frappe.datetime.str_to_user(from_date)
					: `${frappe.datetime.str_to_user(from_date)} – ${frappe.datetime.str_to_user(to_date)}`;
				$root.find('.lid-period').html(`${__('Activity period')}: <b>${esc(period)}</b>`);
				$root.find('.lid-updated').text(__('Updated {0}', [moment().format('hh:mm A')]));
				render();
			},
		});
	}

	function set_user_types(types) {
		TYPE_COLOR = Object.fromEntries(types.map((t) => [t.name, t.color]));
		const options = [''].concat(types.map((t) => t.name)).join('\n');
		if (f.user_category.df.options !== options) {
			const cur = f.user_category.get_value();
			f.user_category.df.options = options;
			f.user_category.refresh();
			// keep the selection only if that type still exists
			if (cur && !(cur in TYPE_COLOR)) f.user_category.set_value('');
		}
	}

	function dept_rows() {
		const dept = f.department.get_value();
		const type = f.user_category.get_value();
		return (DATA.rows || []).filter((r) => (!dept || r.department === dept) && (!type || r.user_category === type));
	}

	function render() {
		render_kpis();
		render_users();
		render_now();
		render_feed();
	}

	// ---------------------------------------------------------------
	// KPIs
	// ---------------------------------------------------------------
	function render_types() {
		const rows = dept_rows();
		const types = (DATA.user_types || []).map((t) => t.name).filter((t) => rows.some((r) => r.user_category === t));
		$root.find('.lid-types').html(types.map((t) => {
			const all = rows.filter((r) => r.user_category === t);
			const on = all.filter((r) => r.status === 'Online' || r.status === 'Logged In').length;
			return `<span title="${__('Signed in now / total')}"><span class="lid-dot" style="background:${cvar(TYPE_COLOR[t])}; margin-right:5px"></span>${esc(__(t))} <b>${on}</b> / ${all.length}</span>`;
		}).join(''));
	}

	function render_kpis() {
		render_types();
		const rows = dept_rows();
		const total = rows.length || 1;
		const count = (st) => rows.filter((r) => r.status === st).length;
		const mins = (DATA.summary || {}).online_minutes || 15;
		const cards = Object.keys(STATUS).map((st) => {
			const n = count(st);
			const s = STATUS[st];
			return `<div class="lid-kpi click ${status_filter === st ? 'active' : ''}" data-status="${esc(st)}">
				<div class="lid-kpi-title"><span class="lid-dot" style="background:${cvar(s.color)}"></span>${esc(s.label)}</div>
				<div class="lid-kpi-num">${n}</div>
				<div class="lid-kpi-sub">${esc(__(s.hint, [mins]))}</div>
				<div class="lid-kpi-bar"><span style="width:${(n * 100 / total).toFixed(1)}%; background:${cvar(s.color)}"></span></div>
			</div>`;
		});
		const active = rows.filter((r) => r.logins).length;
		const failed = rows.reduce((a, r) => a + (r.failed || 0), 0);
		cards.push(`<div class="lid-kpi">
			<div class="lid-kpi-title"><span class="lid-dot" style="background:${cvar('purple')}"></span>${__('Logged In During Period')}</div>
			<div class="lid-kpi-num">${active}</div>
			<div class="lid-kpi-sub">${__('of {0} users', [rows.length])}</div>
			<div class="lid-kpi-bar"><span style="width:${(active * 100 / total).toFixed(1)}%; background:${cvar('purple')}"></span></div>
		</div>`);
		cards.push(`<div class="lid-kpi">
			<div class="lid-kpi-title"><span class="lid-dot" style="background:${cvar('red')}"></span>${__('Failed Attempts')}</div>
			<div class="lid-kpi-num ${failed ? 'lid-fail' : ''}">${failed}</div>
			<div class="lid-kpi-sub">${__('Wrong password / blocked')}</div>
		</div>`);
		$root.find('.lid-kpis').html(cards.join(''));
	}

	// ---------------------------------------------------------------
	// Users table
	// ---------------------------------------------------------------
	function filtered_users() {
		const q = ($root.find('.lid-search').val() || '').toLowerCase().trim();
		return dept_rows().filter((r) => {
			if (status_filter && r.status !== status_filter) return false;
			if (!q) return true;
			return `${r.user} ${r.full_name || ''} ${r.employee_name || ''} ${r.department || ''} ${r.user_category}`.toLowerCase().includes(q);
		});
	}

	function render_users() {
		const rows = filtered_users();
		$root.find('.lid-users-count').text(rows.length);
		$root.find('.lid-seg button').each(function () { $(this).toggleClass('active', $(this).data('status') === status_filter); });
		const $wrap = $root.find('.lid-users .lid-table-wrap');
		if (!rows.length) { $wrap.html(`<div class="lid-empty">${__('No users match the filters.')}</div>`); return; }

		// Customers / drivers have no Employee, so skip an all-empty Department column
		const show_dept = rows.some((r) => r.department);
		const head = `<tr>
			<th>${__('User')}</th><th>${__('Type')}</th>${show_dept ? `<th>${__('Department')}</th>` : ''}<th>${__('Status')}</th>
			<th>${__('Last Seen')}</th><th>${__('Last Login')}</th><th>${__('Last Logout')}</th>
<th class="num" title="${__('Logins · Logouts · Failed in the selected period')}">${__('In · Out · Failed')}</th>
			<th>${__('Last IP')}</th>
		</tr>`;
		const body = rows.map((r) => `<tr data-user="${esc(r.user)}">
			<td><div class="lid-user">${avatar(r.user, r.full_name, r.status)}<div><div class="nm">${esc(r.full_name)}${r.enabled ? '' : ` <span class="indicator-pill red">${__('Disabled')}</span>`}</div><div class="em" title="${esc(r.user)}">${esc(r.user)}</div></div></div></td>
			<td>${type_tag(r.user_category)}</td>
			${show_dept ? `<td class="muted lid-dept" title="${esc(r.department)}">${r.department ? esc(dept_label(r.department)) : '—'}</td>` : ''}
			<td>${pill(r.status)}${r.sessions ? `<div class="muted" style="font-size:11px; margin-top:3px">${r.sessions > 1 ? __('{0} sessions', [r.sessions]) : __('1 session')}${r.devices ? ` · ${esc(r.devices)}` : ''}</div>` : ''}</td>
			<td>${when(r.last_seen)}</td>
			<td>${when(r.last_login)}</td>
			<td>${when(r.last_logout)}</td>
			<td class="num">${r.logins || '<span class="muted">0</span>'} <span class="muted">·</span> ${r.logouts || '<span class="muted">0</span>'} <span class="muted">·</span> ${r.failed ? `<span class="lid-fail">${r.failed}</span>` : '<span class="muted">0</span>'}</td>
			<td class="muted">${esc(r.last_ip || '—')}</td>
		</tr>`).join('');
		$wrap.html(`<table class="lid-table"><thead>${head}</thead><tbody>${body}</tbody></table>`);
	}

	// ---------------------------------------------------------------
	// Signed in now
	// ---------------------------------------------------------------
	function render_now() {
		const rows = dept_rows().filter((r) => r.status === 'Online' || r.status === 'Logged In');
		$root.find('.lid-now-count').text(rows.length);
		const $box = $root.find('.lid-now');
		if (!rows.length) { $box.html(`<div class="lid-empty">${__('Nobody is signed in right now.')}</div>`); return; }
		$box.html(rows.map((r) => `<div class="lid-now-row" data-user="${esc(r.user)}">
			<div class="lid-user" style="min-width:0">${avatar(r.user, r.full_name, r.status)}<div style="min-width:0"><div class="nm">${esc(r.full_name)}${type_tag(r.user_category)}</div><div class="em">${esc(r.department ? dept_label(r.department) : r.user)}</div></div></div>
			<div class="lid-now-meta">${pill(r.status)}<div style="margin-top:3px">${esc(frappe.datetime.prettyDate(r.last_seen))}${r.sessions > 1 ? ` · ${r.sessions} ${__('sessions')}` : ''}</div></div>
		</div>`).join(''));
	}

	// ---------------------------------------------------------------
	// Activity feed
	// ---------------------------------------------------------------
	function filtered_events() {
		const q = ($root.find('.lid-search').val() || '').toLowerCase().trim();
		const allowed = (f.department.get_value() || f.user_category.get_value()) ? new Set(dept_rows().map((r) => r.user)) : null;
		return (DATA.events || []).filter((e) => (!allowed || allowed.has(e.user))
			&& (!q || `${e.user} ${e.full_name || ''}`.toLowerCase().includes(q)));
	}

	function render_feed() {
		const ev = filtered_events();
		$root.find('.lid-ev-count').text(ev.length);
		const $box = $root.find('.lid-feed');
		if (!ev.length) { $box.html(`<div class="lid-empty">${__('No logins or logouts in this period.')}</div>`); $root.find('.lid-feed-foot').hide(); return; }
		let last_day = null;
		const html = ev.map((e) => {
			const day = moment(e.creation).format('YYYY-MM-DD');
			const head = day !== last_day ? `<div class="lid-day">${esc(moment(e.creation).format('dddd, DD MMM YYYY'))}</div>` : '';
			last_day = day;
			const [color, label] = e.operation === 'Logout' ? ['gray', __('Logged out')]
				: e.status === 'Failed' ? ['red', __('Failed login')] : ['green', __('Logged in')];
			return `${head}<div class="lid-ev">
				<div class="tm">${esc(moment(e.creation).format('hh:mm A'))}</div>
				<div class="bd"><div class="who">${esc(e.full_name || e.user)}</div>
				<div class="what"><span class="lid-dot" style="background:${cvar(color)}"></span>${label}${e.ip_address ? ` · ${esc(e.ip_address)}` : ''}</div></div>
			</div>`;
		}).join('');
		$box.html(html);
		$root.find('.lid-feed-foot').toggle(ev.length >= 500).text(__('Showing the latest 500 events — narrow the dates to see more.'));
	}

	// ---------------------------------------------------------------
	// Export
	// ---------------------------------------------------------------
	function export_users() {
		const rows = [['User', 'Full Name', 'User Type', 'Department', 'Status', 'Last Seen', 'Last Login', 'Last Logout', 'Sessions', 'Logins', 'Logouts', 'Failed', 'Last IP']]
			.concat(filtered_users().map((r) => [r.user, r.full_name, r.user_category, r.department || '', STATUS[r.status].label, r.last_seen || '', r.last_login || '', r.last_logout || '', r.sessions, r.logins, r.logouts, r.failed, r.last_ip || '']));
		frappe.tools.downloadify(rows, null, 'Logged In Details - Users');
	}
	function export_events() {
		const rows = [['Time', 'User', 'Full Name', 'Event', 'Status', 'IP Address']]
			.concat(filtered_events().map((e) => [e.creation, e.user, e.full_name || '', e.operation, e.status, e.ip_address || '']));
		frappe.tools.downloadify(rows, null, 'Logged In Details - Activity');
	}

	// ---------------------------------------------------------------
	// Events
	// ---------------------------------------------------------------
	$root.on('click', '.lid-seg button', function () { status_filter = $(this).data('status') || ''; render_kpis(); render_users(); });
	$root.on('click', '.lid-kpi.click', function () {
		const st = $(this).data('status');
		status_filter = status_filter === st ? '' : st;
		render_kpis(); render_users();
	});
	$root.on('input', '.lid-search', frappe.utils.debounce(() => { render_users(); render_feed(); }, 200));
	$root.on('click', 'table.lid-table tbody tr, .lid-now-row', function () { open_user($(this).data('user')); });

	// Keep "who is online" fresh while the page is open
	const timer = setInterval(() => { if (frappe.get_route_str() === 'logged-in-details') load(); }, 60000);
	$(wrapper).on('remove', () => clearInterval(timer));

	load();
};
