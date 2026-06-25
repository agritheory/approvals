<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Configuration

<div class="byline">
  Rohan Bansal, Cursor, fproldan, Ishwarya, Myuddin Khatri, Heather Kusmierz, and Tyler Matteson 2026-06-23
</div>

## Creating an Approval Rule

Organizations often need certain documents to require approval before submission. For example, purchase orders over a certain amount might need a manager to sign off. Invoices hitting specific expense accounts might need review from the accounting team.

To set up a rule, navigate to Approvals > Document Approval Rule and create a new record.

A rule answers two questions:

1. Which documents need approval? Select the DocType (for example, Purchase Order or Purchase Invoice).
2. Who should approve them? Select a Role (for example, Accounts Manager or Purchase Manager).

Check the Enabled box and save. Every document of that type now requires approval from someone with that role.

## Narrowing Down with Conditions

Not every purchase order needs manager approval. Only the expensive ones might. A condition makes a rule selective.

Conditions are Jinja templates that evaluate against the document. When the condition returns true, the rule applies. When it returns false, the rule does not apply.

**Require approval for orders over $10,000:**

```jinja
{{ doc.grand_total > 10000 }}
```

**Require approval when items hit specific expense accounts:**

```jinja
{{ any([i.expense_account in account_numbers('Capital Equipment - CO', 'Office Supplies - CO') for i in doc.items]) }}
```

**Require approval for a specific supplier:**

```jinja
{{ doc.supplier == "SUPPLIER-001" }}
```

Conditions can combine multiple checks:

```jinja
{{ doc.grand_total > 5000 and doc.company == "Main Company" }}
```

Use the Test Condition button to verify a condition works against a real document before enabling the rule.

### Available Context

Conditions have access to the full document as `doc`, plus several helpers:

- `doc.fieldname` accesses any field on the document
- `doc.items` accesses child table rows for iteration
- `expense_accounts`, `income_accounts`, `tax_accounts`, and `asset_accounts` are pre-fetched lists of account names by type
- `account_numbers('Capital Equipment - CO', 'Office Supplies - CO')` returns a list of exact account names to check against. Pass each account name as it appears in ERPNext; the helper does not expand ranges.
- `any()` and `all()` are Python built-ins for checking lists
- `frappe.get_value()` and `frappe.get_all()` perform database lookups when related data is needed

To find field names for conditions, navigate to Setup > Customize Form, select the DocType, and review the field names in the Fields table.

## Multiple Rules for the Same Document

A DocType can have multiple rules. Each rule that matches creates an approval requirement.

**Example setup for Purchase Order:**

| Rule | Role | Condition |
| :--- | :--- | :-------- |
| 1 | Purchase Manager | `{{ doc.grand_total > 5000 }}` |
| 2 | Finance Manager | `{{ doc.grand_total > 25000 }}` |
| 3 | Accounts Manager | `{{ any([i.expense_account in expense_accounts for i in doc.items]) }}` |

A $30,000 order with expense items requires approval from all three roles. A $3,000 order with no expense items requires none.

## Controlling Assignment

When a rule matches, someone needs to review the document. There are two approaches.

**Distribute work automatically:** Leave Primary Assignee empty and keep Automatically Assign Users checked. The system assigns approvals round-robin to users who have the role. It tracks who received the last assignment so work distributes evenly.

**Assign to one person:** Set a Primary Assignee. Every matching document goes to that user. This approach works well for roles where one person handles all approvals, or during testing.

When Automatically Assign Users is unchecked, the rule still requires the role's approval, but no ToDo is created. Users with the role can still approve from the document. They just do not receive a notification.

### Skipping Auto Repeat Documents

Check **Skip for Auto Repeat** on a rule when documents created by Auto Repeat should not trigger that rule. When enabled and the document has an `auto_repeat` value set, the rule is bypassed entirely. Use this for recurring documents that were already approved on the original and should not require a fresh approval cycle each time they are generated.

## Setting Up a Fallback

When a document matches a DocType that has approval rules configured, but none of those rules apply, the system needs a fallback. Without configuration, it throws an error.

Navigate to Approvals > Document Approval Settings and set a Fallback Approver Role. Documents of a configured DocType that do not match any rules require approval from this role instead of failing.

A specific Fallback Approver user can also be set. Unmatched documents then always go to that one person.

The fallback does not apply to DocTypes with no approval rules at all. Those DocTypes do not show the approval sidebar.

## Using Settings in Conditions

Document Approval Settings includes a **Settings** field that accepts arbitrary JSON. The parsed values are available in every condition template as `settings`.

Store thresholds, account lists, or other site-specific values in the JSON blob instead of hard-coding them in each rule. For example, set the Settings field to:

