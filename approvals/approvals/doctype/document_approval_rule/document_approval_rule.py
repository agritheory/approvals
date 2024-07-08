import frappe
import frappe.cache_manager
from frappe.model.document import Document
from frappe.share import add as add_share
from frappe.utils import today

from approvals.approvals.api import create_approval_notification


class DocumentApprovalRule(Document):
	def validate(self):
		self.title = f"{self.approval_doctype} - {self.approval_role}"

	def apply(
		self,
		doc: Document,
		method: str | None = None,
		doctype: str | None = None,
		name: str | None = None,
	):
		if frappe.flags.in_patch or frappe.flags.in_install or frappe.flags.in_setup_wizard:
			return False

		if not self.enabled:
			return False

		if not self.condition:
			return True

		# try:
		eval_globals = frappe._dict(
			{
				"frappe": frappe._dict(
					{
						"get_value": frappe.db.get_value,
						"get_all": frappe.db.get_all,
					}
				),
				"any": any,
				"all": all,
			}
		)
		settings = frappe.get_doc("Document Approval Settings")
		eval_locals = {"doc": doc, "settings": settings.get_settings()}
		return frappe.safe_eval(self.condition, eval_globals=eval_globals, eval_locals=eval_locals)
		# except:
		# 	frappe.throw(f'Error parsing approval rule conditions for {self.title}')

	def get_message(self, doc: Document):
		return frappe.render_template(self.message, doc.__dict__)

	def assign_user(self, doc: Document):
		users = get_users(self.approval_role)
		# get index of current user
		if not users:
			frappe.throw(f"No users are assigned this approval role: {self.approval_role}")
		if self.primary_assignee:
			self.last_user = self.primary_assignee
			user = self.primary_assignee
		else:
			index = users.index(self.last_user) if self.last_user and self.last_user in users else 0
			user = users[index % len(users)]
		if frappe.get_value(
			"ToDo",
			{"role": self.approval_role, "owner": user, "reference_name": doc.name, "status": "Open"},
		):
			return
		add_share(doc.doctype, doc.name, user, read=True, write=True)  # share document with user
		todo = frappe.new_doc("ToDo")
		todo.owner = user  # Saving as 'Administrator' regardless of user value
		todo.allocated_to = user
		todo.reference_type = doc.doctype
		todo.reference_name = doc.name
		todo.role = self.approval_role
		todo.assigned_by = "Administrator"
		todo.date = today()
		todo.status = "Open"
		todo.priority = "Medium"
		todo.description = (
			self.get_message(doc) if self.message else "A document has been assigned to you"
		)
		todo.save(ignore_permissions=True)
		if self.message:
			create_approval_notification(doc, user)


@frappe.whitelist()
def get_users(role: str):
	users = frappe.get_all(
		"User",
		filters={"enabled": True, "user_type": "System User", "name": ("!=", "Administrator")},
		pluck="name",
	)

	users_with_role = frappe.get_all(
		"Has Role", filters={"role": role, "parent": ("in", users)}, pluck="parent"
	)

	return users_with_role
