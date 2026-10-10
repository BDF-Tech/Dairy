import re
import statistics
from collections import defaultdict

import frappe
from frappe.utils import flt, getdate, add_months, add_days, date_diff

# ---------------------------------------------------------------------------
# Loan Dashboard
#
# The business does NOT use the ERPNext Loan module - every loan / overdraft is
# just a GL account under the "Loans (Liabilities)" and "Bank OD A/c" trees. So
# the only facts the system actually holds are ledger movements. This dashboard
# is built entirely from `tabGL Entry`, which means:
#
#   * Outstanding, principal repaid, fresh disbursement and interest paid are
#     all REAL (they are what was posted).
#   * EMI amount, interest rate % and the next due date are NOT stored anywhere,
#     so we never pretend to know them. Instead we derive the closest honest
#     proxy from actual payments: the trailing-6-month average repayment
#     ("approx monthly outflow") and the date of the last principal repayment.
#
# The whole payload is assembled in a fixed handful of grouped queries no matter
# how many loans exist - there is no per-loan round trip.
# ---------------------------------------------------------------------------

# Group anchors are matched by account_name so the same code works across every
# company's chart of accounts (the numeric prefix / abbr suffix differ per co).
SECURED_NAMES = ("Secured Loans",)
UNSECURED_NAMES = ("Unsecured Loans",)
OD_NAMES = ("Bank OD A/c", "Bank Overdraft Account")
INTEREST_GROUP_NAMES = ("Bank Interest & Secured Loan Expense",)

# These groups are physically filed under the loan trees in the CoA but are NOT
# borrowings - they are in-transit clearing ledgers that net to zero over time.
# Their subtree is dropped so the loan totals reflect real debt, not settlements.
EXCLUDE_GROUP_NAMES = ("Temporary Settlement ledger",)


def _leaves_under(company, names, category):
	"""Return leaf accounts sitting under any group anchor named in `names`.

	Account is a nested set, so a group's whole subtree is exactly the accounts
	whose lft/rgt fall inside the anchor's range. An anchor that is itself a leaf
	(some companies keep "Secured Loans" as a single posting account) is returned
	as-is. Every returned row is tagged with `category` for the UI.
	"""
	anchors = frappe.get_all(
		"Account",
		filters={"company": company, "account_name": ["in", list(names)]},
		fields=["name", "lft", "rgt", "is_group"],
	)
	out = {}
	for a in anchors:
		if a.is_group:
			rows = frappe.get_all(
				"Account",
				filters={
					"company": company,
					"is_group": 0,
					"lft": [">=", a.lft],
					"rgt": ["<=", a.rgt],
				},
				fields=["name", "account_name", "account_number", "lft", "rgt"],
			)
		else:
			rows = frappe.get_all(
				"Account",
				filters={"name": a.name},
				fields=["name", "account_name", "account_number", "lft", "rgt"],
			)
		for r in rows:
			# First anchor wins if an account somehow matched twice.
			out.setdefault(r.name, {**r, "category": category})
	return list(out.values())


def _excluded_ranges(company):
	"""lft/rgt ranges of non-loan clearing groups filed under the loan trees."""
	return frappe.get_all(
		"Account",
		filters={"company": company, "is_group": 1, "account_name": ["in", list(EXCLUDE_GROUP_NAMES)]},
		fields=["lft", "rgt"],
	)


def _loan_accounts(company):
	"""All borrowing accounts (Secured, Unsecured, OD) for a company."""
	accts = []
	accts += _leaves_under(company, OD_NAMES, "OD")
	accts += _leaves_under(company, SECURED_NAMES, "Secured")
	accts += _leaves_under(company, UNSECURED_NAMES, "Unsecured")

	excl = _excluded_ranges(company)

	def is_excluded(a):
		return any(e.lft <= a["lft"] and a["rgt"] <= e.rgt for e in excl)

	# De-dupe keeping the earliest (OD > Secured > Unsecured) category, and drop
	# any account sitting inside a clearing-ledger subtree.
	seen, uniq = set(), []
	for a in accts:
		if a["name"] in seen or is_excluded(a):
			continue
		seen.add(a["name"])
		uniq.append(a)
	return uniq


