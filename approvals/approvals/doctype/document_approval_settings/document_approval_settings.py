from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
import json


class DocumentApprovalSettings(Document):
	def validate(self):
		try:
			json.loads(self.settings)
		except:
			frappe.throw('Invalid JSON')

	def get_settings(self):
		settings = json.loads(self.settings)
		return frappe._dict(settings)
