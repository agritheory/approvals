<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Usage

<div class="byline">
  Rohan Bansal, Cursor, fproldan, Ishwarya, Myuddin Khatri, Heather Kusmierz, and Tyler Matteson 2026-06-12
</div>

## Finding Documents That Need Approval

When someone saves a document that requires approval, the assigned approver knows through several channels:

- A ToDo appears in their ToDo list with a link to the document
- A notification may appear depending on notification settings
- If email reminders are configured, a daily email lists everything waiting

Open the document to review it and take action.

The approval sidebar appears only on DocTypes configured with at least one enabled Document Approval Rule. Other forms are unchanged.

## Approving a Document

When a user opens a document awaiting their approval, an approval panel appears in the right sidebar. It shows each role or user that must approve, and whether they have done so.

Users with the required role see Approve and Reject buttons next to their approval.

To approve, review the document and click Approve.

The approval records immediately. If this was the last required approval, the document finalizes automatically. Submittable documents (like Purchase Order or Purchase Invoice) submit. Non-submittable documents transition to the workflow's approved state. If other approvals are still pending, the document stays in its current state until everyone has approved.

On submittable documents **without a workflow**, the final approver sees a confirmation dialog before submit — **Permanently Submit {document name}?** — the same prompt ERPNext shows for a normal Submit action. Dismissing the dialog leaves the document in draft and does not record the approval.

Documents **with a workflow** do not show this dialog; the workflow handles state transitions when approvers act from the sidebar.

## Rejecting a Document

When something is wrong with a document, click Reject.

Depending on workflow settings, a reason explaining what needs to be fixed may be required. This comment is added to the document so the creator knows what to address.

Rejection does several things when a workflow is configured:

- Moves the document back to Draft through the workflow
- Clears all approvals that were already recorded (everyone needs to re-approve after changes)
- Notifies the document owner

When no workflow exists for the DocType, Reject does not change document status. Add a comment on the document or configure a workflow if you need structured reject-and-revise flows.

The owner can then edit the document and resubmit for approval.

## Adding User Approvals

Sometimes a document needs review from someone outside the normal approval roles. This might be a subject matter expert, a department head for a special case, or a colleague covering for someone.

Any user can be added as an approver on a specific document. They appear in the approval panel alongside the role-based approvals. The document does not proceed until they have also approved.

The added user automatically receives read and write access to the document if they do not already have it.

## Understanding the Approval Panel

The sidebar panel shows the status of each required approval.

**With a workflow**, the panel is active while the document is in the workflow's Approval State. The form is read-only for editing during that state. After approval completes and the document moves to another state, normal editing resumes.

**Without a workflow**, the panel is active on draft documents (`docstatus = 0`) that match at least one rule. The form stays editable until the document is submitted. Approvers can act from the sidebar at any time while the document remains in draft.

Pending approvals show who the approval is assigned to. "You" means it is waiting on the current user.

Completed approvals show who approved, with a checkmark.

User approvals (those added for a specific document) appear with the user's name instead of a role name.

## How Assignment Works

When a document is saved, the system evaluates all matching rules and assigns approvers. For DocTypes with a workflow, assignment also requires the document to be in the workflow's Approval State.

If a rule has a specific Primary Assignee, that user always receives the assignment. Otherwise, the system rotates through users who have the required role, distributing work evenly over time.

The assigned user receives a ToDo. However, any user with the required role can approve. Assignment handles notification and tracking, not restriction.

## After All Approvals

Once every required approval is recorded:

- Submittable documents (like Purchase Order or Purchase Invoice) automatically submit
- Non-submittable documents apply the workflow transition to the configured approved state and save
- Workflow state field updates and any configured state Update Field values are applied

On submittable documents without a workflow, the last approver confirms submit in a dialog before the document posts.

No manual **Submit** click is needed after the last sidebar approval when auto-submit applies.
