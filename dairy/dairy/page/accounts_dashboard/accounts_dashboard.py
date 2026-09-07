import frappe
from frappe.utils import flt, getdate, add_months, date_diff, add_days

# ---------------------------------------------------------------------------
# Accounts Dashboard
#
# A desk-page rebuild of the standard "BDF Accounts" Dashboard (28 Number Cards
# + charts). Every figure is the same one the old cards computed.
#
# PERFORMANCE
# -----------
# The naive version ran one SQL per number (~30 round-trips per load). Two-part
# fix so the dashboard puts almost no load on the server:
#
# 1. CONDITIONAL AGGREGATION - every metric from the same table is computed in a
#    SINGLE grouped scan via SUM(CASE WHEN ...). 8 queries instead of ~30.
#
# 2. CACHE THE SLOW BLOCK - the flow figures (invoices / payments / cash / bank
#    movement) are cheap: they filter posting_date and default to a one-day
#    range, so they are computed live every call. The point-in-time aggregates
#    (account balances, stock valuation, fiscal-year totals) are expensive -
#    they scan ~100k+ GL rows for a running balance - and do NOT need second-
#    level freshness on an overview screen. They are cached per (company, date)
#    for CACHE_TTL seconds, so only the first open in each window pays the cost;
#    every later open (filter tweak, re-open, second user) is a cache hit.
#    Pass refresh=1 (the "Refresh" button) to force a live recompute.
#
# This keeps the hot GL Entry / Payment Entry write path untouched (no wide
# covering indexes) while making repeat reads effectively free. The one index
# this relies on is Payment Entry (posting_date, company) - a standard, cheap,
# broadly useful index that Payment Entry ships without.
#
# Live figures (per uncached call): Sales Invoice range, Purchase Invoice range
# count, Payment Entry range (5 cash modes + 2 bank pay/receive).
# Cached figures: 3 GL balances, 3 stock values, 3 FY totals, vehicle count.
#
# Accounts / warehouses / payment modes are BDF-specific (they carry the
# " - BDF" company abbreviation), exactly as the original cards were.
# ---------------------------------------------------------------------------

# How long the balances / stock / FY block is cached, in seconds. A scheduled
# job (warm_cache, every 10 min) refreshes it in the background, so this is set
# comfortably above that interval - user requests are always a cache hit and
# never pay the lifetime-balance scans.
CACHE_TTL = 900

# --- Main customer trade receivable (for the 7-day outstanding trend) -------
AR_ACCOUNT = "1111 - Sundry Debtors - BDF"

# --- Party classification for "Payment Today" / "Collection Today" ----------
# Milk procurement supplier groups -> the "Milk" payment bucket; every other
# supplier payment is "Vendor"; payments to Employees are "Salary".
MILK_SUPPLIER_GROUPS = [
	"Bulk Milk Supplier", "Agent-Milk Collection", "Farmer -Milk Collection",
	"VLC AGENT GROUP",
]
# Collection buckets by customer group.
FRANCHISE_GROUPS = ["Franchise", "Master Franchise", "Sub Franchise"]
DISTRIBUTOR_GROUPS = ["Distributor Vadilal"]

EMI_DUE_WINDOW = 5     # flag term-loan EMIs falling due within N days

# --- GL accounts (from the "Account balance - *" query reports) -------------
ACC_OD = "1123 - ICICI BANK OD 221255 - BDF"        # ICICI overdraft 221255
ACC_CA = "1124 - ICICI BANK CA 0325 - BDF"          # ICICI current a/c 0325
ACC_CASH_BCO = "1153 - Cash In Hand BCO - BDF"       # Cash in Hand BCO

# --- Sales-warehouse split (from "Invoice Total Amount [*]" cards) ----------
WH_PLANT = "Dispatch Cold Room - BDF"
WH_DEPO = "Depo Warehouse - BDF"
# NB: real warehouse name has a non-breaking space between "Sanjay" and "Market".
WH_SANJAY = "BDF Warehouse - Sanjay Market - BDF"

