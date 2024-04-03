<template>
	<div>
		<h4>Approvals</h4>
		<ul class="list-unstyled">
			<ApprovalListItem
				v-for="(approval, index) in approvals"
				:key="index"
				:approval="approval"
        :approval_state="approval_state"
				@documentapproval="handleDocumentApproval" />
		</ul>
		<a v-show="docstatus()" class="text-muted" @click="handleAddApprover"
			>Add Approver <i class="octicon octicon-plus" style="margin-left: 2px"></i
		></a>
		<br />
		<a v-show="docstatus()" class="text-muted" @click="handleRemoveApprover" style="position: relative"
			>Remove Approver<i class="remove-approver">×</i></a
		>
	</div>
</template>
<script>
import ApprovalListItem from './ApprovalListItem.vue'

export default {
	name: 'ApprovalList',
	components: { ApprovalListItem },
	data() {
    return {
			approvals: [],
			approval_state: ''
		}
	},
	methods: {
		fetchApprovalsAndRoles() {
			frappe.xcall('approvals.approvals.api.fetch_approvals_and_roles', { doc: cur_frm.doc }).then(r => {
        this.$set(this, 'approvals', r.approvals)
				this.$set(this, 'approval_state', r.approval_state)
			})
		},
		handleDocumentApproval() {
			this.fetchApprovalsAndRoles()
			window.setTimeout(cur_frm.reload_doc(), 200)
		},
		handleAddApprover() {
			approvals.add_approver_dialog(cur_frm).then(user => {
				cur_dialog.hide()
				frappe.xcall('approvals.approvals.api.add_user_approval', { doc: cur_frm.doc, user: user.user }).then(r => {
					this.fetchApprovalsAndRoles()
				})
			})
		},
		handleRemoveApprover() {
			let userApprovals = this.approvals
				.filter(approval => {
					return approval.approval_role == 'User Approval'
				})
				.map(approval => approval.assigned_to_user)
			approvals.remove_approver_dialog(cur_frm, userApprovals).then(user => {
				let username = ''
				if (user.user.includes('@')) {
					username = user.user
				} else {
					username = this.approvals
						.filter(approval => {
							return approval.assigned_to_user == user.user
						})
						.map(approval => approval.assigned_username)[0]
				}
				cur_dialog.hide()
				frappe.xcall('approvals.approvals.api.remove_user_approval', { doc: cur_frm.doc, user: username }).then(r => {
					this.fetchApprovalsAndRoles()
				})
			})
		},
		docstatus() {
			return cur_frm.doc.docstatus === 0
		},
	},
	mounted() {
		this.fetchApprovalsAndRoles()
	},
}
</script>
<style scoped>
ul {
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
