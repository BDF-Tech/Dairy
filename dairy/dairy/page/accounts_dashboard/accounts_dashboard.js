frappe.pages['accounts-dashboard'].on_page_load = function (wrapper) {

	const page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Accounts Dashboard',
		single_column: true
	});

	// ======================
	// LOADER & THEME-AWARE STYLES
	// All colours come from Frappe CSS variables so contrast stays correct in
	// both the light and dark desk themes.
	// ======================
	$(`
		<div id="acc-dash-loader" style="
			position:fixed; top:0; left:0; width:100%; height:100%;
			background: rgba(127,127,127,0.25); backdrop-filter: blur(3px);
			display:none; align-items:center; justify-content:center; z-index:10001;">
			<div class="acc-spinner"><div></div><div></div><div></div><div></div></div>
		</div>
	`).appendTo('body');

	if ($('#acc-dash-styles').length === 0) {
		$(`<style id="acc-dash-styles">
		.acc-spinner { display:inline-block; position:relative; width:64px; height:64px; }
		.acc-spinner div { box-sizing:border-box; display:block; position:absolute; width:51px; height:51px; margin:6px; border:4px solid var(--primary, #2563eb); border-radius:50%; animation:acc-spin 1.2s linear infinite; border-color:var(--primary, #2563eb) transparent transparent transparent; }
		.acc-spinner div:nth-child(1){ animation-delay:-0.45s; }
		.acc-spinner div:nth-child(2){ animation-delay:-0.3s; }
		.acc-spinner div:nth-child(3){ animation-delay:-0.15s; }
		@keyframes acc-spin { 0%{ transform:rotate(0deg);} 100%{ transform:rotate(360deg);} }

		.acc-sec-head { margin-top:24px; font-size:13px; font-weight:600; color:var(--text-color); display:flex; align-items:baseline; gap:8px; }
		.acc-sec-head .sub { font-size:11.5px; color:var(--text-muted); font-weight:400; }

		.acc-kpis { display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:12px; margin-top:10px; }
		.acc-kpi { padding:14px 16px; background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-lg, 12px); box-shadow:var(--card-shadow, none); }
		.acc-kpi.hero { border-left:3px solid var(--primary, #2563eb); }
		.acc-kpi .l { font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600; letter-spacing:.3px; }
		.acc-kpi .v { font-size:22px; font-weight:700; margin-top:2px; }
		.acc-kpi .s { font-size:11px; color:var(--text-muted); margin-top:2px; }

		.acc-panel { background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-lg, 12px); overflow:hidden; margin-top:10px; }
		.acc-panel .p-head { padding:12px 16px 4px; }
		.acc-panel h4 { font-size:12px; text-transform:uppercase; letter-spacing:.3px; color:var(--text-muted); font-weight:600; margin:0; }
		.acc-panel .p-sub { font-size:11.5px; color:var(--text-muted); margin:2px 0 0; }

		.acc-table { border-top:1px solid var(--border-color); }
		.acc-row { display:grid; align-items:center; gap:12px; padding:11px 16px; border-bottom:1px solid var(--border-color); }
		.acc-row:last-child { border-bottom:none; }
		.acc-row.head { font-size:10.5px; text-transform:uppercase; letter-spacing:.3px; color:var(--text-muted); font-weight:600; background:var(--subtle-fg, var(--control-bg)); }
		.acc-name { font-size:13px; font-weight:600; color:var(--heading-color, var(--text-color)); }
		.acc-num { text-align:right; font-weight:600; color:var(--text-color); white-space:nowrap; }
		.acc-muted { color:var(--text-muted); }
		.acc-green { color:var(--green-600, #16a34a); }
		.acc-red { color:var(--red-600, #dc2626); }
		.acc-blue { color:var(--blue-600, #2563eb); }
		.acc-orange { color:var(--orange-600, #ea580c); }

		.acc-two { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:10px; }
		@media (max-width: 720px){ .acc-two { grid-template-columns:1fr; } }
		.acc-trends { display:grid; grid-template-columns:repeat(2, 1fr); gap:12px; margin-top:10px; }
		@media (max-width: 720px){ .acc-trends { grid-template-columns:1fr; } }
		.acc-chart text { fill:var(--text-muted) !important; }

		.acc-out-total { padding:14px 16px 6px; }
		.acc-out-total .l { font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600; letter-spacing:.3px; }
		.acc-out-total .v { font-size:24px; font-weight:700; margin-top:2px; }
		.acc-out-total .adv { font-size:11.5px; color:var(--text-muted); margin-top:3px; }

		.acc-alert-panel { background:var(--card-bg); border:1px solid var(--border-color); border-left:3px solid var(--red-600, #dc2626); border-radius:var(--border-radius-lg, 12px); overflow:hidden; margin-top:15px; }
		.acc-alert-row { display:flex; justify-content:space-between; align-items:center; gap:10px; padding:11px 16px; border-bottom:1px solid var(--border-color); font-size:13px; }
		.acc-alert-row:last-child { border-bottom:none; }
		.acc-alert-row .lbl { color:var(--text-color); display:flex; gap:8px; align-items:center; }
		.acc-alert-row .amt { font-weight:700; color:var(--red-600, #dc2626); white-space:nowrap; }
		.acc-alert-ok { padding:12px 16px; font-size:12.5px; color:var(--text-muted); }

		.acc-intro { background:var(--subtle-fg, var(--control-bg)); border:1px solid var(--border-color); border-left:3px solid var(--primary, #2563eb); border-radius:var(--border-radius-lg, 12px); padding:16px 18px; margin-top:15px; }
		.acc-intro .head { font-size:15px; font-weight:700; color:var(--heading-color, var(--text-color)); }
		.acc-intro .headline { font-size:13.5px; color:var(--text-color); margin-top:2px; }
		.acc-insights { display:grid; grid-template-columns:repeat(auto-fit, minmax(260px, 1fr)); gap:8px 20px; margin-top:12px; }
		.acc-insight { font-size:12.8px; color:var(--text-color); display:flex; gap:8px; align-items:flex-start; line-height:1.4; }
		.acc-insight .ic { flex:0 0 auto; font-size:14px; line-height:1.3; }
		.acc-insight b { color:var(--heading-color, var(--text-color)); }
		</style>`).appendTo('head');
	}

	// Compact Indian-currency formatter.
	const inr = (v) => parseFloat((Number(v) || 0).toFixed(2)).toLocaleString('en-IN');
	function money(v) {
		v = Number(v) || 0;
		const a = Math.abs(v), sign = v < 0 ? '-' : '';
		if (a >= 1e7) return `${sign}₹${(a / 1e7).toFixed(2)} Cr`;
		if (a >= 1e5) return `${sign}₹${(a / 1e5).toFixed(2)} L`;
		return `${sign}₹${inr(a)}`;
	}
	const esc = frappe.utils.escape_html;
	const show_loader = () => $("#acc-dash-loader").css('display', 'flex');
	const hide_loader = () => $("#acc-dash-loader").hide();

	// ======================
	// FILTERS
	// Most figures are "activity in the selected range" (default: today);
	// balances/stock are as-of the To Date. The Period select rewrites From/To.
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
		options: ['Today', 'Yesterday', 'This Week', 'This Month', 'This Fiscal Year', 'Custom'],
		default: 'Today',
		change() { apply_period(); reload_soon(); }
	});

	let from_date = page.add_field({ label: 'From Date', fieldtype: 'Date', change() { reload_soon(); } });
	let to_date = page.add_field({ label: 'To Date', fieldtype: 'Date', change() { reload_soon(); } });

	function apply_period() {
		let p = period.get_value();
		let today = frappe.datetime.get_today();
		if (p === 'Custom') return;
		let f = today, t = today;
		if (p === 'Yesterday') { f = t = frappe.datetime.add_days(today, -1); }
		else if (p === 'This Week') { f = moment().startOf('week').format('YYYY-MM-DD'); }
		else if (p === 'This Month') { f = moment().startOf('month').format('YYYY-MM-DD'); }
		else if (p === 'This Fiscal Year') { f = frappe.datetime.get_today().slice(0, 4) + '-04-01'; }
		from_date.set_value(f);
		to_date.set_value(t);
	}
	apply_period();

	// ======================
	// LAYOUT
	// ======================
	let header_stats = $(`<div id="acc-header-stats" style="display:flex; gap:22px; align-items:center; margin-right:14px;"></div>`);
	page.page_actions.prepend(header_stats);

	let intro_wrap = $(`<div id="acc-intro"></div>`).appendTo(page.body);

	// Section: Alerts (red items only)
	let alerts_wrap = $(`<div id="acc-alerts"></div>`).appendTo(page.body);

	// Section: Customer / Vendor outstanding (two columns)
	$(`<div class="acc-sec-head">Outstanding <span class="sub" id="acc-out-asof"></span></div>`).appendTo(page.body);
	let outstanding_wrap = $(`<div class="acc-two" id="acc-outstanding"></div>`).appendTo(page.body);

	// Section: Payment today / Collection today (two columns)
	$(`<div class="acc-sec-head">Money moved <span class="sub" id="acc-moved-range"></span></div>`).appendTo(page.body);
	let moved_wrap = $(`<div class="acc-two" id="acc-moved"></div>`).appendTo(page.body);

	// Section: Sales & Bills
	$(`<div class="acc-sec-head">Sales &amp; bills <span class="sub" id="acc-flow-range"></span></div>`).appendTo(page.body);
	let flow_kpis = $(`<div class="acc-kpis" id="acc-flow-kpis"></div>`).appendTo(page.body);
	let wh_wrap = $(`<div id="acc-wh"></div>`).appendTo(page.body);

	// Section: Cash collected
	$(`<div class="acc-sec-head">Cash collected <span class="sub">by mode of payment, in the selected range</span></div>`).appendTo(page.body);
	let cash_wrap = $(`<div id="acc-cash"></div>`).appendTo(page.body);

	// Section: Bank movement
	$(`<div class="acc-sec-head">Bank movement <span class="sub">ICICI accounts — money in / out in range, and current balance</span></div>`).appendTo(page.body);
	let bank_wrap = $(`<div id="acc-bank"></div>`).appendTo(page.body);

	// Section: Fiscal year to date
	$(`<div class="acc-sec-head">Fiscal year to date <span class="sub" id="acc-fy-range"></span></div>`).appendTo(page.body);
	let fy_kpis = $(`<div class="acc-kpis" id="acc-fy-kpis"></div>`).appendTo(page.body);

	// Section: Balances & stock
	$(`<div class="acc-sec-head">Balances, stock &amp; assets <span class="sub" id="acc-bal-asof"></span></div>`).appendTo(page.body);
	let bal_kpis = $(`<div class="acc-kpis" id="acc-bal-kpis"></div>`).appendTo(page.body);

	// Section: 7-day trends (charts)
	$(`<div class="acc-sec-head">Last 7 days <span class="sub">daily sales, collections, net cash flow and net receivable</span></div>`).appendTo(page.body);
	let trend_wrap = $(`
		<div class="acc-trends">
			<div class="acc-panel"><div class="p-head"><h4>Sales</h4></div><div id="acc-tr-sales" class="acc-chart"></div></div>
			<div class="acc-panel"><div class="p-head"><h4>Collections</h4></div><div id="acc-tr-coll" class="acc-chart"></div></div>
			<div class="acc-panel"><div class="p-head"><h4>Net cash flow</h4></div><div id="acc-tr-cash" class="acc-chart"></div></div>
			<div class="acc-panel"><div class="p-head"><h4>Net receivable</h4></div><div id="acc-tr-out" class="acc-chart"></div></div>
		</div>`).appendTo(page.body);
	let tr_sales = null, tr_coll = null, tr_cash = null, tr_out = null;

	// ======================
	// LOAD
	// ======================
	// refresh=1 forces a live recompute of the cached balances/stock/FY block;
	// auto-load and filter changes use the cache (refresh=0) to spare the server.
	function load_data(refresh) {
		let f = from_date.get_value(), t = to_date.get_value();
		if (!f || !t) { frappe.msgprint('Please select From Date and To Date.'); return; }
		clearTimeout(reload_timer);
		const token = ++request_seq;
		show_loader();
		frappe.call({
			method: 'dairy.dairy.page.accounts_dashboard.accounts_dashboard.get_dashboard_data',
			args: { from_date: f, to_date: t, company: company.get_value() || null, refresh: refresh ? 1 : 0 },
			callback: (r) => {
				if (token !== request_seq) return;
				render(r && r.message || {});
				hide_loader();
			},
			error: () => { if (token === request_seq) hide_loader(); }
		});
	}
	// Explicit click = give me live numbers now.
	page.set_primary_action('Refresh', () => load_data(true), 'refresh');

	// ======================
	// RENDER
	// ======================
	function kpi(label, value, sub, cls, hero) {
		return `<div class="acc-kpi ${hero ? 'hero' : ''}">
			<div class="l">${esc(label)}</div>
			<div class="v ${cls || ''}">${value}</div>
			${sub ? `<div class="s">${sub}</div>` : ''}
		</div>`;
	}

	function render(d) {
		let asof = d.as_of ? frappe.datetime.str_to_user(d.as_of) : '';
		let rangeTxt = (from_date.get_value() === to_date.get_value())
			? asof
			: `${frappe.datetime.str_to_user(from_date.get_value())} – ${asof}`;

		// Header quick stats
		let bal = d.balances || {};
		header_stats.html(`
			<div style="line-height:1.15;">
				<div class="v acc-blue" style="font-size:16px; font-weight:700;">${money(bal.cash_in_hand_bco)}</div>
				<div class="l" style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600;">Cash in Hand (BCO)</div>
			</div>
			<div style="line-height:1.15;">
				<div class="v ${(Number(bal.icici_od) < 0 ? 'acc-red' : 'acc-green')}" style="font-size:16px; font-weight:700;">${money(bal.icici_od)}</div>
				<div class="l" style="font-size:11px; color:var(--text-muted); text-transform:uppercase; font-weight:600;">ICICI OD Balance</div>
			</div>
		`);

		render_intro(d, rangeTxt);

		// ---- Alerts ----
		render_alerts(d.alerts || []);

		// ---- Outstanding ----
		$('#acc-out-asof').text(asof ? `net party balances, as of ${asof}` : '');
		render_outstanding(d.receivable || {}, d.payable || {});

		// ---- Money moved (payment / collection today) ----
		$('#acc-moved-range').text(`in ${rangeTxt}`);
		render_moved(d.payment_today || {}, d.collection_today || {});

		// ---- Sales & bills ----
		$('#acc-flow-range').text(`in ${rangeTxt}`);
		let flow = d.flow || {};
		flow_kpis.html(
			kpi('Outgoing Bills', money(flow.outgoing_bill), 'Sales invoiced (net), excl. internal transfer', 'acc-blue', true) +
			kpi('Purchase Invoices', flow.purchase_invoice_count || 0, 'Incoming bills booked', 'acc-orange') +
			kpi('Sales Returns', flow.sales_return_count || 0, 'Return invoices in range', 'acc-red')
		);
		render_warehouses(flow.warehouses || []);

		// ---- Cash collected ----
		render_cash(d.cash || [], d.cash_total);

		// ---- Bank movement ----
		render_bank(d.bank || []);

		// ---- Fiscal year to date ----
		let fy = d.fy || {};
		$('#acc-fy-range').text(fy.start ? `${frappe.datetime.str_to_user(fy.start)} – ${frappe.datetime.str_to_user(fy.end)}` : '');
		fy_kpis.html(
			kpi('Incoming Payments', money(fy.incoming_payment), 'Received from customers (FY)', 'acc-green', true) +
			kpi('Outgoing Payments', money(fy.outgoing_payment), 'Paid to vendors (FY)', 'acc-red') +
			kpi('Incoming Bills', money(fy.incoming_bills), 'Purchase invoices booked (FY)', 'acc-orange')
		);

		// ---- Balances, stock & assets ----
		$('#acc-bal-asof').text(asof ? `as of ${asof}` : '');
		let st = d.stock || {};
		bal_kpis.html(
			kpi('Cash in Hand (BCO)', money(bal.cash_in_hand_bco), 'GL balance', 'acc-blue', true) +
			kpi('ICICI OD 221255', money(bal.icici_od), 'GL balance', Number(bal.icici_od) < 0 ? 'acc-red' : 'acc-green') +
			kpi('ICICI CA 0325', money(bal.icici_ca), 'GL balance', 'acc-blue') +
			kpi('Total Stock Value', money(st.total), 'All warehouses', 'acc-green') +
			kpi('Audit Warehouses', money(st.audit), 'Valuation across audited stores', 'acc-muted') +
			kpi('Depo Stock', money(st.depo), 'Depo Warehouse valuation', 'acc-muted') +
			kpi('Vehicles', d.vehicles || 0, 'Fleet on record', 'acc-muted')
		);

		// ---- 7-day trends ----
		render_trends(d.trend || {});
	}

	function render_intro(d, rangeTxt) {
		let flow = d.flow || {}, fy = d.fy || {}, st = d.stock || {};
		let ins = [];
		ins.push(['🧾', `In <b>${esc(rangeTxt)}</b> you invoiced <b>${money(flow.outgoing_bill)}</b> in sales across <b>${(flow.warehouses || []).reduce((a, w) => a + (w.count || 0), 0)}</b> bills.`]);
		ins.push(['💵', `You collected <b>${money(d.cash_total)}</b> in cash (all modes) in this range.`]);
		if (Number(fy.incoming_payment) > 0) ins.push(['📈', `This fiscal year you've received <b>${money(fy.incoming_payment)}</b> and paid out <b>${money(fy.outgoing_payment)}</b>.`]);
		ins.push(['📦', `Stock on hand is worth <b>${money(st.total)}</b> across all warehouses.`]);

		intro_wrap.html(`
			<div class="acc-intro">
				<div class="head">At a glance</div>
				<div class="headline">Cash in hand (BCO) is <b>${money((d.balances || {}).cash_in_hand_bco)}</b>; the ICICI overdraft sits at <b>${money((d.balances || {}).icici_od)}</b>.</div>
				<div class="acc-insights">
					${ins.map(([ic, t]) => `<div class="acc-insight"><span class="ic">${ic}</span><span>${t}</span></div>`).join('')}
				</div>
			</div>
		`);
	}

	function render_warehouses(rows) {
		if (!rows.length) { wh_wrap.empty(); return; }
		let body = rows.map(r => `
			<div class="acc-row" style="grid-template-columns:1.6fr 1fr 0.8fr;">
				<div class="acc-name">${esc(r.label)}</div>
				<div class="acc-num acc-blue">${money(r.amount)}</div>
				<div class="acc-num acc-muted">${r.count} bill${r.count === 1 ? '' : 's'}</div>
			</div>`).join('');
		wh_wrap.html(`
			<div class="acc-panel">
				<div class="p-head"><h4>Sales by dispatch point</h4><div class="p-sub">Invoiced amount (rounded total) and bill count per warehouse.</div></div>
				<div class="acc-table">
					<div class="acc-row head" style="grid-template-columns:1.6fr 1fr 0.8fr;"><div>Location</div><div class="acc-num">Amount</div><div class="acc-num">Bills</div></div>
					${body}
				</div>
			</div>`);
	}

	function render_cash(rows, total) {
		if (!rows.length) { cash_wrap.empty(); return; }
		let cards = rows.map(r => kpi(r.label, money(r.value), '', Number(r.value) < 0 ? 'acc-red' : 'acc-green')).join('');
		cash_wrap.html(`<div class="acc-kpis">
			${kpi('Total Cash', money(total), 'All modes combined', 'acc-blue', true)}
			${cards}
		</div>`);
	}

	function render_bank(rows) {
		if (!rows.length) { bank_wrap.empty(); return; }
		let body = rows.map(r => `
			<div class="acc-row" style="grid-template-columns:1.4fr 1fr 1fr 1fr;">
				<div class="acc-name">${esc(r.label)}</div>
				<div class="acc-num acc-green">${money(r.receive)}</div>
				<div class="acc-num acc-red">${money(r.pay)}</div>
				<div class="acc-num ${Number(r.balance) < 0 ? 'acc-red' : 'acc-blue'}">${money(r.balance)}</div>
			</div>`).join('');
		bank_wrap.html(`
			<div class="acc-panel">
				<div class="acc-table">
					<div class="acc-row head" style="grid-template-columns:1.4fr 1fr 1fr 1fr;"><div>Account</div><div class="acc-num">Received</div><div class="acc-num">Paid</div><div class="acc-num">Balance (as of)</div></div>
					${body}
				</div>
			</div>`);
	}

	function render_alerts(rows) {
		if (!rows.length) {
			alerts_wrap.html(`<div class="acc-alert-panel" style="border-left-color:var(--green-600,#16a34a);"><div class="acc-alert-ok">✅ No red items — nothing needs attention right now.</div></div>`);
			return;
		}
		let body = rows.map(r => `
			<div class="acc-alert-row">
				<span class="lbl"><span>🔴</span> ${esc(r.label)}</span>
				<span class="amt">${money(r.value)}</span>
			</div>`).join('');
		alerts_wrap.html(`
			<div class="acc-alert-panel">
				<div class="p-head" style="padding:12px 16px 4px;"><h4 style="color:var(--red-600,#dc2626);">Alerts — items needing attention</h4></div>
				${body}
			</div>`);
	}

	function out_card(title, desc, total, totalCls, sub) {
		return `
			<div class="acc-panel">
				<div class="p-head"><h4>${esc(title)}</h4><div class="p-sub">${esc(desc)}</div></div>
				<div class="acc-out-total">
					<div class="l">Outstanding</div>
					<div class="v ${totalCls}">${money(total)}</div>
					<div class="adv">${sub}</div>
				</div>
			</div>`;
	}

	function render_outstanding(ar, ap) {
		outstanding_wrap.html(
			out_card('Customer Outstanding',
				'Net of what customers owe us (receipts are posted on-account, so this is the GL party balance, not open invoices).',
				ar.owed || 0, 'acc-blue',
				`Across <b>${ar.count || 0}</b> customer${(ar.count || 0) === 1 ? '' : 's'} · advances held: <b>${money(ar.advances)}</b>`) +
			out_card('Vendor Outstanding',
				'Net of what we owe suppliers, from the GL party balance.',
				ap.owed || 0, 'acc-red',
				`Across <b>${ap.count || 0}</b> supplier${(ap.count || 0) === 1 ? '' : 's'} · advances paid: <b>${money(ap.advances)}</b>`)
		);
	}

	function split_card(title, rows, totalCls) {
		let total = rows.reduce((a, r) => a + Number(r[1] || 0), 0);
		let body = rows.map(([lbl, val]) => `
			<div class="acc-row" style="grid-template-columns:1.4fr 1fr;">
				<div class="acc-name">${esc(lbl)}</div>
				<div class="acc-num">${money(val)}</div>
			</div>`).join('');
		return `
			<div class="acc-panel">
				<div class="p-head"><h4>${esc(title)}</h4></div>
				<div class="acc-out-total"><div class="l">Total</div><div class="v ${totalCls}">${money(total)}</div></div>
				<div class="acc-table">${body}</div>
			</div>`;
	}

	function render_moved(pay, coll) {
		moved_wrap.html(
			split_card('Payment Today', [
				['Vendor', pay.vendor], ['Milk', pay.milk], ['Salary', pay.salary],
			], 'acc-red') +
			split_card('Collection Today', [
				['Franchise', coll.franchise], ['Distributor', coll.distributor], ['Others', coll.others],
			], 'acc-green')
		);
	}

	function mini_chart(existing, sel, values, labels, color, type) {
		if (!labels || !labels.length) return existing;
		let data = { labels, datasets: [{ values }] };
		if (existing) { existing.update(data); return existing; }
		return new frappe.Chart(sel, {
			data, type: type || 'line', height: 180, colors: [color],
			axisOptions: { xAxisMode: 'tick', shortenYAxisNumbers: 1 },
			lineOptions: { hideDots: 0, regionFill: 1 },
			tooltipOptions: { formatTooltipY: (v) => money(v) }
		});
	}

	function render_trends(t) {
		let L = t.labels || [];
		tr_sales = mini_chart(tr_sales, '#acc-tr-sales', t.sales || [], L, '#2563eb', 'bar');
		tr_coll = mini_chart(tr_coll, '#acc-tr-coll', t.collection || [], L, '#16a34a', 'bar');
		tr_cash = mini_chart(tr_cash, '#acc-tr-cash', t.cashflow || [], L, '#ea580c', 'line');
		tr_out = mini_chart(tr_out, '#acc-tr-out', t.outstanding || [], L, '#7c3aed', 'line');
	}

	// Auto-load on open, then let filter changes drive reloads.
	setTimeout(() => { load_data(); ready = true; }, 150);
};
