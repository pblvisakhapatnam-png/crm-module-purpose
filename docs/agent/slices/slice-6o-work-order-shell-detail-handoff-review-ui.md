# Slice 6O - Work Order Shell Detail and Handoff Review UI

## Objective

Improve the accepted Commercial Offer -> Work Order shell handoff experience and the Work Order shell detail page so a user can review the source offer before handoff, understand exactly what the shell represents, and trace it back to the Commercial Offer, Opportunity, Account and source Commercial Offer lines - without changing the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract or any backend business rule.

This is a UI and traceability polish slice, not a redesign of Work Order business processing.

## Scope

In scope:

```text
- A "Work Order handoff review" snapshot inside the existing Lifecycle Guidance panel on the
  Commercial Offer Submission tab, shown only while the offer is Accepted: offer reference,
  status, mode/type, date, value, Account, Opportunity, active line count and a short line
  summary, plus an explicit "no Work Order created yet" / "N shell(s) already exist" statement.
- Minor context enrichment on the existing `/work-orders/new` handoff review/create page: offer
  mode/type/date display and an explicit existing-shell summary before the create action.
- A substantially improved Work Order shell detail page: a "Handoff shell" status badge,
  created-by/last-updated fields, a "Handoff provenance" section (creation timestamp, creator,
  and - for Admin/Management Read Only roles - the underlying WorkOrderCreated business event),
  and a contained, responsive table for Work Order line traceability showing each line's source
  Commercial Offer line identity.
- A narrow, backward-compatible extension to the existing `GET /api/events/recent` route: optional
  `record_type` / `record_public_id` query filters, reusing the existing business_event table,
  permissions (ADMIN / MANAGEMENT_READ_ONLY only) and read-only semantics.
- Backend regression/traceability tests for Work Order detail, line source identity, the new
  event filter, and partial-award (multiple shells from one offer) behavior.
```

Out of scope (unchanged from prior slices):

```text
- Automatic Work Order creation.
- A new handoff mutation contract or any change to POST /api/work-orders/from-commercial-offer.
- Partial-award allocation/remaining-quantity logic.
- Work Order editing, approval, release/posting.
- Customer Master activation, equipment/crew assignment, log sheets, billing, invoicing.
- Any change to the frozen Slice 6D.1 handoff contract file.
```

## Design decisions

- The Commercial Offer "handoff review" content was added to the existing Lifecycle Guidance
  panel (Submission tab) rather than a new panel, because Slice 6M already derives the
  authoritative `work_order_handoff_available` / `linked_work_orders` / blocked-reasons state
  there. Duplicating that logic in a second panel would risk disagreement between two UI
  surfaces; reusing it keeps the review truthful by construction.
- The events filter was added to the existing `/api/events/recent` route instead of a new
  route or a new "audit" subsystem, per repository guidance to avoid inventing new audit
  infrastructure. The filter is optional and backward compatible - omitting it reproduces the
  prior unfiltered behavior exactly.
- The Work Order detail page keeps showing raw UUIDs for Account/Opportunity/source-offer-line
  references (as links where a target page exists), matching the existing convention across the
  whole app (Commercial Offer, Opportunity and Account pages already show raw public IDs; no
  page in this repository resolves a friendly name for a linked record).
- The default "Create Work Order shell" action continues to be hidden once one shell already
  exists for an offer (established in Slice 6M/6M.1). This slice does not add allocation logic
  to distinguish a legitimate additional partial-award shell from an accidental duplicate; the
  frozen contract's multi-shell support remains reachable directly through
  `POST /api/work-orders/from-commercial-offer` (proven by a new regression test), just not
  offered as a second one-click UI action.

## Backend changes

```text
backend/app/modules/events/repository.py  - list_recent_business_events gains optional
                                             record_type / record_public_id filters.
backend/app/modules/events/service.py     - get_recent_business_events passes the new filters
                                             through.
backend/app/modules/events/routes.py      - GET /api/events/recent accepts optional
                                             record_type / record_public_id query parameters.
```

No changes were made to `backend/app/modules/work_orders/*` or
`backend/app/modules/commercial_offers/*`. No migration was added or required.

## Frontend changes

```text
frontend/app/commercial-offers/[commercialOfferId]/page.tsx
  - Lifecycle Guidance panel (Submission tab) gains a "Work Order handoff review" snapshot,
    visible only while offer_status_code === "ACCEPTED".

frontend/app/work-orders/new/page.tsx
  - CommercialOffer type gains offer_mode/offer_type/offer_date; the source-offer card displays
    them plus an explicit "no Work Order yet" / "N shell(s) already exist" statement fetched via
    the existing GET /api/work-orders?commercial_offer_public_id= filter.
  - After a successful create, the newly created shell is appended to local state immediately so
    the panel does not show stale "no Work Order yet" text next to the success message.

frontend/app/work-orders/[workOrderId]/page.tsx
  - "Handoff shell" status badge, created-by/last-updated fields on the snapshot.
  - New "Handoff provenance" section: creation timestamp/creator for all roles, plus the filtered
    WorkOrderCreated business event for Admin/Management Read Only roles.
  - Work Order lines rendered as a contained, responsive data table (reusing the existing
    `.data-table-wrap` / `.data-table` CSS pattern already used elsewhere in the app) showing
    scope, category, quantity/UOM, rate, amount and the source Commercial Offer line identifier.
```

## Backend tests added/updated

```text
backend/tests/test_events.py
  - test_recent_events_can_filter_by_record_type_and_public_id
  - test_recent_events_filter_by_unmatched_record_returns_empty_list

backend/tests/test_work_orders_api.py
  - test_work_order_detail_traceability_and_read_creates_no_event
  - test_work_order_multiple_lines_remain_traceable
  - test_work_order_partial_award_allows_additional_shell_from_same_offer
  - test_events_recent_filter_still_rejects_sales_user
```

## Results

```text
Alembic head: unchanged (no migration).
Focused tests (test_events.py + test_work_orders_api.py): 15 passed.
Full backend suite: 149 passed.
Frontend production build: passed, no TypeScript errors.
Frontend test command: "Frontend automated tests not configured" (unchanged baseline).
Frozen Slice 6D.1 handoff contract file: byte-for-byte unchanged (SHA-256 verified before and
  after this slice).
```

## Known limitations / deferred work

```text
- No allocation/remaining-quantity model was added; a second Work Order shell for the same
  accepted offer remains reachable only through the API or a fresh /work-orders/new visit with
  the same commercialOfferId, not a dedicated "create additional shell" UI action.
- Business event provenance on the Work Order detail page is visible only to Admin / Management
  Read Only roles, matching the existing Events module permission model; other roles see the
  handoff creation timestamp and creator but not the full event list.
- Mobile/narrow-viewport verification relied on computed CSS (`.data-table-wrap` has
  `overflow-x: auto`, matching the same pattern already used on Accounts/Leads/Opportunities list
  pages) rather than a live screenshot, because the browser tool's resize/screenshot actions were
  not reliably reflecting a changed `window.innerWidth` in this environment during this session.
```

## Next recommended slice

`6P - Demo Data and Vendor Walkthrough Scenario Pack`, per `docs/agent/FUTURE_SLICES.md`.
