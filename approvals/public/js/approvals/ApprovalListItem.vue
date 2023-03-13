<template>
<li>
	<div
		style="font-size: 110%"
		:style="!approval.approved ? 'display: table-cell;' : 'display: table-row;'"
	>{{approval.approval_role}}</div>
	<div
		v-if="!approval.approved"
	>
		<button 
			@click="handleApproval"
			:disabled="status() ? 'disabled' : null"
			:class="status() ? 'btn btn-disabled' : 'btn'"
		>APPROVE</button>
		<button 
			@click="handleRejection"
			:disabled="status() ? 'disabled' : null"
			:class="status() ? 'btn btn-disabled button-reject' : 'btn button-reject'"
		>REJECT</button>
	</div>
	<div>
	<span v-if="approval.approved">{{ approval.approver }} - Approved</span>
	<span v-else >{{approval.assigned_to_user === 'Unassigned' ? approval.assigned_to_user : `${approval.assigned_to_user} - Assigned`}}</span>
	</div>
</li>
</template>
<script>
export default {
	name: "ApprovalListItem",
	props: ["approval", "approval_state"],
	methods: {
		handleApproval(){
			frappe.xcall('approvals.approvals.api.approve_document', {
				doc: cur_frm.doc,
				role: this.$props.approval.approval_role,
				user: frappe.session.user,
				})
			.then(r => {
				this.$emit('documentapproval')
			})
		},
		handleRejection(){
			approvals.provide_rejection_reason(cur_frm)
			.then((r) => {
				frappe.xcall('approvals.approvals.api.reject_document', {
					doc: cur_frm.doc,
					role: this.$props.approval.approval_role,
					comment: r.rejection_reason
				}).then(r => {this.$emit('documentapproval')})
			})
		},
		status(){
			if(cur_frm.doc[frappe.workflow.get_state_fieldname(cur_frm.doctype)] !== this.approval_state){
				return true
			}	else if(this.approval.approval_role != 'User Approval' && !this.approval.user_has_approval_role){
				return true
			}	else if(this.approval.approval_role == 'User Approval' && this.approval.assigned_username !== frappe.session.user){
				return true
			} else {
				return false
			}
		}
	},
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
	box-shadow: rgba(0, 0, 0, 0.05) 0px 0.5px 0px 0px, rgba(0, 0, 0, 0.08) 0px 0px 0px 1px, rgba(0, 0, 0, 0.05) 0px 2px 4px 0px
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
