<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Extending Approvals

<div class="byline">
  Tyler Matteson 2026-10-04
</div>

This page is for developers building a Frappe app alongside Approvals. Each extension point is a hook registered in the other app's `hooks.py`. None of them require changes to Approvals itself.

## Adding Names to Conditions

Rule conditions and Reapproval Conditions run in Frappe's safe evaluation environment, with `doc` and `settings` added (see [What a Condition Can Use](configuration.md#what-a-condition-can-use)). To add more names, register a function under `approval_condition_context`. The function takes no arguments and returns a dict of names to add.

```python
# my_app/hooks.py
approval_condition_context = ["my_app.approvals.condition_context"]

# my_app/approvals.py
def condition_context():
	return {"is_capital_account": is_capital_account}
```

An administrator can then use the new name in a rule condition:

```python
any(is_capital_account(i.expense_account) for i in doc.items)
```

## Supplying Approvers from Your Own Data

Rules assign approvals by role. Some approvals belong to a specific person found through the document's own data, such as the project manager on the Purchase Order's project. An approver provider returns those people. The app keeps them in sync as User Approval rows on the document.

Register providers under `approvals_approver_providers`, keyed by DocType. Use `"*"` for every DocType.

```python
# my_app/hooks.py
approvals_approver_providers = {
	"Purchase Order": ["my_app.approvals.project_manager_provider"],
}

# my_app/approvals.py
import frappe


def project_manager_provider(doc):
	manager = frappe.db.get_value("Project", doc.project, "project_manager")
	return [{"user": manager, "reason": "Project manager sign-off"}] if manager else []
```

A provider receives the document and returns a list. Each entry is either a user name or a dict with `user` and an optional `reason`.

Providers run every time the document is saved, after rules assign their approvals. Each run compares the provider's current list with the rows it added before:

- New users get a User Approval row, a ToDo, and a notification. The row records the provider's dotted path as its origin.
- Users the provider no longer returns are removed, unless they have already approved
- Users still returned are left alone

If a provider raises an error, the app logs it in the Error Log and skips that provider for that save. Approvers from a provider can only be removed by hand by a user with the User Approval Manager Role.

## Changing Who Can Manage Approvers

The default rules for adding, removing, and reassigning approvers are described in [Usage](usage.md#working-with-approvers-on-a-single-document). To change them, register a permission function under `approvals_user_approval_permission`.

```python
# my_app/hooks.py
approvals_user_approval_permission = ["my_app.approvals.user_approval_permission"]

# my_app/approvals.py
def user_approval_permission(action, doc, user, uda=None):
	if action == "add" and doc.doctype == "Purchase Invoice":
		return "Accounts User" in frappe.get_roles(user)
	return None
```

The function receives:

| Argument | Description |
| :--- | :--- |
| `action` | `"add"`, `"remove"`, or `"reassign"` |
| `doc` | The document being approved |
| `user` | The user attempting the action |
| `uda` | The User Document Approval row for remove and reassign, otherwise `None` |

Return `True` to allow, `False` to deny, or `None` to defer. The app tries each registered function in order, and the first result that is not `None` wins. If every function returns `None`, the built-in rules apply.

The server checks these permissions when an approver is added or removed, and the drawer uses them to decide which buttons to show. Reassigning a rule approval does not consult this hook. It is always limited to the current assignee and the User Approval Manager Role.

## Reacting to Approver Changes

Register handlers under `approvals_user_approval_events` to act when an approver is added, removed, or reassigned, for example to post to a chat channel.

```python
# my_app/hooks.py
approvals_user_approval_events = ["my_app.approvals.on_user_approval_event"]

# my_app/approvals.py
def on_user_approval_event(event, uda, actor, reason=None, previous_approver=None, doc=None, **kwargs):
	if event == "reassigned":
		notify_channel(f"{doc.name}: approval moved from {previous_approver} to {uda.approver}")
```

| Argument | Description |
| :--- | :--- |
| `event` | `"added"`, `"removed"`, or `"reassigned"` |
| `uda` | The affected row, with `reference_doctype`, `reference_name`, `approver`, and `requested_by` |
| `actor` | The user who made the change |
| `reason` | The reason entered in the dialog, if any |
| `previous_approver` | The previous assignee, for reassignments |
| `doc` | The document being approved |

Accept `**kwargs` so the handler keeps working if more arguments are added later.

After the registered handlers run, the app's own handler creates the Notification Log entries and the timeline comment described in [Usage](usage.md). Code that changes approvers in bulk, such as a data migration, can set `frappe.flags.skip_user_approval_events = True` to skip all handlers, including the app's own.

## Linking to the Pending Approvals Drawer

Any desk URL for a document can open the drawer by adding query parameters:

| Parameter | Effect |
| :--- | :--- |
| `flyin=pending-approvals` | Opens the Pending Approvals drawer |
| `approval_todo=TODO-00001` | Selects that ToDo in the drawer |

For example, `/app/purchase-order/PO-00001?flyin=pending-approvals&approval_todo=TODO-00001`. The drawer removes both parameters from the address bar once it opens.

To build this link in Python, call `approvals.approvals.api.get_approval_notification_link(doc, todo_name=None)`. It accepts a document, or a dict with `doctype` and `name` (or `reference_doctype` and `reference_name`). The function is also available in Jinja templates such as Email Templates and Print Formats:

```jinja
<a href="{{ get_approval_notification_link(document) }}">{{ document.name }}</a>
<a href="{{ get_approval_notification_link(document, document.todo_name) }}">{{ document.name }}</a>
```

The reminder email already passes each row a ready-made link as `document.url`, so a customized Pending Approval Email Template can use that directly.

## Scheduling Reminder Emails

The app provides `approvals.approvals.api.send_reminder_email` but does not schedule it. Schedule it hourly. The function only sends when `approvals.send_reminder_email` is true in `site_config.json` and the current server hour matches Reminder Email Hour in Document Approval Settings.

```python
# my_app/hooks.py
scheduler_events = {
	"hourly": ["approvals.approvals.api.send_reminder_email"],
}
```
