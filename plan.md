# Crate Tracking Module — Build Plan

**App:** `dairy`
**Module:** `dairy` (dairy/dairy/)
**Status:** Phase 3C + Audit Report + Mobile Delivery + Warehouse Crates + GPS Capture + Material Gate Pass
**Last Updated:** 2026-07-02

---

## Production Deployment Checklist — Custom Fields

These fields were added via **Customize Form** or **bench console** on the dev site.
You must recreate them on prod before running `bench migrate`.

| # | Doctype | Fieldname | Type | Options | How Added | Notes |
|---|---|---|---|---|---|---|
| 1 | Driver | `custom_invoice_crate_balance` | Float | — | Customize Form | Read Only. Running total of invoice crates physically with driver. |
| 2 | Driver | `custom_crate_type_balances` | Table | Driver Crate Type Balance | Customize Form | Child table for per-type loose crate balance. Child doctype is in code. |
| 3 | Driver | `custom_user` | Link | User | bench console | Links driver's Frappe login to their Driver record. Used by app to identify driver. |
| 4 | Customer | `custom_current_crate_balance` | Float | — | Customize Form | Read Only. Running crate balance owed by customer to the plant. |
| 5 | Sales Invoice | `custom_vehicle_movement_log` | Link | Vehicle Movement Log | Customize Form | Links invoice to its dispatch trip. Set at Gate Check via db.set_value. |
| 6 | Stock Entry | `van_collection_item` | Link | Vehicle Movement Log | Customize Form | Links stock entry to its dispatch trip. Set at Gate Check via db.set_value. |
| 7 | Sales Invoice | `custom_pickup_log` | Link | Pickup Log | Customize Form | Links invoice to its pickup entry. Set at submit via db.set_value. Read Only, No Copy. |
| 8 | Warehouse | `custom_crate_section` | Section Break | — | bench console (create_custom_fields) | Collapsible "Crate Balance" section, inserted after `warehouse_name`. |
| 9 | Warehouse | `custom_crate_balance` | Float | — | bench console (create_custom_fields) | Total crates maintained at the warehouse (e.g. plant pool). Inserted after `custom_crate_section`. |
| 10 | Warehouse | `custom_crate_type_balances` | Table | Driver Crate Type Balance | bench console (create_custom_fields) | Per-crate-type loose balance for the warehouse. Reuses the Driver child doctype. Inserted after `custom_crate_balance`. |

> **All fields above (rows 1–10) were added via Customize Form / bench console and must be manually recreated on prod BEFORE running bench migrate.**

**Prod recreation script for rows 8–10 (Warehouse) — run in `bench --site <prod> console`:**
```python
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
create_custom_fields({
    "Warehouse": [
        {"fieldname": "custom_crate_section", "label": "Crate Balance",
         "fieldtype": "Section Break", "insert_after": "warehouse_name", "collapsible": 1},
        {"fieldname": "custom_crate_balance", "label": "Crate Balance",
         "fieldtype": "Float", "insert_after": "custom_crate_section",
         "description": "Total crates maintained at this warehouse."},
        {"fieldname": "custom_crate_type_balances", "label": "Loose Crate Balances",
         "fieldtype": "Table", "options": "Driver Crate Type Balance",
         "insert_after": "custom_crate_balance"},
    ]
}, ignore_validate=True)
frappe.db.commit()
```

> **How to recreate on prod:** Go to Customize Form → select the Doctype → add field → Save → bench migrate.
> Fields added via bench console (row 3) must be recreated the same way on prod.

### Frappe Roles to Create on Prod

These roles must be created in Frappe → Role List before any app user can log in.

| Role Name | Who gets it | App Access | Status |
|---|---|---|---|
| `Dairy Driver` | Driver mobile users | Driver home, trip detail, crate delivery | ✅ Created |
| `Dairy Dispatch` | Dispatch / gate staff | All VMLs, driver balances | ✅ Created |
| `Dairy Production` | Production planning team | Crate summary | ✅ Created |
| `Master User` | Owner / all-access admin | Everything | ✅ Created |
| `Customer` | Customer portal users (already exists in Frappe) | Orders, invoices, crate balance | ✅ Already exists |

**Step 1 — Create roles (do once on each site: dev + prod):**
1. Go to `Role List` → click **New**
2. Enter Role Name exactly as shown above → Save
3. All 5 roles are now created on dev site ✅

**Step 2 — Assign role to a user:**
1. Go to `User List` → open the user
2. Go to the **Roles** tab → click Add Row → select the role → Save

**Step 3 — For Driver users only (extra step):**
After assigning `Dairy Driver` role to a user, you must also link that user to their Driver record:
1. Go to `Driver List` → open the Driver
2. Find the `custom_user` field → select the Frappe user → Save

> Without step 3, the driver will be able to login but the app will show "No Driver linked" error.

---

## Guiding Principles

- Single system: Vehicle Movement Log + Customer Crate Ledger only. Old Gate Pass / Crate Log system is not touched.
- Lightweight: Customer carries a `custom_current_crate_balance` field — balance is maintained in real-time, never aggregated on-the-fly.
- Driver carries `custom_invoice_crate_balance` and per-type loose crate balance — same real-time principle.
- No over-engineering: v1 covers the core loop. Real-world feedback drives v2.
- All logic lives in the `dairy` app inside `dairy/dairy/`.

---

## Business Rules

1. Crate balance cannot go negative per customer.
2. Partial returns are allowed (customer can return fewer crates than they received).
3. A Sales Invoice linked to a VML cannot be cancelled while the VML is active.
4. Plant pickup (customer collects directly) bypasses vehicle/driver logic via Crate Pickup Entry.
5. UOM for all crate transactions = "Crate".
6. All ledger entries are idempotent — guard checks prevent duplicate entries.
7. A vehicle already Out cannot be assigned to another trip.
8. At Gate Check, crates go to Driver first — not directly to Customer.
9. Invoice crates and loose crates tracked separately on Driver. Loose crates tracked per crate type.

---

## Full Lifecycle Overview

