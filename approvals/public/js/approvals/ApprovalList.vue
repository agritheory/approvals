<template>
	<div>
		<h4>Approvals</h4>
		<ul class="list-unstyled">
			<ApprovalListItem
				v-for="(approval, index) in approvalsData"
				:key="index"
				:approval="approval"
				@documentapproval="approveDocument" />
		</ul>

		<div v-if="isDraft">
			<a class="text-muted" @click="addApprover">
				Add Approver
				<i class="octicon octicon-plus" style="margin-left: 2px"></i>
			</a>
			<br />
			<a class="text-muted" @click="removeApprover" style="position: relative">
				Remove Approver
				<i class="remove-approver">×</i>
			</a>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onMounted, computed, ref } from 'vue'

import ApprovalListItem from './ApprovalListItem.vue'

// typescript declarations for FrappeJS
declare const approvals: any;
declare const cur_dialog: any;
declare const cur_frm: any;
declare const frappe: any;

const approvalsData = ref<any[]>([])

onMounted(async () => {
	await fetchApprovalsAndRoles()
})

const isDraft = computed(() => {
	return cur_frm.doc.docstatus === 0
})

const fetchApprovalsAndRoles = async () => {
	const response = await frappe.xcall('approvals.approvals.api.fetch_approvals_and_roles', { doc: cur_frm.doc })
	approvalsData.value = response
}

const approveDocument = async () => {
	await fetchApprovalsAndRoles()
	window.setTimeout(cur_frm.reload_doc(), 200)
}

const addApprover = async () => {
	const user = await approvals.add_approver_dialog(cur_frm)
	cur_dialog.hide()
	await frappe.xcall('approvals.approvals.api.add_user_approval', { doc: cur_frm.doc, user: user.user })
	await fetchApprovalsAndRoles()
}

const removeApprover = async () => {
	const userApprovals = approvalsData.value
		.filter(approval => {
			return approval.approval_role == 'User Approval'
		})
		.map(approval => approval.assigned_to_user)

	const user = await approvals.remove_approver_dialog(cur_frm, userApprovals)
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
