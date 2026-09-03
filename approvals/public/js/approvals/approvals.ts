// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

declare const $: any
declare const approvals: any
declare const frappe: any

frappe.provide('approvals')

approvals.apply_form_gating = async frm => {
	if (frm.is_new()) {
		return
	}

	const response = await frappe.xcall('approvals.approvals.api.fetch_approvals_and_roles', {
		doc: frm.doc,
	})
	if (!response.show_approvals) {
		return
	}

	frappe.workflow.setup(frm.doctype)

	const workflowStateField = frappe.workflow.get_state_fieldname(frm.doctype)
	if (workflowStateField && frm.doc[workflowStateField] == response.approval_state) {
		frm.set_read_only()
	}
}

$(document).on('form-refresh', (_e, frm) => {
	approvals.apply_form_gating(frm)
})
