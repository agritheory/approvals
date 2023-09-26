import frappe
from frappe.utils import flt
import pytest


"""
Approval Rules:
- PI, Item Manager (Sam Adams, sam@cfc.com) 200.00 <= doc.grand_total < 500.00
- PI, Stock Manager (Quincy Adams, quincy@cfc.com): 500.00 <= doc.grand_total <= 1000.00

Purchase Invoices requiring approval:
- Liu $ Loewen Accountants LLP, $500, ACC-PINV-2023-00002 (Quincy)
- Mare Digitalis, $200, ACC-PINV-2023-00003 (Sam)
- AgriTheory, $1,000, ACC-PINV-2023-00004 (Quincy)
- Sphere Cellular, $250, ACC-PINV-2023-00006 (Sam)
"""


def test_todo_creation():
	todos = frappe.get_all("ToDo")
	assert len(todos) == 4
	for todo in todos:
		td = frappe.get_doc("ToDo", todo)
		assert td.reference_type == "Purchase Invoice"
		grand_total = flt(frappe.get_value("Purchase Invoice", td.reference_name, "grand_total"))
		if 200 <= grand_total < 500:
			assert td.role == "Item Manager"
			assert td.allocated_to == "sam@cfc.com"
		elif 500 <= grand_total <= 1000:
			assert td.role == "Stock Manager"
			assert td.allocated_to == "quincy@cfc.com"
