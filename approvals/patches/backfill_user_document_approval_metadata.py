# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe


def execute():
	for row in frappe.get_all("User Document Approval", fields=["name", "owner"]):
		values = {}
		if not frappe.db.get_value("User Document Approval", row.name, "origin"):
			values["origin"] = "manual"
		if not frappe.db.get_value("User Document Approval", row.name, "requested_by"):
			values["requested_by"] = row.owner
		if values:
			frappe.db.set_value("User Document Approval", row.name, values, update_modified=False)
