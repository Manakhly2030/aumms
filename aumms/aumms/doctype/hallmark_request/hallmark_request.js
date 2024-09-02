// Copyright (c) 2024, efeone and contributors
// For license information, please see license.txt

frappe.ui.form.on("Hallmark Request", {
  refresh: function(frm) {
    handle_hallmark_return_button(frm)
  }
})

frappe.ui.form.on("Hallmark Items", {
  hallmarking_cost: function (frm, cdt, cdn) {
    calculate_totals(frm);
  },
});

function calculate_totals(frm) {
  var total_hallmarking_cost = 0;
  frm.doc.items.forEach((row) => {
    total_hallmarking_cost += row.hallmarking_cost;
  });
  frm.set_value("total_hallmarking_cost", total_hallmarking_cost);
}

function handle_hallmark_return_button(frm) {
  frm.add_custom_button("Mark Hallmark Return", function () {
    frm.doc.items.forEach(element => {
      frm.add_child("hallmark_return_details", {
        item_code: element.item_code,
      })
      frm.refresh_fields()
    });
  });
}
