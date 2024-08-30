import frappe
from frappe import _
from frappe.model.document import Document

class HallmarkRequest(Document):
    def on_update_after_submit(self):
        if self.workflow_state == "Sent for Hallmarking":
            self.create_stock_entry()
        if self.workflow_state == "Items Hallmarked":
            self.create_stock_entry_to_finished_goods()

    def create_stock_entry(self):
        stock_entry = frappe.new_doc("Stock Entry")
        stock_entry.stock_entry_type = "Material Transfer"
        stock_entry.from_warehouse = frappe.db.get_value("Warehouse", {"name": ["like", "%Stores%"]}, "name")
        stock_entry.to_warehouse = frappe.db.get_value("Warehouse", {"name": ["like", "%Work In Progress%"]}, "name")

        for item in self.items:
            stock_entry.append("items", {
                'item_code': item.item_code,
                'qty': 1,
                'uom': "Nos",
            })
        
        self.submit_stock_entry(stock_entry, "Stock Entry to Work In Progress")

    def create_stock_entry_to_finished_goods(self):
        stock_entry = frappe.new_doc("Stock Entry")
        print("\n\n\n")
        print('stock_entry', stock_entry)
        stock_entry.stock_entry_type = "Material Transfer"
        from_warehouse = frappe.db.get_value("Warehouse", {"name": ["like", "%Work In Progress%"]}, "name")
        to_warehouse = frappe.db.get_value("Warehouse", {"name": ["like", "%Finished Goods%"]}, "name")

        for item in self.items:
            stock_entry.append("items", {
                'item_code': item.item_code,
                'qty': 1,
                'uom': "Nos",
                's_warehouse': from_warehouse,
                't_warehouse': to_warehouse 
            })

        self.submit_stock_entry(stock_entry, "Stock Entry to Finished Goods")

    def submit_stock_entry(self, stock_entry, entry_type):
        try:
            stock_entry.insert()
            stock_entry.submit()
            frappe.db.commit()
            frappe.msgprint(_(f"{entry_type} {stock_entry.name} created and submitted"))
        except Exception as e:
            frappe.db.rollback()
            frappe.log_error(f"Failed to create {entry_type} for Hallmark Request {self.name}: {str(e)}")
            frappe.throw(_(f"Failed to create {entry_type}. Please check the error log."))

