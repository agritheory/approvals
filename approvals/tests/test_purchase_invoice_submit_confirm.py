# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt
#
# Headed: pytest approvals/tests/test_purchase_invoice_submit_confirm.py \
#   --browser chromium --headed --slowmo 500 -s

from unittest.mock import MagicMock

import frappe
import pytest
from frappe.database.mariadb.database import MariaDBDatabase

from approvals.tests.playwright_helpers import (
	accept_confirm_modal,
	click_approve,
	confirm_modal_visible,
	dismiss_confirm_modal,
	login_as,
	open_form_page,
)
from approvals.tests.playwright_telemetry import (
	ensure_bench_web_running,
	init_playwright_url_state,
)
from approvals.tests.test_purchase_invoice_non_workflow_approval import (
	create_draft_purchase_invoice_for_supplier,
	ensure_purchase_invoice_assignments,
	purchase_invoice_for_supplier,
)
from approvals.tests.test_approval_workflow import prepare_purchase_order_for_approval
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
	page.on("console", lambda msg: print(f"[console:{msg.type}] {msg.text}"))
	page.on("pageerror", lambda exc: print(f"[pageerror] {exc}"))
	page.on(
		"requestfailed",
		lambda request: print(f"[requestfailed] {request.method} {request.url} - {request.failure}"),
	)
	yield


@pytest.mark.order(20)
@pytest.mark.parametrize(
	"supplier,user",
	[
		pytest.param("Cooperative Ag Finance", "mbritt@cfc.co", id="accounts_manager"),
	],
)
def test_approve_shows_submit_confirm_for_non_workflow_invoice(page, supplier, user):
	pi = purchase_invoice_for_supplier(supplier)
	ensure_purchase_invoice_assignments(pi)

	login_as(page, user)
	open_form_page(page, pi.doctype, pi.name)
	click_approve(page)
	confirm_modal_visible(page, pi.name)
	dismiss_confirm_modal(page)

	with use_current_db_transaction():
		pi.reload()
		assert pi.docstatus == 0


@pytest.mark.order(21)
@pytest.mark.parametrize(
	"supplier,user,approval_role",
	[
		pytest.param("Sphere Cellular", "arivers@cfc.co", "Stock Manager", id="stock_manager"),
	],
)
def test_dismissing_confirm_does_not_submit_invoice(page, supplier, user, approval_role):
	pi = purchase_invoice_for_supplier(supplier)
	ensure_purchase_invoice_assignments(pi)

	login_as(page, user)
	open_form_page(page, pi.doctype, pi.name)
	click_approve(page)
	confirm_modal_visible(page, pi.name)
	dismiss_confirm_modal(page)

	with use_current_db_transaction():
		pi.reload()
		assert pi.docstatus == 0
		assert not frappe.db.exists(
			"Document Approval",
			{
				"reference_doctype": "Purchase Invoice",
				"reference_name": pi.name,
				"approver": user,
				"approval_role": approval_role,
			},
		)


@pytest.mark.order(22)
@pytest.mark.parametrize(
	"supplier,user,approval_role",
	[
		pytest.param(
			"Liu & Loewen Accountants LLP", "mmckay@cfc.co", "Sales Manager", id="sales_manager"
		),
	],
)
def test_confirming_submits_invoice(page, supplier, user, approval_role):
	pi = create_draft_purchase_invoice_for_supplier(supplier)
	ensure_purchase_invoice_assignments(pi)

	login_as(page, user)
	open_form_page(page, pi.doctype, pi.name)
	click_approve(page)
	confirm_modal_visible(page, pi.name)
	accept_confirm_modal(page)

	with use_current_db_transaction():
		pi.reload()
		assert pi.docstatus == 1
		assert frappe.db.exists(
			"Document Approval",
			{
				"reference_doctype": "Purchase Invoice",
				"reference_name": pi.name,
				"approver": user,
				"approval_role": approval_role,
			},
		)


@pytest.mark.order(23)
def test_workflow_purchase_order_does_not_show_submit_confirm(page):
	po = prepare_purchase_order_for_approval("Premier Equipment Leasing")

	extra_rule = frappe.new_doc("Document Approval Rule")
	extra_rule.approval_doctype = "Purchase Order"
	extra_rule.approval_role = "Sales Manager"
	extra_rule.condition = (
		"{{ doc.supplier == 'Premier Equipment Leasing' and doc.grand_total > 1000 }}"
	)
	extra_rule.primary_assignee = "mmckay@cfc.co"
	extra_rule.enabled = 1
	extra_rule.insert(ignore_permissions=True)
	frappe.db.commit()
	try:
		frappe.call("approvals.approvals.api.assign_approvers", doc=po)
		frappe.db.commit()

		login_as(page, "mbritt@cfc.co")
		open_form_page(page, po.doctype, po.name)
		click_approve(page)
		modal = page.locator(".modal.show")
		assert not modal.filter(has_text="Permanently Submit").is_visible()

		with use_current_db_transaction():
			po.reload()
			assert po.docstatus == 0
	finally:
		frappe.db.delete(
			"ToDo",
			{"reference_type": "Purchase Order", "reference_name": po.name, "role": "Sales Manager"},
		)
		frappe.db.commit()
		extra_rule.delete(ignore_permissions=True)