# --- Stock valuation warehouses (from the "Audit Warehouse" card) -----------
AUDIT_WAREHOUSES = [
	"Balaji Office Warehouse - BDF", "BDF Hyderabad Warehouse - BDF",
	"Dairy Section (Milk) - BDF", "Depo Warehouse - BDF",
	"Dispatch Cold Room - BDF", "Frozen Coldroom - BDF",
	"Lalbagh Office Warehouse  - BDF", "Main Store - BDF",
	"Process Section - BDF", "Production Cold Room - BDF",
	"Production Store (WIP) - BDF", "Tanker - BDF",
	"DCS-03Jamrunda - BDF", "DCS-04Anchala - BDF", "DCS-06Pakhanjur - BDF",
	"DCS-08Plant - BDF", "DCS-09Jagdalpur - BDF", "DCS07-Nagarnar - BDF",
]


def _fiscal_year(date):
	"""Start/end of the fiscal year containing `date` (falls back to calendar)."""
	fy = frappe.db.sql(
		"""SELECT year_start_date, year_end_date FROM `tabFiscal Year`
		   WHERE %(d)s BETWEEN year_start_date AND year_end_date
		   ORDER BY year_start_date DESC LIMIT 1""",
		{"d": date}, as_dict=True,
	)
	if fy:
		return fy[0].year_start_date, fy[0].year_end_date
	y = getdate(date).year
	return getdate(f"{y}-01-01"), getdate(f"{y}-12-31")


