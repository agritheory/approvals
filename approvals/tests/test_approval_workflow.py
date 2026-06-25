# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.exceptions import ValidationError

from approvals.approvals.api import get_submittable_approval_action
from approvals.approvals.workflow import apply_workflow


def purchase_order_workflow_config():
	workflow_name = frappe.db.get_value(
		"Workflow", {"document_type": "Purchase Order", "is_active": 1}, "name"
	)
	return frappe.get_cached_doc("Workflow", workflow_name)


def send_purchase_orders_for_approval():
	frappe.set_user("Administrator")
	frappe.set_value(
		"Document Approval Settings",
		"Document Approval Settings",
		"fallback_approver",
		"mbritt@cfc.co",
	)
	workflow = purchase_order_workflow_config()
	state_field = workflow.workflow_state_field
	approval_state = workflow.approval_state

	for po_name in frappe.get_all("Purchase Order", {"docstatus": 0}, pluck="name"):
		po = frappe.get_doc("Purchase Order", po_name)
		if po.get(state_field) == approval_state:
			apply_workflow(po, "Reject")
			po.reload()
		if po.get(state_field) in (None, "", "Draft"):
			apply_workflow(po, "Send for Approval")


@pytest.mark.order(1)
def test_get_submittable_approval_action_from_pending_approval():
	send_purchase_orders_for_approval()

	po_name = frappe.db.get_value(
		"Purchase Order", {"supplier": "Sphere Cellular", "docstatus": 0}, "name"
	)
	assert po_name, "No unsubmitted Purchase Order found for Sphere Cellular"

	po = frappe.get_doc("Purchase Order", po_name)
	assert po.workflow_state == "Pending Approval"
	assert get_submittable_approval_action(po) == "Approve"


@pytest.mark.order(2)
def test_get_submittable_approval_action_from_draft():
	send_purchase_orders_for_approval()

	po_name = frappe.db.get_value(
		"Purchase Order", {"supplier": "Sphere Cellular", "docstatus": 0}, "name"
	)
	assert po_name, "No unsubmitted Purchase Order found for Sphere Cellular"

	po = frappe.get_doc("Purchase Order", po_name)
	frappe.db.set_value("Purchase Order", po.name, "workflow_state", "Draft", update_modified=False)
	po.reload()

	assert get_submittable_approval_action(po) is None


@pytest.mark.order(3)
def test_get_submittable_approval_action_defaults_when_approval_action_empty():
	send_purchase_orders_for_approval()

	po_name = frappe.db.get_value(
		"Purchase Order", {"supplier": "Sphere Cellular", "docstatus": 0}, "name"
	)
	assert po_name, "No unsubmitted Purchase Order found for Sphere Cellular"

	workflow_name = frappe.db.get_value("Workflow", {"document_type": "Purchase Order"}, "name")
	assert workflow_name
	frappe.db.set_value("Workflow", workflow_name, "approval_action", None, update_modified=False)

	po = frappe.get_doc("Purchase Order", po_name)
	assert po.workflow_state == "Pending Approval"
	assert get_submittable_approval_action(po) == "Approve"

	frappe.db.set_value(
		"Workflow", workflow_name, "approval_action", "Approve", update_modified=False
	)


@pytest.mark.order(4)
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


@pytest.mark.order(5)
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


@pytest.mark.order(6)
def test_workflow_approve_blocked_without_approvals():
	send_purchase_orders_for_approval()

	po_name = frappe.db.get_value(
		"Purchase Order", {"supplier": "Premier Equipment Leasing", "docstatus": 0}, "name"
	)
	assert po_name, "No unsubmitted Purchase Order found for Premier Equipment Leasing"

	po = frappe.get_doc("Purchase Order", po_name)
	assert po.workflow_state == "Pending Approval"

	frappe.set_user("Administrator")
	with pytest.raises(ValidationError, match="All approvers must approve"):
		apply_workflow(po, "Approve")

	po.reload()
	assert po.docstatus == 0
	assert po.workflow_state == "Pending Approval"


@pytest.mark.order(7)
def test_workflow_approve_blocked_until_all_required_roles_approve():
	send_purchase_orders_for_approval()

	po_name = frappe.db.get_value(
		"Purchase Order", {"supplier": "North County Grain Cooperative", "docstatus": 0}, "name"
	)
	assert po_name, "No unsubmitted Purchase Order found for North County Grain Cooperative"

	po = frappe.get_doc("Purchase Order", po_name)
	assert po.workflow_state == "Pending Approval"

	extra_rule = frappe.new_doc("Document Approval Rule")
	extra_rule.approval_doctype = "Purchase Order"
	extra_rule.approval_role = "Sales Manager"
	extra_rule.condition = "{{ doc.grand_total > 1000 }}"
	extra_rule.primary_assignee = "mmckay@cfc.co"
	extra_rule.enabled = 1
	extra_rule.insert(ignore_permissions=True)

	frappe.call("approvals.approvals.api.assign_approvers", doc=po)

	frappe.set_user("mbritt@cfc.co")
	frappe.call(
		"approvals.approvals.api.approve_document",
		doc=frappe.as_json(po.as_dict()),
		role="Accounts Manager",
		user="mbritt@cfc.co",
	)
	frappe.set_user("Administrator")

	po.reload()
	assert po.docstatus == 0
	assert po.workflow_state == "Pending Approval"

	with pytest.raises(ValidationError, match="All approvers must approve"):
		apply_workflow(po, "Approve")

	frappe.set_user("mmckay@cfc.co")
	frappe.call(
		"approvals.approvals.api.approve_document",
		doc=frappe.as_json(po.as_dict()),
		role="Sales Manager",
		user="mmckay@cfc.co",
	)
	frappe.set_user("Administrator")

	po.reload()
	assert po.docstatus == 1
	assert po.workflow_state == "Approved"

	extra_rule.delete(ignore_permissions=True)
