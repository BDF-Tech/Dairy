<<<<<<< HEAD
=======
// // Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
// // For license information, please see license.txt

// frappe.ui.form.on('Gate Pass', {
//      onload : function(frm){

//         frm.set_query('route', function(doc) {
//             return {
//                 filters: {
//                     "company":doc.company,
//                      "route_type":"Milk Marketing",
//                     // "docstatus":1,
//                     "transporter":doc.transporter
//                 }
//             };
//         });

//         frm.set_query('transporter', function() {
// 			return {
// 				filters: {
// 					'is_transporter': 1
// 				}
// 			}
// 		});
//      },

// 	 refresh: function(frm) {
// 		if (!frm.doc.__islocal) {
// 			frm.set_df_property("items_section", "hidden", 1);
// 			frm.set_df_property("merge_items", "read_only", frm.is_new() ? 0 : 1);
// 		}
// 		if (frm.doc.__islocal) {
// 			frm.set_df_property("item", "reqd", 1);
// 			frm.set_df_property("merge_items", "hidden", 1);
// 			frm.set_df_property("crate_count_section", "hidden", 1);
// 			frm.set_df_property("loose_crate_section", "hidden", 1);
	
// 		} else {
// 			frm.set_df_property("merge_items", "hidden", 0);
// 			frm.set_df_property("crate_count_section", "hidden", 0);
// 			frm.set_df_property("loose_crate_section", "hidden", 0);
// 		}
// 		if (frm.is_new()) {
// 			if (frm.doc.docstatus === 0) {
// 				frappe.db.get_doc('Dairy Settings').then(t => {
// 					if (t.crate_reconciliation_based_on == "Delivery Note" || t.crate_reconciliation_based_on == "Gate Pass") {
// 						frm.add_custom_button(__('Delivery Note'),
// 							function() {
// 								erpnext.utils.map_current_doc({
// 									method: "dairy.milk_entry.doctype.gate_pass.gate_pass.make_delivery_note",
// 									source_doctype: "Delivery Note",
// 									target: me.frm,
// 									setters: {
// 										route: frm.doc.route || undefined,
// 										shift: frm.doc.shift || undefined,
// 										transporter: frm.doc.transporter || undefined
// 									},
// 									get_query_filters: {
// 										docstatus: 1,
// 										status: ["=", ["To Bill"]],
// 										crate_gate_pass_done: 0,
// 										posting_date: frm.doc.date
// 									}
// 								});
// 							}, __("Get items from"));
// 					}
// 				});
	
// 				frappe.db.get_doc('Dairy Settings').then(t => {
// 					if (t.crate_reconciliation_based_on == "Sales Invoice" || t.crate_reconciliation_based_on == "Gate Pass") {
// 						frm.add_custom_button(__('Sales Invoice'),
// 							function() {
// 								erpnext.utils.map_current_doc({
// 									method: "dairy.milk_entry.doctype.gate_pass.gate_pass.make_sales_invoice",
// 									source_doctype: "Sales Invoice",
// 									target: me.frm,
// 									setters: {
// 										route: frm.doc.route || undefined,
// 										delivery_shift: frm.doc.shift || undefined,
// 										transporter: frm.doc.transporter || undefined
// 									},
// 									get_query_filters: {
// 										docstatus: 1,
// 										status: ["=", ["To Bill"]],
// 										gate_pass: 0,
// 										posting_date: frm.doc.date
// 									}
// 								});
// 							}, __("Get items from"));
// 					}
// 				});
	
// 				frappe.db.get_doc('Dairy Settings').then(t => {
// 					if (t.crate_reconciliation_based_on == "Sales Order" || t.crate_reconciliation_based_on == "Gate Pass") {
// 						frm.add_custom_button(__('Sales Order'),
// 							function() {
// 								erpnext.utils.map_current_doc({
// 									method: "dairy.milk_entry.doctype.gate_pass.gate_pass.make_sales_order",
// 									source_doctype: "Sales Order",
// 									target: me.frm,
// 									setters: {
// 										route: frm.doc.route || undefined,
// 										delivery_shift: frm.doc.shift || undefined,
// 										transporter: frm.doc.transporter || undefined
// 									},
// 									get_query_filters: {
// 										docstatus: 1,
// 										status: ["=", ["To Bill"]],
// 										transaction_date: frm.doc.date
// 									}
// 								});
// 							}, __("Get items from"));
// 					}
// 				});


