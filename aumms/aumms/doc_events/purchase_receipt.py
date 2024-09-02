import frappe
from frappe import _
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

def purchase_receipt_on_submit(doc, method):
    ''' Method to trigger Purchase Receipt on_submit '''
    if doc.create_invoice_on_submit:
        create_purchase_invoice(doc)
        
def purchase_receipt_on_update_after_submit(doc, method=None):
    print(doc.workflow_state == "Sent for Hallmarking", doc.custom_hallmarking_details, not doc.custom_hallmark_return)
    if doc.workflow_state == "Sent for Hallmarking" and not doc.custom_sent_for_hallmarking:
        hallmarking_entry = frappe.new_doc("Stock Entry")
        hallmarking_entry.stock_entry_type = "Material Transfer"
        hallmarking_entry.from_warehouse = frappe.db.exists("Warehouse", {"name":["like", "%Stores%"]})
        hallmarking_entry.to_warehouse = frappe.db.exists("Warehouse", {"name":["like", "%Work In Progress%"]})
        for item in doc.items:
            hallmarking_entry.append("items", {
                "item_code": item.item_code,
                "qty": item.qty,
                "uom": item.uom,
                "basic_rate": item.base_rate,
                "additional_cost": frappe.db.get_single_value("AuMMS Settings", "hallmarking_cost_per_item")
            })
        hallmarking_entry.submit()
        # create_metal_ledger_entries_for_hallmarking(doc, False)
        doc.custom_sent_for_hallmarking = 1
        doc.save()
    elif doc.workflow_state == "Sent for Hallmarking" and doc.custom_hallmarking_details and not doc.custom_hallmark_return:
        hallmarked_entry = frappe.new_doc("Stock Entry")
        hallmarked_entry.stock_entry_type = "Material Transfer"
        hallmarked_entry.from_warehouse = frappe.db.exists("Warehouse", {"name":["like", "%Work In Progress%"]})
        hallmarked_entry.to_warehouse = frappe.db.exists("Warehouse", {"name":["like", "%Finished Goods%"]})
        for item in doc.custom_hallmarking_details:
            if not item.broken:
                hallmarked_entry.append("items", {
                    "item_code": item.item_code,
                    "qty": frappe.db.get_value("Purchase Receipt Item", {"item_code": item.item_code, "parent":doc.name}, "qty"),
                    "uom": frappe.db.get_value("Purchase Receipt Item", {"item_code": item.item_code, "parent":doc.name}, "uom"),
                    "basic_rate": frappe.db.get_value("Purchase Receipt Item", {"item_code": item.item_code, "parent":doc.name}, "base_rate"),
                })
                frappe.db.get_value("AuMMS Item", item.item_code, "hallmarked", 1)
            else:
                hallmarked_entry.append("items", {
                    "item_code": item.item_code,
                    "qty": frappe.db.get_value("Purchase Receipt Item", {"item_code": item.item_code, "parent":doc.name}, "qty"),
                    "uom": frappe.db.get_value("Purchase Receipt Item", {"item_code": item.item_code, "parent":doc.name}, "uom"),
                    "basic_rate": frappe.db.get_value("Purchase Receipt Item", {"item_code": item.item_code, "parent":doc.name}, "base_rate"),
                    "t_warehouse": frappe.db.exists("Warehouse", {"name":["like", "%Scrap%"]})
                })
        hallmarked_entry.submit()
        # create_metal_ledger_entries_for_hallmarking(doc, True)
        doc.custom_hallmark_return = 1
        doc.workflow_state = "Items Hallmarked"
        doc.save()
        
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
        'party_link': doc.party_link
    }

    # set party type and party in fields if doctype is Purchase Receipt
    if doc.doctype == 'Purchase Receipt':
        fields['party_type'] = 'Supplier'
        fields['party'] = doc.supplier

    # check items is keep_metal_ledger
    if doc.keep_metal_ledger:
        # declare ledger_created as false
        ledger_created = 0
        for h_item in doc.custom_hallmarking_details:
                for item in doc.items:
                    if item.item_code == h_item.item_code:
                        break
            
                aumms_item_doc = frappe.get_doc("AuMMS Item", item.item_code)

                # set item details in fields
                fields['item_code'] = item.item_code
                fields['item_name'] = item.item_name
                fields['stock_uom'] = item.weight_uom
                fields['purity'] = aumms_item_doc.purity
                fields['purity_percentage'] = aumms_item_doc.purity_percentage
                fields['board_rate'] = item.rate
                fields['batch_no'] = item.batch_no
                fields['item_type'] = aumms_item_doc.item_type
                # get balance qty of the item for this party
                filters = {
                    'item_type': aumms_item_doc.item_type,
                    'purity': aumms_item_doc.purity,
                    'stock_uom': item.weight_uom,
                    'party_link': doc.party_link,
                    'is_cancelled': 0
                    }
                balance_qty = frappe.db.get_value('Metal Ledger Entry', filters, 'balance_qty')

                if hallmark_return:
                    # update balance_qtydirection
                    balance_qty = balance_qty+item.total_weight if balance_qty else item.total_weight
                    fields['in_qty'] = item.total_weight
                    if h_item.gold_weight_loss:
                        if h_item.gold_weight_loss > 0:
                            fields['in_qty'] = item.total_weight - h_item.gold_weight_loss
                            aumms_item_doc.weight_per_unit - h_item.gold_weight_loss
                            aumms_item_doc.gold_weight - h_item.gold_weight_loss
                    fields['outgoing_rate'] = item.rate
                    fields['balance_qty'] = balance_qty
                    fields['amount'] = -item.amount

                else:
                    # update balance_qty
                    balance_qty = balance_qty-item.total_weight if balance_qty else -item.total_weight
                    fields['incoming_rate'] = item.rate
                    fields['out_qty'] = item.total_weight
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

