# TE-1 - Reusable Smoke-Test Fixtures and Playwright Regression Foundation

## Status

Implemented. Technical-enablement work package, not a numbered CRM business slice. Delivered on branch `technical-enablement-te1-smoke-fixtures-playwright-foundation`, layered on top of Slice 6O.

## Objective

Replace throwaway seed/cleanup scripts with a reusable, safe test-data harness; add a thin, deterministic Playwright regression suite for the stable prototype flow; establish repeatable validation commands; and add code review as a standard final gate for substantial slices.

## Architecture

### Backend smoke-data harness

```text
backend/tooling/smoke_data/
  __init__.py         package docstring; testing/tooling code only
  __main__.py          entrypoint for `python -m tooling.smoke_data`
  cli.py                argparse CLI: seed / cleanup / list-runs / scenarios
  manifest.py           Manifest dataclass, run-id generation/validation, manifest_version
  actors.py             resolves a seeded prototype user (default: sales1) as the acting user
  builders.py           one function per domain step, each calling the real service layer
  scenarios.py          named scenario catalogue, composed from builders.py
  cleanup.py            FK-safe, ownership-aware, idempotent cleanup
scripts/smoke-data.ps1  PowerShell wrapper; always runs Python inside the backend container
```

`backend/tooling/` is a sibling of `backend/app/` and `backend/tests/`, never imported by `app.main` and never reachable through any `/api` route (`backend/tests/test_smoke_data_harness.py::test_no_public_api_route_exposes_the_smoke_data_harness` asserts this directly). `backend/Dockerfile` gained one `COPY tooling ./tooling` line; `docker-compose.yml` gained a matching `./backend/tooling:/app/tooling` bind mount for the `backend` service, consistent with the existing `app`/`tests` mounts.

### Why service-layer calls, not raw SQL or HTTP

`builders.py` calls the exact same service functions the FastAPI routes call (`accounts.service.create_account`, `opportunities.service.create_opportunity` + `repair_opportunity_account`, `commercial_offers.service.create_commercial_offer` / `create_commercial_offer_line` / `create_commercial_offer_submission_evidence` / `create_commercial_offer_credit_review` / `mark_commercial_offer_submitted` / `create_commercial_offer_customer_response`, `work_orders.service.create_work_order_from_commercial_offer`), each opening its own `SessionLocal()` session (mirroring one-session-per-request semantics) and passing a real seeded `app_user.public_id` as `current_user_public_id`. This means every scenario runs through real business validation and lifecycle guards -- including the Slice 6M.1 terminal-status guard, since `ACCEPTED`/`REJECTED` are reached only through `create_commercial_offer_customer_response` (the Slice 6L Customer Response action), never through a direct status write. Service functions take a plain `current_user_public_id: str | None`, not a request-scoped auth object, so this works without going through HTTP or bypassing any FastAPI route dependency; authorization (role checks) lives in `routes.py`, not `service.py`, so this is a deliberate, documented trade-off for a trusted internal tooling script that never runs through the network -- not a security bypass.

`opportunities.service.create_opportunity` always creates an unlinked Opportunity (`business_party_id` forced `None`); the harness links it to the created Account via the existing `repair_opportunity_account` service call, the same repair path Slice 6B.1 built for humans repairing an unlinked Opportunity.

### Manifest format (`manifest_version: 1`)

```json
{
  "manifest_version": 1,
  "run_id": "te1-<8 hex chars>",
  "scenario": "core-regression-bundle",
  "created_at": "2026-07-12T13:38:36.93Z",
  "actor": {"public_id": "...", "username": "sales1"},
  "records": {
    "handoff_target": {
      "account": {"public_id": "...", "account_name": "TE1-SMOKE-<run_id> Account Handoff"},
      "opportunity": {"public_id": "...", "opportunity_name": "..."},
      "commercial_offer": {"public_id": "...", "offer_code": "CO-...", "line_public_id": "..."},
      "commercial_offer_status": "ACCEPTED",
      "work_orders": []
    }
  },
  "urls": {"handoff_target.commercial_offer": "http://localhost:3000/commercial-offers/..."},
  "notes": []
}
```

