# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest

from approvals.approvals.api import revoke_approvals_on_reject
from approvals.approvals.user_approvals import MANUAL_ORIGIN, can_manage_user_approval
from approvals.approvals.doctype.document_approval_rule.document_approval_rule import get_users
from approvals.tests.test_purchase_invoice_non_workflow_approval import (
	create_draft_purchase_invoice_for_supplier,
	ensure_purchase_invoice_assignments,
)


ROLE_ACCOUNTS_MANAGER = "Accounts Manager"


def fetch_approvals_for_pi(pi):
	return frappe.call(
		"approvals.approvals.api.fetch_approvals_and_roles",
		doc=frappe.as_json(pi.as_dict()),
	)


def approval_row(response, role_label: str):
	return next(row for row in response["approvals"] if row["approval_role"] == role_label)


def user_approval_rows(response):
	return [row for row in response["approvals"] if row["approval_role"] == "User Approval"]


def other_user_with_role(role: str, exclude: str) -> str:
	for email in get_users(role):
		if email != exclude:
			return email
	raise AssertionError(f"No other enabled user found for role {role}")


def accounts_manager_peer(exclude: str) -> str:
	peers = [email for email in get_users(ROLE_ACCOUNTS_MANAGER) if email != exclude]
	if peers:
		return peers[0]
	peer = "arivers@cfc.co"
	user = frappe.get_doc("User", peer)
	role_names = {row.role for row in user.roles}
	if ROLE_ACCOUNTS_MANAGER not in role_names:
		user.append("roles", {"role": ROLE_ACCOUNTS_MANAGER})
		user.save(ignore_permissions=True)
		frappe.db.commit()
	return peer


def passthrough_get_hooks(monkeypatch, overrides: dict):
	original_get_hooks = frappe.get_hooks

	def mock_get_hooks(hook_name=None, default=None, app_name=None):
		if hook_name in overrides:
			return overrides[hook_name]
		result = original_get_hooks(hook_name, default=default, app_name=app_name)
		if result is None:
			return default if default is not None else []
		return result

	monkeypatch.setattr(frappe, "get_hooks", mock_get_hooks)


def open_rule_todo_for_role(pi, role: str):
	return frappe.db.get_value(
		"ToDo",
		{
			"reference_type": pi.doctype,
			"reference_name": pi.name,
			"role": role,
			"status": "Open",
			"document_approval_rule": ["is", "set"],
		},
		["name", "allocated_to"],
		as_dict=True,
	)


def open_todo_allocated_for_role(pi, role: str):
	return frappe.db.get_value(
		"ToDo",
		{
			"reference_type": pi.doctype,
			"reference_name": pi.name,
			"role": role,
			"status": "Open",
		},
		["name", "allocated_to"],
		as_dict=True,
	)


def satisfies_role_uda_name(pi, role: str):
	return frappe.db.get_value(
		"User Document Approval",
		{
			"reference_doctype": pi.doctype,
			"reference_name": pi.name,
			"satisfies_role": role,
		},
		"name",
	)


def assert_no_satisfies_role_uda(pi, role: str):
	assert not satisfies_role_uda_name(pi, role)


def assert_open_rule_role_todo(pi, role: str, allocated_to: str):
	todo = open_rule_todo_for_role(pi, role)
	assert todo, f"Expected open Document Approval Rule ToDo for {role}"
	assert todo.allocated_to == allocated_to
	return todo


def cleanup_user_approvals_for_pi(pi_name: str):
	for row in frappe.get_all(
		"User Document Approval",
		filters={"reference_doctype": "Purchase Invoice", "reference_name": pi_name},
		fields=["name", "todo"],
	):
		if row.todo and frappe.db.exists("ToDo", row.todo):
			frappe.db.set_value("User Document Approval", row.name, "todo", None)
		frappe.delete_doc("User Document Approval", row.name, ignore_permissions=True)
	for todo in frappe.get_all(
		"ToDo",
		filters={"reference_type": "Purchase Invoice", "reference_name": pi_name},
		pluck="name",
	):
		frappe.delete_doc("ToDo", todo, ignore_permissions=True)
	for approval in frappe.get_all(
		"Document Approval",
		filters={"reference_doctype": "Purchase Invoice", "reference_name": pi_name},
		pluck="name",
	):
		frappe.delete_doc("Document Approval", approval, ignore_permissions=True)


