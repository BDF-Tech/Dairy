// Copyright (c) 2023, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Bulk Payment', {
    get_records: function(frm) {
        frappe.call({
            method: "get_data",
            doc: frm.doc,
            callback:function(r){
                frm.refresh_field("items")
                frm.refresh()
            }

            })
       

    },
	before_submit: function(frm) {
        frappe.call({
            method: "get_lines",
            doc: frm.doc,
            callback:function(r){
    
            }

            })
       

    },
    refresh:function(frm){
        frm.set_query("party_type", function() {
			return {
				filters: {
					"name": ["in", ["Supplier", "Employee","Customer"]]
				}
			};
		});
		if(frm.doc.docstatus==1){
        frm.add_custom_button(__("Download Csv"),function(){
           
        var url = frappe.urllib.get_full_url(
            '/api/method/dairy.dairy.doctype.bulk_payment.bulk_payment.get_download?'
            + 'name='+encodeURIComponent(frm.doc.name))
    
        $.ajax({
            url: url,
            type: 'GET',
            success: function(result) {
                if(jQuery.isEmptyObject(result)){
                    frappe.msgprint(__('No Records for these settings.'));
                }
                else{
                    window.location = url;
                }
            }
        });
    })
	}
    }
    


});

