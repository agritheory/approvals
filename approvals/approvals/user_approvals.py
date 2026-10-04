# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.workflow import get_workflow_name
from frappe.utils.data import today

from approvals.approvals.validation import (
	close_open_approval_todos,
	close_open_role_todos,
	session_user_has_approval_role,
)

if TYPE_CHECKING:
	pass

MANUAL_ORIGIN = "manual"

ROLE_EXCLUDED_FROM_PEER_MATCH = frozenset({"All", "Guest", "Administrator"})


@contextmanager
def user_approval_mutation():
	"""Timeline comments save the reference doc and must not re-run assign_approvers mid-mutation."""
	previous = getattr(frappe.flags, "skip_assign_approvers", False)
	frappe.flags.skip_assign_approvers = True
	try:
		yield
	finally:
		frappe.flags.skip_assign_approvers = previous


def resolve_reassign_role_filter(
	satisfies_role: str | None,
	approval_role: str | None,
) -> str | None:
	if satisfies_role:
		return satisfies_role
	if approval_role and approval_role != "User Approval":
		return approval_role
	return None


def get_assignable_reassign_users(
	*,
	role: str | None = None,
	from_approver: str | None = None,
	exclude_user: str | None = None,
	search: str = "",
) -> list[str]:
	from approvals.approvals.doctype.document_approval_rule.document_approval_rule import (
		get_users,
	)

	if role:
		candidates = get_users(role)
	elif from_approver:
		approver_roles = [
			entry
			for entry in frappe.get_all("Has Role", {"parent": from_approver}, pluck="role")
			if entry not in ROLE_EXCLUDED_FROM_PEER_MATCH
		]
		if not approver_roles:
			return []
		has_role = frappe.qb.DocType("Has Role")
		user = frappe.qb.DocType("User")
		candidates = (
			frappe.qb.from_(has_role)
			.join(user)
			.on(has_role.parent == user.name)
			.select(has_role.parent)
			.distinct()
			.where(
				has_role.role.isin(approver_roles)
				& (user.enabled == 1)
				& (user.user_type == "System User")
				& (user.name != "Administrator")
			)
			.orderby(has_role.parent)
			.run(pluck=True)
		)
	else:
		return []

	if exclude_user:
		candidates = [name for name in candidates if name != exclude_user]

	if search:
		needle = search.lower()
		filtered = []
		for name in candidates:
			if needle in name.lower():
				filtered.append(name)
				continue
			full_name = frappe.db.get_value("User", name, "full_name") or ""
			if needle in full_name.lower():
				filtered.append(name)
		candidates = filtered

	return candidates


def validate_reassign_target_user(
	to_user: str,
	*,
	role: str | None = None,
	from_approver: str | None = None,
):
	allowed = get_assignable_reassign_users(role=role, from_approver=from_approver)
	if to_user in allowed:
		return
	if role:
		frappe.throw(_("Only users with the {0} role can be reassigned here.").format(role))
	frappe.throw(_("Select a user who shares a role with the current approver."))


def parse_doc(doc: Document | str) -> Document:
	if isinstance(doc, str):
		return frappe.get_doc(json.loads(doc))
	return doc


def get_user_approval_manager_role() -> str:
	return (
		frappe.db.get_single_value("Document Approval Settings", "user_approval_manager_role")
		or "System Manager"
	)


def user_has_manager_role(user: str) -> bool:
	role = get_user_approval_manager_role()
	return user == "Administrator" or frappe.db.exists("Has Role", {"parent": user, "role": role})


def approvals_active_on_doc(doc: Document) -> bool:
	if doc.docstatus != 0:
		return False
	workflow_name = get_workflow_name(doc.doctype)
	if not workflow_name:
		return True
	approval_state = frappe.db.get_value("Workflow", workflow_name, "approval_state")
	if not approval_state:
		return True
	state_field = frappe.get_cached_value("Workflow", workflow_name, "workflow_state_field")
	return doc.get(state_field) == approval_state


