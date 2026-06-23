# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.exceptions import ValidationError

from approvals.approvals.workflow import apply_workflow
from approvals.tests.fixtures import customer_credit_limit_workflow
from approvals.tests.setup import sync_workflow_from_fixture


@pytest.mark.order(40)
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
	frappe.set_user("Administrator")
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
			"allocated_to": "mmckay@cfc.co",
			"status": "Open",
		},
	)

	approver = "mmckay@cfc.co"
	frappe.set_user(approver)
	frappe.call(
		"approvals.approvals.api.approve_document",
		doc=frappe.as_json(customer.as_dict()),
		role="Sales Manager",
		user=approver,
	)
	frappe.set_user("Administrator")

	customer.reload()
	assert customer.docstatus == 0
	assert customer.workflow_state == "Approved"
	assert customer.last_approved_credit_limit == 10000
	assert frappe.db.exists(
		"Document Approval",
		{
			"reference_doctype": "Customer",
			"reference_name": customer.name,
			"approver": approver,
			"approval_role": "Sales Manager",
		},
	)

	customer.credit_limits[0].credit_limit = 20000
	customer.save()
	customer.reload()
	assert customer.workflow_state == "Pending Approval"
	assert customer.last_approved_credit_limit == 10000


@pytest.mark.order(41)
def test_customer_workflow_approve_blocked_without_approvals():
	"""Non-submittable workflow Approve must not bypass required sidebar approvals."""
	frappe.set_user("Administrator")
	workflow_name = frappe.db.get_value("Workflow", {"document_type": "Customer"}, "name")
	if workflow_name:
		sync_workflow_from_fixture(workflow_name, customer_credit_limit_workflow)

	customer_name = "Chelsea Fruit Wholesale"
	name = frappe.db.get_value("Customer", {"customer_name": customer_name}, "name")
	assert name

	customer = frappe.get_doc("Customer", name)
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

	with pytest.raises(ValidationError, match="All approvers must approve"):
		apply_workflow(customer, "Approve")

	customer.reload()
	assert customer.workflow_state == "Pending Approval"
