import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, now, nowtime

from dairy.franchise_pos.stock import (
	add_ledger_rows,
	check_day_open,
	invoice_stock_rows,
	need_pos_franchise,
	receipt_stock_date,
	remove_ledger_rows,
)


class FranchiseStockReceipt(Document):
	"""The franchise confirms a BDF delivery. The system makes it (Pending) when the BDF Sales Invoice is
	submitted; the franchise enters only what is short or damaged and submits. Only the good quantity
	goes into the franchise stock. Nothing here touches BDF stock or accounts."""

	def validate(self):
		need_pos_franchise(self.franchise)
		self.franchise_code = self.franchise
		other = frappe.db.get_value(
			self.doctype,
			{"sales_invoice": self.sales_invoice, "docstatus": ["<", 2], "name": ["!=", self.name or ""]},
		)
		if other:
			frappe.throw(_("Delivery {0} already exists for invoice {1}.").format(other, self.sales_invoice))
		self.set_items()
		self.status = "Pending"

	def set_items(self):
		"""Invoiced quantities always come from the invoice; only Short / Damaged / Reason are the franchise's."""
		inv = frappe.db.get_value("Sales Invoice", self.sales_invoice, ["customer", "posting_date", "docstatus"], as_dict=True)
		if not inv or inv.docstatus != 1:
			frappe.throw(_("Sales Invoice {0} is not submitted.").format(self.sales_invoice))
		if inv.customer != self.franchise:
			frappe.throw(_("Sales Invoice {0} is not for {1}.").format(self.sales_invoice, self.franchise))
		self.invoice_date = inv.posting_date
		entered = {d.item_code: d for d in self.items}
		# BDF credit notes made while the delivery was still waiting take the quantity off the delivery itself
		before_confirm = {}
		for c in self.get("credits") or []:
			if not flt(c.covered_qty) and not flt(c.stock_qty):
				before_confirm[c.item_code] = before_confirm.get(c.item_code, 0) + flt(c.qty)
		self.set("items", [])
		totals = dict(total_invoiced_qty=0, total_short_qty=0, total_damaged_qty=0, total_received_qty=0, loss_amount=0)
		for r in invoice_stock_rows(self.sales_invoice):
			if r.qty <= 0:
				continue
			billed = r.qty
			returned = flt(min(before_confirm.get(r.item_code, 0), billed), 3)
			r.qty = flt(billed - returned, 3)
			old = entered.get(r.item_code)
			short = flt(old.short_qty, 3) if old else 0
			damaged = flt(old.damaged_qty, 3) if old else 0
			if short < 0 or damaged < 0:
				frappe.throw(_("{0}: short and damaged cannot be negative.").format(r.item_name))
			if short + damaged > r.qty:
				frappe.throw(_("{0}: short + damaged ({1}) is more than invoiced ({2}).").format(
					r.item_name, flt(short + damaged, 3), r.qty))
			received = flt(r.qty - short - damaged, 3)
			loss = flt((short + damaged) * r.rate, 2)
			self.append("items", {
				"item_code": r.item_code, "item_name": r.item_name, "uom": r.uom, "invoiced_qty": r.qty,
				"billed_qty": billed, "returned_qty": returned,
				"short_qty": short, "damaged_qty": damaged, "received_qty": received,
				"reason": (old.reason if old and (short or damaged) else None), "rate": r.rate, "loss_amount": loss,
			})
			totals["total_invoiced_qty"] += r.qty
			totals["total_short_qty"] += short
			totals["total_damaged_qty"] += damaged
			totals["total_received_qty"] += received
			totals["loss_amount"] += loss
		for k, v in totals.items():
			self.set(k, flt(v, 2 if k == "loss_amount" else 3))
		self.open_loss_amount = self.loss_amount

	def before_submit(self):
		# the earliest franchise day still open, from the invoice date on (never a closed day)
		self.posting_date = receipt_stock_date(self.franchise, self.invoice_date)
		if not self.flags.system_confirm:
			check_day_open(self.franchise, self.posting_date, need_previous_closed=False)
		self.status = "Auto Received" if self.auto_received else (
			"Short Received" if (self.total_short_qty or self.total_damaged_qty) else "Received")
		self.source = self.source or ("System" if self.auto_received else "Desk")
		self.confirmed_by = frappe.session.user
		self.confirmed_on = now()

	def on_submit(self):
		add_ledger_rows([{
			"franchise": self.franchise, "item_code": d.item_code, "item_name": d.item_name, "uom": d.uom,
			"posting_date": self.posting_date, "posting_time": nowtime(), "qty": d.received_qty,
			"entry_type": "Received from BDF", "voucher_type": self.doctype, "voucher_no": self.name,
			"remarks": f"BDF invoice {self.sales_invoice}",
		} for d in self.items if flt(d.received_qty) > 0])
		if flt(self.total_short_qty) or flt(self.total_damaged_qty):
			# made in the background after this commit, so confirming in the app stays instant
			frappe.enqueue(
				"dairy.franchise_pos.doctype.franchise_stock_receipt.franchise_stock_receipt.make_credit_note_draft",
				queue="short", enqueue_after_commit=True, receipt=self.name,
			)

	def before_cancel(self):
		# the invoice itself being cancelled takes the stock back whatever the day (as before)
		if not self.flags.from_invoice_cancel:
			check_day_open(self.franchise, self.posting_date, need_previous_closed=False)

	def on_cancel(self):
		self.db_set("status", "Cancelled")
		remove_ledger_rows(self.doctype, self.name)


