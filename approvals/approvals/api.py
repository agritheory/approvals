import json

import frappe
from frappe import _
from frappe.utils import cint, get_datetime
from frappe.desk.form.utils import add_comment
from frappe.model.workflow import get_workflow_name
from frappe.query_builder import DocType
from frappe.utils.data import get_url_to_form


@frappe.whitelist()
def get_approval_roles(doc, method=None):
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
def get_document_approvals(doc, method=None):
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
def fetch_approvals_and_roles(doc, method=None):
	doc = frappe._dict(json.loads(doc)) if isinstance(doc, str) else doc
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
def approve_document(doc, method=None, role=None, user=None):
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

	checked_all = check_all_document_approvals(doc, method, include_role=role, user=user)
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
def check_all_document_approvals(doc, method=None, include_role=None, user=None):
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
def set_status_to_approved(doc, method=None, automatic=False):
	if doc.status != "Approved":
		return
	if not check_all_document_approvals(doc, method, automatic):
		frappe.throw("All Approvers are required to Submit this document")


@frappe.whitelist()
def reject_document(doc, role=None, comment="", method=None):
	doc = frappe._dict(json.loads(doc)) if isinstance(doc, str) else doc
	doc = frappe.get_doc(doc.doctype, doc.name)
	doc.save(ignore_permissions=True)
	doc.set_status(update=True, status="Rejected")
	rejection = add_comment(doc.doctype, doc.name, comment, frappe.session.user, frappe.session.user)
	revoke_approvals_on_reject(doc, method)
	return rejection


@frappe.whitelist()
def revoke_approvals_on_reject(doc, method=None):
	for approval in frappe.get_all(
		"Document Approval", filters={"reference_doctype": doc.doctype, "reference_name": doc.name}
	):
		frappe.get_doc("Document Approval", approval).delete()
	for approval in frappe.get_all(
		"User Document Approval", filters={"reference_doctype": doc.doctype, "reference_name": doc.name}
	):
		frappe.get_doc("User Document Approval", approval).delete()


@frappe.whitelist()
def assign_approvers(doc, method=None):
	roles = [
		{"approval_role": i["approval_role"]}
		for i in frappe.get_all(
			"Document Approval Rule", {"approval_doctype": doc.doctype}, "approval_role"
		)
	]
	for role in roles:
		approval_rule = frappe.get_cached_doc(
			"Document Approval Rule",
			{"approval_doctype": doc.doctype, "approval_role": role["approval_role"]},
		)
		if approval_rule.apply(doc):
			approval_rule.assign_user(doc)


@frappe.whitelist()
def add_user_approval(doc, method=None, user=None):
	if not user:
		return
	doc = frappe._dict(json.loads(doc)) if isinstance(doc, str) else doc
	uda = frappe.new_doc("User Document Approval")
	uda.reference_doctype = doc.doctype
	uda.reference_name = doc.name
	uda.approver = user
	uda.save(ignore_permissions=True)
	frappe.db.commit()


@frappe.whitelist()
def remove_user_approval(doc, method=None, user=None):
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
def create_approval_notification(doc, user):
	no = frappe.new_doc("Notification Log")
	no.flags.ignore_permissions = True
	no.owner = "Administrator"
	no.for_user = user
	no.subject = f"A {doc.doctype} requires your approval"
	no.type = "Assignment"
	no.document_type = doc.doctype
	no.document_name = doc.name
	no.from_user = doc.owner
	no.email_content = f"{doc.doctype} {doc.name} requires your approval"
	try:
		no.save(ignore_permissions=True)
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
