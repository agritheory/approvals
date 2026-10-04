# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.share import add_docshare
from frappe.utils.data import today


class UserDocumentApproval(Document):
	def validate(self):
		self.title = f"{self.reference_name} - {self.approver}"
		if not self.todo or not frappe.db.exists("ToDo", self.todo):
			self.add_todo()

	def on_trash(self):
		self.remove_todo()

	def add_todo(self):
		if not frappe.has_permission(
			self.reference_doctype, ptype="read", user=self.approver, doc=self.reference_name
		):
			add_docshare(
				self.reference_doctype,
				self.reference_name,
				user=self.approver,
				read=1,
				write=1,
				share=0,
				flags={"ignore_share_permission": True},
			)

		todo = frappe.new_doc("ToDo")
		todo.owner = self.approver
		todo.allocated_to = self.approver
		todo.reference_type = self.reference_doctype
		todo.reference_name = self.reference_name
		todo.role = self.satisfies_role
		todo.assigned_by = self.requested_by or frappe.session.user
		todo.date = today()
		todo.status = "Open"
		todo.priority = "Medium"
		todo.description = self.reason or "A document requires your approval"
		todo.save(ignore_permissions=True)
		self.todo = todo.name

	def remove_todo(self):
		if self.todo and frappe.db.exists("ToDo", self.todo):
			todo_name = self.todo
			frappe.db.set_value("User Document Approval", self.name, "todo", None)
			self.todo = None
			frappe.delete_doc("ToDo", todo_name, ignore_permissions=True)
			return
		todo = frappe.get_value(
			"ToDo",
			{
				"reference_type": self.reference_doctype,
				"reference_name": self.reference_name,
				"allocated_to": self.approver,
			},
			"name",
		)
		if todo:
			frappe.delete_doc("ToDo", todo, ignore_permissions=True)
