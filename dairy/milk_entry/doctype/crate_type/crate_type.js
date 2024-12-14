// Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Crate Type', {
	 refresh: function(frm) {
	 if(! frm.doc.__islocal){
             frm.add_custom_button(__('Crate Log'),function() {
             let d = new frappe.ui.Dialog({
                    title: 'Enter details',
                    fields: [
                        {
                            label: 'Crate Type',
                            fieldname: 'crate_type',
                            fieldtype: 'Link',
                            options: 'Crate Type',
                            default: frm.doc.name,
                            reqd: 1
                        },
                        {
                            label: 'Crate Issue',
                            fieldname: 'crate_issue',
                            fieldtype: 'Int',
                            reqd: 1
                        },
                        {
                            label: 'Crate Return',
                            fieldname: 'crate_return',
                            fieldtype: 'Int',
                            reqd: 1
                        },
                        {
                            label: 'Transporter',
                            fieldname: 'transporter',
                            fieldtype: 'Link',
                            options: "Supplier",
                            reqd: 1
                        },
                        {
                            label: 'Route',
                            fieldname: 'route',
                            fieldtype: 'Link',
                            options: "Route Master",
                            reqd: 1
                        },
                        {
                            label: 'Warehouse',
                            fieldname: 'warehouse',
                            fieldtype: 'Link',
                            options: "Warehouse",
                            reqd: 1
                        },
                        {
                            label: 'Company',
                            fieldname: 'company',
                            fieldtype: 'Link',
                            options: "Company",
                            default: frappe.defaults.get_user_default("Company"),
                            reqd: 1
                        },


                    ],
                    primary_action_label: 'Submit',
                    primary_action(values) {
                        console.log(values);
                         frm.call("add_crate_log", {
                            crate_type: values.crate_type,
                            crate_issue: values.crate_issue,
                            crate_return: values.crate_return,
                            transporter: values.transporter,
                            route:values.route,
                            warehouse:values.warehouse,
                            company:values.company
                        }, () => {
//                            reset_sla.enable_primary_action();
//                            frm.refresh();
                            frappe.msgprint(__("Crate was added."));
                        });
                        d.hide();
                    }
                });
                d.show();
            }, __("Create"));
            }

	 }
});