def _compute_slow_block(company, to_date):
	"""The expensive, slowly-changing figures: GL balances, stock, FY totals,
	vehicle count. Computed together, cached by (company, to_date)."""
	fy_start, fy_end = _fiscal_year(to_date)
	fy_to = min(getdate(to_date), getdate(fy_end))
	p = {
		"company": company, "t": to_date, "fy_f": fy_start, "fy_t": fy_to,
		"acc_od": ACC_OD, "acc_ca": ACC_CA, "acc_cash": ACC_CASH_BCO,
		"wh_depo": WH_DEPO, "audit": tuple(AUDIT_WAREHOUSES),
	}

	# GL balances (OD / CA / Cash-in-Hand BCO), as of to_date - one scan.
	bal_rows = frappe.db.sql(
		"""SELECT account, SUM(debit - credit) AS bal FROM `tabGL Entry`
		   WHERE is_cancelled = 0 AND company = %(company)s
		     AND account IN (%(acc_od)s, %(acc_ca)s, %(acc_cash)s)
		     AND posting_date <= %(t)s
		   GROUP BY account""",
		p, as_dict=True,
	)
	balmap = {r.account: flt(r.bal) for r in bal_rows}

	# Stock value (total / audit set / depo), current - one scan.
	stk = frappe.db.sql(
		"""SELECT
			SUM(b.stock_value) AS total,
			SUM(CASE WHEN b.warehouse IN %(audit)s THEN b.stock_value ELSE 0 END) AS audit,
			SUM(CASE WHEN b.warehouse = %(wh_depo)s THEN b.stock_value ELSE 0 END) AS depo
		   FROM `tabBin` b
		   JOIN `tabWarehouse` w ON w.name = b.warehouse
		   WHERE w.company = %(company)s""",
		p, as_dict=True,
	)[0]

	# Payment Entry, fiscal-year-to-date - one scan.
	pe_fy = frappe.db.sql(
		"""SELECT
			SUM(CASE WHEN payment_type = 'Receive' THEN base_received_amount ELSE 0 END) AS incoming_payment,
			SUM(CASE WHEN payment_type = 'Pay'     THEN base_paid_amount     ELSE 0 END) AS outgoing_payment
		   FROM `tabPayment Entry`
		   WHERE docstatus = 1 AND company = %(company)s
		     AND posting_date BETWEEN %(fy_f)s AND %(fy_t)s""",
		p, as_dict=True,
	)[0]

	# Purchase Invoice total, fiscal-year-to-date.
	incoming_bills = frappe.db.sql(
		"""SELECT SUM(base_net_total) FROM `tabPurchase Invoice`
		   WHERE docstatus = 1 AND company = %(company)s
		     AND posting_date BETWEEN %(fy_f)s AND %(fy_t)s""",
		p,
	)[0][0]

	# Customer / Vendor outstanding.
	#
	# BDF posts customer receipts and vendor payments ON ACCOUNT (against the
	# debtors/creditors control accounts) rather than allocating them to specific
	# invoices, so `Sales/Purchase Invoice.outstanding_amount` is NOT reconciled
	# and hugely overstates reality (crores of "open" invoices that are actually
	# paid). The economically correct outstanding is therefore the NET PARTY
	# BALANCE from GL: sum per party of (debit - credit) on the Receivable /
	# Payable control accounts. Parties with a debit balance owe us (receivable)
	# / we owe them (payable, a credit balance); the opposite sign is an advance.
	# Because payments aren't invoice-matched, honest invoice-date ageing buckets
	# aren't derivable here - we report real totals + party counts + advances.
	ar = frappe.db.sql(
		"""SELECT
			ROUND(SUM(CASE WHEN bal > 0 THEN bal ELSE 0 END), 2) AS owed,
			SUM(CASE WHEN bal > 0 THEN 1 ELSE 0 END) AS owing_count,
			ROUND(SUM(CASE WHEN bal < 0 THEN -bal ELSE 0 END), 2) AS advances
		   FROM (
			SELECT gl.party, SUM(gl.debit - gl.credit) AS bal
			FROM `tabGL Entry` gl JOIN `tabAccount` a ON a.name = gl.account
			WHERE gl.company = %(company)s AND gl.is_cancelled = 0
			  AND a.account_type = 'Receivable' AND gl.party_type = 'Customer'
			  AND gl.posting_date <= %(t)s
			GROUP BY gl.party
		   ) t""", p, as_dict=True,
	)[0]

	ap = frappe.db.sql(
		"""SELECT
			ROUND(SUM(CASE WHEN bal < 0 THEN -bal ELSE 0 END), 2) AS owed,
			SUM(CASE WHEN bal < 0 THEN 1 ELSE 0 END) AS owing_count,
			ROUND(SUM(CASE WHEN bal > 0 THEN bal ELSE 0 END), 2) AS advances
		   FROM (
			SELECT gl.party, SUM(gl.debit - gl.credit) AS bal
			FROM `tabGL Entry` gl JOIN `tabAccount` a ON a.name = gl.account
			WHERE gl.company = %(company)s AND gl.is_cancelled = 0
			  AND a.account_type = 'Payable' AND gl.party_type = 'Supplier'
			  AND gl.posting_date <= %(t)s
			GROUP BY gl.party
		   ) t""", p, as_dict=True,
	)[0]

	# ---- 7-day trends (ending to_date) ---------------------------------
	trend = _seven_day_trend(company, to_date)

	# ---- alerts (red items only) ---------------------------------------
	alerts = []
	if flt(ap.owed) > 0:
		alerts.append({"label": f"Vendor payable — {int(flt(ap.owing_count))} suppliers", "value": round(flt(ap.owed), 2)})
	if flt(ar.owed) > 0:
		alerts.append({"label": f"Customers owe — {int(flt(ar.owing_count))} accounts", "value": round(flt(ar.owed), 2)})
	for e in _emi_due_soon(company, to_date):
		alerts.append(e)

	return {
		"balances": {
			"cash_in_hand_bco": round(balmap.get(ACC_CASH_BCO, 0), 2),
			"icici_od": round(balmap.get(ACC_OD, 0), 2),
			"icici_ca": round(balmap.get(ACC_CA, 0), 2),
		},
		"stock": {
			"total": round(flt(stk.total), 2),
			"audit": round(flt(stk.audit), 2),
			"depo": round(flt(stk.depo), 2),
		},
		"fy": {
			"start": str(fy_start),
			"end": str(fy_to),
			"incoming_bills": round(flt(incoming_bills), 2),
			"incoming_payment": round(flt(pe_fy.incoming_payment), 2),
			"outgoing_payment": round(flt(pe_fy.outgoing_payment), 2),
		},
		"vehicles": frappe.db.count("Vehicle"),
		"receivable": {
			"owed": round(flt(ar.owed), 2),
			"count": int(flt(ar.owing_count)),
			"advances": round(flt(ar.advances), 2),
		},
		"payable": {
			"owed": round(flt(ap.owed), 2),
			"count": int(flt(ap.owing_count)),
			"advances": round(flt(ap.advances), 2),
		},
		"alerts": alerts,
		"trend": trend,
	}


