import frappe
from frappe.model.document import Document
from frappe.utils.data import today
from approvals.approvals.api import create_approval_notification


class UserDocumentApproval(Document):
	def validate(self):
		self.title = f"{self.reference_name} - {self.approver}"
		self.add_todo()

	def on_trash(self):
		self.remove_todo()

	def add_todo(self):
		todo = frappe.new_doc("ToDo")
		todo.owner = self.approver
		todo.reference_type = self.reference_doctype
		todo.reference_name = self.reference_name
		todo.assigned_by = "Administrator"
		todo.date = today()
		todo.status = "Open"
		todo.priority = "Medium"
		todo.description = "A document requires your approval"
		todo.save()
		create_approval_notification(
			frappe._dict(
				{"doctype": self.reference_doctype, "name": self.reference_name, "owner": frappe.session.user}
			),
			self.approver,
		)

	def remove_todo(self):
		todo = frappe.get_value(
			"ToDo", {"reference_name": self.reference_name, "owner": self.approver}, "name"
		)
		if todo:
			frappe.delete_doc('ToDo', todo, force=True)
