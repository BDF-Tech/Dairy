frappe.ui.form.on("Work Order", {

    production_item:function(frm){
        frappe.db.get_value(
            "Item",
            frm.doc.production_item,
            "maintain_fat_snf_clr",
            (r) => {
                frm.set_df_property("source_warehouse","reqd",1)
                console.log(r.maintain_fat_snf_clr)
                if(r.maintain_fat_snf_clr==0){
                    frm.set_df_property("required_fat","hidden",1)
                    frm.set_df_property("required_snf_","hidden",1)
                    frm.set_df_property("required_fat_in_kg","hidden",1)
                    frm.set_df_property("required_snt_in_kg","hidden",1)
                }
    
            })
        frappe.call({
            method : "dairy.milk_entry.custom_work_order.get_required_fat_snf",
            args:{
                production_item: frm.doc.production_item,
                quantity : frm.doc.qty
            },
            callback:function(response){
                console.log(response)
                frm.set_value('required_fat',response.message[0]);
                frm.set_value('required_snf_',response.message[1]);
                frm.set_value('required_fat_in_kg',response.message[2]);
                frm.set_value('required_snt_in_kg',response.message[3]);
                frm.refresh_field('required_fat')
                frm.refresh_field('required_snf_')
                frm.refresh_field('required_fat_in_kg')
                frm.refresh_field('required_snt_in_kg')
                frm.refresh()
            }
        })
    },
    after_submit:function(frm){
        frm.reload()

    },
    qty:function(frm){
        frappe.call({
            method : "dairy.milk_entry.custom_work_order.get_required_fat_snf",
            args:{
                production_item: frm.doc.production_item,
                quantity : frm.doc.qty
            },
            callback:function(response){
                console.log(response)
                frm.clear_table("fg_item_scrap")
                frm.set_value('required_fat',response.message[0]);
                frm.set_value('required_snf_',response.message[1]);
                frm.set_value('required_fat_in_kg',response.message[2]);
                frm.set_value('required_snt_in_kg',response.message[3]);
                frm.refresh_field('required_fat')
                frm.refresh_field('required_snf_')
                frm.refresh_field('required_fat_in_kg')
                frm.refresh_field('required_snt_in_kg')
            }
        })
    },
    refresh:function(frm){
    frappe.db.get_value(
        "Item",
        frm.doc.production_item,
        "maintain_fat_snf_clr",
        (r) => {
            frm.set_df_property("source_warehouse","reqd",1)
            console.log(r.maintain_fat_snf_clr)
            if(r.maintain_fat_snf_clr==0){
                frm.set_df_property("required_fat","hidden",1)
                frm.set_df_property("required_snf_","hidden",1)
                frm.set_df_property("required_fat_in_kg","hidden",1)
                frm.set_df_property("required_snt_in_kg","hidden",1)
            }

        })
        if(frm.doc.production_item && frm.doc.qty && frm.doc.required_fat_in_kg==0 && frm.doc.required_snt_in_kg==0){
            frappe.call({
                method : "dairy.milk_entry.custom_work_order.get_required_fat_snf",
                args:{
                    production_item: frm.doc.production_item,
                    quantity : frm.doc.qty
                },
                callback:function(response){
                    console.log(response)
                    frm.set_value('required_fat',response.message[0]);
                    frm.set_value('required_snf_',response.message[1]);
                    frm.set_value('required_fat_in_kg',response.message[2]);
                    frm.set_value('required_snt_in_kg',response.message[3]);
                    frm.refresh_field('required_fat')
                    frm.refresh_field('required_snf_')
                    frm.refresh_field('required_fat_in_kg')
                    frm.refresh_field('required_snt_in_kg')
                }
            })
        }
    if (!frm.doc.__islocal && frm.doc.docstatus==0 && frm.doc.diff_fat_in_kg!=0){
        frm.add_custom_button(__("Adjust Fat"),function(){
           
            frappe.call({
                method : "dairy.milk_entry.custom_work_order.get_data_fat",
                args:{
                    name: frm.doc.name
                },
                callback:function(r){
                    if(r.message){
                        $.each(r.message, function(index, row)
                        {   if(row.threshhold==0){
                        var child_table = frm.fields_dict['required_items'].grid;
	
						// Create a new row object
						var new_row = child_table.add_new_row();
			
						frappe.model.set_value(new_row.doctype, new_row.name, 'item_code', row.item);
						frappe.model.set_value(new_row.doctype, new_row.name, 'required_qty', row.pickedqty);
						frappe.model.set_value(new_row.doctype, new_row.name, 'source warhouse', row.warehouse);
						frappe.model.set_value(new_row.doctype, new_row.name, 'fat_per', row.fat_per);
						frappe.model.set_value(new_row.doctype, new_row.name, 'fat_per_in_kg', row.picked_fat_in_kg);
						frm.refresh_fields("required_items");
                        var ctable = frm.fields_dict['fg_item_scrap'].grid;
	
                        var c_row = ctable.add_new_row();
			
						frappe.model.set_value(c_row.doctype, c_row.name, 'item', frm.doc.production_item);
						frappe.model.set_value(c_row.doctype, c_row.name, 'qty', row.pickedqty);
                        frm.refresh_fields("fg_item_scrap");
                        }else{
                            frm.clear_table("operations")
                            var child_table = frm.fields_dict['operations'].grid;
	
                            // Create a new row object
                            var new_row = child_table.add_new_row();
                
                            frappe.model.set_value(new_row.doctype, new_row.name, 'operation', row.operation);
                            frappe.model.set_value(new_row.doctype, new_row.name, 'bom', row.bom);
                            frappe.model.set_value(new_row.doctype, new_row.name, 'workstation', row.workstation);
                            frappe.model.set_value(new_row.doctype, new_row.name, 'workstation_type', row.workstation_type);
                            frappe.model.set_value(new_row.doctype, new_row.name, 'time_in_mins', row.time_in_mins);
                            frappe.model.set_value(new_row.doctype, new_row.name, 'completed_qty', row.completed_qty);
                            frm.refresh_fields("operations");
                        }
                        
                        })
                       
                        // frm.save()
                    }
                   
                }
            })
        })
    
    }
    if (!frm.doc.__islocal && frm.doc.docstatus==0 && frm.doc.diff_snf_in_kg!=0){
        frm.add_custom_button(__("Adjust Snf"),function(){
           
            frappe.call({
                method : "dairy.milk_entry.custom_work_order.get_data_snf",
                args:{
                    name: frm.doc.name
                },
                callback:function(r){
                    if(r.message){
                        $.each(r.message, function(index, row)
                        {   
                        var child_table = frm.fields_dict['required_items'].grid;
	
						// Create a new row object
						var new_row = child_table.add_new_row();
			
						frappe.model.set_value(new_row.doctype, new_row.name, 'item_code', row.item);
						frappe.model.set_value(new_row.doctype, new_row.name, 'required_qty', row.pickedqty);
						frappe.model.set_value(new_row.doctype, new_row.name, 'source warhouse', row.warehouse);
						frappe.model.set_value(new_row.doctype, new_row.name, 'fat_per', row.fat_per);
						frappe.model.set_value(new_row.doctype, new_row.name, 'fat_per_in_kg', row.picked_fat_in_kg);
						frm.refresh_fields("required_items");
                        var ctable = frm.fields_dict['fg_item_scrap'].grid;
	
                        var c_row = ctable.add_new_row();
			
						frappe.model.set_value(c_row.doctype, c_row.name, 'item', frm.doc.production_item);
						frappe.model.set_value(c_row.doctype, c_row.name, 'qty', row.pickedqty);
                        frm.refresh_fields("fg_item_scrap");
                        
                        })
                       
                        // frm.save()
                    }
                   
                }
            })
        })
    
    }
}


})

