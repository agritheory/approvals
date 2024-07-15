import pytest
import frappe
from playwright.sync_api import Page, expect
from frappe.utils.data import get_url

from playwright.sync_api import sync_playwright


@pytest.fixture
def admin_user():
	pass


@pytest.fixture
def stock_manager_user():
	pass


def test_non_workflow_approval():
	# frappe.set_user(stock_manager_user.usr)
	doc = frappe.get_doc("Purchase Invoice", "ACC-PINV-2024-00007")
	assert doc.docstatus == 0

	with sync_playwright() as p:
		browser = p.firefox.launch()
		context = browser.new_context(
			base_url=f"http://localhost:{frappe.get_conf(frappe.local.site).webserver_port}"
		)
		page = browser.new_page()
		api_request_context = context.request
		page = context.new_page()
		response = api_request_context.get(
			f"{context.base_url}{doc.get_url()}",
			headers={
				"usr": "Administrator",
				"pwd": "admin",
			},
		)
		page.goto(purchase_invoice_07)
		print(page.title())
		browser.close()

	# TODO:
	# click on approve button
	# click on confirm dialog

	doc.reload()
	assert doc.docstatus == 1