Every created record's display name is stamped `TE1-SMOKE-<run_id> ...` (see `manifest.data_tag`), making seeded rows trivially identifiable in the UI or a raw SQL query, and distinguishing them from ordinary demo/user data. `seed --json` prints only the manifest JSON to stdout (no mixed log lines); the human-readable summary mode is the default when `--json` is omitted.

### Scenario catalogue

| Scenario | What it produces |
| --- | --- |
| `accepted-offer-no-work-order` | Account -> Opportunity -> Offer + line -> submission evidence -> clean credit review -> `mark-submitted` -> `ACCEPTED_AWARDED` Customer Response. No Work Order. |
| `accepted-offer-with-work-order` | Same as above, plus the frozen Slice 6D.1 handoff (`create_work_order_from_commercial_offer`) performed explicitly. |
| `rejected-offer` | Same submission chain, then `REJECTED_LOST` Customer Response. |
| `revision-requested` | Same submission chain, then `REVISION_REQUESTED` Customer Response (status stays `SUBMITTED`). |
| `blocked-handoff` | Stops at `SUBMITTED` (no Customer Response yet), then calls the Work Order handoff and asserts it is rejected; the real backend error message becomes `records.blocked_handoff.blocked_reason`. If the handoff ever stops rejecting this, the scenario itself raises `RuntimeError` -- this is a live regression check, not a scripted fake blocker. |
| `core-regression-bundle` | Four independent record sets, so no two Playwright tests mutate the same Commercial Offer: `handoff_target` (accepted, no WO -- Test 1 creates one), `terminal_guard` (rejected -- Test 2), `existing_traceability` (accepted + WO already created -- Test 3), `read_only_view` (accepted + WO already created, separate instance -- Test 4). |

Extending the catalogue: add a new `_build_*` composition function in `scenarios.py` using the existing `builders.py` primitives, register it in `SCENARIOS`/`SCENARIO_DESCRIPTIONS`, and reuse the existing manifest shape (`account`/`opportunity`/`commercial_offer`/`commercial_offer_status`/`work_orders`) so cleanup and any future Playwright fixtures keep working unmodified.

### Cleanup safety: read TE-3 and TE-4 before changing it

The design described immediately below is TE-1's original and has since been rewritten twice.
Start from the later records:

- **TE-3** replaced one-level discovery calls with an ownership **closure**, and added deletes for
  the Slice 9C/9D/9E record types that have no declared foreign key to their parents.
- **TE-4** fixed what the closure still could not see, using a **mixed ownership rule**: parents
  by provenance - an Account the Opportunity repair flow *created* is ours, one it merely *linked*
  is not - and descendants by the approved downward cascade. It also fixed audit deletion, which
  matched on a public id alone across record types. **`status` still cannot certify a targeted
  cleanup**: a mechanism for that was built and then removed, for reasons recorded in the TE-4
  package document.

`docs/agent/technical-enablement/TE_3_UAT_SYNTHETIC_DATA_PACK.md` and
`docs/agent/technical-enablement/TE_4_CLEANUP_PROVENANCE.md`.

### Cleanup safety

`cleanup.py` requires either `--run-id <id>` (looked up from a locally-persisted manifest under `backend/.smoke-runs/`, gitignored) or `--manifest <path>`. Before touching the database it validates the full manifest shape (`manifest.validate_manifest_dict`: exact top-level keys, `manifest_version == 1`, well-formed `run_id`, non-empty `records`) and every collected public_id against a strict UUID regex, raising `CleanupValidationError` on anything that doesn't look like a genuine TE-1 manifest -- there is no loose name-prefix matching anywhere in the delete path.

Deletion order (children before parents, verified against the actual Alembic `FOREIGN KEY` constraints, none of which use `CASCADE`):

