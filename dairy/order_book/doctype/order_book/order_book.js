// Copyright (c) 2019, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txts

frappe.ui.form.on('Order Book', {
    onload: function(frm){
        frm.set_query('delivery_warehouse', function(doc) {
            return {
                filters: {
                    "is_dcs":0,
                    "is_group":0,
                    "company":frappe.defaults.get_user_default("Company"),
                    "disabled":0
                }
            };
        });
    },


	refresh: function(frm, dt, dn) {
		frm.add_custom_button(__('Customer Credit Balance'), function() {
            frappe.set_route('query-report', 'Customer Credit Balance', {Customer:frm.doc.name});
        })
    
        
        

        if (frm.doc.docstatus==0) {
            frm.add_custom_button(__('Field Order'),
                function() {
                    erpnext.utils.map_current_doc({
                        method: "dairy.field_order.doctype.field_order.field_order.make_order_book",
                        source_doctype: "Field Order",
                        target: frm,
                        date_field: "transaction_date",
                        setters: [ 
                            {
                                label: "Customer",
                                fieldname: "customer",
                                fieldtype: "Link",
                                options: "Customer",
                                default: frm.doc.customer || undefined,
                            }
                        ],
                        get_query_filters: {
                            company: frm.doc.company,
                            docstatus: 1,
                            disable: 0,
                            
                        }
                    })
                }, __("Get items from"));
        }
        
    },
});

frappe.ui.form.on("Order Book Line", "rate", function(frm, cdt, cdn) {
    var d = locals[cdt][cdn];
    frappe.model.set_value(cdt, cdn, "amount", d.qty  * d.rate);
refresh_field("amount");
 



    // on_submit: function(frm) {
    //     frappe.model.open_mapped_doc({
    //         method: "dairy.order_book.doctype.order_book.order_book.create_sales_order",
    //         frm: cur_frm,
   
    //     })
    // }

});	