# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe


def execute():
	if not frappe.db.exists(
		"Custom Field", "Workflow Document State-custom_is_approved_state_for_non_submittable_document"
	):
		return

	if frappe.db.exists(
		"Custom Field", "Workflow Document State-is_approved_state_for_non_submittable_document"
	):
		frappe.delete_doc(
			"Custom Field",
			"Workflow Document State-custom_is_approved_state_for_non_submittable_document",
			force=True,
		)
	else:
		frappe.rename_doc(
			"Custom Field",
			"Workflow Document State-custom_is_approved_state_for_non_submittable_document",
			"Workflow Document State-is_approved_state_for_non_submittable_document",
			force=True,
		)

	frappe.clear_cache(doctype="Workflow Document State")
