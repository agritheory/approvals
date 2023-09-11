suppliers = [
	("Exceptional Grid", "Electricity", "Credit Card", 150.00),
	("Liu & Loewen Accountants LLP", "Accounting Services", "Check", 500.00),
	("Mare Digitalis", "Cloud Services", "Credit Card", 200.00),
	("AgriTheory", "ERPNext Consulting", "Check", 1000.00),
	("HIJ Telecom, Inc", "Internet Services", "Check", 150.00),
	("Sphere Cellular", "Phone Services", "Credit Card", 250.00),
	("Cooperative Ag Finance", "Financial Services", "Bank Draft", 5000.00),
]

tax_authority = [
	("Local Tax Authority", "Payroll Taxes", "Check", 0.00),
]

pi_dars = [
	{
		"approval_doctype": "Purchase Invoice",
		"approval_role": "Accounts Manager",
		"primary_assignee": "",
		"condition": "doc.grand_total > 999.00",
		"enabled": 1,
	},
	{
		"approval_doctype": "Purchase Invoice",
		"approval_role": "Stock Manager",
		"primary_assignee": "quincy@cfc.com",
		"condition": "500.00 <= doc.grand_total <= 999.00",
		"enabled": 1,
	},
	{
		"approval_doctype": "Purchase Invoice",
		"approval_role": "Item Manager",
		"primary_assignee": "",
		"condition": "100.00 <= doc.grand_total < 500.00",
		"enabled": 0,
	},
]

users = [
	{
		"email": "quincy@cfc.com",
		"first_name": "Quincy",
		"last_name": "Adams",
		"send_welcome_email": 0,
		"enabled": 1,
		"language": "en",
		"time_zone": "US/Eastern",
		"role": pi_dars[1]["approval_role"],
	},
	{
		"email": "sam@cfc.com",
		"first_name": "Sam",
		"last_name": "Adams",
		"send_welcome_email": 0,
		"enabled": 1,
		"language": "en",
		"time_zone": "US/Eastern",
		"role": pi_dars[2]["approval_role"],
	},
]

script_text = """
roles = [{'approval_role': i['approval_role']} for i in frappe.get_all(
		"Document Approval Rule",
		{'approval_doctype': doc.doctype, 'enabled': 1},
		'approval_role'
	)
]
for role in roles:
	approval_rule = frappe.get_cached_doc(
		'Document Approval Rule',
		{'approval_doctype': doc.doctype, 'approval_role': role['approval_role']}
	)
	if approval_rule.apply(doc):
		approval_rule.assign_user(doc)
"""
