// Copyright (c) 2026, BDF and contributors
// Status moves through the Workflow "Actions" menu. This script only adds helpers.

// Issue Type options per group (same lists as ISSUE_TYPES in customer_complaint.py, which re-checks on save)
const CC_ISSUE_TYPES = {
	Farmer: ["Payment Pending", "Wrong Fat / SNF", "Wrong Quantity", "Collection Timing", "Milk Rate", "Bonus / Incentive", "Other"],
	Vendor: ["Payment Delay", "Purchase Order Issue", "Quality", "Returns", "Vehicle / Transport", "Other"],
	Other: ["General", "Quality", "Service", "Other"],
};

// Resolution Type options per group (same lists as RESOLUTION_TYPES in customer_complaint.py)
const CC_RESOLUTION_TYPES = {
	"Customer": [
		"Replacement",
		"Credit Note",
		"Refund",
		"Explanation Given",
		"Process Fixed",
		"No Action Needed",
		"Other"
	],
	"Employee": [
		"Issue Fixed",
		"Policy / Process Changed",
		"Explanation Given",
		"Escalated to Management",
		"Referred to Department",
		"Disciplinary Action Taken",
		"No Action Needed",
		"Other"
	],
	"Farmer": [
		"Payment Released",
		"Fat / SNF Corrected",
		"Rate Corrected",
		"Explanation Given",
		"Process Fixed",
		"No Action Needed",
		"Other"
	],
	"Vendor": [
		"Payment Released",
		"PO Corrected",
		"Goods Returned / Replaced",
		"Explanation Given",
		"No Action Needed",
		"Other"
	],
	"Other": [
		"Explanation Given",
		"Process Fixed",
		"Replacement",
		"No Action Needed",
		"Other"
	]
};

// show only the chosen group's issue types, and call the name field just "Name" for the Other group
function cc_apply_group(frm) {
	const g = frm.doc.complaint_from;
	frm.set_df_property("issue_type", "options", ["", ...(CC_ISSUE_TYPES[g] || [])].join("\n"));
	frm.set_df_property("name_of_a_customer", "label", g === "Other" ? __("Name") : __("Name of a Customer"));
	frm.set_df_property("supplier", "label", g === "Farmer" ? __("Farmer") : __("Supplier"));
	const res = CC_RESOLUTION_TYPES[g || "Customer"] || [];
	// an old record may hold a value from the previous single list: keep it visible so it isn't blanked
	const cur = frm.doc.resolution_type;
	frm.set_df_property("resolution_type", "options", ["", ...res, ...(cur && !res.includes(cur) ? [cur] : [])].join("\n"));
}

frappe.ui.form.on("Customer Complaint", {
	setup(frm) {
		frm.set_query("category", () => ({
			filters: Object.assign({ enabled: 1 }, frm.doc.complaint_type ? { category_group: frm.doc.complaint_type } : {}),
		}));
		frm.set_query("assigned_user", () => ({ filters: { user_type: "System User", enabled: 1 } }));
		// farmers live under the milk-collection supplier groups; vendors are every other group
		frm.set_query("supplier", () => ({
			filters: { disabled: 0, supplier_group: [frm.doc.complaint_from === "Farmer" ? "like" : "not like", "%Milk Collection%"] },
		}));
	},
	onload(frm) {
		// staff whose permission is "own complaints only" are raising their own: start as an Employee complaint
		if (!frm.is_new() || frm.doc.employee || frm.doc.customer_id) return;
		frappe.xcall("dairy.customer_service.doctype.customer_complaint.customer_complaint.get_complaint_defaults")
			.then((d) => {
				if (!d || !d.only_own || !d.employee || !frm.is_new()) return;
				frm.set_value({ complaint_from: "Employee", employee: d.employee, source: "ERP" });
				frm.set_df_property("employee", "read_only", 1);
				frm.set_df_property("complaint_from", "read_only", 1);
			});
	},
	refresh(frm) {
		cc_apply_group(frm);
		if (frm.is_new()) return;
		const s = frm.doc.status;

		if ((s === "Open" || s === "Assigned") && frm.perm[0].write) {
			frm.add_custom_button(s === "Open" ? __("Assign") : __("Reassign"), () => assign(frm));
		}
		if (s === "Assigned" && frm.doc.entry_type === "Complaint" && !frm.doc.action_taken) {
			frm.set_intro(__("Fill <b>Action Taken</b> and <b>Resolution Type</b>, save, then use <b>Actions → Submit Resolution</b>."), "blue");
		}
		if (s === "Pending Approval" || s === "Accounts Approval") {
			frm.set_intro(__("Waiting for {0}. Approver: write remarks before <b>Send Back</b>.",
				[s === "Accounts Approval" ? __("Accounts approval") : __("Complaint Manager approval")]), "orange");
		}
		if (frm.doc.escalated && (s === "Open" || s === "Assigned")) {
			frm.dashboard.set_headline_alert(
				`<span class="indicator red">${__("Overdue — escalated to {0}", [frm.doc.escalated_to || __("no one set")])}</span>`
			);
		}
		if (frm.doc.confidential) {
			frm.dashboard.add_comment(__("Marked confidential. Handle with care."), "red", true);
		}
	},
	complaint_from(frm) {
		if (frm.doc.complaint_from === "Employee") {
			frm.set_value("source", "ERP");
		}
		// a value picked for another group would not fit this one
		const clear = { issue_type: null, resolution_type: null };
		if (!["Farmer", "Vendor"].includes(frm.doc.complaint_from)) Object.assign(clear, { supplier: null, purchase_order: null });
		if (frm.doc.complaint_from !== "Customer") Object.assign(clear, { customer_id: null, complaint_type: null, category: null });
		frm.set_value(clear);
		cc_apply_group(frm);
	},
	customer_id(frm) {
		if (!frm.doc.customer_id) return;
		frappe.db.get_value("Customer", frm.doc.customer_id, ["mobile_no", "primary_address"]).then(({ message: m }) => {
			if (!m) return;
			if (m.mobile_no && (!frm.doc.contact_no || frm.doc.contact_no === "+91")) frm.set_value("contact_no", m.mobile_no);
			if (m.primary_address && !frm.doc.address) frm.set_value("address", strip_html(m.primary_address).slice(0, 140));
		});
	},
	against_department(frm) {
		if (frm.doc.against_department && !frm.doc.department) frm.set_value("department", frm.doc.against_department);
	},
	complaint_type(frm) {
		if (frm.doc.category) {
			frappe.db.get_value("Complaint Category", frm.doc.category, "category_group").then(({ message: m }) => {
				if (m && m.category_group && m.category_group !== frm.doc.complaint_type) frm.set_value("category", null);
			});
		}
	},
});

function assign(frm) {
	frappe.prompt(
		[
			{ fieldname: "department", fieldtype: "Link", options: "Department", label: __("Department"), default: frm.doc.department },
			{ fieldname: "assigned_user", fieldtype: "Link", options: "User", label: __("Assign To"), reqd: 1, default: frm.doc.assigned_user,
			  get_query: () => ({ filters: { user_type: "System User", enabled: 1 } }) },
			{ fieldname: "due_date", fieldtype: "Date", label: __("Due Date"), default: frm.doc.due_date },
		],
		(v) => { frm.set_value(v); frm.save(); },
		__("Assign Complaint"), __("Assign")
	);
}
