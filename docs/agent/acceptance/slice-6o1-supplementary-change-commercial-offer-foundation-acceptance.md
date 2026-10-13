# Slice 6O.1 Acceptance - Supplementary and Change Commercial Offer Foundation

## Automated checks

- `docker compose exec backend alembic heads` reports `20260712_0028 (head)`.
- `docker compose exec backend alembic current` matches head after `upgrade head` (applied
  cleanly against the existing running database with pre-existing data present).
- `docker compose exec backend pytest tests/test_commercial_offer_related_offers_api.py -q` -
  11 passed.
- `docker compose exec backend pytest tests/test_smoke_data_harness.py -q` - 21 passed (14
  pre-existing + 7 new).
- `docker compose exec backend pytest` (full suite) - 181 passed (163 pre-existing + 11 + 7).
- Frontend `npm run build` - passes, including the new
  `/commercial-offers/[commercialOfferId]/related-offers/new` route.
- Frontend `npm test` - unchanged placeholder ("Frontend automated tests not configured").
- `.\scripts\run-e2e.ps1` run twice from clean state - `7 passed` both times (4 pre-existing +
  3 new), distinct run ids each time, cleanup succeeded both times, zero `TE1-SMOKE%` rows left
  in the database after either run.
- `docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` byte-for-byte
  unchanged (`git diff --stat` for that path is empty both before and after this slice).

## Manual/backend test coverage summary

`backend/tests/test_commercial_offer_related_offers_api.py` (11 tests):

```text
test_ordinary_commercial_offer_is_created_as_base_purpose
test_supplementary_offer_created_from_accepted_base_with_no_copied_data
test_related_offer_listing_shows_multiple_independent_series
test_change_quotation_requires_linked_work_order
test_related_offer_rejects_cross_opportunity_work_order_lineage
test_related_offer_rejects_invalid_purpose_and_blank_summary_and_missing_base
test_related_offer_cannot_be_created_from_draft_or_non_accepted_base
test_related_offer_cannot_be_created_from_another_related_offer
test_actionable_base_offer_guard_ignores_related_offers_and_names_base_offer
test_related_offer_has_independent_lifecycle_and_does_not_mutate_base_offer
test_related_offer_creation_is_unreachable_without_account_traceability
```

Covers: BASE-purpose backward compatibility, Supplementary/Change Quotation creation success
paths, no-copy verification, multi-series listing (CO + Opportunity + Work Order read
endpoints), Change Quotation Work Order requirement, cross-Opportunity Work Order rejection,
invalid purpose / blank summary / missing base / non-accepted base / chained-related-offer /
unauthorized-role negative paths, the refined one-active-Base-Offer guard naming the correct
(Base, not related) offer, and independent lifecycle (line -> submit -> accept on the related
offer without mutating the Base Offer or auto-creating a Work Order).

`backend/tests/test_smoke_data_harness.py` (7 new tests) additionally cover: no-copied-data at
the harness level, Change Quotation Work Order linkage resolving through the DB, independent
lifecycle via the harness, the three-purpose regression bundle shape, cross-run isolation for
related offers, ownership-based discovery of a related offer created *after* seeding (mirroring
the TE-1 Work Order discovery fix), and the cross-table FK-cycle null-out fix.

## Manual UI acceptance

Test users: `sales1` (SALES_USER, creation), `readonly1` (MANAGEMENT_READ_ONLY, read-only
verification). Starting point: seed `related-offer-regression-bundle` via
`.\scripts\smoke-data.ps1 seed -Scenario related-offer-regression-bundle -Json`, then browse.

Positive path (performed live via exploratory browser testing during this slice, then cleaned up):

1. Open the `supplementary_offer_create_target` Base Offer as `sales1` - purpose badge shows
   "Base Offer", status "Accepted". Traceability tab shows "No Supplementary Offer or Change
   Quotation has been created from this Commercial Offer yet.", "Create Supplementary Offer" is
   present, and "Create Change Quotation requires an existing linked Work Order." is shown
   (correctly disabled) because this target has no Work Order yet.
2. Click "Create Supplementary Offer" - lands on the locked-context creation page showing the
   correct Base Offer code/status/Opportunity/Account. Filled request summary and reference,
   submitted - "CO-XXXX created successfully." and an "Open CO-XXXX" link appear.
3. Opened the created offer - purpose badge "Supplementary Offer", status "Draft", Traceability
   tab shows the Base Offer link, the customer request summary/reference, and correctly does
   *not* show the two create-related-offer actions (since this offer's own purpose is not
   BASE).
4. Returned to the Base Offer - unchanged (same "Updated" timestamp as "Created", still
   "Accepted"), and the Traceability tab now lists the new Supplementary Offer with an Open
   link; "Create Supplementary Offer" remains available (multiple may coexist).