```
[SETUP]
  Vehicle master              compliance docs (insurance, RC, fitness, pollution)
  Driver master               custom_invoice_crate_balance + custom_crate_type_balances child table
  Route Master                route_type → purpose
  Crate Type master           Blue Crate, Red Crate, etc.
  Crate Settings (single)     transit_warehouse, dispatch_warehouse, crate_uom, otp_expiry_minutes, otp_length, auto_stock_entry_on_gate_check, overdue_days

[WORKFLOW STATES — as confirmed in DB]
  Route Planning → Dispatch Loading → Gate Check → Submitted → Vehicle Returned → Submitted(final)
  Cancellation allowed from: Route Planning, Dispatch Loading, Gate Check, Submitted, Vehicle Returned
  Back transitions: Gate Check → Dispatch Loading, Dispatch Loading → Route Planning
  All states docstatus = 0 (no Frappe submit — purely workflow states)

[STEP 1: ROUTE PLANNING]        ✅ COMPLETE
  VML workflow state = "Route Planning"
    - Date, Vehicle (compliance + double-booking check), Route, Driver, Helper

[STEP 2: LOAD CRATES]           ✅ COMPLETE
  VML workflow state = "Dispatch Loading"
    - Get Invoices button  →  route + date + shift filter, already-linked invoices excluded
    - Get Stock Entries button  →  adds to table without removing invoice rows
    - Loose crate detail filled manually (crate type + qty)
    - total_invoice_crates recalculated server-side on every save

[STEP 3: GATE OUT]              ✅ COMPLETE
  VML workflow state = "Gate Check"
    - Sales Invoices linked via custom_vehicle_movement_log (db.set_value, bypasses submit lock)
    - Stock Entries linked via van_collection_item (same pattern)
    - Driver Crate Ledger OUT per invoice row (ledger_type = Driver)
    - Driver custom_invoice_crate_balance incremented
    - Driver Crate Ledger OUT per loose crate type
    - Driver custom_crate_type_balances child table updated per type
    - All entries idempotent — second Gate Check save skips already-created entries
  VML workflow state = "Submitted" (after Final check action)
    - Vehicle is OUT on the road — no code runs here

[STEP 4: DELIVERY]              ✅ COMPLETE — Phase 3A
  Crate Delivery doctype
    - Driver → Customer transfer per invoice
    - Customer Crate Ledger OUT, Customer balance incremented
    - Driver invoice crate balance decremented

[STEP 5: CUSTOMER RETURN]       ✅ COMPLETE — Phase 3A
  Part of Crate Delivery form (on_submit → _create_return_ledger)
    - Customer returns crates to Driver on-spot
    - Customer Crate Ledger IN, Customer balance decremented
    - Driver balance incremented back (driver holds them till plant)

[STEP 6: VEHICLE RETURNS]       ✅ COMPLETE (fallback path)
  VML workflow state = "Vehicle Returned"
    - process_customer_crate_return() — Customer Crate Ledger IN (fallback, skips if Crate Delivery exists)
    - close_driver_invoice_crates_on_vml_return() — Driver Crate Ledger IN, driver balance cleared (fallback)
    - create_loose_crate_in_ledger() — loose crate IN per type, driver child table decremented
  VML workflow state = "Submitted" (after final Submit action)
    - Final archive state — no code runs here

[STEP 7: PICKUP LOG]            ✅ COMPLETE — Phase 3B
  Pickup Log doctype
    - Customer walks into warehouse and buys product (Sales Invoice)
    - Invoice fetched via Get Invoices button filtered by warehouse (set_warehouse)
    - VML invoices: set_warehouse = Dispatch Warehouse (from Crate Settings)
    - Pickup invoices: set_warehouse = Pickup Log.warehouse (depot/branch)
    - On submit: Customer Crate Ledger OUT per invoice (crates going home with customer)
    - On submit: Customer Crate Ledger IN per invoice if customer returns crates on the spot
    - Customer.custom_current_crate_balance updated immediately on both

[STEP 8: VISIBILITY]            ❌ NOT BUILT — Phase 4
  Customer Crate Balance Report
    - Per customer, per crate type: total sent, total returned, balance, last transaction
```

---

## Phase 0 — Route Planning (VML Draft)

**Status:** ✅ COMPLETE
**File:** `dairy/dairy/doctype/vehicle_movement_log/vehicle_movement_log.py`

### validate() order

```
validate()
  ├─ check_vehicle_not_on_active_trip()
  ├─ check_vehicle_documents()
  ├─ update_crate_summary_balance()
  ├─ update_loose_crate_balance()
  └─ update_total_invoice_crates()
```

### Fixes Completed

#### Fix 4 — Performance: `frappe.get_doc` → `frappe.db.get_value` in `check_vehicle_documents()`
Single targeted SQL SELECT for 9 fields. No child table queries.

#### Fix 10 — Double Booking: `check_vehicle_not_on_active_trip()`
Conditionally adds `name != self.name` filter only when `self.name` is truthy.
On new unsaved docs, omitting the filter avoids `["!=", None]` ORM bug.

### Test Results

| Test | Scenario | Result |
|---|---|---|
| A | Compliance check passes for a valid vehicle | ✅ PASS |
| B | No false positive when no active trip exists | ✅ PASS |
| C | Double-booking blocked when vehicle status is Out | ✅ PASS |
| D | Existing Out trip can re-save without blocking itself | ✅ PASS |

---

## Phase 1 — Crate Settings (Single DocType)

**Status:** ✅ COMPLETE
**Path:** `dairy/dairy/doctype/crate_settings/`

### Fields

| Fieldname | Type | Default | Notes |
|---|---|---|---|
| `transit_warehouse` | Link → Warehouse | — | Target warehouse for loose crate Stock Entry. VML Python reads this; JS no longer hardcodes it. |
| `dispatch_warehouse` | Link → Warehouse | — | Plant dispatch warehouse. VML "Get Invoices" filters `set_warehouse = this`. |
| `crate_uom` | Data | `Crate` | UOM name used to identify crate items on invoices. All SQL queries read this. |
| `otp_expiry_minutes` | Int | `10` | How long a delivery OTP stays valid. |
| `otp_length` | Int | `4` | Number of digits in the delivery OTP. |
| `auto_stock_entry_on_gate_check` | Check | `1` | If unchecked, skip Stock Entry creation. |
| `overdue_days` | Int | `7` | Reserved for v2 overdue alerts. |

Access pattern: `frappe.db.get_single_value("Crate Settings", "<field>")` — one SQL call, no document overhead.

### Test Results

| Test | Scenario | Result |
|---|---|---|
| 1 | DocType registered in DB after migrate | ✅ PASS |
| 2 | Single record saves without error | ✅ PASS |
| 3 | `frappe.get_single` returns correct warehouse value | ✅ PASS |
| 4 | `frappe.db.get_single_value` fast fetch works | ✅ PASS |

---

## Phase 2 — Gate Out + Driver Balance

**Status:** ✅ COMPLETE
**Files:**
- `dairy/dairy/doctype/vehicle_movement_log/vehicle_movement_log.py`
- `dairy/dairy/doctype/vehicle_movement_log/vehicle_movement_log.js`
- `dairy/dairy/doctype/driver_crate_type_balance/` (new child doctype)

### Python Changes

#### P1 — `create_driver_crate_ledger_for_invoices()` (renamed from `create_customer_crate_ledger`)
Invoice crates now go to **Driver** at Gate Check, not Customer.
- `ledger_type = "Driver"`, sets `driver`, `vehicle`, `customer` (for reference), `sales_invoice`
- Does NOT touch `Customer.custom_current_crate_balance` — that happens at Crate Delivery (Phase 3)
- After loop: increments `Driver.custom_invoice_crate_balance` by newly created crates only (idempotent)

#### P2 — `frappe.get_doc` → `frappe.db.get_value` in invoice ledger loop
`customer = frappe.db.get_value("Sales Invoice", row.sales_invoice, "customer")` — one field, one SQL.

