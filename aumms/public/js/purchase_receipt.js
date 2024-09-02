frappe.ui.form.on('Purchase Receipt', {
  refresh (frm) {
    if ([1, 2].includes(frm.doc.docstatus)) {

      // Custom button Metal Ledger in View
      frm.add_custom_button('Metal Ledger', () => {
        // route to Metal Ledger Report with filter of this voucher no
        frappe.set_route('query-report', 'Metal Ledger', { 'voucher_no': frm.doc.name });
      }, 'View');
    }

    handle_hallmark_return_button(frm)

  },

    posting_date(frm) {
    //Changing the board rate on the changing of posting_date
    if(frm.doc.posting_date && frm.doc.posting_time) {
      frm.doc.items.forEach((child) => {
        //call to get board_rate
        set_board_rate(child)
    });
  }
},
    posting_time(frm) {
      //Changing the board rate on the changing of posting_time
      if(frm.doc.posting_date && frm.doc.posting_time) {
        frm.doc.items.forEach((child) => {
          //call to get board_rate
          set_board_rate(child)
       });
     }
   },
   supplier(frm) {
     //set the supplier type
     if(frm.doc.supplier) {
       frappe.call({
         method : 'aumms.aumms.doc_events.purchase_receipt.set_supplier_type',
         args : {
           supplier: frm.doc.supplier
         },
         callback : function(r) {
           if (r.message) {
             frm.doc.items.forEach((child) => {
               child.supplier_type = r.message
             })
           }
         }
       })
     }
   }
});

frappe.ui.form.on('Purchase Receipt Item', {
      item_code(frm, cdt, cdn) {
        let child = locals[cdt][cdn]
        if (child.item_code) {
          //to make delay in board_rate entry
          setTimeout(function () {
            //call to get board_rate
            set_board_rate(child)
          }, 500);
        }
      },
      items_add(frm, cdt, cdn) {
        let child = locals[cdt][cdn]
        //Checking the keep metal transaction
        if (frm.doc.keep_metal_ledger) {
          //set value to the field is keep_metal_ledger as 1
          frappe.model.set_value(child.doctype, child.name, 'keep_metal_ledger', 1)
}
        if(frm.doc.supplier) {
          console.log('in');
            set_board_rate_read_only(frm, cdt, cdn)
          }
      },
    board_rate (frm, cdt, cdn) {
      let child = locals[cdt][cdn]
      if (child.board_rate){
          // declare rate value as board rate
            let rate = child.board_rate
            if (child.conversion_factor) {
              // multiply rate with conversion factor
              rate = rate * child.conversion_factor
            }
            // set value to the rate field
            frappe.model.set_value(child.doctype, child.name, 'rate', rate)
        }
      },
    conversion_factor (frm, cdt, cdn) {
       let child = locals[cdt][cdn]
       if (child.conversion_factor) {
         // trigger board rate field
         frm.script_manager.trigger('board_rate', cdt, cdn);
       }
     }
  })

let set_board_rate = function (child) {
      //function to set board rate
        if (child.item_type){
        if (child.item_type && child.is_purity_item) {
          frappe.call({
              method : 'aumms.aumms.utils.get_board_rate',
              args: {
                item_type: child.item_type,
                stock_uom: child.stock_uom,
                date: cur_frm.doc.posting_date,
                time: cur_frm.doc.posting_time,
                purity: child.purity
              },
              callback : function(r) {
                if (r.message) {
                  frappe.model.set_value(child.doctype, child.name, 'board_rate', r.message)
                }
              }
          })
       }
      }
  }

let set_board_rate_read_only = function (frm, cdt, cdn) {
  //function for setting supplier type
  let child = locals[cdt][cdn]
    frappe.call({
      method : 'aumms.aumms.doc_events.purchase_receipt.set_supplier_type',
      args : {
        supplier: frm.doc.supplier
      },
      callback : function(r) {
        if (r.message) {
            frappe.model.set_value(child.doctype, child.name, 'supplier_type', r.message)
        }
      }
    })
}
