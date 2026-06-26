# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from playwright.sync_api import Page, expect

from approvals.tests.playwright_telemetry import get_playwright_base_url


def login_as(page: Page, user: str, password: str = "admin"):
	page.goto(get_playwright_base_url())
	page.get_by_role("textbox", name="Email").fill(user)
	page.get_by_role("textbox", name="Password").fill(password)
	page.get_by_role("button", name="Login").click()
	page.wait_for_url("**/app/**", timeout=15000)


def form_page_url(doctype: str, name: str):
	return f"{get_playwright_base_url()}{frappe.utils.get_absolute_url(doctype, name)}"


def dismiss_blocking_modals(page: Page):
	for _ in range(5):
		modal = page.locator(".modal.show")
		if modal.count() == 0:
			return
		if "Permanently Submit" in modal.first.inner_text():
			return
		for selector in (
			".btn-modal-close:visible",
			".modal-header .close:visible",
			".btn-secondary:visible",
		):
			button = modal.locator(selector)
			if button.count():
				button.first.click(timeout=2000)
				page.wait_for_timeout(300)
				break
		else:
			page.keyboard.press("Escape")
			page.wait_for_timeout(300)


def enabled_approve_button(page: Page):
	return page.locator("#approvals-section button#approve-btn:not([disabled])")


def wait_for_enabled_approve(page: Page, timeout: int = 30000):
	dismiss_blocking_modals(page)
	expect(page.locator("#approvals-section")).to_be_visible(timeout=timeout)
	expect(page.locator("#approvals-section li")).not_to_have_count(0, timeout=timeout)
	approve = enabled_approve_button(page)
	expect(approve).to_have_count(1, timeout=timeout)
	expect(approve).to_be_visible(timeout=timeout)
	return approve


def open_form_page(page: Page, doctype: str, name: str):
	page.goto(form_page_url(doctype, name), wait_until="domcontentloaded")
	dismiss_blocking_modals(page)
	wait_for_enabled_approve(page)


def click_approve(page: Page):
	approve = wait_for_enabled_approve(page, timeout=15000)
	approve.scroll_into_view_if_needed()
	approve.click()


def confirm_modal_visible(page: Page, docname: str):
	modal = page.locator(".modal.show")
	expect(modal).to_be_visible(timeout=5000)
	expect(modal).to_contain_text("Permanently Submit")
	expect(modal).to_contain_text(docname)


def dismiss_confirm_modal(page: Page):
	modal = page.locator(".modal.show")
	modal.get_by_role("button", name="No", exact=True).click()
	expect(modal).to_have_count(0, timeout=5000)


def accept_confirm_modal(page: Page):
	modal = page.locator(".modal.show")
	modal.get_by_role("button", name="Yes", exact=True).click()
	expect(modal).to_have_count(0, timeout=10000)
	page.wait_for_function(
		"() => typeof cur_frm !== 'undefined' && cur_frm.doc && cur_frm.doc.docstatus === 1",
		timeout=15000,
	)
