# Baseline manifest

What this copy is, what it was made from, and what was left out or changed in making it.

## Identity

| Item | Value |
| --- | --- |
| Made from | PBL's internal repository, branch `main`, commit `f8bba7ce` (13 October 2026) |
| Prepared | 13 October 2026 |
| Delivered as | A single commit with no history. Its fingerprint (the commit's tree identifier and the archive's SHA-256) is given in the letter that accompanied your copy, and kept by PBL; a file cannot hold the fingerprint of the copy that contains it |
| Database | One chain of migrations, head `20260908_0055` |
| Frozen handoff contract | SHA-256 `7954b4558a12578cc98bcb851b48a302ce7a155b249969d2b4b817af4bd10130` (history in `docs/continuity/NEXT_STEPS.md`) |
| Scope | The CRM. Equipment Hiring is included for context and its tests, outside this package (`VENDOR_START_HERE.md`) |

## Left out of this copy

1,291 files of PBL's internal working material and Hiring detail. None is needed to build, run or test the system, and the automatic
checks were adjusted wherever they referred to one.

| What | Files | Why | What replaces it |
| --- | --- | --- | --- |
| The technical review's working papers (`docs/agent/tb-1/`) | 809 | Internal review material | Annex A lists what is still open |
| PBL's running notes (`docs/continuity/`, all but four) | 175 | Internal history | The package records; doc 01; the new `NEXT_STEPS.md` |
| Internal tooling records, a review benchmark, a hosting study, the test sites' deployment record, and proof and evidence folders (`docs/agent/technical-enablement/`) | 157 | Internal | The remaining technical-enablement records describe the tools you use |
| PBL's internal development tooling (`tools/devorch/`, `tools/review/`, `scripts/devorch-run-approved-script.ps1` and its test) | 75 | Internal | Not needed |
| Hosting files and runbooks for PBL's test sites (`deploy/uat/`, `docs/deployment/`, their test) | 21 | Specific to PBL's test servers | Docs 07 and 10 |
| Earlier plans and demonstration notes (`docs/planning/` but three, `docs/demo/`) | 19 | Superseded | The vendor documents. The three planning files the frozen contract names are kept |
| Two extracts of annexures withheld from the functional specification: billing rules and examples, tools and assets (`docs/reference/erp-source-extracts/`) | 2 | Equipment Hiring and asset detail the CRM does not need | Annexure 21's list of equipment types stays in the full-text extract |
| PBL's fleet list, used by one Hiring test, and that test (`backend/tests/fixtures/plum_vehicle_report_dummified_2026-09-24.csv`, `backend/tests/test_ert1_plum_report.py`) | 2 | Confidential, and Equipment Hiring | Not needed |
| PDF copies of the tester sheets (`docs/uat/`, `docs/uat-hiring/`) | 15 | Copies of the Markdown sheets, which are kept | The Markdown sheets |
| Internal planning and working notes (`docs/agent/PLAN.md`, `AGENT_HANDOFF.md`, `AGENT_WORKFLOW.md`, `SKILLS_AND_TOOLS.md`, PBL's internal working instructions), PBL's internal review procedures (four records in `docs/agent/architecture/`), the technical review's own slice record, two hosting studies (Slices 6C.2 and 6C.3) and the test sites' deployment acceptance | 16 | Internal | `VENDOR_START_HERE.md`, `AGENTS.md`, docs 07 and 08 |

## Written for this copy

| File | What it is |
| --- | --- |
| `VENDOR_START_HERE.md`, everything in `docs/vendor/` | New |
| `AGENTS.md` | Rewritten: the rules a change most often touches, under the headings the code cites |
| `docs/continuity/NEXT_STEPS.md` | Rewritten: the current status and the frozen contract's fingerprint history |
| `docs/continuity/OPEN_QUESTIONS.md` | Rewritten: PBL's decisions and the questions still open, with the same numbers |
| `README.md` | Pointers to this pack |

## Changed only for this copy

| Change | Where |
| --- | --- |
| Wording about outside systems made neutral; the names of tools used in PBL's internal process, local folder paths, internal repository names and test-site addresses replaced | About 60 records under `docs/` |
| Five internal architecture decisions shortened to a note, keeping their numbers (ADR-011, 012, 029, 034, 035) | `docs/agent/ARCHITECTURE_DECISIONS.md` |
| Rules documents adjusted to working with a vendor: the review step is PBL's reviewer; an internal review benchmark taken out of the testing strategy | `docs/agent/TESTING_STRATEGY.md`, `docs/agent/CODING_STANDARDS.md`, `docs/agent/UI_UAT_GUIDELINES.md`, `docs/agent/architecture/CONTRACT_REGISTRY.md`, `docs/agent/architecture/PRODUCTION_READINESS_GATES.md` |
| PBL's requirements documents given as clean copies: tracked changes accepted, review comments removed, author "PBL"; the text is unchanged from what the extracts read. The functional specification holds only annexures 1, 2, 3 and 21, and the full-text extract and the annexure index are cut to match | `docs/source/current/requirements/`, `docs/reference/erp-source-extracts/`; noted in `docs/source/SOURCE_DOCUMENT_REGISTER.md` |
| A dated note marking two early hosting studies as history | `docs/agent/FUTURE_SLICES.md` |
| The test sites' deployment checks removed from the automatic checks, with the files they checked | `.github/workflows/te-2ci-validation.yml`, `.gitattributes` |
| Pointers to removed documents replaced in the test-pack guides and runbooks | `docs/uat/`, `docs/uat-hiring/`, `db/notes/migration-rules.md` |
| **Code: no change in behaviour.** One comment line and one help text reworded | `frontend/src/layout/menuPreference.ts`, `backend/tooling/user_admin/cli.py` |
| **One test corrected.** It counted every offer version in the database, so the practice data of doc 07, step 6 made it fail; it now counts only the version it makes. The same correction goes to PBL's main line | `backend/tests/test_slice_9f_commercial_offer_versions.py` |

Every application file not listed here is exactly as it is at commit `f8bba7ce`.

## Known open issues

Annex A lists the open findings of the technical review; doc 03 sorts all the remaining work.

## Checked on this copy before delivery

Checked on 13 October 2026 in two ways: the full automatic checks on GitHub's Linux machines, on the branch this copy
was made from; and the sequence in doc 07, followed step by step on a Windows 11 laptop with Docker Desktop, from a
fresh copy of the delivered repository, on an empty database.

| Check | Linux (automatic checks) | Windows (doc 07, step by step) |
| --- | --- | --- |
| Database built from empty to one head | Passed | `20260908_0055 (head)` for both commands |
| Health, screens and sign-in | Passed | Health "ok"; screens answer; `admin1` signs in |
| Practice data (`vendor-demo-bundle`) | - | Loaded |
| Server tests | 3,567 passed | 3,564 passed, 2 skipped (they read documents the container does not hold), 1 failed: the test above, which the step 6 practice data tripped. Corrected in this copy; the corrected file passes on the same data, 12 of 12 |
| Screen type check, tests and build | Passed | Type check clean; 628 tests in 34 files passed; build succeeded |
| Repository checks | Passed | Contract fixtures passed; no committed-credential findings in 988 files; the scripts' 65 tests passed |
| Library check | Passed. The full report lists 18 known advisories in 3 Python libraries, all on the recorded accepted list; upgrading them is annex A, CS-15 | - |
| Browser walk-throughs | 39 passed, 9 skipped by design | 39 passed, 9 skipped by design; clean-up succeeded |
| Frozen handoff contract fingerprint | - | `7954b455...0130`, as recorded |
| No passwords, keys, personal data, internal addresses or tool names | - | None found. PBL's public website and support mailbox appear in one test, one code comment and the specification's own text |