def _interest_accounts(company):
	"""Loan / OD interest expense heads (excludes TDS and bank charges)."""
	rows = _leaves_under(company, INTEREST_GROUP_NAMES, "Interest")
	return [
		r for r in rows
		if "interest" in (r["account_name"] or "").lower()
		and "tds" not in (r["account_name"] or "").lower()
	]


def _sum_balance(company, accounts, upto=None, before=None):
	"""Cumulative closing balance (credit - debit) per account.

	`upto` -> posting_date <= upto ; `before` -> posting_date < before.
	Balance-sheet accounts carry forward, so the outstanding is simply the
	running total from inception. Positive = amount still owed.
	"""
	if not accounts:
		return {}
	cond, vals = "", {"company": company, "accts": tuple(accounts)}
	if upto:
		cond = "AND posting_date <= %(d)s"
		vals["d"] = upto
	elif before:
		cond = "AND posting_date < %(d)s"
		vals["d"] = before
	rows = frappe.db.sql(
		f"""
		SELECT account, SUM(credit) - SUM(debit) AS bal
		FROM `tabGL Entry`
		WHERE company = %(company)s AND is_cancelled = 0
		  AND account IN %(accts)s {cond}
		GROUP BY account
		""",
		vals,
		as_dict=True,
	)
	return {r.account: flt(r.bal) for r in rows}


def _movement(company, accounts, from_date, to_date):
	"""Per-account disbursed (credit), repaid (debit) and last-repayment inside
	the selected window."""
	if not accounts:
		return {}
	rows = frappe.db.sql(
		"""
		SELECT account,
			SUM(credit) AS disbursed,
			SUM(debit)  AS repaid,
			MAX(CASE WHEN debit > 0 THEN posting_date END) AS last_repayment
		FROM `tabGL Entry`
		WHERE company = %(company)s AND is_cancelled = 0
		  AND account IN %(accts)s
		  AND posting_date BETWEEN %(f)s AND %(t)s
		GROUP BY account
		""",
		{"company": company, "accts": tuple(accounts), "f": from_date, "t": to_date},
		as_dict=True,
	)
	return {r.account: r for r in rows}


def _trailing_repayment(company, accounts, to_date):
	"""Trailing-6-month repayments per account -> an honest 'approx monthly
	outflow' when no EMI schedule is stored, plus the true last-payment date
	regardless of the selected period."""
	if not accounts:
		return {}
	start = add_months(getdate(to_date), -6)
	rows = frappe.db.sql(
		"""
		SELECT account,
			SUM(debit) AS repaid6,
			MAX(CASE WHEN debit > 0 THEN posting_date END) AS last_repay
		FROM `tabGL Entry`
		WHERE company = %(company)s AND is_cancelled = 0
		  AND account IN %(accts)s
		  AND posting_date BETWEEN %(s)s AND %(t)s
		GROUP BY account
		""",
		{"company": company, "accts": tuple(accounts), "s": start, "t": to_date},
		as_dict=True,
	)
	return {r.account: {"avg_month": flt(r.repaid6) / 6.0, "last_repay": r.last_repay} for r in rows}


def _interest_in_period(company, accounts, from_date, to_date):
	"""Interest actually expensed per interest head in the window (debit - credit)."""
	if not accounts:
		return {}
	rows = frappe.db.sql(
		"""
		SELECT account, SUM(debit) - SUM(credit) AS amt
		FROM `tabGL Entry`
		WHERE company = %(company)s AND is_cancelled = 0
		  AND account IN %(accts)s
		  AND posting_date BETWEEN %(f)s AND %(t)s
		GROUP BY account
		""",
		{"company": company, "accts": tuple(accounts), "f": from_date, "t": to_date},
		as_dict=True,
	)
	return {r.account: flt(r.amt) for r in rows}


