<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# Changelog

This changelog was automatically generated from GitHub releases and pull requests.

## Unreleased

Users can now import custom functions into conditions using a hook. This allows for more flexibility and customization in document approval rules.

## [v15.3.3] - 2025-07-29

### Release Notes

## v15.3.3 (2025-07-29)

### Bug Fixes

- Create comments for on adding or removing approvals ([#77](https://github.com/agritheory/approvals/pull/77), [`c2da2ba`](https://github.com/agritheory/approvals/commit/c2da2bafe28f9e784375deff77df8756273a9901))

---

**Detailed Changes**: [v15.3.2...v15.3.3](https://github.com/agritheory/approvals/compare/v15.3.2...v15.3.3)


### Changes from Pull Requests

Added comments for adding or removing approvals and corrected the set_status method in apply_workflow. Fixed issues with file handling.
  _Source: PR #77_

## [v15.3.2] - 2025-07-29

### Release Notes

## v15.3.2 (2025-07-29)

### Bug Fixes

- Add cache busting to approvals ([#75](https://github.com/agritheory/approvals/pull/75), [`ecbda50`](https://github.com/agritheory/approvals/commit/ecbda507750ff14118285552943062dcfd5d4adf))

- Modify assets.json directly ([#75](https://github.com/agritheory/approvals/pull/75), [`ecbda50`](https://github.com/agritheory/approvals/commit/ecbda507750ff14118285552943062dcfd5d4adf))

---

**Detailed Changes**: [v15.3.1...v15.3.2](https://github.com/agritheory/approvals/compare/v15.3.1...v15.3.2)


### Changes from Pull Requests

Added cache busting to approvals workflow. Now, changes in Vue files automatically clear cache and reload UI without manual intervention.
  _Source: PR #75_

Document Approval Rules can now be configured to bypass when Auto Repeat is enabled and populated. This allows for more flexible approval processes in certain scenarios.
  _Source: PR #80_

## [v15.3.1] - 2025-07-29

### Release Notes

## v15.3.1 (2025-07-29)

### Bug Fixes

- Create comments for on adding or removing approvals ([#56](https://github.com/agritheory/approvals/pull/56), [`1a42391`](https://github.com/agritheory/approvals/commit/1a42391c913e8028d8b8d5f3c31d5d0d09b569d8))

- Create comments on adding or removing approvals ([#56](https://github.com/agritheory/approvals/pull/56), [`1a42391`](https://github.com/agritheory/approvals/commit/1a42391c913e8028d8b8d5f3c31d5d0d09b569d8))

---

**Detailed Changes**: [v15.3.0...v15.3.1](https://github.com/agritheory/approvals/compare/v15.3.0...v15.3.1)


### Changes from Pull Requests

Added comments for adding or removing approvals. Fixed issues in approval workflow and linting scripts.
  _Source: PR #56_

Added notifications when adding an approver. Fixed issues in linting and pytest workflows. Updated pre-commit configuration.
  _Source: PR #78_

Added a new GitHub workflow for generating changelogs automatically. This simplifies the process of documenting code changes and updates.
  _Source: PR #82_

## [v15.3.0] - 2025-07-22

### Release Notes

## v15.3.0 (2025-07-22)

### Bug Fixes

- Error messages ([#72](https://github.com/agritheory/approvals/pull/72), [`0bf5ea3`](https://github.com/agritheory/approvals/commit/0bf5ea32ac7183ef83e0d25efe26322c04d09624))

### Features

- Dry option to apply ([#72](https://github.com/agritheory/approvals/pull/72), [`0bf5ea3`](https://github.com/agritheory/approvals/commit/0bf5ea32ac7183ef83e0d25efe26322c04d09624))

- Test condition ([#72](https://github.com/agritheory/approvals/pull/72), [`0bf5ea3`](https://github.com/agritheory/approvals/commit/0bf5ea32ac7183ef83e0d25efe26322c04d09624))

- Validate condition field ([#72](https://github.com/agritheory/approvals/pull/72), [`0bf5ea3`](https://github.com/agritheory/approvals/commit/0bf5ea32ac7183ef83e0d25efe26322c04d09624))

---

**Detailed Changes**: [v15.2.0...v15.3.0](https://github.com/agritheory/approvals/compare/v15.2.0...v15.3.0)


### Changes from Pull Requests

Backported validation for Python in condition fields for Document Approval Rules. Fixed errors and improved test coverage.
  _Source: PR #72_

## [v15.2.0] - 2024-10-17

### Release Notes

## v15.2.0 (2024-10-17)

### Features

* feat: require rejection reason in workflow (#73)

Co-authored-by: fproldan <franciscoproldan@gmail.com> ([`a33e1d9`](https://github.com/agritheory/approvals/commit/a33e1d97e266bd0cacc250f38f8a36f538c6afb7))

### Refactoring

* refactor: pyproject to poetry(v15) (#71)

* refactor: pyproject to poetry(v15)

* refactor: pyproject to poetry(v14)

* fix: remove js dependency check

---------

Co-authored-by: Tyler Matteson <tyler@agritheory.com> ([`f3ce58a`](https://github.com/agritheory/approvals/commit/f3ce58af1df7e0fa83ca8c946abe22384d7d8b0a))

* refactor: added typing(v15) (#46) ([`f92a21d`](https://github.com/agritheory/approvals/commit/f92a21db34a67558e9ed1479d0c95f29c3379ee2))

### Unknown

* [Backport] Reminder Email (#47)

* chore: backport

* chore: backport ([`087fb1f`](https://github.com/agritheory/approvals/commit/087fb1f79e380fa973f60873afb63c04939b1975))

* Workflow integration v15 (#44)

* wip: add workflow integration

* wip: add workflow integration

* wip: approval workflow with tests

* fix: add typing to Vue files

* fix: tests cleanup

* fix: build entry point

* fix: clean up python typing

---------

Co-authored-by: Rohan Bansal <rohan@agritheory.dev> ([`9c92ca0`](https://github.com/agritheory/approvals/commit/9c92ca0a08c6e0823d740ed9f70dbef9722787d4))


### Changes from Pull Requests

Users can now provide a reason when rejecting workflows. This helps in better understanding and managing rejections.
  _Source: PR #73_

Refactored project configuration to use Poetry for better dependency management. Added pytest-coverage for code coverage reports and updated pre-commit hooks for code quality checks.
  _Source: PR #71_

## [v14.2.3] - 2024-10-17

### Release Notes

## v14.2.3 (2024-10-17)

### Continuous Integration

* ci: change backport config (#67)

* ci: change backport config

* fix: change pre-commit config ([`248b30d`](https://github.com/agritheory/approvals/commit/248b30df8242f40dc82f8546e8cc95f132b57477))

### Fixes

* fix: check for docstatus if doc is submittable (#63)

* fix: check for docstatus if doc is submittable

* fix: remove property setter for ToDo field order

* fix: combine if statement checks ([`fef7d42`](https://github.com/agritheory/approvals/commit/fef7d42458c0d48e3ceea2a8a675ecdb048a5bd2))

### Testing

* test(fix): non workflow test (#64)

* test(fix): non workflow test

* test(fix): non workflow test

* fix: remove headless

* fix: restore invoice number

* fix: wait for selector

* fix: added timeout before query selector

* fix: added timeout before query selector

* fix: added timeout before query selector

* fix: remove wait for selector

* fix: set password on user creation for test data

* fix: use page.locator

* fix: build app before running tests

* fix: remove client script and add approval doctypes on create test data

* fix: add init script before navigating to page

* fix: asset path

* ci: build before bench start ([`b19003d`](https://github.com/agritheory/approvals/commit/b19003da1533500622f037c30acd277f8b17e744))

### Unknown

* Validate Python in condition field Document Approval Rule  (#69)

* feat: validate condition field

* feat: test condition

* feat: dry option to apply

* fix: error messages ([`8b30643`](https://github.com/agritheory/approvals/commit/8b30643ace782e64b49703445ae0052ff578019e))

* Rejection Notification User (#65)

* feat: rejection user

* fix: permission

* fix: fallback rejection user

* feat: approval_doctypes in create_document_approval_settings

* feat: wip notifications

* chore: fix customization, prettier

* feat: rejection, notifications

* chore: fix for mypy

* fix: disable notifications ([`6b08331`](https://github.com/agritheory/approvals/commit/6b08331ca9e71596478dc23fb2106d39d149d0de))

* Remove client script requirement (#57)

* wip: remove client script requirement

* fix: minor fixes

---------

Co-authored-by: Rohan Bansal <rohan@agritheory.dev> ([`3781ab1`](https://github.com/agritheory/approvals/commit/3781ab16325ecfbca26598104bd7484a72583ee5))


### Changes from Pull Requests

Backported reminder email feature. Fixed merge conflicts and added new files for improved document approval process.
  _Source: PR #47_

## [v14.2.2] - 2024-07-24

### Release Notes

# v14.2.2 (2024-07-24)

## Ci

* ci: install playwright before running tests (#58) ([`4042765`](https://github.com/agritheory/approvals/commit/404276548465c0e9053db3be1f8631d9e9bcd86f))

## Fix

* fix: translate approval labels (#61)

Co-authored-by: Rohan Bansal &lt;rohan@agritheory.dev&gt; ([`29ce726`](https://github.com/agritheory/approvals/commit/29ce726f5939bffed95554ed8ae7897433b0c58a))

## Refactor

* refactor: pyproject.toml to poetry (#49)

* refactor: pyproject.toml to poetry

* fix: add pytest-cov as a dev dependency ([`92cb558`](https://github.com/agritheory/approvals/commit/92cb55844209efe29f58d89360767a5e0bbee770))

* refactor: added typing (#31)

* refactor: added typing

* refactor: added typing

* refactor: added typing in document approval rule ([`50e8077`](https://github.com/agritheory/approvals/commit/50e8077004cdb9fa5fdab333a336c3ebabf5efac))

## Unknown

* Draft: feat: confirm to submit for doctypes where workflow does not exist (#48)

* feat: confirm to submit for doctypes where workflow does not exist

* fix: use string substitution

* wip: add playwright

* fix: update test case for test_non_workflow_approval

---------

Co-authored-by: Tyler Matteson &lt;tyler@agritheory.com&gt; ([`32f180d`](https://github.com/agritheory/approvals/commit/32f180d568785d28603735d725f5c4cd3196b2e9))

* Reminder Email (#27)

* fix: query and added missing commit

* feat: Pending Approval Email Template

* feat: add pending approval email template

* feat: Document Approval Rule link in ToDo

* fix: remove scheduler hook

* fix: ToDo in UserDocumentApproval

* feat: send reminder email logic

* feat: send reminder email logic

* feat: email reminder hour settings

* chore: merge

* chore: merge

* fix: settings layout ([`02c613e`](https://github.com/agritheory/approvals/commit/02c613e57f4ac3ec599b6a6f46b693babfe93ccb))

* Workflow Integration (#39)

* wip: add workflow integration

* wip: workflow integration

* wip: approval workflow with tests

* fix: add typing to Vue files

---------

Co-authored-by: Rohan Bansal &lt;rohan@agritheory.dev&gt; ([`a9abbe8`](https://github.com/agritheory/approvals/commit/a9abbe85d81e926dfddef3a5539500e7a0d4a426))

### Changes from Pull Requests

Integrated workflow approval system with tests. Fixed typing issues in Vue files and cleaned up tests. Added new test cases for approval workflows. Renamed `approvals.ts` to `approvals.ts`. Removed unused test file `test_tmp.py`.
  _Source: PR #44_

Added type annotations to improve code clarity and maintainability. Fixed issues with document approval rules.
  _Source: PR #46_

## [v14.2.1] - 2024-07-08

### Release Notes

# v14.2.1 (2024-07-08)

## Chore

* chore: fix backport ([`ad4bfa2`](https://github.com/agritheory/approvals/commit/ad4bfa24210fdd4a042b0de54a3558defc078393))

* chore: backport ([`2a11834`](https://github.com/agritheory/approvals/commit/2a11834ca863cbe1136cf95c6ba975b457a8df15))

## Ci

* ci: fix version numbering (#30) ([`2caf35a`](https://github.com/agritheory/approvals/commit/2caf35a9a7ddbd1c2c98a9163ff9cd0c376b13e4))

## Fix

* fix: allow approvers to view non-role documents (#26)

* fix: handle case where fallback approver is not set

* fix: throw error on missing fallback approval role

* fix: allow approvers to view non-role documents

* fix: use wildcard permissions for approvals

* fix: recursion permission checks

* fix: share documents with approvers

* fix: replace SQL with ORM

* fix: remove permission controller hook

* style: pre-commit fixes

* fix: alias add to add_share

---------

Co-authored-by: Rohan Bansal &lt;rohan@agritheory.dev&gt;
Co-authored-by: Tyler Matteson &lt;tyler@agritheory.com&gt; ([`3b16714`](https://github.com/agritheory/approvals/commit/3b167143d74558b4cef2ade136f5a6981cb9f356))

## Unknown

* Merge pull request #33 from agritheory/fix_backport

chore: fix backport ([`2b307c7`](https://github.com/agritheory/approvals/commit/2b307c76a78ffc8f2f30d2e746c8d2f40d2df49a))

* Merge pull request #32 from agritheory/backport

chore: backport ([`4c62a18`](https://github.com/agritheory/approvals/commit/4c62a18353c2b93fe2572683dae6a3f5c34be706))

## [v14.2.0] - 2024-07-02

### Release Notes

fix: handle case where fallback approver is not set (#25)

* fix: handle case where fallback approver is not set

* fix: throw error on missing fallback approval role

---------

Co-authored-by: Rohan Bansal <rohan@agritheory.dev>
Co-authored-by: Tyler Matteson <tyler@agritheory.com>

### Changes from Pull Requests

Updated Vue files to use Composition API for better organization and improved code readability. Fixed issues with CSS styling and reversed show/hide logic in status components. Switched to Vite as the build tool for approvals.
  _Source: PR #20_

## [v15.0.1] - 2024-06-13

### Release Notes

# v15.0.1 (2024-06-13)

## Ci

* ci: update conftest for json (#12) ([`8d43518`](https://github.com/agritheory/approvals/commit/8d435186242f47f0842a0abc22487f0bd80a7bc5))

* ci: update versions, mypy to pre-commit ([`dda57eb`](https://github.com/agritheory/approvals/commit/dda57eb073eb8ceb357b47229eef922cd953bfba))

* ci: add app names in get-app call ([`546dc18`](https://github.com/agritheory/approvals/commit/546dc18d47cfe549277d345be043bec06d18704f))

## Fix

* fix: enable server script before creating invoices (#19)

Co-authored-by: Rohan Bansal &lt;rohan@agritheory.dev&gt; ([`baa41d5`](https://github.com/agritheory/approvals/commit/baa41d54e38d4a36d6bc25b4627eddb3d4a66d5a))

### Changes from Pull Requests

Fixed an issue where server scripts were disabled when creating invoices. Enabled server scripts before invoice creation to resolve this problem.
  _Source: PR #19_

Updated `conftest.py` to use JSON for configuration.
  _Source: PR #12_

## [v15.0.0] - 2024-03-19
**Initial Version-15 Release**

### Release Notes

Initial version-15 release

## [v14.1.0] - 2023-06-08

### Release Notes

# 14.1.0 (2023-06-08)


### Bug Fixes

* flip docstatus flag ([8d92d74](https://github.com/agritheory/approvals/commit/8d92d742346a602815217efd8bfc92605e857f25))
* re-word remove approver dialog title ([459cc9b](https://github.com/agritheory/approvals/commit/459cc9bd772b466eaede3fab84c4bdb1bb565a4e))


### Features

* add detail to instructions ([3979cce](https://github.com/agritheory/approvals/commit/3979cce16bc754ed8d420688e923ae56b06e114a))
* add function to dismiss onboarding in tests ([b0a4a31](https://github.com/agritheory/approvals/commit/b0a4a316690dc249b9056dba7498376b38bfe3f5))
* add more test scenarios ([1431239](https://github.com/agritheory/approvals/commit/14312393af26f5bee47bc6b7c7762eace4811735))
* Initialize App ([3ec2926](https://github.com/agritheory/approvals/commit/3ec292695c9a96fbd6b9505fcf0395b20e6ad9ba))
* keep test purchase invoices as drafts ([2094b05](https://github.com/agritheory/approvals/commit/2094b05eb3e2e85ce6fa07459ed9e9d2c1b83729))
* prevent disabled rules from being applied ([a1f628a](https://github.com/agritheory/approvals/commit/a1f628a7d7fe6c69eddf30a91f2210553472385d))
* update test client script to load Vue components ([66cc58d](https://github.com/agritheory/approvals/commit/66cc58d44a6202988ce993acd9111c687fad1f01))
