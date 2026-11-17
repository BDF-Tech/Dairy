import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt, getdate, nowtime, today

from dairy.franchise_pos.stock import (
	add_ledger_rows,
	check_day_open,
	get_balances,
	get_mrp,
	get_settings,
	need_pos_franchise,
	remove_ledger_rows,
)


class FranchiseSale(Document):
	"""The bill a franchise gives its own buyer. It only moves the franchise's stock book:
	no BDF stock ledger, no BDF accounts."""

	def validate(self):
		need_pos_franchise(self.franchise)
		self.franchise_code = self.franchise  # the Link shows the customer's name; this shows the code
		self.posting_date = self.posting_date or today()
		self.posting_time = self.posting_time or nowtime()
		if getdate(self.posting_date) > getdate(today()):
			frappe.throw(_("A bill cannot be dated in the future."))
		check_day_open(self.franchise, self.posting_date)
		if not self.is_return:
			self.return_against = None
		self.set_items()

	def set_items(self):
		if not self.items:
			frappe.throw(_("Add at least one item."))
		codes = [d.item_code for d in self.items]
		if len(codes) != len(set(codes)):
			frappe.throw(_("The same item is entered twice. Keep one line per item."))

		info = {
			i.name: i
			for i in frappe.get_all("Item", filters={"name": ["in", codes]}, fields=["name", "item_name", "stock_uom"])
		}
		# a sale is always at MRP; a return is always at the rate of the bill it reverses
		rates = self.return_rates() if self.is_return else get_mrp(codes, self.posting_date)

		self.total_qty = self.grand_total = 0
		for d in self.items:
			if flt(d.qty) <= 0:
				frappe.throw(_("Row {0}: quantity must be more than zero.").format(d.idx))
			d.item_name, d.uom = info[d.item_code].item_name, info[d.item_code].stock_uom
			d.rate = flt(rates.get(d.item_code))
			if not d.rate:
				frappe.throw(_("Row {0}: MRP is not set for {1}.").format(d.idx, frappe.bold(d.item_name)))
			d.amount = flt(flt(d.qty) * d.rate, 2)
			self.total_qty += flt(d.qty)
			self.grand_total += d.amount
		self.grand_total = flt(self.grand_total, 2)

	def return_rates(self):
		"""Checks the return against the original bill and gives back that bill's rates."""
		if not self.return_against:
			frappe.throw(_("Choose the bill this return is against."))
		orig = frappe.db.get_value(
			"Franchise Sale", self.return_against, ["franchise", "docstatus", "is_return", "payment_mode"], as_dict=True
		)
		if not orig or orig.docstatus != 1 or orig.is_return:
			frappe.throw(_("{0} is not a submitted bill.").format(self.return_against))
		if orig.franchise != self.franchise:
			frappe.throw(_("Bill {0} belongs to another franchise.").format(self.return_against))
		self.payment_mode = orig.payment_mode

		sold = {
			r.item_code: r
			for r in frappe.get_all(
				"Franchise Sale Item", filters={"parent": self.return_against, "parenttype": "Franchise Sale"},
				fields=["item_code", "qty", "rate"],
			)
		}
		already = dict(
			frappe.db.sql(
				"""select i.item_code, sum(i.qty) from `tabFranchise Sale Item` i
				join `tabFranchise Sale` s on s.name = i.parent
				where s.return_against = %s and s.docstatus = 1 and s.is_return = 1 and s.name != %s
				group by i.item_code""",
				(self.return_against, self.name or ""),
			)
		)
		for d in self.items:
			if d.item_code not in sold:
				frappe.throw(_("Row {0}: {1} is not on bill {2}.").format(d.idx, d.item_code, self.return_against))
			left = flt(sold[d.item_code].qty) - flt(already.get(d.item_code))
			if flt(d.qty) > left + 0.0001:
				frappe.throw(
					_("Row {0}: only {1} of {2} can still be returned.").format(d.idx, left, d.item_code)
				)
		return {code: r.rate for code, r in sold.items()}

	def before_submit(self):
		# checked before anything is written, so a refused bill leaves no trace
		if not self.is_return and not get_settings().allow_negative_stock:
			balances = get_balances(self.franchise, items=[d.item_code for d in self.items])
			for d in self.items:
				have = flt(balances.get(d.item_code))
				if flt(d.qty) > have + 0.0001:
					frappe.throw(
						_("Not enough stock of {0}: {1} {2} in hand, {3} billed.").format(
							frappe.bold(d.item_name), have, d.uom, flt(d.qty)
						),
						title=_("Not enough stock"),
					)

	def on_submit(self):
		sign = 1 if self.is_return else -1
		add_ledger_rows([
			{
				"franchise": self.franchise, "item_code": d.item_code, "item_name": d.item_name, "uom": d.uom,
				"posting_date": self.posting_date, "posting_time": self.posting_time, "qty": sign * flt(d.qty),
				"entry_type": "Sale Return" if self.is_return else "Sale",
				"voucher_type": self.doctype, "voucher_no": self.name,
			}
			for d in self.items
		])

	def before_cancel(self):
		check_day_open(self.franchise, self.posting_date)
		if not self.is_return and frappe.db.exists(
			"Franchise Sale", {"return_against": self.name, "docstatus": 1, "is_return": 1}
		):
			frappe.throw(_("This bill has a return against it. Cancel the return first."))

	def on_cancel(self):
		remove_ledger_rows(self.doctype, self.name)


def on_doctype_update():
	frappe.db.add_index("Franchise Sale", ["franchise", "posting_date"])