```text
crm_work_order_line -> crm_work_order -> commercial_offer_customer_response ->
commercial_offer_revision -> commercial_offer_credit_review ->
commercial_offer_submission_evidence -> commercial_offer_tc_clause ->
crm_commercial_offer_pricing_evidence -> crm_commercial_offer_line ->
crm_commercial_offer -> crm_opportunity -> business_party
```

`business_event` rows are deleted last by matching `record_public_id` (that table has no FK to any of the above -- deleting it is for tidiness, not required for FK safety).

**Real bug found and fixed during E2E validation:** a Playwright test can trigger the live Slice 6D.1 handoff through the UI for an offer seeded with `work_orders: []` (this is exactly what `accepted-offer-no-work-order` / Test 1 does on purpose). The resulting Work Order's public_id is never in the manifest. The first cleanup implementation looked up Work Orders to delete only by the manifest's own `work_orders` list, so it never found or deleted that live-created Work Order -- and then failed with an `fk_crm_work_order_line_offer_line` FK violation when it tried to delete the offer's line while an orphaned `crm_work_order_line` row still referenced it. Fixed by having cleanup discover *every* Work Order owned by a known offer (`crm_work_order.commercial_offer_id` is `NOT NULL`, so ownership-by-offer is a complete, safe cleanup key, not just the manifest's own list) via `cleanup._find_all_owned_work_order_ids`. Covered by `test_cleanup_discovers_a_work_order_created_after_seeding_and_not_recorded_in_the_manifest` and reproduced live in the E2E run that surfaced it.

Cleanup is idempotent: re-running it against an already-cleaned run reports zero deletions everywhere and exits `0` (`(no rows matched -- this run may already have been cleaned up; that is not an error)`), rather than raising. `cleanup --run-id` deliberately does **not** delete its local manifest file after a successful run, specifically so a repeated `cleanup --run-id` against the same run stays idempotent instead of failing with "manifest not found."

### Playwright suite

```text
e2e/
  package.json           pinned @playwright/test 1.61.1
  playwright.config.ts    globalSetup, timeouts, reporters, single chromium project
  tsconfig.json
  tests/
    fixtures/manifest.ts  reads MANIFEST_PATH, validates manifest_version
    fixtures/auth.ts      logs in through the real /login form
    global-setup.ts       warms every dynamic route the suite touches (see below)
    accepted-offer-handoff.spec.ts
    terminal-status-guard.spec.ts
    existing-work-order-traceability.spec.ts
    read-only-role.spec.ts
```

`docker-compose.yml` gained an `e2e` service guarded by `profiles: ["e2e"]`, using the official `mcr.microsoft.com/playwright:v1.61.1-noble` image (pinned to the exact same version as `@playwright/test` in `e2e/package.json`), bind-mounting `./e2e:/e2e` plus a named `e2e-node-modules` volume, and depending on `frontend`. It is not part of default `docker compose up -d`, is never built into the frontend production image, and requires no host Node.js -- `npm install && npx playwright test` both run inside the container.

**Why `globalSetup` existed (removed by TE-2A):** the frontend originally ran `next dev`, not a production build, so each dynamic route compiled on its first request. Without a warm-up, whichever spec ran first absorbed the combined first-compile cost of every route it touched and exceeded even a 60-second test timeout. `tests/global-setup.ts` logged in once and visited every route the suite would touch before any individual test's timer started -- an explicit deterministic one-time cost paid outside any test's budget, not a retry. TE-2A replaced the runtime with a pre-built Vite bundle served by `vite preview`, which has no per-route compile cost, so the file and its `globalSetup` registration were deleted. Retries remain `0` and no scenario or assertion changed.

