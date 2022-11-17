from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils.data import today

class DocumentApproval(Document):
	def validate(self):
		self.validate_user_has_role()
		self.title = f"{self.reference_name} - {self.approver}"

	def validate_user_has_role(self):
		if self.user_approval:
			user_approval = frappe.get_doc('User Document Approval', {
				'reference_doctype': self.reference_doctype,
				'reference_name': self.reference_name,
				'approver': self.approver
			})
			if not user_approval:
				frappe.throw(frappe._('This User has not been assigned an approval for this document'),frappe.PermissionError)
			return

		user_has_role = frappe.get_value('Has Role', {'parent': self.approver, 'role': self.approval_role})
		if not user_has_role:
			frappe.throw(frappe._('Approving User Does not have the Required Role'),frappe.PermissionError)
