frappe.ui.form.on('Crate Delivery', {

    // =========================================================
    // REFRESH
    // =========================================================

    refresh: function(frm) {

        _render_location_map(frm);

        // Permanently hide the "+" (New) button on the Customer Crate Ledger
        // connection — ledger rows are only ever created by the system.
        // A CSS rule is used because the form dashboard re-shows the button in
        // after_refresh() (based on can_create), which would override a .hide().
        if (!document.getElementById('hide-ccl-new-btn')) {
            $(`<style id="hide-ccl-new-btn">
                .btn-new[data-doctype="Customer Crate Ledger"] { display: none !important; }
            </style>`).appendTo('head');
        }

        // Only show invoices linked to this VML that have no active Crate Delivery
        frm.set_query('sales_invoice', function() {
            return {
                query: 'dairy.dairy.doctype.crate_delivery.crate_delivery.get_available_invoices_for_cd',
                filters: { vml: frm.doc.vehicle_movement_log || '' }
            };
        });

        // Only show stock entries linked to this VML that have no active Crate Delivery
        frm.set_query('stock_entry', function() {
            return {
                query: 'dairy.dairy.doctype.crate_delivery.crate_delivery.get_available_stock_entries_for_cd',
                filters: { vml: frm.doc.vehicle_movement_log || '' }
            };
        });

        // Recovery: confirmed delivery whose ledger is missing → offer regenerate
        if (frm.doc.docstatus === 1 && frm.doc.customer_confirmed) {
            frappe.db.count('Customer Crate Ledger', {
                filters: { crate_delivery: frm.doc.name, entry_type: 'OUT' }
            }).then(function(count) {
                if (count > 0) return;   // ledger already present
                frm.add_custom_button(__('Generate Crate Ledger'), function() {
                    frappe.call({
                        method: 'dairy.dairy.doctype.crate_delivery.crate_delivery.regenerate_delivery_ledger',
                        args: { crate_delivery_name: frm.doc.name },
                        freeze: true,
                        callback: function(r) {
                            if (r.message && r.message.created) {
                                frappe.show_alert({ message: __('Crate ledger generated'), indicator: 'green' });
                                frm.reload_doc();
                            }
                        }
                    });
                }).addClass('btn-warning');
            });
        }

        // OTP flow — only on submitted, unconfirmed docs
        if (frm.doc.docstatus === 1 && !frm.doc.customer_confirmed) {

            // "Send OTP" button — shows channel picker before sending
            frm.add_custom_button(__('Send OTP'), function() {

                let d = new frappe.ui.Dialog({
                    title: __('Send OTP'),
                    fields: [
                        {
                            fieldname: 'channel',
                            fieldtype: 'Select',
                            label: __('Send Via'),
                            options: 'SMS\nWhatsApp',
                            default: 'SMS',
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Send'),
                    primary_action: function(values) {
                        d.hide();

                        const method = values.channel === 'WhatsApp'
                            ? 'dairy.dairy.doctype.crate_delivery.crate_delivery.send_delivery_otp'
                            : 'dairy.dairy.doctype.crate_delivery.crate_delivery.send_delivery_sms';

                        frappe.show_alert({ message: __('Sending OTP via {0}…', [values.channel]), indicator: 'blue' });

                        frappe.call({
                            method: method,
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
                    }
                });

                d.show();

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

            // "Bypass OTP" button — only if enabled in Crate Settings
            frappe.db.get_single_value('Crate Settings', 'allow_otp_bypass').then(function(allow) {
                if (!allow) return;

                frm.add_custom_button(__('Bypass OTP'), function() {

                    frappe.prompt(
                        {
                            label: __('Reason for bypassing OTP'),
                            fieldname: 'reason',
                            fieldtype: 'Small Text',
                            reqd: 1
                        },
                        function(values) {
                            frappe.confirm(
                                __('Confirm this delivery WITHOUT OTP verification?'),
                                function() {
                                    frappe.call({
                                        method: 'dairy.dairy.doctype.crate_delivery.crate_delivery.bypass_delivery_otp',
                                        args: {
                                            crate_delivery_name: frm.doc.name,
                                            reason: values.reason
                                        },
                                        callback: function(r) {
                                            if (r.message && r.message.confirmed) {
                                                frappe.show_alert({ message: __('Delivery confirmed (OTP bypassed)'), indicator: 'orange' });
                                                frm.reload_doc();
                                            }
                                        }
                                    });
                                }
                            );
                        },
                        __('Bypass OTP'),
                        __('Continue')
                    );

                }).removeClass('btn-default').addClass('btn-danger');
            });
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
                query: 'dairy.dairy.doctype.crate_delivery.crate_delivery.get_available_invoices_for_cd',
                filters: { vml: frm.doc.vehicle_movement_log || '' }
            };
        });

        frm.set_query('stock_entry', function() {
            return {
                query: 'dairy.dairy.doctype.crate_delivery.crate_delivery.get_available_stock_entries_for_cd',
                filters: { vml: frm.doc.vehicle_movement_log || '' }
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
    // Stock Entry → fetch crate qty (like Sales Invoice)
    // =========================================================

    stock_entry: function(frm) {

        if (!frm.doc.stock_entry) {
            frm.set_value('invoice_crate_qty', 0);
            return;
        }

        frappe.call({
            method: 'dairy.dairy.doctype.crate_delivery.crate_delivery.get_stock_entry_crate_qty',
            args: { stock_entry: frm.doc.stock_entry },
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

function _render_location_map(frm) {
    const wrapper = frm.fields_dict['location_map_html'];
    if (!wrapper) return;

    const lat = frm.doc.delivery_latitude;
    const lng = frm.doc.delivery_longitude;

    if (!lat || !lng) {
        wrapper.$wrapper.html(
            '<div style="color:#aaa;font-size:12px;padding:8px 0;">No location captured.</div>'
        );
        return;
    }

    const mapsUrl = `https://www.google.com/maps?q=${lat},${lng}`;
    wrapper.$wrapper.html(`
        <div style="padding:8px 0;">
            <a href="${mapsUrl}" target="_blank"
               style="display:inline-flex;align-items:center;gap:8px;
                      background:#2d6a4f;color:#fff;padding:8px 16px;
                      border-radius:8px;text-decoration:none;font-weight:600;font-size:13px;">
                📍 Open in Google Maps
            </a>
            <div style="margin-top:8px;font-size:12px;color:#888;">
                ${lat}, ${lng}
            </div>
            <iframe
                width="100%" height="220" frameborder="0" style="border:0;border-radius:8px;margin-top:10px;"
                src="https://maps.google.com/maps?q=${lat},${lng}&z=16&output=embed"
                allowfullscreen>
            </iframe>
        </div>
    `);
}
