frappe.ui.form.on("Raw Material Bundle", {
    refresh: function(frm) {
        frm.set_query("item", "items", () => {
            return {
                filters: {
                    "custom_is_raw_material": 1
                }
            };
        });
    },
    on_submit: function(frm) {
        if (!frm.doc.raw_material_available) {
            frm.add_custom_button('Create Raw Material Request', () => {
                frappe.call({
                    method: 'aumms.aumms_manufacturing.doctype.raw_material_bundle.raw_material_bundle.create_raw_material_request',
                    args: {
                        docname: frm.doc.name
                    },
                    freeze: true,
                    callback: (r) => {
                        frm.reload_doc();
                    }
                });
            });
        }
    }
});

// frappe.ui.form.on("Raw Material Details", {
//     purity_of_required_item: function(frm, cdt, cdn) {
//         let d = locals[cdt][cdn];
//         if (d.required_purity_percentage < d.available_purity_percentage) {
//             let alloy_weight = ((d.required_purity_percentage / d.available_purity_percentage) * d.available_weight);
//             frappe.model.set_value(cdt, cdn, 'alloy_weight', alloy_weight);
//          }
//        },
//   purity_of_available_item: function(frm, cdt, cdn) {
//     let d = locals[cdt][cdn];
//     if (d.required_purity_percentage < d.available_purity_percentage) {
//       let alloy_weight = ((d.required_purity_percentage / d.available_purity_percentage) * d.available_weight);
//       frappe.model.set_value(cdt, cdn, 'alloy_weight', alloy_weight);
//
//           let row = frappe.model.add_child(frm.doc, 'items');
//           row.item = d.alloy_name;
//           row.alloy_weight = d.alloy_weight;
//           row.alloy_name = d.alloy_name;
//           row.uom = d.uom;
//           row.quantity = d.required_quantity;
//             frm.refresh_field('items');
//         }
//     },
//     // alloy_details: function(frm, cdt, cdn) {
//     //     let d = locals[cdt][cdn];
//     //     let alloy_weight = d.alloy_weight;
//     //     let uom = d.uom;
//     //     let alloy_name = d.item;
//     //     let dialog = new frappe.ui.Dialog({
//     //         title: 'Alloy Details',
//     //         fields: [
//     //             {
//     //                 label: 'UOM',
//     //                 fieldname: 'uom',
//     //                 fieldtype: 'Link',
//     //                 options: 'UOM',
//     //                 default: uom,
//     //                 reqd: 1
//     //             },
//     //             {
//     //                 label: 'Alloy Weight',
//     //                 fieldname: 'alloy_weight',
//     //                 fieldtype: 'Float',
//     //                 default: alloy_weight
//     //             },
//     //             {
//     //                 label: 'Alloy Name',
//     //                 fieldname: 'alloy_name',
//     //                 fieldtype: 'Data',
//     //                 default: alloy_name
//     //             }
//     //         ],
//     //         primary_action_label: 'Add to Item',
//     //         primary_action: function(values) {
//     //             let child = locals[cdt][cdn];
//     //             if (!child) {
//     //                 child = frm.add_child('items');
//     //             }
//     //             child.uom = values.uom;
//     //             child.alloy_weight = values.alloy_weight;
//     //             child.alloy_name = values.alloy_name;
//     //             frm.refresh_field('items');
//     //             dialog.hide();
//     //         }
//     //     });
//     //     dialog.show();
//     // }
//   });