Manifest handoff: `scripts/run-e2e.ps1` seeds `core-regression-bundle` on the host (`docker compose exec -T backend python -m tooling.smoke_data seed --scenario core-regression-bundle --json`), writes the JSON to the gitignored `e2e/.manifest/run.json`, and the `e2e` service's `MANIFEST_PATH=/e2e/.manifest/run.json` environment variable (set in `docker-compose.yml`) points every test at it via the bind mount -- no hard-coded UUIDs anywhere in `e2e/tests/*.spec.ts`. Cleanup afterwards uses `--run-id` against the backend's own locally-persisted manifest (`backend/.smoke-runs/`), not the copy under `e2e/.manifest/`, so the backend and E2E filesystems never need to share a mount.

### Authentication

Tests log in through the real `/login` form using documented prototype seed users (`admin1`, `sales1`, `readonly1` / `password` -- Alembic revision `20260629_0002` until 7 October 2026; since TB-1 TB1-203 the backend creates them when it starts with a development or CI `APP_ENV`, and the harness creates any it writes as, elsewhere, switched off with no password; also listed on the login page itself). `login()` in `tests/fixtures/auth.ts` waits for the "You are signed in as ..." line and checks that its "here" link goes to the Dashboard (`/`); where someone is already signed in, the sign-in page offers Sign out in place of the form, and `login()` signs out there first (28 September 2026); the login page does not redirect after success, so callers navigate to their target page explicitly afterward. No credentials are hard-coded beyond these already-public, non-production prototype defaults; no `.env` was read; no test-only login endpoint or bypass was added.

### Selector policy

No `data-testid` attributes exist anywhere in `frontend/app/` (confirmed by an explicit repo-wide search before writing any selector), and none were added -- every assertion targets real, stable UI text or ARIA roles already present from Slice 6O/6M.1 (`role="tab"`, button/link accessible names, exact heading and status text, table `role="row"`). No CSS class names, positional `nth()` calls, hard-coded database UUIDs (IDs always come from the manifest), or brittle XPath are used.

### Artifacts and Git hygiene

`.gitignore` gained:

```text
backend/.smoke-runs/
e2e/node_modules/
e2e/playwright-report/
e2e/test-results/
e2e/.manifest/
e2e/.auth/
```

`trace: "retain-on-failure"`, `screenshot: "only-on-failure"`, `video: "off"` in `playwright.config.ts` -- failure artifacts land under `e2e/test-results/` (bind-mounted to the host) only when a test fails.

## Tests and results

Backend: `backend/tests/test_smoke_data_harness.py`, 14 tests, all passing against the real dockerized SQL Server, each cleaning up after itself:

```text
test_seed_returns_valid_manifest_with_unique_run_ids
test_seeded_records_are_visibly_tagged
test_accepted_scenario_uses_customer_response_action_not_a_status_bypass
test_accepted_scenario_does_not_auto_create_a_work_order
test_accepted_with_work_order_uses_explicit_frozen_handoff_and_preserves_line_traceability
test_cleanup_discovers_a_work_order_created_after_seeding_and_not_recorded_in_the_manifest
test_rejected_scenario_is_non_actionable
test_blocked_handoff_scenario_reports_a_genuine_blocker
test_two_seed_runs_remain_isolated_and_cleanup_only_removes_the_selected_run
test_cleanup_is_idempotent
test_cleanup_rejects_malformed_manifest_and_run_id
test_cleanup_after_partial_setup_is_safe
test_cleanup_rejects_unrecognizable_manifest_records
test_no_public_api_route_exposes_the_smoke_data_harness
```

Full backend suite: 163 passed (149 pre-existing + 14 new), no regressions.

Frontend: clean `npm run build` passed (no frontend source changed by TE-1); `npm test` remains the pre-existing "not configured" placeholder.

E2E: two consecutive clean runs of `.\scripts\run-e2e.ps1`, each ending with `4 passed` and a successful cleanup report, run ids differing (`te1-cc48c5a2`, `te1-4d85af90`) and zero `TE1-SMOKE%`-tagged rows left in the database afterward both times. A simulated/real test failure during development (before the `globalSetup` warm-up and `actionTimeout` tuning existed) confirmed the `finally`-equivalent cleanup path in `scripts/run-e2e.ps1` runs and succeeds even when Playwright exits non-zero.

