// Copyright (c) 2026, BDF and contributors
// Complaint Dashboard — one request per filter change (server-cached); card clicks filter in the browser.

frappe.pages["complaint-dashboard"].on_page_load = function (wrapper) {
	const page = frappe.ui.make_app_page({ parent: wrapper, title: __("Complaint Dashboard"), single_column: true });
	wrapper.cd = new ComplaintDashboard(page);
};

frappe.pages["complaint-dashboard"].on_page_show = function (wrapper) {
	// coming back to the page: reload only if something changed while away
	if (wrapper.cd && wrapper.cd.dirty) wrapper.cd.load();
};

const CD = {
	method: "dairy.customer_service.page.complaint_dashboard.complaint_dashboard.get_dashboard",
	route: "complaint-dashboard",
	cards: [
		// key, label, accent, hint
		["mine", __("Waiting on Me"), "var(--green-600)", __("needs your action")],
		["today", __("Created Today"), "var(--blue-500)", __("logged today")],
		["open", __("New / Unassigned"), "var(--orange-500)", __("not assigned yet")],
		["in_process", __("In Process"), "var(--blue-600)", __("department working")],
		["approval", __("Pending Approval"), "var(--purple-500)", __("manager / accounts")],
		["overdue", __("Overdue"), "var(--red-500)", __("past due date")],
		["resolved", __("Resolved / Closed"), "var(--green-500)", __("in selected period")],
		["rejected", __("Rejected"), "var(--gray-600)", __("in selected period")],
		["period", __("All in Period"), "var(--gray-500)", __("complaints in period")],
	],
	status_color: {
		Open: "orange", Assigned: "blue", "Pending Approval": "purple", "Accounts Approval": "purple",
		Resolved: "green", Closed: "gray", Rejected: "darkgrey",
	},
	charts: [
		// key, title, type, colour, span
		["trend", __("Created vs Resolved"), "line", null, 2],
		["type", __("By Type"), "bar", "#ff5858", 1],
		["source", __("By Source"), "donut", null, 1],
		["department", __("Pending by Department"), "bar", "#743ee2", 1],
		["route", __("Customer Complaints by Route"), "bar", "#ffa00a", 1],
	],
};

class ComplaintDashboard {
	constructor(page) {
		this.page = page;
		this.bucket = "mine";
		this.charts = {};
		this.add_styles();
		this.make_filters();
		this.make_layout();
		page.set_primary_action(__("New Complaint"), () => frappe.new_doc("Customer Complaint"), "add");
		page.add_inner_button(__("Refresh"), () => this.load());
		page.add_menu_item(__("Complaint List"), () => frappe.set_route("List", "Customer Complaint"));
		page.add_menu_item(__("Complaint Register"), () => frappe.set_route("query-report", "Customer Complaint Register"));

		// no polling: the server signals after any complaint is saved; reload only if this page is on screen
		frappe.realtime.on("complaint_counters_stale", () => {
			this.dirty = true;
			if (this.visible()) this.load_soon();
		});
		$(document).on("visibilitychange.cd", () => this.dirty && this.visible() && this.load_soon());
		this.load();
	}

	visible() {
		return !document.hidden && frappe.get_route_str() === CD.route;
	}

	load_soon() {
		// several saves in a row (bulk approve) -> one reload
		clearTimeout(this.timer);
		this.timer = setTimeout(() => this.load(), 1500);
	}

	make_filters() {
		const today = frappe.datetime.get_today();
		const add = (df) => this.page.add_field(Object.assign({ change: () => this.load() }, df));
		this.filters = [
			add({ fieldname: "from_date", label: __("From"), fieldtype: "Date", default: frappe.datetime.add_days(today, -30) }),
			add({ fieldname: "to_date", label: __("To"), fieldtype: "Date", default: today }),
			add({ fieldname: "complaint_from", label: __("Complaint From"), fieldtype: "Select", options: ["", "Customer", "Employee", "Farmer", "Vendor", "Other"] }),
			add({ fieldname: "entry_type", label: __("Type"), fieldtype: "Select", options: ["", "Complaint", "Feedback", "Suggestion"] }),
			add({ fieldname: "source", label: __("Source"), fieldtype: "Select",
				options: ["", "Mobile App", "WhatsApp", "Phone Call", "Web Form", "Customer Visit", "Sales Person", "ERP", "Email"] }),
			add({ fieldname: "department", label: __("Department"), fieldtype: "Link", options: "Department" }),
			add({ fieldname: "route", label: __("Route"), fieldtype: "Link", options: "Route Master" }),
			add({ fieldname: "only_mine", label: __("Assigned to me"), fieldtype: "Check" }),
		];
	}

