# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe

from approvals.approvals.api import approve_document
from approvals.tests.fixtures import customer_credit_limit_workflow
from approvals.tests.setup import create_customer_custom_fields, sync_workflow_from_fixture


def test_customer_credit_limit_approval_workflow():
	"""
	Changing a Customer credit limit sends the document for approval and locks it
	until a Sales Manager approves, without submitting the Customer.

	| Step                    | Credit Limit | Last Approved | Workflow State   |
	| ----------------------- | -----------: | ------------: | ---------------- |
	| Initial limit set       |    $10,000   |             — | Pending Approval |
	| Sales Manager approves  |    $10,000   |       $10,000 | Approved         |
	| Credit limit raised     |    $20,000   |       $10,000 | Pending Approval |
	"""
	create_customer_custom_fields()
	workflow_name = frappe.db.get_value("Workflow", {"document_type": "Customer"}, "name")
	if workflow_name:
		sync_workflow_from_fixture(workflow_name, customer_credit_limit_workflow)

	customer_name = "Chelsea Fruit Wholesale"
	name = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
	assert name, f"No Customer found for {customer_name}"
	customer = frappe.get_doc("Customer", name)

	# Idempotent reruns: reset to a known credit limit and clear the approved baseline.
	customer.credit_limits[0].credit_limit = 10000
	frappe.db.set_value(
		"Customer",
		customer.name,
		{"workflow_state": "Draft", "last_approved_credit_limit": 0},
		update_modified=False,
	)
	customer.reload()
	customer.credit_limits[0].credit_limit = 10000
	customer.save()
	customer.reload()

	assert customer.workflow_state == "Pending Approval"
	assert frappe.db.exists(
		"ToDo",
		{
			"reference_type": "Customer",
			"reference_name": customer.name,
			"allocated_to": "arivers@cfc.co",
			"status": "Open",
		},
	)

	frappe.set_user("mmckay@cfc.co")
	approve_document(doc=customer, role="Sales Manager", user="mmckay@cfc.co")
	frappe.set_user("Administrator")

	customer.reload()
	assert customer.docstatus == 0
	assert customer.workflow_state == "Approved"
	assert customer.last_approved_credit_limit == 10000

	customer.credit_limits[0].credit_limit = 20000
	customer.save()
	customer.reload()
	assert customer.workflow_state == "Pending Approval"
	assert customer.last_approved_credit_limit == 10000
