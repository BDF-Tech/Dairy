frappe.ui.form.on("Vehicle Movement Log", {

    refresh(frm) {

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

                inv.items.forEach(item => {

                    let item_row =
                        frm.add_child(
                            "crate_item_details"
                        );

                    item_row.sales_invoice =
                        inv.name;

                    item_row.item_code =
                        item.item_code;

                    item_row.item_name =
                        item.item_name;

                    item_row.qty =
                        item.qty;

                    item_row.uom =
                        item.uom;

                    item_row.crates =
                        item.crates;

                });

            });

        };

        const add_stock_entry_rows = function(stock_entries) {

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

                se.items.forEach(item => {

                    let item_row =
                        frm.add_child(
                            "crate_item_details"
                        );

                    item_row.stock_entry =
                        se.name;

                    item_row.item_code =
                        item.item_code;

                    item_row.item_name =
                        item.item_name;

                    item_row.qty =
                        item.qty;

                    item_row.uom =
                        item.uom;

                    item_row.crates =
                        item.crates;

                });

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

                        "stock_entry_type"
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
