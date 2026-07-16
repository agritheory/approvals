# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import json
from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.desk.form.utils import add_comment
from frappe.model.document import Document
from frappe.model.workflow import get_workflow_name
from frappe.query_builder import DocType
from frappe.utils import cint, cstr, get_datetime
from frappe.utils.data import get_url_to_form
from frappe.share import add as add_share
from approvals.approvals.validation import (
	check_all_document_approvals,
	close_open_approval_todos,
	doctype_has_approval_rules,
	get_approval_roles,
	get_document_approvals,
)
from approvals.approvals.workflow import apply_workflow
from approvals.approvals.workflow import evaluate_workflow_template


if TYPE_CHECKING:
	from approvals.approvals.doctype.document_approval_rule.document_approval_rule import (
		DocumentApprovalRule,
	)


@frappe.whitelist()
def get_pending_approval_count() -> int:
	"""Get count of pending approvals for current user."""
	return frappe.db.count(
		"ToDo",
		{
			"allocated_to": frappe.session.user,
			"status": "Open",
			"document_approval_rule": ["is", "set"],
		},
	)


@frappe.whitelist()
def get_pending_approvals() -> list[dict]:
	"""Get pending approval items assigned to current user."""
	todos = frappe.get_all(
		"ToDo",
		filters={
			"allocated_to": frappe.session.user,
			"status": "Open",
			"document_approval_rule": ["is", "set"],
		},
		fields=[
			"name",
			"description",
			"status",
			"reference_type",
			"reference_name",
			"role",
			"document_approval_rule",
			"creation",
		],
		order_by="creation desc",
		limit=50,
	)
	return todos


@frappe.whitelist()
def fetch_approvals_and_roles(doc: Document | str, method: str | None = None):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	if doc.get("__islocal"):
		return {
			"approvals": [],
			"approval_state": None,
			"require_rejection_reason": None,
			"workflow_exists": bool(get_workflow_name(doc.doctype)),
			"show_approvals": False,
		}
	if not doctype_has_approval_rules(doc.doctype):
		return {
			"approvals": [],
			"approval_state": None,
			"require_rejection_reason": None,
			"workflow_exists": bool(get_workflow_name(doc.doctype)),
			"show_approvals": False,
		}
	roles = get_approval_roles(doc)
	approvals = get_document_approvals(doc)
	user_roles = [
		i["role"] for i in frappe.get_all("Has Role", {"parent": frappe.session.user}, "role")
	]
	assignments = {
		a["role"] if a["role"] else a["allocated_to"]: a["allocated_to"]
		for a in frappe.get_all("ToDo", {"reference_name": doc.name}, ["allocated_to", "role"])
	}
	add_roles = []
	for role in roles:
		assigned_user = (
			frappe.get_value("User", assignments.get(role, role), "full_name") or "Unassigned"
		)
		assigned_user = "You" if assignments.get(role, role) == frappe.session.user else assigned_user
		approver = ""
		if approvals.get(role):
			approver = frappe.get_value("User", approvals.get(role), "full_name")
			approver = "You" if approvals.get(role) == frappe.session.user else approver
		if "@" in role and assigned_user == "Unassigned":
			assigned_user = role
		_role = frappe._dict(
			{
				"approval_role": "User Approval" if "@" in role else role,
				"user_has_approval_role": True if (role in user_roles or "@" in role) else False,
				"approved": True if approvals.get(role) else False,
				"approver": approver,
				"assigned_to_user": assigned_user,
				"assigned_username": assignments.get(role, role),
			}
		)
		add_roles.append(_role)
	approval_state = frappe.get_value("Workflow", get_workflow_name(doc.doctype), "approval_state")
	require_rejection_reason = frappe.get_value(
		"Workflow", get_workflow_name(doc.doctype), "require_rejection_reason"
	)

	return {
		"approvals": add_roles,
		"approval_state": approval_state,
		"require_rejection_reason": require_rejection_reason,
		"workflow_exists": bool(get_workflow_name(doc.doctype)),
		"show_approvals": True,
	}


@frappe.whitelist()
def check_rejection_reason_required(doc: Document | str, method: str | None = None):
	document = json.loads(doc)
	require_rejection_reason = frappe.get_value(
		"Workflow", get_workflow_name(document["doctype"]), "require_rejection_reason"
	)

	return require_rejection_reason


def get_non_submittable_approval_action(doc: Document) -> str | None:
	workflow_name = get_workflow_name(doc.doctype)
	if not workflow_name:
		return None

	workflow = frappe.get_doc("Workflow", workflow_name)
	approved_state = next(
		(
			state.state for state in workflow.states if state.is_approved_state_for_non_submittable_document
		),
		None,
	)
	if not approved_state:
		return None

	current_state = doc.get(workflow.workflow_state_field)
	for transition in workflow.transitions:
		if transition.state == current_state and transition.next_state == approved_state:
			return transition.action
	return None


