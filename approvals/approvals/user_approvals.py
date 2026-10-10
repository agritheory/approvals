# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""User Document Approvals: per-document approvers added by hand, by User rules, or by providers.

This module sits below `api` and the Document Approval Rule controller and must not import
either at module level.
"""

from __future__ import annotations

import json
from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.workflow import get_workflow_name

MANUAL_ORIGIN = "manual"


def in_install_or_patch() -> bool:
	return bool(frappe.flags.in_patch or frappe.flags.in_install or frappe.flags.in_setup_wizard)


def get_approval_workflow(doctype: str) -> Document | None:
	"""The active Workflow for doctype, if it defines an approval state."""
	workflow_name = get_workflow_name(doctype)
	if not workflow_name:
		return None
	workflow = frappe.get_cached_doc("Workflow", workflow_name)
	return workflow if workflow.get("approval_state") else None


def approvals_active_on_doc(doc: Document) -> bool:
	if doc.docstatus != 0:
		return False
	workflow = get_approval_workflow(doc.doctype)
	return not workflow or doc.get(workflow.workflow_state_field) == workflow.approval_state


def parse_doc(doc: Document | str) -> Document:
	return frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc


def uda_filters(doc: Document, **extra) -> dict:
	return {"reference_doctype": doc.doctype, "reference_name": doc.name, **extra}


def todo_filters(doc: Document, **extra) -> dict:
	return {"reference_type": doc.doctype, "reference_name": doc.name, **extra}


@contextmanager
def user_approval_mutation():
	"""Timeline comments save the reference doc and must not re-run assign_approvers mid-mutation."""
	previous = getattr(frappe.flags, "skip_assign_approvers", False)
	frappe.flags.skip_assign_approvers = True
	try:
		yield
	finally:
		frappe.flags.skip_assign_approvers = previous


def is_rule_synced_user_approval(origin: str | None) -> bool:
	return bool(origin and origin != MANUAL_ORIGIN)


def get_reassign_role_for_user_approval(origin: str | None) -> str | None:
	"""The role a User rule's approvers can be reassigned within; None if the row cannot be reassigned."""
	if not is_rule_synced_user_approval(origin):
		return None
	rule = frappe.db.get_value(
		"Document Approval Rule", origin, ["approver_type", "approval_role"], as_dict=True
	)
	if not rule or rule.approver_type != "User":
		return None
	return rule.approval_role or None


def user_approval_source_display(origin: str | None, requested_by: str | None) -> tuple[str, str]:
	"""Drawer label and text for a User Approval row."""
	if origin and is_rule_synced_user_approval(origin):
		title = frappe.db.get_value("Document Approval Rule", origin, "title")
		if title is not None:
			return (_("Rule"), title or origin)
		return (_("Source"), origin.rsplit(".", 1)[-1] or origin)
	if requested_by:
		return (_("Requested by"), frappe.get_value("User", requested_by, "full_name") or requested_by)
	return ("", "")


def user_has_manager_role(user: str) -> bool:
	role = (
		frappe.db.get_single_value("Document Approval Settings", "user_approval_manager_role")
		or "System Manager"
	)
	return user == "Administrator" or bool(
		frappe.db.exists("Has Role", {"parent": user, "role": role})
	)


def session_user_has_approval_role(user: str, role: str, user_roles: list[str]) -> bool:
	"""Whether the session user may act on a role-based approval row in the UI."""
	return "@" in role or user == "Administrator" or role in user_roles


def get_assignable_reassign_users(
	*,
	role: str | None = None,
	exclude_user: str | None = None,
	search: str = "",
) -> list[str]:
	from approvals.approvals.doctype.document_approval_rule.document_approval_rule import get_users

	if not role:
		return []
	candidates = [name for name in get_users(role) if name != exclude_user]
	if not search:
		return candidates
	needle = search.lower()
	return [
		name
		for name in candidates
		if needle in name.lower()
		or needle in (frappe.db.get_value("User", name, "full_name") or "").lower()
	]


def validate_reassign_target_user(to_user: str, *, role: str | None = None):
	if not role:
		frappe.throw(_("This approver cannot be reassigned."), frappe.PermissionError)
	if to_user not in get_assignable_reassign_users(role=role):
		frappe.throw(_("Only users with the {0} role can be reassigned here.").format(role))


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