// 				frappe.db.get_doc('Dairy Settings').then(t => {
// 					if (t.crate_reconciliation_based_on == "Sales Order" || t.crate_reconciliation_based_on == "Gate Pass") {
// 						frm.add_custom_button(__('Stock Entry'),
// 							function() {
// 								erpnext.utils.map_current_doc({
// 									method: "dairy.milk_entry.doctype.gate_pass.gate_pass.make_stock_entry",
// 									source_doctype: "Stock Entry",
// 									target: me.frm,
// 									setters: {
// 										from_warehouse: frm.doc.from_warehouse || undefined,
// 										to_warehouse: frm.doc.to_warehouse || undefined,
// 									},
// 									get_query_filters: {
// 										docstatus: 1,
// 										purpose: ["=", ["Material Transfer"]],
// 										posting_date: frm.doc.date

// 									}
// 								});
// 							}, __("Get items from"));
// 					}
// 				});
	
	
				
// 			}
// 		}
// 	},
// // 	        if(! frm.doc.__islocal){
// // 	            frm.set_df_property("items_section", "hidden", 1);
// // 				frm.set_df_property("merge_items", "read_only", frm.is_new() ? 0 : 1);
// // 	        }
// // 	        if( frm.doc.__islocal){
// // 	            frm.set_df_property("item", "reqd", 1);
// // 	            frm.set_df_property("merge_items", "hidden", 1);
// // 	            frm.set_df_property("crate_count_section", "hidden", 1);
// //                 frm.set_df_property("loose_crate_section", "hidden", 1);

// // 	        }
// // 	        else{
// // 	            frm.set_df_property("merge_items", "hidden", 0);
// // 	            frm.set_df_property("crate_count_section", "hidden", 0);
// //                 frm.set_df_property("loose_crate_section", "hidden", 0);
// // 	        }
// // 	        if ((frm.is_new())) {
// //             if (frm.doc.docstatus===0 ) {
// // 			frappe.db.get_doc('Dairy Settings').then(t => {
// // 			if(t.crate_reconciliation_based_on=="Delivery Note" || t.crate_reconciliation_based_on=="Gate Pass"){
// // 				frm.add_custom_button(__('Delivery Note'),
// // 					function() {
						
// // 						erpnext.utils.map_current_doc({		
// // 							method: "dairy.milk_entry.doctype.gate_pass.gate_pass.make_delivery_note",
// // 							source_doctype: "Delivery Note",
// // 							target: me.frm,
// // 							setters: {
// // 							route: frm.doc.route || undefined,
// // 							shift: frm.doc.shift || undefined,
// // 							transporter: frm.doc.transporter || undefined
// // 							},

// // 							get_query_filters: {
// // 								docstatus: 1,
// // 								status: ["=", ["To Bill"]],
// //                                 crate_gate_pass_done:0,
// // 								posting_date: frm.doc.date
// // 							}
// // 						})
// // //						frappe.msgprint({
// // //                            title: __('Note'),
// // //                            indicator: 'green',
// // //                            message: __('After getting item. Save the document to see item details...')
// // //                        });
					
					
// // 					}, __("Get items from"));
// // 				}
// // 			})
// // 				frappe.db.get_doc('Dairy Settings').then(t => {
// // 					if(t.crate_reconciliation_based_on=="Sales Invoice" || t.crate_reconciliation_based_on=="Gate Pass"){
// // 					frm.add_custom_button(__('Sales Invoice'),
// // 					function() {
// // 						erpnext.utils.map_current_doc({
// // 							method: "dairy.milk_entry.doctype.gate_pass.gate_pass.make_sales_invoice",
// // 							source_doctype: "Sales Invoice",
// // 							target: me.frm,
// // 							setters: {
// // 							route: frm.doc.route || undefined,
// // 							delivery_shift: frm.doc.shift || undefined,
// // 							transporter: frm.doc.transporter || undefined
// // 							},