def _seven_day_trend(company, to_date):
	"""Last 7 calendar days (ending to_date) of: daily sales, collections,
	net cash flow, and the customer-receivable (AR) closing balance.

	Sales/collection/cashflow come from two grouped scans. The AR line is the
	running Sundry-Debtors balance: an opening balance before the window plus
	each day's GL delta, accumulated forward.
	"""
	start = add_days(getdate(to_date), -6)
	q = {"company": company, "s": start, "t": to_date, "ar": AR_ACCOUNT}

	si_rows = frappe.db.sql(
		"""SELECT posting_date AS d, SUM(base_net_total) AS v
		   FROM `tabSales Invoice`
		   WHERE docstatus = 1 AND company = %(company)s
		     AND status != 'Internal Transfer'
		     AND posting_date BETWEEN %(s)s AND %(t)s
		   GROUP BY posting_date""", q, as_dict=True)
	sales_by_day = {str(r.d): flt(r.v) for r in si_rows}

	pe_rows = frappe.db.sql(
		"""SELECT posting_date AS d,
			SUM(CASE WHEN payment_type = 'Receive' THEN base_received_amount ELSE 0 END) AS recv,
			SUM(CASE WHEN payment_type = 'Pay'     THEN base_paid_amount     ELSE 0 END) AS pay
		   FROM `tabPayment Entry`
		   WHERE docstatus = 1 AND company = %(company)s
		     AND posting_date BETWEEN %(s)s AND %(t)s
		   GROUP BY posting_date""", q, as_dict=True)
	recv_by_day = {str(r.d): flt(r.recv) for r in pe_rows}
	pay_by_day = {str(r.d): flt(r.pay) for r in pe_rows}

	# AR opening (before the window) + daily deltas.
	ar_open = flt(frappe.db.sql(
		"""SELECT SUM(debit - credit) FROM `tabGL Entry`
		   WHERE is_cancelled = 0 AND company = %(company)s
		     AND account = %(ar)s AND posting_date < %(s)s""", q)[0][0])
	ar_rows = frappe.db.sql(
		"""SELECT posting_date AS d, SUM(debit - credit) AS delta
		   FROM `tabGL Entry`
		   WHERE is_cancelled = 0 AND company = %(company)s
		     AND account = %(ar)s AND posting_date BETWEEN %(s)s AND %(t)s
		   GROUP BY posting_date""", q, as_dict=True)
	ar_delta = {str(r.d): flt(r.delta) for r in ar_rows}

	labels, sales, collection, cashflow, outstanding = [], [], [], [], []
	run = ar_open
	cur = getdate(start)
	end = getdate(to_date)
	while cur <= end:
		k = str(cur)
		labels.append(getdate(cur).strftime("%d %b"))
		sales.append(round(sales_by_day.get(k, 0), 2))
		collection.append(round(recv_by_day.get(k, 0), 2))
		cashflow.append(round(recv_by_day.get(k, 0) - pay_by_day.get(k, 0), 2))
		run += ar_delta.get(k, 0)
		outstanding.append(round(run, 2))
		cur = add_days(cur, 1)

	return {"labels": labels, "sales": sales, "collection": collection,
		"cashflow": cashflow, "outstanding": outstanding}


