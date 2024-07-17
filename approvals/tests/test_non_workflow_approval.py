# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import pytest
import frappe
from frappe.utils.data import get_url_to_form

from playwright.sync_api import sync_playwright


@pytest.fixture
def admin_user():
	pass


@pytest.fixture
def stock_manager_user():
	pass


@pytest.fixture
def purchase_invoice_07():
	return f"http://localhost:{frappe.conf(frappe.local.site).webserver_port}"


def test_non_workflow_approval():
	doc = frappe.get_doc("Purchase Invoice", "ACC-PINV-2024-00007-15")
	assert doc.docstatus == 0

	with sync_playwright() as p:
		browser = p.firefox.launch(headless=False)
		context = browser.new_context()

		# Login via API
		api_request_context = context.request
		login_url = f"{frappe.utils.get_url()}/api/method/login"
		login_response = api_request_context.post(
			login_url,
			data={
				"usr": "Administrator",
				"pwd": "admin",
			},
		)
		assert login_response.ok, "Login failed"

		invoice_url = get_url_to_form(doc.doctype, doc.name)
		page = context.new_page()
		page.goto(invoice_url)
		page.wait_for_selector("#approve-btn")
		approve_button = page.query_selector("#approve-btn")
		approve_button.click()
		page.wait_for_selector(".btn-modal-primary")
		yes_button = page.query_selector(".btn-modal-primary")
		yes_button.click()
		browser.close()

	doc.reload()
	assert doc.status == "Approved"
