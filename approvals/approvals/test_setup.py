import datetime

import frappe
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
from erpnext.setup.utils import enable_all_roles_and_domains, set_defaults_for_tests
from erpnext.accounts.doctype.account.account import update_account_number


def before_test():
	frappe.clear_cache()
	today = frappe.utils.getdate()
	setup_complete({
		"currency": "USD",
		"full_name": "Administrator",
		"company_name": "Chelsea Fruit Co",
		"timezone": "America/New_York",
		"company_abbr": "CFC",
		"domains": ["Distribution"],
		"country": "United States",
		"fy_start_date": today.replace(month=1, day=1).isoformat(),
		"fy_end_date": today.replace(month=12, day=31).isoformat(),
		"language": "english",
		"company_tagline": "Chelsea Fruit Co",
		"email": "support@agritheory.dev",
		"password": "admin",
		"chart_of_accounts": "Standard with Numbers",
		"bank_account": "Primary Checking"
	})
	enable_all_roles_and_domains()
	set_defaults_for_tests()
	frappe.db.commit()
	create_test_data()

suppliers = [
	("Exceptional Grid", "Electricity", "ACH/EFT", 150.00),
	("Liu & Loewen Accountants LLP", "Accounting Services", "ACH/EFT", 500.00),
	("Mare Digitalis", "Cloud Services", "Credit Card", 200.00),
	("AgriTheory", "ERPNext Consulting", "Check", 1000.00),
	("HIJ Telecom, Inc", "Internet Services", "Check", 150.00),
	("Sphere Cellular", "Phone Services", "ACH/EFT", 250.00),
	("Cooperative Ag Finance", "Financial Services", "Bank Draft", 5000.00),
]

tax_authority = [
	("Local Tax Authority", "Payroll Taxes", "Check", 0.00),
]

def create_test_data():
	settings = frappe._dict({
		'day': datetime.date(int(frappe.defaults.get_defaults().get('fiscal_year')), 1 ,1),
		'company': frappe.defaults.get_defaults().get('company'),
		'company_account': frappe.get_value("Account",
			{"account_type": "Bank", "company": frappe.defaults.get_defaults().get('company'), "is_group": 0}),
		})
	create_suppliers(settings)
	create_items(settings)
	create_invoices(settings)

def create_suppliers(settings):
	for supplier in suppliers + tax_authority:
		biz = frappe.new_doc("Supplier")
		biz.supplier_name = supplier[0]
		biz.supplier_group = "Services"
		biz.country = "United States"
		biz.supplier_default_mode_of_payment = supplier[2]
		biz.currency = "USD"
		biz.default_price_list = "Standard Buying"
		biz.save()

def create_items(settings):
	for supplier in suppliers + tax_authority:
		item = frappe.new_doc("Item")
		item.item_code = item.item_name = supplier[1]
		item.item_group = "Services"
		item.stock_uom = "Nos"
		item.maintain_stock = 0
		item.is_sales_item, item.is_sub_contracted_item, item.include_item_in_manufacturing = 0, 0, 0
		item.grant_commission = 0
		item.is_purchase_item = 1
		item.append("supplier_items", {"supplier": supplier[0]})
		item.append("item_defaults", {"company": settings.company, "default_warehouse": "", "default_supplier": supplier[0]})
		item.save()

def create_invoices(settings):
	for supplier in suppliers:
		pi = frappe.new_doc('Purchase Invoice')
		pi.company = settings.company
		pi.set_posting_time = 1
		pi.posting_date = settings.day
		pi.supplier = supplier[0]
		pi.append('items', {
			'item_code': supplier[1],
			'rate': supplier[3],
			'qty': 1,
		})
		pi.save()
		pi.submit()
	pi = frappe.new_doc('Purchase Invoice')
	pi.company = settings.company
	pi.set_posting_time = 1
	pi.posting_date = settings.day
	pi.supplier = suppliers[0][0]
	pi.append('items', {
		'item_code': suppliers[0][1],
		'rate': 75.00,
		'qty': 1,
	})
	pi.save()
	pi.submit()


def create_pi_document_approval_rule():
	dar = frappe.new_doc('Document Approval Rule')
	dar.approval_doctype = 'Purchase Invoice'
	dar.approval_role = 'Accounts Manager'
	dar.condition = "doc.grand_total > 999.00"
	dar.save()

def create_document_approval_settings():
	das = frappe.get_doc('Document Approval Settings', 'Document Approval Settings')
	das.fallback_approver = "Accounts Manager"
	das.save()


def create_client_script():
	cs = frappe.new_doc("Client Script")
	cs.dt = cs.name = "Purchase Invoice"
	cs.apply_to = "Form"
	cs.script = "frappe.ui.form.on('Purchase Invoice', {refresh: frm => {frappe.approvals.load_approvals(frm)}})"
	cs.save()


def create_server_script():
	da = frappe.new_doc("Server Script")
	da.name = 'Assign Approvers - Purchase Invoice'
	da.group = 'on_update'
	da.script_type = 'DocType Event'
	da.reference_doctype = 'Purchase Invoice'
	da.doctype_event = 'After Save'
	da.action = 'approvals.approvals.api.assign_approvers(doc)'
	da.save()