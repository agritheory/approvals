<template>
	<div class="pending-approvals">
		<div v-if="loading" class="pending-approvals__loading">{{ __('Loading...') }}</div>

		<div v-else-if="!hasContent" class="pending-approvals__empty">
			<p>{{ caughtUp ? __('All caught up.') : __('No pending approvals.') }}</p>
		</div>

		<template v-else>
			<section v-if="currentFormRoute && documentGroup.show" class="pending-approvals__section">
				<div class="pending-approvals__section-title">{{ __(currentFormRoute[1]) }}: {{ currentFormRoute[2] }}</div>

				<div v-if="documentGroup.loading" class="pending-approvals__context-loading">
					{{ __('Loading approvals for this document...') }}
				</div>

				<div
					v-for="(approval, index) in documentGroupApprovals"
					v-else
					:key="documentApprovalKey(approval, index)"
					class="pending-approvals__document-row">
					<div class="pending-approvals__context">
						<div class="pending-approvals__context-row">
							<span class="pending-approvals__label">{{ __('Role') }}</span>
							<span>{{ translateRole(approval.approval_role) }}</span>
						</div>
						<div class="pending-approvals__context-row">
							<span class="pending-approvals__label">{{ __('Assigned to') }}</span>
							<span>{{ approval.assigned_to_user }}</span>
						</div>
						<div v-if="approval.requested_by_name" class="pending-approvals__context-row">
							<span class="pending-approvals__label">{{ __('Requested by') }}</span>
							<span>{{ approval.requested_by_name }}</span>
						</div>
						<div v-if="approval.reason" class="pending-approvals__context-row">
							<span class="pending-approvals__label">{{ __('Reason') }}</span>
							<span>{{ approval.reason }}</span>
						</div>
						<div v-if="approval.approved" class="pending-approvals__context-row">
							<span class="pending-approvals__label">{{ __('Approved by') }}</span>
							<span>{{ approval.approver }}</span>
						</div>
					</div>

					<div
						v-if="documentApprovalRowShowsActions(approval, index)"
						class="flyout-queue-item__actions pending-approvals__row-actions">
						<template v-if="canActOnDocumentApproval(approval)">
							<button
								class="flyout-action-btn flyout-action-btn--success flyout-action-btn--compact"
								@click="approveDocumentApproval(approval)">
								{{ __('Approve') }}
							</button>
							<button
								class="flyout-action-btn flyout-action-btn--danger flyout-action-btn--compact"
								@click="rejectDocumentApproval(approval)">
								{{ __('Reject') }}
							</button>
						</template>
						<button
							v-if="approval.can_reassign"
							class="flyout-action-btn flyout-action-btn--warning flyout-action-btn--compact"
							@click="reassignApprover(approval)">
							{{ __('Reassign') }}
						</button>
						<button
							v-if="approval.can_remove"
							class="flyout-action-btn flyout-action-btn--danger flyout-action-btn--compact"
							@click="removeApprover(approval)">
							{{ __('Remove') }}
						</button>
						<button
							v-if="showAddApproverOnRow(index)"
							class="flyout-action-btn flyout-action-btn--secondary flyout-action-btn--compact"
							@click="addApprover">
							{{ __('Add approver') }}
						</button>
					</div>
				</div>
			</section>

			<section v-if="assignedItems.length" class="pending-approvals__section">
				<div v-if="currentFormRoute && documentGroup.show" class="pending-approvals__section-title">
					{{ __('Assigned to you') }}
				</div>

				<div
					v-for="item in assignedItems"
					:key="item.name"
					class="flyout-queue-item"
					:class="{ 'flyout-queue-item--active': isActiveItem(item) }"
					@click="onItemClick(item)">
					<div class="flyout-queue-item__title">{{ __(item.reference_type) }}: {{ item.reference_name }}</div>
					<div class="flyout-queue-item__synopsis">
						{{ displayRole(item) }}
					</div>
					<div class="flyout-queue-item__meta">
						{{ timeAgo(item.creation) }}
					</div>

					<div v-if="!isActiveItem(item)" class="flyout-queue-item__actions" @click.stop>
						<button
							class="flyout-action-btn flyout-action-btn--primary flyout-action-btn--compact"
							@click="reviewItem(item)">
							{{ __('Review') }}
						</button>
					</div>

					<div v-else class="pending-approvals__active" @click.stop>
						<div class="pending-approvals__context">
							<div class="pending-approvals__context-row">
								<span class="pending-approvals__label">{{ __('Role') }}</span>
								<span>{{ displayRole(item) }}</span>
							</div>
							<div v-if="item.document_approval_rule" class="pending-approvals__context-row">
								<span class="pending-approvals__label">{{ __('Approval Rule') }}</span>
								<span>{{ item.document_approval_rule }}</span>
							</div>
						</div>

						<div v-if="getItemContext(item)?.loading" class="pending-approvals__context-loading">
							{{ __('Checking approval status...') }}
						</div>

						<div v-else-if="canAct(item)" class="flyout-queue-item__actions">
							<button
								class="flyout-action-btn flyout-action-btn--success flyout-action-btn--compact"
								@click="approveItem(item)">
								{{ __('Approve') }}
							</button>
							<button
								class="flyout-action-btn flyout-action-btn--danger flyout-action-btn--compact"
								@click="rejectItem(item)">
								{{ __('Reject') }}
							</button>
						</div>
					</div>
				</div>
			</section>
		</template>

		<p class="pending-approvals__shortcut-hint" aria-hidden="true">
			{{ __('Toggle drawer:') }}
			<kbd>Ctrl</kbd>
			+
			<kbd>Shift</kbd>
			+
			<kbd>X</kbd>
		</p>
	</div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useFlyin } from '@agritheory/flyin'
