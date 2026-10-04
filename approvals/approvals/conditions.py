# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import ast
import re

import frappe
from frappe.utils.safe_exec import render_safe_globals

CHILD_TABLE_FIELDTYPES = ("Table", "Table MultiSelect")
IDENTIFIER = r"[A-Za-z_][A-Za-z0-9_]*"
STRING_LITERAL = re.compile(r"""('(?:\\.|[^'\\])*'|"(?:\\.|[^"\\])*")""", re.DOTALL)


def get_condition_globals():
	globals_dict = render_safe_globals()

	for path in frappe.get_hooks("approval_condition_context") or []:
		extra = frappe.get_attr(path)()
		if isinstance(extra, dict):
			globals_dict.update(extra)

	return globals_dict


def get_condition_locals(doc):
	settings = frappe.get_cached_doc("Document Approval Settings").get_settings()
	return {"doc": doc, "settings": settings}


def evaluate_condition(condition: str, doc) -> bool:
	if not condition:
		return True

	return bool(
		frappe.safe_eval(
			condition,
			eval_globals=get_condition_globals(),
			eval_locals=get_condition_locals(doc),
		)
	)


def validate_condition(condition: str, doctype: str | None = None):
	if not condition:
		return

	try:
		ast.parse(condition, mode="eval")
	except SyntaxError as e:
		frappe.throw(frappe._("Invalid condition expression: {0}").format(e.msg))

	if doctype:
		validate_condition_fields(condition, doctype)


def strip_string_literals(condition: str) -> str:
	return STRING_LITERAL.sub("''", condition)


def text_is_call(text: str, index: int) -> bool:
	return text[index:].lstrip().startswith("(")


def collect_condition_field_references(condition: str):
	"""Read doc.field and doc.get('field') names, plus child fields the expression touches."""
	parent_fields: set[str] = set()
	child_fields: dict[str, set[str]] = {}
	table_reads: set[str] = set()

	doc_get = re.compile(rf"(?<![\w.])doc\.get\(\s*(['\"])({IDENTIFIER})\1\s*\)")
	for match in doc_get.finditer(condition):
		parent_fields.add(match.group(2))

	index_get = re.compile(
		rf"(?<![\w.])doc\.({IDENTIFIER})\s*\[[^\]]*\]\s*\.get\(\s*(['\"])({IDENTIFIER})\2\s*\)"
	)
	for match in index_get.finditer(condition):
		table_reads.add(match.group(1))
		child_fields.setdefault(match.group(1), set()).add(match.group(3))

	stripped = strip_string_literals(condition)

	doc_attr = re.compile(rf"(?<![\w.])doc\.({IDENTIFIER})")
	for match in doc_attr.finditer(stripped):
		if text_is_call(stripped, match.end()):
			continue
		parent_fields.add(match.group(1))

	for_loop = re.compile(rf"for\s+({IDENTIFIER})\s+in\s+doc\.({IDENTIFIER})")
	for match in for_loop.finditer(stripped):
		variable, table = match.group(1), match.group(2)
		table_reads.add(table)
		parent_fields.add(table)
		variable_attr = re.compile(rf"(?<![\w.]){re.escape(variable)}\.({IDENTIFIER})")
		for attr in variable_attr.finditer(stripped):
			if text_is_call(stripped, attr.end()):
				continue
			child_fields.setdefault(table, set()).add(attr.group(1))
		variable_get = re.compile(
			rf"(?<![\w.]){re.escape(variable)}\.get\(\s*(['\"])({IDENTIFIER})\1\s*\)"
		)
		for attr in variable_get.finditer(condition):
			child_fields.setdefault(table, set()).add(attr.group(2))

	index_attr = re.compile(rf"(?<![\w.])doc\.({IDENTIFIER})\s*\[[^\]]*\]\s*\.({IDENTIFIER})")
	for match in index_attr.finditer(stripped):
		if text_is_call(stripped, match.end()):
			continue
		table_reads.add(match.group(1))
		parent_fields.add(match.group(1))
		child_fields.setdefault(match.group(1), set()).add(match.group(2))

	return parent_fields, child_fields, table_reads


def validate_condition_fields(condition: str, doctype: str):
	parent_fields, child_fields, table_reads = collect_condition_field_references(condition)
	meta = frappe.get_meta(doctype)
	fields_by_name = {df.fieldname: df for df in meta.fields}
	problems = []

	missing = sorted(parent_fields - set(fields_by_name))
	if missing:
		problems.append(frappe._("{0} has no field: {1}").format(doctype, ", ".join(missing)))

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
			problems.append(
				frappe._("{0} has no field: {1}").format(field.options, ", ".join(missing_child))
			)

	if not_tables:
		problems.append(
			frappe._("{0} is not a child table on {1}").format(", ".join(not_tables), doctype)
		)

	if problems:
		frappe.throw("<br>".join(problems), title=frappe._("Invalid Condition"))
