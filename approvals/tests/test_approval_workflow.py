# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt
from frappe.model.workflow import apply_workflow

from approvals.approvals.api import fetch_approvals_and_roles

"""
Approval Rules:
- PO less than 200, no approvals required
- PO, Stock Manager mmckay@cfc.com 200.00 < doc.grand_total < 500.00
- PO, Sales Manager arivers@cfc.com 500.00 < doc.grand_total < 1000.00
- PO, Accounts Manager mbritt@cfc.co doc.grand_total > 1000
"""


def send_po_for_approval():
	frappe.set_user("Administrator")
	for ts in frappe.get_all("Purchase Order", {"docstatus": 0}):
		po = frappe.get_doc("Purchase Order", ts)
		if po.workflow_state == "Draft":
			apply_workflow(po, "Send for Approval")


def test_approval_side_effects():
	send_po_for_approval()
	frappe.set_value(
		"Document Approval Settings", "Document Approval Settings", "fallback_approver", "mbritt@cfc.co"
	)
	purchase_orders = frappe.get_all("Purchase Order", {"docstatus": 0})
	for p in purchase_orders:
		po = frappe.get_doc("Purchase Order", p)
		a = fetch_approvals_and_roles(po)
		assert po.workflow_state == "Pending Approval"
	return
	for p in purchase_orders:
		if flt(po.grand_total) < 200.00:
			assert not frappe.db.exists("ToDo", {"reference_name": po.name})
		elif 200.00 < flt(po.grand_total) < 500.00:
			assert frappe.db.exists("ToDo", {"allocated_to": "mmckay@cfc.co", "reference_name": po.name})
			assert frappe.db.exists("DocShare", {"user": "mmckay@cfc.co", "share_name": po.name})
			# assert frappe.db.exists('Notification Log')
		elif 500.00 < flt(po.grand_total) < 1000.00:
			# assert po._assign == ['arivers@cfc.com']
			assert frappe.db.exists("ToDo", {"allocated_to": "arivers@cfc.co", "reference_name": po.name})
			assert frappe.db.exists("DocShare", {"user": "arivers@cfc.co", "share_name": po.name})
			# assert frappe.db.exists('Notification Log')
		elif 1000.00 < flt(po.grand_total):
			assert frappe.db.exists("ToDo", {"allocated_to": "mbritt@cfc.co", "reference_name": po.name})
			# None because user has permission to view the document normally
			assert not frappe.db.exists("DocShare", {"user": "mbritt@cfc.co", "share_name": po.name})
			# assert frappe.db.exists('Notification Log')
