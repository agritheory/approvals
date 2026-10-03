# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest


def purchase_order_rule(condition):
	rule = frappe.new_doc("Document Approval Rule")
	rule.approval_doctype = "Purchase Order"
	rule.approval_role = "Purchase Manager"
	rule.condition = condition
	return rule


@pytest.mark.parametrize(
	"condition",
	[
		"",
		"{{ doc.grand_total > 500 }}",
		"{{ total_amount > 500 and doc.get('supplier') }}",
		"{{ doc.items | selectattr('cost_center', 'equalto', 'Main - CFC') | list | length > 0 }}",
		"{{ doc.items | selectattr('cost_center', 'ne', 'Main - CFC') | list | length > 0 }}",
		"{{ doc.items | selectattr('is_fixed_asset') | list | length > 0 }}",
		"{% if doc.grand_total > 500 %}True{% endif %}",
	],
)
def test_valid_conditions_are_accepted(condition):
	purchase_order_rule(condition).validate_condition()


@pytest.mark.parametrize(
	"condition,message",
	[
		("doc.grand_total > 500", "no Jinja expression"),
		("{{ doc.grand_total > 500 }} and {{ doc.supplier }}", "text outside"),
		("{{ doc.grand_total > 500 && doc.supplier }}", "syntax error"),
		("{{ any([i.cost_center == 'Main - CFC' for i in doc.items]) }}", "syntax error"),
		("{{ doc.items | not_a_filter }}", "syntax error"),
		(
			"{{ doc.items | selectattr('cost_center', 'notequalto', 'Main - CFC') | list }}",
			"Unknown Jinja test",
		),
		("{{ grand_total > 500 }}", "Unknown variable"),
		("{{ doc.total_amount > 500 }}", "no field"),
		("{{ doc.get('total_amount') > 500 }}", "no field"),
	],
)
def test_invalid_conditions_are_rejected(condition, message):
	with pytest.raises(frappe.ValidationError, match=message):
		purchase_order_rule(condition).validate_condition()
