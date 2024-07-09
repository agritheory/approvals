<template>
	<div>
		<h4>Approvals</h4>
		<ul class="list-unstyled">
			<ApprovalListItem
				v-for="(approval, index) in approvalsData.approvals"
				:key="index"
				:approval="approval"
				:approvalStateName="approvalsData.approval_state"
				@documentapproval="refreshApprovals" />
		</ul>

		<div v-if="isDraft">
			<a class="text-muted" @click="addApprover">
				Add Approver
				<i class="octicon octicon-plus" style="margin-left: 2px"></i>
			</a>
			<br />
			<a v-if="approvalsData.length > 0" class="text-muted" @click="removeApprover" style="position: relative">
				Remove Approver
				<i class="remove-approver">×</i>
			</a>
		</div>
	</div>
</template>

<script setup>
import { computed, onMounted, unref, reactive } from 'vue';

import ApprovalListItem from './ApprovalListItem.vue';

let approvalsData = reactive({
	'approvals': [],
	'approval_state': '',
})

onMounted(async () => {
	await fetchApprovalsAndRoles()
})

const isDraft = computed(() => {
	return cur_frm.doc.docstatus === 0
})

const fetchApprovalsAndRoles = async () => {
	const response = await frappe.xcall('approvals.approvals.api.fetch_approvals_and_roles', { doc: cur_frm.doc })
	approvalsData.approvals = response.approvals
	approvalsData.approval_state = response.approval_state
	let workflowStateField = frappe.workflow.state_fields[cur_frm.doc.doctype]
	if(cur_frm.doc[workflowStateField] == approvalsData.approval_state){
		cur_frm.set_read_only()
	}
}

const refreshApprovals = async () => {
	await fetchApprovalsAndRoles()
	cur_frm.reload_doc()
}

const addApprover = async () => {
	const user = await approvals.add_approver_dialog()
	cur_dialog.hide()
	await frappe.xcall('approvals.approvals.api.add_user_approval', { doc: cur_frm.doc, user: user.user })
	await refreshApprovals()
}

const removeApprover = async () => {
	const userApprovals = approvalsData.value
		.filter(approval => {
			return approval.approval_role == 'User Approval'
		})
		.map(approval => approval.assigned_to_user)

	const user = await approvals.remove_approver_dialog(userApprovals)
	let username = ''
	if (user.user.includes('@')) {
		username = user.user
	} else {
		username = approvalsData.value
			.filter(approval => {
				return approval.assigned_to_user == user.user
			})
			.map(approval => approval.assigned_username)[0]
	}

	cur_dialog.hide()
	await frappe.xcall('approvals.approvals.api.remove_user_approval', { doc: cur_frm.doc, user: username })
	await fetchApprovalsAndRoles()
}
</script>

<style scoped>
.list-unstyled {
	width: 100%;
	display: table;
	margin-bottom: 0px;
	padding-bottom: 0px;
}

.remove-approver {
	position: absolute;
	bottom: -1px;
	font-size: 22px;
	font-style: normal;
	margin-left: 5px;
	font-weight: bold;
	line-height: 1;
	color: rgb(141, 153, 166);
	outline: 0;
}
</style>
