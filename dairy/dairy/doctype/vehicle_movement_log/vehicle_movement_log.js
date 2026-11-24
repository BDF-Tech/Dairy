frappe.ui.form.on("Vehicle Movement Log", {

    refresh(frm) {

        // Only allow Active drivers to be selected
        frm.set_query("driver", function() {
            return { filters: { status: "Active" } };
        });

        const isVehicleReturned =
            frm.doc.workflow_state === "Vehicle Returned";

        frm.set_df_property(
            "security_loose_crate_entries",
            "read_only",
            !isVehicleReturned
        );

        frm.refresh_field("security_loose_crate_entries");

        // Control "+" button visibility on connection tiles based on workflow state
        const _control_plus_buttons = () => {
            const show_crate = frm.doc.workflow_state === "Submitted";

            $(frm.wrapper).find('button.btn-new[data-doctype="Sales Invoice"]').hide();
            $(frm.wrapper).find('button.btn-new[data-doctype="Stock Entry"]').hide();
            $(frm.wrapper).find('button.btn-new[data-doctype="Crate Delivery"]').toggle(show_crate);
        };

        frappe.after_ajax(_control_plus_buttons);
        setTimeout(_control_plus_buttons, 500);

        const add_invoice_rows = function(invoices) {

            // Summary stays per-invoice
            invoices.forEach(inv => {

                let row =
                    frm.add_child(
                        "crate_summary"
                    );

                row.sales_invoice =
                    inv.name;

                row.total_crate_out =
                    inv.total_crates;

                row.balance_crate =
                    inv.customer_balance;

            });

            // Item details CONSOLIDATED by item_code across all invoices
            let item_map = {};

            invoices.forEach(inv => {
                (inv.items || []).forEach(item => {
                    let key = item.item_code;
                    if (!item_map[key]) {
                        item_map[key] = {
                            sales_invoice: inv.name,   // representative source
                            item_code: item.item_code,
                            item_name: item.item_name,
                            uom: item.uom,
                            qty: 0,
                            crates: 0
                        };
                    }
                    item_map[key].qty += (item.qty || 0);
                    item_map[key].crates += (item.crates || 0);
                });
            });

            Object.values(item_map).forEach(agg => {
                let item_row =
                    frm.add_child("crate_item_details");
                item_row.sales_invoice = agg.sales_invoice;
                item_row.item_code = agg.item_code;
                item_row.item_name = agg.item_name;
                item_row.qty = agg.qty;
                item_row.uom = agg.uom;
                item_row.crates = agg.crates;
            });

        };

        const add_stock_entry_rows = function(stock_entries) {

            // Summary stays per-stock-entry
            stock_entries.forEach(se => {

                let row =
                    frm.add_child(
                        "crate_summary"
                    );

                row.stock_entry =
                    se.name;

                row.total_crate_out =
                    se.total_crates;

                row.total_crate_in = 0;

                row.balance_crate =
                    se.total_crates;

            });

            // Item details CONSOLIDATED by item_code across all stock entries
            let item_map = {};

            stock_entries.forEach(se => {
                (se.items || []).forEach(item => {
                    let key = item.item_code;
                    if (!item_map[key]) {
                        item_map[key] = {
                            stock_entry: se.name,   // representative source
                            item_code: item.item_code,
                            item_name: item.item_name,
                            uom: item.uom,
                            qty: 0,
                            crates: 0
                        };
                    }
                    item_map[key].qty += (item.qty || 0);
                    item_map[key].crates += (item.crates || 0);
                });
            });

            Object.values(item_map).forEach(agg => {
                let item_row =
                    frm.add_child("crate_item_details");
                item_row.stock_entry = agg.stock_entry;
                item_row.item_code = agg.item_code;
                item_row.item_name = agg.item_name;
                item_row.qty = agg.qty;
                item_row.uom = agg.uom;
                item_row.crates = agg.crates;
            });

        };

        const update_total_crates = function() {

            let total_crates = 0;

            (frm.doc.crate_summary || []).forEach(row => {

                total_crates +=
                    row.total_crate_out || 0;

            });

            frm.set_value(
                "total_invoice_crates",
                total_crates
            );

            frm.refresh_field(
                "crate_summary"
            );

            frm.refresh_field(
                "crate_item_details"
            );

        };

        if (frm.doc.workflow_state === "Dispatch Loading") {

        frm.add_custom_button("Get Invoices", async () => {

            if (!frm.doc.route) {

                frappe.msgprint(
                    "Please select Route"
                );

                return;
            }

            if (!frm.doc.date_and_time) {

                frappe.msgprint(
                    "Please select Date"
                );

                return;
            }

            const crate_settings = await frappe.db.get_doc("Crate Settings", "Crate Settings");
            const dispatch_warehouses = (crate_settings.dispatch_warehouses || []).map(r => r.warehouse);

            if (!dispatch_warehouses.length) {

                frappe.msgprint({
                    title: "Setup Required",
                    indicator: "orange",
                    message: "Please add at least one <b>Dispatch</b> warehouse in Crate Settings before fetching invoices."
                });

                return;
            }

            new frappe.ui.form.MultiSelectDialog({

                doctype: "Sales Invoice",

                target: frm,

                setters: {

                    customer_name: null,

                    delivery_shift: null
                },

                add_filters_group: 1,

                columns: [

                    "name",

                    "customer_name",

                    "delivery_shift"
                ],

                get_query() {

                    return {

                        filters: {

                            docstatus: 1,

                            is_return: 0,

                            route: frm.doc.route,

                            posting_date:
                                frm.doc.date_and_time.split(" ")[0],

                            set_warehouse: ["in", dispatch_warehouses],

                            custom_vehicle_movement_log: ""
                        }
                    };
                },

                action(selections) {

                    console.log(
                        "SELECTED INVOICES",
                        selections
                    );

                    frm.doc.crate_summary = (
                        frm.doc.crate_summary || []
                    ).filter(r => r.stock_entry);

                    frm.doc.crate_item_details = (
                        frm.doc.crate_item_details || []
                    ).filter(r => r.stock_entry);

                    frm.refresh_field("crate_summary");
                    frm.refresh_field("crate_item_details");

                    frappe.call({

                        method:
                            "dairy.dairy.doctype.vehicle_movement_log.vehicle_movement_log.get_invoice_details",

                        args: {

                            invoices: selections,

                            posting_date:
                                frm.doc.date_and_time.split(" ")[0]
                        },

                        freeze: true,

                        freeze_message:
                            "Fetching Invoices",

                        callback: function(r) {

                            let data =
                                r.message || {};

                            let invoices =
                                data.invoices || [];

                            add_invoice_rows(
                                invoices
                            );

                            update_total_crates();

                        },

                        error: function(err) {

                            console.error(
                                "SERVER ERROR",
                                err
                            );

                            frappe.msgprint({

                                title: "SERVER ERROR",

                                message:
                                    `<pre>${JSON.stringify(err, null, 2)}</pre>`,

                                indicator: "red"
                            });

                        }

                    });

                    cur_dialog.hide();

                }

            });

        });

        frm.add_custom_button("Get Stock Entries", () => {

            if (!frm.doc.date_and_time) {

                frappe.msgprint(
                    "Please select Date"
                );

                return;
            }

            let dialog =
                new frappe.ui.form.MultiSelectDialog({

                    doctype: "Stock Entry",

                    target: frm,

                    setters: {

                        stock_entry_type: null
                    },

                    add_filters_group: 1,

                    date_field: "posting_date",

                    columns: [

                        "name",

                        "posting_date",

                        "posting_time",

                        "to_warehouse"
                    ],

                    get_query() {

                        return {

                            query:
                                "dairy.dairy.doctype.vehicle_movement_log.vehicle_movement_log.get_stock_entry_query",

                            filters: {

                                posting_date:
                                    frm.doc.date_and_time.split(" ")[0]
                            }
                        };
                    },

                    action(selections) {

                        frm.doc.crate_summary = (
                            frm.doc.crate_summary || []
                        ).filter(r => r.sales_invoice);

                        frm.doc.crate_item_details = (
                            frm.doc.crate_item_details || []
                        ).filter(r => r.sales_invoice);

                        frm.refresh_field("crate_summary");
                        frm.refresh_field("crate_item_details");

                        frappe.call({

                            method:
                                "dairy.dairy.doctype.vehicle_movement_log.vehicle_movement_log.get_stock_entry_details",

                            args: {

                                stock_entries:
                                    selections,

                                posting_date:
                                    frm.doc.date_and_time.split(" ")[0]
                            },

                            freeze: true,

                            freeze_message:
                                "Fetching Stock Entries",

                            callback: function(r) {

                                add_stock_entry_rows(
                                    r.message || []
                                );

                                update_total_crates();

                            }

                        });

                        dialog.dialog.hide();

                    }

                });

        });

        } // end if Dispatch Loading

    },

    before_workflow_action: function(frm) {

        if (frm.selected_workflow_action !== "Final check") return;

        // Frappe freezes the DOM before firing this hook — unfreeze so dialog renders
        frappe.dom.unfreeze();

        const summary      = frm.doc.crate_summary || [];
        const invoice_rows = summary.filter(r => r.sales_invoice);
        const invoice_count = invoice_rows.length;
        const total_crates  = frm.doc.total_invoice_crates || 0;

        const loose_entries = frm.doc.loose_crate_detail || [];
        const loose_total   = loose_entries.reduce((s, r) => s + (r.crates_out || 0), 0);

        const inv_rows = invoice_rows.map(r =>
            `<tr>
                <td>${r.sales_invoice}</td>
                <td style="text-align:right">${r.total_crate_out || 0}</td>
            </tr>`
        ).join('') || '<tr><td colspan="2" style="color:#999">None</td></tr>';

        const loose_rows = loose_entries.map(r =>
            `<tr>
                <td>${r.crate_item || ''}</td>
                <td style="text-align:right">${r.crates_out || 0}</td>
            </tr>`
        ).join('') || '<tr><td colspan="2" style="color:#999">None</td></tr>';

        const driver  = frm.doc.driver || '—';
        const vehicle = frm.doc.vehicle || '—';

        const msg = `
            <p style="margin-bottom:14px">
                <b>Driver:</b> ${driver} &nbsp;&nbsp; <b>Vehicle:</b> ${vehicle}
            </p>
            <b>Invoices &mdash; ${invoice_count}</b>
            <table class="table table-bordered table-condensed" style="margin:8px 0 16px">
                <thead><tr><th>Invoice</th><th style="text-align:right">Crates</th></tr></thead>
                <tbody>${inv_rows}</tbody>
                <tfoot><tr>
                    <th>Total Crates Assigned to Driver</th>
                    <th style="text-align:right">${total_crates}</th>
                </tr></tfoot>
            </table>
            <b>Loose Crates &mdash; ${loose_total}</b>
            <table class="table table-bordered table-condensed" style="margin:8px 0 0">
                <thead><tr><th>Item</th><th style="text-align:right">Qty</th></tr></thead>
                <tbody>${loose_rows}</tbody>
            </table>
        `;

        return new Promise((resolve, reject) => {
            let d = new frappe.ui.Dialog({
                title: __('Final Check Summary'),
                fields: [{ fieldtype: 'HTML', options: msg }],
                primary_action_label: __('Confirm & Submit'),
                primary_action: function() {
                    d.hide();
                    frappe.dom.freeze();
                    resolve();
                },
                secondary_action_label: __('Back to Gate Check'),
                secondary_action: function() { d.hide(); reject(); },
            });
            d.show();
        });
    }

});


