# Copyright (c) 2024, efeone and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class HallmarkRequest(Document):
    def on_update_after_submit(self):
        if self.workflow_state == "Sent for Hallmarking":
            self.create_stock_entry()
        elif self.workflow_state == "Items Hallmarked":
            self.create_stock_entry_to_finished_goods()

    def create_stock_entry(self):
        old_doc = self._doc_before_save
        if old_doc.workflow_state == self.workflow_state:
            return
        try:
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.stock_entry_type = "Material Transfer"
            stock_entry.from_warehouse = frappe.db.exists(
                "Warehouse", {"name": ["Like", "%Stores%"]}
            )
            stock_entry.to_warehouse = frappe.db.exists(
                "Warehouse", {"name": ["Like", f"%{self.hallmarking_warehouse}%"]}
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
        except Exception as e:
            frappe.log_error(f"Error Occurred in create_stock_entry: {e}")
            frappe.throw(
                _(
                    "Something went wrong while creating Stock Entry. Please check the error log."
                )
            )

    def create_stock_entry_to_finished_goods(self):
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Transfer"
        from_warehouse = frappe.db.exists(
            "Warehouse", {"name": ["Like", f"%{self.hallmarking_warehouse}%"]}
        )
        to_warehouse = frappe.db.get_value(
            "Warehouse", {"name": ["like", "%Finished Goods%"]}, "name"
        )

        for item in self.hallmark_return_details:
            if item.broken:
                to_warehouse = frappe.db.get_value(
                    "Warehouse", {"name": ["like", "%Scrap%"]}, "name"
                )
            else:
                to_warehouse = frappe.db.get_value(
                    "Warehouse", {"name": ["like", "%Finished Goods%"]}, "name"
                )
            stock_entry.append(
                "items",
                {
                    "item_code": item.item_code,
                    "qty": 1,
                    "uom": "Nos",
                    "s_warehouse": from_warehouse,
                    "t_warehouse": to_warehouse,
                },
            )

        self.submit_stock_entry(stock_entry, "Stock Entry to Finished Goods")
        create_metal_ledger_entries_for_hallmarking(self, True)

        for item in self.hallmark_return_details:
            if not item.broken:
                frappe.db.set_value(
                    "AuMMS Item", {"item_name", item.item_code}, "hallmarked", 1
                )

    def submit_stock_entry(self, stock_entry, entry_type):
        try:
            stock_entry.submit()
            frappe.msgprint(_(f"{entry_type} {stock_entry.name} created and submitted"))
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(
                f"Failed to create {entry_type} for Hallmark Request {self.name}: {str(e)}"
            )
            frappe.throw(
                _(f"Failed to create {entry_type}. Please check the error log.")
            )

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
    if doc.doctype == 'Hallmark Request':
        fields['party_type'] = 'Supplier'
        fields['party'] = doc.supplier

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
            'party_link': doc.supplier,
            'is_cancelled': 0
            }
        balance_qty = frappe.db.get_value('Metal Ledger Entry', filters, 'balance_qty')

        if doc.hallmark_return_details:
            # update balance_qtydirection
            balance_qty = balance_qty+item.gold_weight if balance_qty else item.gold_weight
            fields['in_qty'] = item.gold_weight
            for h_item in doc.hallmark_return_details:
                if h_item.gold_weight_loss:
                    if h_item.gold_weight_loss > 0:
                        fields['in_qty'] = item.gold_weight - h_item.gold_weight_loss
                        aumms_item_doc.weight_per_unit - h_item.gold_weight_loss
                        aumms_item_doc.gold_weight - h_item.gold_weight_loss
            fields['outgoing_rate'] = frappe.db.get_value("Purchase Receipt Item", {"parent":doc.reference, "item_code":item.item_code}, "rate")
            fields['balance_qty'] = balance_qty
            fields['amount'] = -item.amount

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
