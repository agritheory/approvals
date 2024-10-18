# CHANGELOG


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


## v14.2.2 (2024-07-24)

### Continuous Integration

* ci: install playwright before running tests (#58) ([`4042765`](https://github.com/agritheory/approvals/commit/404276548465c0e9053db3be1f8631d9e9bcd86f))

### Fixes

* fix: translate approval labels (#61)

Co-authored-by: Rohan Bansal <rohan@agritheory.dev> ([`29ce726`](https://github.com/agritheory/approvals/commit/29ce726f5939bffed95554ed8ae7897433b0c58a))

### Refactoring

* refactor: pyproject.toml to poetry (#49)

* refactor: pyproject.toml to poetry

* fix: add pytest-cov as a dev dependency ([`92cb558`](https://github.com/agritheory/approvals/commit/92cb55844209efe29f58d89360767a5e0bbee770))

* refactor: added typing (#31)

* refactor: added typing

* refactor: added typing

* refactor: added typing in document approval rule ([`50e8077`](https://github.com/agritheory/approvals/commit/50e8077004cdb9fa5fdab333a336c3ebabf5efac))

### Unknown

* Draft: feat: confirm to submit for doctypes where workflow does not exist (#48)

* feat: confirm to submit for doctypes where workflow does not exist

* fix: use string substitution

* wip: add playwright

* fix: update test case for test_non_workflow_approval

---------

Co-authored-by: Tyler Matteson <tyler@agritheory.com> ([`32f180d`](https://github.com/agritheory/approvals/commit/32f180d568785d28603735d725f5c4cd3196b2e9))

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

Co-authored-by: Rohan Bansal <rohan@agritheory.dev> ([`a9abbe8`](https://github.com/agritheory/approvals/commit/a9abbe85d81e926dfddef3a5539500e7a0d4a426))


## v14.2.1 (2024-07-08)

### Chores

* chore: fix backport ([`ad4bfa2`](https://github.com/agritheory/approvals/commit/ad4bfa24210fdd4a042b0de54a3558defc078393))

* chore: backport ([`2a11834`](https://github.com/agritheory/approvals/commit/2a11834ca863cbe1136cf95c6ba975b457a8df15))

### Continuous Integration

* ci: fix version numbering (#30) ([`2caf35a`](https://github.com/agritheory/approvals/commit/2caf35a9a7ddbd1c2c98a9163ff9cd0c376b13e4))

### Fixes

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

Co-authored-by: Rohan Bansal <rohan@agritheory.dev>
Co-authored-by: Tyler Matteson <tyler@agritheory.com> ([`3b16714`](https://github.com/agritheory/approvals/commit/3b167143d74558b4cef2ade136f5a6981cb9f356))

### Unknown

* Merge pull request #33 from agritheory/fix_backport

chore: fix backport ([`2b307c7`](https://github.com/agritheory/approvals/commit/2b307c76a78ffc8f2f30d2e746c8d2f40d2df49a))

* Merge pull request #32 from agritheory/backport

chore: backport ([`4c62a18`](https://github.com/agritheory/approvals/commit/4c62a18353c2b93fe2572683dae6a3f5c34be706))


## v14.2.0 (2024-07-02)

### Chores

* chore: conform code changes (#2)

* chore: conform code changes

* chore: port v13 changes

* wip: integrate workflow status ([`4c5c641`](https://github.com/agritheory/approvals/commit/4c5c6410b6b571e15e9c4d236cdaddf61fe1d4b8))

### Continuous Integration

* ci: remove testing artifacts, fix cache and hrms errors (#8) ([`6373545`](https://github.com/agritheory/approvals/commit/63735454c6cdf1c3a39574c24a4cef8fc7cbdefd))

* ci: migrate to Python semantic release (#7)

* ci: migrate to Python semantic release

* ci: refactor test workflow to accommodate db logger

* ci: create yarn.lock file

* ci: cache fix test ([`2980408`](https://github.com/agritheory/approvals/commit/298040846a52c3e369b5e2767749421f4f3acd5e))

### Features

* feat: format vue files to composition API (v14) (#23)

* feat: use vite as builder for approvals

* ci: update pytest runner

* fix: update approvals file type

* fix: handle errors

* ci: update runner dependencies

* fix: include css, reverse show/hide of status

---------

Co-authored-by: Rohan Bansal <rohan@agritheory.dev>
Co-authored-by: Tyler Matteson <tyler@agritheory.com> ([`82ddfce`](https://github.com/agritheory/approvals/commit/82ddfce82c552d447e41bcef3bbbb4e21345350b))

### Fixes

* fix: handle case where fallback approver is not set (#25)

* fix: handle case where fallback approver is not set

* fix: throw error on missing fallback approval role

---------

Co-authored-by: Rohan Bansal <rohan@agritheory.dev>
Co-authored-by: Tyler Matteson <tyler@agritheory.com> ([`ebed7f1`](https://github.com/agritheory/approvals/commit/ebed7f1d14c81346eeb01429bea00972f35f471d))

* fix: enable server script before creating invoices (#22)

Co-authored-by: Rohan Bansal <rohan@agritheory.dev> ([`c99c9c2`](https://github.com/agritheory/approvals/commit/c99c9c27ddcc866cc1e5ed161ed5bd0086ed9578))


## v1.0.0 (2023-06-08)

### Chores

* chore: prettier ([`0eb602d`](https://github.com/agritheory/approvals/commit/0eb602d0d80e7afc9ba67f3c4d0ac3f078c356ef))

* chore: black codebase ([`8604520`](https://github.com/agritheory/approvals/commit/860452040ad55ce9b769c079098ca760d654dd06))

### Continuous Integration

* ci: add lint and release ([`2595bf2`](https://github.com/agritheory/approvals/commit/2595bf2517c8448280f4fa1b952ddabafb1ed60f))

### Documentation

* docs: update readme ([`84566ac`](https://github.com/agritheory/approvals/commit/84566ac4abce9dd2c39d67142aa0fdf1870ca5ea))

### Features

* feat: add function to dismiss onboarding in tests ([`b0a4a31`](https://github.com/agritheory/approvals/commit/b0a4a316690dc249b9056dba7498376b38bfe3f5))

* feat: keep test purchase invoices as drafts ([`2094b05`](https://github.com/agritheory/approvals/commit/2094b05eb3e2e85ce6fa07459ed9e9d2c1b83729))

* feat: update test client script to load Vue components ([`66cc58d`](https://github.com/agritheory/approvals/commit/66cc58d44a6202988ce993acd9111c687fad1f01))

* feat: add more test scenarios ([`1431239`](https://github.com/agritheory/approvals/commit/14312393af26f5bee47bc6b7c7762eace4811735))

* feat: prevent disabled rules from being applied ([`a1f628a`](https://github.com/agritheory/approvals/commit/a1f628a7d7fe6c69eddf30a91f2210553472385d))

* feat: add detail to instructions ([`3979cce`](https://github.com/agritheory/approvals/commit/3979cce16bc754ed8d420688e923ae56b06e114a))

* feat: Initialize App ([`3ec2926`](https://github.com/agritheory/approvals/commit/3ec292695c9a96fbd6b9505fcf0395b20e6ad9ba))

### Fixes

* fix: re-word remove approver dialog title ([`459cc9b`](https://github.com/agritheory/approvals/commit/459cc9bd772b466eaede3fab84c4bdb1bb565a4e))

* fix: flip docstatus flag ([`8d92d74`](https://github.com/agritheory/approvals/commit/8d92d742346a602815217efd8bfc92605e857f25))

### Testing

* test: iterating on CI ([`ad1abb3`](https://github.com/agritheory/approvals/commit/ad1abb3ed9e0569edd9aa982657915d8b73e8ef5))

* test: iterating on CI ([`2189f81`](https://github.com/agritheory/approvals/commit/2189f8139a57023984eb14eb70536efc06452c63))

* test: iterating on CI ([`aeeb5cf`](https://github.com/agritheory/approvals/commit/aeeb5cf80e041ccccd4153e61fa74350acd1a728))

* test: iterating on CI ([`6756329`](https://github.com/agritheory/approvals/commit/6756329fd3c35def5a4374aa5e439ce0dc0c0d2b))

* test: iterating on CI ([`745da97`](https://github.com/agritheory/approvals/commit/745da971b7ded966d9ffebd65c38bda8957e14be))

* test: iterating on CI ([`d23c261`](https://github.com/agritheory/approvals/commit/d23c261f83751f3364b89491487eea7ab125af08))

* test: iterating on CI ([`3738b78`](https://github.com/agritheory/approvals/commit/3738b78cd360b3f9b656c61da02609905d451822))

* test: iterating on CI ([`91ad1ca`](https://github.com/agritheory/approvals/commit/91ad1ca14e6dc5bbdbb5dcc63a3066f665bae1e0))

* test: iterating on CI ([`f0493c6`](https://github.com/agritheory/approvals/commit/f0493c654ac1f5be568a8f035cb7ab1d6ac2db3d))

* test: iterating on CI ([`8da625f`](https://github.com/agritheory/approvals/commit/8da625ffe66c1874cb2433f38e97065ee951fe7a))

* test: iterating on CI ([`774db0c`](https://github.com/agritheory/approvals/commit/774db0cae5507e2856225c1885e8069ae5b01789))

* test: iterating on CI ([`28228e3`](https://github.com/agritheory/approvals/commit/28228e3f31ebbce36cbf01c50e84ba338379430a))

* test: add other apps in CI ([`56c4209`](https://github.com/agritheory/approvals/commit/56c420982aee0b6a0b1ef2cf190b61e144ac2b4e))

### Unknown

* Merge pull request #4 from agritheory/v14_dx

V14 dx ([`c74193a`](https://github.com/agritheory/approvals/commit/c74193af2ca543abed725358dc8d1e4ac3d941fb))

* Merge pull request #1 from agritheory/test_fixes

Test fixes ([`57bdcdb`](https://github.com/agritheory/approvals/commit/57bdcdb160f58f25d9acb1b72715914087c77ecd))

* Update pyproject.toml ([`a365983`](https://github.com/agritheory/approvals/commit/a365983fe9b05e9473e4a2f4b071500123fc0e82))

* initial commit ([`fc6b94c`](https://github.com/agritheory/approvals/commit/fc6b94c41178ad0c58ad3dd017e1156abaeae21d))
