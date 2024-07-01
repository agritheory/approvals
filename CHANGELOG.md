# CHANGELOG

## v15.1.0 (2024-07-01)

### Feature

* feat: format vue files to composition API (v15) (#20)

* feat: format vue files to composition API

* feat: use vite as builder for approvals

* fix: typing issue

* fix: include css, reverse show/hide of status

* feat: add naming format for Document Approval Rule

* fix: handle case where fallback approver is not set

---------

Co-authored-by: Rohan Bansal &lt;rohan@agritheory.dev&gt;
Co-authored-by: Tyler Matteson &lt;tyler@agritheory.com&gt; ([`bd44a6b`](https://github.com/agritheory/approvals/commit/bd44a6b7b39e766d18893d7b015c3571e0e03a87))

## v15.0.1 (2024-06-13)

### Ci

* ci: update conftest for json (#12) ([`8d43518`](https://github.com/agritheory/approvals/commit/8d435186242f47f0842a0abc22487f0bd80a7bc5))

* ci: update versions, mypy to pre-commit ([`dda57eb`](https://github.com/agritheory/approvals/commit/dda57eb073eb8ceb357b47229eef922cd953bfba))

* ci: add app names in get-app call ([`546dc18`](https://github.com/agritheory/approvals/commit/546dc18d47cfe549277d345be043bec06d18704f))

### Fix

* fix: enable server script before creating invoices (#19)

Co-authored-by: Rohan Bansal &lt;rohan@agritheory.dev&gt; ([`baa41d5`](https://github.com/agritheory/approvals/commit/baa41d54e38d4a36d6bc25b4627eddb3d4a66d5a))

## v15.0.0 (2024-03-19)

### Ci

* ci: remove extra echos ([`d39e09a`](https://github.com/agritheory/approvals/commit/d39e09a410ae3611eb05e4aac957606ce6c23469))

* ci: enable server scripts ([`a164d6a`](https://github.com/agritheory/approvals/commit/a164d6a049402d85236416d49ae58b35cd62049f))

* ci: remove resolve dependencies ([`e1fa6ad`](https://github.com/agritheory/approvals/commit/e1fa6ad2d2f793b008a5651aceb6932aca0a23ef))

* ci: update for v-15 ([`a3aed39`](https://github.com/agritheory/approvals/commit/a3aed398a308171ee541ade62ebd26220fe34e32))

* ci: remove testing artifacts, fix cache and hrms errors (#8) ([`6373545`](https://github.com/agritheory/approvals/commit/63735454c6cdf1c3a39574c24a4cef8fc7cbdefd))

* ci: migrate to Python semantic release (#7)

* ci: migrate to Python semantic release

* ci: refactor test workflow to accommodate db logger

* ci: create yarn.lock file

* ci: cache fix test ([`2980408`](https://github.com/agritheory/approvals/commit/298040846a52c3e369b5e2767749421f4f3acd5e))

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