def _trend(company, loan_accts, interest_accts, to_date):
	"""Trailing 12 calendar months of principal repaid vs interest paid.

	Always trailing-12 ending at `to_date` (independent of the period filter) so
	the trend line stays readable even when the user picks a single month.
	"""
	all_accts = list(set(loan_accts) | set(interest_accts))
	if not all_accts:
		return {"labels": [], "repaid": [], "interest": []}
	start = add_days(add_months(getdate(to_date), -11), -(getdate(to_date).day - 1))
	loan_tuple = tuple(loan_accts) or ("",)
	int_tuple = tuple(interest_accts) or ("",)
	rows = frappe.db.sql(
		"""
		SELECT DATE_FORMAT(posting_date, '%%Y-%%m') AS ym,
			SUM(CASE WHEN account IN %(loans)s THEN debit ELSE 0 END) AS repaid,
			SUM(CASE WHEN account IN %(ints)s  THEN debit - credit ELSE 0 END) AS interest
		FROM `tabGL Entry`
		WHERE company = %(company)s AND is_cancelled = 0
		  AND account IN %(all)s
		  AND posting_date BETWEEN %(s)s AND %(t)s
		GROUP BY ym ORDER BY ym
		""",
		{
			"company": company,
			"loans": loan_tuple,
			"ints": int_tuple,
			"all": tuple(all_accts),
			"s": start,
			"t": to_date,
		},
		as_dict=True,
	)
	by_ym = {r.ym: r for r in rows}
	labels, repaid, interest = [], [], []
	cur = getdate(start)
	end = getdate(to_date)
	while cur <= end:
		ym = cur.strftime("%Y-%m")
		labels.append(cur.strftime("%b %y"))
		r = by_ym.get(ym)
		repaid.append(round(flt(r.repaid), 2) if r else 0)
		interest.append(round(flt(r.interest), 2) if r else 0)
		cur = add_months(cur, 1)
	return {"labels": labels, "repaid": repaid, "interest": interest}


def _emi_analysis(company, accounts, to_date):
	"""Infer each loan's EMI and payment regularity purely from the ledger.

	A repayment posts as a monthly debit to the loan account. So the recurring
	monthly debit IS the EMI (its principal part) - we detect it, the usual pay
	day, whether any month was skipped, and when the next one is due. No EMI
	schedule is stored anywhere; this is reverse-engineered from what was paid.

	Returns {account: {emi, day, months_paid, missed, varies, last_pay}}.
	Interest is intentionally ignored (pooled in shared heads, not per-loan).
	"""
	if not accounts:
		return {}
	start = getdate(add_months(getdate(to_date), -12)).replace(day=1)
	rows = frappe.db.sql(
		"""
		SELECT account, posting_date, debit
		FROM `tabGL Entry`
		WHERE company = %(company)s AND is_cancelled = 0
		  AND account IN %(accts)s AND debit > 0
		  AND posting_date BETWEEN %(s)s AND %(t)s
		""",
		{"company": company, "accts": tuple(accounts), "s": start, "t": to_date},
		as_dict=True,
	)

	# account -> month(YYYY-MM) -> {total, first_date}
	by_acc = defaultdict(lambda: defaultdict(lambda: {"total": 0.0, "day": None, "date": None}))
	for r in rows:
		d = getdate(r.posting_date)
		m = by_acc[r.account][d.strftime("%Y-%m")]
		m["total"] += flt(r.debit)
		if m["date"] is None or d < m["date"]:
			m["date"] = d
			m["day"] = d.day

	out = {}
	for acc, months in by_acc.items():
		keys = sorted(months.keys())
		totals = [months[k]["total"] for k in keys]
		days = [months[k]["day"] for k in keys if months[k]["day"]]
		recent = totals[-6:]
		# EMI = median of the recent monthly repayments (robust to the first
		# part-month and to the slow principal creep on reducing-balance loans).
		emi = round(statistics.median(recent), 2) if recent else 0
		day = int(statistics.median(sorted(days))) if days else None
		last_pay = max(months[k]["date"] for k in keys)

		# Gap check: months between the first and the last-due month that have no
		# payment. The current (possibly not-yet-due) month is excluded.
		first = getdate(keys[0] + "-01")
		cur = first
		last_due = getdate(to_date).replace(day=1)
		expected = 0
		while cur < last_due:
			expected += 1
			cur = add_months(cur, 1)
		missed = max(0, expected - len([k for k in keys if getdate(k + "-01") < last_due]))

		# Amount irregularity, ignoring the growing-principal trend: only flag if
		# the spread across recent months is wide.
		varies = len(recent) >= 3 and (max(recent) / max(min(recent), 1)) > 1.6

		out[acc] = {
			"emi": emi,
			"day": day,
			"months_paid": len(keys),
			"missed": missed,
			"varies": bool(varies),
			"last_pay": last_pay,
		}
	return out