#### P3 — `update_total_invoice_crates()` added to `validate()`
Server-side sum of `total_crate_out` across all `crate_summary` rows. Cannot be manipulated client-side.

#### P4 — `link_sales_invoices()` guard + Stock Entry linking
- Invoice: `db.set_value` only fires when `existing_trip` is falsy — no redundant writes
- Stock Entry: same loop for `van_collection_item` field with same duplicate-trip guard
- `db.set_value` bypasses submit lock — works on submitted Sales Invoice and Stock Entry

#### P5 — Dead code fix: `self.status` → `self.workflow_state` in `on_update`
`self.status` options are Draft/Out/In. "Gate Check" is a workflow state. Was unreachable code.

#### P6 — `TRANSIT_WAREHOUSE` constant removed
Replaced everywhere with `frappe.db.get_single_value("Crate Settings", "transit_warehouse")`.

#### P7 — `_update_driver_loose_crate_balances()` helper
One `frappe.get_doc("Driver")` + one `driver_doc.save()` per event regardless of how many crate types.
Finds existing child row for crate type and updates balance; creates new row if type not seen before.

#### P8 — `create_loose_crate_out_ledger()` updates Driver child table
Tracks newly created entries only. Calls `_update_driver_loose_crate_balances(changes)` after loop.

#### P9 — `create_loose_crate_in_ledger()` decrements Driver child table
On vehicle return, returned loose crates reduce the driver's per-type balance.

#### Bug fix — `self.custom_stock_entry` AttributeError
Removed the guard block that called `create_stock_entry_for_loose_items()`. Field does not exist on VML doctype. Stub method retained for future implementation.

#### Additional — Stock Entry Crate Ledger
- `create_driver_crate_ledger_for_stock_entries()` — Driver OUT at Gate Check for stock entry rows
- `close_driver_stock_entry_crates_on_vml_return()` — Driver IN at Vehicle Returned for stock entry rows using `total_crate_in`

#### Additional — VML Cancel + Trash Cleanup (`_cleanup_crate_entries()`)
Triggered on `workflow_state = "Cancelled"` and `on_trash()`:
- Delinks all Sales Invoices (`custom_vehicle_movement_log → None`)
- Delinks all Stock Entries (`van_collection_item → None`)
- Collects all ledger entries for this VML, calculates reversals
- Deletes all Customer Crate Ledger entries for this VML
- Reverses Driver and Customer balances
- Shows detailed cancellation message in UI

#### Additional — `sync_crate_item_details()`
Called in `validate()`. Removes rows from `crate_item_details` child table whose `sales_invoice` or `stock_entry` no longer exists in `crate_summary`. Keeps the two tables in sync automatically when rows are deleted.

#### Additional — Comprehensive Gate Check Message
`link_sales_invoices()` now shows a full summary: invoices linked with crate counts, stock entries linked, total crates out, item breakdown sorted by quantity.

#### Additional — `customer_crate_ledger.json` — `stock_entry` field
Added `stock_entry` (Link → Stock Entry) field to Customer Crate Ledger doctype JSON. Migrated via `bench migrate`. No manual step needed on prod.

### JS Changes

#### J1 — Freeze message corrected
Get Invoices: `"Fetching Invoices & Stock Entries"` → `"Fetching Invoices"`

#### J2 — Selective table clear (not full wipe)
- Get Invoices: removes only invoice rows (where `sales_invoice` is set), keeps stock entry rows
- Get Stock Entries: removes only stock entry rows (where `stock_entry` is set), keeps invoice rows

#### J3 — Already-linked invoices filtered from Get Invoices dialog
`custom_vehicle_movement_log: ""` added to `get_query()` filters. Invoices already on another VML are hidden.

### New DocType: Driver Crate Type Balance (child)
**Path:** `dairy/dairy/doctype/driver_crate_type_balance/`

| Fieldname | Type | Notes |
|---|---|---|
| `crate_type` | Link → Crate Type | |
| `balance` | Float | Read only |

Added as `custom_crate_type_balances` child table on Driver doctype via Customize Form.

### VML Connections (Links)
Added to `vehicle_movement_log.json`:
- Sales Invoice via `custom_vehicle_movement_log`
- Stock Entry via `van_collection_item`

Shows live count badges on VML form.

### Driver Doctype Fields Added (via Customize Form)

| Fieldname | Type | Notes |
|---|---|---|
| `custom_invoice_crate_balance` | Float, Read Only | Total invoice crates currently with driver |
| `custom_crate_type_balances` | Table → Driver Crate Type Balance | Per-type loose crate balance |

### Test Results

| Test | Scenario | Result |
|---|---|---|
| 1 | Gate Check transition links Sales Invoices | ✅ PASS |
| 2 | Gate Check transition links Stock Entries | ✅ PASS |
| 3 | Already-linked invoices not shown in Get Invoices dialog | ✅ PASS |
| 4 | Get Invoices + Get Stock Entries coexist in crate_summary | ✅ PASS |
| 5 | Driver Crate Ledger OUT entries created per invoice row | ✅ PASS |
| 6 | Driver invoice crate balance incremented | ✅ PASS |
| 7 | Driver loose crate type balance rows created/updated | ✅ PASS |
| 8 | total_invoice_crates recalculates on save | ✅ PASS |
| 9 | Connections section on VML shows linked Invoice + SE count | ✅ PASS |

### VML Flaw Fixes (applied 2026-05-27)

All 7 flaws identified in the full system review are resolved or tracked below.

| Flaw | Description | Fix | Status |
|---|---|---|---|
| 1 | `process_customer_crate_return()` guard missing `vehicle_movement_log` | Added `vehicle_movement_log: self.name` to guard filter | ✅ FIXED |
| 2 | Driver `custom_invoice_crate_balance` never decremented at VML Submitted | New method `close_driver_invoice_crates_on_vml_return()` — creates Driver Crate Ledger IN per invoice + decrements balance by `total_crate_out` | ✅ FIXED |
| 3 | VML Submitted double-counts Customer balance once Phase 3 (Crate Delivery) is live | Both `process_customer_crate_return()` and `close_driver_invoice_crates_on_vml_return()` skip invoices where `Crate Delivery` (docstatus=1) already exists | ✅ FIXED |
| 4 | No duplicate guard on Crate Delivery submit | Idempotency guard on every ledger entry in `_create_delivery_ledger()` and `_create_return_ledger()` | ✅ FIXED |
| 5 | Redirect delivery: ledger uses original customer, not `actual_customer` | All ledger entries use `self.actual_customer` — Flaw handled by design | ✅ FIXED |
| 6 | `balance_crates` on Customer Crate Ledger was `row.balance_crate` (trip level) | Now reads `Customer.custom_current_crate_balance` from DB — actual running balance after the transaction | ✅ FIXED |
| 7 | `frappe.get_doc("Sales Invoice")` in `process_customer_crate_return()` loop | Replaced with `frappe.db.get_value("Sales Invoice", name, "customer")` | ✅ FIXED |

---

## Driver Balance 3-Rule Fix (2026-05-29)

