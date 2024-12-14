frappe.ui.form.on("Purchase Invoice", {
  
})

frappe.ui.form.on("Purchase Invoice Item", {

    fat: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        console.log("--------------fat------------")
        if(d.fat){
            var weight = d.total_weight
            var per = ((d.fat / weight) * 100)
            frappe.model.set_value(cdt, cdn, "fat_per", per);
        }
	},

   fat_per: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        if(d.fat_per){
            var weight = d.total_weight
            var fat = ((d.fat_per / 100) * weight)
            frappe.model.set_value(cdt, cdn, "fat", fat);
        }
	},

	snf_clr: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        if(d.snf_clr){
            var weight = d.total_weight
            var per = ((d.snf_clr / weight) * 100)
            frappe.model.set_value(cdt, cdn, "snf_clr_per", per);
        }
	},

    snf_clr_per: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        if(d.snf_clr_per){
            var weight = d.total_weight
            var snf_clr = ((d.snf_clr_per / 100) * weight)
            frappe.model.set_value(cdt, cdn, "snf_clr", snf_clr);
        }
	},

	snf_per: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        if(d.snf_per){
            var weight = d.total_weight
            var snf = ((d.snf_per / 100) * weight)
            frappe.model.set_value(cdt, cdn, "snf", snf);
        }
	},

	snf: function(frm, cdt, cdn) {
	    var d = locals[cdt][cdn];
        if(d.snf){
            var weight = d.total_weight
            var s_per = ((d.snf / weight) * 100)
            frappe.model.set_value(cdt, cdn, "snf_per", s_per);
            
            
        }
	},

	qty : function(frm, cdt, cdn) {
		var d = locals[cdt][cdn];
		if(d.qty){
            frappe.db.get_value("Item", d.item_code, ["weight_per_unit"]).then((r) => {
                console.log('rrrrrrrrrrrrrrrrrrrrr',r.message,d.qty)
           
                if(d.snf_per){
                    var weight = d.total_weight
                    var snf = ((d.snf_per / 100) * weight)
                    console.log('snffffffffffffffffffff',snf)
                    frappe.model.set_value(cdt, cdn, "snf", snf);
                }
                    

            
                if(d.snf_clr_per){
                    var weight = d.total_weight
                    var snf_clr = ((d.snf_clr_per / 100) * weight)
                    frappe.model.set_value(cdt, cdn, "snf_clr", snf_clr);
                }
                

                
                if(d.fat_per){
                    var weight = d.total_weight
                    var fat = ((d.fat_per / 100) * weight)
                    frappe.model.set_value(cdt, cdn, "fat", fat);
                }
            })           
		}
	},
    
    
});
