import ast
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.share import add as add_share
from frappe.utils import today


class DocumentApprovalRule(Document):
	def validate(self):
		self.title = f"{self.approval_doctype} - {self.approval_role}"

	def is_syntax_valid_and_returning_bool(self):
		from RestrictedPython import compile_restricted

		if not self.condition:
			return True

		try:
			compile_restricted(self.condition)
		except Exception as e:
			return False, _(f"Error parsing approval rule condition:<br> <code>{e}</code>")

		tree = ast.parse(self.condition)
		last_statement = tree.body[-1]

		if isinstance(last_statement, ast.Expr):
			return_expr = last_statement.value
		elif isinstance(last_statement, ast.Return):
			return_expr = last_statement.value
		else:
			return False, _("Condition should returns a boolean value")

		bool_exprs = (ast.Compare, ast.BoolOp, ast.UnaryOp)
		bool_values = (ast.Constant,)

		if isinstance(return_expr, bool_exprs) or (
			isinstance(return_expr, bool_values) and isinstance(return_expr.value, bool)
		):
			return True, ""
		return False, _("Condition should returns a boolean value")

	@frappe.whitelist()
	def test_condition(self, doctype: str, docname: str):
		doc = frappe.get_doc(doctype, docname)

		result, message = self.is_syntax_valid_and_returning_bool()
		if not result:
			return message

		try:
			result = self.apply(doc)
			if result:
				return _(f"Document Approval Rule applies to {doctype} {docname}")
			return _(f"Document Approval Rule not applies to {doctype} {docname}")
		except Exception as e:
			return _(f"Error: {e}")

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
		# if result and self.assign_users:
		# 	self.assign_user(doc)
		return result
		# except:
		# 	frappe.throw(f'Error parsing approval rule conditions for {self.title}')

	def get_message(self, doc: Document):
		return frappe.render_template(self.message, doc.__dict__)

	def assign_user(self, doc: Document, rejection: bool = False):
		if doc.meta:
			workflow_name = doc.meta.get_workflow()
			if workflow_name:
				workflow_state_field = frappe.get_cached_value(
					"Workflow", workflow_name, "workflow_state_field"
				)
				approval_state = frappe.get_cached_value("Workflow", workflow_name, "approval_state")
				if doc.get(workflow_state_field) != approval_state:
					return

		if rejection:
			user = self.primary_rejection_user
		else:
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
			{
				"role": self.approval_role,
				"allocated_to": user,
				"reference_name": doc.name,
				"status": "Open",
			},
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
			todo.document_approval_rule = self.name
			todo.rejection = rejection
			todo.description = (
				self.get_message(doc) if self.message else frappe._("A document has been assigned to you")
			)
			todo.save(ignore_permissions=True)


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
