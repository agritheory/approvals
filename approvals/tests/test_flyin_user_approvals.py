# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from playwright.sync_api import expect

from approvals.tests.playwright_helpers import (
	frappe_confirm_yes,
	login_as,
	open_form_with_flyin,
	submit_add_user_approval_dialog,
	wait_for_pending_approvals_ready,
)
from approvals.tests.test_flyin_approval_visibility import (
	browser_context_args,
	browser_setup,
	browser_type_launch_args,
	cleanup_test_purchase_invoice,
	playwright_bench_web,
	use_real_database_commits,
)
from approvals.tests.test_purchase_invoice_non_workflow_approval import (
	create_draft_purchase_invoice_for_supplier,
	ensure_purchase_invoice_assignments,
)


@pytest.mark.order(50)
def test_flyin_add_and_remove_user_approver(page):
	requester = "arivers@cfc.co"
	added_user = "mmckay@cfc.co"
	pi = create_draft_purchase_invoice_for_supplier("Cooperative Ag Finance")
	ensure_purchase_invoice_assignments(pi)
	frappe.db.commit()

	try:
		login_as(page, requester)
		open_form_with_flyin(page, pi.doctype, pi.name)

		document_section = page.locator(".pending-approvals__section").first
		document_section.get_by_role("button", name="Add approver", exact=True).click()
		submit_add_user_approval_dialog(page, added_user)

		document_section = page.locator(".pending-approvals__section").first
		expect(document_section).to_contain_text("User Approval", timeout=15000)
		expect(document_section).to_contain_text("Requested by", timeout=15000)

		document_section.get_by_role("button", name="Remove", exact=True).click()
		with page.expect_response(
			lambda response: "remove_user_approval" in response.url and response.request.method == "POST",
			timeout=30000,
		):
			frappe_confirm_yes(page, message="Remove this approver?")

		wait_for_pending_approvals_ready(page, timeout=30000)
		expect(document_section).not_to_contain_text(added_user, timeout=15000)
	finally:
		cleanup_test_purchase_invoice(pi.name)
