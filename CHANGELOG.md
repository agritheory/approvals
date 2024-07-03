# CHANGELOG

## v14.2.0 (2024-07-02)

### Chore

* chore: conform code changes (#2)

* chore: conform code changes

* chore: port v13 changes

* wip: integrate workflow status ([`4c5c641`](https://github.com/agritheory/approvals/commit/4c5c6410b6b571e15e9c4d236cdaddf61fe1d4b8))

### Ci

* ci: remove testing artifacts, fix cache and hrms errors (#8) ([`6373545`](https://github.com/agritheory/approvals/commit/63735454c6cdf1c3a39574c24a4cef8fc7cbdefd))

* ci: migrate to Python semantic release (#7)

* ci: migrate to Python semantic release

* ci: refactor test workflow to accommodate db logger

* ci: create yarn.lock file

* ci: cache fix test ([`2980408`](https://github.com/agritheory/approvals/commit/298040846a52c3e369b5e2767749421f4f3acd5e))

### Feature

* feat: format vue files to composition API (v14) (#23)

* feat: use vite as builder for approvals

* ci: update pytest runner

* fix: update approvals file type

* fix: handle errors

* ci: update runner dependencies

* fix: include css, reverse show/hide of status

---------

Co-authored-by: Rohan Bansal &lt;rohan@agritheory.dev&gt;
Co-authored-by: Tyler Matteson &lt;tyler@agritheory.com&gt; ([`82ddfce`](https://github.com/agritheory/approvals/commit/82ddfce82c552d447e41bcef3bbbb4e21345350b))

### Fix

* fix: handle case where fallback approver is not set (#25)

* fix: handle case where fallback approver is not set

* fix: throw error on missing fallback approval role

---------

Co-authored-by: Rohan Bansal &lt;rohan@agritheory.dev&gt;
Co-authored-by: Tyler Matteson &lt;tyler@agritheory.com&gt; ([`ebed7f1`](https://github.com/agritheory/approvals/commit/ebed7f1d14c81346eeb01429bea00972f35f471d))

* fix: enable server script before creating invoices (#22)

Co-authored-by: Rohan Bansal &lt;rohan@agritheory.dev&gt; ([`c99c9c2`](https://github.com/agritheory/approvals/commit/c99c9c27ddcc866cc1e5ed161ed5bd0086ed9578))

## v14.1.0 (2023-06-08)

### Chore

* chore: prettier ([`0eb602d`](https://github.com/agritheory/approvals/commit/0eb602d0d80e7afc9ba67f3c4d0ac3f078c356ef))

* chore: black codebase ([`8604520`](https://github.com/agritheory/approvals/commit/860452040ad55ce9b769c079098ca760d654dd06))

### Ci

* ci: add lint and release ([`2595bf2`](https://github.com/agritheory/approvals/commit/2595bf2517c8448280f4fa1b952ddabafb1ed60f))

### Documentation

* docs: update readme ([`84566ac`](https://github.com/agritheory/approvals/commit/84566ac4abce9dd2c39d67142aa0fdf1870ca5ea))

### Feature

* feat: add function to dismiss onboarding in tests ([`b0a4a31`](https://github.com/agritheory/approvals/commit/b0a4a316690dc249b9056dba7498376b38bfe3f5))

* feat: keep test purchase invoices as drafts ([`2094b05`](https://github.com/agritheory/approvals/commit/2094b05eb3e2e85ce6fa07459ed9e9d2c1b83729))

* feat: update test client script to load Vue components ([`66cc58d`](https://github.com/agritheory/approvals/commit/66cc58d44a6202988ce993acd9111c687fad1f01))

* feat: add more test scenarios ([`1431239`](https://github.com/agritheory/approvals/commit/14312393af26f5bee47bc6b7c7762eace4811735))

* feat: prevent disabled rules from being applied ([`a1f628a`](https://github.com/agritheory/approvals/commit/a1f628a7d7fe6c69eddf30a91f2210553472385d))

* feat: add detail to instructions ([`3979cce`](https://github.com/agritheory/approvals/commit/3979cce16bc754ed8d420688e923ae56b06e114a))

* feat: Initialize App ([`3ec2926`](https://github.com/agritheory/approvals/commit/3ec292695c9a96fbd6b9505fcf0395b20e6ad9ba))

### Fix

* fix: re-word remove approver dialog title ([`459cc9b`](https://github.com/agritheory/approvals/commit/459cc9bd772b466eaede3fab84c4bdb1bb565a4e))

* fix: flip docstatus flag ([`8d92d74`](https://github.com/agritheory/approvals/commit/8d92d742346a602815217efd8bfc92605e857f25))

### Test

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