def delete_test_purchase_invoice(pi_name: str):
	if not frappe.db.exists("Purchase Invoice", pi_name):
		return
	frappe.set_user("Administrator")
	cleanup_user_approvals_for_pi(pi_name)
	pi = frappe.get_doc("Purchase Invoice", pi_name)
	if pi.docstatus == 1:
		pi.flags.ignore_permissions = True
		pi.cancel()
		frappe.db.commit()
	frappe.delete_doc("Purchase Invoice", pi_name, ignore_permissions=True, force=True)


@pytest.mark.order(37)
def test_add_user_approval_records_requested_by_and_origin():
	requester = "arivers@cfc.co"
	added_user = "mmckay@cfc.co"
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	ensure_purchase_invoice_assignments(pi)

	try:
		frappe.set_user(requester)
		frappe.call(
			"approvals.approvals.api.add_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			user=added_user,
			reason="Extra review",
		)
		uda = frappe.get_doc(
			"User Document Approval",
			{
				"reference_doctype": pi.doctype,
				"reference_name": pi.name,
				"approver": added_user,
			},
		)
		assert uda.requested_by == requester
		assert uda.origin == MANUAL_ORIGIN
		assert uda.reason == "Extra review"
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(38)
def test_remove_user_approval_permissions():
	requester = "arivers@cfc.co"
	owner_like = "mbritt@cfc.co"
	added_user = "mmckay@cfc.co"
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	ensure_purchase_invoice_assignments(pi)

	try:
		frappe.set_user(requester)
		frappe.call(
			"approvals.approvals.api.add_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			user=added_user,
		)
		uda_name = frappe.db.get_value(
			"User Document Approval",
			{
				"reference_doctype": pi.doctype,
				"reference_name": pi.name,
				"approver": added_user,
			},
			"name",
		)

		frappe.set_user(owner_like)
		with pytest.raises(frappe.PermissionError):
			frappe.call(
				"approvals.approvals.api.remove_user_approval",
				doc=frappe.as_json(pi.as_dict()),
				uda_name=uda_name,
			)

		frappe.set_user(requester)
		frappe.call(
			"approvals.approvals.api.remove_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			uda_name=uda_name,
		)
		assert not frappe.db.exists("User Document Approval", uda_name)
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


def deny_remove(action, doc, user, uda=None):
	if action == "remove":
		return False
	return None


@pytest.mark.order(39)
def test_permission_hook_overrides_default(monkeypatch):
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	passthrough_get_hooks(
		monkeypatch,
		{"approvals_user_approval_permission": ["approvals.tests.test_user_approvals.deny_remove"]},
	)

	uda = frappe._dict(
		requested_by="arivers@cfc.co",
		origin=MANUAL_ORIGIN,
	)
	assert not can_manage_user_approval("remove", pi, "arivers@cfc.co", uda=uda)

	try:
		pass
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(40)
def test_rule_reassign_does_not_add_user_approval_row():
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	ensure_purchase_invoice_assignments(pi)
	delegate = "mbritt@cfc.co"

	try:
		frappe.set_user("Administrator")
		with pytest.raises(frappe.ValidationError):
			frappe.call(
				"approvals.approvals.api.reassign_user_approval",
				doc=frappe.as_json(pi.as_dict()),
				uda_name_or_role="Accounts Manager",
				to_user="mmckay@cfc.co",
				reason="Should fail",
			)
		frappe.call(
			"approvals.approvals.api.reassign_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			uda_name_or_role="Accounts Manager",
			to_user=delegate,
			reason="Covering",
		)
		assert_no_satisfies_role_uda(pi, ROLE_ACCOUNTS_MANAGER)
		assert_open_rule_role_todo(pi, ROLE_ACCOUNTS_MANAGER, delegate)
		response = frappe.call(
			"approvals.approvals.api.fetch_approvals_and_roles",
			doc=frappe.as_json(pi.as_dict()),
		)
		user_rows = [row for row in response["approvals"] if row["approval_role"] == "User Approval"]
		assert len(user_rows) == 0

		frappe.set_user(delegate)
		delegate_response = frappe.call(
			"approvals.approvals.api.fetch_approvals_and_roles",
			doc=frappe.as_json(pi.as_dict()),
		)
		accounts_row = next(
			row for row in delegate_response["approvals"] if row["approval_role"] == "Accounts Manager"
		)
		assert accounts_row["can_approve"] is True

		frappe.call(
			"approvals.approvals.api.approve_document",
			doc=frappe.as_json(pi.as_dict()),
			role="Accounts Manager",
			user=delegate,
		)
		assert frappe.db.exists(
			"Document Approval",
			{"reference_name": pi.name, "approver": delegate, "approval_role": "Accounts Manager"},
		)
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


