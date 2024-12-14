//frappe.provide('frappe.ui.form');
//
//frappe.ui.form.MilkEntryQuickEntryForm = frappe.ui.form.QuickEntryForm.extend({
//	init: function(doctype, after_insert) {
//		this.skip_redirect_on_error = true;
//		this._super(doctype, after_insert);
//	},
//
//	render_dialog: function() {
//        this.mandatory = this.mandatory.concat(this.get_variant_fields());
//        console.log("======this.mandatory",this.mandatory)
//		this._super();
//	},
//    validate: function(frm) {
//        console.log("====validate==")
//    }
//
//    get_variant_fields: function(frm) {
//        var me = this;
//        let dcs = null;
//		var variant_fields = [
//		{
//			label: __('DCS'),
//			fieldname: 'quick_dcs',
//			fieldtype: 'Link',
//			options:"Warehouse",
//			reqd:1,
//			onchange: function() {
//                dcs = this.get_value()
//			},
//			get_query: function() {
//				return {
//					filters: {
//						"is_dcs": 1
//					}
//				};
//			},
//		},
//		{
//			label: __("Member"),
//			fieldname: "quick_member",
//			fieldtype: "Link",
//			options:"Supplier",
//			reqd:1,
//			get_query: function() {
//				return {
//					filters: {
//						"dcs_id":dcs
//					}
//				};
//			}
//		},
//		{
//			label: __("Milk Type"),
//			fieldname: "quick_milk_type",
//			fieldtype: "Select",
//			options:[
//			        { "value": "Cow", "label": __("Cow Milk") },
//				    { "value": "Buf", "label": __("Buffaow Milk") },
//				    { "value": "Mix", "label": __("Mix Milk") },
//			],
//		    default: "Cow"
//		},
//		{
//			label: __("Volume"),
//			fieldname: "quick_vol",
//			fieldtype: "Float",
//			default:1
//		},
//
//		{
//			label: __("FAT"),
//			fieldname: "quick_fat",
//			fieldtype: "Float"
//		},
//        {
//			label: __("CLR"),
//			fieldname: "quick_clr",
//			fieldtype: "Float"
//		}
//		];
//		return variant_fields;
//	},
//})