frappe.pages["franchise-pos-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Franchise POS Dashboard"), single_column: true });
	new FranchisePOSDashboard(page);
};

class FranchisePOSDashboard {
	constructor(page) {
		this.page = page;
		this.body = $('<div class="fpos-dash"></div>').appendTo(page.main);
		this.add_style();
		const today = frappe.datetime.get_today();
		this.from = page.add_field({ fieldname: "from_date", label: __("From"), fieldtype: "Date",
			default: frappe.datetime.add_days(today, -6), change: () => this.load() });
		this.to = page.add_field({ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: today,
			change: () => this.load() });
		this.franchise = page.add_field({ fieldname: "franchise", label: __("Franchise"), fieldtype: "Link",
			options: "Customer", get_query: () => ({ filters: { custom_franchise_pos: 1 } }), change: () => this.load() });
		page.set_secondary_action(__("Refresh"), () => this.load(), "refresh");
		this.load();
	}

	load() {
		const args = { from_date: this.from.get_value(), to_date: this.to.get_value(), franchise: this.franchise.get_value() || null };
		if (!args.from_date || !args.to_date) return;
		const key = JSON.stringify(args);
		if (key === this.loading) return;
		this.loading = key;
		frappe.call({ method: "dairy.franchise_pos.page.franchise_pos_dashboard.franchise_pos_dashboard.get_data", args })
			.then((r) => { if (this.loading === key) this.render(r.message); })
			.always(() => { if (this.loading === key) this.loading = null; });
	}

	render(d) {
		const money = (v) => format_currency(v || 0, frappe.defaults.get_default("currency"), 0);
		const esc = frappe.utils.escape_html;
		const date = (v) => (v ? frappe.datetime.str_to_user(v) : "-");
		const k = d.kpi;
		const cards = [
			[__("Franchise Sales (MRP)"), money(k.net_sales), `${k.bills} ${__("bills")}`],
			d.can_invoice ? [__("Bought from BDF"), money(k.bought), __("invoice value")] : null,
			d.can_stock ? [__("Stock in Hand (MRP)"), money(k.stock_value), __("as of now")] : null,
			d.can_stock ? [__("Wastage (MRP)"), money(k.wastage_value), __("in this period")] : null,
			[__("Billed Today"), `${k.billed_today} / ${k.franchises}`, __("franchises")],
			[__("Day Close Pending"), k.close_pending, __("franchises"), k.close_pending ? "red" : "green"],
		].filter(Boolean);

		const rows = d.franchises.map((r) => `
			<tr>
				<td><a href="/app/customer/${encodeURIComponent(r.franchise)}"><b>${esc(r.franchise)}</b></a>
					<div class="text-muted small">${esc([r.franchise_name, r.territory].filter(Boolean).join(" · "))}</div></td>
				${d.can_invoice ? `<td class="text-right">${money(r.bought)}</td>` : ""}
				<td class="text-right"><b>${money(r.net_sales)}</b></td>
				<td class="text-right">${r.bills}</td>
				${d.can_stock ? `<td class="text-right">${money(r.stock_value)}</td><td class="text-right">${money(r.wastage_value)}</td>` : ""}
				<td>${date(r.last_bill)}</td>
				<td><span class="indicator-pill ${r.close_pending ? "red" : "green"}">${date(r.last_close)}</span></td>
			</tr>`).join("");

		const items = d.items.map((i) => `
			<tr><td>${esc(i.item_name || i.item_code)}</td>
			<td class="text-right">${format_number(i.qty, null, 0)} ${esc(i.uom || "")}</td>
			<td class="text-right">${money(i.amount)}</td></tr>`).join("");
		const modes = d.modes.map((m) => `
			<tr><td>${esc(m.payment_mode || "-")}</td><td class="text-right">${money(m.amount)}</td></tr>`).join("");
		const empty = (cols) => `<tr><td colspan="${cols}" class="text-muted text-center">${__("Nothing in this period")}</td></tr>`;

		this.body.html(`
			<div class="fpos-cards">${cards.map((c) => `
				<div class="fpos-card"><div class="fpos-label">${c[0]}</div>
				<div class="fpos-value ${c[3] ? "text-" + (c[3] === "red" ? "danger" : "success") : ""}">${c[1]}</div>
				<div class="text-muted small">${c[2]}</div></div>`).join("")}</div>
			<div class="fpos-box"><div class="fpos-title">${__("Daily Sales")}</div><div class="fpos-chart"></div></div>
			<div class="fpos-box"><div class="fpos-title">${__("Franchise-wise")}</div>
				<div class="fpos-scroll"><table class="table table-sm fpos-table"><thead><tr>
					<th>${__("Franchise")}</th>${d.can_invoice ? `<th class="text-right">${__("Bought from BDF")}</th>` : ""}
					<th class="text-right">${__("Sold (MRP)")}</th><th class="text-right">${__("Bills")}</th>
					${d.can_stock ? `<th class="text-right">${__("Stock in Hand")}</th><th class="text-right">${__("Wastage")}</th>` : ""}
					<th>${__("Last Bill")}</th><th>${__("Last Day Close")}</th>
				</tr></thead><tbody>${rows || empty(8)}</tbody></table></div></div>
			<div class="fpos-two">
				<div class="fpos-box"><div class="fpos-title">${__("Top Items")}</div>
					<table class="table table-sm fpos-table"><thead><tr><th>${__("Item")}</th>
					<th class="text-right">${__("Qty")}</th><th class="text-right">${__("Amount")}</th></tr></thead>
					<tbody>${items || empty(3)}</tbody></table></div>
				<div class="fpos-box"><div class="fpos-title">${__("Payment Mode")}</div>
					<table class="table table-sm fpos-table"><thead><tr><th>${__("Mode")}</th>
					<th class="text-right">${__("Amount")}</th></tr></thead><tbody>${modes || empty(2)}</tbody></table></div>
			</div>`);

		const chart_el = this.body.find(".fpos-chart")[0];
		if (d.trend.length) {
			new frappe.Chart(chart_el, {
				type: "bar", height: 220, colors: ["#2490ef"],
				data: {
					labels: d.trend.map((t) => frappe.datetime.str_to_user(t.posting_date).slice(0, 5)),
					datasets: [{ name: __("Net Sales"), values: d.trend.map((t) => t.amount) }],
				},
				axisOptions: { xIsSeries: true },
				tooltipOptions: { formatTooltipY: (v) => money(v) },
			});
		} else {
			$(chart_el).html(`<div class="text-muted text-center" style="padding:40px 0">${__("No bills in this period")}</div>`);
		}
	}

	add_style() {
		if (document.getElementById("fpos-dash-style")) return;
		$(`<style id="fpos-dash-style">
			.fpos-dash { padding: 12px 0 30px; }
			.fpos-cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; margin-bottom: 14px; }
			.fpos-card, .fpos-box { background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 10px; padding: 14px 16px; }
			.fpos-box { margin-bottom: 14px; }
			.fpos-label { font-size: 12px; color: var(--text-muted); }
			.fpos-value { font-size: 22px; font-weight: 600; margin: 4px 0 2px; }
			.fpos-title { font-weight: 600; margin-bottom: 10px; }
			.fpos-two { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; }
			.fpos-two .fpos-box { margin-bottom: 0; }
			.fpos-scroll { overflow-x: auto; }
			.fpos-table { margin: 0; }
			.fpos-table th { font-weight: 500; color: var(--text-muted); border-top: 0; white-space: nowrap; }
			.fpos-table td { vertical-align: middle; }
		</style>`).appendTo(document.head);
	}
}