def provider_for_purchase_invoice_hook(doc):
	return [{"user": "mmckay@cfc.co", "reason": "Configured approver"}]


@pytest.mark.order(41)
def test_approver_provider_sync(monkeypatch):
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	passthrough_get_hooks(
		monkeypatch,
		{
			"approvals_approver_providers": {
				"Purchase Invoice": ["approvals.tests.test_user_approvals.provider_for_purchase_invoice_hook"]
			}
		},
	)

	try:
		frappe.call("approvals.approvals.api.assign_approvers", doc=pi)
		assert frappe.db.exists(
			"User Document Approval",
			{
				"reference_name": pi.name,
				"approver": "mmckay@cfc.co",
				"origin": "approvals.tests.test_user_approvals.provider_for_purchase_invoice_hook",
			},
		)
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(42)
def test_reject_keeps_user_document_approvals():
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	added_user = "mmckay@cfc.co"

	try:
		frappe.call(
			"approvals.approvals.api.add_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			user=added_user,
		)
		uda_name = frappe.db.get_value(
			"User Document Approval",
			{"reference_name": pi.name, "approver": added_user},
			"name",
		)
		revoke_approvals_on_reject(pi)
		assert frappe.db.exists("User Document Approval", uda_name)
		assert frappe.db.exists(
			"ToDo",
			{
				"reference_name": pi.name,
				"allocated_to": added_user,
				"status": "Open",
			},
		)
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(43)
def test_rule_row_before_reassignment():
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	ensure_purchase_invoice_assignments(pi)
	initial_assignee = "mbritt@cfc.co"

	try:
		for user in (initial_assignee, "Administrator"):
			frappe.set_user(user)
			response = fetch_approvals_for_pi(pi)
			row = approval_row(response, ROLE_ACCOUNTS_MANAGER)
			assert row["can_remove"] is False
			assert row["can_reassign"] is True
		assert len(user_approval_rows(response)) == 0

		rule_todo = open_rule_todo_for_role(pi, ROLE_ACCOUNTS_MANAGER)
		assert rule_todo
		assert rule_todo.allocated_to == initial_assignee
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(44)
def test_reassign_rule_role_to_user_with_role():
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	ensure_purchase_invoice_assignments(pi)
	initial_assignee = "mbritt@cfc.co"
	new_assignee = accounts_manager_peer(initial_assignee)
	bystander = "mmckay@cfc.co"

	try:
		frappe.set_user(initial_assignee)
		frappe.call(
			"approvals.approvals.api.reassign_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			uda_name_or_role=ROLE_ACCOUNTS_MANAGER,
			to_user=new_assignee,
			reason="Covering",
		)

		assert_no_satisfies_role_uda(pi, ROLE_ACCOUNTS_MANAGER)
		assert_open_rule_role_todo(pi, ROLE_ACCOUNTS_MANAGER, new_assignee)
		assert not frappe.db.exists(
			"ToDo",
			{
				"reference_name": pi.name,
				"role": ROLE_ACCOUNTS_MANAGER,
				"allocated_to": initial_assignee,
				"status": "Open",
			},
		)

		frappe.get_doc(
			{
				"doctype": "ToDo",
				"allocated_to": initial_assignee,
				"reference_type": pi.doctype,
				"reference_name": pi.name,
				"role": ROLE_ACCOUNTS_MANAGER,
				"status": "Closed",
				"description": "Stale assignment after reassign",
			}
		).insert(ignore_permissions=True)
		frappe.set_user("Administrator")
		delegate_row = approval_row(fetch_approvals_for_pi(pi), ROLE_ACCOUNTS_MANAGER)
		assert delegate_row["assigned_username"] == new_assignee

		for user in (new_assignee, initial_assignee, "Administrator"):
			frappe.set_user(user)
			response = fetch_approvals_for_pi(pi)
			assert len(user_approval_rows(response)) == 0
			row = approval_row(response, ROLE_ACCOUNTS_MANAGER)
			assert row["can_remove"] is False

		frappe.set_user(new_assignee)
		delegate_row = approval_row(fetch_approvals_for_pi(pi), ROLE_ACCOUNTS_MANAGER)
		assert delegate_row["can_approve"] is True
		assert delegate_row["can_reassign"] is True

		frappe.set_user(initial_assignee)
		previous_row = approval_row(fetch_approvals_for_pi(pi), ROLE_ACCOUNTS_MANAGER)
		assert previous_row["can_approve"] is False
		assert previous_row["can_reassign"] is False

		frappe.set_user(bystander)
		with pytest.raises(frappe.PermissionError):
			frappe.call(
				"approvals.approvals.api.reassign_user_approval",
				doc=frappe.as_json(pi.as_dict()),
				uda_name_or_role=ROLE_ACCOUNTS_MANAGER,
				to_user=initial_assignee,
			)
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(45)
def test_reassign_rule_role_second_time():
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	ensure_purchase_invoice_assignments(pi)
	initial_assignee = "mbritt@cfc.co"
	intermediate = accounts_manager_peer(initial_assignee)

	try:
		frappe.set_user("Administrator")
		frappe.call(
			"approvals.approvals.api.reassign_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			uda_name_or_role=ROLE_ACCOUNTS_MANAGER,
			to_user=intermediate,
		)
		frappe.call(
			"approvals.approvals.api.reassign_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			uda_name_or_role=ROLE_ACCOUNTS_MANAGER,
			to_user=initial_assignee,
		)

		response = fetch_approvals_for_pi(pi)
		assert len(user_approval_rows(response)) == 0
		assert (
			len([r for r in response["approvals"] if r["approval_role"] == ROLE_ACCOUNTS_MANAGER]) == 1
		)

		row = approval_row(response, ROLE_ACCOUNTS_MANAGER)
		assert row["can_remove"] is False

		assert_no_satisfies_role_uda(pi, ROLE_ACCOUNTS_MANAGER)
		assert_open_rule_role_todo(pi, ROLE_ACCOUNTS_MANAGER, initial_assignee)
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(46)
def test_remove_rejected_on_rule_backed_rows():
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	ensure_purchase_invoice_assignments(pi)

	try:
		frappe.set_user("mbritt@cfc.co")
		frappe.call(
			"approvals.approvals.api.reassign_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			uda_name_or_role=ROLE_ACCOUNTS_MANAGER,
			to_user="mbritt@cfc.co",
			reason="Self-assign via rule reassign",
		)
		assert_no_satisfies_role_uda(pi, ROLE_ACCOUNTS_MANAGER)
		assert_open_rule_role_todo(pi, ROLE_ACCOUNTS_MANAGER, "mbritt@cfc.co")

		with pytest.raises(frappe.ValidationError):
			frappe.call(
				"approvals.approvals.api.remove_user_approval",
				doc=frappe.as_json(pi.as_dict()),
				uda_name=ROLE_ACCOUNTS_MANAGER,
			)

		assert open_todo_allocated_for_role(pi, ROLE_ACCOUNTS_MANAGER)
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(47)
def test_manual_user_approval_add_remove_clears_todo():
	requester = "arivers@cfc.co"
	added_user = "mmckay@cfc.co"
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	ensure_purchase_invoice_assignments(pi)

	try:
		frappe.set_user(requester)
		frappe.call(
			"approvals.approvals.api.add_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			user=added_user,
			reason="Extra review",
		)
		uda_name = frappe.db.get_value(
			"User Document Approval",
			{"reference_name": pi.name, "approver": added_user},
			"name",
		)
		todo_name = frappe.db.get_value("User Document Approval", uda_name, "todo")
		assert todo_name

		response = fetch_approvals_for_pi(pi)
		user_row = approval_row(response, "User Approval")
		assert user_row["can_remove"] is True
		assert user_row["can_reassign"] is False
		assert user_row["can_approve"] is False

		frappe.set_user(added_user)
		assignee_row = approval_row(fetch_approvals_for_pi(pi), "User Approval")
		assert assignee_row["can_approve"] is True
		assert assignee_row["can_reassign"] is False

		frappe.set_user("Administrator")
		admin_row = approval_row(fetch_approvals_for_pi(pi), "User Approval")
		assert admin_row["can_approve"] is False
		assert admin_row["can_reassign"] is False
		assert admin_row["can_remove"] is True

		frappe.set_user("mbritt@cfc.co")
		assert approval_row(fetch_approvals_for_pi(pi), "User Approval")["can_remove"] is False

		frappe.set_user(requester)
		frappe.call(
			"approvals.approvals.api.remove_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			uda_name=uda_name,
		)
		assert not frappe.db.exists("User Document Approval", uda_name)
		assert not frappe.db.exists("ToDo", todo_name)
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(48)
def test_manual_user_approval_cannot_reassign():
	requester = "arivers@cfc.co"
	first_user = "mmckay@cfc.co"
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	ensure_purchase_invoice_assignments(pi)

	try:
		frappe.set_user(requester)
		frappe.call(
			"approvals.approvals.api.add_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			user=first_user,
		)
		uda_name = frappe.db.get_value(
			"User Document Approval",
			{"reference_name": pi.name, "approver": first_user},
			"name",
		)

		frappe.set_user(first_user)
		with pytest.raises(frappe.ValidationError):
			frappe.call(
				"approvals.approvals.api.reassign_user_approval",
				doc=frappe.as_json(pi.as_dict()),
				uda_name_or_role=uda_name,
				to_user=requester,
			)
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)


@pytest.mark.order(49)
def test_approved_rule_row_hides_reassign_and_remove():
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	ensure_purchase_invoice_assignments(pi)
	delegate = "mbritt@cfc.co"

	try:
		frappe.set_user("Administrator")
		frappe.call(
			"approvals.approvals.api.reassign_user_approval",
			doc=frappe.as_json(pi.as_dict()),
			uda_name_or_role=ROLE_ACCOUNTS_MANAGER,
			to_user=delegate,
		)
		assert_no_satisfies_role_uda(pi, ROLE_ACCOUNTS_MANAGER)
		frappe.set_user(delegate)
		frappe.call(
			"approvals.approvals.api.approve_document",
			doc=frappe.as_json(pi.as_dict()),
			role=ROLE_ACCOUNTS_MANAGER,
			user=delegate,
		)

		row = approval_row(fetch_approvals_for_pi(pi), ROLE_ACCOUNTS_MANAGER)
		assert row["approved"] is True
		assert row["can_reassign"] is False
		assert row["can_remove"] is False
	finally:
		frappe.set_user("Administrator")
		delete_test_purchase_invoice(pi.name)