import { useFilePreview } from '@agritheory/flyin/file-preview'
import {
	approvalRoleKey,
	canActOnApproval,
	findPendingApproval,
	type ApprovalRole,
	type DocLike,
} from './approvalGating'

const __ = (
	window as Window & {
		__: (message: string, replace?: Array<string | number> | null, context?: string | null) => string
	}
).__

const props = defineProps<{
	approvalTodo?: string
}>()

const SLOT_ID = 'pending-approvals'

type FormRoute = [string, string, string] | null

interface ApprovalItem {
	name: string
	description: string
	status: string
	reference_type: string
	reference_name: string
	role: string | null
	document_approval_rule: string | null
	creation: string
}

interface ApprovalsData {
	approvals: ApprovalRole[]
	approval_state: string
	workflow_exists: boolean
	require_rejection_reason?: boolean
	show_approvals: boolean
	can_add?: boolean
}

interface ItemContext {
	loading: boolean
	doc: DocLike | null
	approvalsData: ApprovalsData | null
}

interface DocumentGroupState {
	loading: boolean
	show: boolean
	doc: DocLike | null
	approvalsData: ApprovalsData | null
}

const flyin = useFlyin()
const preview = useFilePreview()
const items = ref<ApprovalItem[]>([])
const selected = ref<string | null>(null)
const loading = ref(true)
const caughtUp = ref(false)
const currentRoute = ref<FormRoute>(null)
const itemContexts = ref<Map<string, ItemContext>>(new Map())
const documentGroup = ref<DocumentGroupState>({
	loading: false,
	show: false,
	doc: null,
	approvalsData: null,
})

let routeCloseRegistered = false
let suppressRouteClose = false
let advanceTimeout: ReturnType<typeof setTimeout> | null = null

const APPROVE_ADVANCE_DELAY_MS = 2000

const currentFormRoute = computed(() => currentRoute.value)

const assignedItems = computed(() => {
	const route = currentRoute.value
	if (!route) {
		return items.value
	}
	return items.value.filter(item => !matchesItem(item, route))
})

const documentGroupApprovals = computed(() => documentGroup.value.approvalsData?.approvals ?? [])

const hasContent = computed(() => {
	if (documentGroup.value.show && (documentGroup.value.loading || documentGroupApprovals.value.length)) {
		return true
	}
	return assignedItems.value.length > 0
})

function clearAdvanceTimeout() {
	if (advanceTimeout) {
		clearTimeout(advanceTimeout)
		advanceTimeout = null
	}
}

function sleep(ms: number): Promise<void> {
	return new Promise(resolve => {
		advanceTimeout = setTimeout(() => {
			advanceTimeout = null
			resolve()
		}, ms)
	})
}

function readFormRoute(): FormRoute {
	const route = window.frappe.get_route?.() || []
	if (route[0] === 'Form' && route[1] && route[2]) {
		return [route[0], route[1], route[2]]
	}
	return null
}