def get_user_document_approval_rows(doc: Document) -> list[frappe._dict]:
	return frappe.get_all(
		"User Document Approval",
		filters={"reference_doctype": doc.doctype, "reference_name": doc.name},
		fields=[
			"name",
			"approver",
			"requested_by",
			"origin",
			"satisfies_role",
			"reason",
			"todo",
		],
	)


def get_satisfies_role_delegates(doc: Document) -> dict[str, str]:
	delegates: dict[str, str] = {}
	for row in get_user_document_approval_rows(doc):
		if row.satisfies_role:
			delegates[row.satisfies_role] = row.approver
	return delegates


def get_uda_for_role_key(doc: Document, role_key: str) -> frappe._dict | None:
	if "@" in role_key:
		for row in get_user_document_approval_rows(doc):
			if not row.satisfies_role and row.approver == role_key:
				return row
		return None
	for row in get_user_document_approval_rows(doc):
		if row.satisfies_role == role_key:
			return row
	return None


def default_user_approval_permission(
	action: str,
	doc: Document,
	user: str,
	uda: frappe._dict | Document | None = None,
) -> bool:
	if action == "add":
		if user_has_manager_role(user):
			return True
		return approvals_active_on_doc(doc)

	if not uda:
		return False

	uda_row = uda if isinstance(uda, frappe._dict) else frappe._dict(uda.as_dict())

	if action == "remove":
		if uda_row.get("satisfies_role"):
			return False
		if user_has_manager_role(user):
			return True
		if uda_row.get("origin") and uda_row.origin != MANUAL_ORIGIN:
			return False
		return uda_row.requested_by == user

	if action == "reassign":
		if user_has_manager_role(user):
			return True
		return current_assignee_for_uda(doc, uda_row) == user

	return False


def can_manage_user_approval(
	action: str,
	doc: Document,
	user: str,
	uda: frappe._dict | Document | None = None,
) -> bool:
	for path in frappe.get_hooks("approvals_user_approval_permission") or []:
		result = frappe.get_attr(path)(action=action, doc=doc, user=user, uda=uda)
		if result is not None:
			return bool(result)
	return default_user_approval_permission(action, doc, user, uda)


def current_assignee_for_uda(doc: Document, uda: frappe._dict) -> str | None:
	if uda.satisfies_role:
		return uda.approver
	if uda.approver:
		return uda.approver
	return None


def current_assignee_for_role(doc: Document, role: str) -> str | None:
	delegates = get_satisfies_role_delegates(doc)
	if role in delegates:
		return delegates[role]
	todo_user = frappe.db.get_value(
		"ToDo",
		{
			"reference_type": doc.doctype,
			"reference_name": doc.name,
			"role": role,
			"status": "Open",
			"document_approval_rule": ["is", "set"],
		},
		"allocated_to",
	)
	if todo_user:
		return todo_user
	return None


def user_can_approve_row(
	doc: Document,
	role_key: str,
	user: str,
	user_roles: list[str],
	approved: bool,
) -> bool:
	if approved:
		return False
	if not approvals_active_on_doc(doc):
		return False
	if "@" in role_key:
		return user == role_key
	assignee = current_assignee_for_role(doc, role_key)
	if assignee:
		return user == assignee or user == "Administrator"
	return session_user_has_approval_role(user, role_key, user_roles)


def emit_user_approval_event(
	event: str,
	uda: Document | frappe._dict | None,
	actor: str,
	reason: str | None = None,
	previous_approver: str | None = None,
	doc: Document | None = None,
):
	if frappe.flags.skip_user_approval_events:
		return

	payload = {
		"event": event,
		"uda": uda,
		"actor": actor,
		"reason": reason,
		"previous_approver": previous_approver,
		"doc": doc,
	}

	handlers = list(frappe.get_hooks("approvals_user_approval_events") or [])
	handlers.append("approvals.approvals.user_approvals.default_user_approval_event_handler")

	for path in handlers:
		frappe.get_attr(path)(**payload)


