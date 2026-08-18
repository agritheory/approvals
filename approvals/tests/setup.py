# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

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
	customers,
)
from approvals.tests.fixtures import customer_custom_fields


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
			"language": "en-US",
			"time_zone": "America/New_York",
		}
	)
	create_customer_custom_fields()
	create_workflows()
	create_employees(settings)
	create_suppliers(settings)
	create_items(settings)
	create_document_approval_settings(settings)
	create_pi_document_approval_rules(settings)
	create_customers(settings)
	create_purchase_orders(settings)
	create_invoices(settings)
	set_test_user_passwords()
	sync_approver_user_roles()
	dismiss_onboarding(settings)


def create_customers(settings):
	customer_group = frappe.db.get_value("Customer Group", {"is_group": 0}, "name")
	for customer_name, credit_limit in customers:
		customer = frappe.new_doc("Customer")
		customer.customer_name = customer_name
		customer.customer_type = "Company"
		customer.customer_group = customer_group
		customer.append(
			"credit_limits",
			{"company": settings.company, "credit_limit": credit_limit},
		)
		customer.save()


def create_customer_custom_fields():
	for field in customer_custom_fields:
		if frappe.db.exists("Custom Field", {"dt": field["dt"], "fieldname": field["fieldname"]}):
			continue
		custom_field = frappe.new_doc("Custom Field")
		custom_field.update(field)
		custom_field.insert(ignore_permissions=True)

	frappe.clear_cache(doctype="Customer")


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
		existing_name = frappe.db.get_value(
			"Document Approval Rule",
			{"approval_doctype": d.get("approval_doctype"), "approval_role": d.get("approval_role")},
			"name",
		)
		if existing_name:
			dar = frappe.get_doc("Document Approval Rule", existing_name)
			for field in ("primary_assignee", "condition", "enabled", "message"):
				if d.get(field) is not None:
					dar.set(field, d[field])
			dar.save()
			continue
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


def set_test_user_passwords():
	from frappe.utils.password import update_password

	for email in ("mbritt@cfc.co", "mmckay@cfc.co", "arivers@cfc.co"):
		if frappe.db.exists("User", email):
			update_password(email, "admin")


def sync_approver_user_roles():
	"""PI forms read Buying Settings on load; approvers need Purchase User in the desk."""
	role_map = {
		"arivers@cfc.co": ["Stock Manager", "Item Manager", "Purchase User"],
		"mmckay@cfc.co": [
			"Sales User",
			"Sales Manager",
			"Sales Master Manager",
			"Purchase User",
		],
	}
	for email, roles in role_map.items():
		if not frappe.db.exists("User", email):
			continue
		user = frappe.get_doc("User", email)
		existing_roles = {row.role for row in user.roles}
		if not any(role not in existing_roles for role in roles):
			continue
		for role in roles:
			if role not in existing_roles:
				user.append("roles", {"role": role})
		user.save(ignore_permissions=True)


def dismiss_onboarding(settings=None):
	for m in frappe.get_all("Module Onboarding"):
		frappe.db.set_value("Module Onboarding", m, "is_complete", 1)


def create_workflows(settings=None):
	for workflow in workflows:
		existing_name = frappe.db.get_value(
			"Workflow", {"document_type": workflow.get("document_type")}, "name"
		)
		if existing_name:
			sync_workflow_from_fixture(existing_name, workflow)
			continue
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
		doc.update(workflow)
		doc.save()


def sync_workflow_from_fixture(name, workflow):
	doc = frappe.get_doc("Workflow", name)
	for field in (
		"reapproval_condition",
		"approval_state",
		"approval_action",
		"require_rejection_reason",
		"workflow_state_field",
		"override_status",
	):
		if workflow.get(field) is not None:
			doc.set(field, workflow[field])

	fixture_states = {state["state"]: state for state in workflow.get("states", [])}
	for state in doc.states:
		fixture = fixture_states.get(state.state)
		if not fixture:
			continue
		for field in (
			"update_field",
			"update_value",
			"is_approved_state_for_non_submittable_document",
		):
			if field in fixture:
				state.set(field, fixture[field])
			elif field in ("update_field", "update_value"):
				state.set(field, None)

	doc.save()


def create_purchase_orders(settings=None):
	for supplier in suppliers:
		po = frappe.new_doc("Purchase Order")
		po.company = settings.company
		po.transaction_date = po.schedule_date = settings.day
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
	if not frappe.db.exists("Designation", "Associate"):
		frappe.get_doc({"doctype": "Designation", "designation_name": "Associate"}).insert()

	for employee in employees:
		if only_create and employee.get("employee_name") not in only_create:
			continue

		if frappe.db.exists("Employee", {"employee_name": employee.get("employee_name")}):
			continue

		empl = frappe.new_doc("Employee")
		empl.update({key: value for key, value in employee.items() if key != "roles"})
		empl.designation = "Associate"
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