function formIsNew(route: FormRoute): boolean {
	const frm = window.cur_frm as
		| {
				is_new?: () => boolean | number
				doc?: { doctype?: string; name?: string }
		  }
		| undefined
	if (!route || !frm?.is_new?.()) {
		return false
	}
	return frm.doc?.doctype === route[1] && frm.doc?.name === route[2]
}

function matchesItem(item: ApprovalItem, route: FormRoute): boolean {
	if (!route) return false
	return route[1] === item.reference_type && route[2] === item.reference_name
}

function isActiveItem(item: ApprovalItem): boolean {
	return matchesItem(item, currentRoute.value)
}

function translateRole(role: string | null | undefined): string {
	const key = approvalRoleKey(role)
	if (key === 'User Approval') {
		return __('User Approval')
	}
	return __(key)
}

function displayRole(item: ApprovalItem): string {
	return translateRole(item.role)
}

function documentApprovalKey(approval: ApprovalRole, index: number): string {
	return `${approval.approval_role}-${approval.assigned_username}-${index}`
}

function getItemContext(item: ApprovalItem): ItemContext | undefined {
	return itemContexts.value.get(item.name)
}

function canAct(item: ApprovalItem): boolean {
	const context = getItemContext(item)
	if (!context?.doc || !context.approvalsData?.show_approvals) {
		return false
	}

	const approval = findPendingApproval(context.approvalsData.approvals, item.role)
	return canActOnApproval(context.doc, approval, context.approvalsData.approval_state)
}

function canActOnDocumentApproval(approval: ApprovalRole): boolean {
	const { doc, approvalsData } = documentGroup.value
	if (!doc || !approvalsData?.show_approvals) {
		return false
	}
	return canActOnApproval(doc, approval, approvalsData.approval_state)
}

function showAddApproverOnRow(index: number): boolean {
	if (!documentGroup.value.approvalsData?.can_add) {
		return false
	}
	return index === documentGroupApprovals.value.length - 1
}

function documentApprovalRowShowsActions(approval: ApprovalRole, index: number): boolean {
	return (
		Boolean(approval.can_reassign) ||
		Boolean(approval.can_remove) ||
		canActOnDocumentApproval(approval) ||
		showAddApproverOnRow(index)
	)
}

function ensureRouteHandling() {
	if (routeCloseRegistered) return
	const router = window.frappe?.router as { on?: (event: string, callback: () => void) => void } | undefined
	if (!router?.on) return

	routeCloseRegistered = true
	router.on('change', onRouteChange)
}

function onRouteChange() {
	currentRoute.value = readFormRoute()

	if (suppressRouteClose) {
		suppressRouteClose = false
	}

	void loadCurrentDocumentGroup()
	void loadActiveContexts()
}

async function fetchItems(silent = false) {
	if (!silent) {
		loading.value = true
	}
	try {
		const response = await window.frappe.xcall('approvals.approvals.api.get_pending_approvals')
		items.value = response
		if (response.length > 0) {
			caughtUp.value = false
		}
		await refreshBadge()
		void loadCurrentDocumentGroup()
		void loadActiveContexts()
	} catch (error) {
		console.error('[flyin] Failed to fetch pending approvals:', error)
		items.value = []
	} finally {
		if (!silent) {
			loading.value = false
		}
	}
}

async function refreshBadge() {
	await flyin.refreshBadge(SLOT_ID)
}

/** Sidebar “Assigned To” reads frappe.model.docinfo.assignments, not the form doc. */
async function refreshFormAssignedTo(doctype: string, name: string) {
	const frm = window.cur_frm as
		| {
				doc?: { doctype?: string; name?: string }
				assign_to?: { refresh: () => void }
				timeline?: { refresh: () => void }
		  }
		| undefined
	if (!frm?.doc || frm.doc.doctype !== doctype || frm.doc.name !== name) {
		return
	}
	await window.frappe.xcall('frappe.desk.form.load.get_docinfo', { doctype, name })
	frm.assign_to?.refresh()
	frm.timeline?.refresh()
}

async function reloadOpenFormAndFlyin(doc: { doctype?: string; name?: string }) {
	if (doc.doctype && doc.name) {
		await refreshFormAssignedTo(doc.doctype, doc.name)
	}
	await loadCurrentDocumentGroup()
	await fetchItems(true)
}

