# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import json
from urllib.parse import urlencode

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.workflow import get_workflow_name
from frappe.query_builder import DocType
from frappe.utils import cint, cstr, get_datetime
from frappe.utils.data import get_url_to_form

from approvals.approvals.user_approvals import (  # noqa: F401 (add/remove/reassign are whitelisted here)
	add_user_approval,
	build_fetch_row_permissions,
	can_add_user_approval,
	close_open_approval_todos,
	get_approval_workflow,
	get_assignable_reassign_users,
	get_reassign_role_for_user_approval,
	get_satisfies_role_delegates,
	get_uda_for_role_key,
	in_install_or_patch,
	reassign_user_approval,
	remove_user_approval,
	reopen_user_approval_todos,
	session_user_has_approval_role,
	sync_user_approvers,
	todo_filters,
	uda_filters,
	user_approval_source_display,
	user_has_manager_role,
)
from approvals.approvals.workflow import apply_workflow

FLYIN_APPROVALS_SLOT = "pending-approvals"


def doctype_has_approval_rules(doctype: str, approver_type: str | None = None) -> bool:
	filters = {"approval_doctype": doctype, "enabled": 1}
	if approver_type:
		filters["approver_type"] = approver_type
	return bool(frappe.db.exists("Document Approval Rule", filters))


def get_role_rule(doctype: str, role: str):
	return frappe.get_cached_doc(
		"Document Approval Rule",
		{"approval_doctype": doctype, "approval_role": role, "approver_type": "Role"},
	)


def get_role_rule_roles(doctype: str) -> list[str]:
	return [
		role
		for role in frappe.get_all(
			"Document Approval Rule",
			filters={"approval_doctype": doctype, "approver_type": "Role"},
			pluck="approval_role",
		)
		if role
	]


@frappe.whitelist()
def get_approval_roles(doc: Document | frappe._dict, method: str | None = None):
	"""Every approval key doc needs: matching Role rule roles, then User Approval emails."""
	roles = [
		role for role in get_role_rule_roles(doc.doctype) if get_role_rule(doc.doctype, role).apply(doc)
	]
	user_approvers = frappe.get_all(
		"User Document Approval",
		filters=uda_filters(doc, satisfies_role=["is", "not set"]),
		pluck="approver",
	)
	roles.extend(user_approvers)
	if roles or not doctype_has_approval_rules(doc.doctype, approver_type="Role"):
		return roles

	fallback_role = frappe.get_cached_doc("Document Approval Settings").fallback_approver_role
	if not fallback_role:
		frappe.throw(
			_("No approvers found. Please set a fallback approver role in Document Approval Settings.")
		)
	return [fallback_role]


@frappe.whitelist()
def get_document_approvals(doc: Document | frappe._dict, method: str | None = None):
	"""Recorded approvals keyed like get_approval_roles: role, or approver email for User Approvals."""
	return frappe._dict(
		{
			row.approver if row.user_approval else row.approval_role: row.approver
			for row in frappe.get_all(
				"Document Approval",
				filters=uda_filters(doc),
				fields=["approver", "approval_role", "user_approval"],
			)
		}
	)


@frappe.whitelist()
def check_all_document_approvals(doc: Document, method: str | None = None, include_role=None):
	if method != "before_submit" and not include_role:
		return False
	approved = set(get_document_approvals(doc)) | {include_role}
	return all(role in approved for role in get_approval_roles(doc))


def validate_all_approvals_complete(doc: Document, method: str | None = None):
	if in_install_or_patch() or not doctype_has_approval_rules(doc.doctype):
		return
	if not get_approval_roles(doc):
		return
	if not check_all_document_approvals(doc, method=method or "before_submit"):
		frappe.throw(_("All approvers must approve this document before it can be finalized."))


