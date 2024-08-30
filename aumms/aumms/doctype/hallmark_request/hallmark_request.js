// Copyright (c) 2024, efeone and contributors
// For license information, please see license.txt


// frappe.ui.form.on('Hallmark Request', {
//     refresh: function(frm) {
//         if (frm.doc.docstatus === 1) {
//             frm.add_custom_button(__('Create Stock Entry'), function() {
//                 frappe.call({
//                     method: 'aumms.aumms.doctype.hallmark_request.hallmark_request.make_stock_entry',
//                     args: {
//                         'source_name': frm.doc.name
//                     },
//                     callback: function(r) {
//                         if (r.message) {
//                             frappe.set_route('Form', 'Stock Entry', r.message.name);
//                         }
//                     }
//                 });
//             });
//         }
//     }
// });


