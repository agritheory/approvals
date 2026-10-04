# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import ast

import frappe
from frappe.utils.safe_exec import render_safe_globals


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


def validate_condition(condition: str):
	if not condition:
		return

	try:
		ast.parse(condition, mode="eval")
	except SyntaxError as e:
		frappe.throw(frappe._("Invalid condition expression: {0}").format(e.msg))
