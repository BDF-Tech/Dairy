frappe.ui.form.on('Crate Delivery', {

    // =========================================================
    // REFRESH
    // =========================================================

    refresh: function(frm) {

        // Filter sales_invoice to only show invoices linked to this VML
        frm.set_query('sales_invoice', function() {
            return {
                filters: {
                    custom_vehicle_movement_log: frm.doc.vehicle_movement_log || ''
                }
            };
        });

        // Filter stock_entry to only show entries linked to this VML
        frm.set_query('stock_entry', function() {
            return {
                filters: {
                    van_collection_item: frm.doc.vehicle_movement_log || ''
                }
            };
        });

        // OTP flow — only on submitted, unconfirmed docs
        if (frm.doc.docstatus === 1 && !frm.doc.customer_confirmed) {

            // "Send OTP" button — generates and dispatches the OTP
            frm.add_custom_button(__('Send OTP'), function() {

                frappe.show_alert({ message: __('Sending OTP…'), indicator: 'blue' });

                frappe.call({
                    method: 'dairy.dairy.doctype.crate_delivery.crate_delivery.send_delivery_otp',
                    args: { crate_delivery_name: frm.doc.name },
                    callback: function(r) {
                        if (r.message) {
                            frappe.show_alert({
                                message: __('OTP sent via {0} to {1}', [r.message.channel, r.message.sent_to]),
                                indicator: 'green'
                            });
                            frm.reload_doc();
                        }
                    }
                });

            }).addClass('btn-warning');

            // "Verify OTP" button — only show if an OTP has been sent
            if (frm.doc.otp_sent_to) {

                frm.add_custom_button(__('Verify OTP'), function() {

                    frappe.prompt(
                        {
                            label: __('Enter OTP sent to {0}', [frm.doc.otp_sent_to]),
                            fieldname: 'otp',
                            fieldtype: 'Data',
                            reqd: 1
                        },
                        function(values) {
                            frappe.call({
                                method: 'dairy.dairy.doctype.crate_delivery.crate_delivery.verify_delivery_otp',
                                args: {
                                    crate_delivery_name: frm.doc.name,
                                    otp: values.otp
                                },
                                callback: function(r) {
                                    if (r.message && r.message.confirmed) {
                                        frappe.show_alert({ message: __('Customer confirmed!'), indicator: 'green' });
                                        frm.reload_doc();
                                    }
                                }
                            });
                        },
                        __('Verify Customer OTP'),
                        __('Verify')
                    );

                }).addClass('btn-primary');
            }
        }
    },

    // =========================================================
    // VML → auto-fill driver, vehicle, route
    // =========================================================

    vehicle_movement_log: function(frm) {

        // Clear invoice selection when VML changes so stale value doesn't remain
        frm.set_value('sales_invoice', '');
        frm.set_value('customer', '');
        frm.set_value('actual_customer', '');
        frm.set_value('invoice_crate_qty', 0);
        frm.set_value('customer_current_balance', 0);

        if (!frm.doc.vehicle_movement_log) return;

        // Re-apply filters so dropdowns immediately reflect the new VML
        frm.set_query('sales_invoice', function() {
            return {
                filters: {
                    custom_vehicle_movement_log: frm.doc.vehicle_movement_log
                }
            };
        });

        frm.set_query('stock_entry', function() {
            return {
                filters: {
                    van_collection_item: frm.doc.vehicle_movement_log
                }
            };
        });

        frappe.db.get_value(
            'Vehicle Movement Log',
            frm.doc.vehicle_movement_log,
            ['driver', 'vehicle', 'route'],
            function(d) {
                if (!d) return;
                frm.set_value('driver', d.driver);
                frm.set_value('vehicle', d.vehicle);
                frm.set_value('route', d.route);
            }
        );
    },

    // =========================================================
    // Sales Invoice → auto-fill customer + invoice_crate_qty
    // =========================================================

    sales_invoice: function(frm) {

        if (!frm.doc.sales_invoice) return;

        // Fetch customer from invoice
        frappe.db.get_value(
            'Sales Invoice',
            frm.doc.sales_invoice,
            'customer',
            function(d) {
                if (!d || !d.customer) return;
                frm.set_value('customer', d.customer);
                // Default actual_customer to invoice customer (can be changed for redirect)
                if (!frm.doc.actual_customer) {
                    frm.set_value('actual_customer', d.customer);
                }
            }
        );

        // Fetch invoice crate qty (server-side sum of Crate UOM items)
        frappe.call({
            method: 'dairy.dairy.doctype.crate_delivery.crate_delivery.get_invoice_crate_qty',
            args: { sales_invoice: frm.doc.sales_invoice },
            callback: function(r) {
                if (r.message !== undefined) {
                    frm.set_value('invoice_crate_qty', r.message);
                }
            }
        });
    },

    // =========================================================
    // Actual Customer → refresh live balance
    // =========================================================

    actual_customer: function(frm) {

        if (!frm.doc.actual_customer) return;

        frappe.db.get_value(
            'Customer',
            frm.doc.actual_customer,
            'custom_current_crate_balance',
            function(d) {
                frm.set_value(
                    'customer_current_balance',
                    (d && d.custom_current_crate_balance) || 0
                );
            }
        );
    },

    // =========================================================
    // Inline warnings on crates_delivered / crates_returned
    // =========================================================

    crates_delivered: function(frm) {

        if (
            !frm.doc.crates_delivered
            || !frm.doc.invoice_crate_qty
        ) return;

        if (frm.doc.crates_delivered < frm.doc.invoice_crate_qty) {

            frappe.msgprint({
                title: __('Warning'),
                indicator: 'orange',
                message: __(
                    `Crates Delivered (${frm.doc.crates_delivered}) is less than `
                    + `Invoice Crate Qty (${frm.doc.invoice_crate_qty}). `
                    + `You will not be able to submit.`
                )
            });
        }
    },

    crates_returned: function(frm) {

        if (!frm.doc.crates_returned) return;

        const delivered = frm.doc.crates_delivered || 0;
        const existing  = frm.doc.customer_current_balance || 0;
        const max_returnable = delivered + existing;

        if (max_returnable && frm.doc.crates_returned > max_returnable) {

            frappe.msgprint({
                title: __('Warning'),
                indicator: 'orange',
                message: __(
                    `You are returning <b>${frm.doc.crates_returned}</b> crates `
                    + `but only <b>${max_returnable}</b> crates are assigned to this customer.<br><br>`
                    + `Delivered this trip: <b>${delivered}</b><br>`
                    + `Customer existing balance: <b>${existing}</b>`
                )
            });
        }
    }

});
