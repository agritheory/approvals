import frappe
from frappe.model.document import Document
from frappe.utils.data import today
from frappe.share import add as add_share

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
		result = frappe.safe_eval(self.condition, eval_globals=eval_globals, eval_locals=eval_locals)
		if result and self.assign_users:
			self.assign_user(doc)
		return result
		# except:
		# 	frappe.throw(f'Error parsing approval rule conditions for {self.title}')

	def get_message(self, doc):
		return frappe.render_template(self.message, doc.__dict__)

	def assign_user(self, doc: Document):
		if doc.meta:
			workflow_name = doc.meta.get_workflow()
			if workflow_name:
				workflow_state_field = frappe.get_cached_value(
					"Workflow", workflow_name, "workflow_state_field"
				)
				approval_state = frappe.get_cached_value("Workflow", workflow_name, "approval_state")
				if doc.get(workflow_state_field) != approval_state:
					return
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
		if not frappe.has_permission(doc.doctype, ptype="read", user=user, doc=doc.name):
			add_share(doc.doctype, doc.name, user, read=True, write=True, share=True)
		if not frappe.db.get_value(
			"ToDo",
			{
				"allocated_to": user,
				"reference_type": doc.doctype,
				"reference_name": doc.name,
			},
		):
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
				self.get_message(doc) if self.message else frappe._("A document has been assigned to you")
			)
			todo.save(ignore_permissions=True)
			if self.message:
				create_approval_notification(doc, user)


@frappe.whitelist()
def get_users(role):
	return [
		i["parent"]
		for i in frappe.db.sql(
			"""
	SELECT `tabHas Role`.parent
	FROM `tabHas Role`, `tabUser`
	WHERE
		`tabHas Role`.role = %(role)s
		AND `tabHas Role`.parent = `tabUser`.name
		AND `tabUser`.enabled = 1
		AND `tabUser`.user_type = 'System User'
		AND `tabUser`.name != 'Administrator'
	ORDER BY parent
	""",
			{"role": role},
			as_dict=True,
		)
	]
