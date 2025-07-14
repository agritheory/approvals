<!-- Copyright (c) 2025, AgriTheory and contributors
For license information, please see license.txt-->

## Customer Credit Limit Approval Workflow Example

This example demonstrates how the workflow and document approval rules work for the `Customer` doctype when managing credit limits.

### Scenario

1. **Create a Customer**: A new Customer is created with a specific credit limit.
2. **Send for Approval**: The document is sent for approval using the workflow action "Send for Approval". The approval rule for `Customer` and `Sales Manager` is triggered.
3. **Approve**: The Sales Manager approves the document. The workflow state changes to `Approved`.
4. **Change Credit Limit**: Later, a user edits the Customer and changes the credit limit. Upon saving, the workflow state automatically changes back to `Draft` (because the approval rule's condition detects a change in credit limit).
5. **Re-approval Required**: The document must go through the approval workflow again for the new credit limit to be approved.

### How it works

- The workflow for `Customer` has states: `Draft`, `Pending Approval`, and `Approved`.
- The `Document Approval Rule` for `Customer` and `Sales Manager` is enabled and has a condition that checks if any credit limit has changed:

  ```python
  any([
      c.credit_limit != frappe.get_value('Customer Credit Limit', c.name, 'credit_limit')
      for c in doc.credit_limits
  ])
  ```

- When the credit limit is changed and the document is saved, the rule triggers, and the workflow state is set to `Draft`.
- The document must be sent for approval and approved again before it is considered fully approved.

> **Note:** This test assumes the workflow and approval rule are set up as shown above. Adjust field names and logic as per your actual implementation.
> Workflow
> {
> "name":"Customer",
> "owner":"Administrator",
> "creation":"2024-07-17 13:34:20.596129",
> "modified":"2024-07-17 13:40:17.807270",
> "modified_by":"Administrator",
> "docstatus":0,
> "idx":0,
> "workflow_name":"Customer",
> "document_type":"Customer",
> "is_active":1,
> "override_status":0,
> "send_email_alert":0,
> "workflow_state_field":"workflow_state",
> "doctype":"Workflow",
> "transitions":[
>
> > {
> > "name":"01gui08d70",
> > "owner":"Administrator",
> > "creation":"2024-07-17 13:34:20.596129",
> > "modified":"2024-07-17 13:40:17.807270",
> > "modified_by":"Administrator",
> > "docstatus":0,
> > "idx":1,
> > "state":"Draft",
> > "action":"Save",
> > "next_state":"Draft",
> > "allowed":"All",
> > "allow_self_approval":1,
> > "parent":"Customer",
> > "parentfield":"transitions",
> > "parenttype":"Workflow",
> > "doctype":"Workflow Transition",
> > "**unsaved":1
> > },
> > {
> > "name":"01gu0atn9d",
> > "owner":"Administrator",
> > "creation":"2024-07-17 13:34:20.596129",
> > "modified":"2024-07-17 13:40:17.807270",
> > "modified_by":"Administrator",
> > "docstatus":0,
> > "idx":2,
> > "state":"Draft",
> > "action":"Send for Approval",
> > "next_state":"Pending Approval",
> > "allowed":"All",
> > "allow_self_approval":1,
> > "parent":"Customer",
> > "parentfield":"transitions",
> > "parenttype":"Workflow",
> > "doctype":"Workflow Transition",
> > "**unsaved":1
> > },
> > {
> > "name":"01gugjgh3a",
> > "owner":"Administrator",
> > "creation":"2024-07-17 13:34:20.596129",
> > "modified":"2024-07-17 13:40:17.807270",
> > "modified_by":"Administrator",
> > "docstatus":0,
> > "idx":3,
> > "state":"Pending Approval",
> > "action":"Approve",
> > "next_state":"Approved",
> > "allowed":"All",
> > "allow_self_approval":1,
> > "parent":"Customer",
> > "parentfield":"transitions",
> > "parenttype":"Workflow",
> > "doctype":"Workflow Transition",
> > "**unsaved":1
> > },
> > {
> > "name":"01gunadm3o",
> > "owner":"Administrator",
> > "creation":"2024-07-17 13:34:20.596129",
> > "modified":"2024-07-17 13:40:17.807270",
> > "modified_by":"Administrator",
> > "docstatus":0,
> > "idx":4,
> > "state":"Approved",
> > "action":"Save",
> > "next_state":"Draft",
> > "allowed":"All",
> > "allow_self_approval":1,
> > "parent":"Customer",
> > "parentfield":"transitions",
> > "parenttype":"Workflow",
> > "doctype":"Workflow Transition",
> > "**unsaved":1
> > },
> > {
> > "name":"01gu1vobp2",
> > "owner":"Administrator",
> > "creation":"2024-07-17 13:34:20.596129",
> > "modified":"2024-07-17 13:40:17.807270",
> > "modified_by":"Administrator",
> > "docstatus":0,
> > "idx":5,
> > "state":"Approved",
> > "action":"Save",
> > "next_state":"Approved",
> > "allowed":"All",
> > "allow_self_approval":1,
> > "parent":"Customer",
> > "parentfield":"transitions",
> > "parenttype":"Workflow",
> > "doctype":"Workflow Transition",
> > "**unsaved":1
> > },
> > {
> > "docstatus":0,
> > "doctype":"Workflow Transition",
> > "name":"04nbb1u4kr",
> > "**unsaved":1,
> > "owner":"Administrator",
> > "allow_self_approval":1,
> > "parent":"Customer",
> > "parentfield":"transitions",
> > "parenttype":"Workflow",
> > "idx":6,
> > "state":"Pending Approval",
> > "action":"Reject",
> > "next_state":"Draft",
> > "allowed":"All",
> > "creation":"2024-07-17 13:34:20.596129",
> > "modified":"2024-07-17 13:40:17.807270",
> > "modified_by":"Administrator"
> > }
> > ],
> > "states":[
> >
> > > > {
> > > > "name":"01gu4f804j",
> > > > "owner":"Administrator",
> > > > "creation":"2024-07-17 13:34:20.596129",
> > > > "modified":"2024-07-17 13:40:17.807270",
> > > > "modified_by":"Administrator",
> > > > "docstatus":0,
> > > > "idx":1,
> > > > "state":"Draft",
> > > > "doc_status":"0",
> > > > "is_optional_state":0,
> > > > "avoid_status_override":0,
> > > > "allow_edit":"All",
> > > > "parent":"Customer",
> > > > "parentfield":"states",
> > > > "parenttype":"Workflow",
> > > > "doctype":"Workflow Document State",
> > > > "**unsaved":1
> > > > },
> > > > {
> > > > "name":"01gurmn3nh",
> > > > "owner":"Administrator",
> > > > "creation":"2024-07-17 13:34:20.596129",
> > > > "modified":"2024-07-17 13:40:17.807270",
> > > > "modified_by":"Administrator",
> > > > "docstatus":0,
> > > > "idx":2,
> > > > "state":"Pending Approval",
> > > > "doc_status":"0",
> > > > "is_optional_state":0,
> > > > "avoid_status_override":0,
> > > > "allow_edit":"All",
> > > > "parent":"Customer",
> > > > "parentfield":"states",
> > > > "parenttype":"Workflow",
> > > > "doctype":"Workflow Document State",
> > > > "**unsaved":1
> > > > },
> > > > {
> > > > "name":"01gu3tclpi",
> > > > "owner":"Administrator",
> > > > "creation":"2024-07-17 13:34:20.596129",
> > > > "modified":"2024-07-17 13:40:17.807270",
> > > > "modified_by":"Administrator",
> > > > "docstatus":0,
> > > > "idx":3,
> > > > "state":"Approved",
> > > > "doc_status":"0",
> > > > "is_optional_state":0,
> > > > "avoid_status_override":0,
> > > > "allow_edit":"All",
> > > > "parent":"Customer",
> > > > "parentfield":"states",
> > > > "parenttype":"Workflow",
> > > > "doctype":"Workflow Document State",
> > > > "\_\_unsaved":1
> > > > }
> > > > ],
> > > > "approval_state":"Approved"
> > > > }

Document Approval Rule
{
"name":"033lc8oo7s",
"owner":"Administrator",
"creation":"2024-07-17 13:37:02.951572",
"modified":"2024-07-17 13:41:37.472312",
"modified_by":"Administrator",
"docstatus":0,
"idx":0,
"approval_doctype":"Customer",
"approval_role":"Sales Manager",
"enabled":1,
"primary_assignee":"arivers@cfc.co",
"assign_users":1,
"condition":"True # any([c.credit_limit != frappe.get_value('Customer Credit Limit', c.name, 'credit_limit') for c in doc.credit_limits])",
"title":"Customer - Sales Manager",
"doctype":"Document Approval Rule"
}
