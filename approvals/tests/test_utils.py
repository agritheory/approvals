# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

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