@frappe.whitelist()
def create_purchase_invoice(doc):
    """
        method to create Purchase Invoice
        args:
            doc: object of purchase Receipt doctype
            method: on submit of purchase reciept
        output: new purchase invoice doc
    """
    # using purchase invoice creation function from purchase receipt
    purchase_invoice = make_purchase_invoice(doc.name).insert(ignore_permissions = 1)
    # message to user after creation of purchase receipt
    frappe.msgprint(_('Purchase Invoice created for the Supplier {0}'.format(doc.supplier)), indicator="green", alert = 1)
    if purchase_invoice:
        if purchase_invoice.docstatus == 0:
            purchase_invoice.submit()
        set_purchase_invoice_link_to_jewellery_invoice(doc.name, purchase_invoice.name)
    return purchase_invoice


@frappe.whitelist()
def check_is_purity_item(item_type):
    ''' Method for fetching items with is_purity_item as 1 '''
    is_purity = ''
    if frappe.db.exists('Item Type', {'name': item_type, 'is_purity_item': 1}):
        is_purity = frappe.db.get_value('Item Type', {'name': item_type , 'is_purity_item': 1}, 'is_purity_item')
    return is_purity

@frappe.whitelist()
def set_supplier_type (supplier):
    ''' Method for setting supplier type in purchase receipt item'''
    if frappe.db.exists('Supplier', supplier, 'supplier_type'):
        supplier_type = frappe.db.get_value('Supplier', supplier, 'supplier_type')
    return supplier_type

def set_purchase_invoice_link_to_jewellery_invoice(purchase_receipt, purchase_invoice):
    if frappe.db.exists('Jewellery Invoice', { 'purchase_receipt':purchase_receipt }):
        invoice_id = frappe.db.get_value('Jewellery Invoice', { 'purchase_receipt':purchase_receipt })
        frappe.db.set_value('Jewellery Invoice', invoice_id, 'purchase_invoice', purchase_invoice)
        frappe.db.commit()



def create_hallmark_request_from_purchase_receipt(doc, method=None):

    if doc.workflow_state == "Sent for Hallmarking":

        try:
                
            hallmark_request = frappe.new_doc("Hallmark Request")
            hallmark_request.reference_type = "Purchase Receipt"
            hallmark_request.reference = doc.name

            for item in doc.items:
                if frappe.db.get_value("AuMMS Item", item.item_code, "hallmarked"):
                    continue
                hallmark_request.append("items", {
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "gold_weight": frappe.get_value("Item", {"item_name":item.item_name},"gold_weight"),
                    "total_weight": frappe.get_value("Item", {"item_name":item.item_name},"weight_per_unit"),
                    "base_rate": item.rate,
                    "amount":item.amount
                })
                
            
            hallmark_request.save()
            frappe.msgprint(f"Hallmark Request {hallmark_request} Created", alert=True)
        except Exception as e:
                frappe.log_error(f"Failed to create Hallmark Request from Purchase Receipt {doc.name}: {str(e)}")  
                frappe.msgprint("Failed to create Hallmark Request. Please check the error log.", indicator="red")


