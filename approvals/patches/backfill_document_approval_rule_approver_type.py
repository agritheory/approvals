# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe


def execute():
	for name in frappe.get_all("Document Approval Rule", pluck="name"):
		if frappe.db.get_value("Document Approval Rule", name, "approver_type"):
			continue
		frappe.db.set_value(
			"Document Approval Rule", name, "approver_type", "Role", update_modified=False
		)
