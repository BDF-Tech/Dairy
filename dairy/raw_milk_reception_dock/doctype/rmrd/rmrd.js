// Copyright (c) 2020, Dexciss Technology Pvt Ltd and contributors
// For license information, please see license.txt

frappe.ui.form.on('RMRD', {
	 refresh: function(frm) {
        // if (!frm.doc.__islocal && frm.doc.docstatus == 0 && !frm.doc.hide_start_rmrd_button){
        if (frm.doc.status=='Submitted'){  
            frm.add_custom_button(__('Start RMRD'), function () {
                return frappe.call({
                    doc: frm.doc,
                    method: 'start_rmrd',
                    callback: function(r) {
                        frm.refresh();
                    }
                });
            }).addClass("btn-primary");
        }
        if (frm.doc.status=='In-Progress'){
            frm.add_custom_button(__('Add / Edit RMRD'), function () {
                frappe.route_options = {"rmrd": frm.doc.name};
                frappe.set_route("Report", "RMRD Lines");
        });

            frm.add_custom_button(__('Complete'), function () {
                 return frappe.call({
                    doc: frm.doc,
                    method: 'change_status_complete1',
                    callback: function(r) {
                        frm.refresh();
                    }
                });
            }).addClass("btn-primary");


         }
	 },
     on_submit: function (frm){
        if (frm.doc.t_g_cow_can <=0){
            frm.set_df_property("t_g_cow_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_g_cow_can", "hidden", 0);

        }
        if (frm.doc.t_g_cow_wt <=0){
            frm.set_df_property("t_g_cow_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_g_cow_wt", "hidden", 0);

        }
        if (frm.doc.t_g_buf_can <=0){
            frm.set_df_property("t_g_buf_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_g_buf_can", "hidden", 0);

        }
        if (frm.doc.t_g_buf_wt <=0){
            frm.set_df_property("t_g_buf_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_g_buf_wt", "hidden", 0);

        }
        if (frm.doc.t_g_mix_can <=0){
            frm.set_df_property("t_g_mix_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_g_mix_can", "hidden", 0);

        }
        if (frm.doc.t_g_mix_wt <=0){
            frm.set_df_property("t_g_mix_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_g_mix_wt", "hidden", 0);

        }
        if (frm.doc.t_s_cow_can <=0){
            frm.set_df_property("t_s_cow_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_s_cow_can", "hidden", 0);

        }
        if (frm.doc.t_s_cow_wt <=0){
            frm.set_df_property("t_s_cow_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_s_cow_wt", "hidden", 0);

        }
        if (frm.doc.t_s_buf_can <=0){
            frm.set_df_property("t_s_buf_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_s_buf_can", "hidden", 0);

        }
        if (frm.doc.t_s_buf_wt <=0){
            frm.set_df_property("t_s_buf_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_s_buf_wt", "hidden", 0);

        }
        if (frm.doc.t_s_mix_can <=0){
            frm.set_df_property("t_s_mix_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_s_mix_can", "hidden", 0);

        }
        if (frm.doc.t_s_mix_wt <=0){
            frm.set_df_property("t_s_mix_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_s_mix_wt", "hidden", 0);

        }
        if (frm.doc.t_c_cow_can <=0){
            frm.set_df_property("t_c_cow_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_c_cow_can", "hidden", 0);

        }
        if (frm.doc.t_c_cow_wt <=0){
            frm.set_df_property("t_c_cow_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_c_cow_wt", "hidden", 0);

        }
        if (frm.doc.t_c_buf_can <=0){
            frm.set_df_property("t_c_buf_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_c_buf_can", "hidden", 0);

        }
        if (frm.doc.t_c_buf_wt <=0){
            frm.set_df_property("t_c_buf_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_c_buf_wt", "hidden", 0);

        }
        if (frm.doc.t_c_mix_can <=0){
            frm.set_df_property("t_c_mix_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_c_mix_can", "hidden", 0);

        }
        if (frm.doc.t_c_mix_wt <=0){
            frm.set_df_property("t_c_mix_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_c_mix_wt", "hidden", 0);

        }
        if (frm.doc.t_cow_sam <=0){
            frm.set_df_property("t_cow_sam", "hidden", 1);

        }
        else{
            frm.set_df_property("t_cow_sam", "hidden", 0);

        }
        if (frm.doc.t_buf_sam <=0){
            frm.set_df_property("t_buf_sam", "hidden", 1);

        }
        else{
            frm.set_df_property("t_buf_sam", "hidden", 0);

        }
        if (frm.doc.t_mix_sam <=0){
            frm.set_df_property("t_mix_sam", "hidden", 1);

        }
        else{
            frm.set_df_property("t_mix_sam", "hidden", 0);

        }
        if (frm.doc.t_cow_m_fat <=0){
            frm.set_df_property("t_cow_m_fat", "hidden", 1);

        }
        else{
            frm.set_df_property("t_cow_m_fat", "hidden", 0);

        }
        if (frm.doc.t_cow_m_fat_kg <=0){
            frm.set_df_property("t_cow_m_fat_kg", "hidden", 1);

        }
        else{
            frm.set_df_property("t_cow_m_fat_kg", "hidden", 0);

        }
        if (frm.doc.t_cow_m_clr <=0){
            frm.set_df_property("t_cow_m_clr", "hidden", 1);

        }
        else{
            frm.set_df_property("t_cow_m_clr", "hidden", 0);

        }
        if (frm.doc.t_cow_m_clr_kg <=0){
            frm.set_df_property("t_cow_m_clr_kg", "hidden", 1);

        }
        else{
            frm.set_df_property("t_cow_m_clr_kg", "hidden", 0);

        }
        if (frm.doc.t_buf_m_fat <=0){
            frm.set_df_property("t_buf_m_fat", "hidden", 1);

        }
        else{
            frm.set_df_property("t_buf_m_fat", "hidden", 0);

        }
        if (frm.doc.t_buf_m_fat_kg <=0){
            frm.set_df_property("t_buf_m_fat_kg", "hidden", 1);

        }
        else{
            frm.set_df_property("t_buf_m_fat_kg", "hidden", 0);

        }
        if (frm.doc.t_buf_m_clr <=0){
            frm.set_df_property("t_buf_m_clr", "hidden", 1);

        }
        else{
            frm.set_df_property("t_buf_m_clr", "hidden", 0);

        }
        if (frm.doc.t_buf_m_clr_kg <=0){
            frm.set_df_property("t_buf_m_clr_kg", "hidden", 1);

        }
        else{
            frm.set_df_property("t_buf_m_clr_kg", "hidden", 0);

        }
        if (frm.doc.t_mix_m_fat <=0){
            frm.set_df_property("t_mix_m_fat", "hidden", 1);

        }
        else{
            frm.set_df_property("t_mix_m_fat", "hidden", 0);

        }
        if (frm.doc.t_mix_m_fat_kg <=0){
            frm.set_df_property("t_mix_m_fat_kg", "hidden", 1);

        }
        else{
            frm.set_df_property("t_mix_m_fat_kg", "hidden", 0);

        }
        if (frm.doc.t_mix_m_clr <=0){
            frm.set_df_property("t_mix_m_clr", "hidden", 1);

        }
        else{
            frm.set_df_property("t_mix_m_clr", "hidden", 0);

        }
        if (frm.doc.t_mix_m_clr_kg <=0){
            frm.set_df_property("t_mix_m_clr_kg", "hidden", 1);

        }
        else{
            frm.set_df_property("t_mix_m_clr_kg", "hidden", 0);

        }
     },

     before_submit: function(frm) {
        return frm.call('submit_rmrd').then(() => {
            frm.refresh_field('status');
        });
    },
    
	 onload: function(frm){
        frm.set_query('route', function(doc) {
            return {
                filters: {
                    "route_type":"Milk Procurement",
                    // "docstatus":1
                }
            };
        });
        frm.set_query('target_warehouse', function(doc) {
            return {
                filters: {
//                    "is_dcs":0,
                    "is_group":0,
                    "company":frappe.defaults.get_user_default("Company"),
                    "disabled":0
                }
            };
        });
        if (frm.doc.t_g_cow_can <=0){
            frm.set_df_property("t_g_cow_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_g_cow_can", "hidden", 0);

        }
        if (frm.doc.t_g_cow_wt <=0){
            frm.set_df_property("t_g_cow_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_g_cow_wt", "hidden", 0);

        }
        if (frm.doc.t_g_buf_can <=0){
            frm.set_df_property("t_g_buf_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_g_buf_can", "hidden", 0);

        }
        if (frm.doc.t_g_buf_wt <=0){
            frm.set_df_property("t_g_buf_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_g_buf_wt", "hidden", 0);

        }
        if (frm.doc.t_g_mix_can <=0){
            frm.set_df_property("t_g_mix_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_g_mix_can", "hidden", 0);

        }
        if (frm.doc.t_g_mix_wt <=0){
            frm.set_df_property("t_g_mix_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_g_mix_wt", "hidden", 0);

        }
        if (frm.doc.t_s_cow_can <=0){
            frm.set_df_property("t_s_cow_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_s_cow_can", "hidden", 0);

        }
        if (frm.doc.t_s_cow_wt <=0){
            frm.set_df_property("t_s_cow_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_s_cow_wt", "hidden", 0);

        }
        if (frm.doc.t_s_buf_can <=0){
            frm.set_df_property("t_s_buf_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_s_buf_can", "hidden", 0);

        }
        if (frm.doc.t_s_buf_wt <=0){
            frm.set_df_property("t_s_buf_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_s_buf_wt", "hidden", 0);

        }
        if (frm.doc.t_s_mix_can <=0){
            frm.set_df_property("t_s_mix_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_s_mix_can", "hidden", 0);

        }
        if (frm.doc.t_s_mix_wt <=0){
            frm.set_df_property("t_s_mix_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_s_mix_wt", "hidden", 0);

        }
        if (frm.doc.t_c_cow_can <=0){
            frm.set_df_property("t_c_cow_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_c_cow_can", "hidden", 0);

        }
        if (frm.doc.t_c_cow_wt <=0){
            frm.set_df_property("t_c_cow_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_c_cow_wt", "hidden", 0);

        }
        if (frm.doc.t_c_buf_can <=0){
            frm.set_df_property("t_c_buf_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_c_buf_can", "hidden", 0);

        }
        if (frm.doc.t_c_buf_wt <=0){
            frm.set_df_property("t_c_buf_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_c_buf_wt", "hidden", 0);

        }
        if (frm.doc.t_c_mix_can <=0){
            frm.set_df_property("t_c_mix_can", "hidden", 1);

        }
        else{
            frm.set_df_property("t_c_mix_can", "hidden", 0);

        }
        if (frm.doc.t_c_mix_wt <=0){
            frm.set_df_property("t_c_mix_wt", "hidden", 1);

        }
        else{
            frm.set_df_property("t_c_mix_wt", "hidden", 0);

        }
        if (frm.doc.t_cow_sam <=0){
            frm.set_df_property("t_cow_sam", "hidden", 1);

        }
        else{
            frm.set_df_property("t_cow_sam", "hidden", 0);

        }
        if (frm.doc.t_buf_sam <=0){
            frm.set_df_property("t_buf_sam", "hidden", 1);

        }
        else{
            frm.set_df_property("t_buf_sam", "hidden", 0);

        }
        if (frm.doc.t_mix_sam <=0){
            frm.set_df_property("t_mix_sam", "hidden", 1);

        }
        else{
            frm.set_df_property("t_mix_sam", "hidden", 0);

        }
        if (frm.doc.t_cow_m_fat <=0){
            frm.set_df_property("t_cow_m_fat", "hidden", 1);

        }
        else{
            frm.set_df_property("t_cow_m_fat", "hidden", 0);

        }
        if (frm.doc.t_cow_m_fat_kg <=0){
            frm.set_df_property("t_cow_m_fat_kg", "hidden", 1);

        }
        else{
            frm.set_df_property("t_cow_m_fat_kg", "hidden", 0);

        }
        if (frm.doc.t_cow_m_clr <=0){
            frm.set_df_property("t_cow_m_clr", "hidden", 1);

        }
        else{
            frm.set_df_property("t_cow_m_clr", "hidden", 0);

        }
        if (frm.doc.t_cow_m_clr_kg <=0){
            frm.set_df_property("t_cow_m_clr_kg", "hidden", 1);

        }
        else{
            frm.set_df_property("t_cow_m_clr_kg", "hidden", 0);

        }
        if (frm.doc.t_buf_m_fat <=0){
            frm.set_df_property("t_buf_m_fat", "hidden", 1);

        }
        else{
            frm.set_df_property("t_buf_m_fat", "hidden", 0);

        }
        if (frm.doc.t_buf_m_fat_kg <=0){
            frm.set_df_property("t_buf_m_fat_kg", "hidden", 1);

        }
        else{
            frm.set_df_property("t_buf_m_fat_kg", "hidden", 0);

        }
        if (frm.doc.t_buf_m_clr <=0){
            frm.set_df_property("t_buf_m_clr", "hidden", 1);

        }
        else{
            frm.set_df_property("t_buf_m_clr", "hidden", 0);

        }
        if (frm.doc.t_buf_m_clr_kg <=0){
            frm.set_df_property("t_buf_m_clr_kg", "hidden", 1);

        }
        else{
            frm.set_df_property("t_buf_m_clr_kg", "hidden", 0);

        }
        if (frm.doc.t_mix_m_fat <=0){
            frm.set_df_property("t_mix_m_fat", "hidden", 1);

        }
        else{
            frm.set_df_property("t_mix_m_fat", "hidden", 0);

        }
        if (frm.doc.t_mix_m_fat_kg <=0){
            frm.set_df_property("t_mix_m_fat_kg", "hidden", 1);

        }
        else{
            frm.set_df_property("t_mix_m_fat_kg", "hidden", 0);

        }
        if (frm.doc.t_mix_m_clr <=0){
            frm.set_df_property("t_mix_m_clr", "hidden", 1);

        }
        else{
            frm.set_df_property("t_mix_m_clr", "hidden", 0);

        }
        if (frm.doc.t_mix_m_clr_kg <=0){
            frm.set_df_property("t_mix_m_clr_kg", "hidden", 1);

        }
        else{
            frm.set_df_property("t_mix_m_clr_kg", "hidden", 0);

        }
       
    },
});
