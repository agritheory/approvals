import json

import frappe
from frappe.model.document import Document


class DocumentApprovalSettings(Document):
	def validate(self):
		try:
			json.loads(self.settings)
		except Exception:
			frappe.throw(frappe._("Invalid JSON"))

	def get_settings(self):
		settings = json.loads(self.settings)
		return frappe._dict(settings)
