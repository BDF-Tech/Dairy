frappe.ui.form.on("Vehicle Movement Log", {

    refresh(frm) {

        const transit_warehouse =
            "Goods and Transit - BDF";

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

                row.total_crate_in = 0;

                row.balance_crate =
                    inv.total_crates;

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

        frm.add_custom_button("Get Invoices", () => {

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

            new frappe.ui.form.MultiSelectDialog({

                doctype: "Sales Invoice",

                target: frm,

                setters: {

                    customer_name: null,

                    route: frm.doc.route,

                    delivery_shift: null
                },

                add_filters_group: 1,

                date_field: "posting_date",

                columns: [

                    "name",

                    "customer_name",

                    "route",

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
                                    frm.doc.date_and_time.split(" ")[0],

                                t_warehouse:
                                    transit_warehouse
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
                                    frm.doc.date_and_time.split(" ")[0],

                                t_warehouse:
                                    transit_warehouse
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

    }

});