async function loadCurrentDocumentGroup() {
	const route = readFormRoute()
	if (!route || formIsNew(route)) {
		documentGroup.value = { loading: false, show: false, doc: null, approvalsData: null }
		return
	}

	const [, doctype, name] = route
	documentGroup.value = { ...documentGroup.value, loading: true, show: false }

	try {
		const doc = await window.frappe.db.get_doc(doctype, name)
		const approvalsData = await window.frappe.xcall('approvals.approvals.api.fetch_approvals_and_roles', {
			doc: JSON.stringify(doc),
		})

		documentGroup.value = {
			loading: false,
			show: Boolean(approvalsData.show_approvals),
			doc,
			approvalsData,
		}
	} catch (error) {
		console.error('[flyin] Failed to load document approvals:', error)
		documentGroup.value = { loading: false, show: false, doc: null, approvalsData: null }
	}
}

function timeAgo(dateStr: string): string {
	const date = new Date(dateStr)
	const now = new Date()
	const diffMs = now.getTime() - date.getTime()
	const diffMins = Math.floor(diffMs / 60000)

	if (diffMins < 60) return __('{0}m ago', [diffMins])
	const diffHours = Math.floor(diffMins / 60)
	if (diffHours < 24) return __('{0}h ago', [diffHours])
	const diffDays = Math.floor(diffHours / 24)
	return __('{0}d ago', [diffDays])
}

async function previewAttachments(item: ApprovalItem) {
	try {
		const attachments = await window.frappe.db.get_list('File', {
			filters: {
				attached_to_doctype: item.reference_type,
				attached_to_name: item.reference_name,
			},
			fields: ['file_url', 'file_name'],
		})

		if (attachments.length > 0) {
			preview.show({
				url: attachments[0].file_url,
				title: `${__(item.reference_type)}: ${item.reference_name}`,
			})
		} else {
			preview.close()
		}
	} catch (error) {
		console.error('[flyin] Failed to load attachments:', error)
	}
}

function onItemClick(item: ApprovalItem) {
	if (!isActiveItem(item)) {
		void reviewItem(item)
	}
}

async function reviewItem(item: ApprovalItem) {
	selected.value = item.name
	await previewAttachments(item)

	if (!item.reference_type || !item.reference_name) return

	suppressRouteClose = true
	await window.frappe.set_route('Form', item.reference_type, item.reference_name)
}

async function loadItemContext(item: ApprovalItem) {
	const key = item.name
	itemContexts.value.set(key, { loading: true, doc: null, approvalsData: null })

	try {
		const doc = await window.frappe.db.get_doc(item.reference_type, item.reference_name)
		const approvalsData = await window.frappe.xcall('approvals.approvals.api.fetch_approvals_and_roles', {
			doc: JSON.stringify(doc),
		})

		itemContexts.value.set(key, {
			loading: false,
			doc,
			approvalsData,
		})
	} catch (error) {
		console.error('[flyin] Failed to load approval context:', error)
		itemContexts.value.set(key, { loading: false, doc: null, approvalsData: null })
	}
}

async function loadActiveContexts() {
	const activeItems = assignedItems.value.filter(isActiveItem)
	await Promise.all(activeItems.map(loadItemContext))
}

async function afterAction(completedItem: ApprovalItem, options: { advanceDelayMs?: number } = {}) {
	preview.close()
	itemContexts.value.delete(completedItem.name)
	items.value = items.value.filter(row => row.name !== completedItem.name)
	await refreshBadge()
	void loadCurrentDocumentGroup()

	const next = assignedItems.value[0]
	if (!next) {
		selected.value = null
		if (!documentGroup.value.show) {
			caughtUp.value = true
			window.frappe.show_alert({ message: __('All caught up'), indicator: 'green' })
		}
		void fetchItems(true)
		return
	}

	if (options.advanceDelayMs) {
		await sleep(options.advanceDelayMs)
	}

	suppressRouteClose = true
	selected.value = next.name
	await window.frappe.set_route('Form', next.reference_type, next.reference_name)
	void fetchItems(true)
}

type UserApprovalDialogOptions = {
	reassignRole?: string | null
	fromApprover?: string | null
	excludeUser?: string | null
}