// // 							get_query_filters: {
// // 								docstatus: 1,
// // 								status: ["=", ["To Bill"]],
// // 								gate_pass:0,
// // 								posting_date: frm.doc.date 
// //                                 // crate_gate_pass_done:0
// // 							}
// // 						})
// // //						frappe.msgprint({
// // //                            title: __('Note'),
// // //                            indicator: 'green',
// // //                            message: __('After getting item. Save the document to see item details...')
// // //                        });
					
					
// // 					}, __("Get items from"));
// // 				}
// // 				})

// // 				frappe.db.get_doc('Dairy Settings').then(t => {
// // 					if(t.crate_reconciliation_based_on=="Sales Order" || t.crate_reconciliation_based_on=="Gate Pass"){
// // 					frm.add_custom_button(__('Sales Order'),
// // 					function() {
// // 						debugger
// // 						erpnext.utils.map_current_doc({
// // 							method: "dairy.milk_entry.doctype.gate_pass.gate_pass.make_sales_order",
// // 							source_doctype: "Sales Order",
// // 							target: me.frm,
// // 							setters: {
// // 							route: frm.doc.route || undefined,
// // 							delivery_shift: frm.doc.shift || undefined,
// // 							transporter: frm.doc.transporter || undefined
// // 							},

// // 							get_query_filters: {
// // 								docstatus: 1,
// // 								status: ["=", ["To Bill"]],
// // 								// gate_pass:0,
// // 								transaction_date: frm.doc.date 
// //                                 // crate_gate_pass_done:0
// // 							}
// // 						})
// // //						frappe.msgprint({
// // //                            title: __('Note'),
// // //                            indicator: 'green',
// // //                            message: __('After getting item. Save the document to see item details...')
// // //                        });
					
					
// // 					}, __("Get items from"));
// // 				}
// // 				})
// // 				frappe.db.get_doc('Dairy Settings').then(t => {
// // 					if(t.crate_reconciliation_based_on=="Sales Order" || t.crate_reconciliation_based_on=="Gate Pass"){
// // 						debugger
// // 					frm.add_custom_button(__('Stock Entry'),
// // 					function() {

// // 						erpnext.utils.map_current_doc({
// // 							// method: "dairy.milk_entry.doctype.gate_pass.gate_pass.make_stock_entry",
// // 							source_doctype: "Stock Entry",
// // 							target: me.frm,
// // 							// setters: {
// // 							// route: frm.doc.route || undefined,
// // 							// delivery_shift: frm.doc.shift || undefined,
// // 							// transporter: frm.doc.transporter || undefined
// // 							// },

// // 							get_query_filters: {
// // 								docstatus: 1,
// // 								// status: ["=", ["To Bill"]],
// // 								// // gate_pass:0,
// // 								// transaction_date: frm.doc.date 
// //                                 // crate_gate_pass_done:0
// // 							}
// // 						})
// // //						frappe.msgprint({
// // //                            title: __('Note'),
// // //                            indicator: 'green',
// // //                            message: __('After getting item. Save the document to see item details...')
// // //                        });
					
					
// // 					}, __("Get items from"));
// // 				}
// // 				})




				
			
// // 			}
// // 			}
// // 	 },

//     calculate_crate: function(frm){
//             if(frm.doc.name  && frm.doc.gate_crate_cal_done != "Done"){
//                 return cur_frm.call({
//                     method:"dairy.milk_entry.doctype.gate_pass.gate_pass.calculate_crate",
//                     args: {
//                             doc_name: cur_frm.doc.name
//                           },
//                     callback: function(r)
//                         {
//                            cur_frm.reload_doc();
//                         }
//                 });
//                 }
//         },


// });