def get_submittable_approval_action(doc: Document) -> str | None:
	workflow_name = get_workflow_name(doc.doctype)
	if not workflow_name:
		return None

	workflow = frappe.get_doc("Workflow", workflow_name)
	action_name = workflow.get("approval_action") or "Approve"
	current_state = doc.get(workflow.workflow_state_field)

	for transition in workflow.transitions:
		if transition.state != current_state or transition.action != action_name:
			continue
		next_state = next(
			(state for state in workflow.states if state.state == transition.next_state),
			None,
		)
		if next_state and cstr(next_state.doc_status) == "1":
			return transition.action
	return None


def finalize_document_after_approval(doc: Document):
	doc.flags.ignore_permissions = True
	if doc.meta.is_submittable:
		action = get_submittable_approval_action(doc)
	else:
		action = get_non_submittable_approval_action(doc)

	if action:
		apply_workflow(doc, action)
	elif doc.meta.is_submittable:
		doc.submit()
	else:
		doc.save(ignore_permissions=True)


@frappe.whitelist()
def approve_document(
	doc: Document | str,
	method: str | None = None,
	role: str | None = None,
	user: str | None = None,
):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	approval = frappe.new_doc("Document Approval")
	approval.reference_doctype = doc.doctype
	approval.reference_name = doc.name
	approval.approver = user
	approval.approval_role = role if role != "User Approval" else None
	approval.user_approval = "User Approval" if role == "User Approval" else None
	approval.save(ignore_permissions=True)

	# TODO: is this required?
	doc.add_comment(
		comment_type="Comment",
		text=f"Document approved by <b>{frappe.session.user}</b>",
		comment_by=user,
	)

	todo = frappe.get_value("ToDo", {"reference_name": doc.name, "role": role}, "name")
	if todo:
		todo = frappe.get_doc("ToDo", todo)
		todo.status = "Closed"
		todo.save(ignore_permissions=True)
	frappe.db.commit()

	checked_all = check_all_document_approvals(doc, method, include_role=role)
	if checked_all:
		doc = frappe.get_doc(doc.doctype, doc.name)
		finalize_document_after_approval(doc)

	return approval


@frappe.whitelist()
def set_status_to_approved(doc: Document, method: str | None = None, automatic=False):
	if doc.status != "Approved":
		return
	if not check_all_document_approvals(doc, method, automatic):
		frappe.throw("All Approvers are required to Submit this document")


@frappe.whitelist()
def reject_document(doc: Document | str, role=None, comment: str = "", method: str | None = None):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	doc.save(ignore_permissions=True)

	workflow = frappe.db.get_value("Workflow", {"document_type": doc.doctype})

	if workflow:
		try:
			apply_workflow(doc, action="Reject")
		except Exception as e:
			frappe.log_error(
				f"Workflow transition failed for {doc.doctype} {doc.name} with error: {str(e)}"
			)
			frappe.throw(f"Could not apply 'Reject' workflow action: {str(e)}")
	else:
		frappe.msgprint(f"No workflow found for {doc.doctype}. Status not changed.")

	rejection = doc.add_comment(
		comment_type="Comment",
		text=comment or f"Document rejected by <b>{frappe.session.user}</b>",
		comment_by=frappe.session.user,
	)

	revoke_approvals_on_reject(doc, method)
	return rejection


@frappe.whitelist()
def revoke_approvals_on_reject(doc: Document, method: str | None = None):
	for approval in frappe.get_all(
		"Document Approval", filters={"reference_doctype": doc.doctype, "reference_name": doc.name}
	):
		frappe.get_doc("Document Approval", approval).delete(ignore_permissions=True)
	for approval in frappe.get_all(
		"User Document Approval",
		filters={"reference_doctype": doc.doctype, "reference_name": doc.name},
	):
		frappe.get_doc("User Document Approval", approval).delete(ignore_permissions=True)


def reset_to_reapproval_state_if_needed(doc: Document, method: str | None = None):
	workflow_name = get_workflow_name(doc.doctype)
	if not workflow_name:
		return

	workflow = frappe.get_cached_doc("Workflow", workflow_name)
	condition = workflow.get("reapproval_condition")
	approval_state = workflow.get("approval_state")
	if not condition or not approval_state:
		return

	state_field = workflow.workflow_state_field
	if doc.get(state_field) == approval_state:
		return

	try:
		needs_reapproval = evaluate_workflow_template(condition, doc)
	except Exception:
		frappe.log_error(
			f"Error evaluating reapproval condition for {doc.doctype} {doc.name}",
			"Workflow Reapproval Condition Error",
		)
		return

	if not needs_reapproval:
		return

	revoke_approvals_on_reject(doc, method)
	frappe.db.set_value(
		doc.doctype,
		doc.name,
		state_field,
		approval_state,
		update_modified=False,
	)
	doc.set(state_field, approval_state)


