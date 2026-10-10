# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import ast
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from frappe.utils.data import cstr, today
from frappe.utils.safe_exec import render_safe_globals

from approvals.approvals.api import create_approval_notification, get_document_approvals
from approvals.approvals.user_approvals import (
	close_open_approval_todos,
	ensure_share,
	get_approval_workflow,
	in_install_or_patch,
	todo_filters,
)

CHILD_TABLE_FIELDTYPES = ("Table", "Table MultiSelect")
IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
STRING_LITERAL = re.compile(r"""('(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*")""", re.DOTALL)


class DocumentApprovalRule(Document):
	def autoname(self):
		key = "User" if self.approver_type == "User" else self.approval_role
		self.name = make_autoname(f"{self.approval_doctype}-{key}-.#####", "", self)

	def validate(self):
		self.approver_type = self.approver_type or "Role"
		if self.approver_type == "User":
			if not self.approvers:
				frappe.throw(_("Approvers expression is required when Approver Type is User"))
			validate_condition(self.approvers, self.approval_doctype)
			self.condition = None
			self.title = f"{self.approval_doctype} - User"
			if self.approval_role:
				self.title += f" ({self.approval_role})"
		else:
			if not self.approval_role:
				frappe.throw(_("Approval Role is required when Approver Type is Role"))
			validate_condition(self.condition, self.approval_doctype)
			self.approvers = None
			self.title = f"{self.approval_doctype} - {self.approval_role}"

	def is_active(self, doc: Document) -> bool:
		if in_install_or_patch() or not self.enabled:
			return False
		return not (self.skip_for_auto_repeat and doc.get("auto_repeat"))

	@frappe.whitelist()
	def test_condition(self, doctype: str, docname: str):
		doc = frappe.get_doc(doctype, docname)
		is_user_rule = self.approver_type == "User"

		try:
			validate_condition(self.approvers if is_user_rule else self.condition, self.approval_doctype)
		except Exception as e:
			label = _("approvers") if is_user_rule else _("condition")
			return _("Invalid {0} expression: {1}").format(label, e)

		if not self.enabled:
			return _("Document Approval Rule is disabled")
		if self.skip_for_auto_repeat and doc.get("auto_repeat"):
			return _("Document Approval Rule skipped: {0} {1} is an Auto Repeat document").format(
				doctype, docname
			)

		try:
			if is_user_rule:
				users = self.get_approvers(doc)
				if users:
					return _("Approvers for {0} {1}: {2}").format(doctype, docname, ", ".join(users))
				return _("No approvers required for {0} {1}").format(doctype, docname)
			if evaluate_condition(self.condition, doc):
				return _("Document Approval Rule applies to {0} {1}").format(doctype, docname)
			return _("Document Approval Rule does not apply to {0} {1}").format(doctype, docname)
		except Exception as e:
			return _("Error evaluating rule: {0}").format(e)

	def apply(self, doc: Document) -> bool:
		"""Whether this rule requires approval on doc. User rules always apply; their expression picks people."""
		if not self.is_active(doc):
			return False
		if self.approver_type == "User":
			return True
		try:
			return evaluate_condition(self.condition, doc)
		except Exception as e:
			frappe.log_error(
				f"Error evaluating approval rule condition for {self.title}: {e}",
				"Document Approval Rule Error",
			)
			return False

	def get_approvers(self, doc: Document) -> list[str]:
		if self.approver_type != "User" or not self.is_active(doc):
			return []
		try:
			return normalize_approver_list(evaluate_expression(self.approvers, doc))
		except Exception as e:
			frappe.log_error(
				f"Error evaluating approvers for {self.title}: {e}",
				"Document Approval Rule Error",
			)
			return []

	def get_message(self, doc: Document):
		return frappe.render_template(self.message, doc.__dict__)

	def assign_user(self, doc: Document):
		if self.approver_type != "Role":
			return
		if self.approval_role in get_document_approvals(doc):
			close_open_approval_todos(doc, self.approval_role)
			return
		workflow = get_approval_workflow(doc.doctype)
		if workflow and doc.get(workflow.workflow_state_field) != workflow.approval_state:
			return

		users = get_users(self.approval_role)
		if not users:
			frappe.throw(_("No users are assigned this approval role: {0}").format(self.approval_role))
		if self.primary_assignee:
			self.last_user = self.primary_assignee
			user = self.primary_assignee
		else:
			index = users.index(self.last_user) if self.last_user in users else 0
			user = users[index % len(users)]

		if frappe.db.exists("ToDo", todo_filters(doc, allocated_to=user, status="Open")):
			return
		todo = self.create_approval_todo(doc, user)
		if self.message:
			create_approval_notification(doc, user, todo_name=todo.name)

	def create_approval_todo(
		self,
		doc: Document,
		user: str,
		description: str | None = None,
		assigned_by: str = "Administrator",
	) -> Document:
		ensure_share(doc, user)
		todo = frappe.new_doc("ToDo")
		todo.update(
			todo_filters(
				doc,
				owner=user,
				allocated_to=user,
				role=self.approval_role,
				document_approval_rule=self.name,
				assigned_by=assigned_by,
				date=today(),
				status="Open",
				priority="Medium",
				description=description
				or (self.get_message(doc) if self.message else _("A document requires your approval")),
			)
		)
		todo.save(ignore_permissions=True)
		return todo


