frappe.pages['stock-dashboard'].on_page_load = function(wrapper) {

    var page = frappe.ui.make_app_page({
        parent: wrapper,
        title: 'Production Inventory Hub',
        single_column: true
    });

    // ==========================
    // CSS (Premium + Layer Fix)
    // ==========================

    $(`
    <style>

        .layout-main-section,
        .page-content,
        .layout-main,
        .page-body {
            background: #111827 !important;
        }

        body {
            background: radial-gradient(circle at 30% 20%, #1f2937, #111827 70%);
            font-family: 'Inter', sans-serif;
        }

        /* ===== FIX DROPDOWN OVERLAY ISSUE ===== */

        .page-form {
            position: relative;
            z-index: 50;
        }

        .awesomplete,
        .select2-container,
        .select2-dropdown,
        .ui-autocomplete,
        .dropdown-menu {
            z-index: 9999 !important;
        }

        .stats-wrapper,
        .stat-card,
        .dashboard-container {
            position: relative;
            z-index: 1;
        }

        /* FILTER BAR */
        .page-form {
            background: rgba(30, 41, 59, 0.85);
            backdrop-filter: blur(10px);
            padding: 18px 35px !important;
            border-bottom: 1px solid rgba(255,255,255,0.05) !important;
            border-radius: 0 0 20px 20px;
            margin-bottom: 30px;
        }

        /* ================= STATS ================= */

        .stats-wrapper {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px,1fr));
            gap: 18px;
            padding: 0 40px 30px 40px;
        }

        .stat-card {
            background: rgba(30, 41, 59, 0.8);
            backdrop-filter: blur(10px);
            border-radius: 18px;
            padding: 18px;
            border: 1px solid rgba(255,255,255,0.05);
            transition: all 0.25s ease;
        }

        .stat-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 12px 35px rgba(0,0,0,0.45);
        }

        .stat-title {
            font-size: 10px;
            letter-spacing: 1px;
            text-transform: uppercase;
            color: #94a3b8;
            margin-bottom: 6px;
        }

        .stat-value {
            font-size: 24px;
            font-weight: 700;
            color: #ffffff;
        }

        .critical { color: #f87171; }
        .healthy { color: #4ade80; }

        /* ================= CARDS ================= */

        .dashboard-container {
            padding: 0 40px 60px 40px;
        }

        .grid-container {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px,1fr));
            gap: 22px;
        }

        .stock-card {
            background: rgba(30, 41, 59, 0.85);
            backdrop-filter: blur(12px);
            border-radius: 22px;
            padding: 20px;
            border: 1px solid rgba(255,255,255,0.04);
            transition: all .3s ease;
            position: relative;
            cursor: pointer;
        }

        .stock-card:hover {
            transform: translateY(-6px);
            box-shadow: 0 20px 45px rgba(0,0,0,0.5);
        }

        /* Status strip */
        .stock-card.safe::after,
        .stock-card.critical::after {
            content: "";
            position: absolute;
            left: 0;
            top: 18px;
            bottom: 18px;
            width: 4px;
            border-radius: 12px;
        }

        .stock-card.safe::after {
            background: #4ade80;
        }

        .stock-card.critical::after {
            background: #f87171;
        }

        .item-name {
            font-size: 15px;
            font-weight: 600;
            color: #f8fafc;
            margin-bottom: 12px;
        }

        .metric-row {
            display: flex;
            justify-content: space-between;
            font-size: 12px;
            color: #9ca3af;
            margin-top: 6px;
        }

        .metric-row b {
            font-weight: 600;
            color: #e5e7eb;
        }

        .metric-row.status-critical {
            color: #f87171;
            font-weight: 600;
        }

        .metric-row.status-healthy {
            color: #4ade80;
            font-weight: 600;
        }

        .empty-state {
            color: #94a3b8;
            padding: 60px;
            text-align: center;
            font-size: 14px;
        }

    </style>
    `).appendTo(page.main);


    // ==========================
    // FILTERS
    // ==========================

    page.wh_f = page.add_field({
        fieldname:'warehouse',
        label:__('Warehouse'),
        fieldtype:'Link',
        options:'Warehouse',
        change:()=>refresh_data(page)
    });

    page.group_f = page.add_field({
        fieldname:'item_group',
        label:__('Item Group'),
        fieldtype:'Link',
        options:'Item Group',
        change:()=>refresh_data(page)
    });

    page.status_f = page.add_field({
        fieldname:'stock_status',
        label:'Stock Status',
        fieldtype:'Select',
        options:['All','Critical','Healthy'],
        default:'All',
        change:()=>refresh_data(page)
    });

    page.sort_f = page.add_field({
        fieldname:'sort_order',
        label:'Sort',
        fieldtype:'Select',
        options:['asc','desc'],
        default:'asc',
        change:()=>refresh_data(page)
    });

    page.set_primary_action(__('Refresh'), ()=>refresh_data(page));


    // ==========================
    // HTML
    // ==========================

    $(`
    <div class="stats-wrapper">
        <div class="stat-card">
            <div class="stat-title">Total Items</div>
            <div class="stat-value" id="total-items">0</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Reorder Required</div>
            <div class="stat-value critical" id="critical-items">0</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Healthy Items</div>
            <div class="stat-value healthy" id="healthy-items">0</div>
        </div>
        <div class="stat-card">
            <div class="stat-title">Avg Days</div>
            <div class="stat-value" id="avg-days">0</div>
        </div>
    </div>

    <div class="dashboard-container">
        <div id="stock-cards-container" class="grid-container"></div>
    </div>
    `).appendTo(page.main);

    refresh_data(page);
};


