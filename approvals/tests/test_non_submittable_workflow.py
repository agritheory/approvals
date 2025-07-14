# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest


def test_customer_credit_limit_workflow():
	# Create a new customer with a credit limit
	customer = frappe.get_doc(
		{
			"doctype": "Customer",
			"customer_name": "Test Customer NonSubmittable",
			"credit_limits": [{"credit_limit": 10000, "company": "Chelsea Fruit Co"}],
		}
	)
	customer.insert()

	# Send for approval (simulate workflow action)
	customer.workflow_state = "Pending Approval"
	customer.save()

	# Simulate approval by Sales Manager
	customer.workflow_state = "Approved"
	customer.save()

	# Change the credit limit
	customer.credit_limits[0].credit_limit = 20000
	customer.save()

	# After saving, workflow should revert to Draft
	customer.reload()
	assert customer.workflow_state == "Draft"

	# Send for approval again
	customer.workflow_state = "Pending Approval"
	customer.save()

	# Approve again
	customer.workflow_state = "Approved"
	customer.save()

	# Final state should be Approved
	customer.reload()
	assert customer.workflow_state == "Approved"
