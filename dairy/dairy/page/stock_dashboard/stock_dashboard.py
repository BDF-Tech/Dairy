import frappe
from frappe import _

@frappe.whitelist()
def get_stock_data(
    warehouse=None,
    item_code=None,
    item_group=None,
    stock_status="All",   # NEW FILTER
    sort_order="asc"
):

    # ----------------------------
    # Safety
    # ----------------------------
    if sort_order not in ["asc", "desc"]:
        sort_order = "asc"

    if not frappe.has_permission("Bin", "read"):
        frappe.throw(_("Not permitted"), frappe.PermissionError)

    lft, rgt = None, None

    # ----------------------------
    # Item Group Tree Handling
    # ----------------------------
    if item_group:
        group_info = frappe.db.get_value(
            "Item Group",
            item_group,
            ["lft", "rgt"],
            as_dict=True
        )
        if group_info:
            lft, rgt = group_info.lft, group_info.rgt

    # ----------------------------
    # Main Query
    # ----------------------------
    query = """
        SELECT 
            b.item_code,
            i.item_name,
            b.warehouse,
            SUM(b.actual_qty) as actual_qty,
            i.stock_uom,
            i.item_group,
            i.custom_no_of_days,
            COALESCE(MAX(r.warehouse_reorder_level), 0) as reorder_level
        FROM `tabBin` b
        JOIN `tabItem` i ON b.item_code = i.name
        LEFT JOIN `tabItem Reorder` r
            ON r.parent = b.item_code
            AND r.warehouse = b.warehouse
        WHERE b.actual_qty != 0
    """

    conditions = []
    values = {}

    if warehouse:
        conditions.append("b.warehouse = %(warehouse)s")
        values["warehouse"] = warehouse

    if item_code:
        conditions.append("b.item_code = %(item_code)s")
        values["item_code"] = item_code

    if lft and rgt:
        conditions.append("""
            i.item_group IN (
                SELECT name FROM `tabItem Group`
                WHERE lft >= %(lft)s AND rgt <= %(rgt)s
            )
        """)
        values.update({"lft": lft, "rgt": rgt})

    if conditions:
        query += " AND " + " AND ".join(conditions)

    query += """
        GROUP BY b.item_code, b.warehouse
    """

    # ----------------------------
    # Stock Status Filter
    # ----------------------------
    if stock_status == "Critical":
        query += " HAVING actual_qty <= reorder_level"
    elif stock_status == "Healthy":
        query += " HAVING actual_qty > reorder_level"

    query += f" ORDER BY actual_qty {sort_order}"

    return frappe.db.sql(query, values, as_dict=True)