def default_user_approval_event_handler(
	event: str,
	uda: Document | frappe._dict | None,
	actor: str,
	reason: str | None = None,
	previous_approver: str | None = None,
	doc: Document | None = None,
	**kwargs,
):
	if not uda:
		return

	if isinstance(uda, Document):
		uda_dict = uda.as_dict()
	elif isinstance(uda, frappe._dict):
		uda_dict = uda
	else:
		uda_dict = frappe._dict(uda)
	reference_doctype = uda_dict.reference_doctype
	reference_name = uda_dict.reference_name
	approver = uda_dict.approver
	requested_by = uda_dict.requested_by

	if not doc:
		doc = frappe.get_doc(reference_doctype, reference_name)

	recipients: set[str] = set()
	if approver and approver != actor:
		recipients.add(approver)
	if previous_approver and previous_approver != actor:
		recipients.add(previous_approver)
	if requested_by and requested_by != actor:
		recipients.add(requested_by)

	todo_name = uda_dict.get("todo")
	from approvals.approvals.api import create_approval_notification, get_approval_notification_link

	doc_ref = frappe._dict(doctype=reference_doctype, name=reference_name)
	link = get_approval_notification_link(doc_ref)
	for user in recipients:
		if event == "added":
			create_approval_notification(
				doc_ref,
				user,
				todo_name=todo_name if user == approver else None,
			)
			continue

		subject = {
			"removed": _("An approver was removed from a document you follow"),
			"reassigned": _("An approver was reassigned on a document you follow"),
		}.get(event, _("User approval updated"))
		log = frappe.new_doc("Notification Log")
		log.flags.ignore_permissions = True
		log.update(
			{
				"document_name": reference_name,
				"document_type": reference_doctype,
				"email_content": subject,
				"for_user": user,
				"from_user": actor,
				"owner": "Administrator",
				"subject": subject,
				"type": "Alert",
				"link": link,
			}
		)
		log.save(ignore_permissions=True)

	comment = build_timeline_comment(event, approver, actor, reason, previous_approver)
	doc.add_comment(
		comment_type="Comment",
		text=comment,
		comment_by=actor,
	)


def build_timeline_comment(
	event: str,
	approver: str,
	actor: str,
	reason: str | None,
	previous_approver: str | None,
) -> str:
	reason_suffix = f" Reason: {frappe.utils.escape_html(reason)}" if reason else ""
	if event == "added":
		return f"<b>{approver}</b> added as approver by <b>{actor}</b>.{reason_suffix}"
	if event == "removed":
		return f"<b>{approver}</b> removed as approver by <b>{actor}</b>.{reason_suffix}"
	if event == "reassigned":
		previous = previous_approver or "the previous approver"
		return f"Approval for <b>{approver}</b> reassigned from <b>{previous}</b> by <b>{actor}</b>.{reason_suffix}"
	return f"User approval updated by <b>{actor}</b>.{reason_suffix}"


def ensure_share(doc: Document, user: str):
	if frappe.has_permission(doc.doctype, ptype="read", user=user, doc=doc.name):
		return
	from frappe.share import add_docshare

	add_docshare(
		doc.doctype,
		doc.name,
		user=user,
		read=1,
		write=1,
		share=1,
		flags={"ignore_share_permission": True},
	)


