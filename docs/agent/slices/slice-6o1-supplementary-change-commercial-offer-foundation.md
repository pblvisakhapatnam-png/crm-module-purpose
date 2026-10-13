# Slice 6O.1 - Supplementary and Change Commercial Offer Foundation

## Objective

Add the commercial foundation for two post-award scenarios without touching the frozen Slice
6D.1 Accepted Offer -> Work Order handoff contract:

- a customer requests one or more additional lines/quantity against an enquiry already awarded
  (Supplementary Offer);
- a customer requests a revised price or scope before an amendment to an existing Work Order
  (Change Quotation).

Neither scenario is a revision of the original Commercial Offer. Both are separate Commercial
Offer series linked directly to their Base Offer.

## Scope

In scope:

```text
- Explicit offer_purpose (BASE / SUPPLEMENTARY / CHANGE_QUOTATION) on crm_commercial_offer.
- Direct self-referencing base_offer_id link from a related offer to its Base Offer.
- Optional (Supplementary) / required (Change Quotation) related_work_order_id link.
- Thin customer request context: customer_request_reference, customer_request_received_date,
  customer_request_summary (required on related-offer creation).
- POST /api/commercial-offers/{base_offer_public_id}/related-offers creation action.
- GET  /api/commercial-offers/{public_id}/related-offers listing.
- GET  /api/work-orders/{public_id}/related-offers listing.
- Refinement of the Slice 6B.1 one-active-Base-Offer-per-Opportunity guard to scope its scan
  to offer_purpose = BASE only.
- Independent lifecycle for related offers, reusing all existing Commercial Offer lifecycle
  routes (lines, pricing evidence, T&C, submission readiness, credit review, mark-submitted,
  revisions, customer responses, lifecycle guidance) unmodified.
- Frontend: purpose badges (Commercial Offer list, detail, Opportunity detail, Work Order
  detail), Create Supplementary Offer / Create Change Quotation actions, a dedicated
  related-offer creation page, and read-only related-offer sections on the Opportunity and
  Work Order detail pages.
- TE-1 smoke-data harness extension: 4 new scenarios, 2 new builders, ownership-aware cleanup
  extension covering the new self-referencing FK and the new cross-table FK cycle with
  crm_work_order.
- Playwright extension: 3 new specs (Supplementary creation from Base Offer, Change Quotation
  creation from Work Order, Opportunity multi-series listing) plus global-setup/run-e2e.ps1
  wiring for a second seeded manifest.
```

Out of scope (see `docs/agent/DEFERRED_REQUIREMENTS.md` / `docs/agent/FUTURE_SLICES.md`):

```text
- Work Order Amendment records or applying an amendment to a Work Order (Slice 6O.2).
- Automatic copying of offer lines, prices or terms from the Base Offer to a related offer.
- Automatic Work Order or Work Order Amendment creation on related-offer acceptance.
- Reopening or mutating the Base Offer in any way.
- Remaining-quantity / partial-award allocation logic.
- A second revision mechanism; Slice 6K revisions remain scoped inside one offer's own series.
```

## Core domain distinction

A revision (Slice 6K) changes one Commercial Offer's own lifecycle within its own series. A
Supplementary Offer or Change Quotation is a **separate Commercial Offer series** under the same
Opportunity, linked directly to its Base Offer:

```text
Opportunity
├── Base Offer            (offer_purpose = BASE)
│   ├── Revision 0        (Slice 6K, inside the Base Offer's own series)
│   └── Revision 1
├── Supplementary Offer    (offer_purpose = SUPPLEMENTARY, base_offer_id -> Base Offer)
│   └── Revision 0
└── Change Quotation       (offer_purpose = CHANGE_QUOTATION, base_offer_id -> Base Offer)
    └── Revision 0
```

Related offers never link to another related offer (no chains); every related offer's
`base_offer_id` points directly at a BASE-purpose offer.

## Base Offer eligibility

A Base Offer may father a related offer only while it currently carries `offer_status_code =
ACCEPTED`. Since `ACCEPTED` is a cannot-leave terminal status for the general update route
(Slice 6M.1) and is reachable only through the Slice 6L Customer Response action, this is a
stable, sufficient compatibility rule for this foundation. It never reopens, mutates or
reinterprets the Base Offer.

## Refined one-active-Base-Offer guard