// ==========================
// DATA REFRESH
// ==========================

function refresh_data(page){

    $("#stock-cards-container").html(
        "<div class='empty-state'>Loading inventory data...</div>"
    );

    frappe.call({
        method:"dairy.dairy.page.stock_dashboard.stock_dashboard.get_stock_data",
        args:{
            warehouse:page.wh_f.get_value(),
            item_group:page.group_f.get_value(),
            stock_status:page.status_f.get_value(),
            sort_order:page.sort_f.get_value()
        },
        callback:function(r){
            render_data(r.message || []);
        }
    });
}


// ==========================
// RENDER
// ==========================

function render_data(data){

    if(!data.length){
        $("#stock-cards-container").html(
            "<div class='empty-state'>No stock found.</div>"
        );
        return;
    }

    let total = data.length;
    let critical = 0;
    let healthy = 0;
    let total_days = 0;
    let valid_day_items = 0;

    data.forEach(i=>{
        if(i.actual_qty <= i.reorder_level){
            critical++;
        } else {
            healthy++;
        }

        if(i.custom_no_of_days && i.custom_no_of_days > 0){
            total_days += (i.actual_qty / i.custom_no_of_days);
            valid_day_items++;
        }
    });

    let avg_days = valid_day_items ? (total_days / valid_day_items).toFixed(1) : 0;

    $("#total-items").text(total);
    $("#critical-items").text(critical);
    $("#healthy-items").text(healthy);
    $("#avg-days").text(avg_days);

    let html = data.map(i=>{

        let days_remaining = 0;
        if(i.custom_no_of_days && i.custom_no_of_days > 0){
            days_remaining = (i.actual_qty / i.custom_no_of_days).toFixed(1);
        }

        let isCritical = i.actual_qty <= i.reorder_level;

        return `
        <div class="stock-card ${isCritical ? 'critical' : 'safe'}"
             onclick="frappe.set_route('Form','Item','${i.item_code}')">

            <div class="item-name">${i.item_name}</div>

            <div class="metric-row">
                <span>Warehouse</span>
                <b>${i.warehouse || 'Multiple'}</b>
            </div>

            <div class="metric-row">
                <span>Quantity</span>
                <b>${Math.round(i.actual_qty)} ${i.stock_uom}</b>
            </div>

            <div class="metric-row">
                <span>Reorder</span>
                <b>${i.reorder_level}</b>
            </div>

            <div class="metric-row">
                <span>Days Left</span>
                <b>${days_remaining}</b>
            </div>

            <div class="metric-row ${isCritical ? 'status-critical' : 'status-healthy'}">
                <span>Status</span>
                <b>${isCritical ? 'Reorder Required' : 'Healthy'}</b>
            </div>

        </div>
        `;
    }).join("");

    $("#stock-cards-container").html(html);
}