<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Configuration

<div class="byline">
  Tyler Matteson 2026-03-02
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

**Require approval when items hit capital expense accounts:**

```jinja
{{ any([i.expense_account in account_numbers('6100', '6200') for i in doc.items]) }}
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
- `account_numbers('5000', '5100')` creates a list of account numbers to check against
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

## Setting Up a Fallback

When a document matches a DocType that has approval rules configured, but none of those rules apply, the system needs a fallback. Without configuration, it throws an error.

Navigate to Approvals > Document Approval Settings and set a Fallback Approver Role. Documents of a configured DocType that do not match any rules require approval from this role instead of failing.

A specific Fallback Approver user can also be set. Unmatched documents then always go to that one person.

The fallback does not apply to DocTypes with no approval rules at all. Those DocTypes do not show the approval sidebar.

## Email Reminders

Users can forget they have documents waiting. Daily reminder emails list all pending approvals for each user.

1. In Document Approval Settings, set Reminder Email Hour to when reminders should send (0-23, in server time).

2. Add this to the site's `site_config.json`:

```json
{
  "approvals": {
    "send_reminder_email": true
  }
}
```

## Connecting to Workflows

Approval rules evaluate when documents enter a specific workflow state. The DocType needs a Workflow configured with an Approval State set.

In the Workflow record, the Approval State field tells Approvals which state represents "waiting for approval." When a document transitions into this state, rules evaluate and assignments are created.

A typical workflow has states like Draft, Pending Approval, and Approved. A Rejected state returns documents to Draft.

The app adds three fields to the standard Workflow DocType:

| Field | Purpose |
| :--- | :-------- |
| **Approval State** | Workflow state where approval rules run and the form is locked |
| **Require Rejection Reason** | Prompt approvers for a comment when rejecting |
| **Reapproval Condition** | Jinja condition that returns a document to Approval State on save |

Non-submittable DocTypes (documents that are never submitted) need one workflow state marked **Approved State for Non-Submittable Document**. When all required approvals are recorded, the app applies the workflow transition to that state instead of submitting the document.

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