function userApprovalDialog(
	title: string,
	primaryLabel: string,
	options: UserApprovalDialogOptions = {}
): Promise<{ user: string; reason?: string }> {
	return new Promise(resolve => {
		const userField: Record<string, unknown> = {
			fieldtype: 'Link',
			label: __('User'),
			fieldname: 'approval_user',
			reqd: 1,
			options: 'User',
		}
		if (options.reassignRole || options.fromApprover) {
			userField.get_query = () => ({
				query: 'approvals.approvals.api.query_reassign_users',
				filters: {
					role: options.reassignRole || '',
					from_approver: options.fromApprover || '',
					exclude_user: options.excludeUser || '',
				},
			})
		}

		const dialog = new window.frappe.ui.Dialog({
			title,
			fields: [
				userField,
				{
					fieldtype: 'Small Text',
					label: __('Reason'),
					fieldname: 'reason',
				},
			],
			primary_action: () => {
				const values = dialog.get_values()
				dialog.hide()
				resolve({ user: values.approval_user, reason: values.reason })
			},
			primary_action_label: primaryLabel,
		})
		dialog.show()
	})
}

async function addApprover() {
	const { doc } = documentGroup.value
	if (!doc) return

	const values = await userApprovalDialog(__('Add a user to approve this document'), __('Add approver'))
	try {
		await window.frappe.xcall('approvals.approvals.api.add_user_approval', {
			doc: JSON.stringify(doc),
			user: values.user,
			reason: values.reason,
		})
		window.frappe.show_alert({ message: __('Approver added'), indicator: 'green' })
		await refreshBadge()
		await reloadOpenFormAndFlyin(doc)
	} catch (error) {
		console.error('[flyin] Failed to add approver:', error)
		window.frappe.show_alert({ message: __('Failed to add approver'), indicator: 'red' })
	}
}

async function removeApprover(approval: ApprovalRole) {
	const { doc } = documentGroup.value
	if (!doc || !approval.uda_name) return

	window.frappe.confirm(__('Remove this approver?'), async () => {
		try {
			await window.frappe.xcall('approvals.approvals.api.remove_user_approval', {
				doc: JSON.stringify(doc),
				uda_name: approval.uda_name,
			})
			window.frappe.show_alert({ message: __('Approver removed'), indicator: 'green' })
			await refreshBadge()
			await reloadOpenFormAndFlyin(doc)
		} catch (error) {
			console.error('[flyin] Failed to remove approver:', error)
			window.frappe.show_alert({ message: __('Failed to remove approver'), indicator: 'red' })
		}
	})
}

async function reassignApprover(approval: ApprovalRole) {
	const { doc } = documentGroup.value
	if (!doc) return

	const target = approval.approval_role === 'User Approval' ? approval.uda_name : approval.approval_role
	if (!target) return

	const reassignRole =
		approval.approval_role && approval.approval_role !== 'User Approval' ? approval.approval_role : null
	const fromApprover = !reassignRole && approval.assigned_username ? approval.assigned_username : null

	const values = await userApprovalDialog(__('Reassign this approver'), __('Reassign approver'), {
		reassignRole,
		fromApprover,
		excludeUser: approval.assigned_username || undefined,
	})
	try {
		await window.frappe.xcall('approvals.approvals.api.reassign_user_approval', {
			doc: JSON.stringify(doc),
			uda_name_or_role: target,
			to_user: values.user,
			reason: values.reason,
		})
		window.frappe.show_alert({ message: __('Approver reassigned'), indicator: 'green' })
		await refreshBadge()
		await reloadOpenFormAndFlyin(doc)
	} catch (error) {
		console.error('[flyin] Failed to reassign approver:', error)
		window.frappe.show_alert({ message: __('Failed to reassign approver'), indicator: 'red' })
	}
}

