// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import { createApp } from 'vue'

import ApprovalList from './ApprovalList.vue'

declare const __: any
declare const $: any
declare const approvals: any
declare const cur_dialog: any
declare const frappe: any

frappe.provide('approvals')

frappe.get_form_sidebar_extension = () => {
	return `<div id="approvals-section"></div>`
}

const clear_approvals_section = () => {
	const approvals_section = document.getElementById('approvals-section')
	if (approvals_section) {
		approvals_section.innerHTML = ''
	}
	if (approvals.Approvals) {
		approvals.Approvals.unmount()
		approvals.Approvals = null
	}
}

approvals.load_approvals = async frm => {
	if (frm.is_new()) {
		return
	}

	const response = await frappe.xcall('approvals.approvals.api.fetch_approvals_and_roles', {
		doc: frm.doc,
	})
	if (!response.show_approvals) {
		clear_approvals_section()
		return
	}

	frappe.workflow.setup(frm.doctype)

	const mount = () => {
		const approvals_section = document.getElementById('approvals-section')
		if (!approvals_section) {
			return
		}
		if (approvals.Approvals) {
			approvals.Approvals.unmount()
		}
		const app = createApp(ApprovalList)
		app.mount(approvals_section)
		approvals.Approvals = app
	}

	mount()
	if (!document.getElementById('approvals-section')) {
		setTimeout(mount, 0)
	}
}

approvals.rejection_reason_dialog = (frm: any) => {
	return new Promise(resolve => {
		const dialog = new frappe.ui.Dialog({
			title: __('Please provide a reason for rejection'),
			fields: [
				{
					fieldtype: 'HTML',
					label: __('Rejection Reason'),
					fieldname: 'rejection_reason',
				},
			],
			primary_action: function () {
				const reason = dialog.comment_box.value
				if (!reason) {
					frappe.throw('A rejection reason is required')
				}
				resolve({
					doc: frm.doc,
					docname: frm.doc.name,
					rejection_reason: reason,
					user: frappe.session.user,
				})
			},
			primary_action_label: __('Add Comment'),
		})
		const wrapper = $(dialog.fields_dict.rejection_reason.$wrapper)
		dialog.comment_box = frappe.ui.form.make_control({
			parent: wrapper,
			render_input: true,
			only_input: true,
			enable_mentions: true,
			df: {
				fieldtype: 'Comment',
				fieldname: 'rejection_reason',
				reqd: 1,
			},
		})
		wrapper.find('.btn-comment').hide()
		$(wrapper.find('.text-muted')[0]).hide()
		$(wrapper.find('.text-muted')[1]).hide()
		dialog.show()
		dialog.get_close_btn()
	})
}

approvals.provide_rejection_reason = async (frm: any) => {
	const args = await approvals.rejection_reason_dialog(frm)
	cur_dialog.hide()
	return args
}

approvals.add_approver_dialog = () => {
	return new Promise(resolve => {
		const dialog = new frappe.ui.Dialog({
			title: __('Add a user to approve this document'),
			fields: [
				{
					fieldtype: 'Link',
					label: __('User'),
					fieldname: 'approval_user',
					reqd: 1,
					options: 'User',
				},
			],
			primary_action: function () {
				const values = dialog.get_values()
				resolve({ user: values.approval_user })
			},
			primary_action_label: __('Add Approver'),
		})
		dialog.show()
		dialog.get_close_btn()
	})
}

approvals.remove_approver_dialog = (user_approvals: (string | undefined)[]) => {
	return new Promise(resolve => {
		const dialog = new frappe.ui.Dialog({
			title: __('Remove a user from approving this document'),
			fields: [
				{
					fieldtype: 'Select',
					label: __('User'),
					fieldname: 'remove_user',
					reqd: 1,
					options: user_approvals,
				},
			],
			primary_action: function () {
				const values = dialog.get_values()
				resolve({ user: values.remove_user })
			},
			primary_action_label: __('Remove Approver'),
		})
		dialog.show()
		dialog.get_close_btn()
	})
}

$(document).on('form-refresh', (_e, frm) => {
	approvals.load_approvals(frm)
})
