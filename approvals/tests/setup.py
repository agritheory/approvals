import datetime
import os

import frappe
from erpnext.setup.utils import enable_all_roles_and_domains, set_defaults_for_tests
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
from frappe.installer import update_site_config

from approvals.tests.fixtures import (
	document_approval_rules,
	suppliers,
	tax_authority,
	employees,
	workflows,
)


def before_test():
	frappe.clear_cache()
	today = frappe.utils.getdate()
	setup_complete(
		{
			"currency": "USD",
			"full_name": "Administrator",
			"company_name": "Chelsea Fruit Co",
			"timezone": "America/New_York",
			"company_abbr": "CFC",
			"domains": ["Distribution"],
			"country": "United States",
			"fy_start_date": today.replace(month=1, day=1).isoformat(),
			"fy_end_date": today.replace(month=12, day=31).isoformat(),
			"language": "en-US",
			"company_tagline": "Chelsea Fruit Co",
			"email": "support@agritheory.dev",
			"password": "admin",
			"chart_of_accounts": "Standard with Numbers",
			"bank_account": "Primary Checking",
		}
	)
	enable_all_roles_and_domains()
	set_defaults_for_tests()
	frappe.db.commit()
	create_test_data()


def create_test_data():
	settings = frappe._dict(
		{
			"day": datetime.date(
				int(frappe.defaults.get_defaults().get("fiscal_year", datetime.datetime.now().year)), 1, 1
			),
			"company": frappe.defaults.get_defaults().get("company"),
		}
	)
	create_workflows()
	create_employees(settings)
	create_suppliers(settings)
	create_items(settings)
	create_document_approval_settings(settings)
	create_pi_document_approval_rules(settings)
	create_client_scripts(settings)
	create_purchase_orders(settings)
	create_invoices(settings)
	dismiss_onboarding()


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
		item.append(
			"item_defaults",
			{"company": settings.company, "default_warehouse": "", "default_supplier": supplier[0]},
		)
		item.save()


def create_invoices(settings):
	for supplier in suppliers:
		pi = frappe.new_doc("Purchase Invoice")
		pi.company = settings.company
		pi.set_posting_time = 1
		pi.posting_date = settings.day
		pi.supplier = supplier[0]
		pi.append(
			"items",
			{
				"item_code": supplier[1],
				"rate": supplier[3],
				"qty": 1,
			},
		)
		pi.save()
		# pi.submit()  # Create drafts in system to be able to test approval mechanism
	pi = frappe.new_doc("Purchase Invoice")
	pi.company = settings.company
	pi.set_posting_time = 1
	pi.posting_date = settings.day
	pi.supplier = suppliers[0][0]
	pi.append(
		"items",
		{
			"item_code": suppliers[0][1],
			"rate": 75.00,
			"qty": 1,
		},
	)
	pi.save()
	# pi.submit()


def create_pi_document_approval_rules(settings=None):
	for d in document_approval_rules:
		dar = frappe.new_doc("Document Approval Rule")
		dar.approval_doctype = d.get("approval_doctype")
		dar.approval_role = d.get("approval_role")
		dar.primary_assignee = d.get("primary_assignee")
		dar.condition = d.get("condition")
		dar.enabled = d.get("enabled")
		dar.save()


def create_document_approval_settings(settings=None):
	das = frappe.get_doc("Document Approval Settings", "Document Approval Settings")
	das.settings = "{}"  # Invalid JSON error if left blank in UI
	das.fallback_approver_role = "Accounts Manager"
	das.save()


def create_client_scripts(settings=None):
	cs = frappe.new_doc("Client Script")
	cs.dt = cs.name = "Purchase Invoice"
	cs.apply_to = "Form"
	cs.enabled = 1
	cs.script = "frappe.ui.form.on('Purchase Invoice', {refresh(frm) {frappe.provide('approvals').load_approvals(frm)}})"
	cs.save()

	cs = frappe.new_doc("Client Script")
	cs.dt = cs.name = "Purchase Order"
	cs.apply_to = "Form"
	cs.enabled = 1
	cs.script = "frappe.ui.form.on('Purchase Order', {refresh(frm) {frappe.provide('approvals').load_approvals(frm)}})"
	cs.save()


def dismiss_onboarding(settings=None):
	for m in frappe.get_all("Module Onboarding"):
		frappe.db.set_value("Module Onboarding", m, "is_complete", 1)


def create_workflows(settings=None):
	for workflow in workflows:
		for state in workflow.get("states"):
			if frappe.db.exists("Workflow State", state.get("state")):
				continue
			ws = frappe.new_doc("Workflow State")
			ws.workflow_state_name = state.get("state")
			ws.style = state.get("style")
			ws.save()
		for state in workflow.get("transitions"):
			if frappe.db.exists("Workflow Action Master", state.get("action")):
				continue
			ws = frappe.new_doc("Workflow Action Master")
			ws.workflow_action_name = state.get("action")
			ws.save()
		doc = frappe.new_doc("Workflow")
		doc.update(**workflow)
		doc.save()


def create_purchase_orders(settings=None):
	for supplier in suppliers:
		po = frappe.new_doc("Purchase Order")
		po.company = settings.company
		po.transaction_date = po.required_date = settings.day
		po.supplier = supplier[0]
		po.append(
			"items",
			{
				"item_code": supplier[1],
				"rate": supplier[3],
				"qty": 1,
			},
		)
		po.save()


def create_employees(settings, only_create=None):

	for employee in employees:
		if only_create and employee.get("employee_name") not in only_create:
			continue

		if frappe.db.exists("Employee", {"employee_name": employee.get("employee_name")}):
			continue

		if not frappe.db.exists("Designation", employee.get("designation")):
			desg = frappe.new_doc("Designation")
			desg.designation_name = employee.get("designation")
			desg.save()

		empl = frappe.new_doc("Employee")
		empl.update(employee)
		empl.reports_to = None
		if settings.company:
			empl.company = settings.company
		empl.save()

		user = frappe.new_doc("User")
		user.email = f"{empl.first_name[0].lower()}{empl.last_name.lower()}@cfc.co"
		user.first_name = empl.first_name
		user.last_name = empl.last_name
		user.send_welcome_email = 0
		user.enabled = 1
		user.language = settings.language
		user.time_zone = settings.time_zone
		for r in employee.get("roles", []):
			user.append("roles", {"role": r})

		user.save()
		empl.user_id = user.email
		if employee.get("reports_to"):
			empl.reports_to = frappe.get_value("Employee", {"employee_name": employee.get("reports_to")})
		empl.save()