	get_filters() {
		const out = {};
		this.filters.forEach((fld) => {
			const v = fld.get_value();
			if (v) out[fld.df.fieldname] = v;
		});
		return out;
	}

	make_layout() {
		const charts = CD.charts.map(([key, title, , , span]) =>
			`<div class="cd-panel ${span === 2 ? "cd-span2" : ""}"><div class="cd-head">${title}<span class="cd-sub" data-sub="${key}"></span></div>
			 <div class="cd-chart" data-chart="${key}"></div></div>`).join("");
		this.$body = $(`<div class="cd">
			<div class="cd-kpis"></div>
			<div class="cd-grid">${charts}</div>
			<div class="cd-panel">
				<div class="cd-head cd-list-head"><span class="cd-list-title"></span><span class="cd-count"></span>
					<input type="search" class="form-control input-xs cd-search" placeholder="${__("Search customer, item, ID…")}"></div>
				<div class="cd-table-wrap"></div>
			</div>
			<div class="cd-foot"></div>
		</div>`).appendTo(this.page.main);
		this.$body.on("click", ".cd-kpi", (e) => {
			this.bucket = $(e.currentTarget).data("key");
			this.render_cards();
			this.render_rows(); // browser-side filter, no server call
		});
		this.$body.on("input", ".cd-search", frappe.utils.debounce(() => this.render_rows(), 200));
		this.$body.on("click", "tr[data-name]", (e) => frappe.set_route("Form", "Customer Complaint", $(e.currentTarget).data("name")));
	}

	load() {
		if (this.loading) {
			this.reload_after = true;
			return;
		}
		this.loading = true;
		this.dirty = false;
		frappe.xcall(CD.method, { filters: this.get_filters() }).then((d) => {
			this.data = d;
			this.render_cards();
			this.render_charts();
			this.render_rows();
			this.$body.find(".cd-foot").text(__("Updated {0}", [frappe.datetime.comment_when(d.generated)]));
		}).finally(() => {
			this.loading = false;
			if (this.reload_after) {
				this.reload_after = false;
				this.load();
			}
		});
	}

	render_cards() {
		const c = this.data.counts;
		const cards = CD.cards.map(([key, label, accent, hint]) => `
			<div class="cd-kpi ${key === this.bucket ? "active" : ""}" data-key="${key}" style="--cd:${accent}">
				<div class="cd-kpi-title"><span class="cd-dot"></span>${label}</div>
				<div class="cd-kpi-num">${c[key]}</div><div class="cd-kpi-hint">${hint}</div>
			</div>`).join("");
		this.$body.find(".cd-kpis").html(cards + `
			<div class="cd-kpi cd-static" style="--cd:var(--gray-500)">
				<div class="cd-kpi-title"><span class="cd-dot"></span>${__("Avg Resolution")}</div>
				<div class="cd-kpi-num">${this.data.avg_hours}<small> ${__("hrs")}</small></div>
				<div class="cd-kpi-hint">${__("complaint → resolution")}</div>
			</div>`);
	}

