<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Configuration

<div class="byline">
  Rohan Bansal, Cursor, fproldan, Ishwarya, Myuddin Khatri, Heather Kusmierz, and Tyler Matteson 2026-10-04
</div>

Organizations often want certain documents reviewed before they post. Purchase Orders over a certain amount might need a manager's sign-off. Invoices that hit capital equipment accounts might need review from the accounting team. In Approvals, each of these requirements is a Document Approval Rule.

## Creating an Approval Rule

Navigate to Document Approval Rule and create a new record. A rule answers two questions:

1. Which documents need approval? Select the DocType, for example Purchase Order or Purchase Invoice.
2. Who should approve them? Select a Role, for example Accounts Manager or Purchase Manager.

Check Enabled and save. Every document of that type now requires approval from someone with that role.

## Narrowing Down with Conditions

Not every Purchase Order needs a manager's approval. Perhaps only the expensive ones do. A condition makes a rule selective.

A condition is a short Python expression that the app evaluates against the document. When the expression is true, the rule applies. When it is false, the rule does not apply. A rule with no condition applies to every document of its DocType.

Require approval for orders over $10,000:

```python
doc.grand_total > 10000
```

Require approval when any item posts to specific expense accounts:

```python
any(i.expense_account in ("Capital Equipment - CFC", "Office Supplies - CFC") for i in doc.items)
```

Require approval for a specific supplier:

```python
doc.supplier == "SUPPLIER-001"
```

Combine checks with `and` and `or`:

```python
doc.grand_total > 5000 and doc.company == "Chelsea Fruit Co"
```

Before enabling a rule, use the Test Condition button to check the condition against a real document.

### What a Condition Can Use