>>>>>>> eaa607b (Update)
// Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('Gate Pass', {
	onload: function (frm) {

		frm.set_query('route', function (doc) {
			return {
				filters: {
					"company": doc.company,
					"route_type": "Milk Marketing",
<<<<<<< HEAD
=======
					// "docstatus":1,
>>>>>>> eaa607b (Update)
					"transporter": doc.transporter
				}
			};
		});

		frm.set_query('transporter', function () {
			return {
				filters: {
					'is_transporter': 1
				}
			}
		});
	},

	refresh: function (frm) {
		if (!frm.doc.__islocal) {
			frm.set_df_property("items_section", "hidden", 1);
			frm.set_df_property("merge_items", "read_only", frm.is_new() ? 0 : 1);
		}
		if (frm.doc.__islocal) {
			frm.set_df_property("item", "reqd", 1);
			frm.set_df_property("merge_items", "hidden", 1);
			frm.set_df_property("crate_count_section", "hidden", 1);
			frm.set_df_property("loose_crate_section", "hidden", 1);

		}
		else {
			frm.set_df_property("merge_items", "hidden", 0);
			frm.set_df_property("crate_count_section", "hidden", 0);
			frm.set_df_property("loose_crate_section", "hidden", 0);
		}
		if ((frm.is_new())) {
			if (frm.doc.docstatus === 0) {
				frappe.db.get_doc('Dairy Settings').then(t => {
					if (t.crate_reconciliation_based_on == "Delivery Note" || t.crate_reconciliation_based_on == "Gate Pass") {
						frm.add_custom_button(__('Delivery Note'),
							() => {
								erpnext.utils.map_current_doc({
									method: "dairy.milk_entry.doctype.gate_pass.gate_pass.make_delivery_note",
									source_doctype: "Delivery Note",
									target: frm,
									setters: {
										route: frm.doc.route || undefined,
										shift: frm.doc.shift || undefined,
										transporter: frm.doc.transporter || undefined
									},

									get_query_filters: {
										docstatus: 1,
										status: ["=", ["To Bill"]],
										crate_gate_pass_done: 0,
										posting_date: frm.doc.date
									}
								})
<<<<<<< HEAD
=======
								//						frappe.msgprint({
								//                            title: __('Note'),
								//                            indicator: 'green',
								//                            message: __('After getting item. Save the document to see item details...')
								//                        });

>>>>>>> eaa607b (Update)

							}, __("Get items from"));
					}
				})
				frappe.db.get_doc('Dairy Settings').then(t => {
					if (t.crate_reconciliation_based_on == "Sales Invoice" || t.crate_reconciliation_based_on == "Gate Pass") {
						frm.add_custom_button(__('Sales Invoice'),
							() => {
								erpnext.utils.map_current_doc({
									method: "dairy.milk_entry.doctype.gate_pass.gate_pass.make_sales_invoice",
									source_doctype: "Sales Invoice",
									target: frm,
									setters: [
										{
											fieldtype: "Link",
											label: __("Customer"),
											options: "Customer",
											fieldname: "customer_name",
										},
										{
											fieldtype: "Link",
											label: "Route",
											options: "Route Master",
											fieldname: "route",
											default: frm.doc.route,
										},
										{
											fieldtype: "Select",
											label: "Delivery Shift",
											options: "\nMorning\nEvening",
											fieldname: "delivery_shift",
											default: frm.doc.delivery_shift,
										},
									],
									get_query_filters: {
										docstatus: 1,
										status: ["=", ["To Bill"]],
										gate_pass: 0,
										posting_date: frm.doc.date,
									},
								});
							}, __("Get items from"));
					}
				})
				frappe.db.get_doc('Dairy Settings').then(t => {
					if (t.crate_reconciliation_based_on == "Sales Order" || t.crate_reconciliation_based_on == "Gate Pass") {
						frm.add_custom_button(__('Sales Order'),
							() => {
								erpnext.utils.map_current_doc({
									method: "dairy.milk_entry.doctype.gate_pass.gate_pass.make_sales_order",
									source_doctype: "Sales Order",
									target: frm,
									setters: {
										route: frm.doc.route || undefined,
										delivery_shift: frm.doc.shift || undefined,
										transporter: frm.doc.transporter || undefined
									},

									get_query_filters: {
										docstatus: 1,
										status: ["=", ["To Bill"]],
										// gate_pass:0,
										transaction_date: frm.doc.date
										// crate_gate_pass_done:0
									}
								})
								//						frappe.msgprint({
								//                            title: __('Note'),
								//                            indicator: 'green',
								//                            message: __('After getting item. Save the document to see item details...')
								//                        });


							}, __("Get items from"));
					}
				})

			}
		}
	},

	calculate_crate: function (frm) {
		if (frm.doc.name && frm.doc.gate_crate_cal_done != "Done") {
			return cur_frm.call({
				method: "dairy.milk_entry.doctype.gate_pass.gate_pass.calculate_crate",
				args: {
					doc_name: cur_frm.doc.name
				},
				callback: function (r) {
					cur_frm.reload_doc();
				}
			});
		}
	},


});
