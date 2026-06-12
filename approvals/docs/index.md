<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Approvals

<div class="byline">
  Tyler Matteson 2026-03-02
</div>

Approvals is a document approval workflow app for Frappe and ERPNext. It allows organizations to define conditional approval rules for business documents based on configurable criteria. It supports submittable documents (Purchase Order, Purchase Invoice) and non-submittable documents through workflow configuration.

## Design Philosophy

The app routes documents to roles, not people. People change positions, leave organizations, and take time off. Roles persist. When organizational changes happen, approval logic stays intact.

## Documentation

### [Configuration](configuration.md)

Administrators set up approval rules that define which roles must approve each document type and under what conditions. Rules use Jinja templates to match documents based on field values like amounts, accounts, or other criteria. Workflows control approval states, reapproval conditions, and field updates on approval. Global settings control fallback approvers and email reminder timing.

### [Usage](usage.md)

Users work with approvals through a sidebar panel on configured DocTypes. From this panel, a user can approve or reject documents, and add other users as approvers when needed. The panel does not appear on DocTypes without approval rules.