5. Logged in as `readonly1`, reopened the Base Offer - no "Edit Commercial Offer / Status", no
   "Create Work Order shell", no "Create Supplementary Offer" / "Create Change Quotation"
   actions anywhere, but the related-offer relationship (purpose, Base Offer link, request
   summary) remained fully visible.
6. Confirmed a direct unauthorized `POST .../related-offers` call as `readonly1` (via
   PowerShell `Invoke-WebRequest`) returns `403 {"detail":"User does not have the required
   role."}` - backend authorization is authoritative, independent of frontend hiding.

Result: **Pass**. All browser-created data cleaned up via
`docker compose exec backend python -m tooling.smoke_data cleanup --run-id <id>`; zero
`TE1-SMOKE%`-tagged rows remained afterward.

## Playwright coverage

`related-offer-supplementary-creation.spec.ts`, `related-offer-change-quotation-creation.spec.ts`
and `related-offer-opportunity-listing.spec.ts` automate the equivalent flows above (Supplementary
creation from the Base Offer, Change Quotation creation from a Work Order with auto-selected
linked Work Order, and Opportunity multi-series display with independent navigation), each
against its own dedicated seeded target so no two tests mutate the same Commercial Offer. All
three passed in two consecutive clean `.\scripts\run-e2e.ps1` runs, alongside the four
pre-existing TE-1 specs.

## Known limitations / deferred (recorded, not guessed at)

- The Playwright suite covers three of the six scenarios originally enumerated for this slice
  (Supplementary creation, Change Quotation creation, Opportunity multi-series display).
  Independent-lifecycle progression and read-only-role visibility for related offers
  specifically are covered at the backend/harness level
  (`test_related_offer_has_independent_lifecycle_and_does_not_mutate_base_offer`,
  `test_supplementary_offer_lifecycle_scenario_is_independent_of_base_offer`) and were verified
  manually via exploratory browser testing (see above), but do not have dedicated Playwright specs. A future
  agent extending this thread should add
  `related-offer-independent-lifecycle.spec.ts` and `related-offer-read-only-role.spec.ts`
  using the existing `related-offer-regression-bundle` scenario and the `read-only-role.spec.ts`
  pattern already in the suite.
- No Work Order Amendment record, application, or remaining-quantity/partial-award allocation
  logic exists. Accepting a related offer never creates or amends anything automatically; that
  remains Slice 6O.2 (Work Order Amendment Intake Foundation).
- `data-testid` was added to exactly one table (`commercial-offer-row-{public_id}` on the
  Opportunity detail page) after two rounds of demonstrating that a pure semantic/text selector
  is genuinely ambiguous for this specific table (a related offer's default title and its Base
  Offer column both legitimately repeat the Base Offer's own code). No other `data-testid` was
  added anywhere else in the frontend.
- Related-offer numbering reuses the existing `CO-NNNNNN` global sequence; there is no separate
  numbering scheme distinguishing a related offer from a Base Offer by code alone (purpose badge
  and Base Offer link are the source of truth).

## Regression confirmation

- Existing Slice 4A-6O Commercial Offer, Opportunity and Work Order flows are unaffected: full
  backend suite (181 tests) and both pre-existing/new Playwright groups passed together.
- The Slice 6B.1 one-active-Base-Offer guard's existing behavior (blocking a second ordinary
  Commercial Offer while an active Base Offer exists) is preserved and additionally now points
  at the correct Base Offer even when related offers exist
  (`test_actionable_base_offer_guard_ignores_related_offers_and_names_base_offer`).
- The Slice 6M.1 terminal-status guard, Slice 6D.1 frozen handoff, and Slice 6L Customer
  Response action are all unmodified and their existing tests still pass unchanged.

## TB-1 fix TB1-801 (5 October 2026): a refused offer value keeps the page

Before this fix, typing an offer value the server refuses - "1,00,000", "-5000", "1500.755" - and pressing Create
replaced the whole page with "Unexpected Application Error!": the page put FastAPI's list of field errors on screen as
it came. The page now checks the value first, and reads any refusal through the shared reader
(`frontend/src/components/errorDetail.ts`).

Test user: `sales1` / `password` (SALES_USER). Starting URL: an Accepted Base Offer, Traceability tab, **Create
Supplementary Offer**.

1. Fill **Request / change summary**, type `1,00,000` in **Offer value (optional)**, press **Create Supplementary
   Offer**: "Offer value must be a number." appears; the form keeps what was typed.
2. Type `100000` and press it again: the Supplementary Offer is created.

`e2e/tests/related-offer-supplementary-creation.spec.ts` runs both, and also answers the create once with the server's
list of field errors to show the page stays and says "Check the values entered: one of them is not accepted."
