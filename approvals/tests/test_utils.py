# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import time
from contextlib import contextmanager

import frappe
import pytest
from frappe.database.mariadb.database import MariaDBDatabase

from approvals.tests.fixtures import (
	reassign_fixture_invoices,
	timesheet_approval_employees,
	timesheet_fixture_note_prefix,
)


@pytest.fixture(scope="module", autouse=True)
def use_real_database_commits():
	mocked_commit = frappe.db.commit
	frappe.db.rollback()
	frappe.db.commit = lambda: MariaDBDatabase.commit(frappe.db)
	yield frappe.db
	frappe.db.commit = mocked_commit


@contextmanager
def use_current_db_transaction():
	"""
	Refresh pytest's database transaction so reads see commits from the live bench.

	Browser actions (Approve, Submit) commit through the web server. Pytest keeps its
	own transaction scope until rollback/begin.
	"""
	frappe.db.rollback()
	frappe.db.begin()
	yield


def clear_document_read_cache(doctype: str, name: str):
	frappe.clear_document_cache(doctype, name)


def wait_for_docstatus(doctype: str, name: str, docstatus: int, timeout: float = 30):
	"""Poll the database until a document reaches the expected docstatus."""
	deadline = time.time() + timeout
	last = None
	while time.time() < deadline:
		with use_current_db_transaction():
			clear_document_read_cache(doctype, name)
			last = frappe.db.get_value(doctype, name, "docstatus")
			if last == docstatus:
				return
		time.sleep(0.25)
	raise AssertionError(f"{doctype} {name} docstatus={last}, expected {docstatus}")


def timesheet_for_fixture(fixture_key: str):
	note = f"{timesheet_fixture_note_prefix}{fixture_key}"
	name = frappe.db.get_value("Timesheet", {"note": note}, "name")
	assert name, (
		f"Missing Timesheet fixture {fixture_key}. "
		"Run bench execute 'approvals.tests.setup.before_test'."
	)
	return frappe.get_doc("Timesheet", name)


def purchase_invoice_for_fixture(fixture_key: str):
	from approvals.tests.setup import create_reassign_fixture_invoices

	bill_no = reassign_fixture_invoices[fixture_key]
	name = frappe.db.get_value("Purchase Invoice", {"bill_no": bill_no, "docstatus": 0}, "name")
	if not name:
		create_reassign_fixture_invoices()
		name = frappe.db.get_value("Purchase Invoice", {"bill_no": bill_no, "docstatus": 0}, "name")
	assert name, (
		f"Missing Purchase Invoice fixture {fixture_key} (bill_no={bill_no}). "
		"Run bench execute 'approvals.tests.setup.before_test'."
	)
	return frappe.get_doc("Purchase Invoice", name)


def restore_timesheet_employee(timesheet, employee_name: str | None = None):
	employee_name = employee_name or timesheet_approval_employees["technician"]
	employee = frappe.db.get_value("Employee", {"employee_name": employee_name}, "name")
	timesheet.employee = employee
	timesheet.save()
	frappe.call("approvals.approvals.api.assign_approvers", doc=timesheet)
