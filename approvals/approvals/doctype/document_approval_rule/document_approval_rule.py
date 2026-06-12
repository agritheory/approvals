# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import ast
import frappe
from frappe.model.document import Document
from frappe.utils.data import today
from frappe.share import add as add_share
from approvals.approvals.api import create_approval_notification
from frappe import render_template
from frappe.utils.jinja import validate_template
from jinja2 import Environment, BaseLoader, TemplateSyntaxError, UndefinedError


class DocumentApprovalRule(Document):
	def validate(self):
		self.title = f"{self.approval_doctype} - {self.approval_role}"

		if self.condition:
			try:
				validate_template(self.condition)
			except Exception as e:
				frappe.throw(f"Invalid Jinja condition: {str(e)}")

	def is_syntax_valid_and_returning_bool(self):
		from RestrictedPython import compile_restricted

		if not self.condition:
			return True

		try:
			compile_restricted(self.condition)
		except Exception as e:
			return False, frappe._(f"Error parsing approval rule condition:<br> <code>{e}</code>")

		tree = ast.parse(self.condition)
		last_statement = tree.body[-1]

		if isinstance(last_statement, ast.Expr):
			return_expr = last_statement.value
		elif isinstance(last_statement, ast.Return):
			return_expr = last_statement.value
		else:
			return False, frappe._("Condition should return a boolean value")

		bool_exprs = (ast.Compare, ast.BoolOp, ast.UnaryOp)
		bool_values = (ast.Constant,)

		if isinstance(return_expr, bool_exprs) or (
			isinstance(return_expr, bool_values) and isinstance(return_expr.value, bool)
		):
			return True, ""
		return False, frappe._("Condition should return a boolean value")

	@frappe.whitelist()
	def test_condition(self, doctype: str, docname: str):
		doc = frappe.get_doc(doctype, docname)

		result, message = self.is_syntax_valid_and_returning_bool()
		if not result:
			return message

		try:
			result = self.apply(doc, dry=True)
			if result:
				return frappe._(f"Document Approval Rule applies to {doctype} {docname}")
			return frappe._(f"Document Approval Rule does not apply to {doctype} {docname}")
		except Exception as e:
			return frappe._(f"Error: {e}")

	def apply(
		self,
		doc: Document,
		method: str | None = None,
		doctype: str | None = None,
		name: str | None = None,
		dry: bool = False,
	):
		if frappe.flags.in_patch or frappe.flags.in_install or frappe.flags.in_setup_wizard:
			return False

		if not self.enabled:
			return False

		if self.skip_for_auto_repeat and doc.get("auto_repeat"):
			return False

		if not self.condition:
			return True

		try:
			result = self.evaluate_jinja_condition(doc)

			if result and self.assign_users:
				self.assign_user(doc)
			return result

		except Exception as e:
			frappe.log_error(
				f"Error evaluating approval rule condition for {self.title}: {str(e)}",
				"Document Approval Rule Error",
			)
			return False

	def evaluate_jinja_condition(self, doc: Document):
		"""Evaluate Jinja-based condition"""
		try:
			context = self.get_jinja_context(doc)

			# Create Jinja environment
			jinja_env = Environment(loader=BaseLoader(), autoescape=True)
			template = jinja_env.from_string(self.condition)
			result = template.render(**context)

			if isinstance(result, str):
				result = result.strip().lower()
				return result not in ["false", "0", "", "none", "null"]

			return bool(result)

		except TemplateSyntaxError as e:
			frappe.log_error(
				f"Jinja syntax error in approval rule {self.name}: {str(e)}",
				"Document Approval Jinja Error",
			)
			return False

		except UndefinedError as e:
			frappe.log_error(
				f"Undefined variable in approval rule {self.name}: {str(e)}",
				"Document Approval Jinja Error",
			)
			return False

	def get_jinja_context(self, doc: Document):
		"""Prepare context for Jinja evaluation"""
		settings = frappe.get_doc("Document Approval Settings")

		context = {
			"doc": doc,
			"settings": settings.get_settings(),
			"frappe": frappe._dict(
				{
					"get_value": frappe.db.get_value,
					"get_all": frappe.db.get_all,
				}
			),
			"any": any,
			"all": all,
		}

		context.update(self.get_account_context())
		context.update(get_condition_context())
		context.update(self.get_document_context(doc))

		return context

	def get_account_context(self):
		"""Get account-related context variables"""
		try:
			expense_accounts = frappe.get_all(
				"Account", filters={"account_type": "Expense Account"}, pluck="name"
			)

			tax_accounts = frappe.get_all(
				"Account", filters={"account_type": ["in", ["Tax", "Chargeable"]]}, pluck="name"
			)

			income_accounts = frappe.get_all(
				"Account", filters={"account_type": "Income Account"}, pluck="name"
			)

			asset_accounts = frappe.get_all(
				"Account",
				filters={"account_type": ["in", ["Fixed Asset", "Current Asset"]]},
				pluck="name",
			)

			return {
				"expense_accounts": expense_accounts,
				"tax_accounts": tax_accounts,
				"income_accounts": income_accounts,
				"asset_accounts": asset_accounts,
			}
		except Exception as e:
			frappe.log_error(f"Error getting account context: {str(e)}")
			return {
				"expense_accounts": [],
				"tax_accounts": [],
				"income_accounts": [],
				"asset_accounts": [],
			}

	def get_document_context(self, doc: Document):
		"""Get document-specific context variables"""
		context = {}

		if hasattr(doc, "doctype"):
			if doc.doctype in [
				"Purchase Invoice",
				"Sales Invoice",
				"Purchase Order",
				"Sales Order",
			]:
				context.update(
					{
						"total_amount": getattr(doc, "grand_total", 0),
						"net_amount": getattr(doc, "net_total", 0),
						"tax_amount": getattr(doc, "total_taxes_and_charges", 0),
						"company": getattr(doc, "company", ""),
						"currency": getattr(doc, "currency", ""),
						"supplier": getattr(doc, "supplier", ""),
						"customer": getattr(doc, "customer", ""),
					}
				)

				if hasattr(doc, "items") and doc.items:
					context.update(
						{
							"item_count": len(doc.items),
							"item_codes": [item.item_code for item in doc.items if item.item_code],
							"item_groups": list({item.item_group for item in doc.items if item.item_group}),
						}
					)

		return context

	def get_message(self, doc: Document):
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
			todo.document_approval_rule = self.name
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
def get_users(role: str):
	has_role = frappe.qb.DocType("Has Role")
	user = frappe.qb.DocType("User")

	result = (
		frappe.qb.from_(has_role)
		.join(user)
		.on(has_role.parent == user.name)
		.select(has_role.parent)
		.where(
			(has_role.role == role)
			& (user.enabled == 1)
			& (user.user_type == "System User")
			& (user.name != "Administrator")
		)
		.orderby(has_role.parent)
		.run(as_dict=True)
	)

	return [d["parent"] for d in result]


def account_numbers(*args):
	"""Returns a list of normalized account numbers"""
	return list(args)


def get_condition_context():
	"""Get additional context functions for conditions"""
	return {
		"account_numbers": account_numbers,
	}
