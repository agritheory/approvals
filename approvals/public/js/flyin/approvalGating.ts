// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

export interface ApprovalRole {
	approval_role?: string
	approved?: boolean
	approver?: string
	assigned_to_user?: string
	assigned_username?: string
	user_has_approval_role?: boolean
	uda_name?: string | null
	origin?: string | null
	requested_by_name?: string
	source_label?: string
	source_name?: string
	reason?: string | null
	satisfies_role?: string | null
	can_approve?: boolean
	can_remove?: boolean
	can_reassign?: boolean
	reassign_role?: string | null
}

export interface DocLike {
	doctype?: string
	docstatus?: number
	[key: string]: unknown
}

export function approvalRoleKey(role: string | null | undefined): string {
	return role || 'User Approval'
}

export function findPendingApproval(
	approvals: ApprovalRole[],
	role: string | null | undefined
): ApprovalRole | undefined {
	const key = approvalRoleKey(role)
	return approvals.find(approval => approval.approval_role === key)
}

export function isApprovableInWorkflow(
	doc: DocLike,
	approval: ApprovalRole,
	approvalStateName?: string | null
): boolean {
	const frappe = window.frappe as {
		workflow: { get_state_fieldname: (doctype: string) => string | null }
	}
	const workflowStateField = doc.doctype ? frappe.workflow.get_state_fieldname(doc.doctype) : null

	if (workflowStateField) {
		return doc.docstatus === 0 && doc[workflowStateField] == approvalStateName && !approval.approved
	}

	return doc.docstatus === 0 && !approval.approved
}

export function userCanApprove(approval: ApprovalRole, user: string): boolean {
	if (approval.approval_role === 'User Approval') {
		return approval.assigned_username === user
	}

	if (user !== 'Administrator' && !approval.user_has_approval_role) {
		return false
	}

	return true
}

export function canActOnApproval(
	doc: DocLike,
	approval: ApprovalRole | undefined,
	approvalStateName?: string | null,
	user?: string
): boolean {
	if (!approval) {
		return false
	}

	if (typeof approval.can_approve === 'boolean') {
		return isApprovableInWorkflow(doc, approval, approvalStateName) && approval.can_approve
	}

	const sessionUser = user || window.frappe.session.user
	return isApprovableInWorkflow(doc, approval, approvalStateName) && userCanApprove(approval, sessionUser)
}