**Status:** ✅ COMPLETE
**File:** `dairy/dairy/doctype/vehicle_movement_log/vehicle_movement_log.py`

### Problem

At VML "Vehicle Returned", the old code:
- **CD invoice rows**: skipped entirely → driver balance stayed inflated permanently
- **Non-CD invoice rows**: always reduced by `total_crate_out` regardless of actual returns
- **Loose crates**: used `row.crates_in` (user-entered) which could be wrong

### 3 Rules Implemented

**Rule 1 — Loose crates** (`create_loose_crate_in_ledger`):
Loose crates are always 1:1 — 10 out, 10 back. System auto-uses `crates_out` as `crates_in`. User-entered `crates_in` field is ignored.

**Rule 2 — CD invoice rows** (`close_driver_invoice_crates_on_vml_return`):
If a submitted Crate Delivery exists for that invoice, fetch `crates_returned` from it. That's the locked, validated figure of how many crates the driver is physically bringing back from that customer.

**Rule 3 — Non-CD invoice rows** (`close_driver_invoice_crates_on_vml_return`):
No Crate Delivery exists, so use `total_crate_in` entered by dispatch/driver. Cap it at `total_crate_out` — driver cannot return more than they loaded.

### Remaining balance = driver's responsibility

After VML final submit (gate confirms), any crates still on the driver's balance are their responsibility — those are crates at customers who haven't returned them yet.

---

## Phase 3 — Crate Delivery + Crate Pickup Entry

**Status:** 🔨 IN PROGRESS — 3A built, 3B pending

### 3A — Crate Delivery (Driver → Customer)

**Purpose:** One document per invoice stop. Driver delivers crates, customer returns empties, OTP confirms the transaction.
**Entry point:** ERPNext (dispatch fallback) OR Flutter app (primary).

#### Delivery Sequence (locked)
```
1. Driver hands invoice crates to customer
2. Customer gives back empty crates to driver
3. OTP generated on app
4. Customer enters OTP  →  customer_confirmed = 1
5. Document submitted  =  delivery confirmed
```

#### Business Rules (locked)
- One Crate Delivery per Sales Invoice (one per customer stop)
- `crates_delivered >= invoice_crate_qty` enforced — cannot deliver fewer than invoiced
- No cap on `crates_returned` — driver can accept fewer crates back
- Redirect scenario: if Customer A is closed, entire invoice transfers to one other customer via `actual_customer` (no split)
- All ledger entries are idempotent (Flaw 4 guard baked in from the start)
- `actual_customer` drives all ledger entries — Flaw 5 handled by design

#### Parent: `Crate Delivery`

| Fieldname | Type | Notes |
|---|---|---|
| `vehicle_movement_log` | Link → Vehicle Movement Log | Required |
| `date` | Date | Default today |
| `driver` | Link → Driver | Fetched from VML |
| `vehicle` | Link → Vehicle | Fetched from VML |
| `route` | Link → Route Master | Fetched from VML |
| `sales_invoice` | Link → Sales Invoice | One per document |
| `customer` | Link → Customer | Read-only, from Sales Invoice |
| `actual_customer` | Link → Customer | Editable — use for redirect; defaults to `customer` |
| `invoice_crate_qty` | Float | Read-only, from Sales Invoice crate items |
| `customer_current_balance` | Float | Read-only, live from Customer.custom_current_crate_balance |
| `crates_delivered` | Float | Must be ≥ invoice_crate_qty |
| `crates_returned` | Float | ≤ crates_delivered; no minimum |
| `customer_confirmed` | Check | Set by OTP confirmation on app |
| `amended_from` | Link → Crate Delivery | |

#### On Submit
```
Delivery ledger:
  Customer Crate Ledger OUT  (ledger_type=Customer, entry_type=OUT)
    customer = actual_customer
    crates_out = crates_delivered
    balance_crates = actual_customer.custom_current_crate_balance + crates_delivered
  → Customer.custom_current_crate_balance += crates_delivered
  → Driver.custom_invoice_crate_balance -= crates_delivered

Return ledger (if crates_returned > 0):
  Customer Crate Ledger IN  (ledger_type=Customer, entry_type=IN)
    customer = actual_customer
    crates_in = crates_returned
    balance_crates = actual_customer.custom_current_crate_balance - crates_returned
  → Customer.custom_current_crate_balance -= crates_returned
  → Driver.custom_invoice_crate_balance += crates_returned  (driver holds them back)
```

#### On Cancel
Reverse all ledger entries and restore all balances.

### 3B — Pickup Log (warehouse counter sale)

**Status:** ✅ COMPLETE
**Path:** `dairy/dairy/doctype/pickup_log/`

**Purpose:** Customer walks into a warehouse/depot and buys products. If the invoice has crate items, the crate balance is tracked the same way as VML deliveries. Customer can also return empty crates on the spot.

**Key distinction from VML:** No driver or vehicle involved. Invoice filtering uses the pickup warehouse's `set_warehouse` field instead of route. Dispatch Warehouse (plant) goes to VML; any other warehouse goes to Pickup Log.

#### Parent: `Pickup Log`

| Fieldname | Type | Notes |
|---|---|---|
| `date` | Date | Default today, required |
| `warehouse` | Link → Warehouse | Required. Filters which invoices appear (`set_warehouse` filter) |
| `total_invoice_crates` | Float | Read-only, auto sum of crate_summary |
| `crate_summary` | Table → Vehicle Invoice Crate Detail | Reuses same child table as VML |
| `amended_from` | Link → Pickup Log | Standard |

#### Invoice Fetching

"Get Invoices" button filters Sales Invoices:
- `docstatus = 1`
- `is_return = 0`
- `posting_date = frm.doc.date`
- `set_warehouse = frm.doc.warehouse` ← distinguishes from VML invoices
- `custom_pickup_log = ""` ← not already assigned to another Pickup Log

#### On Submit
```
For each row in crate_summary:
  Fetch customer from Sales Invoice
  If total_crate_out > 0:
    Customer Crate Ledger OUT  (ledger_type=Customer, crate_category=Pickup)
    Customer.custom_current_crate_balance += total_crate_out
  If total_crate_in > 0 (customer returns crates on spot):
    Customer Crate Ledger IN   (ledger_type=Customer, crate_category=Pickup)
    Customer.custom_current_crate_balance -= total_crate_in
  Set Sales Invoice.custom_pickup_log = self.name
```

#### On Cancel
- Calculates net balance change per customer from all ledger entries
- Deletes all Customer Crate Ledger entries for this Pickup Log
- Reverses Customer.custom_current_crate_balance per customer
- Removes custom_pickup_log link from all invoices

#### Crate Settings integration
- `dispatch_warehouse` → VML "Get Invoices" filters by this warehouse. Set to `Dispatch Cold Room - BDF`.
- `crate_uom` → Used in all SQL queries to count crate items on invoices.
- VML JS no longer hardcodes `"Goods and Transit - BDF"` — Python reads `transit_warehouse` from Crate Settings.

