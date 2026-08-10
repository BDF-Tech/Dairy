frappe.pages['loan-dashboard'].on_page_load = function (wrapper) {

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Loan Dashboard',
		single_column: true
	});

	// ======================
	// LOADER & THEME-AWARE STYLES
	// All colours come from Frappe CSS variables so contrast stays correct in
	// both the light and dark desk themes (no hardcoded white/grey).
	// ======================
	$(`
		<div id="loan-dash-loader" style="
			position:fixed; top:0; left:0; width:100%; height:100%;
			background: rgba(127,127,127,0.25); backdrop-filter: blur(3px);
			display:none; align-items:center; justify-content:center; z-index:10001;">
			<div class="loan-spinner"><div></div><div></div><div></div><div></div></div>
		</div>
	`).appendTo('body');

	if ($('#loan-dash-styles').length === 0) {
		$(`<style id="loan-dash-styles">
		.loan-spinner { display:inline-block; position:relative; width:64px; height:64px; }
		.loan-spinner div { box-sizing:border-box; display:block; position:absolute; width:51px; height:51px; margin:6px; border:4px solid var(--primary, #2563eb); border-radius:50%; animation:loan-spin 1.2s linear infinite; border-color:var(--primary, #2563eb) transparent transparent transparent; }
		.loan-spinner div:nth-child(1){ animation-delay:-0.45s; }
		.loan-spinner div:nth-child(2){ animation-delay:-0.3s; }
		.loan-spinner div:nth-child(3){ animation-delay:-0.15s; }
		@keyframes loan-spin { 0%{ transform:rotate(0deg);} 100%{ transform:rotate(360deg);} }

		.loan-kpis { display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:12px; }
		.loan-kpi { padding:14px 16px; background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-lg, 12px); box-shadow:var(--card-shadow, none); }
		.loan-kpi.hero { border-left:3px solid var(--primary, #2563eb); }
		.loan-kpi .l { font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600; letter-spacing:.3px; }
		.loan-kpi .v { font-size:22px; font-weight:700; margin-top:2px; }
		.loan-kpi .s { font-size:11px; color:var(--text-muted); margin-top:2px; }

		.loan-charts { display:grid; grid-template-columns:2fr 1fr; gap:15px; margin-top:20px; }
		@media (max-width: 900px){ .loan-charts { grid-template-columns:1fr; } }
		.loan-panel { background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-lg, 12px); padding:10px 15px; }
		.loan-panel h4 { font-size:12px; text-transform:uppercase; letter-spacing:.3px; color:var(--text-muted); font-weight:600; margin:4px 0 6px; }
		.loan-chart text { fill:var(--text-muted) !important; }
		.loan-chart .title { fill:var(--text-color) !important; font-weight:600; }

		.loan-card { background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-lg, 12px); padding:16px; box-shadow:var(--card-shadow, none); }
		.loan-title { font-weight:600; font-size:14.5px; color:var(--heading-color, var(--text-color)); line-height:1.25; }
		.loan-sub { font-size:11.5px; color:var(--text-muted); margin-top:1px; }
		.loan-row { display:flex; justify-content:space-between; gap:8px; font-size:12.5px; padding:5px 0; border-bottom:1px solid var(--border-color); }
		.loan-row:last-child { border-bottom:none; }
		.loan-row .k { color:var(--text-muted); }
		.loan-row .val { font-weight:600; color:var(--text-color); white-space:nowrap; }
		.loan-muted { color:var(--text-muted); }
		.loan-green { color:var(--green-600, #16a34a); }
		.loan-red { color:var(--red-600, #dc2626); }
		.loan-blue { color:var(--blue-600, #2563eb); }
		.loan-orange { color:var(--orange-600, #ea580c); }

		.loan-bar { height:6px; border-radius:4px; background:var(--control-bg, var(--subtle-fg)); overflow:hidden; margin-top:10px; }
		.loan-bar > span { display:block; height:100%; background:var(--primary, #2563eb); }

		.pill { display:inline-block; font-size:10.5px; font-weight:600; padding:1px 8px; border-radius:20px; text-transform:uppercase; letter-spacing:.3px; }
		.pill.secured { background:rgba(22,163,74,.14); color:var(--green-600,#16a34a); }
		.pill.unsecured { background:rgba(234,88,12,.14); color:var(--orange-600,#ea580c); }
		.pill.od { background:rgba(37,99,235,.14); color:var(--blue-600,#2563eb); }

		.loan-link { color:var(--text-color); text-decoration:underline; text-decoration-color:var(--text-muted); text-underline-offset:2px; }
		.loan-link:hover { color:var(--primary, #2563eb); text-decoration-color:var(--primary, #2563eb); }

		/* Plain-language layer */
		.loan-intro { background:var(--subtle-fg, var(--control-bg)); border:1px solid var(--border-color); border-left:3px solid var(--primary, #2563eb); border-radius:var(--border-radius-lg, 12px); padding:16px 18px; }
		.loan-intro .head { font-size:15px; font-weight:700; color:var(--heading-color, var(--text-color)); }
		.loan-intro .headline { font-size:13.5px; color:var(--text-color); margin-top:2px; }
		.loan-insights { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:8px 20px; margin-top:12px; }
		.loan-insight { font-size:12.8px; color:var(--text-color); display:flex; gap:8px; align-items:flex-start; line-height:1.4; }
		.loan-insight .ic { flex:0 0 auto; font-size:14px; line-height:1.3; }
		.loan-insight b { color:var(--heading-color, var(--text-color)); }

		.kpi .plain { font-size:11.5px; color:var(--text-muted); margin-top:3px; font-weight:500; text-transform:none; letter-spacing:0; }
		.help-icon { display:inline-block; width:14px; height:14px; line-height:14px; text-align:center; border-radius:50%; border:1px solid var(--text-muted); color:var(--text-muted); font-size:10px; font-weight:700; cursor:help; margin-left:4px; vertical-align:middle; }

		.loan-subhead { font-size:11.5px; color:var(--text-muted); font-weight:400; text-transform:none; letter-spacing:0; margin:-2px 0 8px; }

		.glossary-toggle { cursor:pointer; font-size:12.5px; color:var(--primary, #2563eb); font-weight:600; user-select:none; }
		.glossary { margin-top:10px; display:none; grid-template-columns:repeat(auto-fit, minmax(230px, 1fr)); gap:10px 22px; }
		.glossary.open { display:grid; }
		.gloss-term { font-size:12.5px; }
		.gloss-term b { color:var(--heading-color, var(--text-color)); }
		.gloss-term span { color:var(--text-muted); }

		.loan-legend { display:flex; flex-wrap:wrap; gap:6px 16px; margin:4px 0 8px; }
		.loan-legend div { font-size:11.5px; color:var(--text-muted); display:flex; gap:6px; align-items:center; }
		.loan-legend .dot { width:10px; height:10px; border-radius:3px; flex:0 0 auto; }

		/* Loan Position table (plain summary, mockup-style) */
		.loan-pos-table { border-top:1px solid var(--border-color); }
		.loan-pos-row { display:grid; grid-template-columns:1.6fr 1fr 1.1fr; gap:12px; align-items:center; padding:12px 16px; border-bottom:1px solid var(--border-color); }
		.loan-pos-row:last-child { border-bottom:none; }
		.pos-title { font-size:13.5px; font-weight:600; color:var(--heading-color, var(--text-color)); }
		.pos-desc { font-size:11.5px; color:var(--text-muted); margin-top:1px; }
		.pos-amt { text-align:right; }
		.pos-out { font-size:16px; font-weight:700; color:var(--text-color); }
		.pos-share { font-size:11px; color:var(--text-muted); }
		.pos-emi { text-align:right; font-size:12.5px; color:var(--text-color); }
		.pos-last { font-size:11px; color:var(--text-muted); margin-top:2px; }
		@media (max-width: 640px){
			.loan-pos-row { grid-template-columns:1fr 1fr; }
			.pos-emi { grid-column:1/-1; text-align:left; border-top:1px dashed var(--border-color); padding-top:8px; }
		}

		/* EMI & regularity table */
		.emi-table { border-top:1px solid var(--border-color); }
		.emi-row { display:grid; grid-template-columns:2fr 1.1fr 1.4fr 1fr; gap:12px; align-items:center; padding:11px 16px; border-bottom:1px solid var(--border-color); }
		.emi-row:last-child { border-bottom:none; }
		.emi-head { font-size:10.5px; text-transform:uppercase; letter-spacing:.3px; color:var(--text-muted); font-weight:600; background:var(--subtle-fg, var(--control-bg)); }
		.emi-name { font-size:13px; font-weight:600; color:var(--heading-color, var(--text-color)); }
		.emi-sub { font-size:11px; color:var(--text-muted); margin-top:1px; }
		.emi-amt { text-align:right; font-size:14px; font-weight:700; color:var(--text-color); }
		.emi-due { font-size:12px; color:var(--text-color); }
		.emi-cap { font-size:10.5px; color:var(--text-muted); margin-top:1px; font-weight:400; }
		.emi-head .emi-amt, .emi-head .emi-due { font-size:10.5px; font-weight:600; }
		.emi-status { text-align:right; }
		.stpill { display:inline-block; font-size:11px; font-weight:600; padding:2px 9px; border-radius:20px; white-space:nowrap; }
		.stpill.st-green { background:rgba(22,163,74,.14); color:var(--green-600,#16a34a); }
		.stpill.st-amber { background:rgba(234,88,12,.14); color:var(--orange-600,#ea580c); }
		.stpill.st-red { background:rgba(220,38,38,.14); color:var(--red-600,#dc2626); }
		@media (max-width: 680px){
			.emi-row { grid-template-columns:1.4fr 1fr; }
			.emi-due { grid-column:1; }
			.emi-status { grid-column:2; }
		}
		</style>`).appendTo('head');
	}

	// Compact Indian-currency formatter: big numbers as ₹x.xx Cr / L, small as grouped.
	const inr = (v) => parseFloat((Number(v) || 0).toFixed(2)).toLocaleString('en-IN');
	function money(v) {
		v = Number(v) || 0;
		const a = Math.abs(v), sign = v < 0 ? '-' : '';
		if (a >= 1e7) return `${sign}₹${(a / 1e7).toFixed(2)} Cr`;
		if (a >= 1e5) return `${sign}₹${(a / 1e5).toFixed(2)} L`;
		return `${sign}₹${inr(a)}`;
	}
	const esc = frappe.utils.escape_html;

	function show_loader() { $("#loan-dash-loader").css('display', 'flex'); }
	function hide_loader() { $("#loan-dash-loader").hide(); }

	// ======================
	// FILTERS
	// Period/Year/Sub Period rewrite From/To; the reload is debounced so a
	// cascade collapses into one call. `ready` blocks the initial cascade from
	// firing before the first explicit load.
	// ======================
	let ready = false, reload_timer = null, request_seq = 0;

	function reload_soon() {
		if (!ready) return;
		clearTimeout(reload_timer);
		reload_timer = setTimeout(() => load_data(), 250);
	}

	let company = page.add_field({
		label: 'Company', fieldtype: 'Link', options: 'Company',
		default: frappe.defaults.get_user_default('Company'),
		change() { reload_soon(); }
	});

	let period = page.add_field({
		label: 'Period', fieldtype: 'Select',
		options: ['Yearly', 'Half Yearly', 'Quarterly', 'Monthly', 'Custom'],
		default: 'Yearly',
		change() { on_period_change(); reload_soon(); }
	});

	let year_sel = page.add_field({ label: 'Year', fieldtype: 'Select', change() { apply_period(); reload_soon(); } });
	let sub_sel = page.add_field({ label: 'Sub Period', fieldtype: 'Select', change() { apply_period(); reload_soon(); } });
	$(sub_sel.wrapper).hide();

	let from_date = page.add_field({ label: 'From Date', fieldtype: 'Date', change() { reload_soon(); } });
	let to_date = page.add_field({ label: 'To Date', fieldtype: 'Date', change() { reload_soon(); } });

	const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
		'July', 'August', 'September', 'October', 'November', 'December'];

	function year_options() {
		let y = moment().year(), arr = [];
		for (let i = 0; i < 6; i++) arr.push(String(y - i));
		return arr;
	}

	function on_period_change() {
		let p = period.get_value();
		$(sub_sel.wrapper).hide();

		if (p === 'Custom') { $(year_sel.wrapper).hide(); return; }

		let yopts = year_options();
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

	// Resolve Period + Year + Sub-period into an actual from/to range. "To Date"
	// is capped at today so outstanding always means "as of now" for the current
	// period rather than a future year-end.
	function apply_period() {
		let p = period.get_value();
		let y = parseInt(year_sel.get_value(), 10) || moment().year();
		let today = frappe.datetime.get_today();
		const cap = (d) => (d > today ? today : d);

		if (p === 'Monthly') {
			let m = MONTHS.indexOf(sub_sel.get_value()); if (m < 0) m = moment().month();
			let start = moment({ year: y, month: m, day: 1 });
			from_date.set_value(start.format('YYYY-MM-DD'));
			to_date.set_value(cap(start.clone().endOf('month').format('YYYY-MM-DD')));
		} else if (p === 'Quarterly') {
			let q = parseInt((sub_sel.get_value() || 'Q1').replace('Q', ''), 10) || 1;
			let start = moment({ year: y, month: (q - 1) * 3, day: 1 });
			from_date.set_value(start.format('YYYY-MM-DD'));
			to_date.set_value(cap(start.clone().add(2, 'months').endOf('month').format('YYYY-MM-DD')));
		} else if (p === 'Half Yearly') {
			let start = moment({ year: y, month: sub_sel.get_value() === 'HY2' ? 6 : 0, day: 1 });
			from_date.set_value(start.format('YYYY-MM-DD'));
			to_date.set_value(cap(start.clone().add(5, 'months').endOf('month').format('YYYY-MM-DD')));
		} else if (p === 'Yearly') {
			from_date.set_value(`${y}-01-01`);
			to_date.set_value(cap(`${y}-12-31`));
		}
	}

	on_period_change();

	// ======================
	// LAYOUT   (plain-language summary first, financial detail below)
	// ======================
	let intro_wrap = $(`<div id="loan-intro" style="margin-top:15px;"></div>`).appendTo(page.body);
	let position_wrap = $(`<div id="loan-position" style="margin-top:15px;"></div>`).appendTo(page.body);
	let emi_wrap = $(`<div id="loan-emi" style="margin-top:15px;"></div>`).appendTo(page.body);

	let kpi_head = $(`<div style="margin-top:22px; font-size:13px; font-weight:600; color:var(--text-color);">The numbers in detail</div>`).appendTo(page.body);
	let kpi_wrap = $(`<div class="loan-kpis" style="margin-top:10px;"></div>`).appendTo(page.body);
	let charts_wrap = $(`
		<div class="loan-charts">
			<div class="loan-panel"><h4>How much you still owe on each loan</h4><div class="loan-subhead">Taller bar = more money still to pay back on that loan.</div><div id="loan-out-chart" class="loan-chart"></div></div>
			<div class="loan-panel"><h4>What your debt is made of</h4><div class="loan-subhead">Backed by assets vs. not backed, and the bank overdraft.</div><div id="loan-comp-chart" class="loan-chart"></div><div id="loan-comp-legend" class="loan-legend"></div></div>
		</div>
	`).appendTo(page.body);
	let trend_wrap = $(`
		<div class="loan-panel" style="margin-top:15px;"><h4>Money paid back vs. interest — last 12 months</h4><div class="loan-subhead">Green bars = loan amount you paid off each month. Red line = interest (the extra charge) paid that month.</div><div id="loan-trend-chart" class="loan-chart"></div></div>
	`).appendTo(page.body);
	let interest_wrap = $(`<div id="loan-interest" style="margin-top:15px;"></div>`).appendTo(page.body);

	let cards_head = $(`<div id="loan-cards-head" style="margin-top:22px; font-size:13px; font-weight:600; color:var(--text-color);"></div>`).appendTo(page.body);
	let cards_wrap = $(`
		<div id="loan-cards" style="margin-top:10px; display:grid; grid-template-columns:repeat(auto-fill, minmax(330px, 1fr)); gap:15px;"></div>
	`).appendTo(page.body);

	let out_chart = null, comp_chart = null, trend_chart = null;

	let header_stats = $(`<div id="loan-header-stats" style="display:flex; gap:22px; align-items:center; margin-right:14px;"></div>`);
	page.page_actions.prepend(header_stats);

	// ======================
	// LOAD
	// ======================
	function load_data() {
		let f = from_date.get_value(), t = to_date.get_value();
		if (!f || !t) { frappe.msgprint('Please select From Date and To Date.'); return; }

		clearTimeout(reload_timer);
		const token = ++request_seq;   // ignore out-of-order responses

		show_loader();
		frappe.call({
			method: 'dairy.dairy.page.loan_dashboard.loan_dashboard.get_dashboard_data',
			args: { from_date: f, to_date: t, company: company.get_value() || null },
			callback: (r) => {
				if (token !== request_seq) return;
				let d = (r && r.message) || {};
				render_intro(d);
				render_position(d.position || []);
				render_emi(d.cards || []);
				render_kpis(d.summary || {});
				render_out_chart(d.outstanding_chart || {});
				render_comp_chart(d.composition || {});
				render_trend(d.trend || {});
				render_interest(d.interest_breakdown || []);
				render_cards(d.cards || [], d.summary || {});
				hide_loader();
			},
			error: () => { if (token === request_seq) hide_loader(); }
		});
	}

	page.set_primary_action('Load Data', () => load_data(), 'refresh');

	// ======================
	// RENDERERS
	// ======================
	function help(text) {
		return `<span class="help-icon" title="${esc(text)}">i</span>`;
	}

	function kpi(label, value, plain, cls, hero, tip) {
		return `<div class="loan-kpi ${hero ? 'hero' : ''}">
			<div class="l">${label}${tip ? help(tip) : ''}</div>
			<div class="v ${cls || ''}">${value}</div>
			${plain ? `<div class="plain">${plain}</div>` : ''}
		</div>`;
	}

	// ---- plain-English "At a glance" summary ---------------------------
	function render_intro(d) {
		let s = d.summary || {}, cards = d.cards || [], interest = d.interest_breakdown || [];
		let total = Number(s.total_outstanding) || 0;
		let biggest = cards.find(c => Math.abs(c.outstanding) > 1);
		let costliest = interest.find(x => Number(x.amount) > 0);
		let asof = frappe.datetime.str_to_user(to_date.get_value());

		let ins = [];
		if (biggest) ins.push(['🏦', `Your biggest loan is <b>${esc(biggest.account_name)}</b> — <b>${money(biggest.outstanding)}</b> still to pay.`]);
		ins.push(['⚖️', `Of what you owe: <b>${money(s.secured)}</b> is backed by assets (vehicles/property), <b>${money(s.unsecured)}</b> is not, and <b>${money(s.od)}</b> is the bank overdraft.`]);
		if (Number(s.interest_paid) > 0) ins.push(['💸', `You paid <b>${money(s.interest_paid)}</b> in interest this period${costliest ? ` — the costliest is <b>${esc(costliest.account_name)}</b> (${money(costliest.amount)})` : ''}.`]);
		if (Number(s.principal_repaid) > 0) ins.push(['📉', `You paid off <b>${money(s.principal_repaid)}</b> of loan balance this period (not counting overdraft).`]);
		if (Number(s.disbursed) > 0) ins.push(['🆕', `You took <b>${money(s.disbursed)}</b> in new loans this period.`]);

		let glossary = [
			['Outstanding', 'The money you still have to pay back on a loan right now.'],
			['Secured loan', 'A loan backed by something you own (vehicle, property). The lender can take that asset if unpaid.'],
			['Unsecured loan', 'A loan with no asset backing it — usually from a bank or finance company (NBFC).'],
			['Bank overdraft (OD)', 'A credit line from the bank you dip into as needed and repay — like a flexible loan on your current account.'],
			['Interest', 'The extra charge the lender adds on top of what you borrowed — the cost of the loan.'],
			['Principal repaid', 'The part of your payments that actually reduces the loan balance (separate from interest).'],
			['Disbursed', 'New loan money you received during the period.'],
			['≈ Monthly', 'An estimate of what you pay each month, worked out from your actual recent payments (no EMI schedule is stored in the system).'],
		];

		intro_wrap.html(`
			<div class="loan-intro">
				<div class="head">At a glance</div>
				<div class="headline">As of <b>${asof}</b>, the business owes <b>${money(total)}</b> across <b>${s.active_loans || 0}</b> active loan${(s.active_loans || 0) === 1 ? '' : 's'}.</div>
				<div class="loan-insights">
					${ins.map(([ic, t]) => `<div class="loan-insight"><span class="ic">${ic}</span><span>${t}</span></div>`).join('')}
				</div>
				<div style="margin-top:12px;">
					<span class="glossary-toggle" id="gloss-toggle">ⓘ What do these words mean?</span>
					<div class="glossary" id="gloss-body">
						${glossary.map(([t, dfn]) => `<div class="gloss-term"><b>${esc(t)}</b> — <span>${esc(dfn)}</span></div>`).join('')}
					</div>
				</div>
			</div>
		`);
		$('#gloss-toggle').off('click').on('click', function () {
			$('#gloss-body').toggleClass('open');
			$(this).text($('#gloss-body').hasClass('open') ? '▲ Hide the plain-English guide' : 'ⓘ What do these words mean?');
		});
	}

	// ---- plain-language "Loan Position" (the mockup) -------------------
	const TYPE_DESC = {
		'Term & Equipment Loans': 'Big long-term loans (plant, term loans)',
		'Vehicle Loans': 'Loans against trucks / pickups',
		'Business Loans (NBFC / Bank)': 'Working-capital loans from banks / finance companies',
		'Partner / Director Funds': 'Money put in by partners / directors',
		'Bank Overdraft': 'Flexible bank credit line, repaid as you go',
	};

	function render_position(rows) {
		if (!rows.length) { position_wrap.empty(); return; }
		let grand = rows.reduce((a, r) => a + Number(r.outstanding), 0) || 1;

		let body = rows.map(r => {
			let desc = TYPE_DESC[r.loan_type] || '';
			let share = Math.round(r.outstanding / grand * 100);
			let right = r.revolving
				? `<span class="loan-blue" style="font-weight:600;">Revolving credit line</span>`
				: (r.monthly > 0
					? `≈ <b>${money(r.monthly)}</b>/mo ${help('Estimated monthly payment, based on your actual payments over the last 6 months. Enter the real EMI later to make this exact.')}`
					: `<span class="loan-muted">—</span>`);
			let last = r.last_payment ? `Last paid ${frappe.datetime.str_to_user(r.last_payment)}` : '';
			return `
				<div class="loan-pos-row">
					<div class="pos-name">
						<div class="pos-title">${esc(r.loan_type)} <span class="loan-muted" style="font-weight:500;">· ${r.count} account${r.count === 1 ? '' : 's'}</span></div>
						<div class="pos-desc">${esc(desc)}</div>
					</div>
					<div class="pos-amt">
						<div class="pos-out">${money(r.outstanding)}</div>
						<div class="pos-share">${share}% of total</div>
					</div>
					<div class="pos-emi">${right}<div class="pos-last">${last}</div></div>
				</div>`;
		}).join('');

		position_wrap.html(`
			<div class="loan-panel" style="padding:0; overflow:hidden;">
				<div style="padding:12px 16px 4px;"><h4 style="margin:0;">Loan position — grouped by type</h4>
				<div class="loan-subhead" style="margin:2px 0 0;">A simple summary of what you owe, sorted biggest first.</div></div>
				<div class="loan-pos-table">${body}</div>
			</div>
		`);
	}

	// ---- EMI & payment-regularity (inferred from the ledger) -----------
	const REG = {
		on_track: { pill: 'st-green', label: '🟢 On track', txt: 'Paid regularly, no months missed.' },
		varies: { pill: 'st-amber', label: '🟠 Amounts vary', txt: 'Payments happen but the amount jumps around.' },
		off_track: { pill: 'st-red', label: '🔴 Check this', txt: 'A month was missed, or the next payment is overdue.' },
	};

	function ord(n) { let s = ['th', 'st', 'nd', 'rd'], v = n % 100; return n + (s[(v - 20) % 10] || s[v] || s[0]); }

	function render_emi(cards) {
		let rows = (cards || []).filter(c => !c.revolving && Math.abs(c.outstanding) > 1 && c.emi_amount > 0 && c.regularity);
		if (!rows.length) { emi_wrap.empty(); return; }
		// Anything needing attention floats to the top.
		let rank = { off_track: 0, varies: 1, on_track: 2 };
		rows.sort((a, b) => (rank[a.regularity] - rank[b.regularity]) || (b.emi_amount - a.emi_amount));

		let attn = rows.filter(r => r.regularity !== 'on_track').length;

		let body = rows.map(r => {
			let reg = REG[r.regularity] || REG.on_track;
			return `
				<div class="emi-row">
					<div>
						<div class="emi-name">${esc(r.account_name)}</div>
						<div class="emi-sub">${esc(r.loan_type || '')}</div>
					</div>
					<div class="emi-amt">${money(r.emi_amount)}<div class="emi-cap">per month${r.emi_day ? ' · ' + ord(r.emi_day) : ''}</div></div>
					<div class="emi-due">
						<div>${r.next_due ? 'Next ~ ' + frappe.datetime.str_to_user(r.next_due) : '—'}</div>
						<div class="emi-cap">last paid ${r.last_repayment ? frappe.datetime.str_to_user(r.last_repayment) : '—'}</div>
					</div>
					<div class="emi-status"><span class="stpill ${reg.pill}" title="${esc(reg.txt)}">${reg.label}</span></div>
				</div>`;
		}).join('');

		emi_wrap.html(`
			<div class="loan-panel" style="padding:0; overflow:hidden;">
				<div style="padding:12px 16px 4px;">
					<h4 style="margin:0;">EMIs & payment regularity <span class="help-icon" title="Worked out automatically from your actual monthly payments — the system stores no EMI schedule. 'EMI' is the recurring monthly payment we detected; 'Next' is when the following one is expected.">i</span></h4>
					<div class="loan-subhead" style="margin:2px 0 0;">${attn ? `<b class="loan-red">${attn} loan${attn > 1 ? 's' : ''} need a look</b> — ` : 'All instalment loans are being paid on time. '}sorted with anything unusual first.</div>
				</div>
				<div class="emi-table">
					<div class="emi-row emi-head">
						<div>Loan</div><div class="emi-amt">EMI (detected)</div><div class="emi-due">Next / last payment</div><div class="emi-status">Status</div>
					</div>
					${body}
				</div>
			</div>
		`);
	}

	function render_kpis(s) {
		let total = Number(s.total_outstanding) || 0;
		let pct = (x) => total ? Math.round((Number(x) || 0) / total * 100) : 0;

		header_stats.html(`
			<div style="line-height:1.15;">
				<div class="v loan-blue" style="font-size:16px; font-weight:700;">${money(total)}</div>
				<div class="l" style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600;">Total Owed</div>
			</div>
		`);

		kpi_wrap.html(
			kpi('Total Owed', money(s.total_outstanding), `Across ${s.active_loans || 0} active loans`, 'loan-blue', true,
				'All the money the business still has to pay back on every loan and overdraft, added up.') +
			kpi('Backed by Assets', money(s.secured), `${pct(s.secured)}% of what you owe`, 'loan-green', false,
				'Secured loans — backed by vehicles/property the lender can claim if unpaid.') +
			kpi('Not Backed', money(s.unsecured), `${pct(s.unsecured)}% of what you owe`, 'loan-orange', false,
				'Unsecured loans — no asset behind them, usually from banks or finance companies.') +
			kpi('Bank Overdraft', money(s.od), `${pct(s.od)}% of what you owe`, 'loan-blue', false,
				'A flexible bank credit line you use and repay as needed.') +
			kpi('Interest Paid', money(s.interest_paid), 'The extra you paid lenders, this period', 'loan-red', false,
				'Interest is the lender\'s charge on top of the amount borrowed. This is what you paid in interest during the selected period.') +
			kpi('Loan Paid Off', money(s.principal_repaid), 'Balance reduced, this period', 'loan-green', false,
				'How much of the actual loan balance you cleared this period (overdraft churn excluded).') +
			kpi('New Loans Taken', money(s.disbursed), 'Borrowed this period', 'loan-muted', false,
				'New loan money received during the selected period.')
		);
	}

	function render_out_chart(c) {
		let panel = $('#loan-out-chart').closest('.loan-panel');
		if (!c.labels || !c.labels.length) { panel.hide(); if (out_chart) { out_chart.destroy(); out_chart = null; } return; }
		panel.show();
		let data = {
			labels: c.labels.map(l => l.length > 22 ? l.substring(0, 22) + '…' : l),
			datasets: [{ name: 'Outstanding', values: c.values }]
		};
		if (out_chart) { out_chart.update(data); }
		else {
			out_chart = new frappe.Chart('#loan-out-chart', {
				data, type: 'bar', height: 320,
				colors: ['#2563eb'],
				axisOptions: { xAxisMode: 'tick', shortenYAxisNumbers: 1 },
				barOptions: { spaceRatio: 0.3 },
				tooltipOptions: { formatTooltipY: (v) => money(v) }
			});
		}
	}

	function render_comp_chart(c) {
		let vals = (c.values || []).map(Number);
		let panel = $('#loan-comp-chart').closest('.loan-panel');
		if (!vals.some(v => v > 0)) { panel.hide(); if (comp_chart) { comp_chart.destroy(); comp_chart = null; } return; }
		panel.show();
		let data = { labels: c.labels, datasets: [{ values: vals }] };
		if (comp_chart) { comp_chart.update(data); }
		else {
			comp_chart = new frappe.Chart('#loan-comp-chart', {
				data, type: 'donut', height: 320,
				colors: ['#16a34a', '#ea580c', '#2563eb'],
				tooltipOptions: { formatTooltipY: (v) => money(v) }
			});
		}

		const COMP_PLAIN = {
			'Secured': 'Backed by assets',
			'Unsecured': 'Not backed',
			'OD': 'Bank overdraft',
		};
		const COMP_COLOR = { 'Secured': '#16a34a', 'Unsecured': '#ea580c', 'OD': '#2563eb' };
		let tot = vals.reduce((a, b) => a + b, 0) || 1;
		$('#loan-comp-legend').html((c.labels || []).map((lbl, i) => `
			<div><span class="dot" style="background:${COMP_COLOR[lbl] || '#888'};"></span>
			${esc(COMP_PLAIN[lbl] || lbl)} — <b style="color:var(--text-color);">${money(vals[i])}</b> (${Math.round(vals[i] / tot * 100)}%)</div>
		`).join(''));
	}

	function render_trend(t) {
		let panel = $('#loan-trend-chart').closest('.loan-panel');
		if (!t.labels || !t.labels.length) { panel.hide(); if (trend_chart) { trend_chart.destroy(); trend_chart = null; } return; }
		panel.show();
		let data = {
			labels: t.labels,
			datasets: [
				{ name: 'Principal Repaid', values: t.repaid, chartType: 'bar' },
				{ name: 'Interest Paid', values: t.interest, chartType: 'line' }
			]
		};
		if (trend_chart) { trend_chart.update(data); }
		else {
			trend_chart = new frappe.Chart('#loan-trend-chart', {
				data, type: 'axis-mixed', height: 260,
				colors: ['#16a34a', '#dc2626'],
				axisOptions: { xAxisMode: 'tick', shortenYAxisNumbers: 1 },
				tooltipOptions: { formatTooltipY: (v) => money(v) }
			});
		}
	}

	function render_interest(rows) {
		rows = (rows || []).filter(r => Math.abs(Number(r.amount)) > 0);
		if (!rows.length) { interest_wrap.hide(); return; }
		interest_wrap.show();
		let total = rows.reduce((a, r) => a + Number(r.amount), 0) || 1;
		let items = rows.map(r => `
			<div class="loan-row">
				<span class="k">${esc(r.account_name)}</span>
				<span class="val loan-red">${money(r.amount)} <span class="loan-muted" style="font-weight:500;">· ${Math.round(r.amount / total * 100)}%</span></span>
			</div>`).join('');
		interest_wrap.html(`
			<div class="loan-panel">
				<h4>What each loan is costing you in interest</h4>
				<div class="loan-subhead">Interest is the extra charge lenders add. This is what you paid on each, this period.</div>
				${items}
			</div>`);
	}

	function render_cards(cards, s) {
		let total = Number(s.total_outstanding) || 0;
		cards_head.html(`Every loan, one by one <span class="loan-muted" style="font-weight:400;">(${cards.length} accounts — click any to open its ledger)</span>`);

		if (!cards.length) {
			cards_wrap.html(`<div class="text-muted" style="grid-column:1/-1; text-align:center; padding:40px;">No loan or OD accounts found for this company.</div>`);
			return;
		}

		let html = '';
		cards.forEach(d => {
			let cls = (d.category || '').toLowerCase();
			let share = total ? Math.round(d.outstanding / total * 100) : 0;
			let change = d.outstanding - d.opening;
			let gl = `/app/query-report/General Ledger?company=${encodeURIComponent(company.get_value() || '')}&account=${encodeURIComponent(d.account)}&from_date=${encodeURIComponent(from_date.get_value())}&to_date=${encodeURIComponent(to_date.get_value())}`;
			let settled = Math.abs(d.outstanding) <= 1;

			html += `
				<div class="loan-card" style="${settled ? 'opacity:.62;' : ''}">
					<div style="display:flex; justify-content:space-between; gap:10px; align-items:flex-start;">
						<div style="min-width:0;">
							<div class="loan-title">${esc(d.account_name)}</div>
							<div class="loan-sub"><span class="pill ${cls}">${esc(d.category)}</span> <span class="loan-muted">${esc(d.loan_type || '')}</span>${d.account_number ? ' <span class="loan-muted">· ' + esc(d.account_number) + '</span>' : ''}</div>
						</div>
						<div style="text-align:right; white-space:nowrap;">
							<div class="loan-blue" style="font-size:18px; font-weight:700;">${money(d.outstanding)}</div>
							<div class="loan-muted" style="font-size:11px;">${share}% of debt</div>
						</div>
					</div>

					<div class="loan-bar"><span style="width:${Math.min(share, 100)}%;"></span></div>

					${(!d.revolving && d.emi_amount > 0 && d.regularity) ? `
					<div style="margin-top:12px; padding:8px 10px; border-radius:var(--border-radius-md, 8px); border:1px solid var(--border-color); background:var(--subtle-fg, var(--control-bg)); display:flex; justify-content:space-between; align-items:center; gap:8px;">
						<div style="font-size:12px;">
							<b>${money(d.emi_amount)}</b> <span class="loan-muted">/mo${d.emi_day ? ' · usually ' + ord(d.emi_day) : ''}</span>
							${d.next_due ? `<div class="loan-muted" style="font-size:11px; margin-top:1px;">next ~ ${frappe.datetime.str_to_user(d.next_due)}</div>` : ''}
						</div>
						<span class="stpill ${(REG[d.regularity] || REG.on_track).pill}" title="${esc((REG[d.regularity] || REG.on_track).txt)}">${(REG[d.regularity] || REG.on_track).label}</span>
					</div>` : ''}

					<div style="margin-top:12px;">
						<div class="loan-row"><span class="k">Owed at start of period</span><span class="val">${money(d.opening)}</span></div>
						<div class="loan-row"><span class="k">${d.revolving ? 'Overdraft used more/less by' : 'Went up / down by'} ${help(d.revolving ? 'How much more (or less) of the overdraft was in use by the end of the period.' : 'How the amount owed changed over the period. Down (green) means you paid it down.')}</span><span class="val ${change < 0 ? 'loan-green' : (change > 0 ? 'loan-red' : 'loan-muted')}">${change > 0 ? '+' : ''}${money(change)}</span></div>
						${d.revolving
							? `<div class="loan-row"><span class="k">Money in / out ${help('An overdraft cycles money in and out constantly, so these totals are just flow — not real repayment.')}</span><span class="val loan-muted">${money(d.disbursed)} / ${money(d.repaid)}</span></div>
							   <div class="loan-row"><span class="k">Type of facility</span><span class="val loan-blue">Flexible credit line</span></div>`
							: `<div class="loan-row"><span class="k">Paid back this period</span><span class="val loan-green">${money(d.repaid)}</span></div>
							   ${Number(d.disbursed) > 0 ? `<div class="loan-row"><span class="k">New money taken</span><span class="val loan-orange">${money(d.disbursed)}</span></div>` : ''}
							   <div class="loan-row"><span class="k">Roughly per month ${help('Estimated monthly payment, from your actual payments over the last 6 months. This is a stand-in for the EMI, which isn\'t stored in the system.')}</span><span class="val">${d.approx_monthly > 0 ? money(d.approx_monthly) : '—'}</span></div>`
						}
						<div class="loan-row"><span class="k">Last payment made</span><span class="val">${d.last_repayment ? frappe.datetime.str_to_user(d.last_repayment) : '<span class="loan-muted">none yet</span>'}</span></div>
					</div>

					<div style="margin-top:10px; font-size:11px;">
						<a href="${gl}" target="_blank" class="loan-link">See every transaction →</a>
						${settled ? '<span class="loan-muted" style="float:right;">fully paid off</span>' : ''}
					</div>
				</div>`;
		});
		cards_wrap.html(html);
	}

	// Auto-load on open, then let filter changes drive reloads.
	setTimeout(() => { load_data(); ready = true; }, 150);
};