`/code-review` (medium effort, 4 parallel finder angles) ran against the full diff before commit and surfaced 9 CONFIRMED findings (a second cleanup-ownership gap, a PowerShell `$Args`/return-value bug, a missing timeout on `global-setup.ts`'s first navigation, an ambiguous Playwright label selector, an overly broad `except Exception`, dead code, and a broken documented example), all fixed. A third `.\scripts\run-e2e.ps1` run afterward passed all 4 tests in 1.1 minutes (run id `te1-184dac26`) -- the fastest of the three. Full detail: `docs/continuity/TE_1_REUSABLE_SMOKE_FIXTURES_PLAYWRIGHT_REGRESSION_FOUNDATION.md` and `docs/agent/acceptance/te-1-reusable-smoke-fixtures-playwright-regression-foundation-acceptance.md`.

## Known limitations

- The E2E suite covers exactly the four flows named in the TE-1 scope: the Slice 6D.1 handoff, the Slice 6M.1 terminal-status UI guard, existing Work Order traceability, and read-only-role visibility. It is not a general UI regression suite.
- `globalSetup` warmed routes for the `core-regression-bundle` manifest shape specifically. TE-2A removed it; a future spec no longer needs a warm-up step because the served bundle is pre-built.
- Timeouts in `playwright.config.ts` (`actionTimeout: 30s`, `navigationTimeout: 45s`, per-test `timeout: 60s`, `globalTimeout: 10m`) were originally tuned against `next dev` first-compile latency. TE-2A left them unchanged because several specs drive multi-step business flows against a real database; the whole suite now completes in about 52 seconds. They may still need revisiting in a materially different environment (e.g., CI).
- `backend/.smoke-runs/*.json` files accumulate locally across runs (cleanup intentionally does not delete them, for idempotency); they are gitignored and harmless, but a developer who wants a clean local state can delete the directory manually.
- Playwright currently runs a single Chromium project; cross-browser coverage was explicitly out of scope for this foundation.

## How Slice 6O.1 should use this tooling

A future agent implementing Slice 6O.1 (Supplementary and Change Commercial Offer Foundation) should add new `_build_*` scenario functions to `backend/tooling/smoke_data/scenarios.py` reusing the existing `builders.py` primitives (and adding new ones only for genuinely new service-layer actions 6O.1 introduces), rather than building parallel seed/cleanup tooling. New Playwright specs should follow the existing fixture pattern (`fixtures/manifest.ts`, `fixtures/auth.ts`) and extend `core-regression-bundle` (or add a new named scenario) rather than inventing a second manifest shape. Do not recreate the generic terminal-status bypass Slice 6M.1 closed -- any scenario reaching a terminal offer status must go through the real Customer Response (or future 6O.1-specific) action, not a direct status write.

## Slice 6O.1 extension note

Slice 6O.1 (implemented) added `add_offer_line` and `create_related_offer` to `builders.py`, four new scenarios (`supplementary-offer-draft`, `change-quotation-draft`, `supplementary-offer-lifecycle`, `related-offer-regression-bundle`) to `scenarios.py`, and extended `cleanup.py` with `_find_all_owned_related_offer_ids` (mirrors the existing `_find_all_owned_work_order_ids` live-creation-discovery pattern, now for a related offer's `base_offer_id`) and `_null_out_related_work_order_links` (breaks a new cross-table FK cycle - `crm_commercial_offer.related_work_order_id -> crm_work_order.id` runs opposite to the existing `crm_work_order.commercial_offer_id -> crm_commercial_offer.id` - by nulling the column before Work Orders are deleted).

Rather than merging the new scenario's records into `core-regression-bundle`, Slice 6O.1 seeds `related-offer-regression-bundle` as its own run (own run id, own manifest JSON file at `e2e/.manifest/related-offers.json`, own `RELATED_OFFERS_MANIFEST_PATH` env var, own `loadRelatedOffersManifest()` fixture function), and `scripts/run-e2e.ps1` now seeds and cleans up **two** runs per invocation. This is the pattern a future 6O.2 (or later) extension should follow if its scenario needs are similarly self-contained: a new named scenario plus a new manifest file is simpler to reason about and to keep isolated than growing one ever-larger bundle. If a future slice's Playwright coverage genuinely needs to interact with 6O.1's related-offer records directly, extend `related-offer-regression-bundle` itself rather than adding a third manifest.

Two real bugs were found and fixed while validating this extension (both harness/E2E tooling, not CRM business logic): the cross-table FK cycle above, and a Playwright test-isolation bug where two new specs initially shared one Base Offer target (violating the "no two tests mutate the same Commercial Offer" principle this document already establishes) - fixed by splitting into `supplementary_offer_create_target` and `change_quotation_create_target`. See `docs/continuity/SLICE_6O1_SUPPLEMENTARY_CHANGE_COMMERCIAL_OFFER_FOUNDATION.md` for the full list of defects found and fixed during this slice.

## Slice 6O.2 extension note

Slice 6O.2 (implemented) added `create_work_order_amendment`, `add_amendment_line` and
`decide_amendment` to `builders.py`, three new scenarios (`work-order-amendment-received`,
`commercial-amendment-with-change-quotation`, `work-order-amendment-regression-bundle`) to
`scenarios.py`, and extended `cleanup.py` with ownership-based discovery of
`crm_work_order_amendment` / `crm_work_order_amendment_line` rows keyed off the owned
Work Order id (mirroring the existing `crm_work_order_line` discovery pattern
one level down, since every amendment's `work_order_id` is `NOT NULL`). Amendment lines
are deleted before amendments, which are deleted before Work Order lines/Work Orders
themselves, since an amendment line FKs to both its parent amendment and (optionally)
a Work Order line.

Following the Slice 6O.1 guidance above almost exactly, `work-order-amendment-regression-bundle`
is seeded as its own third run (own run id, own manifest JSON file at
`e2e/.manifest/work-order-amendments.json`, own `WORK_ORDER_AMENDMENTS_MANIFEST_PATH` env
var, own `loadWorkOrderAmendmentsManifest()` fixture function), and `scripts/run-e2e.ps1`
now seeds and cleans up **three** runs per invocation. This was a deliberate exception to
the Slice 6O.1 note's preference for extending an existing manifest rather than adding a
third one: the amendment scenarios needed genuinely new record shapes (an amendment plus
its lines, with a live-status commercial-basis dependency) that don't fit naturally inside
`related-offer-regression-bundle`'s existing record shape, so a fourth manifest would have
been the wrong trade-off in the other direction - reusing `related-offer-regression-bundle`
would have coupled two independently-evolving scenario catalogues together. The bundle
itself grew to 7 independent record sets (`administrative_amendment_create_target`,
`commercial_amendment_with_basis`, `line_delta_target`, `amendment_read_only_view`,
`terminal_amendment_display`, plus two added during Part 2 frontend/Playwright work:
`commercial_amendment_create_target` for the interactive create-through-UI flow, and
`blocked_validation_target` for the commercial-basis-not-yet-accepted blocker), each using
its own Work Order so no two Playwright tests mutate the same record - the same isolation
principle `core-regression-bundle` established.

## Windows / Docker runtime expectations

- Host Python and Node.js are not required. `backend/tooling/smoke_data` runs only inside the `backend` Compose service; Playwright and its browsers run only inside the `e2e` Compose service (official Playwright image).
- Normal `docker compose up -d` does not start the `e2e` service (Compose `profiles` gate).
- `scripts/smoke-data.ps1` and `scripts/run-e2e.ps1` are PowerShell 7+ scripts, consistent with the rest of this repo's tooling.