#### Customer Crate Ledger changes
- Added `pickup_log` Link field
- Added `"Pickup"` to `crate_category` options (alongside Sales Invoice, Stock Entry, Loose Crate)

---

## Phase 4 — Customer Crate Balance Report

**Status:** ❌ NOT STARTED
**Path:** `dairy/dairy/report/customer_crate_balance/`

### Filters

| Fieldname | Type | Notes |
|---|---|---|
| `from_date` | Date | Filter on posting_date |
| `to_date` | Date | Filter on posting_date |
| `route` | Link → Route Master | Optional |
| `outstanding_only` | Check | Hide zero-balance customers |

### Columns

| Column | Notes |
|---|---|
| Customer | Link → Customer |
| Crate Type | Link → Crate Type |
| Total Sent (Out) | Sum of crates_out |
| Total Returned (In) | Sum of crates_in |
| Balance | Out - In |
| Last Transaction | Max posting_date in range |

**Performance:** Single `frappe.db.sql` with `GROUP BY customer, crate_type`. `outstanding_only` handled as `HAVING balance > 0` in SQL.

---

---

## Phase 5 — Mobile App API + Application Screens

**Status:** ❌ NOT STARTED
**File:** `mobile/mobile/api.py` (append to existing file — do NOT create a new file)

> Note: `dairy/dairy/api.py` was created as a draft but is the wrong location. All crate API endpoints go into `mobile/mobile/api.py` alongside the existing customer endpoints.

### Frappe Login (no custom code needed)
The app logs in using the standard Frappe endpoint:
```
POST /api/method/login
Body: { usr: "email", pwd: "password" }
```
After login, the app immediately calls `get_user_info()` to determine which home screen to show.

### How user identification works

```
POST login → call get_user_info()
  frappe.get_roles(session.user) → check in priority order:
    Dairy Master / System Manager  →  user_type = "Master"
    Dairy Driver                   →  user_type = "Driver"  + Driver.custom_user lookup
    Dairy Dispatch                 →  user_type = "Dispatch"
    Dairy Production               →  user_type = "Production"
    Customer                       →  user_type = "Customer" + Portal User → Customer lookup
    (none matched)                 →  user_type = "Unknown"
```

### How entity linking works

| User type | Lookup method |
|---|---|
| Driver | `Driver.custom_user == frappe.session.user` |
| Customer | `Portal User.user == session.user → parent = Customer` (then fallback: Contact.email_id) |
| Dispatch / Production / Master | No entity needed — they see all records |

> Customer lookup uses the **existing `get_logged_in_customer()`** function already in mobile/api.py — do not use Contact Dynamic Link.

---

### APP SIDE — Screens Per Role

#### 🚗 Driver App

| Screen | API Endpoint | Notes |
|---|---|---|
| Home | `get_driver_home()` | Today's VMls + crate balance |
| Trip Detail | `get_vml_details(vml)` | Invoice list for that trip |
| Crate Delivery Form | `create_crate_delivery(vml, invoice, crates_delivered, crates_returned)` | Submit CD |
| OTP Confirm | `confirm_customer_otp(cd_name)` | Set customer_confirmed = 1 |
| History | `get_driver_crate_deliveries()` | Past CDs |

#### 🏭 Dispatch App

| Screen | API Endpoint | Notes |
|---|---|---|
| Home | `get_dispatch_vmls(date)` | All trips for today |
| Driver Balances | `get_dispatch_driver_balances()` | Who has outstanding crates |
| Trip Detail | `get_vml_details(vml)` | View any VML |

#### 🏗️ Production App

| Screen | API Endpoint | Notes |
|---|---|---|
| Home | `get_production_crate_summary()` | Total crates with customers |

#### 👤 Customer App (existing app — add crate tab)

| Screen | API Endpoint | Notes |
|---|---|---|
| Crate Balance | `get_customer_crate_balance()` | Balance + ledger |
| Pending Confirmations | `get_customer_pending_deliveries()` | Deliveries awaiting OTP |

#### 🔑 Master App

All screens from all roles visible.

---

### Security Rules

| Rule | Detail |
|---|---|
| No guest access | Every endpoint checks `frappe.session.user != "Guest"` — throws PermissionError if not logged in |
| Role guards | Every endpoint calls `_require(role)` — throws PermissionError if user doesn't have the right role |
| Data isolation — Driver | Driver endpoints fetch `driver = Driver.custom_user` and filter all queries by that driver — a driver cannot see another driver's VMls or deliveries |
| Data isolation — Customer | Customer endpoints use `get_logged_in_customer()` — a customer cannot see another customer's data |
| Master User override | `Master User` role bypasses all data isolation — can see everything |
| Role constant | `ROLE_MASTER = "Master User"` (not "Dairy Master") |

### API Endpoints to Build (append to mobile/api.py)

| Endpoint | Status | Role |
|---|---|---|
| `get_user_info()` | ✅ BUILT | All |
| `get_driver_vmls(date?)` | ✅ BUILT | Dairy Driver |
| `get_driver_vml_details(vml)` | ✅ BUILT | Dairy Driver, Dairy Dispatch |
| `get_driver_pending_deliveries(vml?)` | ✅ BUILT | Dairy Driver |
| `create_crate_delivery(...)` | ✅ BUILT | Dairy Driver |
| `confirm_customer_otp(cd_name)` | ✅ BUILT | Dairy Driver |
| `get_dispatch_vmls(date?)` | ✅ BUILT | Dairy Dispatch |
| `get_dispatch_driver_balances()` | ✅ BUILT | Dairy Dispatch |
| `get_production_crate_summary()` | ❌ TO BUILD | Dairy Production |
| `get_customer_crate_balance()` | ✅ BUILT | Customer |
| `get_customer_crate_ledger(...)` | ✅ BUILT | Customer |
| `get_customer_pending_deliveries()` | ❌ TO BUILD | Customer |

---

## Deferred (Not in v1)

| Item | Reason |
|---|---|
| Crate damage recording | Needs real-world usage to define workflow |
| Billing for unreturned crates | Needs overdue threshold agreed in real use |
| WhatsApp alert for overdue balances | Post v1 |
| Crate Reconciliation (VML-based) | After usage data shows gaps |
| Retiring old Gate Pass / Crate Log system | Separate architecture decision |
| Mobile app crate pickup confirmation | Post v1 |
| Per-crate-type balance on Customer master | Post v1 if needed |
| Unlink single invoice / stock entry from VML | Deferred — needs careful implementation |
| create_stock_entry_for_loose_items() | Stub in place — implement when stock entry flow is confirmed |

---

## Build Order

