# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from playwright.sync_api import Page


def login_as(page: Page, user: str, password: str = "admin"):
	page.goto(frappe.utils.get_url())
	page.get_by_role("textbox", name="Email").fill(user)
	page.get_by_role("textbox", name="Password").fill(password)
	page.get_by_role("button", name="Login").click()


def form_page_url(doctype: str, name: str):
	return f"{frappe.utils.get_url()}{frappe.utils.get_absolute_url(doctype, name)}"


def dismiss_blocking_modals(page: Page):
	for _ in range(5):
		modal = page.locator(".modal.show")
		if modal.count() == 0:
			return
		if "Permanently Submit" in modal.inner_text():
			return
		dismiss = page.locator(".modal.show .btn-secondary, .modal.show .close")
		if dismiss.count() == 0:
			return
		dismiss.first.click()
		page.wait_for_timeout(500)


def open_form_page(page: Page, doctype: str, name: str):
	page.goto(form_page_url(doctype, name))
	page.wait_for_load_state("networkidle")
	dismiss_blocking_modals(page)
	page.wait_for_selector("#approve-btn:not(.btn-disabled)", timeout=15000)


def click_approve(page: Page):
	page.locator("#approve-btn:not(.btn-disabled)").click()


def confirm_modal_visible(page: Page, docname: str):
	modal = page.locator(".modal.show")
	modal.wait_for(state="visible", timeout=5000)
	assert "Permanently Submit" in modal.inner_text()
	assert docname in modal.inner_text()


def dismiss_confirm_modal(page: Page):
	page.locator(".modal.show .btn-secondary").click()
	page.locator(".modal.show").wait_for(state="hidden", timeout=5000)


def accept_confirm_modal(page: Page):
	page.locator(".modal.show .btn-primary").click()
	page.locator(".modal.show").wait_for(state="hidden", timeout=10000)
