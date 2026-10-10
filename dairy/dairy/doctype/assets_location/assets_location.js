// Copyright (c) 2026, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt

 frappe.ui.form.on("Assets Location", {
setup: function(frm) {
        frm.set_query("assets_code", function() {
            return {
                filters: {
                    item_group: "Asset"
                }
            };
        });
    }
 });