```
Phase 0  →  Route Planning (VML Draft)                              ✅ COMPLETE
             Fix 4  ✅  Performance: frappe.get_doc → frappe.db.get_value
             Fix 10 ✅  Double booking: check_vehicle_not_on_active_trip()
             Tests: A ✅  B ✅  C ✅  D ✅

Phase 1  →  Crate Settings doctype                                  ✅ COMPLETE
             Tests: 1 ✅  2 ✅  3 ✅  4 ✅

Phase 2  →  Gate Out + Driver Balance                               ✅ COMPLETE
             P1  ✅  Driver ledger for invoice crates (not Customer)
             P2  ✅  frappe.get_doc → frappe.db.get_value in loop
             P3  ✅  Server-side total_invoice_crates in validate()
             P4  ✅  link_sales_invoices() guard + Stock Entry linking
             P5  ✅  self.status → self.workflow_state dead code fix
             P6  ✅  TRANSIT_WAREHOUSE constant removed
             P7  ✅  _update_driver_loose_crate_balances() helper
             P8  ✅  loose OUT ledger updates Driver child table
             P9  ✅  loose IN ledger decrements Driver child table
             J1  ✅  Freeze message corrected
             J2  ✅  Selective table clear (invoice vs stock entry rows)
             J3  ✅  Already-linked invoices filtered from dialog
             Driver Crate Type Balance child doctype  ✅
             VML Connections (Sales Invoice + Stock Entry)  ✅
             Tests: 1 ✅  2 ✅  3 ✅  4 ✅  5 ✅  6 ✅  7 ✅  8 ✅  9 ✅

VML Flaw Fixes (2026-05-27)                                         ✅ COMPLETE
             Flaw 1  ✅  Guard includes vehicle_movement_log (idempotency)
             Flaw 2  ✅  close_driver_invoice_crates_on_vml_return() — driver balance cleared
             Flaw 3  ✅  Crate Delivery existence check before processing returns
             Flaw 6  ✅  balance_crates uses running Customer balance from DB
             Flaw 7  ✅  frappe.get_doc → frappe.db.get_value in process_customer_crate_return()
             Flaw 4  ⏳  Handled by design in Crate Delivery (Phase 3 build)
             Flaw 5  ⏳  Handled by actual_customer field design in Crate Delivery (Phase 3 build)

Driver Balance 3-Rule Fix (2026-05-29)                              ✅ COMPLETE
             Rule 1  ✅  Loose crates always 1:1 — auto crates_in = crates_out
             Rule 2  ✅  CD rows — use crates_returned from submitted Crate Delivery
             Rule 3  ✅  Non-CD rows — min(total_crate_in, total_crate_out)

Phase 3  →  Crate Delivery + Pickup Log
             3A  Crate Delivery doctype (Driver → Customer)          ✅ COMPLETE
                 - on_submit: delivery ledger + return ledger
                 - on_cancel: reverse all + restore balances
                 - validate: crates_delivered ≥ invoice_crate_qty
                 - validate: crates_returned warning (not block)
                 - JS: SI filter (VML-linked only), live balance
             3B  Pickup Log (Customer walks into warehouse)           ✅ COMPLETE
                 - Get Invoices filtered by set_warehouse
                 - on_submit: Customer OUT + IN ledger per invoice row
                 - on_cancel: reverse all + delink invoices
                 - Customer Crate Ledger: pickup_log field + Pickup category
             3C  Crate Balance Adjustment (opening/closing balances)  ✅ COMPLETE
                 - New doctype dairy/dairy/doctype/crate_balance_adjustment/
                 - Party Type: Customer or Driver
                 - Entry Type: Opening or Adjustment
                 - Crates: positive = add balance, negative = reduce
                 - on_submit: Customer Crate Ledger entry + master balance update
                 - on_cancel: ledger deleted + balance reversed
                 - Visible in Crate Audit Report (customer-wise section)

Phase 4  →  Crate Audit Report                                      ✅ COMPLETE
             - Trip-wise section: VML → Invoice/SE rows → Assigned/Given/Taken
             - Customer-wise section: Customer → all invoices with trip ref
             - View By filter: Both / Trip Wise / Customer Wise
             - Filters: from_date, to_date, driver, customer, VML
             - Summary bar: total assigned, given, taken, net outstanding
             - File: dairy/dairy/report/crate_audit_report/

Phase 5  →  Mobile App API (file: mobile/mobile/api.py)             🔨 IN PROGRESS
             get_user_info()                     ✅
             get_driver_vmls(date?)              ✅  (now filters: workflow_state = "Dispatch Loading" only)
             get_driver_vml_details(vml)         ✅  (now returns customer_crate_balance per invoice row)
             get_driver_pending_deliveries(vml?) ✅
             create_crate_delivery(...)          ✅
             confirm_customer_otp(cd_name)       ✅
             get_dispatch_vmls(date?)            ✅
             get_dispatch_driver_balances()      ✅
             get_production_crate_summary()      ❌
             get_customer_crate_balance()        ✅
             get_customer_crate_ledger(...)      ✅
             get_customer_pending_deliveries()   ❌
```

---

## Session Changes — 2026-06-29

### VML Form Fixes (vehicle_movement_log.js + .py)

| Change | Detail |
|---|---|
| "+" button selectors fixed | Selector was `btn-new-doc` — correct class is `btn-new` with `data-doctype` attribute |
| Sales Invoice "+" always hidden | Never show at any workflow state |
| Stock Entry "+" always hidden | Never show at any workflow state |
| Crate Delivery "+" only at Submitted | `toggle(frm.doc.workflow_state === "Submitted")` |
| Final check dialog | `before_workflow_action` returns Promise; unfreezes DOM before showing dialog |
| Crate assignment timing | Driver ledger created at "Submitted" (after Final check), NOT at Gate Check |
| Crate cancellation — loose crates | `_cleanup_crate_entries` now reverses `custom_crate_type_balances` child table separately from invoice crates |
| `total_crate_in` removed from Vehicle Invoice Crate Detail | `update_crate_summary_balance` simplified to no-op; `process_customer_crate_return` gutted to pass |
| `crates_in` removed from Loose Crate Detail | `update_loose_crate_balance` simplified: `row.balance = row.crates_out or 0` |
| Customer balance in crate summary | `balance_crate` field on Vehicle Invoice Crate Detail now shows `Customer.custom_current_crate_balance`; label changed to "Customer Balance"; populated in `populate_crate_summary_customer_names` and in `get_invoice_details` JS response |

### Crate Delivery Fixes (crate_delivery.js + .py)

| Change | Detail |
|---|---|
| Sales Invoice dropdown filter | Custom server query `get_available_invoices_for_cd` — only shows invoices linked to VML with no active Crate Delivery |
| Stock Entry dropdown filter | Custom server query `get_available_stock_entries_for_cd` — same logic |
| OTP phone override field | `otp_phone_override` Data field added to Crate Delivery JSON; `allow_on_submit: 1`; both `send_delivery_otp` and `send_delivery_sms` use this number first |
| Ledger gated behind OTP | `on_submit` skips `_create_delivery_ledger` / `_create_return_ledger` if `sales_invoice` set but `customer_confirmed = 0`; `verify_delivery_otp` calls them directly if doc already submitted |
| SMS DLT template updated | New 7-variable template with Inv No, Delivered, Trip No, Returned, Balance, OTP |

### New Doctypes (dairy/dairy/doctype/)