async function approveDocumentApproval(approval: ApprovalRole) {
	if (!canActOnDocumentApproval(approval)) return

	const { doc, approvalsData } = documentGroup.value
	if (!doc || !approvalsData) return

	const runApprove = async () => {
		try {
			await window.frappe.xcall('approvals.approvals.api.approve_document', {
				doc: JSON.stringify(doc),
				role: approval.approval_role,
				user: window.frappe.session.user,
			})

			if (window.cur_frm?.doc?.doctype === doc.doctype && window.cur_frm?.doc?.name === doc.name) {
				await window.cur_frm.reload_doc()
			}

			window.frappe.show_alert({ message: __('Document approved'), indicator: 'green' })
			await refreshBadge()
			void loadCurrentDocumentGroup()
			void fetchItems(true)
		} catch (error) {
			console.error('[flyin] Failed to approve document:', error)
			window.frappe.show_alert({ message: __('Failed to approve'), indicator: 'red' })
		}
	}

	const isSubmittable = window.frappe.get_meta(doc.doctype)?.is_submittable
	if (!approvalsData.workflow_exists && isSubmittable) {
		window.frappe.confirm(__('Permanently Submit {0}?', [doc.name]), runApprove)
		return
	}

	await runApprove()
}

async function rejectDocumentApproval(approval: ApprovalRole) {
	if (!canActOnDocumentApproval(approval)) return

	const { doc, approvalsData } = documentGroup.value
	if (!doc || !approvalsData) return

	const requiresReason = await window.frappe.xcall('approvals.approvals.api.check_rejection_reason_required', {
		doc: JSON.stringify(doc),
	})

	if (requiresReason) {
		window.frappe.prompt(
			{
				fieldtype: 'Small Text',
				label: __('Rejection Reason'),
				fieldname: 'reason',
				reqd: 1,
			},
			async (values: { reason: string }) => {
				await doRejectDocument(approval, doc, values.reason)
			},
			__('Reject Document'),
			__('Reject')
		)
		return
	}

	await doRejectDocument(approval, doc)
}

async function doRejectDocument(approval: ApprovalRole, doc: DocLike, comment = '') {
	try {
		await window.frappe.xcall('approvals.approvals.api.reject_document', {
			doc: JSON.stringify(doc),
			role: approval.approval_role,
			comment,
		})

		window.frappe.show_alert({ message: __('Document rejected'), indicator: 'orange' })
		await refreshBadge()
		void loadCurrentDocumentGroup()
		void fetchItems(true)
	} catch (error) {
		console.error('[flyin] Failed to reject document:', error)
		window.frappe.show_alert({ message: __('Failed to reject'), indicator: 'red' })
	}
}

async function approveItem(item: ApprovalItem) {
	if (!canAct(item)) return

	const context = getItemContext(item)
	if (!context?.doc || !context.approvalsData) return

	const approval = findPendingApproval(context.approvalsData.approvals, item.role)
	if (!approval) return

	const runApprove = async () => {
		try {
			await window.frappe.xcall('approvals.approvals.api.approve_document', {
				doc: JSON.stringify(context.doc),
				role: approval.approval_role,
				user: window.frappe.session.user,
			})

			if (window.cur_frm?.doc?.doctype === context.doc.doctype && window.cur_frm?.doc?.name === context.doc.name) {
				await window.cur_frm.reload_doc()
			}

			window.frappe.show_alert({ message: __('Document approved'), indicator: 'green' })
			await afterAction(item, { advanceDelayMs: APPROVE_ADVANCE_DELAY_MS })
		} catch (error) {
			console.error('[flyin] Failed to approve document:', error)
			window.frappe.show_alert({ message: __('Failed to approve'), indicator: 'red' })
		}
	}

	const isSubmittable = window.frappe.get_meta(item.reference_type)?.is_submittable
	if (!context.approvalsData.workflow_exists && isSubmittable) {
		window.frappe.confirm(__('Permanently Submit {0}?', [item.reference_name]), runApprove)
		return
	}

	await runApprove()
}

async function rejectItem(item: ApprovalItem) {
	if (!canAct(item)) return

	const context = getItemContext(item)
	if (!context?.doc || !context.approvalsData) return

	const approval = findPendingApproval(context.approvalsData.approvals, item.role)
	if (!approval) return

	const requiresReason = await window.frappe.xcall('approvals.approvals.api.check_rejection_reason_required', {
		doc: JSON.stringify(context.doc),
	})

	if (requiresReason) {
		window.frappe.prompt(
			{
				fieldtype: 'Small Text',
				label: __('Rejection Reason'),
				fieldname: 'reason',
				reqd: 1,
			},
			async (values: { reason: string }) => {
				await doReject(item, approval, context.doc!, values.reason)
			},
			__('Reject Document'),
			__('Reject')
		)
		return
	}

	await doReject(item, approval, context.doc!)
}

