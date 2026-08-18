# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import re

import frappe
from playwright.sync_api import Page, expect

from approvals.tests.playwright_telemetry import get_playwright_base_url

FLYIN_SLOT = "pending-approvals"
FLYIN_APPROVE = (
	".pending-approvals__active button.flyout-action-btn--primary:has-text('Approve'):not([disabled])"
)


def login_as(page: Page, user: str, password: str = "admin"):
	base_url = get_playwright_base_url()
	# Login in the browser so session cookies are scoped to the site hostname.
	# page.request posts to 127.0.0.1 with a Host header, but those cookies are
	# not sent when navigating to the canonical hostname (e.g. fraxinus:8045).
	page.goto(f"{base_url}/login", wait_until="domcontentloaded")
	response = page.evaluate(
		"""async ({ user, password }) => {
			const res = await fetch('/api/method/login', {
				method: 'POST',
				headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
				body: new URLSearchParams({ usr: user, pwd: password }),
			});
			return { ok: res.ok, status: res.status, body: await res.text() };
		}""",
		{"user": user, "password": password},
	)
	if not response.get("ok"):
		raise AssertionError(f"login failed for {user}: {response.get('status')} {response.get('body')}")
	page.goto(f"{base_url}/app")
	# The desk may settle at "/app" or redirect to "/app/<workspace>"; accept both.
	page.wait_for_url(re.compile(r"/app(/|\?|$)"), timeout=15000)


def form_page_url(doctype: str, name: str, *, flyin: bool = True):
	url = f"{get_playwright_base_url()}{frappe.utils.get_absolute_url(doctype, name)}"
	if flyin:
		separator = "&" if "?" in url else "?"
		url = f"{url}{separator}flyin={FLYIN_SLOT}"
	return url


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
	return page.locator(FLYIN_APPROVE)


def wait_for_enabled_approve(page: Page, timeout: int = 30000):
	dismiss_blocking_modals(page)
	expect(page.locator("body.flyin-drawer-open")).to_be_visible(timeout=timeout)
	expect(page.locator(".pending-approvals")).to_be_visible(timeout=timeout)
	expect(page.locator(".pending-approvals__context-loading")).to_have_count(0, timeout=timeout)
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


def accept_confirm_modal(page: Page, doctype: str, name: str):
	modal = page.locator(".modal.show")
	modal.get_by_role("button", name="Yes", exact=True).click()
	expect(modal).to_have_count(0, timeout=10000)
	page.wait_for_function(
		"""async ([doctype, name]) => {
			const docstatus = await frappe.db.get_value(doctype, name, 'docstatus');
			if (docstatus === 1) {
				if (typeof cur_frm !== 'undefined' && cur_frm?.doc?.name === name) {
					await cur_frm.reload_doc();
				}
				return true;
			}
			if (typeof cur_frm !== 'undefined' && cur_frm?.doc?.name === name) {
				await cur_frm.reload_doc();
			}
			return false;
		}""",
		arg=[doctype, name],
		timeout=30000,
	)