def add_user_document_approval(
	doc: Document,
	user: str,
	*,
	reason: str | None = None,
	satisfies_role: str | None = None,
	origin: str = MANUAL_ORIGIN,
	requested_by: str | None = None,
	ignore_permissions: bool = False,
	emit_event: bool = True,
) -> Document:
	duplicate_filters = {
		"reference_doctype": doc.doctype,
		"reference_name": doc.name,
		"approver": user,
	}
	if satisfies_role:
		duplicate_filters["satisfies_role"] = satisfies_role
	else:
		duplicate_filters["satisfies_role"] = ["is", "not set"]
	if frappe.db.exists("User Document Approval", duplicate_filters):
		frappe.throw(_("This user is already assigned as an approver for this document"))

	if not ignore_permissions and not can_manage_user_approval("add", doc, frappe.session.user):
		frappe.throw(
			_("You do not have permission to add approvers for this document"), frappe.PermissionError
		)

	with user_approval_mutation():
		ensure_share(doc, user)

		uda = frappe.new_doc("User Document Approval")
		uda.reference_doctype = doc.doctype
		uda.reference_name = doc.name
		uda.approver = user
		uda.requested_by = requested_by or frappe.session.user
		uda.origin = origin or MANUAL_ORIGIN
		uda.satisfies_role = satisfies_role
		uda.reason = reason
		uda.flags.ignore_permissions = True
		uda.save(ignore_permissions=True)

		if emit_event:
			emit_user_approval_event("added", uda, frappe.session.user, reason=reason, doc=doc)

	return uda


@frappe.whitelist()
def add_user_approval(
	doc: Document | str,
	method: str | None = None,
	user: str | None = None,
	reason: str | None = None,
	satisfies_role: str | None = None,
):
	if not user:
		return
	doc = parse_doc(doc)
	return add_user_document_approval(
		doc,
		user,
		reason=reason,
		satisfies_role=satisfies_role,
		origin=MANUAL_ORIGIN,
	)


def remove_user_document_approval(
	doc: Document,
	uda_name: str,
	*,
	reason: str | None = None,
	ignore_permissions: bool = False,
	emit_event: bool = True,
):
	uda = frappe.get_doc("User Document Approval", uda_name)
	if uda.reference_doctype != doc.doctype or uda.reference_name != doc.name:
		frappe.throw(_("User Document Approval does not belong to this document"))

	if not ignore_permissions and uda.satisfies_role:
		frappe.throw(
			_("Cannot remove an approver required by a Document Approval Rule"),
			frappe.ValidationError,
		)

	if not ignore_permissions and not can_manage_user_approval(
		"remove", doc, frappe.session.user, uda=uda
	):
		frappe.throw(_("You do not have permission to remove this approver"), frappe.PermissionError)

	approver = uda.approver
	requested_by = uda.requested_by
	origin = uda.origin

	with user_approval_mutation():
		uda.flags.ignore_permissions = True
		uda.delete(ignore_permissions=True)

		if emit_event:
			emit_user_approval_event(
				"removed",
				frappe._dict(
					{
						"reference_doctype": doc.doctype,
						"reference_name": doc.name,
						"approver": approver,
						"requested_by": requested_by,
						"origin": origin,
					}
				),
				frappe.session.user,
				reason=reason,
				doc=doc,
			)


@frappe.whitelist()
def remove_user_approval(
	doc: Document | str,
	method: str | None = None,
	user: str | None = None,
	uda_name: str | None = None,
	reason: str | None = None,
):
	doc = parse_doc(doc)
	if uda_name:
		if not frappe.db.exists("User Document Approval", uda_name):
			frappe.throw(
				_("Cannot remove a Document Approval Rule requirement"),
				frappe.ValidationError,
			)
		return remove_user_document_approval(doc, uda_name, reason=reason)
	if not user:
		frappe.throw(_("User or User Document Approval name is required"))
	uda_name = frappe.db.get_value(
		"User Document Approval",
		{
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"approver": user,
			"satisfies_role": ["is", "not set"],
		},
		"name",
	)
	if not uda_name:
		frappe.throw(_("User Document Approval not found"))
	return remove_user_document_approval(doc, uda_name, reason=reason)


@frappe.whitelist()
def reassign_user_approval(
	doc: Document | str,
	uda_name_or_role: str,
	to_user: str,
	reason: str | None = None,
):
	doc = parse_doc(doc)
	if not to_user:
		frappe.throw(_("Reassignment approver is required"))

	with user_approval_mutation():
		return reassign_user_approval_within_guard(doc, uda_name_or_role, to_user, reason=reason)


