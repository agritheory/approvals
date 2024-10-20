# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint, get_datetime
from frappe.desk.form.utils import add_comment
from frappe.model.workflow import get_workflow_name
from frappe.query_builder import DocType
from frappe.utils.data import get_url_to_form
from frappe.share import add as add_share


@frappe.whitelist()
def get_approval_roles(doc: Document, method: str | None = None):
	settings = frappe.get_cached_doc("Document Approval Settings")
	if doc.doctype not in settings.doctypes:
		return []

	roles = []
	for document_approval_rule_name in frappe.get_all(
		"Document Approval Rule", filters={"approval_doctype": doc.doctype}, pluck="name"
	):
		document_approval_rule = frappe.get_cached_doc(
			"Document Approval Rule", document_approval_rule_name
		)
		if document_approval_rule.apply(doc):
			roles.append((document_approval_rule.approval_role, document_approval_rule.name))

	user_approvals = frappe.get_all(
		"User Document Approval",
		{"reference_doctype": doc.doctype, "reference_name": doc.name},
		pluck="approver",
	)
	user_approvals = [(user_approval, None) for user_approval in user_approvals]
	roles.extend(user_approvals)

	if not roles:
		fallback_approver = settings.fallback_approver_role
		if not fallback_approver:
			frappe.throw(
				_("No approvers found. Please set a fallback approver role in Document Approval Settings.")
			)
		roles.append((fallback_approver, None))
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
def fetch_approvals_and_roles(doc: Document, method: str | None = None):
	doc = frappe._dict(json.loads(doc)) if isinstance(doc, str) else doc
	settings = frappe.get_cached_doc("Document Approval Settings")
	if doc.doctype not in settings.doctypes:
		return
	if doc.get("__islocal"):
		return
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
	for element in roles:
		role = element[0]
		document_approval_rule = element[1]
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
				"document_approval_rule": document_approval_rule,
			}
		)
		add_roles.append(_role)
	approval_state = frappe.get_value("Workflow", get_workflow_name(doc.doctype), "approval_state")
	workflow_exists = frappe.db.exists("Workflow", get_workflow_name(doc.doctype))
	require_rejection_reason = True
	if workflow_exists:
		require_rejection_reason = bool(
			cint(frappe.get_value("Workflow", get_workflow_name(doc.doctype), "require_rejection_reason"))
		)

	return {
		"approvals": add_roles,
		"approval_state": approval_state,
		"workflow_exists": workflow_exists,
		"require_rejection_reason": require_rejection_reason,
	}


@frappe.whitelist()
def approve_document(
	doc: Document, method: str | None = None, role: str | None = None, user: str | None = None
):
	doc = frappe._dict(json.loads(doc)) if isinstance(doc, str) else doc
	approval = frappe.new_doc("Document Approval")
	approval.reference_doctype = doc.doctype
	approval.reference_name = doc.name
	approval.approver = user
	approval.approval_role = role if role != "User Approval" else None
	approval.user_approval = "User Approval" if role == "User Approval" else None
	approval.save(ignore_permissions=True)
	todo = frappe.get_value("ToDo", {"reference_name": doc.name, "role": role}, "name")
	if todo:
		todo = frappe.get_doc("ToDo", todo)
		todo.status = "Closed"
		todo.save(ignore_permissions=True)
		frappe.db.commit()

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
	if doc.meta.is_submittable and doc.docstatus != 1:
		return
	if not check_all_document_approvals(doc, method, automatic):
		frappe.throw("All Approvers are required to Submit this document")


@frappe.whitelist()
def reject_document(
	doc: Document,
	role=None,
	comment: str = "",
	document_approval_rule_name: str = "",
	method: str | None = None,
):
	from approvals.approvals.doctype.document_approval_rule.document_approval_rule import get_users

	doc = frappe._dict(json.loads(doc)) if isinstance(doc, str) else doc
	doc = frappe.get_doc(doc.doctype, doc.name)
	doc.save(ignore_permissions=True)
	doc.set_status(update=True, status="Rejected")
	rejection = None
	if comment:
		rejection = add_comment(doc.doctype, doc.name, comment, frappe.session.user, frappe.session.user)
	revoke_approvals_on_reject(doc, method)

	if document_approval_rule_name:
		document_approval_rule = frappe.get_doc("Document Approval Rule", document_approval_rule_name)
	else:
		document_approval_rule = frappe.new_doc("Document Approval Rule")

	if not document_approval_rule.primary_rejection_user:
		settings = frappe.get_cached_doc("Document Approval Settings")
		users = get_users(settings.fallback_approver_role)
		if not users:
			return rejection

		document_approval_rule.primary_rejection_user = users[0]

	document_approval_rule.assign_user(doc=doc, rejection=True)
	return rejection


@frappe.whitelist()
def revoke_approvals_on_reject(doc: Document, method: str | None = None):
	for approval in frappe.get_all(
		"Document Approval", filters={"reference_doctype": doc.doctype, "reference_name": doc.name}
	):
		frappe.get_doc("Document Approval", approval).delete(ignore_permissions=True)
	for approval in frappe.get_all(
		"User Document Approval", filters={"reference_doctype": doc.doctype, "reference_name": doc.name}
	):
		frappe.get_doc("User Document Approval", approval).delete(ignore_permissions=True)


@frappe.whitelist()
def assign_approvers(doc: Document, method: str | None = None):
	roles = frappe.get_all(
		"Document Approval Rule", {"approval_doctype": doc.doctype}, pluck="approval_role"
	)

	for role in roles:
		approval_rule = frappe.get_cached_doc(
			"Document Approval Rule",
			{"approval_doctype": doc.doctype, "approval_role": role},
		)
		if approval_rule.apply(doc):
			approval_rule.assign_user(doc)


@frappe.whitelist()
def add_user_approval(doc: Document, method: str | None = None, user: str | None = None):
	if not user:
		return
	doc = frappe._dict(json.loads(doc)) if isinstance(doc, str) else doc
	if not frappe.has_permission(doc.doctype, ptype="read", user=user, doc=doc.name):
		add_share(doc.doctype, doc.name, user, read=True, write=True, share=True)

	uda = frappe.new_doc("User Document Approval")
	uda.reference_doctype = doc.doctype
	uda.reference_name = doc.name
	uda.approver = user
	uda.save(ignore_permissions=True)
	frappe.db.commit()


@frappe.whitelist()
def remove_user_approval(doc: Document, method: str | None = None, user=None):
	doc = frappe._dict(json.loads(doc)) if isinstance(doc, str) else doc
	user_approval = frappe.get_doc(
		"User Document Approval",
		{"reference_doctype": doc.doctype, "reference_name": doc.name, "approver": user},
	)
	user_approval.delete()
	removal = frappe.new_doc("Comment")
	removal.reference_doctype = doc.doctype
	removal.reference_name = doc.name
	removal.comment_type = "Info"
	removal.comment_email = frappe.session.user
	removal.content = f"<b>{user}<b> removed as approver by <b>{frappe.session.user}</b>"
	removal.subject = "Approver removed"
	removal.save(ignore_permissions=True)
	return


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