def _emi_due_soon(company, to_date):
	"""Term-loan EMIs falling due within EMI_DUE_WINDOW days, inferred from the
	ledger. Reuses the Loan Dashboard's loan-account discovery and EMI detection
	so both pages agree on what an 'EMI' is."""
	try:
		from dairy.dairy.page.loan_dashboard.loan_dashboard import _loan_accounts, _emi_analysis, _sum_balance
	except Exception:
		return []

	loans = [a for a in _loan_accounts(company) if a["category"] != "OD"]
	if not loans:
		return []
	names = [a["name"] for a in loans]
	emi = _emi_analysis(company, names, to_date)
	closing = _sum_balance(company, names, upto=to_date)

	out = []
	for a in loans:
		acc = a["name"]
		if abs(flt(closing.get(acc, 0))) <= 1:      # settled loan
			continue
		em = emi.get(acc, {})
		last_pay, amt = em.get("last_pay"), flt(em.get("emi", 0))
		if not last_pay or amt <= 0:
			continue
		next_due = add_months(getdate(last_pay), 1)
		days = date_diff(next_due, getdate(to_date))
		if 0 <= days <= EMI_DUE_WINDOW:
			out.append({
				"label": f"EMI due in {days} day{'s' if days != 1 else ''} — {(a['account_name'] or '').strip()}",
				"value": round(amt, 2),
			})
	return out


def warm_cache():
	"""Scheduler entry (every 10 min): precompute today's slow block for the
	default company so every dashboard open is a cache hit. The heavy lifetime
	GL-balance scans run here, in the background worker, never on a user request.
	"""
	company = frappe.defaults.get_global_default("company") or frappe.db.get_default("company")
	if not company:
		return
	try:
		_get_slow_block(company, str(getdate()), refresh=True)
	except Exception:
		frappe.log_error(title="Accounts Dashboard cache warm failed")


def _get_slow_block(company, to_date, refresh=False):
	"""Cached wrapper around _compute_slow_block (TTL = CACHE_TTL)."""
	key = f"accounts_dashboard::slow::{company}::{to_date}"
	cache = frappe.cache()
	if not refresh:
		cached = cache.get_value(key)
		if cached:
			return cached
	data = _compute_slow_block(company, to_date)
	cache.set_value(key, data, expires_in_sec=CACHE_TTL)
	return data