def lock_fields_in_approval_state(doc: Document, method: str | None = None):
	"""Block edits to a draft that stays in the workflow's approval state, except allow_on_submit fields.

	Saves that move into or out of the approval state are workflow transitions and are not checked.
	"""
	if in_install_or_patch() or doc.is_new() or doc.docstatus != 0:
		return
	workflow = get_approval_workflow(doc.doctype)
	before = doc.get_doc_before_save()
	if not workflow or not before:
		return
	state_field, approval_state = workflow.workflow_state_field, workflow.approval_state
	if before.get(state_field) != approval_state or doc.get(state_field) != approval_state:
		return

	try:
		doc.validate_update_after_submit()
	except frappe.UpdateAfterSubmitError:
		frappe.clear_last_message()
		frappe.throw(
			_("{0} is pending approval and cannot be edited. Reject it to make changes.").format(
				_(doc.doctype)
			),
			frappe.UpdateAfterSubmitError,
			title=_("Pending Approval"),
		)


def get_approval_notification_link(
	doc: Document | frappe._dict,
	todo_name: str | None = None,
) -> str:
	"""Build a desk URL that opens the document and the approvals flyin."""
	doctype = getattr(doc, "doctype", None) or doc.get("reference_doctype")
	name = getattr(doc, "name", None) or doc.get("reference_name")
	if not doctype or not name:
		frappe.throw(_("Cannot build approval notification link without a document reference"))

	params = {"flyin": FLYIN_APPROVALS_SLOT}
	if todo_name:
		params["approval_todo"] = todo_name

	return f"{get_url_to_form(doctype, name)}?{urlencode(params)}"


def get_pending_approval_todos_for_user(user: str | None = None) -> list[dict]:
	"""Open approval ToDos assigned to user (rule-based and user-document approvals)."""
	user = user or frappe.session.user
	fields = [
		"name",
		"description",
		"status",
		"reference_type",
		"reference_name",
		"role",
		"document_approval_rule",
		"creation",
	]

	rule_todos = frappe.get_all(
		"ToDo",
		filters={
			"allocated_to": user,
			"status": "Open",
			"document_approval_rule": ["is", "set"],
		},
		fields=fields,
		order_by="creation desc",
	)

	user_approval_todos: list[dict] = []
	for row in frappe.get_all(
		"User Document Approval",
		filters={"approver": user},
		fields=["reference_doctype", "reference_name"],
	):
		user_approval_todos.extend(
			frappe.get_all(
				"ToDo",
				filters={
					"allocated_to": user,
					"status": "Open",
					"reference_type": row.reference_doctype,
					"reference_name": row.reference_name,
				},
				fields=fields,
			)
		)

	seen: set[str] = set()
	merged: list[dict] = []
	for todo in rule_todos + user_approval_todos:
		todo_name = todo["name"]
		if todo_name in seen:
			continue
		seen.add(todo_name)
		merged.append(todo)

	merged.sort(key=lambda row: row["creation"], reverse=True)
	return merged[:50]


@frappe.whitelist()
def get_pending_approval_count() -> int:
	"""Get count of pending approvals for current user."""
	return len(get_pending_approval_todos_for_user())