// =========================================================
// CHANGE DRIVER / CHANGE VEHICLE (mid-trip)
// =========================================================

frappe.ui.form.on("Vehicle Movement Log", {

    refresh(frm) {

        const state = frm.doc.workflow_state;
        const on_route = ["Submitted", "Vehicle Returned"].includes(state);
        const can_change = !frm.is_new() && frm.perm[0]?.write &&
            ["Route Planning", "Dispatch Loading", "Gate Check", "Submitted"].includes(state);

        // After the vehicle is out, driver/vehicle change only via the buttons
        frm.set_df_property("driver", "read_only", on_route ? 1 : 0);
        frm.set_df_property("vehicle", "read_only", on_route ? 1 : 0);

        if (!can_change) return;

        frm.add_custom_button(__("Change Driver"), () => vml_change_driver(frm), __("Crew"));
        frm.add_custom_button(__("Change Vehicle"), () => vml_change_vehicle(frm), __("Crew"));
    },
});

const VML_API = "dairy.dairy.doctype.vehicle_movement_log.vehicle_movement_log";

function vml_holding_html(holding) {
    if (!holding) {
        return `<p class="text-muted">${__("Vehicle has not gone out yet — no crates to transfer.")}</p>`;
    }
    const rows = [[__("Invoice / Stock Entry crates"), holding.invoice_crates]];
    Object.entries(holding.loose || {}).forEach(([ct, qty]) => rows.push([`${__("Loose")}: ${frappe.utils.escape_html(ct)}`, qty]));
    return `
        <p><b>${__("Crates moving to the new driver")}</b></p>
        <table class="table table-bordered table-sm">
            ${rows.map(([l, q]) => `<tr><td>${l}</td><td class="text-right"><b>${flt(q)}</b></td></tr>`).join("")}
        </table>`;
}

