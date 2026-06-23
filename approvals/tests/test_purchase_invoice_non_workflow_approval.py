# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.model.workflow import get_workflow_name


def purchase_invoice_for_supplier(supplier):
	name = frappe.db.get_value("Purchase Invoice", {"supplier": supplier, "docstatus": 0}, "name")
	assert name, f"No draft Purchase Invoice found for {supplier}"
	return frappe.get_doc("Purchase Invoice", name)


def ensure_purchase_invoice_assignments(pi):
	if not frappe.db.exists(
		"ToDo",
		{"reference_type": "Purchase Invoice", "reference_name": pi.name, "status": "Open"},
	):
		frappe.call("approvals.approvals.api.assign_approvers", doc=pi)


@pytest.mark.order(11)
@pytest.mark.parametrize(
	"supplier,approver,expects_todo,expects_doc_share",
	[
		pytest.param("Exceptional Grid", None, False, False, id="under_200"),
		pytest.param("Sphere Cellular", "arivers@cfc.co", True, True, id="stock_manager"),
		pytest.param("Liu & Loewen Accountants LLP", "mmckay@cfc.co", True, True, id="sales_manager"),
		pytest.param("Cooperative Ag Finance", "mbritt@cfc.co", True, False, id="accounts_manager"),
	],
)
def test_purchase_invoice_approval_side_effects(
	supplier, approver, expects_todo, expects_doc_share
):
	"""
	Draft vendor invoices assign the correct approver without a Frappe Workflow.

	| Supplier                     | PI Total | Approver       | ToDo | DocShare |
	| ---------------------------- | -------: | -------------- | ---- | -------- |
	| Exceptional Grid             |  $150.00 | none           | no   | no       |
	| Sphere Cellular              |  $250.00 | arivers@cfc.co | yes  | yes      |
	| Liu & Loewen Accountants LLP |  $750.00 | mmckay@cfc.co  | yes  | yes      |
	| Cooperative Ag Finance       | $5000.00 | mbritt@cfc.co  | yes  | no       |
	"""
	pi = purchase_invoice_for_supplier(supplier)
	ensure_purchase_invoice_assignments(pi)
	assert not get_workflow_name(pi.doctype)

	if expects_todo:
		assert approver
		assert frappe.db.exists("ToDo", {"allocated_to": approver, "reference_name": pi.name})
	else:
		assert not frappe.db.exists("ToDo", {"reference_name": pi.name})

	if expects_doc_share:
		assert approver
		assert frappe.db.exists("DocShare", {"user": approver, "share_name": pi.name})
	elif approver:
		assert not frappe.db.exists("DocShare", {"user": approver, "share_name": pi.name})


@pytest.mark.order(12)
def test_cooperative_ag_finance_invoice_has_no_workflow():
	pi = purchase_invoice_for_supplier("Cooperative Ag Finance")
	response = frappe.call(
		"approvals.approvals.api.fetch_approvals_and_roles",
		doc=frappe.as_json(pi.as_dict()),
	)
	assert response["workflow_exists"] is False
	assert response["show_approvals"] is True


@pytest.mark.order(31)
@pytest.mark.parametrize(
	"supplier,approver,approval_role",
	[
		pytest.param("Sphere Cellular", "arivers@cfc.co", "Stock Manager", id="stock_manager"),
		pytest.param(
			"Liu & Loewen Accountants LLP", "mmckay@cfc.co", "Sales Manager", id="sales_manager"
		),
		pytest.param(
			"Cooperative Ag Finance", "mbritt@cfc.co", "Accounts Manager", id="accounts_manager"
		),
	],
)
def test_purchase_invoice_approval_via_api_submits_document(supplier, approver, approval_role):
	"""
	Assigned approver approves a draft invoice; the invoice submits with no workflow.

	| Supplier                     | PI Total | Approver       | Role             |
	| ---------------------------- | -------: | -------------- | ---------------- |
	| Sphere Cellular              |  $250.00 | arivers@cfc.co | Stock Manager    |
	| Liu & Loewen Accountants LLP |  $750.00 | mmckay@cfc.co  | Sales Manager    |
	| Cooperative Ag Finance       | $5000.00 | mbritt@cfc.co  | Accounts Manager |
	"""
	pi = purchase_invoice_for_supplier(supplier)
	ensure_purchase_invoice_assignments(pi)

	frappe.set_user(approver)
	frappe.call(
		"approvals.approvals.api.approve_document",
		doc=frappe.as_json(pi.as_dict()),
		role=approval_role,
		user=approver,
	)
	frappe.set_user("Administrator")

	pi.reload()
	assert pi.docstatus == 1
	assert frappe.db.exists(
		"Document Approval",
		{
			"reference_doctype": "Purchase Invoice",
			"reference_name": pi.name,
			"approver": approver,
			"approval_role": approval_role,
		},
	)


@pytest.mark.order(32)
def test_partial_purchase_invoice_approval_leaves_invoice_in_draft():
	"""Partial sidebar approvals must not submit a multi-role invoice."""
	pi = purchase_invoice_for_supplier("North County Grain Cooperative")
	ensure_purchase_invoice_assignments(pi)

	extra_rule = frappe.new_doc("Document Approval Rule")
	extra_rule.approval_doctype = "Purchase Invoice"
	extra_rule.approval_role = "Sales Manager"
	extra_rule.condition = "{{ doc.grand_total > 1000 }}"
	extra_rule.primary_assignee = "mmckay@cfc.co"
	extra_rule.enabled = 1
	extra_rule.insert(ignore_permissions=True)

	frappe.call("approvals.approvals.api.assign_approvers", doc=pi)

	frappe.set_user("mbritt@cfc.co")
	frappe.call(
		"approvals.approvals.api.approve_document",
		doc=frappe.as_json(pi.as_dict()),
		role="Accounts Manager",
		user="mbritt@cfc.co",
	)
	frappe.set_user("Administrator")

	pi.reload()
	assert pi.docstatus == 0

	frappe.set_user("mmckay@cfc.co")
	frappe.call(
		"approvals.approvals.api.approve_document",
		doc=frappe.as_json(pi.as_dict()),
		role="Sales Manager",
		user="mmckay@cfc.co",
	)
	frappe.set_user("Administrator")

	pi.reload()
	assert pi.docstatus == 1

	extra_rule.delete(ignore_permissions=True)
