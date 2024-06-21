import frappe
from frappe.model.document import Document


def has_permission(doc: Document, ptype: str | None = None, user: str | None = None) -> bool:
	user = user or frappe.session.user

	approval_rules = frappe.get_all(
		"Document Approval Rule",
		filters={"enabled": True, "approval_doctype": doc.doctype},
		fields=["approval_role", "primary_assignee"],
	)

	user_roles = frappe.get_roles(user)
	for rule in approval_rules:
		# check if a document approval rule sets the primary assignee to the user
		if rule.primary_assignee == user:
			return True
		# check if a document approval rule sets the approval role to any of the user's roles
		if rule.approval_role in user_roles:
			return True

	# check if another user manually requests the current user for approval
	user_document_approvals = frappe.get_all(
		"User Document Approval",
		filters={"approver": user, "reference_doctype": doc.doctype, "reference_name": doc.name},
	)

	if user_document_approvals:
		return True

	# fallback to standard permission check if all of the above are false
	return doc.has_permission()
