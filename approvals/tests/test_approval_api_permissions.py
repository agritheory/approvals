# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest

from approvals.tests.test_purchase_invoice_non_workflow_approval import (
	create_draft_purchase_invoice_for_supplier,
	ensure_purchase_invoice_assignments,
)
from approvals.tests.test_user_approvals import (
	create_user_approval_rule,
	delete_document_approval_rule,
	delete_test_purchase_invoice,
)

ACCOUNTS_MANAGER_SUPPLIER = "Cooperative Ag Finance"
ACCOUNTS_MANAGER = "mbritt@cfc.co"
SALES_MANAGER = "mmckay@cfc.co"
STOCK_MANAGER = "arivers@cfc.co"


def document_approval_exists(pi, **filters):
	return frappe.db.exists(
		"Document Approval",
		{"reference_doctype": pi.doctype, "reference_name": pi.name, **filters},
	)


@pytest.mark.order(56)
def test_cannot_record_role_approval_as_another_user():
	"""
	Minh McKay (Sales Manager) tries to approve a $5,000 invoice's Accounts Manager row
	by claiming to be Morgan Britt or Administrator.

	| Caller         | Claimed user   | Role             | Outcome          |
	| -------------- | -------------- | ---------------- | ---------------- |
	| mmckay@cfc.co  | mbritt@cfc.co  | Accounts Manager | PermissionError  |
	| mmckay@cfc.co  | Administrator  | Accounts Manager | PermissionError  |
	| mmckay@cfc.co  | (own session)  | Accounts Manager | PermissionError  |
	"""
	pi = create_draft_purchase_invoice_for_supplier(ACCOUNTS_MANAGER_SUPPLIER)
	ensure_purchase_invoice_assignments(pi)

	try:
		frappe.set_user(SALES_MANAGER)
		for claimed_user in (ACCOUNTS_MANAGER, "Administrator"):
			with pytest.raises(frappe.PermissionError):
				frappe.call(
					"approvals.approvals.api.approve_document",
					doc=frappe.as_json(pi.as_dict()),
					role="Accounts Manager",
					user=claimed_user,
				)

		with pytest.raises(frappe.PermissionError):
			frappe.call(
				"approvals.approvals.api.approve_document",
				doc=frappe.as_json(pi.as_dict()),
				role="Accounts Manager",
			)

		frappe.set_user("Administrator")
		assert not document_approval_exists(pi, approval_role="Accounts Manager")
		assert frappe.db.get_value("Purchase Invoice", pi.name, "docstatus") == 0
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(57)
def test_role_holder_can_approve_unassigned_to_them():
	"""Any user holding the rule's role may approve the role row as themselves."""
	pi = create_draft_purchase_invoice_for_supplier(ACCOUNTS_MANAGER_SUPPLIER)
	ensure_purchase_invoice_assignments(pi)

	try:
		frappe.set_user(ACCOUNTS_MANAGER)
		frappe.call(
			"approvals.approvals.api.approve_document",
			doc=frappe.as_json(pi.as_dict()),
			role="Accounts Manager",
		)
		frappe.set_user("Administrator")
		assert document_approval_exists(pi, approval_role="Accounts Manager", approver=ACCOUNTS_MANAGER)
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(58)
def test_cannot_record_user_approval_as_named_approver():
	"""
	Arden Rivers is added as a User Approval on an invoice. Minh McKay tries to satisfy
	Arden's row by claiming to be Arden, or by keying an Administrator approval to Arden's email.
	"""
	pi = create_draft_purchase_invoice_for_supplier(ACCOUNTS_MANAGER_SUPPLIER)
	ensure_purchase_invoice_assignments(pi)

	try:
		frappe.set_user("Administrator")
		frappe.call(
			"approvals.approvals.api.add_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			user=STOCK_MANAGER,
			reason="Confirm receiving",
		)

		frappe.set_user(SALES_MANAGER)
		with pytest.raises(frappe.PermissionError):
			frappe.call(
				"approvals.approvals.api.approve_document",
				doc=frappe.as_json(pi.as_dict()),
				role="User Approval",
				user=STOCK_MANAGER,
			)

		with pytest.raises(frappe.PermissionError):
			frappe.call(
				"approvals.approvals.api.approve_document",
				doc=frappe.as_json(pi.as_dict()),
				role=STOCK_MANAGER,
				user="Administrator",
			)

		with pytest.raises(frappe.PermissionError):
			frappe.call(
				"approvals.approvals.api.approve_document",
				doc=frappe.as_json(pi.as_dict()),
				role="User Approval",
			)

		frappe.set_user("Administrator")
		assert not document_approval_exists(pi, approver=STOCK_MANAGER)
		assert not document_approval_exists(pi, approver=SALES_MANAGER)

		frappe.set_user(STOCK_MANAGER)
		frappe.call(
			"approvals.approvals.api.approve_document",
			doc=frappe.as_json(pi.as_dict()),
			role="User Approval",
		)
		frappe.set_user("Administrator")
		assert document_approval_exists(pi, approver=STOCK_MANAGER, user_approval="User Approval")
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(59)
def test_reject_does_not_save_client_document_fields():
	"""Morgan Britt rejects with a tampered payload; stored invoice fields are unchanged."""
	pi = create_draft_purchase_invoice_for_supplier(ACCOUNTS_MANAGER_SUPPLIER)
	ensure_purchase_invoice_assignments(pi)
	original_bill_no = pi.bill_no
	original_rate = pi.items[0].rate

	try:
		tampered = pi.as_dict()
		tampered["bill_no"] = "TAMPERED-BILL"
		tampered["items"][0]["rate"] = 1

		frappe.set_user(ACCOUNTS_MANAGER)
		frappe.call(
			"approvals.approvals.api.reject_document",
			doc=frappe.as_json(tampered),
			role="Accounts Manager",
			comment="Wrong amount",
		)

		frappe.set_user("Administrator")
		stored = frappe.get_doc("Purchase Invoice", pi.name)
		assert stored.bill_no == original_bill_no
		assert stored.items[0].rate == original_rate
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(60)
def test_non_approver_cannot_reject():
	"""Arden Rivers (Stock Manager) is not an approver on a $5,000 invoice and cannot reject it."""
	pi = create_draft_purchase_invoice_for_supplier(ACCOUNTS_MANAGER_SUPPLIER)
	ensure_purchase_invoice_assignments(pi)

	try:
		frappe.set_user(STOCK_MANAGER)
		with pytest.raises(frappe.PermissionError):
			frappe.call(
				"approvals.approvals.api.reject_document",
				doc=frappe.as_json(pi.as_dict()),
				role="Accounts Manager",
				comment="Not my call",
			)

		frappe.set_user("Administrator")
		assert not frappe.db.exists(
			"Comment",
			{"reference_doctype": pi.doctype, "reference_name": pi.name, "content": "Not my call"},
		)
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(63)
def test_rule_assigned_user_approval_cannot_be_taken_over():
	"""
	A User rule names Minh McKay as approver on Cooperative Ag Finance invoices, reassignable
	within Purchase User. Arden Rivers holds Purchase User but is neither the assignee nor an
	approvals manager, and tries to move her row to himself.
	"""
	rule = create_user_approval_rule(
		approvers=f"['{SALES_MANAGER}'] if doc.supplier == '{ACCOUNTS_MANAGER_SUPPLIER}' else []",
		approval_role="Purchase User",
	)
	pi = create_draft_purchase_invoice_for_supplier(ACCOUNTS_MANAGER_SUPPLIER)

	try:
		frappe.call("approvals.approvals.api.assign_approvers", doc=pi)
		uda_name = frappe.db.get_value(
			"User Document Approval",
			{"reference_name": pi.name, "approver": SALES_MANAGER, "origin": rule.name},
			"name",
		)
		assert uda_name

		frappe.set_user(STOCK_MANAGER)
		with pytest.raises(frappe.PermissionError):
			frappe.call(
				"approvals.approvals.api.reassign_user_approval",
				doc=frappe.as_json(pi.as_dict()),
				uda_name_or_role=uda_name,
				to_user=STOCK_MANAGER,
			)

		frappe.set_user("Administrator")
		assert frappe.db.get_value("User Document Approval", uda_name, "approver") == SALES_MANAGER
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)
		delete_document_approval_rule(rule.name)


