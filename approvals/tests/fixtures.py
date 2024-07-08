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

document_approval_rules = [
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
	{
		"approval_doctype": "Purchase Order",
		"approval_role": "Accounts Manager",
		"primary_assignee": "",
		"condition": "doc.grand_total > 1000.00",
		"enabled": 1,
	},
	{
		"approval_doctype": "Purchase Order",
		"approval_role": "Stock Manager",
		"primary_assignee": "quincy@cfc.com",
		"condition": "500.00 <= doc.grand_total <= 1000.00",
		"enabled": 1,
	},
	{
		"approval_doctype": "Purchase Order",
		"approval_role": "Item Manager",
		"primary_assignee": "sam@cfc.com",
		"condition": "200.00 <= doc.grand_total < 500.00",
		"enabled": 1,
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
		"role": document_approval_rules[1]["approval_role"],
	},
	{
		"email": "sam@cfc.com",
		"first_name": "Sam",
		"last_name": "Adams",
		"send_welcome_email": 0,
		"enabled": 1,
		"language": "en",
		"time_zone": "US/Eastern",
		"role": document_approval_rules[2]["approval_role"],
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


workflows = [
	{
		"name": "Purchase Order",
		"docstatus": 0,
		"idx": 0,
		"workflow_name": "Purchase Order",
		"document_type": "Purchase Order",
		"is_active": 1,
		"override_status": 0,
		"send_email_alert": 0,
		"workflow_state_field": "workflow_state",
		"custom_approval_state": "Pending Approval",
		"states": [
			{
				"idx": 1,
				"state": "Draft",
				"doc_status": "0",
				"is_optional_state": 0,
				"avoid_status_override": 0,
				"allow_edit": "All",
			},
			{
				"idx": 2,
				"state": "Pending Approval",
				"doc_status": "0",
				"is_optional_state": 0,
				"avoid_status_override": 0,
				"allow_edit": "All",
			},
			{
				"name": "lkeo0p1tjq",
				"owner": "Administrator",
				"creation": "2024-07-08 16:12:31.183859",
				"modified": "2024-07-08 16:12:31.183859",
				"modified_by": "Administrator",
				"docstatus": 0,
				"idx": 3,
				"state": "Approved",
				"doc_status": "1",
				"is_optional_state": 0,
				"avoid_status_override": 0,
				"allow_edit": "All",
			},
			{
				"idx": 4,
				"state": "Cancelled",
				"doc_status": "2",
				"is_optional_state": 0,
				"avoid_status_override": 0,
				"allow_edit": "All",
			},
		],
		"transitions": [
			{
				"idx": 1,
				"state": "Draft",
				"action": "Save",
				"next_state": "Draft",
				"allowed": "All",
				"allow_self_approval": 1,
			},
			{
				"idx": 2,
				"state": "Draft",
				"action": "Send for Approval",
				"next_state": "Pending Approval",
				"allowed": "All",
				"allow_self_approval": 1,
			},
			{
				"idx": 3,
				"state": "Pending Approval",
				"action": "Approve",
				"next_state": "Approved",
				"allowed": "All",
				"allow_self_approval": 1,
			},
			{
				"idx": 4,
				"state": "Pending Approval",
				"action": "Reject",
				"next_state": "Draft",
				"allowed": "All",
				"allow_self_approval": 1,
			},
			{
				"idx": 5,
				"state": "Approved",
				"action": "Cancel",
				"next_state": "Cancelled",
				"allowed": "All",
				"allow_self_approval": 1,
			},
		],
	}
]
