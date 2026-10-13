# Slice 6O.2 - Work Order Amendment Intake Foundation

## Status

Implemented, in two coordinated parts on branch
`slice-6o2-work-order-amendment-intake-foundation`: Part 1 (backend model, migration,
service/repository/routes, backend tests, TE-1 smoke-data scenarios) and Part 2
(frontend UI, Playwright extension, exploratory browser testing, documentation, code
review, final validation).

## Objective

Follow on directly from Slice 6O.1 (Supplementary and Change Commercial Offer
Foundation) by adding a Work Order Amendment record: a customer-requested
administrative or commercial change captured against an existing Work Order shell as an
**intake/review record only**. An accepted Supplementary Offer or Change Quotation may
be cited as the amendment's commercial basis. Nothing in this slice applies an amendment
to the Work Order or its lines - that remains explicit future work.

## In scope

```text
- crm_work_order_amendment and crm_work_order_amendment_line tables (Alembic migration
  20260713_0029).
- Amendment types ADMINISTRATIVE / COMMERCIAL / MIXED.
- Amendment statuses RECEIVED / UNDER_REVIEW / VALIDATED / REJECTED / CANCELLED with a
  guarded transition matrix; VALIDATED/REJECTED/CANCELLED are terminal.
- A COMMERCIAL/MIXED amendment's VALIDATED transition requires a linked Supplementary
  Offer / Change Quotation that is currently ACCEPTED, checked live, plus at least one
  amendment line.
- Amendment line actions ADD_LINE / CHANGE_LINE / CANCEL_LINE, with an original-value
  snapshot captured at proposal time for CHANGE_LINE/CANCEL_LINE.
- Full CRUD/lifecycle route set under /api/work-orders/{public_id}/amendments/...
- WORK_ORDER_CREATE_ROLES-gated mutation, WORK_ORDER_READ_ROLES-gated read.
- Nine business events, every mutation payload carrying an explicit
  "applied_to_work_order": false.
- Work Order detail page: Amendments section (list, empty state, Record action).
- /work-orders/{workOrderId}/amendments/new intake page with locked Work Order/Account/
  Opportunity/Base Offer context and a commercial-basis selector scoped to offers
  already linked to that Work Order.
- /work-orders/{workOrderId}/amendments/{amendmentId} detail page: header, source
  context, summary, amendment lines (original vs proposed columns), lifecycle actions
  driven by the backend readiness view.
- A restrained "Record Work Order Amendment" action and linked-amendment list on the
  Commercial Offer detail page for an ACCEPTED related offer with a linked Work Order.
- TE-1 smoke-data harness: 5 new scenarios/targets (2 standalone,
  `work-order-amendment-regression-bundle` extended to 7 independent record sets),
  ownership-based cleanup for amendments/amendment lines (mirrors the existing Work
  Order / related-offer live-creation-discovery pattern).
- A third, independently seeded/cleaned Playwright manifest
  (`work-order-amendments.json`, own run id, own env var) alongside
  `core-regression-bundle` and `related-offer-regression-bundle`, and 5 new specs.
```

## Out of scope

```text
Application of a validated amendment to the Work Order (versioning, line replacement,
  effective totals)
Remaining-quantity / partial-award allocation logic
WO release/posting, equipment/crew assignment, scheduling
Billing, invoicing, log sheets, overtime, breakdown processing
Amendment document generation or customer communication
Automatic Supplementary Offer, Change Quotation, Work Order or amendment-application
  creation from any other action
Reopening or superseding a terminal amendment
A new fixture or E2E framework (the existing TE-1 harness and e2e/ workspace were
  extended, not replaced)
```

## Data model

See `docs/agent/contracts/work-order-amendment-contract.md` for the full field list,
transition matrix, commercial-basis validation rules and event catalogue.

## Deviation from directional guidance: who decides an amendment

*Added 7 October 2026 (TB-1 TB1-108); this slice did not record it when it was built, as
`AGENTS.md` ("Source document and directional-guidance governance", steps 1-8) requires.*

- **The source suggestion.** The System-of-Record matrix
  (`docs/source/current/governance/PBL_CRM_Equipment_Hiring_System_of_Record_Matrix_Clarified.md`,
  row "Amendment validation decision") makes Operations the process owner of the decision, with Sales
  approving the commercial interpretation, Finance the statutory or billing effects, and Management
  only beyond delegated authority.
- **Its classification.** Directional guidance (ADR-013; the matrix's own status note), not a frozen
  contract or an approved rule.
- **What this slice built instead.** The decision is one action for the four roles that record
  amendments - `ADMIN`, `SALES_USER`, `SALES_MANAGER`, `OPERATIONS_USER` - under the same permission,
  `WORK_ORDER_CREATE`, that creates Work Orders and attaches Work Order documents. No second approver.
- **Why that was acceptable.** "Validated" changes nothing on the Work Order - the matrix and the
  contract agree it must not be described as applied - so no business effect follows today; the
  approvals the matrix describes need `APR-001`, which is not built.
- **What it affects, and what stays open.** Work Orders and Documents (one permission for four
  capabilities: `DEFERRED_REQUIREMENTS.md`, "Creating a Work Order and deciding its amendments are one
  permission"). Whether PBL wants the decision separated from recording, or approved by Sales,
  Finance or Management, is a business question for `D-07` (applying amendments) or `APR-001`, not a
  settled one.

## Frozen-contract protection

- `docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` is byte-for-byte
  unchanged (verified before and after this slice).
- The Slice 6O.1 related-offer contract and every existing Commercial Offer lifecycle
  route are unchanged; this slice only reads a related offer's purpose, lineage and live
  status.

## Testing

See `docs/agent/acceptance/slice-6o2-work-order-amendment-intake-foundation-acceptance.md`
for the full validation record (backend, frontend, E2E, exploratory browser, code
review).

## Continuity

See `docs/continuity/SLICE_6O2_WORK_ORDER_AMENDMENT_INTAKE_FOUNDATION.md` for objective,
files changed, checks run and next recommended slice.
