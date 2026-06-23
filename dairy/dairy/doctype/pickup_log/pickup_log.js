frappe.ui.form.on("Pickup Log", {

    refresh(frm) {

        if (frm.doc.docstatus !== 0) return;

        frm.add_custom_button(__("Get Invoices"), () => {

            if (!frm.doc.warehouse) {
                frappe.msgprint(__("Please select Warehouse first."));
                return;
            }

            if (!frm.doc.date) {
                frappe.msgprint(__("Please select Date first."));
                return;
            }

            new frappe.ui.form.MultiSelectDialog({

                doctype: "Sales Invoice",

                target: frm,

                setters: {
                    customer_name: null
                },

                add_filters_group: 1,

                date_field: "posting_date",

                columns: ["name", "customer_name", "posting_date"],

                get_query() {
                    return {
                        filters: {
                            docstatus: 1,
                            is_return: 0,
                            posting_date: frm.doc.date,
                            set_warehouse: frm.doc.warehouse,
                            custom_pickup_log: ""
                        }
                    };
                },

                action(selections) {

                    // Clear existing invoice rows, keep manual ones
                    frm.doc.crate_summary = [];
                    frm.refresh_field("crate_summary");

                    frappe.call({

                        method: "dairy.dairy.doctype.vehicle_movement_log.vehicle_movement_log.get_invoice_details",

                        args: {
                            invoices: selections,
                            posting_date: frm.doc.date
                        },

                        freeze: true,
                        freeze_message: __("Fetching Invoices..."),

                        callback(r) {

                            const invoices = (r.message || {}).invoices || [];

                            invoices.forEach(inv => {

                                const row = frm.add_child("crate_summary");
                                row.sales_invoice  = inv.name;
                                row.total_crate_out = inv.total_crates;
                                row.total_crate_in  = 0;
                                row.balance_crate   = inv.total_crates;

                            });

                            const total = (frm.doc.crate_summary || []).reduce(
                                (sum, r) => sum + (r.total_crate_out || 0), 0
                            );

                            frm.set_value("total_invoice_crates", total);
                            frm.refresh_field("crate_summary");

                        }

                    });

                    cur_dialog.hide();

                }

            });

        });

    }

});
