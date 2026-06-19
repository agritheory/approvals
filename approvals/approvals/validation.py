# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


def doctype_has_approval_rules(doctype: str) -> bool:
	return bool(
		frappe.db.exists("Document Approval Rule", {"approval_doctype": doctype, "enabled": 1})
	)


@frappe.whitelist()
def get_approval_roles(doc: Document | frappe._dict, method: str | None = None):
	settings = frappe.get_cached_doc("Document Approval Settings")

	roles = [
		role
		for role in frappe.get_all(
			"Document Approval Rule",
			filters={"approval_doctype": doc.doctype},
			pluck="approval_role",
		)
		if frappe.get_cached_doc(
			"Document Approval Rule", {"approval_doctype": doc.doctype, "approval_role": role}
		).apply(doc)
	]

	user_approvals = frappe.get_all(
		"User Document Approval",
		{"reference_doctype": doc.doctype, "reference_name": doc.name},
		pluck="approver",
	)

	roles.extend(user_approvals)

	if not roles:
		if not doctype_has_approval_rules(doc.doctype):
			return user_approvals
		fallback_approver = settings.fallback_approver_role
		if not fallback_approver:
			frappe.throw(
				_("No approvers found. Please set a fallback approver role in Document Approval Settings.")
			)
		roles.append(fallback_approver)
	return roles


@frappe.whitelist()
def get_document_approvals(doc: Document | frappe._dict, method: str | None = None):
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


def validate_all_approvals_complete(doc: Document, method: str | None = None):
	if frappe.flags.in_install or frappe.flags.in_patch or frappe.flags.in_setup_wizard:
		return
	if not doctype_has_approval_rules(doc.doctype):
		return
	if not get_approval_roles(doc):
		return
	if not check_all_document_approvals(doc, method=method or "before_submit"):
		frappe.throw(_("All approvers must approve this document before it can be finalized."))
