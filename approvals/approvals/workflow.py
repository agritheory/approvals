# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.core.doctype.submission_queue.submission_queue import queue_submission
from frappe.model.docstatus import DocStatus
from frappe.model.workflow import (
	WorkflowTransitionError,
	get_transitions,
	get_workflow,
	has_approval_access,
)
from frappe.utils import cint, cstr, flt
from frappe.utils.scheduler import is_scheduler_inactive
from jinja2 import BaseLoader, Environment

from approvals.approvals.validation import validate_all_approvals_complete


def render_workflow_template(template: str, doc) -> str:
	if not template or "{{" not in template:
		return template

	env = Environment(loader=BaseLoader(), autoescape=False)
	return env.from_string(template).render(doc=doc, flt=flt, cint=cint)


def evaluate_workflow_template(template: str, doc) -> bool:
	result = render_workflow_template(template, doc)
	if isinstance(result, str):
		result = result.strip().lower()
		return result not in ("false", "0", "", "none", "null")
	return bool(result)


@frappe.whitelist()
def apply_workflow(doc, action):
	"""Apply workflow with Jinja support in state update_value."""
	doc = frappe.get_doc(frappe.parse_json(doc))
	doc.load_from_db()
	workflow = get_workflow(doc.doctype)
	transitions = get_transitions(doc, workflow)
	user = frappe.session.user

	transition = None
	for t in transitions:
		if t.action == action:
			transition = t

	if not transition:
		frappe.throw(_("Not a valid Workflow Action"), WorkflowTransitionError)

	if not has_approval_access(user, doc, transition):
		frappe.throw(_("Self approval is not allowed"))

	next_state = next(d for d in workflow.states if d.state == transition.next_state)
	approval_state = workflow.approval_state
	current_state = doc.get(workflow.workflow_state_field)
	is_leaving_approval = approval_state and current_state == approval_state
	will_finalize = (
		cstr(next_state.doc_status) == "1"
		or cstr(next_state.is_approved_state_for_non_submittable_document) == "1"
	)

	if is_leaving_approval and will_finalize:
		validate_all_approvals_complete(doc, method="before_submit")

	doc.set(workflow.workflow_state_field, transition.next_state)

	if next_state.update_field:
		doc.set(
			next_state.update_field,
			render_workflow_template(next_state.update_value, doc),
		)

	new_docstatus = DocStatus(next_state.doc_status or 0)
	if doc.docstatus.is_draft() and new_docstatus.is_draft():
		doc.save()
	elif doc.docstatus.is_draft() and new_docstatus.is_submitted():
		if doc.meta.queue_in_background and not is_scheduler_inactive():
			queue_submission(doc, "Submit")
			return doc

		doc.flags.ignore_permissions = True
		doc.submit()
	elif doc.docstatus.is_submitted() and new_docstatus.is_submitted():
		doc.save()
	elif doc.docstatus.is_submitted() and new_docstatus.is_cancelled():
		doc.cancel()
	else:
		frappe.throw(_("Illegal Document Status for {0}").format(next_state.state))

	doc.add_comment("Workflow", _(next_state.state))

	return doc
