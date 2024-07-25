# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.model.document import Document


class DocumentApprovalSettings(Document):
	@property
	def doctypes(self):
		return [d.get("approval_doctype") for d in self.approval_doctypes]

	def validate(self):
		try:
			json.loads(self.settings)
		except Exception:
			frappe.throw(frappe._("Invalid JSON"))

	def get_settings(self):
		settings = json.loads(self.settings)
		return frappe._dict(settings)
