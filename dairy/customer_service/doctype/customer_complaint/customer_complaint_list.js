// Customer Complaint list = daily work dashboard: counter strip on top, click a counter to filter the list.
const CC_COUNTERS = [
	// key, label, colour, filters (fn so "today" / user are evaluated on click)
	["all_count", __("Show All"), "var(--gray-500)", () => []],
	["today", __("Created Today"), "var(--blue-500)", () => [["date_of_complaint", "=", frappe.datetime.get_today()]]],
	["open", __("Open"), "var(--orange-500)", () => [["status", "=", "Open"]]],
	["in_process", __("In Process"), "var(--blue-600)", () => [["status", "=", "Assigned"]]],
	["approval", __("Pending Approval"), "var(--purple-500)", () => [["status", "in", ["Pending Approval", "Accounts Approval"]]]],
	["overdue", __("Overdue"), "var(--red-500)", () => [
		["status", "in", ["Open", "Assigned"]], ["due_date", "is", "set"], ["due_date", "<", frappe.datetime.get_today()]]],
	["mine", __("Assigned to Me"), "var(--green-600)", () => [["assigned_user", "=", frappe.session.user], ["status", "in", ["Open", "Assigned"]]]],
	["my_approval", __("Awaiting My Approval"), "var(--purple-600)", (d) => [["status", "in", d.approval_states]]],
];
const CC_STATUS_COLOR = {
	Open: "orange", Assigned: "blue", "Pending Approval": "purple", "Accounts Approval": "purple",
	Resolved: "green", Closed: "gray", Rejected: "darkgrey",
};

frappe.listview_settings["Customer Complaint"] = {
	add_fields: ["status", "due_date", "confidential", "complaint_from"],
	get_indicator(doc) {
		const open = doc.status === "Open" || doc.status === "Assigned";
		if (open && doc.due_date && doc.due_date < frappe.datetime.get_today()) return [__("Overdue"), "red", "status,in,Open|Assigned"];
		return [__(doc.status), CC_STATUS_COLOR[doc.status] || "gray", "status,=," + doc.status];
	},
	onload(listview) {
		cc_add_styles();
		listview.cc_strip = $('<div class="cc-strip"></div>').insertBefore(listview.$frappe_list);
		listview.cc_strip.on("click", ".cc-counter", (e) => cc_apply(listview, $(e.currentTarget).data("key")));
		// counters don't depend on the list's filters, so only a real change to a complaint makes them stale.
		// own event: Frappe's list calls realtime.off("list_update"), which would drop a listener there.
		// remove only OUR previous handler (the dashboard page listens to the same event)
		if (window.cc_stale_handler) frappe.realtime.off("complaint_counters_stale", window.cc_stale_handler);
		window.cc_stale_handler = () => {
			listview.cc_dirty = true;
			if (frappe.get_route_str() === "List/Customer Complaint/List") cc_load(listview);
		};
		frappe.realtime.on("complaint_counters_stale", window.cc_stale_handler);
		// a change that arrived while the tab was hidden is picked up when the user comes back
		$(document).off("visibilitychange.cc").on("visibilitychange.cc", () => {
			if (!document.hidden && listview.cc_dirty) cc_load(listview);
		});
		cc_load(listview, true);
	},
	refresh(listview) {
		// runs after every list refresh (filters, sort, paging, realtime). Hit the server only when needed.
		cc_load(listview);
	},
};

const CC_MIN_GAP = 30 * 1000; // at most one counter query per 30 s per open list, unless something changed

function cc_load(listview, force) {
	if (!listview.cc_strip || document.hidden) return;
	const fresh = listview.cc_loaded_at && Date.now() - listview.cc_loaded_at < CC_MIN_GAP;
	if (!force && !listview.cc_dirty && fresh) return;
	if (listview.cc_loading) return;
	listview.cc_loading = true;
	listview.cc_dirty = false;
	frappe.xcall("dairy.customer_service.doctype.customer_complaint.customer_complaint.get_list_counters").then((d) => {
		listview.cc_loading = false;
		listview.cc_loaded_at = Date.now();
		listview.cc_data = d;
		cc_render(listview);
	}, () => (listview.cc_loading = false));
}

function cc_render(listview) {
	const d = listview.cc_data;
	if (!d) return;
	{
		const html = CC_COUNTERS.filter(([key]) => key !== "my_approval" || d.approval_states.length)
			.map(([key, label, color]) => `
				<div class="cc-counter ${listview.cc_active === key ? "active" : ""}" data-key="${key}" style="--cc:${color}">
					<div class="cc-label">${label}</div><div class="cc-num">${key === "all_count" ? "&#8634;" : d[key]}</div>
				</div>`).join("");
		listview.cc_strip.html(html);
	}
}

function cc_apply(listview, key) {
	const def = CC_COUNTERS.find((c) => c[0] === key);
	if (!def) return;
	listview.cc_active = key === "all_count" ? null : key;
	cc_render(listview); // highlight immediately, no server call
	const filters = def[3](listview.cc_data || {}).map((f) => ["Customer Complaint", ...f]);
	listview.filter_area.clear(false).then(() => (filters.length ? listview.filter_area.add(filters) : listview.refresh()));
}

function cc_add_styles() {
	if (document.getElementById("cc-styles")) return;
	$(`<style id="cc-styles">
	.cc-strip { display:grid; grid-template-columns:repeat(auto-fit,minmax(120px,1fr)); gap:8px; padding:12px 15px 4px; }
	.cc-counter { position:relative; background:var(--card-bg); border:1px solid var(--border-color); border-radius:var(--border-radius-md);
		padding:8px 10px 8px 13px; cursor:pointer; overflow:hidden; transition:border-color .15s, box-shadow .15s; }
	.cc-counter::before { content:""; position:absolute; left:0; top:0; bottom:0; width:3px; background:var(--cc); }
	.cc-counter:hover { border-color:var(--gray-400); }
	.cc-counter.active { border-color:var(--cc); box-shadow:0 0 0 1px var(--cc); }
	.cc-label { font-size:11px; color:var(--text-muted); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
	.cc-num { font-size:20px; font-weight:600; color:var(--text-color); line-height:1.3; font-variant-numeric:tabular-nums; }
	</style>`).appendTo("head");
}