	render_charts() {
		const ch = this.data.charts;
		CD.charts.forEach(([key, , type, color]) => {
			const el = this.$body.find(`[data-chart="${key}"]`)[0];
			let data;
			if (key === "trend") {
				this.$body.find('[data-sub="trend"]').text(ch.trend.unit === "day" ? "" : " · " + __("per {0}", [__(ch.trend.unit)]));
				data = { labels: ch.trend.labels, datasets: [
					{ name: __("Created"), values: ch.trend.created }, { name: __("Resolved"), values: ch.trend.resolved }] };
			} else {
				data = { labels: ch[key].map((r) => r[0]), datasets: [{ name: __("Count"), values: ch[key].map((r) => r[1]) }] };
			}
			if (!data.datasets.some((s) => s.values.some((v) => v))) {
				$(el).html(`<div class="cd-empty">${__("No data for these filters")}</div>`);
				delete this.charts[key];
				return;
			}
			if (this.charts[key] && this.charts[key].type === type) {
				this.charts[key].update(data); // reuse the chart, no re-create
				return;
			}
			$(el).empty();
			this.charts[key] = new frappe.Chart(el, {
				type, data, height: 220, animate: false,
				colors: key === "trend" ? ["#5e64ff", "#29cd42"] : color ? [color] : undefined,
				lineOptions: { regionFill: 1, hideDots: ch.trend.labels.length > 31 },
				axisOptions: { xIsSeries: 1, shortenYAxisNumbers: 1 },
			});
			this.charts[key].type = type;
		});
	}

	render_rows() {
		const esc = frappe.utils.escape_html;
		const label = (CD.cards.find((c) => c[0] === this.bucket) || [, ""])[1];
		const q = (this.$body.find(".cd-search").val() || "").toLowerCase().trim();
		let rows = this.data.rows.filter((r) => r.b.includes(this.bucket));
		if (q) rows = rows.filter((r) => [r.name, r.raised_by, r.item, r.type, r.route, r.desc].some((v) => v && v.toLowerCase().includes(q)));
		// overdue first, then severity, then newest
		const sev = { Critical: 0, Major: 1, Minor: 2 };
		rows.sort((a, b) => (b.overdue - a.overdue) || ((sev[a.severity] ?? 3) - (sev[b.severity] ?? 3)) || (a.date < b.date ? 1 : -1));
		this.$body.find(".cd-list-title").text(label);
		this.$body.find(".cd-count").text(rows.length);
		const LIMIT = 300; // keep the DOM light; search narrows further
		const html = rows.slice(0, LIMIT).map((r) => `
			<tr data-name="${esc(r.name)}" class="${r.overdue ? "cd-overdue" : ""}">
				<td><a class="cd-id">${esc(r.name)}</a>${r.confidential ? ` <span class="cd-tag cd-red-tag">${__("Confidential")}</span>` : ""}
					<div class="cd-muted">${r.date ? frappe.datetime.str_to_user(r.date) : ""} · ${r.age ?? ""}d</div></td>
				<td><b>${esc(r.raised_by || "")}</b><div class="cd-muted">${esc(r.from)} · ${esc(r.source || "")}${r.route ? " · " + esc(r.route) : ""}</div></td>
				<td>${esc(r.type || "")}${r.item ? `<div class="cd-muted">${esc(r.item)}</div>` : ""}${r.desc ? `<div class="cd-desc">${esc(r.desc)}</div>` : ""}</td>
				<td>${r.severity ? `<span class="cd-tag ${r.severity === "Critical" ? "cd-red-tag" : ""}">${esc(r.severity)}</span>` : ""}</td>
				<td>${esc(r.department || "")}<div class="cd-muted">${esc(r.assigned || __("Unassigned"))}</div></td>
				<td>${r.due ? frappe.datetime.str_to_user(r.due) : ""}${r.overdue ? `<div class="cd-red">${__("Overdue")}</div>` : ""}</td>
				<td><span class="indicator-pill ${CD.status_color[r.status] || "gray"}">${__(r.status)}</span></td>
			</tr>`).join("");
		this.$body.find(".cd-table-wrap").html(rows.length
			? `<table class="cd-table"><thead><tr><th>${__("ID")}</th><th>${__("Raised By")}</th><th>${__("Issue")}</th><th>${__("Severity")}</th>
				<th>${__("Department / Owner")}</th><th>${__("Due")}</th><th>${__("Status")}</th></tr></thead><tbody>${html}</tbody></table>
				${rows.length > LIMIT ? `<div class="cd-muted cd-more">${__("Showing first {0} — use search or filters", [LIMIT])}</div>` : ""}`
			: `<div class="cd-empty">${__("Nothing here")}</div>`);
	}