@frappe.whitelist()
def assign_approvers(doc: Document, method: str | None = None):
	reset_to_reapproval_state_if_needed(doc, method)

	approvals = get_document_approvals(doc)

	roles = frappe.get_all(
		"Document Approval Rule", {"approval_doctype": doc.doctype}, pluck="approval_role"
	)

	for role in roles:
		if role in approvals:
			close_open_approval_todos(doc, role)
			continue

		approval_rule: "DocumentApprovalRule" = frappe.get_cached_doc(
			"Document Approval Rule",
			{"approval_doctype": doc.doctype, "approval_role": role},
		)
		if approval_rule.apply(doc):
			approval_rule.assign_user(doc)


@frappe.whitelist()
def add_user_approval(doc: Document | str, method: str | None = None, user: str | None = None):
	if not user:
		return
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	if not frappe.has_permission(doc.doctype, ptype="read", user=user, doc=doc.name):
		add_share(doc.doctype, doc.name, user, read=True, write=True, share=True)

	uda = frappe.new_doc("User Document Approval")
	uda.reference_doctype = doc.doctype
	uda.reference_name = doc.name
	uda.approver = user
	uda.save(ignore_permissions=True)

	doc.add_comment(
		comment_type="Comment",
		text=f"<b>{user}<b> added as approver by <b>{frappe.session.user}</b>",
		comment_by=user,
	)


@frappe.whitelist()
def remove_user_approval(doc: Document | str, method: str | None = None, user=None):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	user_approval = frappe.get_doc(
		"User Document Approval",
		{"reference_doctype": doc.doctype, "reference_name": doc.name, "approver": user},
	)
	user_approval.delete()

	doc.add_comment(
		comment_type="Comment",
		text=f"<b>{user}<b> removed as approver by <b>{frappe.session.user}</b>",
		comment_by=user,
	)


@frappe.whitelist()
def create_approval_notification(doc: Document | frappe._dict, user):
	log = frappe.new_doc("Notification Log")
	log.flags.ignore_permissions = True
	log.update(
		{
			"document_name": doc.name,
			"document_type": doc.doctype,
			"email_content": f"{doc.doctype} {doc.name} requires your approval",
			"for_user": user,
			"from_user": doc.owner,
			"owner": "Administrator",
			"subject": f"A {doc.doctype} requires your approval",
			"type": "Assignment",
		}
	)

	try:
		log.save(ignore_permissions=True)
	except AttributeError:
		# missing outgoing email account error
		frappe.msgprint(
			_(
				"Approval notification delivery failed. Please setup a default Email Account from Setup > Email > Email Account"
			),
		)


@frappe.whitelist()
def send_reminder_email():
	if not frappe.conf.get("approvals", {}).get("send_reminder_email"):
		return

	reminder_email_hour = frappe.get_value(
		"Document Approval Settings", "Document Approval Settings", "reminder_email_hour"
	)
	if get_datetime().hour != cint(reminder_email_hour):
		return

	ToDo = DocType("ToDo")
	UserDocumentApproval = DocType("User Document Approval")
	DocumentApproval = DocType("Document Approval")

	todos = (
		frappe.qb.from_(ToDo)
		.select(
			ToDo.allocated_to.as_("approver"),
			ToDo.reference_type.as_("doctype"),
			ToDo.reference_name.as_("name"),
		)
		.where(
			(ToDo.status == "Open")
			& (ToDo.document_approval_rule.isnotnull())
			& (ToDo.document_approval_rule != "")
		)
	).run(as_dict=True)

	assignments = (
		frappe.qb.from_(UserDocumentApproval)
		.left_join(DocumentApproval)
		.on(
			(UserDocumentApproval.approver == DocumentApproval.approver)
			& (UserDocumentApproval.reference_doctype == DocumentApproval.reference_doctype)
			& (UserDocumentApproval.reference_name == DocumentApproval.reference_name)
		)
		.where(DocumentApproval.name.isnull())
		.select(
			UserDocumentApproval.approver,
			UserDocumentApproval.reference_doctype.as_("doctype"),
			UserDocumentApproval.reference_name.as_("name"),
		)
	).run(as_dict=True)

	pending_approval = todos + assignments

	approvers = {}
	for pending in pending_approval:
		user = pending["approver"]
		if user not in approvers:
			approvers[user] = []
		approvers[user].append(
			frappe._dict(
				{
					"doctype": pending["doctype"],
					"name": pending["name"],
					"url": get_url_to_form(pending["doctype"], pending["name"]),
				}
			)
		)

	email_template = frappe.get_doc("Email Template", "Pending Approval")

	for approver_email, approver_data in approvers.items():
		approver_data = {"documents": approver_data}
		frappe.sendmail(
			recipients=approver_email,
			subject=email_template.subject,
			message=frappe.render_template(email_template.response_html, approver_data),
			add_unsubscribe_link=False,
			reference_doctype=None,
			reference_name=None,
		)
