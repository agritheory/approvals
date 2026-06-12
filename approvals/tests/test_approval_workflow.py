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
	for po_name in frappe.get_all(
		"Purchase Order", {"docstatus": 0, "workflow_state": "Draft"}, pluck="name"
	):
		po = frappe.get_doc("Purchase Order", po_name)
		apply_workflow(po, "Send for Approval")


@pytest.mark.parametrize(
	"supplier,approver,expects_todo,expects_doc_share",
	[
		pytest.param("Exceptional Grid", None, False, False, id="under_200"),
		pytest.param("Sphere Cellular", "mmckay@cfc.co", True, True, id="stock_manager"),
		pytest.param("Liu & Loewen Accountants LLP", "arivers@cfc.co", True, True, id="sales_manager"),
		pytest.param("Cooperative Ag Finance", "mbritt@cfc.co", True, False, id="accounts_manager"),
	],
)
def test_purchase_order_approval_side_effects(supplier, approver, expects_todo, expects_doc_share):
	"""
	Each Chelsea Fruit Co purchase order tier assigns the correct approver after Send for Approval.

	| Supplier                     | PO Total | Approver       | ToDo | DocShare |
	| ---------------------------- | -------: | -------------- | ---- | -------- |
	| Exceptional Grid             |  $150.00 | none           | no   | no       |
	| Sphere Cellular              |  $250.00 | mmckay@cfc.co  | yes  | yes      |
	| Liu & Loewen Accountants LLP |  $750.00 | arivers@cfc.co | yes  | yes      |
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