| Doctype | Purpose |
|---|---|
| `Crate Balance Adjustment` | Create opening / adjustment balance entries for Customer or Driver; writes to Customer Crate Ledger; updates master balance on submit/cancel |

### Customer Crate Ledger

| Change | Detail |
|---|---|
| `entry_type` options | Added "Opening" and "Adjustment" alongside existing "OUT" and "IN" |

### Crate Audit Report (dairy/dairy/report/crate_audit_report/)

Completely redesigned. Previous customer/driver section report replaced with:
- **Trip Wise**: VML header → Invoice/SE rows with Assigned to Driver, Given to Customer, Taken from Customer
- **Customer Wise**: Customer header → all invoices/SEs with date, VML, Given, Taken
- **View By** filter: Both / Trip Wise / Customer Wise
- **Customer filter** added
- Crate Balance Adjustment entries automatically appear in Customer Wise section (via Customer Crate Ledger)

### Mobile API (mobile/mobile/api.py)

| Change | Detail |
|---|---|
| `get_driver_vmls` | Now filters `workflow_state = "Dispatch Loading"` only — driver only sees active trips |
| `get_driver_vml_details` | Returns `customer_crate_balance` per invoice row from `Customer.custom_current_crate_balance` |

### Flutter App (bastar_dairy_farm)

| File | Change |
|---|---|
| `driver_trip_detail_screen.dart` | Invoice delivery card shows "Customer has X crates" below invoice number |

---

## Session Changes — 2026-07-02

### Crate Balance Adjustment — Warehouse party + Loose crates

| Change | Detail |
|---|---|
| Warehouse party type | Added `Warehouse` as a 3rd Party Type (alongside Customer, Driver). New `warehouse` Link field on the doctype. |
| Loose crate support | `driver_balance_type` (Invoice Crates / Loose Crate) + `crate_type` fields now shown for **both Driver and Warehouse** (depends_on generalized). Warehouse loose balances stored per crate type. |
| Warehouse balance storage | Warehouse total → `Warehouse.custom_crate_balance`; loose per-type → `Warehouse.custom_crate_type_balances` (reuses `Driver Crate Type Balance` child doctype). See prod checklist rows 8–10. |
| Python generalized | `crate_balance_adjustment.py` refactored to a single `PARTY_MAP` handling Customer/Driver/Warehouse uniformly (ledger + master balance + loose helpers). |
| Current-balance panel | `get_party_crate_balances` + JS now render live balance cards for the selected party (customer single card; driver/warehouse show invoice + per-type loose cards). |
| Negative balance guard | On submit, an adjustment that pushes any balance below 0 is blocked unless **Crate Settings → Allow Negative Crate Balance** is ticked. |
| Bug fix — invalid ledger link | Adjustment ledger entries were writing to `crate_delivery` (Link to Crate Delivery) → LinkValidationError. Added dedicated `crate_balance_adjustment` Link field on Customer Crate Ledger and use it. |
| Bug fix — crate_category | Loose adjustments set `crate_category = "Opening — Loose"` which is not a valid Select option → ValidationError. Now uses valid `"Loose Crate"` category; direction carried by `entry_type` + `crate_type`. |

### Crate Settings

| Change | Detail |
|---|---|
| `allow_negative_crate` | New Check field (default 0). When off, Crate Balance Adjustment cannot reduce a balance below zero. |

### Customer Crate Ledger

| Change | Detail |
|---|---|
| `crate_balance_adjustment` | New Link field → Crate Balance Adjustment. |
| `warehouse` | New Link field → Warehouse. |
| `ledger_type` options | Added "Warehouse". |
| `crate_category` options | Added "Opening", "Adjustment" (in addition to the earlier Loose Crate/Pickup etc.). |

### Crate Delivery — GPS / Location capture

| Change | Detail |
|---|---|
| Location fields | Added `location_source` (Mobile GPS / ERP Manual), `delivery_latitude`, `delivery_longitude`, `location_captured_at`, and a `location_map_html` (Google Maps embed + link) — all in the doctype JSON (auto-migrated). |
| ERP fallback default | `validate()` defaults `location_source = "ERP Manual"` when not set — used when the dispatch team enters a delivery from the plant/computer because the driver app/phone failed. |
| Mobile GPS required | `create_crate_delivery` (mobile API) now **requires** `latitude`/`longitude` — throws if missing — and stamps `location_source = "Mobile GPS"`, `location_captured_at`. Refreshes GPS on an existing draft too. |
| Desk map | `crate_delivery.js` renders a Google Maps embed + "Open in Google Maps" button from the captured lat/long. |

### Material Gate Pass (NEW doctype — dairy/dairy/doctype/)

| Item | Detail |
|---|---|
| Purpose | Gate pass for material movement, **separate** from the existing milk-route "Gate Pass" (milk_entry module). |
| Types | `gate_pass_type`: Inward (supplier) / Transfer (plant→plant/location). `trip_type`: One Way / Return Trip. |
| Return trip | Return Trip shows a second items table + return gate-entry section (return security guard, returned-at time, accepted/verified by). Status flow Draft → In Transit → Returned → Completed. |
| Child table | `Material Gate Pass Item` (item, qty, uom, received_qty, remarks). |

### Reports

| Report | Fix |
|---|---|
| Assets location details | SQL queried `asset_sn` but the doctype fieldname is `aseet_sn` (typo in field) → `OperationalError`. Report column + SELECT changed to `aseet_sn`. |

### Mobile API (mobile/mobile/api.py)

| Change | Detail |
|---|---|
| `get_customer_crate_balance` | Returns logged-in customer's `custom_current_crate_balance`. (Removed wrong `_require("customer")` — customer endpoints use `get_logged_in_customer()` directly.) |
| `get_customer_crate_ledger` | Returns the customer's crate ledger. Uses `frappe.get_all(..., ignore_permissions=True)` (customers have no read role on Customer Crate Ledger); returns `creation`, `crate_type`, `crate_balance_adjustment` for detailed display. |
| `create_crate_delivery` | New `latitude`/`longitude` params — required; sets Mobile GPS location fields. |

### Flutter App (bastar_dairy_farm)

| File | Change |
|---|---|
| `dashboard_screen.dart` | "Crate Balance" card (taps to ledger) + "Crates" quick-action; overflow fixes. |
| `crate_ledger_screen.dart` | Full detailed ledger — what it's against, action, trip, date+time, +/- qty, running balance; period filter. |
| `crate_delivery_form_screen.dart` | Captures GPS (geolocator) before submitting; blocks delivery if location/permission off. |
| `data_service.dart` | `getCustomerCrateBalance`, `getCustomerCrateLedger` (correct `mobile.api.*` paths); `createCrateDelivery` sends latitude/longitude. |
| `pubspec.yaml` | Added `geolocator: ^13.0.1`. |
| `AndroidManifest.xml` | Added `ACCESS_FINE_LOCATION` + `ACCESS_COARSE_LOCATION`. |

### Driver Crate Ledger (full chain view)