```json
{
  "approval_threshold": 10000,
  "high_risk_suppliers": ["SUPPLIER-001", "SUPPLIER-002"]
}
```

Then reference those values in a condition:

```jinja
{{ doc.grand_total > settings.approval_threshold or doc.supplier in settings.high_risk_suppliers }}
```

Changes to the settings JSON apply to all rules immediately. No code changes are required.

## Approvals Without a Workflow

Some submittable documents need approval before posting, but not a full workflow with states like Pending Approval or Send for Approval. Purchase Invoice is a common example: accounts payable saves vendor bills as drafts, matching rules assign approvers on save, and the final approver submits the invoice from the sidebar.

This pattern works well when:

- The document is submittable (for example, Purchase Invoice or Purchase Order)
- Approvers should act on draft documents without a separate workflow transition
- The site does not need workflow-driven rejection, reapproval, or state locking

Workflows remain optional. Use them when you need explicit approval states, rejection flows, or non-submittable documents like Customer credit limit changes.

### Setup

1. **Do not** create a Workflow for the DocType, or leave the DocType out of any active Workflow record.
2. Navigate to Approvals > Document Approval Rule and create one or more rules for the DocType (see [Creating an Approval Rule](#creating-an-approval-rule) and [Narrowing Down with Conditions](#narrowing-down-with-conditions)).
3. Optionally configure a [Fallback Approver](#setting-up-a-fallback) for documents that match the DocType but no rule condition.
4. Ensure users who approve have the required roles and can open the document (the app creates ToDo assignments and DocShare access when needed).

**Example setup for Purchase Invoice at Chelsea Fruit Co:**

| Rule | Role | Condition | Primary Assignee |
| :--- | :--- | :-------- | :--------------- |
| 1 | Stock Manager | `{{ doc.grand_total > 200 and doc.grand_total < 500 }}` | (round-robin) |
| 2 | Sales Manager | `{{ doc.grand_total > 500 and doc.grand_total < 1000 }}` | (round-robin) |
| 3 | Accounts Manager | `{{ doc.grand_total > 1000 }}` | Morgan Britt |

A $250 invoice from Sphere Cellular requires Stock Manager approval. A $5,000 invoice from Cooperative Ag Finance requires Accounts Manager approval. A $150 invoice matches no rule and needs no approval unless the fallback role is configured.

### How It Behaves

On every save of a draft document, matching rules run and approvers are assigned (ToDo records, and DocShare when the assignee lacks read access). The approval sidebar appears on the form for any DocType with at least one enabled rule.

Approvers use the sidebar **Approve** and **Reject** buttons while the document remains in draft (`docstatus = 0`). The form is not locked by a workflow Approval State; editors can still change the document until it is submitted.

When the last required approver clicks **Approve** on a submittable document **without a workflow**, a confirmation dialog appears — **Permanently Submit {document name}?** — before the approval is recorded and the document submits. This matches ERPNext's normal submit confirmation.

The standard **Submit** toolbar action is also blocked until all required sidebar approvals exist (`before_submit` validation).

### Workflow vs No Workflow

| | No workflow | With workflow |
| :--- | :---------- | :------------ |
| When rules evaluate | On each save while draft | When document enters Approval State |
| Form editing | Draft stays editable | Locked in Approval State |
| Final action | Confirm, then auto-submit (submittable) | Auto-submit or workflow transition |
| Rejection | No workflow state change; use comments | Workflow Reject returns to Draft and clears approvals |
| Reapproval | Change document and save; re-assign on save | Reapproval Condition on workflow |

For rejection handling without a workflow, rely on document comments or add a Workflow later if you need structured reject-and-revise flows.

## Email Reminders

Users can forget they have documents waiting. Reminder emails list all pending approvals for each user.

The app ships with `send_reminder_email()` but does not register a scheduled job by default. Reminders run only when something calls that function on a schedule.

1. In Document Approval Settings, set Reminder Email Hour to when reminders should send (0-23, in server time). The function sends only during that hour.

2. Add this to the site's `site_config.json`:

```json
{
  "approvals": {
    "send_reminder_email": true
  }
}
```

3. Wire up a scheduled job that calls `approvals.approvals.api.send_reminder_email`. For example, add an hourly entry to `scheduler_events` in the app's `hooks.py` or call the function from a custom bench task on the desired cadence.

## Connecting to Workflows

Approval rules can also evaluate when documents enter a specific workflow state. The DocType needs a Workflow configured with an Approval State set.

In the Workflow record, the Approval State field tells Approvals which state represents "waiting for approval." When a document transitions into this state, rules evaluate and assignments are created.

A typical workflow has states like Draft, Pending Approval, and Approved. A Rejected state returns documents to Draft.

The app adds these fields to the standard Workflow DocType:

| Field | Purpose |
| :--- | :-------- |
| **Approval State** | Workflow state where approval rules run and the form is locked |
| **Approval Action** | Workflow transition action applied when all sidebar approvals are recorded (submittable doctypes) |
| **Require Rejection Reason** | Prompt approvers for a comment when rejecting |
| **Reapproval Condition** | Jinja condition that returns a document to Approval State on save |

**Submittable DocTypes** (like Purchase Order) need **Approval State** and **Approval Action** set on the Workflow, plus a matching transition from the approval state to a submitted state (`doc_status=1`). Example: Approval State = `Pending`, Approval Action = `Approve`, with an Approve transition from Pending → Approved. If **Approval Action** is empty, the app defaults to `Approve`.

**Non-submittable DocTypes** (documents that are never submitted) need one workflow state marked **Approved State for Non-Submittable Document**. When all required approvals are recorded, the app applies the workflow transition to that state instead of submitting the document.

### Reapproval Condition

Use Reapproval Condition when a saved change should send the document back for approval without a manual workflow action. The condition is a Jinja template evaluated on every save. When it returns true and the document is not already in Approval State, the workflow state resets to Approval State, existing approvals are cleared, and matching rules assign approvers again.

**Return a Customer to approval when the credit limit changes:**

```jinja
{{ doc.credit_limits and flt(doc.credit_limits[0].credit_limit) != flt(doc.last_approved_credit_limit or 0) }}
```

Reapproval conditions can reference any field on the document, including child tables. The `flt` helper is available in workflow templates.

### State Field Updates

Each workflow state can set an additional field when the document enters that state. Approvals extends Frappe's workflow engine so **Update Value** supports Jinja templates, not just static text.

**Record the approved credit limit on Customer when approval completes:**

| Setting | Value |
| :--- | :------ |
| Update Field | `last_approved_credit_limit` |
| Update Value | `{{ doc.credit_limits[0].credit_limit if doc.credit_limits else 0 }}` |

Sites define their own custom fields through Customize Form. The app does not install DocType-specific fields.

### Using ERPNext Status as the Workflow State Field

Some submittable DocTypes use ERPNext's built-in **status** field as the workflow state field instead of a separate custom field like `workflow_state`. The workflow record sets **Workflow State Field** to `status` and **Override Status** so workflow transitions drive operational status values such as Pending and Approved. Typically this also requires extensive overrides to `status_updater` and to the doctype's listview. This approach isn't recommended but is included here for completeness sake.

Configure sidebar finalization the same way as any other submittable DocType: set **Approval State**, **Approval Action**, and an Approve transition from the approval state to a submitted state (`doc_status=1`).

Set **Update Field** and **Update Value** on the approval and approved states so `status` stays aligned when users move through the workflow:

| Workflow State | doc_status | Update Field | Update Value |
| :--- | :--- | :--- | :--- |
| Pending (Approval State) | 0 | `status` | `Pending` |
| Approved | 1 | `status` | `Approved` |

When the last sidebar approval is recorded, the app applies the configured **Approval Action**. That runs the same workflow transition as the Approve button: it submits the document, sets the workflow state field, and applies the Approved state's **Update Field** values. If finalization only called `submit()` without the workflow transition, the document could end up submitted while **status** still showed Pending.

Document Approval Rule conditions should match documents in the approval state using the same field the workflow uses, for example:

```jinja
{{ doc.status == 'Pending' }}
```

Sites that use **status** as the workflow state field typically also customize Purchase Order `set_status` so ERPNext does not overwrite workflow-driven values such as Pending and Approved on save. That override is site-specific and is not part of the approvals app.

### Where the Sidebar Appears

The approval sidebar appears only on DocTypes that have at least one enabled Document Approval Rule. DocTypes without rules do not show the panel, even when a fallback approver is configured in settings. The fallback applies when rules exist for the DocType but none match the current document.

## Example: Customer Credit Limit

The repository includes a complete example for approving Customer credit limit changes without submitting the Customer. It lives in `approvals/tests/fixtures.py` and is loaded by `approvals/tests/setup.py` for automated tests only. It is not installed with the app.

To use the pattern on a site:

1. Add custom fields to Customer (or your DocType) through Customize Form — at minimum a workflow state field and any baseline fields your reapproval condition compares against.
2. Create a Workflow using the example as a reference: set Approval State, Reapproval Condition, and Approved-state Update Field/Value.
3. Create a Document Approval Rule with a condition that matches documents in Approval State.
4. Mark the Approved workflow state as **Approved State for Non-Submittable Document**.

Run `bench execute 'approvals.tests.setup.before_test'` on a development site to load the example workflow, rule, custom fields, and test customers.
