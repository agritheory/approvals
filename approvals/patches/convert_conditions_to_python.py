# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import ast
import re

import frappe

from approvals.approvals.doctype.document_approval_rule.document_approval_rule import (
	validate_condition,
)

REMOVED_NAMES = (
	"account_numbers",
	"expense_accounts",
	"tax_accounts",
	"income_accounts",
	"asset_accounts",
	"total_amount",
	"net_amount",
	"tax_amount",
	"item_count",
	"item_codes",
	"item_groups",
)

SINGLE_JINJA_BLOCK = re.compile(r"^\{\{\s*(.+?)\s*\}\}$", re.DOTALL)
BARE_FLT = re.compile(r"(?<![.\w])flt\s*\(")
BARE_CINT = re.compile(r"(?<![.\w])cint\s*\(")


def convert_condition_text(condition: str) -> tuple[str | None, str | None]:
	"""Return (converted_condition, review_reason). converted_condition is None if left unchanged."""
	if not condition or not condition.strip():
		return condition, None

	text = condition.strip()

	if "{%" in text:
		return None, "contains Jinja control tags"

	if text.count("{{") != text.count("}}"):
		return None, "unbalanced Jinja braces"

	if "{{" in text:
		if text.count("{{") > 1:
			return None, "multiple Jinja expression blocks"
		if "|" in text:
			return None, "contains Jinja filters"
		match = SINGLE_JINJA_BLOCK.match(text)
		if not match:
			return None, "could not unwrap Jinja expression"
		text = match.group(1).strip()

	text = BARE_FLT.sub("frappe.utils.flt(", text)
	text = BARE_CINT.sub("frappe.utils.cint(", text)

	for name in REMOVED_NAMES:
		if re.search(rf"\b{re.escape(name)}\b", text):
			return text, f"uses removed name {name!r}"

	return text, None


def execute():
	for rule in frappe.get_all("Document Approval Rule", fields=["name", "condition", "enabled"]):
		condition = rule.condition
		if not condition:
			continue

		converted, review_reason = convert_condition_text(condition)
		if converted is None:
			frappe.log_error(
				title="Approval condition migration needs review",
				message=f"Document Approval Rule {rule.name}: {review_reason}\n\n{condition}",
			)
			continue

		if review_reason:
			frappe.log_error(
				title="Approval condition migration needs review",
				message=f"Document Approval Rule {rule.name}: {review_reason}\n\nConverted to:\n{converted}",
			)

		if converted == condition:
			continue

		try:
			validate_condition(converted)
		except Exception as e:
			frappe.db.set_value("Document Approval Rule", rule.name, "enabled", 0)
			frappe.log_error(
				title="Approval condition migration disabled rule",
				message=f"Document Approval Rule {rule.name}: {e}\n\n{converted}",
			)
			continue

		frappe.db.set_value("Document Approval Rule", rule.name, "condition", converted)

	for workflow in frappe.get_all("Workflow", fields=["name", "reapproval_condition"]):
		condition = workflow.reapproval_condition
		if not condition:
			continue

		converted, review_reason = convert_condition_text(condition)
		if converted is None:
			frappe.log_error(
				title="Reapproval condition migration needs review",
				message=f"Workflow {workflow.name}: {review_reason}\n\n{condition}",
			)
			continue

		if review_reason:
			frappe.log_error(
				title="Reapproval condition migration needs review",
				message=f"Workflow {workflow.name}: {review_reason}\n\nConverted to:\n{converted}",
			)

		if converted == condition:
			continue

		try:
			ast.parse(converted, mode="eval")
		except SyntaxError as e:
			frappe.log_error(
				title="Reapproval condition migration needs review",
				message=f"Workflow {workflow.name}: invalid expression after conversion: {e.msg}\n\n{converted}",
			)
			continue

		frappe.db.set_value("Workflow", workflow.name, "reapproval_condition", converted)