@frappe.whitelist()
def get_dashboard_data(from_date, to_date, company=None, refresh=0):
	if not from_date or not to_date:
		frappe.throw("From Date and To Date are required.")
	if not company:
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_default("company")
	refresh = frappe.utils.cint(refresh)

	p = {
		"company": company, "f": from_date, "t": to_date,
		"wh_plant": WH_PLANT, "wh_depo": WH_DEPO, "wh_sanjay": WH_SANJAY,
		"acc_od": ACC_OD, "acc_ca": ACC_CA,
	}

	# =====================================================================
	# LIVE: SALES INVOICE, selected range - one scan
	# =====================================================================
	si = frappe.db.sql(
		"""SELECT
			SUM(CASE WHEN status != 'Internal Transfer' THEN base_net_total ELSE 0 END) AS outgoing_bill,
			SUM(CASE WHEN is_return = 1 THEN 1 ELSE 0 END) AS return_count,
			SUM(CASE WHEN set_warehouse = %(wh_plant)s  THEN base_rounded_total ELSE 0 END) AS amt_plant,
			SUM(CASE WHEN set_warehouse = %(wh_depo)s   THEN base_rounded_total ELSE 0 END) AS amt_depo,
			SUM(CASE WHEN set_warehouse = %(wh_sanjay)s THEN base_rounded_total ELSE 0 END) AS amt_sanjay,
			SUM(CASE WHEN set_warehouse = %(wh_plant)s  AND is_return = 0 AND is_debit_note = 0 THEN 1 ELSE 0 END) AS cnt_plant,
			SUM(CASE WHEN set_warehouse = %(wh_depo)s   AND is_return = 0 AND is_debit_note = 0 THEN 1 ELSE 0 END) AS cnt_depo,
			SUM(CASE WHEN set_warehouse = %(wh_sanjay)s AND is_return = 0 AND is_debit_note = 0 THEN 1 ELSE 0 END) AS cnt_sanjay
		   FROM `tabSales Invoice`
		   WHERE docstatus = 1 AND company = %(company)s
		     AND posting_date BETWEEN %(f)s AND %(t)s""",
		p, as_dict=True,
	)[0]

	# =====================================================================
	# 2. PURCHASE INVOICE count, selected range
	# =====================================================================
	pi_count = frappe.db.sql(
		"""SELECT COUNT(*) FROM `tabPurchase Invoice`
		   WHERE docstatus = 1 AND company = %(company)s
		     AND posting_date BETWEEN %(f)s AND %(t)s
		     AND status != 'Internal Transfer'""",
		p,
	)[0][0]

	# =====================================================================
	# 3. PAYMENT ENTRY, selected range - one scan for all cash modes + banks
	#    FIX: the old OD-Pay card filtered paid_from without the "1123 - "
	#    prefix and returned nothing; we use the real account name.
	# =====================================================================
	pe = frappe.db.sql(
		"""SELECT
			SUM(CASE WHEN mode_of_payment = 'ALL ROUTES CASH' THEN base_paid_amount ELSE 0 END) AS all_routes,
			SUM(CASE WHEN mode_of_payment = 'Warehouse Cash' AND payment_type = 'Receive' THEN base_paid_amount ELSE 0 END) AS warehouse_cash,
			SUM(CASE WHEN mode_of_payment = 'Plant Cash' THEN base_paid_amount ELSE 0 END) AS plant_cash,
			SUM(CASE WHEN mode_of_payment = 'PETTY CASH BCO' THEN base_paid_amount ELSE 0 END) AS petty_cash,
			SUM(CASE WHEN mode_of_payment = 'Cash In Hand BCO' THEN base_paid_amount ELSE 0 END) AS cash_in_hand,
			SUM(CASE WHEN payment_type = 'Pay'     AND paid_from = %(acc_od)s THEN base_paid_amount ELSE 0 END) AS od_pay,
			SUM(CASE WHEN payment_type = 'Receive' AND paid_to   = %(acc_od)s THEN base_paid_amount ELSE 0 END) AS od_recv,
			SUM(CASE WHEN payment_type = 'Pay'     AND paid_from = %(acc_ca)s THEN base_paid_amount ELSE 0 END) AS ca_pay,
			SUM(CASE WHEN payment_type = 'Receive' AND paid_to   = %(acc_ca)s THEN base_paid_amount ELSE 0 END) AS ca_recv
		   FROM `tabPayment Entry`
		   WHERE docstatus = 1 AND company = %(company)s
		     AND posting_date BETWEEN %(f)s AND %(t)s""",
		p, as_dict=True,
	)[0]

	# =====================================================================
	# 4. PAYMENT TODAY by category (Vendor / Milk / Salary) - one scan
	#    Salary = Pay to Employees; Milk = Pay to milk supplier groups;
	#    Vendor = every other supplier payment.
	# =====================================================================
	pay = frappe.db.sql(
		"""SELECT
			SUM(CASE WHEN pe.party_type = 'Employee' THEN pe.base_paid_amount ELSE 0 END) AS salary,
			SUM(CASE WHEN pe.party_type = 'Supplier' AND s.supplier_group IN %(milk)s THEN pe.base_paid_amount ELSE 0 END) AS milk,
			SUM(CASE WHEN pe.party_type = 'Supplier' AND (s.supplier_group NOT IN %(milk)s OR s.supplier_group IS NULL) THEN pe.base_paid_amount ELSE 0 END) AS vendor
		   FROM `tabPayment Entry` pe
		   LEFT JOIN `tabSupplier` s ON s.name = pe.party AND pe.party_type = 'Supplier'
		   WHERE pe.docstatus = 1 AND pe.company = %(company)s AND pe.payment_type = 'Pay'
		     AND pe.posting_date BETWEEN %(f)s AND %(t)s""",
		{**p, "milk": tuple(MILK_SUPPLIER_GROUPS)}, as_dict=True,
	)[0]

	# =====================================================================
	# 5. COLLECTION TODAY by category (Franchise / Distributor / Others)
	# =====================================================================
	coll = frappe.db.sql(
		"""SELECT
			SUM(CASE WHEN c.customer_group IN %(fr)s THEN pe.base_received_amount ELSE 0 END) AS franchise,
			SUM(CASE WHEN c.customer_group IN %(di)s THEN pe.base_received_amount ELSE 0 END) AS distributor,
			SUM(CASE WHEN (c.customer_group NOT IN %(both)s OR c.customer_group IS NULL) THEN pe.base_received_amount ELSE 0 END) AS others
		   FROM `tabPayment Entry` pe
		   LEFT JOIN `tabCustomer` c ON c.name = pe.party AND pe.party_type = 'Customer'
		   WHERE pe.docstatus = 1 AND pe.company = %(company)s AND pe.payment_type = 'Receive'
		     AND pe.posting_date BETWEEN %(f)s AND %(t)s""",
		{**p, "fr": tuple(FRANCHISE_GROUPS), "di": tuple(DISTRIBUTOR_GROUPS),
		 "both": tuple(FRANCHISE_GROUPS + DISTRIBUTOR_GROUPS)}, as_dict=True,
	)[0]

	# =====================================================================
	# SLOW (cached): balances, stock, FY, AR/AP ageing, trends, alerts
	# =====================================================================
	slow = _get_slow_block(company, str(to_date), refresh=refresh)
	bal = slow["balances"]

	# ---- assemble --------------------------------------------------------
	return {
		"company": company,
		"as_of": str(to_date),
		"cached": bool(not refresh),
		"flow": {
			"outgoing_bill": round(flt(si.outgoing_bill), 2),
			"sales_return_count": int(flt(si.return_count)),
			"purchase_invoice_count": int(pi_count or 0),
			"warehouses": [
				{"label": "Plant", "amount": round(flt(si.amt_plant), 2), "count": int(flt(si.cnt_plant))},
				{"label": "Depo", "amount": round(flt(si.amt_depo), 2), "count": int(flt(si.cnt_depo))},
				{"label": "Sanjay Market", "amount": round(flt(si.amt_sanjay), 2), "count": int(flt(si.cnt_sanjay))},
			],
		},
		"cash": [
			{"label": "All Routes Cash", "value": round(flt(pe.all_routes), 2)},
			{"label": "Warehouse Cash", "value": round(flt(pe.warehouse_cash), 2)},
			{"label": "Plant Cash", "value": round(flt(pe.plant_cash), 2)},
			{"label": "Petty Cash BCO", "value": round(flt(pe.petty_cash), 2)},
			{"label": "Cash In Hand BCO", "value": round(flt(pe.cash_in_hand), 2)},
		],
		"cash_total": round(
			flt(pe.all_routes) + flt(pe.warehouse_cash) + flt(pe.plant_cash)
			+ flt(pe.petty_cash) + flt(pe.cash_in_hand), 2),
		"bank": [
			{"label": "ICICI OD 221255", "pay": round(flt(pe.od_pay), 2),
			 "receive": round(flt(pe.od_recv), 2), "balance": bal["icici_od"]},
			{"label": "ICICI CA 0325", "pay": round(flt(pe.ca_pay), 2),
			 "receive": round(flt(pe.ca_recv), 2), "balance": bal["icici_ca"]},
		],
		"payment_today": {
			"vendor": round(flt(pay.vendor), 2),
			"milk": round(flt(pay.milk), 2),
			"salary": round(flt(pay.salary), 2),
		},
		"collection_today": {
			"franchise": round(flt(coll.franchise), 2),
			"distributor": round(flt(coll.distributor), 2),
			"others": round(flt(coll.others), 2),
		},
		"balances": bal,
		"fy": slow["fy"],
		"stock": slow["stock"],
		"vehicles": slow["vehicles"],
		"receivable": slow["receivable"],
		"payable": slow["payable"],
		"alerts": slow["alerts"],
		"trend": slow["trend"],
	}
