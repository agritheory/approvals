// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

function computed_title(doc) {
	if (!doc.approval_doctype) {
		return ''
	}
	if ((doc.approver_type || 'Role') === 'User') {
		const title = `${doc.approval_doctype} - User`
		return doc.approval_role ? `${title} (${doc.approval_role})` : title
	}
	return doc.approval_role ? `${doc.approval_doctype} - ${doc.approval_role}` : ''
}

function sync_title(frm) {
	const next = computed_title(frm.doc)
	if (!frm.doc.title || frm.doc.title === frm.computed_title) {
		frm.set_value('title', next)
	}
	frm.computed_title = next
}

frappe.ui.form.on('Document Approval Rule', {
	onload: function (frm) {
		frm.computed_title = computed_title(frm.doc)
	},
	approval_doctype: sync_title,
	approver_type: sync_title,
	approval_role: sync_title,
	refresh: function (frm) {
		frm.computed_title = computed_title(frm.doc)
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
