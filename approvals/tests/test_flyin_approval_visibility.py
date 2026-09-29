# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock

import frappe
import pytest
from frappe.database.mariadb.database import MariaDBDatabase
from playwright.sync_api import expect

from approvals.tests.playwright_helpers import login_as, open_form_with_flyin
from approvals.tests.playwright_telemetry import (
	ensure_bench_web_running,
	init_playwright_url_state,
)
from approvals.tests.test_purchase_invoice_non_workflow_approval import (
	create_draft_purchase_invoice_for_supplier,
	ensure_purchase_invoice_assignments,
	purchase_invoice_for_supplier,
)
from approvals.tests.test_utils import use_current_db_transaction


@pytest.fixture(scope="session")
def playwright_bench_web():
	ensure_bench_web_running()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, request, playwright_bench_web):
	args = {
		**browser_context_args,
		"viewport": {"width": 1280, "height": 900},
	}
	base_url = getattr(request.config.option, "base_url", None)
	init_playwright_url_state(base_url=base_url)
	return args


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, request, playwright_bench_web):
	base_url = getattr(request.config.option, "base_url", None)
	env = init_playwright_url_state(base_url=base_url)
	map_host = env.get("playwright_resolver_map_host")
	if not map_host:
		return browser_type_launch_args
	launch_args = list(browser_type_launch_args.get("args") or [])
	launch_args.append(f"--host-resolver-rules=MAP {map_host} 127.0.0.1")
	return {**browser_type_launch_args, "args": launch_args}


@pytest.fixture(scope="module", autouse=True)
def use_real_database_commits():
	if isinstance(frappe.db.commit, MagicMock):
		frappe.db.commit = lambda: MariaDBDatabase.commit(frappe.db)
	yield frappe.db


@pytest.fixture(autouse=True)
def browser_setup(page):
	page.set_default_timeout(15000)
	yield


def cleanup_test_purchase_invoice(pi_name: str):
	for uda in frappe.get_all(
		"User Document Approval",
		filters={"reference_doctype": "Purchase Invoice", "reference_name": pi_name},
		pluck="name",
	):
		frappe.delete_doc("User Document Approval", uda, ignore_permissions=True)
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
	if frappe.db.exists("Purchase Invoice", pi_name):
		frappe.delete_doc("Purchase Invoice", pi_name, ignore_permissions=True)
	frappe.db.commit()


@pytest.mark.order(22)
def test_viewer_sees_required_approvals_with_actions_disabled(page):
	"""
	Stock Manager can read a high-value invoice and see every required approval on it,
	even when they cannot act. Their other assignments stay below that group.

	| Document              | Viewer role on doc     | Top group                         | Below        |
	| --------------------- | ---------------------- | --------------------------------- | ------------ |
	| Cooperative Ag Finance| Purchase User (read)   | Accounts Manager, User Approval   | Sphere Cellular |
	"""
	viewer = "arivers@cfc.co"
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	ensure_purchase_invoice_assignments(pi)
	frappe.call(
		"approvals.approvals.api.add_user_approval",
		doc=frappe.as_json(pi.as_dict()),
		user="mmckay@cfc.co",
	)
	frappe.db.commit()

	sphere_pi_name = purchase_invoice_for_supplier("Sphere Cellular").name
	ensure_purchase_invoice_assignments(frappe.get_doc("Purchase Invoice", sphere_pi_name))
	frappe.db.commit()

	try:
		login_as(page, viewer)
		open_form_with_flyin(page, pi.doctype, pi.name)

		document_section = page.locator(".pending-approvals__section").first
		expect(document_section).to_contain_text("Accounts Manager")
		expect(document_section).to_contain_text("User Approval")
		expect(document_section.locator(".pending-approvals__document-row")).to_have_count(2)
		expect(document_section.locator("button:has-text('Approve')")).to_have_count(0)
		expect(document_section.locator("button:has-text('Reject')")).to_have_count(0)

		assigned_section = page.locator(".pending-approvals__section").nth(1)
		expect(assigned_section).to_contain_text("Assigned to you")
		expect(assigned_section).to_contain_text(sphere_pi_name)
		expect(assigned_section).to_contain_text("Stock Manager")
		expect(assigned_section).not_to_contain_text(pi.name)

		with use_current_db_transaction():
			pi.reload()
			assert pi.docstatus == 0
			assert not frappe.db.exists(
				"Document Approval",
				{"reference_name": pi.name, "approver": viewer},
			)
	finally:
		cleanup_test_purchase_invoice(pi.name)
