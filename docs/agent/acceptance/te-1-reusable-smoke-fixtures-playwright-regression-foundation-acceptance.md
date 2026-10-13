# TE-1 Acceptance - Reusable Smoke-Test Fixtures and Playwright Regression Foundation

Technical-enablement work package, not a numbered CRM business slice. No CRM business behavior, API contract or migration changed.

## Automated checks

- `docker compose exec backend alembic heads` / `alembic current` both report `20260712_0027 (head)` -- unchanged by TE-1, no migration added.
- `docker compose exec backend pytest` -- 163 passed (149 pre-existing + 14 new in `tests/test_smoke_data_harness.py`).
- Frontend `npm run build` passes (no frontend source changed).
- Frontend `npm test` remains the pre-existing "not configured" placeholder (unchanged).
- `docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` byte-for-byte unchanged (`git diff --stat` empty).

## Smoke-data harness manual checks

Test user/role: `sales1` (SALES_USER) as the harness's internal acting user for created-by/event-actor fields; no login/role check applies since the harness calls service functions directly, not HTTP routes.

1. `docker compose exec backend python -m tooling.smoke_data scenarios` -- lists all 6 scenarios. Pass.
2. `docker compose exec backend python -m tooling.smoke_data seed --scenario accepted-offer-no-work-order --json` -- valid JSON manifest, `run_id` unique, `records.handoff_target.commercial_offer_status == "ACCEPTED"`, `work_orders == []`. Pass.
3. Opened the seeded Commercial Offer in the browser: title `TE1-SMOKE-<run_id> Commercial Offer ...` visible, status Accepted, Account/Opportunity linked, Submission tab Lifecycle Guidance showing the Slice 6O "Work Order handoff review" panel and "1 Work Order shell(s) already exist" / no-shell-yet text correctly depending on scenario. Pass (see session transcript for full page-text capture).
4. Opened a seeded Work Order (from `accepted-offer-with-work-order` / `core-regression-bundle`): "Handoff shell" badge, "Handoff provenance" section including the `WorkOrderCreated` business event (as `admin1`), line-traceability table showing the exact source `line_public_id` from the manifest. Pass.
5. `cleanup --run-id <id>` -- reports per-table deleted counts; record confirmed gone from DB afterward (`business_party` row count by tagged name == 0). Pass.
6. Seeded two separate runs, confirmed distinct `run_id`s and distinct account rows; cleaned up one, confirmed the other's account row was still present; cleaned up the second. Pass -- isolation holds.
7. Re-ran `cleanup --run-id` against an already-cleaned run: all counts `0`, exit code `0`, explicit "not an error" message. Pass -- idempotent.
8. Malformed run id (`'; DROP TABLE x; --`) rejected with a clean `ValueError` message and exit `1`, no traceback. Pass.
9. Missing manifest file path rejected with a clean message and exit `1`. Pass.
10. Manifest missing required keys rejected by `validate_manifest_dict` before any DELETE runs. Pass.
11. `scripts/smoke-data.ps1 scenarios` / `seed -Scenario ... -Json` / `cleanup -RunId ...` / `list` -- all produce the same output as the raw `docker compose exec` call and exit `0`. `cleanup` with neither `-RunId` nor `-Manifest` exits `2` with a clear message; `seed -Scenario not-a-real-scenario` exits `2` and lists the real catalogue. Pass. (A real PowerShell bug was found and fixed here -- see "Defects found and fixed" below.)

## E2E manual/automated checks

Test users: `sales1` (Test 1), `admin1` (Test 3, to see the `EVENT_VIEW_ROLES`-gated provenance detail), `readonly1` / MANAGEMENT_READ_ONLY (Test 4), `sales1` (Test 2 setup implicitly via manifest data only, no login mutation needed beyond read).

Starting point: `.\scripts\run-e2e.ps1` from a running `db`/`backend`/`frontend` stack.

1. First full run (after fixes) -- `4 passed` (`accepted-offer-handoff`, `existing-work-order-traceability`, `read-only-role`, `terminal-status-guard`), run id `te1-cc48c5a2`, cleanup succeeded, DB confirmed clean afterward.
2. Second full run -- `4 passed`, run id `te1-4d85af90` (different from run 1), cleanup succeeded (correctly discovered and deleted 3 live-created Work Orders not present in the seed-time manifest -- see Defects below), DB confirmed clean afterward.
3. Failure-path check (encountered naturally during development, before the fixes below): a Playwright test failure still triggered the `finally`-equivalent cleanup in `scripts/run-e2e.ps1`, which ran to completion; DB confirmed clean afterward in every case observed.
4. `docker compose up -d` (without `--profile e2e`) does not start or reference the `e2e` service. Confirmed by inspecting `docker compose ps` after normal startup -- no `e2e` container.
5. `e2e` service requires no host Node.js; `docker compose --profile e2e run --rm e2e` runs `npm install && npx playwright test` entirely inside the official `mcr.microsoft.com/playwright:v1.61.1-noble` container.

## Defects found and fixed during this validation (in scope: harness/tooling only, not CRM business logic)