| Name | What it provides |
| :--- | :--- |
| `doc` | Any field on the document, including child tables such as `doc.items` |
| `settings` | Values from the Settings field in Document Approval Settings (see [Using Settings in Conditions](#using-settings-in-conditions)) |
| `frappe.utils` | Helpers such as `flt`, `cint`, `getdate`, `nowdate`, `add_days`, and `date_diff` |
| `frappe.db` | Read-only lookups: `get_value`, `exists`, `count`, `get_all`, and `get_single_value` |
| `frappe.get_doc`, `frappe.get_cached_doc` | Read another document (returned as plain data, not a live document) |
| Python built-ins | `any`, `all`, `min`, `max`, `sum`, and similar |

Conditions cannot change data. Calls such as `frappe.db.set_value` are not available.

To find a field's name, navigate to Customize Form, select the DocType, and look at the Fields table.

A developer can add more names to this list. See [Extending Approvals](extending.md#adding-names-to-conditions).

## Multiple Rules for the Same Document

A DocType can have several rules, one per role. Each rule that matches adds a required approval.

| Rule | Role | Condition |
| :--- | :--- | :--- |
| 1 | Purchase Manager | `doc.grand_total > 5000` |
| 2 | Finance Manager | `doc.grand_total > 25000` |
| 3 | Accounts Manager | `any(i.expense_account.startswith("6") for i in doc.items)` |

With these rules, a $30,000 Purchase Order with expense items needs approval from all three roles. A $3,000 order with no expense items needs none.

## Controlling Assignment

When a rule matches, someone needs to be told about it. There are two approaches.

To spread the work across a team, leave Primary Assignee empty and keep Automatically Assign Users checked. The app assigns approvals in rotation to the users who hold the role, and it remembers who received the last one.

To send every approval to one person, set a Primary Assignee. This works well when one person handles all approvals for a role, and it is convenient during testing.

Once a rule assigns an approval to someone, that person approves it, or hands it to a colleague with Reassign (see [Reassigning an Approval](usage.md#reassigning-an-approval)). When Automatically Assign Users is unchecked, nobody receives a ToDo, and anyone with the role can approve from the Pending Approvals drawer.

### Skipping Auto Repeat Documents

Check Skip for Auto Repeat on a rule when documents created by Auto Repeat should not need that rule's approval. Use this for recurring documents where the original was approved and each new copy should not start a fresh approval cycle.

## Setting Up a Fallback

When a DocType has rules but none of them match a document, the app needs to know who approves it. Without a fallback, saving the document fails with an error.

Navigate to Document Approval Settings and set a Fallback Approver Role. Documents that match no rule then require approval from that role. To send them to one person instead, set a Fallback Approver.

The fallback only applies to DocTypes that have at least one rule. DocTypes without rules never need approval.

## Using Settings in Conditions

Document Approval Settings has a Settings field that holds JSON. Its values are available in every condition as `settings`.

Keeping thresholds and lists in one place means an administrator can change them without editing each rule. For example, enter the following in the Settings field:

```json
{
  "approval_threshold": 10000,
  "high_risk_suppliers": ["SUPPLIER-001", "SUPPLIER-002"]
}
```

Then use those values in a condition:

```python
doc.grand_total > settings.approval_threshold or doc.supplier in settings.high_risk_suppliers
```

Changes to the Settings field take effect for every rule immediately.

## Managing Approvers on Individual Documents

Approvers can add a person to a single document, reassign a rule's approval to a colleague, or remove a person they added. [Usage](usage.md#working-with-approvers-on-a-single-document) describes these actions and who can take them.

In Document Approval Settings, the User Approval Manager Role (System Manager by default) can take all of these actions on any document. Users with this role can add approvers at any time, reassign any rule approval, and remove any added approver, including approvers added by an integration. Give this role to the people who resolve approval problems for others, such as an accounting lead or a system administrator.

## Approvals Without a Workflow

Some submittable documents need approval before they post but do not need a full Workflow with states like Pending Approval. Purchase Invoice is a common example. Accounts payable saves the supplier's invoice as a draft, the matching rules assign approvers on save, and the invoice submits when the last approver approves.

This approach works well when:

- The document is submittable, such as a Purchase Invoice or Purchase Order
- Approvers should act on draft documents without a separate workflow step
- The organization does not need workflow-driven rejection, reapproval, or a locked form while approval is pending

### Setup

1. Do not create a Workflow for the DocType, or leave the DocType out of any active Workflow.
2. Create one or more Document Approval Rules for the DocType (see [Creating an Approval Rule](#creating-an-approval-rule)).
3. Optionally set a [fallback](#setting-up-a-fallback) for documents that match no rule.
4. Make sure the approvers hold the required roles. The app shares the document with an assignee who cannot already open it.

Chelsea Fruit Co uses the following rules for Purchase Invoice:

| Rule | Role | Condition | Primary Assignee |
| :--- | :--- | :--- | :--- |
| 1 | Stock Manager | `doc.grand_total > 200 and doc.grand_total < 500` | Arden Rivers |
| 2 | Sales Manager | `doc.grand_total > 500 and doc.grand_total < 1000` | Minh McKay |
| 3 | Accounts Manager | `doc.grand_total > 1000` | Morgan Britt |

A $250 invoice needs Stock Manager approval from Arden. A $5,000 invoice needs Accounts Manager approval from Morgan. A $150 invoice matches no rule, so it goes to the fallback role if one is set.

### How It Behaves

Every save of a draft re-checks the rules and assigns any new approvals. The form stays editable until the document is submitted, and approvers can act from the Pending Approvals drawer at any time while it is a draft.

The standard Submit button stays blocked until every required approval is recorded. When the last approver approves, the document submits.

### Workflow or No Workflow

| | No Workflow | With a Workflow |
| :--- | :--- | :--- |
| When rules are checked | On every save while the document is a draft | When the document is in the approval state |
| Editing during approval | The draft stays editable | The form is read-only in the approval state |
| After the last approval | The document submits | The workflow's approval action runs, or the document moves to its approved state |
| Rejection | Clears recorded approvals; status does not change | Clears recorded approvals and applies the Reject action, usually back to Draft |
| Reapproval after a change | The next save re-checks the rules | A Reapproval Condition can send the document back for approval |

Without a Workflow, a rejection leaves the document as a draft for its author to correct. Add a Workflow later if the organization needs a formal reject-and-revise process.

## Connecting to Workflows

Approvals can also work inside a Workflow. The Workflow tells the app which state means "waiting for approval," and the app takes care of the approval step.

A typical Workflow for a Purchase Order has the states Draft, Pending Approval, and Approved, with a Reject transition from Pending Approval back to Draft. When a document enters Pending Approval, the rules are checked and approvals are assigned. The form is read-only while the document waits.

The app adds these fields to the Workflow DocType:

| Field | Purpose |
| :--- | :--- |
| Approval State | The workflow state where rules apply and the form is read-only |
| Approval Action | The transition to apply when the last approval is recorded (submittable DocTypes only, defaults to Approve) |
| Require Rejection Reason | Ask approvers for a reason when they reject |
| Reapproval Condition | A condition that sends a saved document back to the approval state |

For a submittable DocType such as Purchase Order, set Approval State and Approval Action. Make sure the Workflow has a transition with that action from the approval state to a submitted state (Doc Status 1). For example, set Approval State to Pending Approval and Approval Action to Approve, and add an Approve transition from Pending Approval to Approved.

For a DocType that is never submitted, such as Customer, mark one workflow state as Approved State for Non-Submittable Document. When the last approval is recorded, the app moves the document to that state.

### Reapproval Condition

A Reapproval Condition sends a document back for approval when a saved change needs a fresh review. It is checked on every save. When it is true and the document is not already in the approval state, the app moves the document back to the approval state, clears the approvals already recorded, and assigns approvers again.

Return a Customer for approval when its credit limit changes:

```python
doc.credit_limits and frappe.utils.flt(doc.credit_limits[0].credit_limit) != frappe.utils.flt(doc.last_approved_credit_limit or 0)
```

Reapproval conditions can use the same names as rule conditions.

### State Field Updates

Each workflow state can set a field when a document enters it. Approvals extends this so that Update Value can be a template rather than only fixed text.

To record the approved credit limit on a Customer when approval completes, set these on the Approved state:

| Setting | Value |
| :--- | :--- |
| Update Field | `last_approved_credit_limit` |
| Update Value | `{{ doc.credit_limits[0].credit_limit if doc.credit_limits else 0 }}` |

The app does not install fields like `last_approved_credit_limit`. Add them through Customize Form.

### Using the Status Field as the Workflow State Field

Some sites set a submittable DocType's Workflow State Field to the built-in status field and check Override Status, so workflow transitions set values such as Pending and Approved. This usually also needs custom code to stop ERPNext from overwriting those status values. It is not recommended, but it works with Approvals.

Configure it like any other submittable DocType, and set Update Field and Update Value so status stays aligned with the workflow:

| Workflow State | Doc Status | Update Field | Update Value |
| :--- | :--- | :--- | :--- |
| Pending (Approval State) | 0 | `status` | `Pending` |
| Approved | 1 | `status` | `Approved` |

When the last approval is recorded, the app runs the Approval Action, the same as clicking Approve in the Workflow. The document submits and its status becomes Approved. Rule conditions should match on the same field, for example `doc.status == "Pending"`.

## Email Reminders

Approvers can forget about documents waiting on them. A reminder email lists every pending approval for each user.

1. In Document Approval Settings, set Reminder Email Hour to the hour (0 to 23, server time) when reminders should go out.
2. Add the following to the site's `site_config.json`:

```json
{
  "approvals": {
    "send_reminder_email": true
  }
}
```

3. Ask a developer to schedule the reminder job. The app does not schedule it on its own (see [Extending Approvals](extending.md#scheduling-reminder-emails)).

Each document in the email links straight to the Pending Approvals drawer with that document selected. Administrators can change the email's wording in the Pending Approval Email Template.

## Example: Customer Credit Limit

The app's test setup includes a complete example of approving Customer credit limit changes. Customer is never submitted, so the example uses a Workflow. The example is loaded only on development sites and is not installed with the app.

To set up the same pattern on a site:

1. Add custom fields to Customer through Customize Form: a workflow state field, and a field to hold the last approved credit limit.
2. Create a Workflow with an approval state, the [Reapproval Condition](#reapproval-condition) above, and an Approved state that records the approved limit (see [State Field Updates](#state-field-updates)).
3. Mark the Approved state as Approved State for Non-Submittable Document.
4. Create a Document Approval Rule for Customer with the role Sales Manager and the condition `doc.workflow_state == "Pending Approval"`.

When someone changes a customer's credit limit and saves, the customer returns to Pending Approval. A Sales Manager approves the change from the Pending Approvals drawer, and the customer moves to Approved with the new limit recorded.