async function doReject(item: ApprovalItem, approval: ApprovalRole, doc: DocLike, comment = '') {
	try {
		await window.frappe.xcall('approvals.approvals.api.reject_document', {
			doc: JSON.stringify(doc),
			role: approval.approval_role,
			comment,
		})

		window.frappe.show_alert({ message: __('Document rejected'), indicator: 'orange' })
		await afterAction(item)
	} catch (error) {
		console.error('[flyin] Failed to reject document:', error)
		window.frappe.show_alert({ message: __('Failed to reject'), indicator: 'red' })
	}
}

async function handleApprovalDeepLink(todoName: string | undefined) {
	if (!todoName) return

	const item = items.value.find(row => row.name === todoName)
	if (!item) return

	selected.value = item.name
	const route = readFormRoute()
	if (!matchesItem(item, route)) {
		suppressRouteClose = true
		await window.frappe.set_route('Form', item.reference_type, item.reference_name)
		return
	}

	void loadItemContext(item)
}

watch(currentRoute, () => {
	void loadCurrentDocumentGroup()
	void loadActiveContexts()
})

watch(
	() => props.approvalTodo,
	todoName => {
		void handleApprovalDeepLink(todoName)
	}
)

watch(
	() => items.value.length,
	() => {
		void handleApprovalDeepLink(props.approvalTodo)
	}
)

onMounted(() => {
	currentRoute.value = readFormRoute()
	ensureRouteHandling()
	void fetchItems().then(() => {
		if (props.approvalTodo) {
			void handleApprovalDeepLink(props.approvalTodo)
		}
	})
})

onUnmounted(() => {
	clearAdvanceTimeout()
})
</script>

<style scoped>
.pending-approvals {
	display: flex;
	flex-direction: column;
	height: 100%;
	min-height: 100%;
}

.pending-approvals__shortcut-hint {
	margin-top: auto;
	padding: 12px 8px 4px;
	font-size: 11px;
	line-height: 1.5;
	color: var(--text-muted, #6b7280);
	text-align: center;
}

.pending-approvals__shortcut-hint kbd {
	display: inline-block;
	margin: 0 1px;
	padding: 1px 5px;
	border-radius: 4px;
	border: 1px solid var(--border-color, rgba(0, 0, 0, 0.12));
	background: var(--control-bg, rgba(0, 0, 0, 0.04));
	font-family: inherit;
	font-size: 10px;
	font-weight: 600;
}

.pending-approvals__loading,
.pending-approvals__empty {
	padding: 24px;
	text-align: center;
	color: var(--text-muted, #6b7280);
}

.pending-approvals__section {
	display: flex;
	flex-direction: column;
	gap: 8px;
}

.pending-approvals__section + .pending-approvals__section {
	margin-top: 16px;
	padding-top: 16px;
	border-top: 1px solid var(--border-color, rgba(0, 0, 0, 0.08));
}

.pending-approvals__section-title {
	padding: 0 4px 4px;
	font-size: 12px;
	font-weight: 600;
	letter-spacing: 0.02em;
	text-transform: uppercase;
	color: var(--text-muted, #6b7280);
}

.pending-approvals__document-row {
	padding: 8px 4px;
}

.pending-approvals__active {
	margin-top: 8px;
}

.pending-approvals__context {
	display: flex;
	flex-direction: column;
	gap: 6px;
	margin-bottom: 10px;
	padding: 10px 12px;
	border-radius: 6px;
	background: var(--control-bg, rgba(0, 0, 0, 0.04));
}

.pending-approvals__context-row {
	display: flex;
	flex-direction: row;
	flex-wrap: wrap;
	gap: 0.35em;
	align-items: baseline;
	font-size: 13px;
	line-height: 1.4;
}

.pending-approvals__label {
	font-size: 11px;
	font-weight: 600;
	letter-spacing: 0.02em;
	text-transform: uppercase;
	color: var(--text-muted, #6b7280);
}

.pending-approvals__context-loading {
	margin-bottom: 8px;
	font-size: 12px;
	color: var(--text-muted, #6b7280);
}

.pending-approvals__row-actions {
	display: flex;
	flex-wrap: wrap;
	gap: 8px;
	align-items: center;
}
</style>