| Change | Detail |
|---|---|
| `get_driver_crate_ledger` (mobile API) | New endpoint. Pulls every Customer Crate Ledger row where `driver = logged-in driver` and classifies each into the chain: `assigned` (plant→driver, ledger_type=Driver OUT), `to_customer` (delivery OUT), `from_customer` (return IN). Resolves customer names. Works because delivery + return ledgers already store both `driver` and `customer`. |
| `DriverCrateLedgerScreen` (Flutter, driver/) | New screen — balance card + legend (navy=assigned, red=given, green=returned) + movement list (customer/invoice, trip, date+time, signed qty). |
| Driver Profile | New "Crates With You" card that opens the driver crate ledger. `data_service.getDriverCrateLedger()` added. |

### VML cancel → cancel linked Crate Deliveries

| Change | Detail |
|---|---|
| `_cancel_linked_crate_deliveries` (vehicle_movement_log.py) | When a VML is cancelled/trashed, `_cleanup_crate_entries` now first cancels submitted linked Crate Deliveries (their `on_cancel` self-reverses delivery/return ledgers + master balances and deletes their ledger rows) and deletes draft ones. Runs BEFORE VML-level ledger cleanup to avoid double-reversal. Per-delivery failures are logged via `frappe.log_error`, not fatal. |

### Warehouse crate balance at Crate Delivery + Transit→Warehouse mapping

| Change | Detail |
|---|---|
| `Crate Transit Warehouse Map` (NEW child doctype) | Two Link fields: `transit_warehouse`, `warehouse` (linked). Maps a transit warehouse to the warehouse that owns its crate balance. |
| Crate Settings → `transit_warehouse_map` | New Table field (options `Crate Transit Warehouse Map`) under the Warehouses section. Admin fills the transit→warehouse rows. **Auto-migrated (JSON).** |
| `_get_mapped_warehouse` (crate_delivery.py) | Resolves the affected warehouse: reads the TRANSIT warehouse from the delivery doc — Stock Entry `to_warehouse` (else first item `t_warehouse`), or Sales Invoice `set_warehouse` — then looks it up in the mapping → uses the LINKED warehouse. Falls back to the transit warehouse itself if unmapped. |
| Warehouse movement on delivery/return | `_warehouse_movement`: delivery → warehouse `custom_crate_balance` ▼ by crates_delivered; return → ▲ by crates_returned. Each writes a `ledger_type=Warehouse` Customer Crate Ledger row (linked to delivery/invoice/SE/driver/customer/VML) for audit. |
| Reversal on Crate Delivery cancel | `_reverse_warehouse_movement`: delivery reversal ▲, return reversal ▼. Ledger rows deleted by `crate_delivery`. |
| Strict reversal on VML cancel | `_cleanup_crate_entries` now also reverses Warehouse-type rows (Step 7) with the OPPOSITE sign (`crates_out − crates_in`) — a safety net for warehouse rows still tied to the VML if a Crate Delivery cancel failed. `warehouse` added to the collected ledger fields. |

### Crate Delivery — stock-entry crate qty + OTP bypass

| Change | Detail |
|---|---|
| `get_stock_entry_crate_qty` + `_set_crates_from_stock_entry` (crate_delivery.py) | Selecting a Stock Entry on a Crate Delivery now fetches its crate count (Stock Entry Detail rows with `uom = crate_uom` received into a transit `t_warehouse`) into `invoice_crate_qty` — same as Sales Invoice does. New JS `stock_entry` handler calls it; server-side setter runs in `validate`. Same "delivered ≥ expected" validation applies. |
| Crate Settings → `allow_otp_bypass` | New Check (default off). Master switch to allow confirming a delivery without OTP. **Auto-migrated (JSON).** |
| Crate Delivery → `otp_bypassed`, `otp_bypass_reason` | New audit fields (read-only). Record that a delivery skipped OTP and why. **Auto-migrated (JSON).** |
| `bypass_delivery_otp` (crate_delivery.py) | Whitelisted. Gated by `allow_otp_bypass` + requires a reason (both enforced server-side). Sets `customer_confirmed`, `otp_bypassed`, reason; runs the same ledger flow as `verify_delivery_otp`. |
| ERP "Bypass OTP" button (crate_delivery.js) | Red button on submitted, unconfirmed deliveries — shown only when `allow_otp_bypass` is on. Prompts for reason → confirm → calls `bypass_delivery_otp`. **ERPNext only — not in the mobile app.** |

### Order / Invoice item display (image + UOM)

| Change | Detail |
|---|---|
| `get_order_details` (mobile API) | Item rows now include `uom`. |
| `get_invoice_details` (mobile API) | Item rows now include `uom` **and** `image` (invoice items had no image before). |
| Review Order, Order Details, Invoice Details (Flutter) | Show item image + UOM in the qty line (e.g. `6 Crate × ₹600`). |

### Flutter — file structure & login/order screens

| Change | Detail |
|---|---|
| `lib/screens/` reorganized | 24 flat screen files moved into domain folders: `auth/`, `customer/`, `driver/`, `dispatch/`, `production/`, `master/`, `hr/`. All intra-app imports normalized to `package:bastar_dairy_farm/...` (location-independent). |
| `login_screen.dart` | Redesigned — animated gradient bg + floating glass orbs, glassmorphism form, staggered entrance, focus-aware inputs, gradient button, validators. |
| `order_placing_screen.dart` (Review Order) | Redesigned with `CustomAppBar` (app theme), delivery-preference cards, item cards with image + UOM, bill details, gradient place-order button with MOQ guard. |

---

## Fields Added via Code (auto-migrated — no manual step on prod)

These were added to doctype JSON files and will apply automatically on `bench migrate`:

| Doctype | Fieldname | Type | Notes |
|---|---|---|---|
| Crate Delivery | `otp_phone_override` | Data (Phone) | Allow on submit. Override number for OTP sending. |
| Vehicle Invoice Crate Detail | `balance_crate` label changed | — | Label changed to "Customer Balance"; now read_only; shows customer's current crate balance |
| Customer Crate Ledger | `entry_type` options | — | Added "Opening" and "Adjustment" options |
| Customer Crate Ledger | `crate_balance_adjustment` | Link (Crate Balance Adjustment) | Links ledger entry to its adjustment doc |
| Customer Crate Ledger | `warehouse` | Link (Warehouse) | Warehouse party on the ledger |
| Customer Crate Ledger | `ledger_type` options | — | Added "Warehouse" |
| Customer Crate Ledger | `crate_category` options | — | Added "Opening", "Adjustment" |
| Crate Settings | `allow_negative_crate` | Check | Allow adjustments below zero |
| Crate Balance Adjustment | `warehouse`, `driver_balance_type`, `crate_type`, balance HTML | mixed | Warehouse + loose crate support |
| Crate Delivery | `location_source`, `delivery_latitude`, `delivery_longitude`, `location_captured_at`, `location_map_html` | mixed | Delivery GPS capture |
| Material Gate Pass + Material Gate Pass Item | (new doctypes) | — | Material/transfer gate pass with one-way/return trips |
