# Testing Strategy

The project values test quality over raw coverage percentage.

A test is useful only if it can fail when the business rule is broken.

## 1. Required testing mindset

Do not write tests only to increase coverage.

Every test should protect one of these:

- business rule
- data integrity rule
- role/permission rule
- workflow/status rule
- API contract
- validation rule
- negative path
- regression from a completed slice

## 2. Minimum test categories per slice

Each slice should define which of the following apply:

1. Backend unit tests for business rules.
2. API tests for success paths.
3. API tests for negative/failure paths.
4. Database migration tests or migration verification.
5. Role/permission tests.
6. Validation tests for mandatory and invalid fields.
7. Business event and workflow status tests where applicable.
8. Frontend smoke tests for main screens.
9. Human UI acceptance checklist.
10. Regression checks to confirm previous slices still work.

## 3. Slice acceptance rule

A slice is not accepted merely because automated tests pass.

A slice is accepted only when:

- relevant automated tests pass;
- the human UI acceptance checklist passes;
- the contract docs match the implemented behavior;
- no unrelated files/modules were changed without justification;
- previous completed slice flows still work.

## 4. Backend test expectations

Backend tests should cover:

- service-layer rules;
- route-level request/response behavior;
- validation failures;
- permission failures;
- event creation where relevant;
- repository behavior where database integration matters.

Avoid tests that only check that a function exists.

**Today's date in a test (9 October 2026).** A test module that dates what it sends or expects from today takes `TODAY`
from `backend/tests/business_day_test_support.py` and holds the server to it with a module-scoped, autouse fixture
around `held_to_the_test_day()`. Never read the clock at import (`datetime.now(...)`, `date.today()`): a run collected
before midnight in India and still running after it then expects yesterday while the server answers today, as
GitHub Actions run 37824561035 did. A module that compares what the server derives from when a record was made - the
day a machine was added, an allocation recorded - names that service's clock to `held_to_the_test_day()`, or, for a
row PostgreSQL stamps itself, makes it inside `dated_on_the_test_day(table)`.

## 5. API test expectations

For each implemented route, test at least:

- successful request;
- invalid request;
- not-found case where applicable;
- unauthorized or forbidden case where role rules apply;
- response shape.

## 6. Database test expectations

For migrations:

- migration applies cleanly;
- key constraints exist;
- required seed data is available;
- rollback strategy is considered where practical.

Verify migrations against a local Docker PostgreSQL instance (ADR-028). Prefer an empty database,
because PostgreSQL applies DDL transactionally: a failed migration rolls back completely, so a
clean upgrade from empty is the meaningful check.

`backend/tests/test_postgresql_dialect_regression.py` covers the TE-2B conversion itself: paging,
boolean filtering/updates, UTC timestamp writing, single-row lookups, `COALESCE`, business-reference
concatenation and case normalization, plus static guards against reintroduced T-SQL.

## 7. Frontend test expectations

Initial frontend testing may be light, but every UI slice must at minimum support manual smoke testing.

Frontend checks should verify:

- page loads;
- data from API is displayed;
- form validation appears;
- save/cancel behavior is understandable;
- errors are visible to user;
- navigation is clear.

Since TE-2A, `npm test` runs Vitest. The route-table tests (`frontend/src/routes.test.ts`) are the
current automated frontend coverage: they run React Router's own matching against the real route
objects, so a removed route, a renamed URL segment, a renamed dynamic parameter or a route wired to
the wrong page module fails there. A slice that adds or changes a public URL must update that table
and its tests. `npm run typecheck` and `npm run build` remain part of the frontend gate.

