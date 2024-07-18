import json
from typing import TYPE_CHECKING

import frappe
from frappe import _
from frappe.desk.form.utils import add_comment
from frappe.model.document import Document
from frappe.model.workflow import get_workflow_name

from approvals.approvals.utils import add_approval_comment

if TYPE_CHECKING:
	from approvals.approvals.doctype.document_approval_rule.document_approval_rule import (
		DocumentApprovalRule,
	)


@frappe.whitelist()
def get_approval_roles(doc: Document, method: str | None = None):
	settings = frappe.get_doc("Document Approval Settings")

	roles = [
		i["approval_role"]
		for i in frappe.get_all(
			"Document Approval Rule", {"approval_doctype": doc.doctype}, "approval_role"
		)
		if frappe.get_cached_doc(
			"Document Approval Rule", {"approval_doctype": doc.doctype, "approval_role": i["approval_role"]}
		).apply(doc)
	]
	user_approvals = [
		a["approver"]
		for a in frappe.get_all(
			"User Document Approval",
			{"reference_doctype": doc.doctype, "reference_name": doc.name},
			"approver",
		)
	]
	roles.extend(user_approvals)

	if not roles:
		fallback_approver = settings.fallback_approver_role
		if not fallback_approver:
			frappe.throw(
				_("No approvers found. Please set a fallback approver role in Document Approval Settings.")
			)
		roles.append(fallback_approver)
	return roles


@frappe.whitelist()
def get_document_approvals(doc: Document, method: str | None = None):
	approvers = frappe.get_all(
		"Document Approval",
		{"reference_doctype": doc.doctype, "reference_name": doc.name},
		["approver", "approval_role", "user_approval"],
	)
	for approver in approvers:
		if approver["user_approval"]:
			approver["approval_role"] = approver["approver"]
	return frappe._dict({a["approval_role"]: a["approver"] for a in approvers})


@frappe.whitelist()
def fetch_approvals_and_roles(doc: Document | str, method: str | None = None):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	if doc.get("__islocal"):
		return
	roles = get_approval_roles(doc)
	approvals = get_document_approvals(doc)
	user_roles = [
		i["role"] for i in frappe.get_all("Has Role", {"parent": frappe.session.user}, "role")
	]
	assignments = {
		a["role"] if a["role"] else a["owner"]: a["owner"]
		for a in frappe.get_all("ToDo", {"reference_name": doc.name}, ["owner", "role"])
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
	approval_state = (
		frappe.get_value("Workflow", get_workflow_name(doc.doctype), "custom_approval_state")
		or "Pending"
	)
	return {"approvals": add_roles, "approval_state": approval_state}


@frappe.whitelist()
def approve_document(
	doc: Document | str, method: str | None = None, role: str | None = None, user: str | None = None
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
	add_approval_comment(
		doc.doctype,
		doc.name,
		f"Document approved by <b>{frappe.session.user}</b>",
		subject="Document approved",
		comment_type="Info",
	)

	todo = frappe.get_value("ToDo", {"reference_name": doc.name, "role": role}, "name")
	if todo:
		todo = frappe.get_doc("ToDo", todo)
		todo.status = "Closed"
		todo.save(ignore_permissions=True)

	checked_all = check_all_document_approvals(doc, method, include_role=role)
	if checked_all:
		doc = frappe.get_doc(doc.doctype, doc.name)
		if doc.meta.is_submittable:
			doc.submit()
			doc.set_status(update=True, status="Approved")
		else:
			doc.save(ignore_permissions=True)
			doc.set_status(update=True, status="Approved")

	return approval


@frappe.whitelist()
def check_all_document_approvals(doc: Document, method: str | None = None, include_role=None):
	if method != "before_submit" and not include_role:
		return False
	roles = get_approval_roles(doc)
	approvals = list(get_document_approvals(doc).keys())
	if include_role:
		approvals.append(include_role)
	for role in roles:
		if role not in approvals:
			return False
	return True


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
	# TODO: should we check if this method exists before calling?
	doc.set_status(update=True, status="Rejected")
	rejection = add_comment(doc.doctype, doc.name, comment, frappe.session.user, frappe.session.user)
	revoke_approvals_on_reject(doc, method)
	return rejection


@frappe.whitelist()
def revoke_approvals_on_reject(doc: Document, method: str | None = None):
	for approval in frappe.get_all(
		"Document Approval", filters={"reference_doctype": doc.doctype, "reference_name": doc.name}
	):
		frappe.get_doc("Document Approval", approval).delete()
	for approval in frappe.get_all(
		"User Document Approval", filters={"reference_doctype": doc.doctype, "reference_name": doc.name}
	):
		frappe.get_doc("User Document Approval", approval).delete()


@frappe.whitelist()
def assign_approvers(doc: Document, method: str | None = None):
	roles = [
		{"approval_role": i["approval_role"]}
		for i in frappe.get_all(
			"Document Approval Rule", {"approval_doctype": doc.doctype}, "approval_role"
		)
	]
	for role in roles:
		approval_rule: "DocumentApprovalRule" = frappe.get_cached_doc(
			"Document Approval Rule",
			{"approval_doctype": doc.doctype, "approval_role": role["approval_role"]},
		)
		if approval_rule.apply(doc):
			approval_rule.assign_user(doc)


@frappe.whitelist()
def add_user_approval(doc: Document | str, method: str | None = None, user=None):
	if not user:
		return
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	uda = frappe.new_doc("User Document Approval")
	uda.reference_doctype = doc.doctype
	uda.reference_name = doc.name
	uda.approver = user
	uda.save(ignore_permissions=True)

	add_approval_comment(
		doc.doctype,
		doc.name,
		f"<b>{user}<b> added as approver by <b>{frappe.session.user}</b>",
		subject="Approver added",
		comment_type="Info",
	)


@frappe.whitelist()
def remove_user_approval(doc: Document | str, method: str | None = None, user=None):
	doc = frappe.get_doc(json.loads(doc)) if isinstance(doc, str) else doc
	user_approval = frappe.get_doc(
		"User Document Approval",
		{"reference_doctype": doc.doctype, "reference_name": doc.name, "approver": user},
	)
	user_approval.delete()

	add_approval_comment(
		doc.doctype,
		doc.name,
		f"<b>{user}<b> removed as approver by <b>{frappe.session.user}</b>",
		subject="Approver removed",
		comment_type="Info",
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
