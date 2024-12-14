
frappe.ui.form.on('Quotation', {
    // setup: function(frm) {
	// 	frm.add_fetch("route", "price_list", "selling_price_list");
	// },
	onload: function(frm){
        frm.set_query('route', function(doc) {
            return {
                filters: {
                    "company":doc.company,
                     "route_type":"Milk Marketing",
                    // "docstatus":1
                }
            };
        });
    },
	validate: function(frm) {


        // var otm = frappe.model.get_value("Dairy Settings","Dairy Settings","morning_locking_time");

        var today = new Date();
        var time = today.getHours() + ":" + today.getMinutes();
        
        frappe.model.get_value('Dairy Settings', {'name': 'Dairy Settings'}, 'morning_locking_time', function(d)
        {
            var otm = d.morning_locking_time;  
            var td = frappe.datetime.add_days(frappe.datetime.get_today(),1);
//            console.log("************",td);
            if (frm.doc.delivery_shift == 'Morning') 
            {            
                if(frm.doc.delivery_date == frappe.datetime.get_today())
                {
                frm.call({
				method:"dairy.milk_entry.custom_sales_order.order_role",
//				doc: frm.doc,
				args: {
				},
				callback: function(r) {
					if(r.message == 1){
                            frappe.validated = true;
                            frappe.throw(__('Order locking time is over'));
					    }
					   else{
					    frappe.validated = false;
                        frappe.throw(__('Order locking time is over'));
					   }
				    }
			    });

                    
                }
                if(frm.doc.delivery_date == td)
                {
                    if(time > otm)
                    {
                        frm.call({
				method:"dairy.milk_entry.custom_sales_order.order_role",
//				doc: frm.doc,
				args: {
				},
				callback: function(r) {
					if(r.message == 1){
                            frappe.validated = true;
                            frappe.throw(__('Order locking time is over'));
					    }
					   else{
					    frappe.validated = false;
                        frappe.throw(__('Order locking time is over'));
					   }
				    }
			    });
                    }
                }
            }
        });

        frappe.model.get_value('Dairy Settings', {'name': 'Dairy Settings'}, 'evening_locking_time', function(e)
        {
            var ote = e.evening_locking_time;
            if(frm.doc.delivery_shift == 'Evening')
            {
                if(frm.doc.delivery_date == frappe.datetime.get_today())
                {
                    if(time > ote)
                    {
                                frm.call({
                        method:"dairy.milk_entry.custom_sales_order.order_role",
        //				doc: frm.doc,
                        args: {
                        },
                        callback: function(r) {
                            if(r.message == 1){
                                    frappe.validated = true;
                                    frappe.throw(__('Order locking time is over'));
                                }
                               else{
                                frappe.validated = false;
                                frappe.throw(__('Order locking time is over'));
                               }
                            }
                        });
                    }
                }
            }
        });
    },

        before_submit:function(frm){
        // validate if restrict_multiple_orders_in_single_shift in dairy setting is check
	    frm.call({
				method:"dairy.milk_entry.custom_sales_order.validate_multiple_orders_in_quotation",
//				doc: frm.doc,
				args: {
					customer: frm.doc.customer_name,
					delivery_shift: frm.doc.delivery_shift,
					route: frm.doc.route,
					delivery_date: frm.doc.delivery_date
				},
				callback: function(r) {
					if(r.message == 1){
                        frappe.validated=false;
                         frappe.msgprint("Multiple Orders In Single Shift Not Allowed");
					}
				}
			});
    },
    
    delivery_shift: function(frm){
        if (frm.doc.delivery_shift == 'Morning')
        {
            var td = frappe.datetime.add_days(frappe.datetime.get_today(),1);
            frm.set_value("delivery_date",td);
        }
        else
        {
             frm.set_value("delivery_date",frappe.datetime.get_today());
        }
    },

    party_name:function(frm){
        if (frm.doc.quotation_to == "Customer")
        {
            return cur_frm.call({
                method:"dairy.milk_entry.custom_delivery_note.get_route_price_list",
                args: {
                        doc_name: cur_frm.doc.party_name
                      },
                callback: function(r)
                    {
                       if(r.message)
                       {
                        frm.set_value("route",r.message.route);
                        // frm.set_value("selling_price_list",r.message.p_list);
                       }
                    }
            });
        }
    },

    route:function(frm){
    //set territory
    	         return cur_frm.call({
            method:"dairy.milk_entry.custom_sales_order.set_territory",
            args: {

                  },
            callback: function(r)
                {
                   if(r.message)
                   {
                    console.log(r.message);
                    if(r.message == "Route"){
                        frm.set_value("territory",frm.doc.route_territory);
                    }
                   }
                }
        });
    }
 });   