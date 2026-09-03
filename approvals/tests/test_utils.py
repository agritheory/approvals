# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import time
from contextlib import contextmanager

import frappe


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