def rule_user_approval(pi, rule_name: str):
	return frappe.db.get_value(
		"User Document Approval",
		{"reference_name": pi.name, "origin": rule_name},
		["name", "approver", "original_approver"],
		as_dict=True,
	)


def user_approval_row_for(pi, user: str):
	frappe.set_user(user)
	response = frappe.call(
		"approvals.approvals.api.fetch_approvals_and_roles",
		doc=frappe.as_json(pi.as_dict()),
	)
	frappe.set_user("Administrator")
	return next(row for row in response["approvals"] if row["approval_role"] == "User Approval")


@pytest.mark.order(65)
def test_rule_assigned_user_approval_reassigns_within_rule_role():
	"""
	A User rule names Minh McKay on Cooperative Ag Finance invoices, reassignable within
	Purchase User. Minh hands the invoice to Morgan Britt, and a later save re-runs the rule.

	| Caller         | Reassign to     | Outcome                                  |
	| -------------- | --------------- | ---------------------------------------- |
	| mmckay@cfc.co  | mreeves@cfc.co  | ValidationError (not a Purchase User)    |
	| mmckay@cfc.co  | mbritt@cfc.co   | reassigned, survives the next rule sync  |
	| mbritt@cfc.co  | arivers@cfc.co  | ValidationError (already has a row)      |
	"""
	rule = create_user_approval_rule(
		approvers=f"['{SALES_MANAGER}'] if doc.supplier == '{ACCOUNTS_MANAGER_SUPPLIER}' else []",
		approval_role="Purchase User",
	)
	pi = create_draft_purchase_invoice_for_supplier(ACCOUNTS_MANAGER_SUPPLIER)

	try:
		frappe.call("approvals.approvals.api.assign_approvers", doc=pi)
		uda = rule_user_approval(pi, rule.name)
		assert uda.approver == SALES_MANAGER
		assert uda.original_approver == SALES_MANAGER

		row = user_approval_row_for(pi, SALES_MANAGER)
		assert row["can_reassign"] is True
		assert row["reassign_role"] == "Purchase User"

		frappe.set_user(SALES_MANAGER)
		with pytest.raises(frappe.ValidationError, match="Purchase User"):
			frappe.call(
				"approvals.approvals.api.reassign_user_approval",
				doc=frappe.as_json(pi.as_dict()),
				uda_name_or_role=uda.name,
				to_user="mreeves@cfc.co",
			)

		frappe.call(
			"approvals.approvals.api.reassign_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			uda_name_or_role=uda.name,
			to_user=ACCOUNTS_MANAGER,
			reason="Morgan owns this vendor",
		)
		frappe.set_user("Administrator")

		uda = rule_user_approval(pi, rule.name)
		assert uda.approver == ACCOUNTS_MANAGER
		assert uda.original_approver == SALES_MANAGER

		frappe.call("approvals.approvals.api.assign_approvers", doc=pi)
		rule_rows = frappe.get_all(
			"User Document Approval",
			filters={"reference_name": pi.name, "origin": rule.name},
			pluck="approver",
		)
		assert rule_rows == [ACCOUNTS_MANAGER]

		frappe.call(
			"approvals.approvals.api.add_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			user=STOCK_MANAGER,
			reason="Confirm receiving",
		)
		frappe.set_user(ACCOUNTS_MANAGER)
		with pytest.raises(frappe.ValidationError, match="already assigned"):
			frappe.call(
				"approvals.approvals.api.reassign_user_approval",
				doc=frappe.as_json(pi.as_dict()),
				uda_name_or_role=uda.name,
				to_user=STOCK_MANAGER,
			)

		frappe.set_user("Administrator")
		assert rule_user_approval(pi, rule.name).approver == ACCOUNTS_MANAGER
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)
		delete_document_approval_rule(rule.name)


