# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from pathlib import Path

import frappe


def after_install():
	add_pending_approval_email_template()


def add_pending_approval_email_template():
	if not frappe.db.exists("Email Template", "Pending Approval"):
		email_template = frappe.new_doc("Email Template")
		template_path = Path(__file__).parent.joinpath("templates/emails/pending_approval.html")
		email_template.update(
			{
				"name": "Pending Approval",
				"subject": "Documents Pending Approval",
				"use_html": 1,
				"response_html": template_path.read_text(),
			}
		)
		email_template.insert()
