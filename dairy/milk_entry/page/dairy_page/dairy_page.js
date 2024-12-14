frappe.pages['dairy-page'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: 'Dairy',
		single_column: true
	});

	wrapper.dairy_page = new erpnext.dairy(wrapper);

	frappe.breadcrumbs.add("Dairy");
}


//frappe.pages['sales-funnel'].on_page_load = function(wrapper) {
//	frappe.ui.make_app_page({
//		parent: wrapper,
//		title: __('Sales Funnel'),
//		single_column: true
//	});
//
//	wrapper.sales_funnel = new erpnext.SalesFunnel(wrapper);
//
//	frappe.breadcrumbs.add("Selling");
//}