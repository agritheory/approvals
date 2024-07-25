# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import pytest
import frappe
from frappe.utils.data import get_url_to_form
from frappe.utils import getdate

from playwright.sync_api import sync_playwright


@pytest.fixture
def purchase_manager_user():
	pass


def test_non_workflow_approval():
	doc = frappe.get_doc("Purchase Invoice", "ACC-PINV-2024-00007")
	assert doc.docstatus == 0

	with sync_playwright() as p:
		browser = p.firefox.launch()
		context = browser.new_context()

		# Login via API
		api_request_context = context.request
		login_url = f"{frappe.utils.get_url()}/api/method/login"
		login_response = api_request_context.post(
			login_url,
			data={
				"usr": "mbritt@cfc.co",
				"pwd": "Admin@123",
			},
		)
		assert login_response.ok, "Login failed"

		invoice_url = get_url_to_form(doc.doctype, doc.name)
		page = context.new_page()
		page.goto(invoice_url)
		page.wait_for_timeout(2000)

		# page.wait_for_selector("#approve-btn")
		# approve_button = page.query_selector("#approve-btn")
		# approve_button.click()
		# page.wait_for_selector(".btn-modal-primary")
		# yes_button = page.query_selector(".btn-modal-primary")
		# yes_button.click()

		approve_button = page.locator("#approve-btn")
		approve_button.click()
		yes_button = page.locator(".btn-modal-primary")
		yes_button.click()

		page.wait_for_timeout(2000)  # wait for 2 seconds
		browser.close()

	doc.reload()
	today = getdate()

	if doc.due_date < today:
		assert doc.status == "Overdue"
	elif doc.due_date >= today:
		assert doc.status == "Unpaid"