*Reconciled 8 October 2026 (TB-1 REP-1, TB1-903):* the route-table tests are no longer the only ones.
`npm test` now runs 28 Vitest files (33 on 12 October 2026): the route table, the shared components' helpers, and the pages'
state modules - the pure functions each page keeps beside it (`*State.ts`). None renders a component:
the frontend still has no component-test capability (`DEFERRED_REQUIREMENTS.md`, "Frontend
component-test capability"; TB-1 TB1-700, package CS-10).

## 8. Human UI testing requirement

Each slice must be small enough for a human to test in about 10-20 minutes.

The acceptance file must specify:

- test user;
- test role;
- starting URL;
- test data;
- positive path;
- negative path;
- expected result;
- notes for defects or confusion.

## 9. Regression discipline

Before accepting a slice, run the regression checklist for previously completed slices.

At minimum, confirm:

- application starts;
- login still works;
- health endpoint works;
- previously accepted UI flow still loads;
- no previous API contract is broken.

## 10. Coverage

Coverage may be measured later, but no slice should be accepted only because it reaches a percentage.

If coverage is introduced, use it as a warning signal, not as the definition of quality.

## 11. Reusable smoke-test data and Playwright regression (TE-1)

TE-1 adds a reusable smoke-test data harness and a thin Playwright regression suite. See `docs/agent/technical-enablement/TE_1_REUSABLE_SMOKE_FIXTURES_PLAYWRIGHT_REGRESSION_FOUNDATION.md` for full detail. Summary for future test-writing agents:

- `backend/tooling/smoke_data` (invoked via `docker compose exec backend python -m tooling.smoke_data ...`, or `scripts/smoke-data.ps1`) seeds named scenarios by calling the same service-layer functions the real API routes use, so business validations and lifecycle guards run for real. It is testing/tooling code only, never imported by `app.main` and never reachable through a public API route.
- The scenario catalogue includes `accepted-offer-no-work-order`, `accepted-offer-with-work-order`, `rejected-offer`, `revision-requested`, `blocked-handoff`, `core-regression-bundle`, (Slice 6O.1) `supplementary-offer-draft`, `change-quotation-draft`, `supplementary-offer-lifecycle`, `related-offer-regression-bundle`, and (Slice 6O.2) `work-order-amendment-received`, `commercial-amendment-with-change-quotation`, `work-order-amendment-regression-bundle`, plus (Slice 7D Part 3) `work-order-contract-period`, which builds a Work Order with three lines - one with two billing-terms periods, one with terms on a different basis, one with none - for the contract-dates and copy-terms screen check. WRR-001 added `work-order-resource-requirements` - a Work Order with a crane requirement and a manlift requirement on different lines, and a third line left for the tester - and a sixth record set to `core-regression-bundle`, `resource_requirement_target`, which the resource-requirement Playwright spec adds a requirement to. ERT-1 added `equipment-plum-import` - invented models, an invented Plum report already confirmed, and a second invented report in the manifest for the tester to upload - and the same as a seventh record set, `equipment_reference_target`, which the equipment Playwright spec uploads, maps, reads, pairs and confirms. Its cleanup is by provenance: the uploaded report's import by its fingerprint, machines by the import that brought them in, value rules by the import they were recorded on, mappings by the model names the run's reports carry. It refuses, deleting nothing, when anything it did not make depends on what it did. ERT-2 added to the same scenario a second crane model with two cranes and kit held for it - boom inserts, a counted counterweight set, a hook block model with no piece yet; cleanup removes the pieces of the run's kit models, including those added on screen, and refuses when a kit model it did not make fits one of its crane models. ELG-1 added to it a second wheeled crane whose carrier is paired when the first report is confirmed, with certificates and their copies on the carrier and the crane but no load test - so it cannot be allocated until one is recorded - the second crawler crane's road papers marked not applicable, and a sling held for the crawler cranes with its examinations; the Playwright spec `equipment-certificates.spec.ts` records the load test and marks the first crawler. Cleanup removes the run's certificates, marks, stored decisions and copies by the run's assets they are on, and refuses, deleting nothing, when a stored decision about a machine the run did not bring in used one of the run's assets. 8A core added to the same record set four invented 250 t crawler cranes - two that can be allocated, one only with a warning, one that cannot - with kit held for their model (a hook block, a counted counterweight set, inserts and a sling that cannot go), and a scenario `equipment-allocation` with, as the core bundle's eighth record set, `allocation_target`: a Work Order whose line's site is in Maharashtra, not a central-government site, with a requirement for two crawler cranes of at least 200 t and nothing allocated. ELG-2 added to the same record set two invented 80 t crawlers - one whose papers run out in 20, 10 and 5 days with a load test run out, one held on a job of its own - with a sling held for them, and, as the core bundle's ninth record set (also in `equipment-allocation`), `reminder_target`: a Work Order in Gujarat with that crawler held from 12 days ahead, its insurance running out before the job and its sling, listed on the first Trip (Own Load), running out during it. The Playwright spec `equipment-alerts.spec.ts` reads the Alerts as Operations and Management and marks a reminder seen; it never saves a reminder setting, which would stay in the shared database. Cleanup removes every "seen" mark on the run's assets, allocations and kit lines, whoever made it. The Playwright spec `equipment-allocation.spec.ts` allocates, lists kit, replaces and frees. Cleanup removes the allocations of the run's requirements - made by anyone, later - with their trips, kit lines and stored decisions, and refuses, deleting nothing, when an allocation of a requirement the run did not make holds or held one of the run's machines or pieces of kit. Because a confirmed Plum report is the whole fleet, `equipment-plum-import`, `equipment-allocation` and `core-regression-bundle` seed only on a database that holds no equipment machine and no waiting report preview, and refuse before writing anything otherwise - run them, and the E2E suite, where no real machines have been imported. TE-7 added `hiring-uat-seeded`, the Hiring user test's practice data for its own site (`docs/uat-hiring/`): four invented customers whose Work Orders and an offer show sites in Gujarat, in Maharashtra and on central-government land, every eligibility answer, kit on trips, a replaced and a freed machine, and every reminder stage on the first day. Like the other equipment scenarios it seeds only on an empty fleet; `test_hiring_uat_smoke_data.py` checks its cleanup leaves every table it wrote as it found it. HOL-1 added `holiday-calendar`, the holiday calendar's screen check - a Work Order with a contract from 1 December 2026 to 30 November 2027, lines in Gujarat and Maharashtra and one with no site, and no calendar started, so the tester sets up 2027 on a test site - and, as the core bundle's tenth record set, `holiday_calendar_target`: a year of PBL's holiday calendar in the harness's own years (2095 to 2099, the latest free one; refused, writing nothing, when none is free) with a Work Order over it, which `holiday-calendar.spec.ts` reads, adds to and changes. The calendar is shared, so the harness never starts a year anyone might keep: its cleanup removes the run's years by provenance, whoever changed them later, and the backend tests use 2090 to 2094. CS-05a added, as the core bundle's eleventh record set, `stale_save_target`: a Draft offer with one line, which `offer-stale-save.spec.ts` edits from two tabs - the second tab's save of the offer and of the line is refused beside its own Save button. CS-05c added the twelfth, `submitted_lock_target`: a Submitted offer with one line, whose lines `submitted-offer-lock.spec.ts` finds locked, then open once it starts a revised offer; cleanup removes that revision with the run's offer. TE-8 (the user-test restart, 9 October 2026) added `hiring-uat-fleet`, the Hiring test site's starting data: `hiring-uat-seeded`'s fleet and PBL's holiday calendar for this year and the next, marked complete, and nothing else; it refuses where a machine is held or either year is started, and `test_hiring_uat_fleet_smoke_data.py` checks its cleanup the same way. See the harness's own `scenarios` command for the current list.
- Cleanup is manifest-driven, FK-order-safe and idempotent (`cleanup --run-id <id>` or `cleanup --manifest <path>`). It never uses a loose name-prefix match as its only safety check.
- `e2e/` is an isolated Playwright workspace (its own `package.json`, pinned `@playwright/test` version, own `playwright.config.ts`) run only through the Docker Compose `e2e` profile (`docker compose --profile e2e run --rm e2e`, normally via `scripts/run-e2e.ps1`). It is never part of default `docker compose up -d` and never bundled into the production frontend image.
- Playwright is repeatable regression coverage for the specific flows its scenarios seed. It does not replace backend business-rule tests, exploratory browser smoke testing of new behavior, or user manual UAT.
- New Playwright scenarios should extend the existing scenario catalogue and manifest shape rather than inventing a second seeding mechanism. Do not recreate the generic terminal-status bypass that Slice 6M.1 closed; scenarios must reach `ACCEPTED`/`REJECTED` only through the real Customer Response action.
- Slice 6O.1 established the durable pattern for a technical-enablement extension layered on TE-1: a second, independently seeded/cleaned manifest run (own run id, own JSON file, own env var) alongside `core-regression-bundle` rather than merging record keys into the existing bundle, plus ownership-based cleanup discovery (a new record's foreign key back to a record the run created) for anything a Playwright test creates live that the seed-time manifest never knew about. Slice 6O.2 followed the same pattern with a third manifest (`work-order-amendments.json`) rather than reusing the related-offer manifest, because its record shapes (an amendment plus its lines, with a live-status commercial-basis dependency) did not fit naturally into the existing bundle. Extend this pattern rather than inventing a new one; only add a new manifest when a scenario's records are genuinely self-contained, as both 6O.1 and 6O.2 were.
- Slice 6P (a documentation/fixture-tooling package, not a numbered business slice) added `vendor-demo-bundle`, the harness's first scenario touching Leads, and a `demo_meta` manifest field used only by that scenario. It reused the same ownership-discovery cleanup pattern for a new case: a seeded-but-unconverted Lead can be converted live through the UI, creating an Opportunity/Account the seed-time manifest never knew about; `cleanup.py` now discovers those by `source_lead_id` ownership before deleting the Lead, the same way it already discovered live-created Work Orders and related offers. It also added a `python -m tooling.smoke_data status --run-id|--manifest` read-only command (reusable beyond this slice) and a separate, non-destructive `@demo-preflight` Playwright suite (`e2e/tests/demo-preflight.spec.ts`) run only via `--grep`, never as part of the ordinary full regression run. Future agents adding demo scenarios should extend `vendor-demo-bundle` and its builders rather than inventing a second demo-data mechanism.

## 12. Continuous integration (TE-2CI.1)

`.github/workflows/te-2ci-validation.yml` reproduces the validation path above as automated checks
on pull requests and manual dispatch (not again on `main` after a merge, since 12 October 2026 - the
pull request's run already proved the merged tree; `AGENTS.md`, "Pull requests and CI cost"): backend regression against PostgreSQL 17,
an empty-database migration to the single Alembic head, the frontend typecheck/test/build gate,
contract-fixture validation, tracked-secret and dependency checks, and the Docker Compose plus
Playwright end-to-end path. Six validation jobs feed one aggregate job, and the single stable
required check is:

```text
Required validation
```

Two of those checks are new standard-library scripts that any agent can run locally, and should be
run whenever a change touches contract fixtures or adds a file that could carry a credential. Both
enumerate the proposed tree (`git ls-files --cached --others --exclude-standard`), so a new file in
a working branch is checked before it is committed while ignored paths such as `.env` are never
opened. Each has its own standard-library `unittest` suite under `scripts/tests/`, which CI runs
before the validator itself:

```bash
python scripts/validate_contract_fixtures.py
python scripts/check_tracked_secrets.py
python -m unittest discover -s scripts/tests
```

CI does not replace any layer described above. It runs the same commands a developer runs, so the
role split between backend tests, Playwright, exploratory browser testing and user manual UAT is
unchanged. In particular, `retries: 0` in `e2e/playwright.config.ts` stays at zero in CI: a flaky
test must be diagnosed, not retried.

TE-2CI is complete and hosted-verified. The whole workflow runs green on GitHub-hosted runners,
with Playwright at 12 passed / 9 skipped / 0 failed and `retries: 0` unchanged — the same counts as
locally, so the hosted environment introduces no flakiness and none is masked by a retry.
`Required validation` has been demonstrated both ways: success when every job succeeds, failure
when one is cancelled.

**As of 17 August 2026, required-check registration and enforced branch protection are active.** A
GitHub repository ruleset technically gates integration into `main` on the named `Required
validation` check having reported for the exact commit, a current-with-`main` pull request, and no
force pushes or deletion. GitHub's own required-status-check semantics accept `success`, `skipped`
and `neutral` alike as satisfying that check; PBL's own stronger invariant — the check must
conclude `success` specifically — is met by the workflow's `if: always()` aggregate design, not by
GitHub ruleset semantics alone (see ADR-031, "Required check semantics"). This is recorded as
**ADR-031**. Before that date, this configuration was not possible on the repository's
then-current GitHub plan; ADR-029 records the interim manual merge gate that applied the stricter
success-only rule by process instead, and remains the accurate historical record of that period.
See `docs/agent/ARCHITECTURE_DECISIONS.md` (ADR-031) and
`docs/agent/technical-enablement/TE_2CI_GITHUB_ACTIONS_VALIDATION_FOUNDATION.md`.

## 13. Review versus deterministic testing

A review of the code - by a person or a tool - looks for what nobody yet knew to test: the omitted case, an unintended
interaction, a wrong assumption. It never replaces a deterministic test. A change that passes review with no test
protecting its core rule is not adequately tested; the review should name that gap.

```text
Deterministic tests (backend pytest, migration checks, frontend build/tests)
    given this input, this exact output or this exact refusal.

Review
    the omitted case, not the miscalculated one.

Runtime / hosted CI
    behaviour that depends on the environment and that reading the code cannot establish: a defect
    in how a Compose profile mounted a volume was missed by every static review of it and caught only
    by running Docker Compose on GitHub's runners.

Playwright
    the specific UI flows its scenarios cover; not a general UI regression suite.

Exploratory / manual UAT
    the separate business-usability review described in UI_UAT_GUIDELINES.md.
```

For a workflow or status change, prefer tests that walk every stored status against every operation that changes
status, so a guard is proved at runtime and not only by reading. For scripts, tooling and CI, test every documented
way of running them where practical, rather than assuming another platform behaves the same; `scripts/tests/` does this
for `ci-compose-cleanup.sh`, the contract-fixture validator and the tracked-secret checker.