# Plain-language buckets so a non-finance reader sees "Vehicle Loans" rather than
# a wall of registration numbers. Derived from the account name + category since
# the CoA has no explicit loan-type field.
_VEHICLE_HINTS = ("bolero", "eicher", "ashok leyland", "bada dost", "pickup",
	"truck", " pup", "maxi", "maxx", "tata ace", "vehicle")


def _loan_type(account_name, category):
	n = (account_name or "").lower()
	if category == "OD":
		return "Bank Overdraft"
	is_vehicle = any(k in n for k in _VEHICLE_HINTS) or re.search(r"cg[\s-]?\d", n)
	if is_vehicle:
		return "Vehicle Loans"
	if category == "Secured":
		return "Term & Equipment Loans"
	if "nagaria" in n or "current" in n or "hasmani" in n:
		return "Partner / Director Funds"
	return "Business Loans (NBFC / Bank)"


@frappe.whitelist()
def get_dashboard_data(from_date, to_date, company=None):
	"""Master endpoint: KPIs, composition, charts and one card per loan."""
	if not from_date or not to_date:
		frappe.throw("From Date and To Date are required.")
	if not company:
		company = frappe.defaults.get_user_default("Company") or frappe.db.get_default("company")

	loans = _loan_accounts(company)
	interest_accts = _interest_accounts(company)

	loan_names = [a["name"] for a in loans]
	int_names = [a["name"] for a in interest_accts]
	# OD is a revolving facility - its daily draw/repay churn is transaction flow,
	# not loan amortisation, so it is kept out of the repaid / disbursed metrics
	# and the trend (but stays in outstanding, composition and its own card).
	term_names = [a["name"] for a in loans if a["category"] != "OD"]

	closing = _sum_balance(company, loan_names, upto=to_date)
	opening = _sum_balance(company, loan_names, before=from_date)
	move = _movement(company, loan_names, from_date, to_date)
	trail = _trailing_repayment(company, term_names, to_date)
	interest_map = _interest_in_period(company, int_names, from_date, to_date)
	trend = _trend(company, term_names, int_names, to_date)
	emi = _emi_analysis(company, term_names, to_date)

	# ---- per-loan cards -------------------------------------------------
	cards = []
	cat_totals = {"Secured": 0.0, "Unsecured": 0.0, "OD": 0.0}
	total_out = 0.0
	for a in loans:
		acc = a["name"]
		revolving = a["category"] == "OD"
		out = flt(closing.get(acc, 0))
		total_out += out
		cat_totals[a["category"]] = cat_totals.get(a["category"], 0) + out
		mv = move.get(acc)
		tr = trail.get(acc, {})

		# EMI + regularity, only for true instalment loans (term / NBFC / vehicle).
		# OD is revolving; partner/director funds move in and out on no schedule -
		# an "EMI" for either would be meaningless, so both are skipped.
		lt = _loan_type(a["account_name"], a["category"])
		has_emi = not revolving and lt != "Partner / Director Funds"
		em = emi.get(acc, {}) if has_emi else {}
		emi_amount = flt(em.get("emi", 0)) if has_emi else 0
		emi_day = em.get("day") if has_emi else None
		last_pay = em.get("last_pay")
		next_due = None
		regularity = None
		if has_emi and abs(out) > 1 and last_pay and emi_amount > 0:
			nd = add_months(getdate(last_pay), 1)
			next_due = str(nd)
			overdue = getdate(nd) < getdate(to_date)
			if overdue or em.get("missed", 0) > 0:
				regularity = "off_track"      # a month missed or the next one is overdue
			elif em.get("varies"):
				regularity = "varies"         # amounts jump around
			else:
				regularity = "on_track"       # steady, no gaps

		cards.append({
			"account": acc,
			"account_name": (a["account_name"] or "").strip(),
			"account_number": a.get("account_number"),
			"category": a["category"],
			"loan_type": lt,
			"revolving": revolving,
			"outstanding": round(out, 2),
			"opening": round(flt(opening.get(acc, 0)), 2),
			"disbursed": round(flt(mv.disbursed), 2) if mv else 0,
			"repaid": round(flt(mv.repaid), 2) if mv else 0,
			# Meaningless for a revolving OD, so it is suppressed there.
			"approx_monthly": 0 if revolving else round(flt(tr.get("avg_month", 0)), 2),
			"last_repayment": str(tr.get("last_repay")) if tr.get("last_repay") else None,
			# Auto-detected EMI facts (term / NBFC loans only).
			"emi_amount": round(emi_amount, 2),
			"emi_day": emi_day,
			"next_due": next_due,
			"months_paid": em.get("months_paid", 0),
			"missed": em.get("missed", 0),
			"regularity": regularity,
		})

	# Active first (by outstanding desc), fully-repaid loans sink to the bottom.
	cards.sort(key=lambda c: c["outstanding"], reverse=True)

	# ---- interest breakdown --------------------------------------------
	interest_rows = sorted(
		(
			{"account_name": (a["account_name"] or "").strip(), "amount": round(flt(interest_map.get(a["name"], 0)), 2)}
			for a in interest_accts
		),
		key=lambda x: x["amount"], reverse=True,
	)
	total_interest = round(sum(x["amount"] for x in interest_rows), 2)

	# Amortisation headline covers term loans only (OD churn excluded above).
	total_repaid = round(sum(c["repaid"] for c in cards if not c["revolving"]), 2)
	total_disbursed = round(sum(c["disbursed"] for c in cards if not c["revolving"]), 2)
	active = len([c for c in cards if abs(c["outstanding"]) > 1])

	summary = {
		"total_outstanding": round(total_out, 2),
		"secured": round(cat_totals["Secured"], 2),
		"unsecured": round(cat_totals["Unsecured"], 2),
		"od": round(cat_totals["OD"], 2),
		"active_loans": active,
		"total_loans": len(cards),
		"interest_paid": total_interest,
		"principal_repaid": total_repaid,
		"disbursed": total_disbursed,
	}

	composition = {
		"labels": ["Secured", "Unsecured", "OD"],
		"values": [summary["secured"], summary["unsecured"], summary["od"]],
	}

	# Top loans by outstanding for the bar chart (skip zero balances).
	top = [c for c in cards if abs(c["outstanding"]) > 1][:12]
	outstanding_chart = {
		"labels": [c["account_name"] for c in top],
		"values": [c["outstanding"] for c in top],
	}

	# ---- plain-language "Loan Position" buckets ------------------------
	# One friendly row per loan type (Term / Vehicle / Business / OD ...),
	# the top-of-page summary a non-finance reader scans first.
	pos = {}
	for c in cards:
		if abs(c["outstanding"]) <= 1:
			continue
		g = pos.setdefault(c["loan_type"], {
			"loan_type": c["loan_type"],
			"revolving": c["revolving"],
			"outstanding": 0.0,
			"count": 0,
			"monthly": 0.0,
			"repaid": 0.0,
			"last_payment": None,
		})
		g["outstanding"] += c["outstanding"]
		g["count"] += 1
		g["monthly"] += flt(c["approx_monthly"])
		g["repaid"] += flt(c["repaid"])
		if c["last_repayment"] and (not g["last_payment"] or c["last_repayment"] > g["last_payment"]):
			g["last_payment"] = c["last_repayment"]
	position = sorted(
		(
			{**g, "outstanding": round(g["outstanding"], 2), "monthly": round(g["monthly"], 2), "repaid": round(g["repaid"], 2)}
			for g in pos.values()
		),
		key=lambda x: x["outstanding"], reverse=True,
	)

	return {
		"summary": summary,
		"position": position,
		"composition": composition,
		"outstanding_chart": outstanding_chart,
		"interest_breakdown": interest_rows,
		"trend": trend,
		"cards": cards,
		"company": company,
	}