def delete_satisfies_role_user_document_approval(doc: Document, role: str) -> None:
	"""Remove legacy delegate rows; rule reassign uses Document Approval Rule ToDos only."""
	name = frappe.db.get_value(
		"User Document Approval",
		{
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"satisfies_role": role,
		},
		"name",
	)
	if not name:
		return
	uda = frappe.get_doc("User Document Approval", name)
	uda.flags.ignore_permissions = True
	if uda.todo and frappe.db.exists("ToDo", uda.todo):
		frappe.db.set_value("User Document Approval", uda.name, "todo", None)
		frappe.delete_doc("ToDo", uda.todo, ignore_permissions=True)
	uda.delete(ignore_permissions=True)


def create_rule_role_approval_todo(
	doc: Document,
	role: str,
	to_user: str,
	reason: str | None = None,
) -> Document:
	approval_rule = frappe.get_cached_doc(
		"Document Approval Rule",
		{"approval_doctype": doc.doctype, "approval_role": role},
	)
	ensure_share(doc, to_user)
	if reason:
		description = reason
	elif approval_rule.message:
		description = approval_rule.get_message(doc)
	else:
		description = _("A document requires your approval")

	todo = frappe.new_doc("ToDo")
	todo.owner = to_user
	todo.allocated_to = to_user
	todo.reference_type = doc.doctype
	todo.reference_name = doc.name
	todo.role = role
	todo.document_approval_rule = approval_rule.name
	todo.assigned_by = frappe.session.user
	todo.date = today()
	todo.status = "Open"
	todo.priority = "Medium"
	todo.description = description
	todo.save(ignore_permissions=True)
	return todo


def reassign_rule_role(
	doc: Document,
	role: str,
	to_user: str,
	reason: str | None = None,
	previous_approver: str | None = None,
) -> Document:
	validate_reassign_target_user(to_user, role=role)
	assignee = current_assignee_for_role(doc, role)
	if assignee != frappe.session.user and not user_has_manager_role(frappe.session.user):
		frappe.throw(_("You do not have permission to reassign this approver"), frappe.PermissionError)

	delete_satisfies_role_user_document_approval(doc, role)
	close_open_role_todos(doc, role)
	todo = create_rule_role_approval_todo(doc, role, to_user, reason=reason)
	previous = previous_approver or assignee
	emit_user_approval_event(
		"reassigned",
		frappe._dict(
			{
				"reference_doctype": doc.doctype,
				"reference_name": doc.name,
				"approver": to_user,
				"requested_by": frappe.session.user,
				"todo": todo.name,
			}
		),
		frappe.session.user,
		reason=reason,
		previous_approver=previous,
		doc=doc,
	)
	return todo


def reassign_user_approval_within_guard(
	doc: Document,
	uda_name_or_role: str,
	to_user: str,
	reason: str | None = None,
):
	if frappe.db.exists("User Document Approval", uda_name_or_role):
		uda = frappe.get_doc("User Document Approval", uda_name_or_role)
		if uda.reference_doctype != doc.doctype or uda.reference_name != doc.name:
			frappe.throw(_("User Document Approval does not belong to this document"))
		if uda.satisfies_role:
			frappe.throw(
				_(
					"Document Approval Rule assignees are not User Document Approvals. "
					"Reassign using the approval role name."
				),
				frappe.ValidationError,
			)
		frappe.throw(
			_("User Approval rows cannot be reassigned. Remove the approver and add someone else instead."),
			frappe.ValidationError,
		)

	return reassign_rule_role(doc, uda_name_or_role, to_user, reason=reason)


def normalize_provider_entry(entry: Any) -> dict | None:
	if isinstance(entry, str):
		return {"user": entry}
	if isinstance(entry, dict) and entry.get("user"):
		return entry
	return None


def sync_provider_approvers(doc: Document):
	if frappe.flags.in_patch or frappe.flags.in_install or frappe.flags.in_setup_wizard:
		return

	hook = frappe.get_hooks("approvals_approver_providers") or {}
	paths = list(hook.get(doc.doctype, [])) + list(hook.get("*", []))
	if not paths:
		return

	for path in paths:
		sync_single_provider(doc, path)