The Slice 6B.1 rule ("only one active/actionable Commercial Offer per Opportunity until formal
revisions and Opportunity lines exist") now scopes its scan to `offer_purpose = BASE` only
(`get_existing_actionable_commercial_offer_for_opportunity` in
`backend/app/modules/commercial_offers/repository.py`). Before this fix, the same query scanned
every offer for the Opportunity regardless of purpose, so once a Supplementary Offer or Change
Quotation existed (with a non-inactive status), it could be surfaced as the "existing
active/actionable Commercial Offer" in the guard's error message instead of the real Base Offer -
confusing and factually wrong. The fix is a one-line `AND co.offer_purpose = 'BASE'` addition; it
does not change `COMMERCIAL_OFFER_INACTIVE_FOR_NEW_OFFER_STATUSES` or any other guard.

An active/accepted Base Offer never blocks creating a Supplementary Offer or Change Quotation (a
different creation path with its own eligibility rule), and multiple Supplementary Offers /
Change Quotations may coexist under the same Base Offer, each representing a distinct customer
request.

## Work Order lineage validation

A related offer optionally (Supplementary) or mandatorily (Change Quotation) links to an
existing Work Order via `related_work_order_id`. `_validate_related_work_order` in
`backend/app/modules/commercial_offers/service.py` rejects a Work Order that does not belong to
the same Opportunity, and (when both sides have a value) the same Account, as the Base Offer -
using a direct raw-SQL lookup against `crm_work_order` (`get_work_order_lineage_context` in
`commercial_offers/repository.py`), matching this repository's existing cross-module read
pattern rather than importing the `work_orders` module.

## Migration and backward compatibility

`backend/alembic/versions/20260712_0028_commercial_offer_related_offer_foundation.py` adds to
`crm_commercial_offer`:

```text
offer_purpose                     VARCHAR(50) NOT NULL DEFAULT 'BASE'  (backfills existing rows)
base_offer_id                     INT NULL, self-referencing FK -> crm_commercial_offer(id)
related_work_order_id             INT NULL, FK -> crm_work_order(id)
customer_request_reference        NVARCHAR(255) NULL
customer_request_received_date    DATE NULL
customer_request_summary          NVARCHAR(2000) NULL
```

Plus two CHECK constraints (`offer_purpose` is one of the three allowed values; `base_offer_id`
is NULL exactly when `offer_purpose = BASE` and NOT NULL otherwise) and three indexes
(`offer_purpose`, `base_offer_id`, `related_work_order_id`). Every pre-existing Commercial Offer
becomes `BASE` through the `NOT NULL ... DEFAULT` backfill; no data migration script was needed.
`CommercialOfferResponse` gained the new fields as additive, defaulted response fields, so every
existing caller of the Commercial Offer API keeps working unchanged.

### Cross-table FK cycle

The new `crm_commercial_offer.related_work_order_id -> crm_work_order.id` FK runs the opposite
direction from the existing `crm_work_order.commercial_offer_id -> crm_commercial_offer.id` FK
(the frozen Slice 6D.1 handoff). No cycle exists in application code (nothing ever needs to
delete a Work Order or a Commercial Offer in production), but the TE-1 smoke-data harness's
cleanup path does delete both, so `backend/tooling/smoke_data/cleanup.py` now nulls out
`related_work_order_id` for every offer this run owns *before* deleting Work Orders, breaking
the cycle safely. See the TE-1 extension note below.

## Creation path

```text
POST /api/commercial-offers/{base_offer_public_id}/related-offers
```

Reuses `COMMERCIAL_OFFER_CREATE_ROLES` (`ADMIN`, `SALES_USER`, `SALES_MANAGER`) - the same
authorization as ordinary Commercial Offer creation. Derives `opportunity_id` and
`business_party_id` from the Base Offer server-side; the request body cannot override them.
Starts the related offer in `DRAFT`, copies no lines/prices/terms/evidence, creates no Work
Order, and records exactly one `CommercialOfferRelatedOfferCreated` business event.

## Frontend

- Commercial Offer list, Commercial Offer detail (header badge), Opportunity detail (Commercial
  Offers table) all show a friendly purpose badge (Base Offer / Supplementary Offer / Change
  Quotation).
- Commercial Offer detail Traceability tab: for a related offer, shows Base Offer link, linked
  Work Order link, and the customer request context; for any offer, lists its own related
  offers with an Open action; for a Base Offer at `ACCEPTED`, shows "Create Supplementary
  Offer" (always) and "Create Change Quotation" (only when at least one Work Order is linked).
- New page `frontend/app/commercial-offers/[commercialOfferId]/related-offers/new/page.tsx`:
  locked Base Offer context, purpose selector, linked-Work-Order selector (auto-selected when
  exactly one exists), required request summary, optional request reference/date and initial
  offer fields.
- Work Order detail page: "Related Commercial Offers (Slice 6O.1)" section listing linked
  Supplementary Offers / Change Quotations with explicit "does not mean this Work Order has
  been amended" language, plus the same two create actions (role-gated).
- Opportunity detail page: new "Commercial Offers" table listing every Base/Supplementary/
  Change Quotation offer for the Opportunity with purpose, status, Base Offer reference and an
  Open action (each row carries `data-testid="commercial-offer-row-{public_id}"`, since the
  domain's own data design - a related offer's default title and its Base Offer column both
  legitimately repeat the Base Offer's code - makes a pure text/accessible-name row selector
  genuinely ambiguous for Playwright; this is the documented escape hatch, not a shortcut).

## TE-1 smoke-data harness extension

New scenarios (`backend/tooling/smoke_data/scenarios.py`):

```text
supplementary-offer-draft          Accepted Base Offer + one DRAFT Supplementary Offer, no copied data.
change-quotation-draft             Accepted Base Offer + Work Order + one DRAFT Change Quotation linked to it.
supplementary-offer-lifecycle      Accepted Base Offer + a Supplementary Offer taken to ACCEPTED independently.
related-offer-regression-bundle    multi_series_target (Base + Supplementary + Change Quotation),
                                    supplementary_offer_create_target (clean accepted Base, no WO),
                                    change_quotation_create_target (clean accepted Base + WO),
                                    related_offer_read_only_view (Base + Supplementary).
```

New builders (`backend/tooling/smoke_data/builders.py`): `add_offer_line` (adds a line to an
already-existing offer, distinct from `create_offer_with_line` which creates a brand-new offer),
`create_related_offer` (calls `create_related_commercial_offer` directly, never bypasses its
guards).

Cleanup extension (`backend/tooling/smoke_data/cleanup.py`):

```text
- _collect_ids now also scans each record's related_offers[] list.
- _find_all_owned_related_offer_ids discovers related offers created live (e.g. through a
  Playwright test) by base_offer_id ownership, mirroring the existing
  _find_all_owned_work_order_ids pattern for live-created Work Orders.
- _null_out_related_work_order_links breaks the new cross-table FK cycle before Work Orders
  are deleted.
```

`related-offer-regression-bundle` deliberately gives the Supplementary-creation and
Change-Quotation-creation Playwright tests **separate** Base Offer targets, matching the
existing `core-regression-bundle` isolation principle (no two tests mutate the same Commercial
Offer) - an earlier draft shared one target and produced order-dependent Playwright failures
during development; see the continuity note for the full story.

## Playwright extension

Three new specs under `e2e/tests/`:

```text
related-offer-supplementary-creation.spec.ts    Create Supplementary Offer from an accepted Base Offer.
related-offer-change-quotation-creation.spec.ts  Create Change Quotation from a Work Order.
related-offer-opportunity-listing.spec.ts        Opportunity shows all three offer series independently.
```

`e2e/tests/fixtures/manifest.ts` gained `loadRelatedOffersManifest()` (a second manifest file,
own run id, kept separate from `core-regression-bundle` rather than merged, so the two scenario
catalogues stay independently seedable/cleanable). `e2e/tests/global-setup.ts` warms the new
routes. `scripts/run-e2e.ps1` seeds `related-offer-regression-bundle` to
`e2e/.manifest/related-offers.json`, and cleans up **both** run ids in its `finally` block
(a failure in either cleanup call surfaces as the script's exit code). `docker-compose.yml`'s
`e2e` service gained `RELATED_OFFERS_MANIFEST_PATH`.

This is a deliberately scoped subset of the six Playwright scenarios the task description
enumerated (independent-lifecycle and read-only-role coverage for related offers are left to
backend/harness tests instead - see the acceptance doc's Known Limitations).

## Explicit exclusions

Everything under "Out of scope" above, plus: no Work Order release/posting, no equipment/crew
assignment, no billing, no document generation, and no change whatsoever to the frozen
`docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` (verified byte-for-byte
unchanged before and after this slice).
