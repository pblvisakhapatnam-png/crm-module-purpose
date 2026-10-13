# Slice 6P - Demo Data and Vendor Walkthrough Scenario Pack

## Status

Implemented on branch `slice-6p-demo-data-vendor-walkthrough-scenario-pack`.
Documentation/fixture-tooling slice only - no CRM business behavior, API contract or
migration changed.

## Objective

Give future presenters a repeatable, disposable vendor-demo data pack and walkthrough
script covering the full implemented chain through Slice 6O.2 (Lead through Work Order
Amendment intake), following the same pattern Slice 6C established for the Slice 6B.2
chain: documentation plus reusable fixtures, not new application behavior.

## In scope

```text
- vendor-demo-bundle scenario added to the existing TE-1 smoke-data harness
  (backend/tooling/smoke_data/scenarios.py), covering demo Tracks A-F (Lead/Account/
  Opportunity, Commercial Offer preparation/submission, award/handoff, revision/outcome
  history, Supplementary Offer/Change Quotation, Work Order Amendment intake). Track G
  (roles/controls) reuses existing records rather than adding new ones.
- New harness builders: Lead create/activity/qualify/convert (backend/tooling/smoke_data/
  builders.py first-ever Lead builders), pricing-evidence and recommended-T&C-attach
  builders, a create_offer_no_line builder for a genuine zero-line blocker, and a
  submit_offer split into add_submission_evidence / add_credit_review /
  mark_offer_submitted (submit_offer itself is unchanged in external behavior, only
  internally composed from the three, so a scenario can stop after preparation without
  marking an offer Submitted).
- Additive, backward-compatible "demo_meta" manifest field (track, fictional_customer,
  purpose, interactive, fallback_of, presenter_role, presenter_action, expected_result)
  attached only to vendor-demo-bundle records; manifest_version stays 1.
- Extended cleanup.py ownership discovery: crm_lead / crm_lead_activity deletion (the
  harness's first Lead-owning cleanup path), plus live-creation discovery for an
  Opportunity/Account created by converting a seeded-but-unconverted Lead through the UI
  (a real bug found and fixed during the Part 11 manual rehearsal - see below).
- New backend/tooling/smoke_data/status.py + `python -m tooling.smoke_data status
  --run-id|--manifest` CLI command: read-only check of whether a manifest's anchor
  records (Account/Opportunity/Commercial Offer/Work Order/Lead) still exist.
- scripts/vendor-demo.ps1: prepare / status / preflight / reset / cleanup wrapper. Always
  delegates seeding/cleanup/status to the existing harness via `docker compose exec
  backend python -m tooling.smoke_data ...`; never a second seed engine. Local state
  (active-run.json, launch-sheet.md) lives under the new gitignored `.vendor-demo/`
  directory.
- Non-destructive Playwright demo-preflight suite (e2e/tests/demo-preflight.spec.ts,
  every test title tagged `@demo-preflight`), run via `docker compose --profile e2e run
  --rm e2e ... npx playwright test --grep '@demo-preflight'`. Reuses the existing e2e/
  workspace, Playwright version, container image and manifest-parsing fixtures; adds
  `loadVendorDemoManifest()` to e2e/tests/fixtures/manifest.ts and an optional (env-var-
  gated) vendor-demo route warm-up to e2e/tests/global-setup.ts. The demo-preflight spec
  itself wraps its manifest load in try/catch so the ordinary full regression run
  (scripts/run-e2e.ps1, which never sets VENDOR_DEMO_MANIFEST_PATH) skips this file's
  tests cleanly instead of aborting Playwright's test collection for every other spec.
- docs/demo/PBL_CRM_VENDOR_DEMO_RUNBOOK.md, _SCENARIO_MATRIX.md,
  _PRESENTER_CHECKLIST.md, _FEEDBACK_TEMPLATE.md - primary/abbreviated walkthrough,
  scenario-by-scenario detail, presenter prep checklist and vendor feedback capture
  template. Cross-reference (not replace) the existing Slice 6C docs/demo/01-04 guides.
- .gitignore entry for `.vendor-demo/`.
```

## Out of scope

```text
New CRM business rules, Commercial Offer lifecycle rules, or Work Order behavior
Work Order Amendment application/versioning
Any operational Work Order processing (equipment, crew, scheduling, log sheets, billing)
Production authentication, seed/reset endpoints, or deployment changes
A second fixture or E2E framework (the existing TE-1 harness and e2e/ workspace were
  extended, not replaced)
Any change to the frozen Slice 6D.1 handoff contract or the Slice 6O.1/6O.2 contracts
Choosing or starting the next functional-build slice
```

## Fictional demo data

All `vendor-demo-bundle` records use a fictional heavy-lift/equipment-hiring customer
story ("Meridian Bay Refinery Expansion") layered onto the harness's existing
`TE1-SMOKE-<run_id>` name-tagging convention. No real customer, employee, vendor, tender
or commercial information is used anywhere in the bundle or in the committed
documentation (which contains no generated UUIDs - those only ever appear in the
gitignored, locally-generated `.vendor-demo/launch-sheet.md`).

## Interactive/fallback design

Every live-mutation step in the primary walkthrough (qualify+convert a Lead, mark an
offer Submitted, create a Work Order shell, validate a Work Order Amendment) has a
paired, already-completed fallback record, so a presenter can recover if a step was
performed early, skipped, or a rehearsal already consumed it. `demo_meta.fallback_of`
on the fallback record names its interactive counterpart; the generated launch sheet
renders this as an explicit "Fallback map" table.

## Real defects found and fixed during this slice

1. **Lead-conversion cleanup ownership gap.** The interactive Track A Lead record is
   seeded unconverted so a presenter can qualify and convert it live. That live
   conversion (Slice 3D) creates a new Opportunity and Account the seed-time manifest
   never recorded. The first cleanup implementation only removed opportunities named in
   the manifest, then failed deleting the Lead with an
   `fk_crm_opportunity_source_lead` constraint violation. Fixed with
   `_find_all_owned_opportunity_ids_via_lead_conversion` /
   `_find_all_owned_account_ids_via_opportunity` in `cleanup.py`, mirroring the existing
   Work-Order/related-offer live-creation-discovery pattern from TE-1/6O.1/6O.2. Found
   during the required manual browser rehearsal, not by automated tests alone; a
   regression test (`test_vendor_demo_bundle_cleanup_discovers_a_lead_converted_live_and_not_in_the_manifest`)
   now covers it.
2. **Playwright test-collection crash on a normal full-suite run.** The new
   `demo-preflight.spec.ts` initially called `loadVendorDemoManifest()` unconditionally
   at module scope. Playwright imports every spec file in `testDir` to collect tests
   regardless of `--grep`, so this threw and aborted the *entire* suite (all specs, not
   just the new one) whenever `VENDOR_DEMO_MANIFEST_PATH` was unset - which is every
   normal `scripts/run-e2e.ps1` run. Fixed by wrapping the load in try/catch and
   `test.skip`-ing the whole file when the manifest is unavailable, matching how
   `global-setup.ts`'s optional vendor-demo warm-up already guards on the same env var.

## Testing

See
`docs/agent/acceptance/slice-6p-demo-data-vendor-walkthrough-scenario-pack-acceptance.md`
for the full validation record (backend, frontend, E2E, vendor-demo cycle, manual
rehearsal, code review).

## Continuity

See `docs/continuity/SLICE_6P_DEMO_DATA_VENDOR_WALKTHROUGH_SCENARIO_PACK.md` for
objective, files changed, checks run and the next recommended step.
