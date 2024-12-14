frappe.ui.form.on("Stock Reconciliation", {
    refresh :function(frm){
        frm.add_custom_button(__("Milk Ledger"), function() {
            frappe.route_options = {
               voucher_no: frm.doc.name,
               from_date: frm.doc.posting_date,
               to_date: moment(frm.doc.modified).format('YYYY-MM-DD'),
               company: frm.doc.company
            };
            frappe.set_route("query-report", "Milk Ledger");
            }, __("View"));
    }
})

frappe.ui.form.on("Stock Reconciliation Item", {
        
    fat: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        frappe.db.get_value("Item", d.item_code, ["weight_per_unit"]).then((r) => {
        if(d.fat){
            var weight = r.message['weight_per_unit'] * d.qty
            var per = ((d.fat / weight) * 100)
            frappe.model.set_value(cdt, cdn, "fat_per", per);
        }
    })
	},

   fat_per: function(frm, cdt, cdn) {
    var d = locals[cdt][cdn];
    frappe.db.get_value("Item", d.item_code, ["weight_per_unit"]).then((r) => {
        if(d.fat_per){
            var weight =r.message['weight_per_unit']* d.qty
            var fat = ((d.fat_per / 100) * weight)
            frappe.model.set_value(cdt, cdn, "fat", fat);
        }
    })
	},

	snf_clr: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        frappe.db.get_value("Item", d.item_code, ["weight_per_unit"]).then((r) => {
        if(d.snf_clr){
            var weight = r.message['weight_per_unit'] * d.qty
            var per = ((d.snf_clr / weight) * 100)
            frappe.model.set_value(cdt, cdn, "snf_clr_per", per);
        }
    })
	},

    snf_clr_per: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        frappe.db.get_value("Item", d.item_code, ["weight_per_unit"]).then((r) => {
        if(d.snf_clr_per){
            var weight =r.message['weight_per_unit'] * d.qty
            var snf_clr = ((d.snf_clr_per / 100) * weight)
            frappe.model.set_value(cdt, cdn, "snf_clr", snf_clr);
        }
    })
	},

	snf_per: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        frappe.db.get_value("Item", d.item_code, ["weight_per_unit"]).then((r) => {
        if(d.snf_per){
            var weight = r.message['weight_per_unit']* d.qty
            var snf = ((d.snf_per / 100) * weight)
            frappe.model.set_value(cdt, cdn, "snf", snf);
        }
    })
	},

	snf: function(frm, cdt, cdn) {
        var d = locals[cdt][cdn];
        frappe.db.get_value("Item", d.item_code, ["weight_per_unit"]).then((r) => {
        if(d.snf){
            var weight = r.message['weight_per_unit'] * d.qty
            var s_per = ((d.snf / weight) * 100)
            frappe.model.set_value(cdt, cdn, "snf_per", s_per);
            
            
        }
    })
	},

	qty : function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.qty){
            frappe.db.get_value("Item", d.item_code, ["weight_per_unit"]).then((r) => {
           
                if(d.snf_per){
                    var weight = r.message['weight_per_unit']* d.qty
                    var snf = ((d.snf_per / 100) * weight)
                    frappe.model.set_value(cdt, cdn, "snf", snf);
                }
                    

            
                if(d.snf_clr_per){
                    var weight = r.message['weight_per_unit']* d.qty
                    var snf_clr = ((d.snf_clr_per / 100) * weight)
                    frappe.model.set_value(cdt, cdn, "snf_clr", snf_clr);
                }
                

                
                if(d.fat_per){
                    var weight = r.message['weight_per_unit'] * d.qty
                    var fat = ((d.fat_per / 100) * weight)
                    frappe.model.set_value(cdt, cdn, "fat", fat);
                }
            })           
		}
	},
    
    
});
