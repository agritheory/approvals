# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe


BROKEN_NAME_SUFFIX = "-#####"


def execute():
	for rule in frappe.get_all(
		"Document Approval Rule",
		filters={"name": ("like", f"%{BROKEN_NAME_SUFFIX}")},
		fields=["name", "approval_doctype", "approval_role"],
	):
		new_name = f"{rule.approval_doctype}-{rule.approval_role}-00001"
		if new_name == rule.name:
			continue
		if frappe.db.exists("Document Approval Rule", new_name):
			continue

		frappe.rename_doc("Document Approval Rule", rule.name, new_name, force=True)
