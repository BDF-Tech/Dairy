frappe.provide("erpnext.stock");

frappe.ui.form.on('Stock Entry', {
	refresh:function(frm){
		if(frm.doc.total_diff_fat_in_kg<0){
			frm.set_df_property("add_fat_button","hidden",0)
		}
		if(frm.doc.total_diff_fat_in_kg>0){
			frm.set_df_property("remove_fat_button","hidden",0)

		}
		if(frm.doc.total_diff_snf_in_kg<0){
			frm.set_df_property("add_snf_button","hidden",0)

		}
		if(frm.doc.total_diff_snf_in_kg>0){
			frm.set_df_property("remove_snf_button","hidden",0)

		}
		frappe.db.get_value(
			"Item",
			frm.doc.item,
			"maintain_fat_snf_clr",
			(r) => {
				// console.log(r.maintain_fat_snf_clr)
				if(r.maintain_fat_snf_clr==1){
					frm.set_df_property("fg_fat_snf_calculations","hidden",0)
					frm.set_df_property("rm_fat__snf_calculations","hidden",0)
					frm.set_df_property("difference_in_fat__snf","hidden",0)

				}

			})

		frm.add_custom_button(__("Milk Ledger"), function() {
			frappe.route_options = {
				voucher_no: frm.doc.name,
				from_date: frm.doc.posting_date,
				to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
				company: frm.doc.company
			};
			frappe.set_route("query-report", "Milk Ledger");
			}, __("View"));
	

	},
	
	setup:function(frm){
		if(frm.doc.__islocal && frm.doc.stock_entry_type && frm.doc.work_order){
		frappe.call({
			method:"dairy.milk_entry.custom_stock_entry.add_scrap_item",
			args:{
				"work_order":frm.doc.work_order,
				"stock_entry_type":frm.doc.stock_entry_type
			},
			callback:function(r){
				if (r.message){
					$.each(r.message, function(index, row){
					var child_table = frm.fields_dict['items'].grid;

                    // Create a new row object
                    var new_row = child_table.add_new_row();
            
                    // Set the values for the new row
                    frappe.model.set_value(new_row.doctype, new_row.name, 't_warehouse', frm.doc.fg_warehouse);
					frappe.model.set_value(new_row.doctype, new_row.name, 's_warehouse', "");
                    frappe.model.set_value(new_row.doctype, new_row.name, 'item_code', row.item);
                    frappe.model.set_value(new_row.doctype, new_row.name, 'qty', row.qty);
					frappe.model.set_value(new_row.doctype, new_row.name, 'is_scrap_item', 1);
					child_table.refresh()

                    frm.refresh_fields("items");
					})

				}
			}
	})
}
	},
// 	add_snf_button:function(frm){
// 		frappe.call({
// 			method:"dairy.milk_entry.custom_stock_entry.get_add_snf",
// 			args:{
// 				"name":frm.doc.name
// 			},
// 			callback:function(r){
// 				if (r.message){
// 					console.log("$$$$$$$$$$$",r.message)
// 						var child_table = frm.fields_dict['items'].grid;
	
// 						// Create a new row object
// 						var new_row = child_table.add_new_row();
				
// 						// Set the values for the new row
// 						frappe.model.set_value(new_row.doctype, new_row.name, 's_warehouse', frm.doc.from_warehouse);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'item_code', r.message.item_code);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'qty', r.message.qty);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'snf_per', r.message.snf);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'fat_per', r.message.fat);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'fat', r.message.total_fat_in_kg);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'fat',  r.message.total_fat_in_kg);
// 						frm.refresh_fields("items");
// 						frappe.model.set_value(new_row.doctype, new_row.name, 't_warehouse', "");
// 						frm.refresh_fields("items");
// 					}
		
// 	}
// 	})
// 	},
// 	remove_fat_button:function(frm){
// 		frappe.call({
// 			method:"dairy.milk_entry.custom_stock_entry.get_remove_fat",
// 			args:{
// 				"name":frm.doc.name
// 			},
// 			callback:function(r){
// 				if (r.message){
// 					console.log("$$$$$$$$$$$",r.message)
// 						var child_table = frm.fields_dict['items'].grid;
	
// 						// Create a new row object
// 						var new_row = child_table.add_new_row();
				
// 						// Set the values for the new row
// 						frappe.model.set_value(new_row.doctype, new_row.name, 's_warehouse', frm.doc.from_warehouse);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'item_code', r.message.item_code);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'qty', r.message.qty);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'snf_per', r.message.snf);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'fat_per', r.message.fat);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'fat', r.message.total_fat_in_kg);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'fat',  r.message.total_fat_in_kg);
// 						frm.refresh_fields("items");
// 						frappe.model.set_value(new_row.doctype, new_row.name, 't_warehouse', "");
// 						frm.refresh_fields("items");
// 					}
// 	}
// 	})
// 	},
// 	remove_snf_button:function(frm){
// 		frappe.call({
// 			method:"dairy.milk_entry.custom_stock_entry.get_remove_snf",
// 			args:{
// 				"name":frm.doc.name
// 			},
// 			callback:function(r){
// 				if (r.message){
// 					console.log("$$$$$$$$$$$",r.message)
// 						var child_table = frm.fields_dict['items'].grid;
	
// 						// Create a new row object
// 						var new_row = child_table.add_new_row();
				
// 						// Set the values for the new row
// 						frappe.model.set_value(new_row.doctype, new_row.name, 's_warehouse', frm.doc.from_warehouse);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'item_code', r.message.item_code);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'qty', r.message.qty);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'snf_per', r.message.snf);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'fat_per', r.message.fat);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'fat', r.message.total_fat_in_kg);
// 						frappe.model.set_value(new_row.doctype, new_row.name, 'fat',  r.message.total_fat_in_kg);
// 						frm.refresh_fields("items");
// 						frappe.model.set_value(new_row.doctype, new_row.name, 't_warehouse', "");
// 						frm.refresh_fields("items");
// 					}
		
// 	}
// 	})
// 	}


})

