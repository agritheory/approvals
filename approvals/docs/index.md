<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Approvals

<div class="byline">
  Rohan Bansal, Cursor, fproldan, Ishwarya, Myuddin Khatri, Heather Kusmierz, and Tyler Matteson 2026-10-04
</div>

Approvals adds conditional sign-off to business documents in ERPNext. An administrator decides which documents need approval and who should give it. For example, a company might require a manager's approval on every Purchase Invoice over $1,000, or a sales manager's approval whenever a customer's credit limit changes. When a document matches, the app assigns the right people, collects their approvals, and then submits the document or moves it to its approved workflow state.

The app works with submittable documents such as Purchase Order and Purchase Invoice, with or without a Workflow. It also works with documents that are never submitted, such as Customer, when paired with a Workflow.

## Design Philosophy

Approval rules route documents to roles, not to people. People change positions, leave the organization, and take time off. Roles persist. When the organization changes, the approval rules keep working.

People still matter when a specific document needs a specific person. Approvers can bring an extra person into a single document, or hand an assignment to a colleague while they are away, without changing the rules for every other document.

## Documentation

### [Usage](usage.md)

Approvers work from the Pending Approvals drawer in the desk navbar. It lists everything waiting on the current user and shows every required approval on the open document. This page covers reviewing, approving, and rejecting documents. It also covers adding an extra approver to a document, reassigning an approval to a colleague, and removing an approver who is no longer needed.

### [Configuration](configuration.md)

Administrators create Document Approval Rules that decide which documents need approval and which role approves them. This page covers rule conditions, assignment, fallback approvers, reminder emails, and how approvals work with and without a Workflow.

### [Extending Approvals](extending.md)

Developers can add names to rule conditions, supply approvers from their own data, change who may manage approvers, and build links into the drawer from custom templates.