@pytest.mark.order(66)
def test_rule_assigned_user_approval_reassign_requires_rule_role():
	"""
	Minh McKay is the named approver but cannot hand the row off when she lacks the rule's
	role, or when the rule has no role at all. Without a role, not even an approvals manager can.

	| Rule's Approval Role | Caller         | can_reassign | Reassign outcome |
	| -------------------- | -------------- | ------------ | ---------------- |
	| Accounts Manager     | mmckay@cfc.co  | False        | PermissionError  |
	| (none)               | mmckay@cfc.co  | False        | PermissionError  |
	| (none)               | Administrator  | False        | PermissionError  |
	"""
	rule = create_user_approval_rule(
		approvers=f"['{SALES_MANAGER}'] if doc.supplier == '{ACCOUNTS_MANAGER_SUPPLIER}' else []",
		approval_role="Accounts Manager",
	)
	pi = create_draft_purchase_invoice_for_supplier(ACCOUNTS_MANAGER_SUPPLIER)

	try:
		frappe.call("approvals.approvals.api.assign_approvers", doc=pi)
		uda = rule_user_approval(pi, rule.name)

		assert user_approval_row_for(pi, SALES_MANAGER)["can_reassign"] is False
		frappe.set_user(SALES_MANAGER)
		with pytest.raises(frappe.PermissionError):
			frappe.call(
				"approvals.approvals.api.reassign_user_approval",
				doc=frappe.as_json(pi.as_dict()),
				uda_name_or_role=uda.name,
				to_user=ACCOUNTS_MANAGER,
			)
		frappe.set_user("Administrator")

		frappe.db.set_value("Document Approval Rule", rule.name, "approval_role", None)

		for caller in (SALES_MANAGER, "Administrator"):
			assert user_approval_row_for(pi, caller)["can_reassign"] is False
			frappe.set_user(caller)
			with pytest.raises(frappe.PermissionError):
				frappe.call(
					"approvals.approvals.api.reassign_user_approval",
					doc=frappe.as_json(pi.as_dict()),
					uda_name_or_role=uda.name,
					to_user=ACCOUNTS_MANAGER,
				)
			frappe.set_user("Administrator")

		assert rule_user_approval(pi, rule.name).approver == SALES_MANAGER
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)
		delete_document_approval_rule(rule.name)
