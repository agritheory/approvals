<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Usage

<div class="byline">
  Tyler Matteson 2026-02-28
</div>

## Finding Documents That Need Approval

When someone submits a document that requires approval, the assigned approver knows through several channels:

- A ToDo appears in their ToDo list with a link to the document
- A notification may appear depending on notification settings
- If email reminders are configured, a daily email lists everything waiting

Open the document to review it and take action.

## Approving a Document

When a user opens a document awaiting their approval, an approval panel appears in the right sidebar. It shows each role or user that must approve, and whether they have done so.

Users with the required role see Approve and Reject buttons next to their approval.

To approve, review the document and click Approve.

The approval records immediately. If this was the last required approval, the document automatically submits and moves to Approved status. If other approvals are still pending, the document stays in its current state until everyone has approved.

## Rejecting a Document

When something is wrong with a document, click Reject.

Depending on workflow settings, a reason explaining what needs to be fixed may be required. This comment is added to the document so the creator knows what to address.

Rejection does several things:

- Moves the document back to Draft through the workflow
- Clears all approvals that were already recorded (everyone needs to re-approve after changes)
- Notifies the document owner

The owner can then edit the document and resubmit for approval.

## Adding User Approvals

Sometimes a document needs review from someone outside the normal approval roles. This might be a subject matter expert, a department head for a special case, or a colleague covering for someone.

Any user can be added as an approver on a specific document. They appear in the approval panel alongside the role-based approvals. The document does not proceed until they have also approved.

The added user automatically receives read and write access to the document if they do not already have it.

## Understanding the Approval Panel

The sidebar panel shows the status of each required approval.

Pending approvals show who the approval is assigned to. "You" means it is waiting on the current user.

Completed approvals show who approved, with a checkmark.

User approvals (those added for a specific document) appear with the user's name instead of a role name.

## How Assignment Works

When a user submits a document for approval, the system evaluates all matching rules and assigns approvers.

If a rule has a specific Primary Assignee, that user always receives the assignment. Otherwise, the system rotates through users who have the required role, distributing work evenly over time.

The assigned user receives a ToDo. However, any user with the required role can approve. Assignment handles notification and tracking, not restriction.

## After All Approvals

Once every required approval is recorded:

- Submittable documents (like Purchase Order) automatically submit
- Non-submittable documents save with Approved status
- The workflow state updates accordingly

No manual action is needed to finalize the document after the last approval.
