# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

# Server tests (default pytest from apps/approvals):
#   pytest --disable-warnings -s
#
# Browser tests (bench root, env activated; same CI runner runs both):
#   bench setup requirements --dev
#   python -m playwright install chromium
#   bench start
#   bench execute 'approvals.tests.setup.before_test'   # if fixture data is missing
#   pytest apps/approvals/approvals/tests/browser --browser chromium --disable-warnings --no-cov
#
# The site host_name must resolve (CI uses test_site in /etc/hosts). For a local bench,
# set host_name in site_config.json or map the site name in /etc/hosts to 127.0.0.1.

import frappe
import pytest

from approvals.tests.browser.helpers import (
	accept_confirm_modal,
	click_approve,
	confirm_modal_visible,
	dismiss_confirm_modal,
	login_as,
	open_form_page,
)
from approvals.tests.test_approval_workflow import send_purchase_orders_for_approval
from approvals.tests.test_purchase_invoice_non_workflow_approval import (
	ensure_purchase_invoice_assignments,
	purchase_invoice_for_supplier,
)
from approvals.tests.test_utils import use_current_db_transaction


@pytest.mark.order(1)
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


@pytest.mark.order(2)
@pytest.mark.parametrize(
	"supplier,user,approval_role",
	[
		pytest.param(
			"Liu & Loewen Accountants LLP", "mmckay@cfc.co", "Sales Manager", id="sales_manager"
		),
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


@pytest.mark.order(3)
@pytest.mark.parametrize(
	"supplier,user,approval_role",
	[
		pytest.param("AgriTheory", "mmckay@cfc.co", "Sales Manager", id="sales_manager"),
	],
)
def test_confirming_submits_invoice(page, supplier, user, approval_role):
	pi = purchase_invoice_for_supplier(supplier)
	ensure_purchase_invoice_assignments(pi)

	login_as(page, user)
	open_form_page(page, pi.doctype, pi.name)
	click_approve(page)
	confirm_modal_visible(page, pi.name)
	accept_confirm_modal(page)
	page.wait_for_timeout(1500)

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


@pytest.mark.order(4)
def test_workflow_purchase_order_does_not_show_submit_confirm(page):
	"""
	Workflow PO sidebar Approve must not show the non-workflow submit confirm dialog.

	Uses North County Grain Cooperative with a second required role so a partial
	Accounts Manager approval does not submit the PO.
	"""
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

	login_as(page, "mbritt@cfc.co")
	open_form_page(page, po.doctype, po.name)
	click_approve(page)
	modal = page.locator(".modal.show")
	assert not modal.filter(has_text="Permanently Submit").is_visible()

	with use_current_db_transaction():
		po.reload()
		assert po.docstatus == 0

	extra_rule.delete(ignore_permissions=True)
