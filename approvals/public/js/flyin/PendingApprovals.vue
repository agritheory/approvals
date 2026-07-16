<template>
	<div class="pending-approvals">
		<div v-if="loading" class="pending-approvals__loading">Loading...</div>

		<div v-else-if="items.length === 0" class="pending-approvals__empty">
			<p>{{ caughtUp ? 'All caught up.' : 'No pending approvals.' }}</p>
		</div>

		<template v-else>
			<div
				v-for="item in items"
				:key="item.name"
				class="flyout-queue-item"
				:class="{ 'flyout-queue-item--active': isActiveItem(item) }"
				@click="onItemClick(item)">
				<div class="flyout-queue-item__title">{{ item.reference_type }}: {{ item.reference_name }}</div>
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
						Review
					</button>
				</div>

				<div v-else class="pending-approvals__active" @click.stop>
					<div class="pending-approvals__context">
						<div class="pending-approvals__context-row">
							<span class="pending-approvals__label">Role</span>
							<span>{{ displayRole(item) }}</span>
						</div>
						<div v-if="item.document_approval_rule" class="pending-approvals__context-row">
							<span class="pending-approvals__label">Approval Rule</span>
							<span>{{ item.document_approval_rule }}</span>
						</div>
					</div>

					<div v-if="getItemContext(item)?.loading" class="pending-approvals__context-loading">
						Checking approval status...
					</div>

					<div v-else class="flyout-queue-item__actions">
						<button
							class="flyout-action-btn flyout-action-btn--primary flyout-action-btn--compact"
							:disabled="!canAct(item)"
							@click="approveItem(item)">
							Approve
						</button>
						<button
							class="flyout-action-btn flyout-action-btn--danger flyout-action-btn--compact"
							:disabled="!canAct(item)"
							@click="rejectItem(item)">
							Reject
						</button>
					</div>
				</div>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useFlyin } from '@agritheory/flyin'
import { useFilePreview } from '@agritheory/flyin/file-preview'
import {
	approvalRoleKey,
	canActOnApproval,
	findPendingApproval,
	type ApprovalRole,
	type DocLike,
} from './approvalGating'

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
}

interface ItemContext {
	loading: boolean
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

let routeCloseRegistered = false
let suppressRouteClose = false
let advanceTimeout: ReturnType<typeof setTimeout> | null = null

const APPROVE_ADVANCE_DELAY_MS = 2000

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

function closeFlyin() {
	if (window.flyin?.close) {
		window.flyin.close()
		return
	}
	flyin.close()
}

function readFormRoute(): FormRoute {
	const route = window.frappe.get_route?.() || []
	if (route[0] === 'Form' && route[1] && route[2]) {
		return [route[0], route[1], route[2]]
	}
	return null
}

function matchesItem(item: ApprovalItem, route: FormRoute): boolean {
	if (!route) return false
	return route[1] === item.reference_type && route[2] === item.reference_name
}

function isActiveItem(item: ApprovalItem): boolean {
	return matchesItem(item, currentRoute.value)
}

function displayRole(item: ApprovalItem): string {
	return approvalRoleKey(item.role)
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
		void loadActiveContexts()
		return
	}

	const route = currentRoute.value
	const onPending = route && items.value.some(item => matchesItem(item, route))
	if (!onPending) {
		closeFlyin()
		return
	}

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

function timeAgo(dateStr: string): string {
	const date = new Date(dateStr)
	const now = new Date()
	const diffMs = now.getTime() - date.getTime()
	const diffMins = Math.floor(diffMs / 60000)

	if (diffMins < 60) return `${diffMins}m ago`
	const diffHours = Math.floor(diffMins / 60)
	if (diffHours < 24) return `${diffHours}h ago`
	const diffDays = Math.floor(diffHours / 24)
	return `${diffDays}d ago`
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
				title: `${item.reference_type}: ${item.reference_name}`,
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
	const activeItems = items.value.filter(isActiveItem)
	await Promise.all(activeItems.map(loadItemContext))
}

async function afterAction(completedItem: ApprovalItem, options: { advanceDelayMs?: number } = {}) {
	preview.close()
	itemContexts.value.delete(completedItem.name)
	items.value = items.value.filter(row => row.name !== completedItem.name)
	await refreshBadge()

	const next = items.value[0]
	if (!next) {
		selected.value = null
		caughtUp.value = true
		window.frappe.show_alert({ message: 'All caught up', indicator: 'green' })
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

			window.frappe.show_alert({ message: 'Document approved', indicator: 'green' })
			await afterAction(item, { advanceDelayMs: APPROVE_ADVANCE_DELAY_MS })
		} catch (error) {
			console.error('[flyin] Failed to approve document:', error)
			window.frappe.show_alert({ message: 'Failed to approve', indicator: 'red' })
		}
	}

	const isSubmittable = window.frappe.get_meta(item.reference_type)?.is_submittable
	if (!context.approvalsData.workflow_exists && isSubmittable) {
		window.frappe.confirm(`Permanently Submit ${item.reference_name}?`, runApprove)
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
				label: 'Rejection Reason',
				fieldname: 'reason',
				reqd: 1,
			},
			async (values: { reason: string }) => {
				await doReject(item, approval, context.doc!, values.reason)
			},
			'Reject Document',
			'Reject'
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

		window.frappe.show_alert({ message: 'Document rejected', indicator: 'orange' })
		await afterAction(item)
	} catch (error) {
		console.error('[flyin] Failed to reject document:', error)
		window.frappe.show_alert({ message: 'Failed to reject', indicator: 'red' })
	}
}

watch(currentRoute, () => {
	void loadActiveContexts()
})

onMounted(() => {
	currentRoute.value = readFormRoute()
	ensureRouteHandling()
	void fetchItems()
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
}

.pending-approvals__loading,
.pending-approvals__empty {
	padding: 24px;
	text-align: center;
	color: var(--text-muted, #6b7280);
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
	flex-direction: column;
	gap: 2px;
	font-size: 13px;
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
</style>
