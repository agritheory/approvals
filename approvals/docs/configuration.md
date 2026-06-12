<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Configuration

<div class="byline">
  Tyler Matteson 2026-02-28
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

When a document does not match any rules, the system needs a fallback. Without configuration, it throws an error.

Navigate to Approvals > Document Approval Settings and set a Fallback Approver Role. Documents that do not match any rules require approval from this role instead of failing.

A specific Fallback Approver user can also be set. Unmatched documents then always go to that one person.

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