1. **Cleanup FK violation on live-created Work Orders.** `accepted-offer-handoff.spec.ts` (Test 1) triggers the real Slice 6D.1 handoff through the UI for an offer seeded with `work_orders: []`. The first cleanup implementation only knew about Work Orders listed in the seed-time manifest, so it left the live-created Work Order (and its line) behind, then failed with an `fk_crm_work_order_line_offer_line` constraint violation when deleting the offer's line. Fixed in `backend/tooling/smoke_data/cleanup.py` by discovering owned Work Orders through `crm_work_order.commercial_offer_id` ownership (`NOT NULL` in the schema, so this is a complete and safe key) rather than only the manifest's explicit list. Covered by a new backend regression test and re-verified live in a passing E2E run.
2. **`smoke-data.ps1` `$Args`/return-value bug.** The original wrapper (a) named a function parameter `$Args`, which collides with PowerShell's automatic per-scope `$args` variable and silently broke splatting to `docker compose exec`, and (b) used `return $LASTEXITCODE` as a function's last statement, which in PowerShell captures every unsuppressed prior output object (i.e. the child process's entire stdout) into the function's return value alongside the exit code, corrupting both. Fixed by removing the wrapper function entirely and calling `docker compose exec` directly in each `switch` branch, then `exit $LASTEXITCODE` immediately. Re-verified: `scenarios`/`seed`/`cleanup`/`list` all show correct output and exit codes now.
3. **`next dev` cold-compile timeouts.** The first Playwright run of the suite (before `tests/global-setup.ts` existed) timed out because the very first hit to each dynamic route pays a first-compile cost under `next dev`. Fixed with an explicit warm-up `globalSetup` step plus generous, documented timeouts (`actionTimeout: 30s`, `navigationTimeout: 45s`, per-test `60s`) -- not retries; retries remain `0`.
4. **`terminal-status-guard.spec.ts` assertion was based on a wrong assumption.** The test originally asserted no `<option>` text could contain "Accepted"/"Rejected", but the real (correct) UI behavior for a terminal offer is to show exactly one disabled `<option>` carrying the current status label plus "(final status, cannot be changed here)" -- so an option containing the word "Rejected" for a REJECTED offer is expected. Fixed the assertion to check for exactly one option matching that pattern and the absence of the normally-selectable targets (Draft/Ready For Review/Withdrawn/Closed), which is what Slice 6M.1 actually guarantees.

None of the above changed any backend route, schema, permission, business event, or the frozen Slice 6D.1 handoff contract.

## Known limitations / deferred

- Cross-browser coverage beyond the single Chromium project was out of scope.
- `backend/.smoke-runs/*.json` files accumulate locally (by design, for idempotent `cleanup --run-id`); gitignored, harmless, deletable manually.
- `tests/global-setup.ts` warms routes specific to the `core-regression-bundle` shape; a future spec using a different scenario standalone should extend it.
- Timeouts were tuned against this development environment's observed `next dev` latency and may need revisiting in a materially different environment (e.g. CI).

## Code review

`/code-review` (medium effort, 4 parallel finder angles: line-by-line scan, removed-behavior
audit, cross-file trace, reuse/simplification/efficiency/altitude/conventions) was run against
the full diff before commit. It surfaced 9 findings, all CONFIRMED and all fixed:

1. Cleanup missed a Work Order created live through the Playwright UI (not in the seed-time
   manifest) -- fixed with ownership-based discovery in `cleanup.py`.
2. `smoke-data.ps1` had a `$Args` automatic-variable collision plus a `return $LASTEXITCODE`
   that bundled child-process stdout into the function's return value -- fixed by removing the
   wrapper function.
3. `next dev` cold-compile timeouts caused the first E2E run to fail -- fixed with
   `tests/global-setup.ts`.
4. `terminal-status-guard.spec.ts` asserted a wrong invariant about the status `<option>` list --
   fixed to match the real, correct UI behavior.
5. The same spec's `getByLabel("Remarks", { exact: false })` was ambiguous against two
   remarks-like fields and silently checked the wrong one -- fixed with an exact label.
6. `global-setup.ts`'s first `/login` navigation was missing the explicit timeout every other
   `goto` in the same fix received -- fixed.
7. `_build_blocked_handoff`'s bare `except Exception` could mask an unrelated crash as the
   expected business blocker -- narrowed to `WorkOrderValidationError`.
8. `store.py`'s `delete_manifest_file()` was dead code contradicting the documented idempotency
   design -- removed.
9. `smoke-data.ps1`'s documented `-Manifest` example used a host path that cannot resolve inside
   the backend container -- docstring corrected to explain container-side path resolution and
   steer users to `-RunId`.

After all fixes: `backend/tests/test_smoke_data_harness.py` re-run (14 passed), full backend suite
re-run (163 passed), and a fresh `.\scripts\run-e2e.ps1` run completed in 1.1 minutes with all 4
tests passing and cleanup succeeding (run id `te1-184dac26`) -- the fastest and cleanest run of
the whole validation process, consistent with the fixes addressing real timing/correctness gaps
rather than papering over them.
