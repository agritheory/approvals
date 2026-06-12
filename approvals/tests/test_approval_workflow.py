# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.model.workflow import apply_workflow


def send_purchase_orders_for_approval():
	frappe.set_user("Administrator")
	frappe.set_value(
		"Document Approval Settings",
		"Document Approval Settings",
		"fallback_approver",
		"mbritt@cfc.co",
	)
	for po_name in frappe.get_all("Purchase Order", {"docstatus": 0}, pluck="name"):
		po = frappe.get_doc("Purchase Order", po_name)
		if po.workflow_state == "Pending Approval":
			apply_workflow(po, "Reject")
		if po.workflow_state == "Draft":
			apply_workflow(po, "Send for Approval")


@pytest.mark.parametrize(
	"supplier,approver,expects_todo,expects_doc_share",
	[
		pytest.param("Exceptional Grid", None, False, False, id="under_200"),
		pytest.param("Sphere Cellular", "arivers@cfc.co", True, True, id="stock_manager"),
		pytest.param("Liu & Loewen Accountants LLP", "mmckay@cfc.co", True, True, id="sales_manager"),
		pytest.param("Cooperative Ag Finance", "mbritt@cfc.co", True, False, id="accounts_manager"),
	],
)
def test_purchase_order_approval_side_effects(supplier, approver, expects_todo, expects_doc_share):
	"""
	Each Chelsea Fruit Co purchase order tier assigns the correct approver after Send for Approval.

	| Supplier                     | PO Total | Approver       | ToDo | DocShare |
	| ---------------------------- | -------: | -------------- | ---- | -------- |
	| Exceptional Grid             |  $150.00 | none           | no   | no       |
	| Sphere Cellular              |  $250.00 | arivers@cfc.co | yes  | yes      |
	| Liu & Loewen Accountants LLP |  $750.00 | mmckay@cfc.co  | yes  | yes      |
	| Cooperative Ag Finance       | $5000.00 | mbritt@cfc.co  | yes  | no       |
	"""
	send_purchase_orders_for_approval()

	po_name = frappe.db.get_value("Purchase Order", {"supplier": supplier, "docstatus": 0}, "name")
	assert po_name, f"No unsubmitted Purchase Order found for supplier {supplier}"

	po = frappe.get_doc("Purchase Order", po_name)
	assert po.workflow_state == "Pending Approval"

	if expects_todo:
		assert approver
		assert frappe.db.exists("ToDo", {"allocated_to": approver, "reference_name": po.name})
	else:
		assert not frappe.db.exists("ToDo", {"reference_name": po.name})

	if expects_doc_share:
		assert approver
		assert frappe.db.exists("DocShare", {"user": approver, "share_name": po.name})
	elif approver:
		assert not frappe.db.exists("DocShare", {"user": approver, "share_name": po.name})


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
def test_purchase_order_approval_via_api(supplier, approver, approval_role):
	"""
	Assigned approver clicks Approve in the sidebar; the PO submits and transitions to Approved.

	| Supplier                     | PO Total | Approver       | Role             |
	| ---------------------------- | -------: | -------------- | ---------------- |
	| Sphere Cellular              |  $250.00 | arivers@cfc.co | Stock Manager    |
	| Liu & Loewen Accountants LLP |  $750.00 | mmckay@cfc.co  | Sales Manager    |
	| Cooperative Ag Finance       | $5000.00 | mbritt@cfc.co  | Accounts Manager |
	"""
	send_purchase_orders_for_approval()

	po_name = frappe.db.get_value("Purchase Order", {"supplier": supplier, "docstatus": 0}, "name")
	assert po_name, f"No unsubmitted Purchase Order found for supplier {supplier}"

	po = frappe.get_doc("Purchase Order", po_name)
	assert po.workflow_state == "Pending Approval"

	frappe.set_user(approver)
	frappe.call(
		"approvals.approvals.api.approve_document",
		doc=frappe.as_json(frappe.get_doc("Purchase Order", po.name).as_dict()),
		role=approval_role,
		user=approver,
	)
	frappe.set_user("Administrator")

	po.reload()
	assert po.docstatus == 1
	assert po.workflow_state == "Approved"
	assert frappe.db.exists(
		"Document Approval",
		{
			"reference_doctype": "Purchase Order",
			"reference_name": po.name,
			"approver": approver,
			"approval_role": approval_role,
		},
	)
