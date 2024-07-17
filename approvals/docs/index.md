<!-- Copyright (c) 2024, AgriTheory and contributors
For license information, please see license.txt-->

# Approvals

_Approvals_ is an application that allows you to configurable require Roles or Users to approve any type of document in ERPNext. 

### Design
This application has a few design opinions that effect how it is used:
 - People change, but Roles tend to be more static. Roles don't usually go on vacation or retire.
 - If a Document Approval Rule computes that a Role's approval is required, it is not subject to hierarchy. The same person with multiple Roles can be asked to approve the same document in different capacities.
 - If a DocType has any rule, then at least one approval will be required to approve it. Since this is typically the same as "Submitting" the document, it becomes the most efficient way to structure your organization's policy.
 - For a document to change into its approved state, all computed approvals and requested User Approvals are required. When the last approver approves the document, it will transition.
 - When a document is rejected, a reason for rejection is required. All previous approvals are revoked. 


### DocTypes
Document Approval Settings allows you to include global variables in your Document Approval Rules as well as define a global fallback approver. This fallback approver should either be a final decision maker, or the person who's responsible for maintaining these rules so they can modify them to appropriately match policy.

Document Approval Rule is where an approval requirement is configured. These are configured per-DocType and per-Role and have a "condition" field that expects a Python expression that returns a Boolean value, typically `True` or `False`, or `1` or `0`. Values like `$ 2.40`, `-50000`, `Chelsea Fruit Company` all evaluate to True, which may not be the author's intention.

User Approval tracks the cases where a specific person is being asked to approve a Document. Any user who can view a document with a configured Document Approval Rule can request a User Approval or remove it. 

## Examples

| Doctype | Role | Logic | Primary Approver | 
| --- | --- | --- | --- |
| Purchase Order | None | less than 200 |  |
| Purchase Order | Stock Manager  | `200.00 < doc.grand_total < 500.00` | mmckay@cfc.co |
| Purchase Order | Sales Manager | `500.00 < doc.grand_total <= 1000.00` | arivers@cfc.co |
| Purchase Order | Accounts Manager | `doc.grand_total > 1000` | mbritt@cfc.co |
| | | | |
| Purchase Order | None | less than 200 |  |
| Purchase Order | Stock Manager  | `200.00 < doc.grand_total < 500.00` | mmckay@cfc.co |
| Purchase Order | Sales Manager | `500.00 < doc.grand_total <= 1000.00` | arivers@cfc.co |
| Purchase Order | Accounts Manager | `doc.grand_total > 1000` | mbritt@cfc.co |
| | | | |
| Customer | Sales Manager | `any([c.credit_limit != frappe.get_value('Customer Credit Limit', c.name, 'credit_limit') for c in doc.credit_limits])` | arivers@cfc.co |


### Purchase Invoice
In this example configuration, a Document Approval Rule exists that 


### Purchase Order (with custom Workflow)


### Non-submittable DocTypes
This exampled is based on company policy where a Sales Manager must approve changes to a Customer's credit limit. This script detects





## Additional configuration and improving user experience

Use a custom script to make a form read-only when it is in its "Pending Approval" state. This can only be achieved when a custom Workflow is used.

```javascript


```