	add_styles() {
		if (document.getElementById("cd-styles")) return;
		$(`<style id="cd-styles">
		.cd { padding:15px 0 30px; }
		.cd-kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(140px,1fr)); gap:10px; margin-bottom:18px; }
		.cd-kpi { position:relative; background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-md);
			box-shadow:var(--card-shadow); padding:12px 12px 10px 15px; cursor:pointer; overflow:hidden; transition:border-color .15s, box-shadow .15s; }
		.cd-kpi::before { content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--cd); }
		.cd-kpi:hover { border-color:var(--gray-400); }
		.cd-kpi.active { border-color:var(--cd); box-shadow:0 0 0 1px var(--cd); }
		.cd-static { cursor:default; }
		.cd-kpi-title { display:flex; align-items:center; gap:6px; font-size:11px; font-weight:500; color:var(--text-muted); text-transform:uppercase; letter-spacing:.3px; }
		.cd-dot { width:7px; height:7px; border-radius:50%; background:var(--cd); flex-shrink:0; }
		.cd-kpi-num { font-size:24px; font-weight:600; color:var(--text-color); line-height:1.2; margin-top:6px; font-variant-numeric:tabular-nums; }
		.cd-kpi-num small { font-size:12px; color:var(--text-muted); font-weight:400; }
		.cd-kpi-hint { font-size:11px; color:var(--text-muted); margin-top:2px; }
		.cd-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px; margin-bottom:18px; }
		.cd-span2 { grid-column:1 / -1; }
		@media (max-width:900px) { .cd-grid { grid-template-columns:1fr; } }
		.cd-panel { background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-md); box-shadow:var(--card-shadow); padding:12px 14px; min-width:0; }
		.cd-head { font-size:13px; font-weight:600; color:var(--text-color); margin-bottom:6px; }
		.cd-sub { font-weight:400; color:var(--text-muted); font-size:12px; }
		.cd-list-head { display:flex; align-items:center; gap:8px; padding-bottom:8px; border-bottom:1px solid var(--border-color); }
		.cd-search { margin-left:auto; max-width:240px; }
		.cd-count { font-size:11px; color:var(--text-muted); background:var(--control-bg); border-radius:999px; padding:1px 8px; font-weight:500; }
		.cd-empty { color:var(--text-muted); font-size:12px; padding:36px 0; text-align:center; }
		.cd-table-wrap { overflow-x:auto; }
		.cd-table { width:100%; border-collapse:collapse; font-size:12px; }
		.cd-table th { text-align:left; color:var(--text-muted); font-weight:500; font-size:11px; text-transform:uppercase; letter-spacing:.3px; padding:8px 10px; border-bottom:1px solid var(--border-color); white-space:nowrap; }
		.cd-table td { padding:8px 10px; border-bottom:1px solid var(--border-color); vertical-align:top; color:var(--text-color); }
		.cd-table tbody tr { cursor:pointer; }
		.cd-table tbody tr:hover td { background:var(--subtle-fg, var(--control-bg)); }
		.cd-table tr.cd-overdue td:first-child { box-shadow:inset 3px 0 0 var(--red-500); }
		.cd-id { font-weight:600; white-space:nowrap; }
		.cd-muted { color:var(--text-muted); font-size:11px; margin-top:2px; }
		.cd-desc { color:var(--text-muted); font-size:11px; margin-top:3px; max-width:340px; white-space:normal; }
		.cd-red { color:var(--red-500); font-size:11px; font-weight:600; }
		.cd-tag { display:inline-block; font-size:10px; padding:1px 7px; border-radius:999px; background:var(--control-bg); color:var(--text-muted); white-space:nowrap; }
		.cd-red-tag { background:var(--red-100, var(--control-bg)); color:var(--red-600, var(--red-500)); }
		.cd-more { padding:8px 10px; }
		.cd-foot { font-size:11px; color:var(--text-muted); margin-top:8px; text-align:right; }
		</style>`).appendTo("head");
	}
}