@frappe.whitelist()
def get_users(role: str):
	has_role = frappe.qb.DocType("Has Role")
	user = frappe.qb.DocType("User")
	return (
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
		.run(pluck=True)
	)


def normalize_approver_list(value) -> list[str]:
	if isinstance(value, str):
		value = [value]
	if not isinstance(value, (list, tuple)):
		return []
	users = (cstr(item).strip() for item in value if item)
	return list(dict.fromkeys(user for user in users if user))


def get_condition_globals():
	globals_dict = render_safe_globals()
	for path in frappe.get_hooks("approval_condition_context") or []:
		extra = frappe.get_attr(path)()
		if isinstance(extra, dict):
			globals_dict.update(extra)
	return globals_dict


def evaluate_expression(expression: str, doc):
	if not expression:
		return None
	# doc must live in eval_globals: list comprehensions in safe_eval cannot see eval_locals (PEP 572 scope).
	eval_globals = get_condition_globals()
	eval_globals["doc"] = doc
	eval_globals["settings"] = frappe.get_cached_doc("Document Approval Settings").get_settings()
	return frappe.safe_eval(expression, eval_globals=eval_globals, eval_locals={})


def evaluate_condition(condition: str, doc) -> bool:
	return True if not condition else bool(evaluate_expression(condition, doc))


def validate_condition(condition: str, doctype: str | None = None):
	if not condition:
		return
	try:
		ast.parse(condition, mode="eval")
	except SyntaxError as e:
		frappe.throw(_("Invalid condition expression: {0}").format(e.msg))
	if doctype:
		validate_condition_fields(condition, doctype)


def text_is_call(text: str, index: int) -> bool:
	return text[index:].lstrip().startswith("(")


def collect_condition_field_references(condition: str):
	"""Read doc.field and doc.get('field') names, plus child fields the expression touches."""
	parent_fields: set[str] = set()
	child_fields: dict[str, set[str]] = {}
	table_reads: set[str] = set()

	def add_child(table: str, field: str):
		child_fields.setdefault(table, set()).add(field)

	doc_get = re.compile(rf"(?<![\w.])doc\.get\(\s*(['\"])({IDENTIFIER})\1\s*\)")
	for match in doc_get.finditer(condition):
		parent_fields.add(match.group(2))

	index_get = re.compile(
		rf"(?<![\w.])doc\.({IDENTIFIER})\s*\[[^\]]*\]\s*\.get\(\s*(['\"])({IDENTIFIER})\2\s*\)"
	)
	for match in index_get.finditer(condition):
		table_reads.add(match.group(1))
		add_child(match.group(1), match.group(3))

	stripped = STRING_LITERAL.sub("''", condition)

	doc_attr = re.compile(rf"(?<![\w.])doc\.({IDENTIFIER})")
	for match in doc_attr.finditer(stripped):
		if not text_is_call(stripped, match.end()):
			parent_fields.add(match.group(1))

	for_loop = re.compile(rf"for\s+({IDENTIFIER})\s+in\s+doc\.({IDENTIFIER})")
	for match in for_loop.finditer(stripped):
		variable, table = match.group(1), match.group(2)
		table_reads.add(table)
		parent_fields.add(table)
		variable_attr = re.compile(rf"(?<![\w.]){re.escape(variable)}\.({IDENTIFIER})")
		for attr in variable_attr.finditer(stripped):
			if not text_is_call(stripped, attr.end()):
				add_child(table, attr.group(1))
		variable_get = re.compile(
			rf"(?<![\w.]){re.escape(variable)}\.get\(\s*(['\"])({IDENTIFIER})\1\s*\)"
		)
		for attr in variable_get.finditer(condition):
			add_child(table, attr.group(2))

	index_attr = re.compile(rf"(?<![\w.])doc\.({IDENTIFIER})\s*\[[^\]]*\]\s*\.({IDENTIFIER})")
	for match in index_attr.finditer(stripped):
		if text_is_call(stripped, match.end()):
			continue
		table_reads.add(match.group(1))
		parent_fields.add(match.group(1))
		add_child(match.group(1), match.group(2))

	return parent_fields, child_fields, table_reads


def validate_condition_fields(condition: str, doctype: str):
	parent_fields, child_fields, table_reads = collect_condition_field_references(condition)
	fields_by_name = {df.fieldname: df for df in frappe.get_meta(doctype).fields}
	problems = []

	missing = sorted(parent_fields - set(fields_by_name))
	if missing:
		problems.append(_("{0} has no field: {1}").format(doctype, ", ".join(missing)))

	not_tables = []
	for table in sorted(table_reads):
		field = fields_by_name.get(table)
		if not field:
			continue
		if field.fieldtype not in CHILD_TABLE_FIELDTYPES:
			not_tables.append(table)
			continue
		child_names = {df.fieldname for df in frappe.get_meta(field.options).fields}
		missing_child = sorted(child_fields.get(table, set()) - child_names)
		if missing_child:
			problems.append(_("{0} has no field: {1}").format(field.options, ", ".join(missing_child)))

	if not_tables:
		problems.append(_("{0} is not a child table on {1}").format(", ".join(not_tables), doctype))

	if problems:
		frappe.throw("<br>".join(problems), title=_("Invalid Condition"))