def sync_single_provider(doc: Document, provider_path: str):
	try:
		entries = frappe.get_attr(provider_path)(doc) or []
	except Exception:
		frappe.log_error(
			f"Approver provider failed for {doc.doctype} {doc.name}: {provider_path}",
			"User Approval Provider Error",
		)
		return

	desired: dict[str, dict] = {}
	for raw in entries:
		entry = normalize_provider_entry(raw)
		if not entry:
			continue
		user = entry["user"]
		key = f"{user}:{entry.get('satisfies_role') or ''}"
		desired[key] = entry

	existing_rows = frappe.get_all(
		"User Document Approval",
		filters={
			"reference_doctype": doc.doctype,
			"reference_name": doc.name,
			"origin": provider_path,
		},
		fields=["name", "approver", "satisfies_role"],
	)

	existing_keys: dict[str, frappe._dict] = {}
	for row in existing_rows:
		key = f"{row.approver}:{row.satisfies_role or ''}"
		existing_keys[key] = row

	for key, entry in desired.items():
		if key in existing_keys:
			continue
		frappe.flags.skip_user_approval_events = True
		try:
			uda = add_user_document_approval(
				doc,
				entry["user"],
				reason=entry.get("reason"),
				satisfies_role=entry.get("satisfies_role"),
				origin=provider_path,
				requested_by="Administrator",
				ignore_permissions=True,
				emit_event=False,
			)
		finally:
			frappe.flags.skip_user_approval_events = False
		emit_user_approval_event("added", uda, "Administrator", reason=entry.get("reason"), doc=doc)

	for key, row in existing_keys.items():
		if key in desired:
			continue
		if frappe.db.exists(
			"Document Approval",
			{
				"reference_doctype": doc.doctype,
				"reference_name": doc.name,
				"approver": row.approver,
			},
		):
			continue
		requested_by = frappe.db.get_value("User Document Approval", row.name, "requested_by")
		frappe.flags.skip_user_approval_events = True
		try:
			remove_user_document_approval(doc, row.name, ignore_permissions=True, emit_event=False)
		finally:
			frappe.flags.skip_user_approval_events = False
		emit_user_approval_event(
			"removed",
			frappe._dict(
				{
					"reference_doctype": doc.doctype,
					"reference_name": doc.name,
					"approver": row.approver,
					"requested_by": requested_by,
					"origin": provider_path,
				}
			),
			"Administrator",
			doc=doc,
		)


def reopen_user_approval_todos(doc: Document):
	for row in get_user_document_approval_rows(doc):
		uda = frappe.get_doc("User Document Approval", row.name)
		if uda.todo and frappe.db.exists("ToDo", uda.todo):
			todo = frappe.get_doc("ToDo", uda.todo)
			if todo.status != "Open":
				todo.status = "Open"
				todo.save(ignore_permissions=True)
			continue
		uda.todo = None
		uda.flags.ignore_permissions = True
		uda.save(ignore_permissions=True)


def build_fetch_row_permissions(
	doc: Document,
	role_key: str,
	user: str,
	user_roles: list[str],
	approved: bool,
) -> frappe._dict:
	uda = get_uda_for_role_key(doc, role_key)
	can_approve = user_can_approve_row(doc, role_key, user, user_roles, approved)
	if "@" not in role_key:
		can_remove = False
	else:
		can_remove = bool(
			uda and not uda.satisfies_role and can_manage_user_approval("remove", doc, user, uda=uda)
		)
	can_reassign = False
	if "@" not in role_key:
		assignee = current_assignee_for_role(doc, role_key)
		if assignee == user or user_has_manager_role(user):
			can_reassign = approvals_active_on_doc(doc) and not approved
	return frappe._dict(
		can_approve=can_approve,
		can_remove=can_remove,
		can_reassign=can_reassign,
	)


def can_add_user_approval(doc: Document, user: str) -> bool:
	return can_manage_user_approval("add", doc, user)