def on_doctype_update():
	frappe.db.add_index("Franchise Stock Receipt", ["franchise", "docstatus"])


def _credit_rows(credit_note):
	"""Stock rows of a credit note, as positive quantities."""
	return [frappe._dict(r, qty=-r.qty) for r in invoice_stock_rows(credit_note) if r.qty < 0]


def apply_credit_note(receipt_name, cn):
	"""SYSTEM ACTION: a BDF credit note against an invoice that has a franchise delivery.
	Waiting delivery: the quantity comes off the delivery (no stock row).
	Confirmed delivery: it first settles what the franchise marked short/damaged (no stock change); only the
	rest is goods sent back and comes off the franchise stock. Returns the stock rows to book."""
	doc = frappe.get_doc("Franchise Stock Receipt", receipt_name)
	rows = _credit_rows(cn.name)
	if doc.docstatus == 0:
		for r in rows:
			doc.append("credits", {"credit_note": cn.name, "posting_date": cn.posting_date, "item_code": r.item_code,
								"item_name": r.item_name, "qty": r.qty, "covered_qty": 0, "stock_qty": 0})
		doc.flags.ignore_permissions = True
		doc.save()
		if not flt(doc.total_invoiced_qty):
			confirm(doc)  # everything was credited: nothing left to check
		return []

	items = {d.item_code: d for d in doc.items}
	settled = {}
	for c in doc.credits:
		settled[c.item_code] = settled.get(c.item_code, 0) + flt(c.covered_qty)
	stock_rows = []
	for r in rows:
		d = items.get(r.item_code)
		lost = (flt(d.short_qty) + flt(d.damaged_qty)) if d else 0
		covered = flt(max(min(r.qty, lost - settled.get(r.item_code, 0)), 0), 3)
		settled[r.item_code] = settled.get(r.item_code, 0) + covered
		back = flt(r.qty - covered, 3)
		doc.append("credits", {"credit_note": cn.name, "posting_date": cn.posting_date, "item_code": r.item_code,
							"item_name": r.item_name, "qty": r.qty, "covered_qty": covered, "stock_qty": back})
		if back:
			stock_rows.append(frappe._dict(r, qty=-back))
	_save_credits(doc)
	return stock_rows


def remove_credit_note(receipt_name, credit_note):
	"""SYSTEM ACTION: the credit note was cancelled; its stock rows are removed by the caller."""
	doc = frappe.get_doc("Franchise Stock Receipt", receipt_name)
	keep = [c for c in doc.credits if c.credit_note != credit_note]
	if len(keep) == len(doc.credits):
		return
	if doc.docstatus == 0:
		doc.set("credits", keep)
		doc.flags.ignore_permissions = True
		doc.save()
		return
	for c in doc.credits:
		if c.credit_note == credit_note:
			frappe.db.delete("Franchise Stock Receipt Credit", {"name": c.name})
	doc.set("credits", keep)
	_save_credits(doc, insert=False)


