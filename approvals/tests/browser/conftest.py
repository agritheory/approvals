# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock

import frappe
import pytest
from frappe.database.mariadb.database import MariaDBDatabase


@pytest.fixture(scope="session", autouse=True)
def use_real_database_commits(db_instance):
	if isinstance(frappe.db.commit, MagicMock):
		frappe.db.commit = lambda: MariaDBDatabase.commit(frappe.db)
	yield frappe.db


@pytest.fixture(autouse=True)
def browser_timeouts(page):
	page.set_default_timeout(15000)
	yield
