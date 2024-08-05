import frappe
from frappe.model.document import Document
from frappe.share import add as add_share
from frappe.utils.data import today


class UserDocumentApproval(Document):
	def validate(self):
		self.title = f"{self.reference_name} - {self.approver}"

	def after_insert(self):
		self.add_todo()

	def on_trash(self):
		self.remove_todo()

	def add_todo(self):
		add_share(self.reference_doctype, self.reference_name, self.approver, read=True, write=True)

		todo = frappe.new_doc("ToDo")
		todo.owner = self.approver
		todo.allocated_to = self.approver
		todo.reference_type = self.reference_doctype
		todo.reference_name = self.reference_name
		todo.assigned_by = "Administrator"
		todo.date = today()
		todo.status = "Open"
		todo.priority = "Medium"
		todo.description = frappe._("A document requires your approval")
		todo.user_document_approval = self.name
		todo.save(ignore_permissions=True)

	def remove_todo(self):
		if todo := frappe.get_value(
			"ToDo", {"reference_name": self.reference_name, "allocated_to": self.approver}, "name"
		):
			frappe.delete_doc("ToDo", todo, force=True)
