frappe.ui.form.on('Document Approval Rule', {
	refresh: function (frm) {
		frm.add_custom_button(__('Test Condition'), function () {
			let d = new frappe.ui.Dialog({
				title: __('Select: {0}', [frm.doc.approval_doctype]),
				fields: [
					{
						label: __(frm.doc.approval_doctype),
						fieldname: 'docname',
						fieldtype: 'Link',
						options: frm.doc.approval_doctype,
						reqd: 1,
					},
				],
				primary_action_label: __('Test'),
				primary_action(values) {
					frappe.call({
						method: 'run_doc_method',
						args: {
							method: 'test_condition',
							dt: frm.doc.doctype,
							dn: frm.doc.name,
							args: { doctype: frm.doc.approval_doctype, docname: values.docname },
						},
						callback: function (r) {
							if (r.message) {
								frappe.msgprint(r.message)
							}
						},
					})
					d.hide()
				},
			})
			d.show()
		})
	},
})
