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

export type DocumentApprovalRowState = 'approved' | 'assigned' | 'waiting' | 'open'

const ROW_STATE_SORT: Record<DocumentApprovalRowState, number> = {
	assigned: 0,
	open: 1,
	waiting: 2,
	approved: 3,
}

export function isAssignedToSessionUser(approval: ApprovalRole, user?: string): boolean {
	const sessionUser = user || window.frappe.session.user
	if (approval.assigned_to_user === 'You') {
		return true
	}
	return Boolean(
		approval.assigned_username && approval.assigned_username.includes('@') && approval.assigned_username === sessionUser
	)
}

export function isWaitingOnSomeoneElse(approval: ApprovalRole): boolean {
	if (approval.approved) {
		return false
	}
	const assigned = approval.assigned_to_user
	if (!assigned || assigned === 'Unassigned') {
		return false
	}
	return assigned !== 'You'
}

export function documentApprovalRowState(
	approval: ApprovalRole,
	doc: DocLike,
	approvalStateName?: string | null
): DocumentApprovalRowState {
	if (approval.approved) {
		return 'approved'
	}
	if (isAssignedToSessionUser(approval)) {
		return 'assigned'
	}
	if (isWaitingOnSomeoneElse(approval)) {
		return 'waiting'
	}
	return 'open'
}

export function documentApprovalRowStateLabel(approval: ApprovalRole, state: DocumentApprovalRowState): string {
	if (state === 'approved') {
		return approval.approver ? `Approved · ${approval.approver}` : 'Approved'
	}
	if (state === 'assigned') {
		return 'Your approval'
	}
	if (state === 'waiting') {
		return 'Waiting'
	}
	return ''
}

export function compareDocumentApprovalRows(
	a: ApprovalRole,
	b: ApprovalRole,
	doc: DocLike,
	approvalStateName?: string | null
): number {
	return (
		ROW_STATE_SORT[documentApprovalRowState(a, doc, approvalStateName)] -
		ROW_STATE_SORT[documentApprovalRowState(b, doc, approvalStateName)]
	)
}
