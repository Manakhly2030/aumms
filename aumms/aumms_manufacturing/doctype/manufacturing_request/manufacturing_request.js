frappe.ui.form.on("Manufacturing Request", {
  refresh: function(frm) {
    if(!frm.is_new){
      hide_add_row_button(frm);
    }
    frm.set_query('uom', () => {
      return {
        filters: {
          "is_purity_uom": 1
        }
      }
    });
    frm.set_query('smith', 'manufacturing_stages', () => {
      return {
        filters: {
          "designation": "Smith"
        }
      }
    });
    marked_as_previous_stage_completed(frm);
    if (!frm.doc.product) {
      frm.toggle_display("product", false);
    }
    if (!frm.doc.weight && frm.doc.weight <= 0) {
      frm.toggle_display("weight", false);
    }
  }
});

frappe.ui.form.on("Manufacturing Request Stage", {
  create_raw_material_bundle: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    frappe.new_doc('Raw Material Bundle', {
      'manufacturing_request': frm.doc.name,
      'stage': row.manufacturing_stage,
      'manufacturing_stage': row.name,
      'expected_execution_time': row.required_time
    });
  },

  create_job_card: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    frm.call('create_jewellery_job_card', { 'stage_row_id': cdn }).then(r => {
      if (r.message && r.message.job_card_created) {
        frappe.model.set_value(cdt, cdn, 'job_card_created', 1);
        frappe.model.set_value(cdt, cdn, 'job_card', r.message.job_card);
        frm.refresh_field(cdt);
        // Hide the create job card button for this row
        frm.fields_dict[`${cdn}-create_job_card`].df.hidden = 1;
      }
    });
  },

  view_job_card: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.job_card_created) {
      frappe.set_route("Form", "Jewellery Job Card", row.job_card);
    }
  },

  previous_stage_completed: function(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    if (row.previous_stage_completed) {
      frm.call('update_previous_stage', { 'idx': row.idx }).then(r => {
        if (r.message) {
          row.previous_stage = r.message;
          frm.refresh_field('manufacturing_stages');
        }
      });

      frm.call('update_previous_stage_weight', { 'idx': row.idx }).then(r => {
        if (r.message) {
          row.previous_stage_weight = r.message;
          frm.refresh_field('manufacturing_stages');
        }
      });
    }
  },

  raw_material_available: function(frm, cdt, cdn) {
    let d = frm.doc.manufacturing_stages;
    let current_index = -1;
    for (let i = 0; i < d.length; i++) {
      if (d[i].name === cdn) {
        current_index = i;
        break;
      }
    }
    if (frm.doc.manufacturing_stages[current_index].raw_material_available) {
      if (current_index < d.length - 1) {
        let next_row = d[current_index + 1];
        next_row.allow_to_start_only_if_raw_material_available = 1;
        frm.refresh_field('manufacturing_stages');
      }
    }
  }
});