frappe.ui.form.on('Stock Entry Detail', {

    s_warehouse : function(frm, cdt, cdn){
        var d = locals[cdt][cdn];
        if(d.s_warehouse){
            var df = frappe.meta.get_docfield("Stock Entry Detail","fat", cur_frm.doc.name);
            df.read_only = 0;
            var df = frappe.meta.get_docfield("Stock Entry Detail","fat_per", cur_frm.doc.name);
            df.read_only = 0;
            var df = frappe.meta.get_docfield("Stock Entry Detail","snf_clr", cur_frm.doc.name);
            df.read_only = 0;
            var df = frappe.meta.get_docfield("Stock Entry Detail","snf_clr_per", cur_frm.doc.name);
            df.read_only = 0;
			var df = frappe.meta.get_docfield("Stock Entry Detail","snf_per", cur_frm.doc.name);
            df.read_only = 0;
			var df = frappe.meta.get_docfield("Stock Entry Detail","snf", cur_frm.doc.name);
            df.read_only = 0;

        }else{
            var df = frappe.meta.get_docfield("Stock Entry Detail","fat", cur_frm.doc.name);
            df.read_only = 0;
            var df = frappe.meta.get_docfield("Stock Entry Detail","fat_per", cur_frm.doc.name);
            df.read_only = 0;
            var df = frappe.meta.get_docfield("Stock Entry Detail","snf_clr", cur_frm.doc.name);
            df.read_only = 0;
            var df = frappe.meta.get_docfield("Stock Entry Detail","snf_clr_per", cur_frm.doc.name);
            df.read_only = 0;
			var df = frappe.meta.get_docfield("Stock Entry Detail","snf_per", cur_frm.doc.name);
            df.read_only = 0;
			var df = frappe.meta.get_docfield("Stock Entry Detail","snf", cur_frm.doc.name);
            df.read_only = 0;
        }
    },

	fat: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        if(d.fat){
            frappe.call({
				method: "dairy.milk_entry.custom_stock_entry.get_item_weight",
				args: {"item_code": d.item_code },
				callback: function(r) {
					if (!r.exe){
					       var weight = r.message * d.transfer_qty
					       var per = ((d.fat / weight) * 100)
					        frappe.model.set_value(cdt, cdn, "fat_per", per);
					}
				}
			});
        }
	},

   fat_per: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        if(d.fat_per){
            frappe.call({
				method: "dairy.milk_entry.custom_stock_entry.get_item_weight",
				args: {"item_code": d.item_code },
				callback: function(r) {
					if (!r.exe){
					       var weight = r.message * d.transfer_qty
					       var fat = ((d.fat_per / 100) * weight)
					       if(! d.fat){
					        frappe.model.set_value(cdt, cdn, "fat", fat);
					       }
					       frappe.model.set_value(cdt, cdn, "fat", fat);

					}
				}
			});
        }
	},

	snf_clr: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        if(d.snf_clr){
            frappe.call({
				method: "dairy.milk_entry.custom_stock_entry.get_item_weight",
				args: {"item_code": d.item_code },
				callback: function(r) {
					if (!r.exe){
					       var weight = r.message * d.transfer_qty
					       var per = ((d.snf_clr / weight) * 100)
					       if(! d.snf_clr_per){
					        frappe.model.set_value(cdt, cdn, "snf_clr_per", per);
					       }
					       frappe.model.set_value(cdt, cdn, "snf_clr_per", per);

					}
				}
			});
        }
	},

    snf_clr_per: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        if(d.snf_clr_per){
            frappe.call({
				method: "dairy.milk_entry.custom_stock_entry.get_item_weight",
				args: {"item_code": d.item_code },
				callback: function(r) {
					if (!r.exe){
					       var weight = r.message * d.transfer_qty
					       var snf_clr = ((d.snf_clr_per / 100) * weight)
					       if(! d.snf_clr){
					        frappe.model.set_value(cdt, cdn, "snf_clr", snf_clr);
					       }
                            frappe.model.set_value(cdt, cdn, "snf_clr", snf_clr);
					}
				}
			});
        }
	},

	snf_per: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        if(d.snf_per){
            frappe.call({
				method: "dairy.milk_entry.custom_stock_entry.get_item_weight",
				args: {"item_code": d.item_code },
				callback: function(r) {
					if (!r.exe){
					       var weight = r.message * d.transfer_qty
					       var snf = ((d.snf_per / 100) * weight)
					       if(! d.snf){
					        frappe.model.set_value(cdt, cdn, "snf", snf);
					       }
                            frappe.model.set_value(cdt, cdn, "snf", snf);
					}
				}
			});
        }
	},

	snf: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        if(d.snf){
            frappe.call({
				method: "dairy.milk_entry.custom_stock_entry.get_item_weight",
				args: {"item_code": d.item_code },
				callback: function(r) {
					if (!r.exe){
					       var weight = r.message * d.transfer_qty
					       var s_per = ((d.snf / weight) * 100)
					       if(! d.snf_per){
					        frappe.model.set_value(cdt, cdn, "snf_per", s_per);
					       }
					       frappe.model.set_value(cdt, cdn, "snf_per", s_per);

					}
					
				}
			});
        }
	},

	qty : function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.qty){
			frappe.call({
				method: "dairy.milk_entry.custom_stock_entry.get_item_weight",
				args: {"item_code": d.item_code },
				callback: function(r) {
					if (!r.exe){
					    	var weight = r.message * d.transfer_qty
					       	var snf = ((d.snf_per / 100) * weight)
					       	if(! d.snf){
					        	frappe.model.set_value(cdt, cdn, "snf", snf);
					       	}
                            frappe.model.set_value(cdt, cdn, "snf", snf);

							var snf_clr = ((d.snf_clr_per / 100) * weight)
							if(! d.snf_clr){
							frappe.model.set_value(cdt, cdn, "snf_clr", snf_clr);
							}
							frappe.model.set_value(cdt, cdn, "snf_clr", snf_clr);

							var fat = ((d.fat_per / 100) * weight)
							if(! d.fat){
							 frappe.model.set_value(cdt, cdn, "fat", fat);
							}
							frappe.model.set_value(cdt, cdn, "fat", fat);
					}
				}
			})
			
		}
	}

});