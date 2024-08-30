import frappe
from frappe import _
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice

def purchase_receipt_on_submit(doc, method):
    ''' Method to trigger Purchase Receipt on_submit '''
    if doc.create_invoice_on_submit:
        create_purchase_invoice(doc)
        
def purchase_receipt_on_update_after_submit(doc, method):
    """
    Create Hallmark Request On Submission of Purchase Receipt
    """
    # Create a new Hallmark Request document
    hallmark = frappe.new_doc('Hallmark Request')
    
    # Assign values from Purchase Receipt to Hallmark Request
    hallmark.supplier = doc.supplier
    hallmark.supplier_name = doc.supplier_name
    hallmark.posting_date = doc.posting_date
    
    # Populate the items table in Hallmark Request from Purchase Receipt items
    for item in doc.items:
        hallmark.append('items', {
            'item_code': item.item_code,
            'item_name': item.item_name,
            # Adjusted to match the correct field
            
            'total_weight': item.total_weight,  # Add other necessary fields
            
        })
    
    # Save and submit the Hallmark Request
   
    hallmark.submit()
    
    frappe.msgprint("Hallmark Request has been created and submitted successfully.")


   
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
