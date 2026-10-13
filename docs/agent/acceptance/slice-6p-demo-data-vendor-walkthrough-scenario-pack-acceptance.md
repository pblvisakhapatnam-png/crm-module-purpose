# Slice 6P Acceptance - Demo Data and Vendor Walkthrough Scenario Pack

Documentation/fixture-tooling slice. No CRM business behavior, API contract or migration
changed.

## Automated checks

- `docker compose exec backend alembic heads` / `alembic current` both report
  `20260713_0029 (head)` before and after this slice - unchanged, no migration added.
- `docker compose exec backend pytest tests/test_smoke_data_harness.py` - 38 passed
  (24 pre-existing + 14 new: 10 `vendor_demo_bundle` tests, one `status` test, one
  `prior_te1_scenarios_remain_compatible` regression test, one lead-conversion cleanup
  regression test, one status-command test).
- `docker compose exec backend pytest` (full suite) - 218 passed (217 pre-existing +1
  net new after this slice's additions; no regressions).
- Frontend `npm run build` passes (no frontend application source changed by this
  slice).
- Frontend `npm test` remains the pre-existing "not configured" placeholder.
- `docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` and
  `docs/agent/contracts/work-order-amendment-contract.md` both confirmed byte-for-byte
  unchanged (SHA-256 compared before and after this slice).

## Existing E2E regression (`scripts/run-e2e.ps1`)

Run twice during this slice (once before, once after fixing the `demo-preflight.spec.ts`
test-collection crash described below):

- First run after adding `demo-preflight.spec.ts` (before the try/catch fix): the
  Playwright suite **failed entirely** - every spec (all 21+9 tests) aborted because the
  new spec's unconditional `loadVendorDemoManifest()` call at module scope threw during
  Playwright's test-collection phase, which imports every spec file in `testDir`
  regardless of `--grep` filtering, and `VENDOR_DEMO_MANIFEST_PATH` is never set by the
  ordinary `run-e2e.ps1` flow. Fixed by wrapping the load in try/catch and adding
  `test.skip(!manifest, ...)`.
- Second run after the fix: **12 passed, 9 skipped** (the 9 skipped are exactly the
  `@demo-preflight` tests, correctly skipping because `VENDOR_DEMO_MANIFEST_PATH` is
  unset in this run), all three manifests (`core-regression-bundle`,
  `related-offer-regression-bundle`, `work-order-amendment-regression-bundle`) seeded
  and cleaned up successfully.

## Vendor-demo cycle (`scripts/vendor-demo.ps1`)

Full cycle run multiple times during this slice; final clean sequence:

1. `prepare` - seeds `vendor-demo-bundle`, writes `.vendor-demo\active-run.json` and
   `.vendor-demo\launch-sheet.md`, prints run id and URLs. Pass.
2. `status` - reports all anchor records present (accounts/opportunities/offers/work
   orders/leads all N/N). Pass.
3. `preflight` - backend/frontend health checks pass; anchor-record status passes; the
   isolated `@demo-preflight` Playwright run (all four manifest env vars pointed at the
   same `vendor-demo-bundle` manifest copy) reports **9 passed**. Pass.
4. `reset` - cleans up the active run and prepares a fresh one with a **different run
   id** (`te1-1038f1b8` -> `te1-0de1dd7d` in one recorded run). Pass.
5. `preflight` (second run, against the reset run) - **9 passed** again. Pass.
6. `cleanup` - removes all seeded records and the local active-run/launch-sheet files;
   confirmed zero residue via direct SQL count; a second `cleanup` call reports "No
   active vendor demo run found. Nothing to clean up." (idempotent). Pass.
7. `prepare` immediately after a completed `cleanup` succeeds again (fresh run,
   different id); a second `prepare` while a run is already active is correctly
   **refused** with a clear message directing to `reset`/`cleanup`. Pass.

Demo-preflight-only invocation was also verified directly (outside the wrapper) by
pointing `MANIFEST_PATH`, `RELATED_OFFERS_MANIFEST_PATH`,
`WORK_ORDER_AMENDMENTS_MANIFEST_PATH` and `VENDOR_DEMO_MANIFEST_PATH` at the same
`vendor-demo-bundle` manifest file - every other (non-demo-preflight) spec's own
`test.skip(!record, ...)` guard correctly skips since its expected record keys are
absent from that manifest, confirmed no unintended crash or false failure.

## Manual rehearsal (exploratory browser testing)

Full primary walkthrough rehearsed end-to-end against a freshly prepared run
(`te1-70253447`), logged in as `sales1` unless noted:

- **Track A**: opened `lead_interactive` (`TE1-SMOKE-... Company DemoLeadReady`, status
  NEW, one CALL activity present); recorded a Qualified decision; clicked Convert Lead.
  Result: Lead status became CONVERTED, with a new Account and Opportunity created and
  linked back (`AccountCreated`, `OpportunityCreated`, `LeadConverted` events shown on
  screen). Pass.
- **Track B**: opened `offer_ready_to_submit` (Draft, 1 active line, pricing evidence,
  submission evidence, clean credit review all pre-recorded, Submission Readiness
  showing 9 Pass/2 Warning/0 Blocking); clicked "Record as Submitted / Commercially
  Committed". Result: status became Submitted, `CommercialOfferCommerciallyCommitted`
  event recorded, readiness improved to 10 Pass/1 Warning. Pass.
- **Track C**: opened `offer_accepted_no_wo` (Accepted, explicit "No Work Order has been
  created yet..." guidance shown); clicked "Create Work Order shell". Result: Work Order
  shell WO-002234 created, offer profile updated to show "1 Work Order shell(s) already
  exist...". Pass.
- **Track E**: opened `related_offers_chain`'s Traceability tab. Confirmed a Draft
  Supplementary Offer (no linked Work Order) and an Accepted Change Quotation (linked to
  the existing Work Order) both listed as separate purpose-badged series under the same
  Base Offer. Pass.
- **Track F**: opened `amendment_commercial_interactive` (Commercial, Under Review,
  citing an Accepted Change Quotation as commercial basis, one proposed Add Line);
  clicked Validate. Result: status became Validated (terminal), page stated "It has not
  been applied to the Work Order." Re-opened the underlying Work Order and confirmed its
  one line's scope/quantity/rate/amount were byte-for-byte unchanged from before
  validation. Pass.
- **Track G**: logged out, logged in as `readonly1` (Management Read Only), reopened the
  same Work Order. Confirmed full business-event history is visible (five events shown,
  including `WorkOrderAmendmentValidated`) with no create/edit controls offered anywhere
  on the page. Pass.

**Real defect found during rehearsal** (not caught by automated tests beforehand): after
performing the Track A live conversion, `vendor-demo.ps1 cleanup` failed with an
`fk_crm_opportunity_source_lead` constraint violation, because the live-created
Opportunity/Account were not in the seed-time manifest and cleanup had no ownership-
discovery path for them. Fixed in `cleanup.py` (see slice doc); cleanup re-run
succeeded completely (zero residue, confirmed via direct SQL count) after the fix, and a
regression test was added and passes.

Approximate rehearsal duration: ~25 minutes end-to-end (including diagnosing and fixing
the cleanup bug), consistent with the runbook's ~35-50 minute primary-walkthrough
estimate for a live, narrated presentation (the rehearsal itself skipped narration/deep
dives).

## Code review

`/code-review` (high effort, 8 parallel finder angles across two consolidated agents:
correctness A/B/C, and cleanup/simplification/efficiency/altitude/conventions) ran
against the full diff. See the continuity note for the itemized findings and
dispositions.

## Known limitations

- Playwright preflight coverage is intentionally thin (9 tests covering readiness, not a
  business-rule regression suite); it reuses the existing full 12+9-test suite for
  actual business-rule regression coverage.
- The launch sheet's per-record "Link" column picks one representative URL (amendment >
  lead > commercial_offer > account, in that priority order) rather than listing every
  URL inline; the full URL list is included in a separate section of the same file.
- Track D (revision/outcome history) and Track G (roles) do not have dedicated
  interactive records; they are documented as view-only/reuse tracks by design, per the
  task's own scope guidance ("need not open every record in the primary route").

## Next recommended step

Consolidated Manual UAT and Vendor-Demo Review Cycle (Slices 6L-6P), before choosing
among 6G.1, 6H.1, 6I.3, Work Order Amendment application/versioning, or platform/NFR
hardening. See `docs/continuity/NEXT_STEPS.md`.
