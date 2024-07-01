import frappe
from frappe import _
from frappe.model.document import Document


class DocumentApproval(Document):
	def validate(self):
		self.validate_user_has_role()
		self.title = f"{self.reference_name} - {self.approver}"

	def validate_user_has_role(self):
		if not self.user_approval:
			if not frappe.get_value("Has Role", {"parent": self.approver, "role": self.approval_role}):
				frappe.throw(_("Approving User does not have the required Role"), frappe.PermissionError)

		if self.user_approval:
			user_approvals = frappe.get_all(
				"User Document Approval",
				filters={
					"reference_doctype": self.reference_doctype,
					"reference_name": self.reference_name,
					"approver": self.approver,
				},
			)

			if not user_approvals:
				frappe.throw(
					_("This User has not been assigned an approval for this document"),
					frappe.PermissionError,
				)
