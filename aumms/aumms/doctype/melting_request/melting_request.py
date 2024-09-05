# Copyright (c) 2024, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class MeltingRequest(Document):
	def on_submit(self):
		self.update_items_tables()
  
	def on_update_after_submit(self):
		if self.workflow_state != self._doc_before_save.workflow_state:
			self.create_stock_entry()

	def create_stock_entry(self):
		old_doc = self._doc_before_save
		if old_doc.workflow_state == self.workflow_state:
			return
		stock_entry = frappe.new_doc("Stock Entry")
		stock_entry.stock_entry_type = "Material Transfer"
		if self.workflow_state == "Issued for Melting":
			stock_entry.from_warehouse = frappe.db.exists(
				"Warehouse", {"name": ["Like", "%Stores%"]}
			)
			stock_entry.to_warehouse = frappe.db.exists(
				"Warehouse", {"name": ["Like", "%Work In Progress%"]}
			)

			for item in self.items:
				stock_entry.append(
					"items",
					{
						"item_code": item.item_code,
						"qty": 1,
						"basic_rate": item.amount,
						"uom": "Nos",
						"valuation_rate": item.amount,
						"additional_cost": item.hallmarking_cost,
					},
				)
		elif self.workflow_state == "Items Melted":
			stock_entry.from_warehouse = frappe.db.exists(
				"Warehouse", {"name": ["Like", "%Work In Progress%"]}
			)
			stock_entry.to_warehouse = frappe.db.exists(
				"Warehouse", {"name": ["Like", "%Raw Materials%"]}
			)

			for item in self.items:
				stock_entry.append(
					"items",
					{
						"item_code": item.item_code,
						"qty": 1,
						"basic_rate": item.amount,
						"uom": "Nos",
						"valuation_rate": item.amount,
						"additional_cost": item.hallmarking_cost,
					},
				)

		self.submit_stock_entry(stock_entry, "Stock Entry to Work In Progress")
		create_metal_ledger_entries_for_hallmarking(self)

	def update_items_tables(self):
		for item in self.items:
			self.append("gold_weight_detail", {"item": item.item_code})
			self.save()
   
@frappe.whitelist()
def create_metal_ledger_entries_for_hallmarking(doc, hallmark_return=False):
	"""
		method to create metal ledger entries
		args:
			doc: object of purchase Receipt doctype and Sales Invoice doctype
			method: on submit of purchase reciept and Sales Invoice
		output:
			new metal ledger entry doc
	"""

	# get default company
	company = frappe.defaults.get_defaults().company

	# set dict of fields for metal ledger entry
	fields = {
		'doctype': 'Metal Ledger Entry',
		'posting_date': frappe.utils.get_datetime().date(),
		'posting_time': frappe.utils.get_datetime().time(),
		'voucher_type': doc.doctype,
		'voucher_no': doc.name,
		'company': company,
	}

	# set party type and party in fields if doctype is Purchase Receipt
	if doc.doctype == 'Melting Request':
		fields['party_type'] = 'Supplier'
		fields['party'] = doc.assay_center_warehouse

	# declare ledger_created as false
	ledger_created = 0
	for item in doc.items:    
		aumms_item_doc = frappe.get_doc("AuMMS Item", item.item_code)

		# set item details in fields
		fields['item_code'] = item.item_code
		fields['item_name'] = item.item_name
		fields['stock_uom'] = frappe.db.get_value("Purchase Receipt Item", {"parent":doc.reference, "item_code":item.item_code}, "weight_uom")
		fields['purity'] = aumms_item_doc.purity
		fields['purity_percentage'] = aumms_item_doc.purity_percentage
		fields['board_rate'] = frappe.db.get_value("Purchase Receipt Item", {"parent":doc.reference, "item_code":item.item_code}, "rate")
		fields['batch_no'] = frappe.db.get_value("Purchase Receipt Item", {"parent":doc.reference, "item_code":item.item_code}, "batch_no")
		fields['item_type'] = aumms_item_doc.item_type
		# get balance qty of the item for this party
		filters = {
			'item_type': aumms_item_doc.item_type,
			'purity': aumms_item_doc.purity,
			'stock_uom': frappe.db.get_value("Purchase Receipt Item", {"parent":doc.reference, "item_code":item.item_code}, "weight_uom"),
			'party_link': doc.assay_center_warehouse,
			'is_cancelled': 0
			}
		balance_qty = frappe.db.get_value('Metal Ledger Entry', filters, 'balance_qty')

		if doc.workflow_state == "Issued for Melting" and (doc.workflow_state != doc._doc_before_save.workflow_state):
			# update balance_qtydirection
			balance_qty = balance_qty+item.gold_weight if balance_qty else item.gold_weight
			fields['out_qty'] = item.gold_weight
			fields['outgoing_rate'] = frappe.db.get_value("Purchase Receipt Item", {"parent":doc.reference, "item_code":item.item_code}, "rate")
			fields['balance_qty'] = balance_qty
			fields['amount'] = -item.amount
		elif doc.workflow_state == "Items Melted" and (doc.workflow_state != doc._doc_before_save.workflow_state):
			balance_qty = balance_qty-item.gold_weight if balance_qty else -item.gold_weight
			fields['incoming_rate'] = frappe.db.get_value("Purchase Receipt Item", {"parent":doc.reference, "item_code":item.item_code}, "rate")
			fields['in_qty'] = item.gold_weight
			for g_item in doc.gold_weight_detail:
				if item.item_code == g_item.item:
					fields['in_qty'] - g_item.gold_weight_loss_after_melting
			fields['balance_qty'] = balance_qty
			fields['amount'] = item.amount
		else:
			# update balance_qty
			balance_qty = balance_qty-item.gold_weight if balance_qty else -item.gold_weight
			fields['incoming_rate'] = frappe.db.get_value("Purchase Receipt Item", {"parent":doc.reference, "item_code":item.item_code}, "rate")
			fields['out_qty'] = item.gold_weight
			fields['balance_qty'] = balance_qty
			fields['amount'] = item.amount

		# create metal ledger entry doc with fields
		aumms_item_doc.save()
		frappe.get_doc(fields).insert(ignore_permissions = 1)
		ledger_created = 1

	# alert message if metal ledger is created
	if ledger_created:
		frappe.msgprint(
			msg = _(
				'Metal Ledger Entry is created.'
			),
			indicator="green",
			alert = 1
		)
