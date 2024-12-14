frappe.ui.form.on('BOM',{
    refresh:function(frm){
        frappe.db.get_value(
            "Item",
            frm.doc.item,
            "maintain_fat_snf_clr",
            (r) => {
                console.log(r.maintain_fat_snf_clr)
                if(r.maintain_fat_snf_clr==0){
                    frm.set_df_property("weight_details","hidden",1)
                  
                }
    
            })
    },
    item:function(frm){
        frappe.call({
            method : "dairy.dairy.custom_bom.get_required_fat_snf",
            args:{
                item_code: frm.doc.item,
                quantity : frm.doc.quantity
            },
            callback:function(response){
                console.log(response)
                frm.set_value('standard_fat',response.message[0]);
                frm.set_value('standard_snf',response.message[1]);
                frm.set_value('item_fat',response.message[2]);
                frm.set_value('item_snf',response.message[3]);
                frm.refresh_field('standard_fat')
                frm.refresh_field('standard_snf')
                frm.refresh_field('item_fat')
                frm.refresh_field('item_snf')
            }
        })
    }, 
    quantity:function(frm){
        frappe.call({
            method : "dairy.dairy.custom_bom.get_required_fat_snf",
            args:{
                item_code: frm.doc.item,
                quantity : frm.doc.quantity
            },
            callback:function(response){
                console.log(response)
                frm.set_value('standard_fat',response.message[0]);
                frm.set_value('standard_snf',response.message[1]);
                frm.set_value('item_fat',response.message[2]);
                frm.set_value('item_snf',response.message[3]);
                frm.refresh_field('standard_fat')
                frm.refresh_field('standard_snf')
                frm.refresh_field('item_fat')
                frm.refresh_field('item_snf')
            }
        })
    }
});

frappe.ui.form.on('BOM Item', { 
	qty:function(frm, cdt, cdn) {
        var child = locals[cdt][cdn];
        // console.log(child.qty)
        frappe.call({
            method : 'dairy.dairy.custom_bom.bom_item_child_table',
            args:{
                item_code : child.item_code,
                qty : child.qty,
            },
            callback:function(resp){
                child.weight  = resp.message[0]
                child.standard_fat = resp.message[1]
                child.bom_fat = resp.message[2]
                child.standard_snf = resp.message[3]
                child.bom_snf = resp.message[4]
                // frm.refresh_field('')
            }
        })
    },
    item_code:function(frm, cdt, cdn) {
        var child = locals[cdt][cdn];
        // console.log(child.qty)
        frappe.call({
            method : 'dairy.dairy.custom_bom.bom_item_child',
            args:{
                item_code : child.item_code,
                qty : child.qty,
            },
            callback:function(resp){
                child.weight  = resp.message[0]
                child.standard_fat = resp.message[1]
                child.bom_fat = resp.message[2]
                child.standard_snf = resp.message[3]
                child.bom_snf = resp.message[4]
                // frm.refresh_field('')
            }
        })
    }
});