def close_open_approval_todos(
	doc: Document, role: str | None = None, rule_todos_only: bool = True
):
	"""Close open approval ToDos on doc, optionally only for one role; delegate ToDos too unless rule_todos_only."""
	filters = todo_filters(doc, status="Open")
	if rule_todos_only:
		filters["document_approval_rule"] = ["is", "set"]
	if role:
		filters["role"] = role
	for todo_name in frappe.get_all("ToDo", filters=filters, pluck="name"):
		todo = frappe.get_doc("ToDo", todo_name)
		todo.status = "Closed"
		todo.save(ignore_permissions=True)


def get_user_document_approval_rows(doc: Document) -> list[frappe._dict]:
	return frappe.get_all(
		"User Document Approval",
		filters=uda_filters(doc),
		fields=[
			"name",
			"approver",
			"requested_by",
			"origin",
			"original_approver",
			"satisfies_role",
			"reason",
			"todo",
		],
	)


def user_already_assigned(doc: Document, user: str, satisfies_role: str | None = None) -> bool:
	return bool(
		frappe.db.exists(
			"User Document Approval",
			uda_filters(doc, approver=user, satisfies_role=satisfies_role or ["is", "not set"]),
		)
	)


def get_satisfies_role_delegates(doc: Document) -> dict[str, str]:
	return {
		row.satisfies_role: row.approver
		for row in get_user_document_approval_rows(doc)
		if row.satisfies_role
	}


def get_uda_for_role_key(doc: Document, role_key: str) -> frappe._dict | None:
	"""The row behind an approval key: a user email for User Approvals, or a role for delegates."""
	for row in get_user_document_approval_rows(doc):
		if "@" in role_key and not row.satisfies_role and row.approver == role_key:
			return row
		if "@" not in role_key and row.satisfies_role == role_key:
			return row
	return None


def current_assignee_for_role(doc: Document, role: str) -> str | None:
	delegate = get_satisfies_role_delegates(doc).get(role)
	if delegate:
		return delegate
	return frappe.db.get_value(
		"ToDo",
		todo_filters(doc, role=role, status="Open", document_approval_rule=["is", "set"]),
		"allocated_to",
	)


def default_user_approval_permission(
	action: str,
	doc: Document,
	user: str,
	uda: frappe._dict | Document | None = None,
) -> bool:
	if action == "add":
		return user_has_manager_role(user) or approvals_active_on_doc(doc)

	if not uda:
		return False
	row = uda if isinstance(uda, frappe._dict) else frappe._dict(uda.as_dict())

	if action == "remove":
		if row.get("satisfies_role") or is_rule_synced_user_approval(row.get("origin")):
			return False
		return user_has_manager_role(user) or row.requested_by == user

	if action == "reassign":
		reassign_role = get_reassign_role_for_user_approval(row.get("origin"))
		if not reassign_role:
			return False
		if user_has_manager_role(user):
			return True
		return row.approver == user and reassign_role in frappe.get_roles(user)

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


def can_add_user_approval(doc: Document, user: str) -> bool:
	return can_manage_user_approval("add", doc, user)


def user_can_approve_row(
	doc: Document,
	role_key: str,
	user: str,
	user_roles: list[str],
	approved: bool,
) -> bool:
	if approved or not approvals_active_on_doc(doc):
		return False
	if "@" in role_key:
		return user == role_key
	assignee = current_assignee_for_role(doc, role_key)
	if assignee:
		return user in (assignee, "Administrator")
	return session_user_has_approval_role(user, role_key, user_roles)


def build_fetch_row_permissions(
	doc: Document,
	role_key: str,
	user: str,
	user_roles: list[str],
	approved: bool,
) -> frappe._dict:
	can_approve = user_can_approve_row(doc, role_key, user, user_roles, approved)
	pending = not approved and approvals_active_on_doc(doc)

	if "@" not in role_key:
		assignee = current_assignee_for_role(doc, role_key)
		return frappe._dict(
			can_approve=can_approve,
			can_remove=False,
			can_reassign=pending and (assignee == user or user_has_manager_role(user)),
		)

	uda = get_uda_for_role_key(doc, role_key)
	if not uda or uda.satisfies_role:
		return frappe._dict(can_approve=can_approve, can_remove=False, can_reassign=False)
	return frappe._dict(
		can_approve=can_approve,
		can_remove=can_manage_user_approval("remove", doc, user, uda=uda),
		can_reassign=pending
		and is_rule_synced_user_approval(uda.origin)
		and can_manage_user_approval("reassign", doc, user, uda=uda),
	)