async function vml_change_driver(frm) {
    if (frm.is_dirty()) {
        frappe.msgprint(__("Please save the trip first."));
        return;
    }

    const { message: preview } = await frappe.call({
        method: `${VML_API}.get_crew_change_preview`,
        args: { vml: frm.doc.name },
    });

    const d = new frappe.ui.Dialog({
        title: __("Change Driver"),
        fields: [
            { fieldtype: "HTML", options: `<p>${__("Current driver")}: <b>${frappe.utils.escape_html(frm.doc.driver_name || frm.doc.driver || "-")}</b></p>` },
            {
                fieldname: "new_driver", fieldtype: "Link", options: "Driver", label: __("New Driver"), reqd: 1,
                get_query: () => ({ filters: { status: "Active", name: ["!=", frm.doc.driver || ""] } }),
            },
            { fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1,
              description: __("e.g. driver unwell / absent") },
            { fieldtype: "HTML", options: vml_holding_html(preview.holding) },
        ],
        primary_action_label: __("Change Driver"),
        primary_action: async (values) => {
            d.disable_primary_action();
            try {
                await frappe.call({
                    method: `${VML_API}.change_driver`,
                    args: { vml: frm.doc.name, new_driver: values.new_driver, reason: values.reason },
                    freeze: true,
                });
                d.hide();
                frappe.show_alert({ message: __("Driver changed"), indicator: "green" });
                frm.reload_doc();
            } finally {
                d.enable_primary_action();
            }
        },
    });
    d.show();
}