@frappe.whitelist()
def get_pending_approvals() -> list[dict]:
	"""Get pending approval items assigned to current user."""
	return get_pending_approval_todos_for_user()


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
	assignments: dict[str, str] = {}
	for row in frappe.get_all(
		"ToDo",
		{
			"reference_type": doc.doctype,
			"reference_name": doc.name,
			"status": "Open",
		},
		["allocated_to", "role"],
		order_by="modified desc",
	):
		key = row["role"] if row["role"] else row["allocated_to"]
		if key not in assignments:
			assignments[key] = row["allocated_to"]
	delegates = get_satisfies_role_delegates(doc)
	add_roles = []
	for role in roles:
		assigned_username = delegates.get(role) or assignments.get(role) or role
		assigned_user = frappe.get_value("User", assigned_username, "full_name") or "Unassigned"
		assigned_user = "You" if assigned_username == frappe.session.user else assigned_user
		approver = ""
		if approvals.get(role):
			approver = frappe.get_value("User", approvals.get(role), "full_name")
			approver = "You" if approvals.get(role) == frappe.session.user else approver
		if "@" in role and assigned_user == "Unassigned":
			assigned_user = role
		approved = bool(approvals.get(role))
		permissions = build_fetch_row_permissions(doc, role, frappe.session.user, user_roles, approved)
		uda = get_uda_for_role_key(doc, role)
		source_label, source_name = ("", "")
		if uda:
			source_label, source_name = user_approval_source_display(uda.origin, uda.requested_by)
		if "@" in role:
			reassign_role = get_reassign_role_for_user_approval(uda.origin) if uda else None
		else:
			reassign_role = role
		role_row = frappe._dict(
			{
				"approval_role": "User Approval" if "@" in role else role,
				"user_has_approval_role": session_user_has_approval_role(
					frappe.session.user, role, user_roles
				),
				"approved": approved,
				"approver": approver,
				"assigned_to_user": assigned_user,
				"assigned_username": assigned_username,
				"uda_name": uda.name if uda else None,
				"origin": uda.origin if uda else None,
				"source_label": source_label,
				"source_name": source_name,
				"requested_by_name": source_name,
				"reason": uda.reason if uda else None,
				"satisfies_role": uda.satisfies_role if uda else None,
				"can_approve": permissions.can_approve,
				"can_remove": permissions.can_remove,
				"can_reassign": permissions.can_reassign,
				"reassign_role": reassign_role,
			}
		)
		add_roles.append(role_row)
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
		"can_add": can_add_user_approval(doc, frappe.session.user),
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


def load_reference_doc(doc: Document | str) -> Document:
	"""Load the stored document; never trust field values sent by the client."""
	data = json.loads(doc) if isinstance(doc, str) else doc
	doctype = data.get("doctype")
	name = data.get("name")
	if not doctype or not name:
		frappe.throw(_("Document type and name are required"))
	return frappe.get_doc(doctype, name)


def user_is_document_approver(doc: Document, user: str) -> bool:
	if user == "Administrator" or user_has_manager_role(user):
		return True
	user_roles = set(frappe.get_roles(user))
	for role in get_approval_roles(doc):
		if "@" in role:
			if role == user:
				return True
		elif role in user_roles:
			return True
	return False


@frappe.whitelist()
def approve_document(
	doc: Document | str,
	method: str | None = None,
	role: str | None = None,
	user: str | None = None,
):
	if user and user != frappe.session.user:
		frappe.throw(_("You can only record your own approval"), frappe.PermissionError)
	user = frappe.session.user
	doc = load_reference_doc(doc)
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

	if role and role != "User Approval":
		filters = todo_filters(doc, status="Open", role=role)
	else:
		filters = todo_filters(
			doc, status="Open", allocated_to=user, document_approval_rule=["is", "not set"]
		)
	for todo_name in frappe.get_all("ToDo", filters=filters, pluck="name"):
		todo = frappe.get_doc("ToDo", todo_name)
		todo.status = "Closed"
		todo.save(ignore_permissions=True)

	doc = frappe.get_doc(doc.doctype, doc.name)
	checked_all = check_all_document_approvals(doc, method, include_role=role)
	if checked_all:
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
	doc = load_reference_doc(doc)
	if not user_is_document_approver(doc, frappe.session.user):
		frappe.throw(_("You are not an approver for this document"), frappe.PermissionError)

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
	for approval in frappe.get_all("Document Approval", filters=uda_filters(doc), pluck="name"):
		frappe.delete_doc("Document Approval", approval, ignore_permissions=True)
	reopen_user_approval_todos(doc)