def user_approval_event_row(doc: Document, approver: str, **fields) -> frappe._dict:
	return frappe._dict(uda_filters(doc, approver=approver, **fields))


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

	handlers = list(frappe.get_hooks("approvals_user_approval_events") or [])
	handlers.append("approvals.approvals.user_approvals.default_user_approval_event_handler")
	for path in handlers:
		frappe.get_attr(path)(
			event=event,
			uda=uda,
			actor=actor,
			reason=reason,
			previous_approver=previous_approver,
			doc=doc,
		)


EVENT_SUBJECTS = {
	"removed": "An approver was removed from a document you follow",
	"reassigned": "An approver was reassigned on a document you follow",
}


def default_user_approval_event_handler(
	event: str,
	uda: Document | frappe._dict | None,
	actor: str,
	reason: str | None = None,
	previous_approver: str | None = None,
	doc: Document | None = None,
	**kwargs,
):
	from approvals.approvals.api import create_approval_notification, get_approval_notification_link

	if not uda:
		return
	row = frappe._dict(uda.as_dict() if isinstance(uda, Document) else uda)
	doc_ref = frappe._dict(doctype=row.reference_doctype, name=row.reference_name)

	recipients = {row.approver, previous_approver, row.requested_by} - {None, "", actor}
	for user in recipients:
		if event == "added":
			create_approval_notification(
				doc_ref, user, todo_name=row.get("todo") if user == row.approver else None
			)
			continue
		subject = _(EVENT_SUBJECTS.get(event, "User approval updated"))
		log = frappe.new_doc("Notification Log")
		log.flags.ignore_permissions = True
		log.update(
			{
				"document_name": row.reference_name,
				"document_type": row.reference_doctype,
				"email_content": subject,
				"for_user": user,
				"from_user": actor,
				"owner": "Administrator",
				"subject": subject,
				"type": "Alert",
				"link": get_approval_notification_link(doc_ref),
			}
		)
		log.save(ignore_permissions=True)

	# Always reload; API callers often pass a stale form snapshot (modified mismatch on add_comment).
	frappe.get_doc(row.reference_doctype, row.reference_name).add_comment(
		comment_type="Comment",
		text=build_timeline_comment(event, row.approver, actor, reason, previous_approver),
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


def add_user_document_approval(
	doc: Document,
	user: str,
	*,
	reason: str | None = None,
	satisfies_role: str | None = None,
	origin: str = MANUAL_ORIGIN,
	requested_by: str | None = None,
	original_approver: str | None = None,
	ignore_permissions: bool = False,
	emit_event: bool = True,
	actor: str | None = None,
) -> Document:
	actor = actor or frappe.session.user
	origin = origin or MANUAL_ORIGIN
	if user_already_assigned(doc, user, satisfies_role):
		frappe.throw(_("This user is already assigned as an approver for this document"))
	if not ignore_permissions and not can_manage_user_approval("add", doc, actor):
		frappe.throw(
			_("You do not have permission to add approvers for this document"), frappe.PermissionError
		)

	with user_approval_mutation():
		ensure_share(doc, user)
		uda = frappe.new_doc("User Document Approval")
		uda.update(
			uda_filters(
				doc,
				approver=user,
				requested_by=requested_by or (actor if origin == MANUAL_ORIGIN else None),
				origin=origin,
				original_approver=original_approver,
				satisfies_role=satisfies_role,
				reason=reason,
			)
		)
		uda.flags.ignore_permissions = True
		uda.save(ignore_permissions=True)
		if emit_event:
			emit_user_approval_event("added", uda, actor, reason=reason, doc=doc)
	return uda


def remove_user_document_approval(
	doc: Document,
	uda_name: str,
	*,
	reason: str | None = None,
	ignore_permissions: bool = False,
	emit_event: bool = True,
	actor: str | None = None,
):
	actor = actor or frappe.session.user
	uda = frappe.get_doc("User Document Approval", uda_name)
	if uda.reference_doctype != doc.doctype or uda.reference_name != doc.name:
		frappe.throw(_("User Document Approval does not belong to this document"))
	if not ignore_permissions:
		if uda.satisfies_role or is_rule_synced_user_approval(uda.origin):
			frappe.throw(_("Cannot remove an approver assigned by a Document Approval Rule"))
		if not can_manage_user_approval("remove", doc, actor, uda=uda):
			frappe.throw(_("You do not have permission to remove this approver"), frappe.PermissionError)

	removed = user_approval_event_row(
		doc, uda.approver, requested_by=uda.requested_by, origin=uda.origin
	)
	with user_approval_mutation():
		uda.flags.ignore_permissions = True
		uda.delete(ignore_permissions=True)
		if emit_event:
			emit_user_approval_event("removed", removed, actor, reason=reason, doc=doc)


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
	return add_user_document_approval(
		parse_doc(doc), user, reason=reason, satisfies_role=satisfies_role
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
	if not uda_name and not user:
		frappe.throw(_("User or User Document Approval name is required"))
	if uda_name:
		if not frappe.db.exists("User Document Approval", uda_name):
			frappe.throw(_("Cannot remove a Document Approval Rule requirement"))
	else:
		uda_name = frappe.db.get_value(
			"User Document Approval", uda_filters(doc, approver=user, satisfies_role=["is", "not set"])
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
	"""Reassign a User rule's row (by User Document Approval name) or a Role rule's assignee (by role)."""
	doc = parse_doc(doc)
	if not to_user:
		frappe.throw(_("Reassignment approver is required"))

	with user_approval_mutation():
		if frappe.db.exists("User Document Approval", uda_name_or_role):
			uda = frappe.get_doc("User Document Approval", uda_name_or_role)
			return reassign_user_document_approval(doc, uda, to_user, reason=reason)
		return reassign_rule_role(doc, uda_name_or_role, to_user, reason=reason)


def reassign_user_document_approval(
	doc: Document,
	uda: Document,
	to_user: str,
	reason: str | None = None,
) -> Document:
	if uda.reference_doctype != doc.doctype or uda.reference_name != doc.name:
		frappe.throw(_("User Document Approval does not belong to this document"))
	if uda.satisfies_role:
		frappe.throw(
			_(
				"Document Approval Rule assignees are not User Document Approvals. "
				"Reassign using the approval role name."
			)
		)
	if not is_rule_synced_user_approval(uda.origin):
		frappe.throw(
			_("User Approval rows cannot be reassigned. Remove the approver and add someone else instead.")
		)
	if not can_manage_user_approval("reassign", doc, frappe.session.user, uda=uda):
		frappe.throw(_("You do not have permission to reassign this approver"), frappe.PermissionError)

	previous = uda.approver
	if previous == to_user:
		return uda
	validate_reassign_target_user(to_user, role=get_reassign_role_for_user_approval(uda.origin))
	if user_already_assigned(doc, to_user):
		frappe.throw(_("This user is already assigned as an approver for this document"))
	ensure_share(doc, to_user)

	old_todo = uda.todo
	uda.original_approver = uda.original_approver or previous
	uda.approver = to_user
	uda.todo = None
	if reason:
		uda.reason = reason
	uda.flags.ignore_permissions = True
	uda.save(ignore_permissions=True)
	if old_todo and old_todo != uda.todo and frappe.db.exists("ToDo", old_todo):
		frappe.delete_doc("ToDo", old_todo, ignore_permissions=True)

	emit_user_approval_event(
		"reassigned",
		user_approval_event_row(doc, to_user, requested_by=frappe.session.user, origin=uda.origin),
		frappe.session.user,
		reason=reason,
		previous_approver=previous,
		doc=doc,
	)
	return uda


def reassign_rule_role(
	doc: Document,
	role: str,
	to_user: str,
	reason: str | None = None,
) -> Document:
	validate_reassign_target_user(to_user, role=role)
	assignee = current_assignee_for_role(doc, role)
	if assignee != frappe.session.user and not user_has_manager_role(frappe.session.user):
		frappe.throw(_("You do not have permission to reassign this approver"), frappe.PermissionError)

	delete_satisfies_role_user_document_approval(doc, role)
	close_open_approval_todos(doc, role, rule_todos_only=False)
	rule = frappe.get_cached_doc(
		"Document Approval Rule",
		{"approval_doctype": doc.doctype, "approval_role": role, "approver_type": "Role"},
	)
	todo = rule.create_approval_todo(
		doc, to_user, description=reason, assigned_by=frappe.session.user
	)
	emit_user_approval_event(
		"reassigned",
		user_approval_event_row(doc, to_user, requested_by=frappe.session.user, todo=todo.name),
		frappe.session.user,
		reason=reason,
		previous_approver=assignee,
		doc=doc,
	)
	return todo


def delete_satisfies_role_user_document_approval(doc: Document, role: str) -> None:
	"""Remove legacy delegate rows; rule reassign uses Document Approval Rule ToDos only."""
	name = frappe.db.get_value("User Document Approval", uda_filters(doc, satisfies_role=role))
	if not name:
		return
	uda = frappe.get_doc("User Document Approval", name)
	if uda.todo and frappe.db.exists("ToDo", uda.todo):
		frappe.db.set_value("User Document Approval", uda.name, "todo", None)
		frappe.delete_doc("ToDo", uda.todo, ignore_permissions=True)
	uda.flags.ignore_permissions = True
	uda.delete(ignore_permissions=True)


def normalize_provider_entry(entry: Any) -> dict | None:
	if isinstance(entry, str):
		return {"user": entry}
	if isinstance(entry, dict) and entry.get("user"):
		return entry
	return None


def collect_approver_sources(doc: Document) -> dict[str, list]:
	"""Approver entries keyed by origin: each User rule's name, then each provider's dotted path."""
	sources: dict[str, list] = {}
	for name in frappe.get_all(
		"Document Approval Rule",
		filters={"approval_doctype": doc.doctype, "approver_type": "User"},
		pluck="name",
	):
		rule = frappe.get_cached_doc("Document Approval Rule", name)
		reason = rule.get_message(doc) if rule.enabled and rule.message else None
		sources[name] = [{"user": user, "reason": reason} for user in rule.get_approvers(doc)]

	hook = frappe.get_hooks("approvals_approver_providers") or {}
	for path in list(hook.get(doc.doctype, [])) + list(hook.get("*", [])):
		try:
			sources[path] = frappe.get_attr(path)(doc) or []
		except Exception:
			frappe.log_error(
				f"Approver provider failed for {doc.doctype} {doc.name}: {path}",
				"User Approval Provider Error",
			)
	return sources


def sync_user_approvers(doc: Document):
	if in_install_or_patch():
		return
	for origin, entries in collect_approver_sources(doc).items():
		sync_approvers(doc, origin, entries)


def sync_approvers(doc: Document, origin: str, entries: list):
	"""Make origin's rows match entries. Reassigned rows match on the approver the origin named."""

	def key(user: str, satisfies_role: str | None) -> str:
		return f"{user}:{satisfies_role or ''}"

	desired = {
		key(entry["user"], entry.get("satisfies_role")): entry
		for entry in map(normalize_provider_entry, entries)  # nosemgrep: frappe-no-functional-code
		if entry
	}
	existing = {
		key(row.original_approver or row.approver, row.satisfies_role): row
		for row in frappe.get_all(
			"User Document Approval",
			filters=uda_filters(doc, origin=origin),
			fields=["name", "approver", "original_approver", "satisfies_role"],
		)
	}

	for entry_key, entry in desired.items():
		if entry_key in existing or user_already_assigned(
			doc, entry["user"], entry.get("satisfies_role")
		):
			continue
		add_user_document_approval(
			doc,
			entry["user"],
			reason=entry.get("reason"),
			satisfies_role=entry.get("satisfies_role"),
			origin=origin,
			original_approver=entry["user"],
			ignore_permissions=True,
			actor="Administrator",
		)

	for row_key, row in existing.items():
		if row_key in desired:
			continue
		if frappe.db.exists("Document Approval", uda_filters(doc, approver=row.approver)):
			continue
		remove_user_document_approval(doc, row.name, ignore_permissions=True, actor="Administrator")


def reopen_user_approval_todos(doc: Document):
	"""Reopen closed ToDos; saving a row whose ToDo is gone makes it create a new one."""
	for row in get_user_document_approval_rows(doc):
		if row.todo and frappe.db.exists("ToDo", row.todo):
			todo = frappe.get_doc("ToDo", row.todo)
			if todo.status != "Open":
				todo.status = "Open"
				todo.save(ignore_permissions=True)
			continue
		uda = frappe.get_doc("User Document Approval", row.name)
		uda.todo = None
		uda.flags.ignore_permissions = True
		uda.save(ignore_permissions=True)
