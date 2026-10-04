# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest

from approvals.approvals.conditions import evaluate_condition, validate_condition
from approvals.patches.convert_conditions_to_python import convert_condition_text


def dummy_condition_context():
	return {"always_true": lambda: True}


def test_convert_condition_unwraps_single_jinja_block():
	converted, reason = convert_condition_text("{{ doc.grand_total > 1000 }}")
	assert converted == "doc.grand_total > 1000"
	assert reason is None


def test_convert_condition_rewrites_bare_flt():
	converted, reason = convert_condition_text("{{ flt(doc.total) > 0 }}")
	assert "frappe.utils.flt" in converted
	assert reason is None


def test_approval_condition_context_hook(monkeypatch):
	monkeypatch.setattr(
		frappe,
		"get_hooks",
		lambda hook, default=None, app_name=None: (
			["approvals.tests.test_conditions.dummy_condition_context"]
			if hook == "approval_condition_context"
			else (default if default is not None else [])
		),
	)

	doc = frappe._dict(grand_total=100)
	assert evaluate_condition("always_true()", doc) is True


def test_condition_accepts_parent_field():
	validate_condition("doc.grand_total > 1000", "Purchase Order")


def test_condition_rejects_missing_parent_field():
	with pytest.raises(frappe.ValidationError, match="total_amount"):
		validate_condition("doc.total_amount > 1000", "Purchase Order")


def test_condition_accepts_doc_get_field():
	validate_condition('doc.get("supplier")', "Purchase Order")


def test_condition_rejects_missing_doc_get_field():
	with pytest.raises(frappe.ValidationError, match="not_a_field"):
		validate_condition('doc.get("not_a_field")', "Purchase Order")


def test_condition_ignores_other_method_calls():
	validate_condition("doc.as_dict()", "Purchase Order")


def test_condition_accepts_child_table_field():
	validate_condition(
		"any(i.expense_account == 'x' for i in doc.items)",
		"Purchase Order",
	)


def test_condition_rejects_missing_child_table_field():
	with pytest.raises(frappe.ValidationError, match="not_a_field"):
		validate_condition(
			"any(i.not_a_field == 'x' for i in doc.items)",
			"Purchase Order",
		)


def test_condition_rejects_index_on_non_table_field():
	with pytest.raises(frappe.ValidationError, match="not a child table"):
		validate_condition("doc.grand_total[0].amount", "Purchase Order")


def test_condition_cannot_call_db_set_value():
	doc = frappe._dict(name="TEST-001", doctype="Purchase Order")
	with pytest.raises(Exception):
		evaluate_condition('frappe.db.set_value("Purchase Order", doc.name, "status", "X")', doc)