def reset_to_reapproval_state_if_needed(doc: Document, method: str | None = None):
	from approvals.approvals.doctype.document_approval_rule.document_approval_rule import (
		evaluate_condition,
	)

	workflow = get_approval_workflow(doc.doctype)
	if not workflow or not workflow.get("reapproval_condition"):
		return
	state_field, approval_state = workflow.workflow_state_field, workflow.approval_state
	if doc.get(state_field) == approval_state:
		return

	try:
		needs_reapproval = evaluate_condition(workflow.reapproval_condition, doc)
	except Exception:
		frappe.log_error(
			f"Error evaluating reapproval condition for {doc.doctype} {doc.name}",
			"Workflow Reapproval Condition Error",
		)
		return
	if not needs_reapproval:
		return

	revoke_approvals_on_reject(doc, method)
	frappe.db.set_value(doc.doctype, doc.name, state_field, approval_state, update_modified=False)
	doc.set(state_field, approval_state)


def revoke_approvals_on_entering_approval_state(doc: Document, method: str | None = None):
	"""Approvals recorded before the document (re)entered the approval state covered other details."""
	workflow = get_approval_workflow(doc.doctype)
	before = doc.get_doc_before_save() if isinstance(doc, Document) else None
	if not workflow or not before:
		return
	state_field, approval_state = workflow.workflow_state_field, workflow.approval_state
	if before.get(state_field) != approval_state and doc.get(state_field) == approval_state:
		revoke_approvals_on_reject(doc, method)


@frappe.whitelist()
def assign_approvers(doc: Document, method: str | None = None):
	if frappe.flags.get("skip_assign_approvers"):
		return

	revoke_approvals_on_entering_approval_state(doc, method)
	reset_to_reapproval_state_if_needed(doc, method)

	approvals = get_document_approvals(doc)
	for role in get_role_rule_roles(doc.doctype):
		if role in approvals:
			close_open_approval_todos(doc, role)
			continue
		rule = get_role_rule(doc.doctype, role)
		if rule.apply(doc) and rule.assign_users:
			rule.assign_user(doc)

	sync_user_approvers(doc)


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def query_reassign_users(doctype, txt, searchfield, start, page_len, filters):
	filters = filters or {}
	users = get_assignable_reassign_users(
		role=filters.get("role") or None,
		exclude_user=filters.get("exclude_user") or None,
		search=txt or "",
	)
	start_index = cint(start)
	page_length = cint(page_len)
	page = users[start_index : start_index + page_length]
	return [[name, name] for name in page]


@frappe.whitelist()
def create_approval_notification(
	doc: Document | frappe._dict,
	user,
	todo_name: str | None = None,
):
	log = frappe.new_doc("Notification Log")
	log.flags.ignore_permissions = True
	log.update(
		{
			"document_name": getattr(doc, "name", None) or doc.get("reference_name"),
			"document_type": getattr(doc, "doctype", None) or doc.get("reference_doctype"),
			"email_content": f"{getattr(doc, 'doctype', None) or doc.get('reference_doctype')} {getattr(doc, 'name', None) or doc.get('reference_name')} requires your approval",
			"for_user": user,
			"from_user": getattr(doc, "owner", None) or frappe.session.user,
			"owner": "Administrator",
			"subject": f"A {getattr(doc, 'doctype', None) or doc.get('reference_doctype')} requires your approval",
			"type": "Assignment",
			"link": get_approval_notification_link(doc, todo_name=todo_name),
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
			ToDo.name.as_("todo_name"),
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
		todo_name = pending.get("todo_name") or frappe.db.get_value(
			"ToDo",
			{
				"allocated_to": pending["approver"],
				"reference_type": pending["doctype"],
				"reference_name": pending["name"],
				"status": "Open",
			},
			"name",
		)
		approvers[user].append(
			frappe._dict(
				{
					"doctype": pending["doctype"],
					"name": pending["name"],
					"url": get_approval_notification_link(
						frappe._dict(doctype=pending["doctype"], name=pending["name"]),
						todo_name=todo_name,
					),
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
