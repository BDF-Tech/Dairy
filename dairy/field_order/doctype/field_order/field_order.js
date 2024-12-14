// Copyright (c) 2019, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt





frappe.ui.form.on('Field Order', {
    
    customer : function(frm) {
        frm.set_query('secondary_customer', function(doc) {
            return {
                filters: {
                    "name":["not in", frm.doc.customer]
                }
            };
        });
    },
    
    
    validate: function(frm) {

        if(frm.doc.qty <= 0) {
            frappe.throw(__('Qty has to be more than 0.'));
        }
    },
    
    onload: function(frm){
        frm.set_query('product', function(doc) {
            return {
                filters: {'is_sales_item': 1}
            };
        });

    },
    
    before_submit: function(frm){

    
        if(frm.doc.periodicity===1 && frm.doc.disable===0){
            var next_date = frappe.datetime.add_days(frappe.datetime.get_today(),1);
            if (frm.doc.repeat_on == 'Weekly'){
                next_date = frappe.datetime.add_days(frappe.datetime.get_today(),7);
                }
            if (frm.doc.repeat_on == 'Monthly'){
                next_date = frappe.datetime.add_months(frappe.datetime.get_today(),1);
                }
            frm.set_value("next_order_date",next_date);
        }
        else
        {
            frm.set_value("next_order_date",frm.doc.transaction_date);
        }
    },
    

});


                     
    