function vml_change_vehicle(frm) {
    if (frm.is_dirty()) {
        frappe.msgprint(__("Please save the trip first."));
        return;
    }

    const d = new frappe.ui.Dialog({
        title: __("Change Vehicle"),
        fields: [
            { fieldtype: "HTML", options: `<p>${__("Current vehicle")}: <b>${frappe.utils.escape_html(frm.doc.vehicle || "-")}</b></p>` },
            {
                fieldname: "new_vehicle", fieldtype: "Link", options: "Vehicle", label: __("New Vehicle"), reqd: 1,
                get_query: () => ({ filters: { name: ["!=", frm.doc.vehicle || ""] } }),
            },
            { fieldname: "reason", fieldtype: "Small Text", label: __("Reason"), reqd: 1,
              description: __("e.g. breakdown on route") },
            { fieldtype: "HTML", options: `<p class="text-muted">${__("Crates stay with the driver.")}</p>` },
        ],
        primary_action_label: __("Change Vehicle"),
        primary_action: async (values) => {
            d.disable_primary_action();
            try {
                await frappe.call({
                    method: `${VML_API}.change_vehicle`,
                    args: { vml: frm.doc.name, new_vehicle: values.new_vehicle, reason: values.reason },
                    freeze: true,
                });
                d.hide();
                frappe.show_alert({ message: __("Vehicle changed"), indicator: "green" });
                frm.reload_doc();
            } finally {
                d.enable_primary_action();
            }
        },
    });
    d.show();
}
