<template>
	<li>
		<div style="font-size: 110%" :style="!approval.approved ? 'display: table-cell;' : 'display: table-row;'">
			{{ approval.approval_role }}
		</div>

		<div v-if="isApproveable">
			<button id="approve-btn" @click="approve" :disabled="!status" :class="status ? 'btn btn-disabled' : 'btn'">
				{{ translate('APPROVE') }}
			</button>
			<button
				id="reject-btn"
				@click="reject"
				:disabled="!status"
				:class="status ? 'btn btn-disabled button-reject' : 'btn button-reject'">
				{{ translate('REJECT') }}
			</button>
		</div>

		<div>
			<span v-if="approval.approved">{{ approval.approver }} - Approved</span>
			<span v-else>{{
				approval.assigned_to_user === 'Unassigned'
					? translate(approval.assigned_to_user)
					: `${approval.assigned_to_user} - ${translate('Assigned')}`
			}}</span>
		</div>
	</li>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import type { Approval } from './ApprovalList.vue'

// typescript declarations for FrappeJS
interface FrappeWindow extends Window {
	__: any
}
declare const approvals: any
declare const cur_frm: any
declare const frappe: any
declare const window: FrappeWindow

const emit = defineEmits(['documentapproval'])

const props = defineProps<{
	approval: Approval
	approvalStateName?: string
	workflowExists?: boolean
}>()

const isApproveable = computed(() => {
	const workflowStateField = frappe.workflow.state_fields[cur_frm.doc.doctype]
	if (workflowStateField) {
		return (
			cur_frm.doc.docstatus === 0 &&
			cur_frm.doc[workflowStateField] == props.approvalStateName &&
			!props.approval.approved
		)
	}
	return cur_frm.doc.docstatus === 0 && !props.approval.approved
})

const status = computed(() => {
	if (cur_frm.doc.docstatus !== 0) {
		return false
	} else if (props.approval.approval_role != 'User Approval' && !props.approval.user_has_approval_role) {
		return false
	} else if (
		props.approval.approval_role == 'User Approval' &&
		props.approval.assigned_username !== frappe.session.user
	) {
		return false
	} else {
		return true
	}
})

const translate = (text: string) => {
	return window.__(text)
}

const approve = async () => {
	const approveDocument = async () => {
		await frappe.xcall('approvals.approvals.api.approve_document', {
			doc: cur_frm.doc,
			role: props.approval.approval_role,
			user: frappe.session.user,
		})
		emit('documentapproval')
	}

	if (!props.workflowExists && cur_frm.meta.is_submittable) {
		frappe.confirm(translate(`Permanently Submit ${cur_frm.doc.name}?`), approveDocument)
	} else {
		await approveDocument()
	}
}

const reject = async () => {
	const response = await approvals.provide_rejection_reason(cur_frm)
	await frappe.xcall('approvals.approvals.api.reject_document', {
		doc: cur_frm.doc,
		role: props.approval.approval_role,
		comment: response.rejection_reason,
		document_approval_rule_name: props.approval.document_approval_rule,
	})
	emit('documentapproval')
}
</script>

<style scoped>
li {
	display: table;
	margin-bottom: 1em;
	width: 100%;
}

button {
	display: table-cell;
	text-align: center;
	min-width: 45%;
	background-color: var(--dark-green-avatar-bg);
	color: var(--dark-green-avatar-color);
	margin-right: 1ch;
	padding: 4px 10px;
}

button:hover:enabled {
	color: var(--dark-green-avatar-color);
	font-weight: bold;
	box-shadow:
		rgba(0, 0, 0, 0.05) 0px 0.5px 0px 0px,
		rgba(0, 0, 0, 0.08) 0px 0px 0px 1px,
		rgba(0, 0, 0, 0.05) 0px 2px 4px 0px;
}

button:disabled {
	text-decoration: line-through;
	background: #687178;
	color: #fff;
}

div {
	width: 100%;
	display: table-row;
}

.button-reject {
	background: var(--bg-orange);
	color: var(--text-on-orange);
	margin-right: 0px;
}

.button-reject:hover:enabled {
	color: var(--text-on-orange);
	font-weight: bold;
}
</style>