def _save_credits(doc, insert=True):
	"""A confirmed delivery cannot be saved again: write the credit rows and the settled figures directly."""
	settled = {}
	for i, c in enumerate(doc.credits, 1):
		c.idx = i
		if insert and c.is_new():
			c.db_insert()
		settled[c.item_code] = settled.get(c.item_code, 0) + flt(c.covered_qty)
	open_loss = 0
	for d in doc.items:
		d.db_set("credited_qty", flt(settled.get(d.item_code), 3), update_modified=False)
		open_loss += (flt(d.short_qty) + flt(d.damaged_qty) - flt(settled.get(d.item_code))) * flt(d.rate)
	doc.db_set("open_loss_amount", flt(max(open_loss, 0), 2))


def make_credit_note_draft(receipt):
	"""SYSTEM ACTION (background job): a DRAFT return invoice against the BDF invoice for what the franchise marked
	short / damaged, at the invoice rate, in stock units. It is never submitted here: the Sales Invoice Return
	workflow (Billing Executive -> Return Approver) decides. Once approved, apply_credit_note settles the shortage.
	One draft per delivery; a failure is written on the delivery so billing can make it by hand."""
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_sales_return

	doc = frappe.get_doc("Franchise Stock Receipt", receipt)
	if doc.docstatus != 1:
		return
	if doc.credit_note and frappe.db.get_value("Sales Invoice", doc.credit_note, "docstatus") in (0, 1):
		return  # already made and still alive
	need = {d.item_code: flt(d.short_qty) + flt(d.damaged_qty) - flt(d.credited_qty) for d in doc.items}
	need = {k: flt(v, 3) for k, v in need.items() if v > 0}
	if not need:
		return
	reasons = {d.item_code: d.reason for d in doc.items if d.item_code in need}
	frappe.db.savepoint("fpos_credit_note")
	try:
		cn = make_sales_return(doc.sales_invoice)
		rows = []
		for r in cn.items:
			left = need.get(r.item_code, 0)
			cf = flt(r.conversion_factor) or 1
			row_stock = abs(flt(r.qty)) * cf  # what this invoice row can still take back, in stock units
			if left <= 0 or row_stock <= 0:
				continue
			take = flt(min(left, row_stock), 3)
			need[r.item_code] = left - take
			# in stock units, so 4 packets stay 4 packets (not 0.2 crate)
			r.price_list_rate = flt(r.price_list_rate) / cf
			r.rate = flt(r.rate) / cf
			r.uom, r.conversion_factor = r.stock_uom, 1
			r.qty, r.stock_qty = -take, -take
			rows.append(r)
		if not rows:
			raise frappe.ValidationError(_("Nothing left on the invoice to return."))
		cn.set("items", rows)
		for i, r in enumerate(cn.items, 1):
			r.idx = i
		cn.set("payments", [])
		cn.remarks = _("Short / damaged on franchise delivery {0}: {1}").format(
			doc.name, ", ".join(f"{k} ({reasons.get(k) or '-'})" for k in reasons))
		cn.flags.ignore_permissions = True  # the franchise login cannot make invoices; approval stays with BDF
		cn.insert()
		doc.db_set({"credit_note": cn.name, "credit_note_error": None})
	except Exception as e:
		frappe.db.rollback(save_point="fpos_credit_note")
		frappe.log_error(frappe.get_traceback(), f"Franchise delivery {receipt}: draft credit note")
		frappe.db.set_value("Franchise Stock Receipt", receipt, "credit_note_error", frappe.utils.strip_html(str(e))[:500],
							update_modified=False)
	frappe.db.commit()


def confirm(doc, auto=False):
	"""SYSTEM ACTION used by the scheduler / auto close: confirm a pending delivery with the full quantity."""
	doc.auto_received = 1 if auto else doc.auto_received
	if auto:
		for d in doc.items:
			d.short_qty = d.damaged_qty = 0
		doc.remarks = doc.remarks or _("Confirmed by the system: the franchise did not confirm the delivery in time.")
	doc.flags.ignore_permissions = True
	doc.flags.system_confirm = True
	doc.source = "System"
	doc.save()
	doc.submit()
	return doc

