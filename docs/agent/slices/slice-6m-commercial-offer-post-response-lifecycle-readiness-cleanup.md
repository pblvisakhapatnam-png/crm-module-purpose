# Slice 6M - Commercial Offer Post-Response Lifecycle Readiness Cleanup

## Status

Implemented.

## Objective

Consolidate the Commercial Offer lifecycle after Slice 6L customer-response recording into one coherent, backend-derived readiness view, and cleanly connect accepted awards to the existing explicit Slice 5A/6D.1 Work Order handoff without changing the frozen handoff contract.

## Scope

In scope:

```text
- Read-only derived lifecycle/readiness endpoint over existing Slice 6H/6I/6I.2/6J/6K/6L records.
- One coherent Submission-tab narrative: readiness -> commitment/revision history -> customer response -> derived guidance -> Work Order handoff state.
- Frontend reuse of the derived flags to avoid scattered/contradictory action panels.
- Regression tests proving existing guards already prevent invalid post-response actions.
```

Out of scope (unchanged, per the calling instructions):

```text
- Automatic Work Order creation.
- Production Work Order processing, scheduling, equipment/crew assignment, billing, invoicing, execution.
- Customer portal or communication modules.
- Award amendment workflow.
- Partial-award allocation redesign.
- New credit engine or exposure calculation.
- Demo data / vendor walkthrough scripts.
- Any change to the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract.
```

## Investigation Findings

Before writing code, the existing guards were reviewed against every Slice 6L outcome:

```text
- Revision creation already requires offer_status_code == SUBMITTED, so it is already
  rejected once a customer response has moved the offer to ACCEPTED or REJECTED.
- Customer-response recording already allows SUBMITTED/ACCEPTED/REJECTED (intentional
  chronological follow-up), so no change was needed there.
- Work Order handoff already requires offer_status_code == ACCEPTED plus Account
  traceability, and status only reaches ACCEPTED through ACCEPTED_AWARDED (or a
  pre-existing, out-of-scope direct PUT), so every other 6L outcome already leaves
  the offer non-ACCEPTED and handoff already blocked.
- There is no "duplicate Work Order" backend guard, by design: the frozen Slice 6D.1
  contract explicitly states one accepted Commercial Offer may create one or more Work
  Order shells for partial award. Slice 6M does not add a backend block for this,
  per instruction to preserve the frozen contract over a conflicting UI convenience.
  Instead, the frontend simply stops offering the "Create" action by default once a
  shell already exists (see Frontend Changes), while the backend and an explicit
  `/work-orders/new?commercialOfferId=...` navigation still allow a genuine additional
  shell if the user deliberately proceeds.
```

Because the guards already held, Slice 6M added no new backend rejections to existing
endpoints; it only added the derived read-only view and the tests proving the above.

**Reconciliation, 8 October 2026 (TB-1 CS-04 part 1).** Two findings above no longer hold. "No duplicate Work Order
backend guard, by design" let the same accepted lines be handed off twice - two requests at once gave two Work Orders
(TB-1 TB1-300) - and the guard read neither the offer's purpose nor its latest response, so an accepted Change
Quotation, or an Accepted offer whose latest response was on hold, was handed off too. By the owner's decisions of 8
October 2026, recorded as a dated amendment of the frozen handoff contract, the handoff now refuses what is already on
Work Orders (an offer line's quantity goes onto Work Orders once, whole or in parts), a Change Quotation, and an offer
whose latest response is not the acceptance; and a lost response is refused while the offer has a Work Order. The
offer page offers "Create another Work Order" while anything is left. See
`docs/continuity/TB1_103_WORK_ORDER_HANDOFF_ONCE_PER_LINE.md`. The text above is kept as Slice 6M wrote it.

## Backend Changes

```text
backend/app/modules/commercial_offers/contract.py   - lifecycle-state code/label constants
backend/app/modules/commercial_offers/repository.py - list_linked_work_order_contexts_for_offer (reads crm_work_order directly, same cross-module raw-SQL pattern already used elsewhere in this repository)
backend/app/modules/commercial_offers/schemas.py    - CommercialOfferLifecycleGuidanceResponse, CommercialOfferLinkedWorkOrderSummary
backend/app/modules/commercial_offers/service.py    - get_commercial_offer_lifecycle_guidance (pure derivation, no new persistence, no event)
backend/app/modules/commercial_offers/routes.py     - GET /api/commercial-offers/{public_id}/lifecycle-guidance
```

New route:

```text
GET /api/commercial-offers/{public_id}/lifecycle-guidance
```

Read-only; uses the existing Commercial Offer read-role set; creates no `business_event`.

Response fields (see schema for exact types): `latest_customer_response_outcome/public_id/received_at`, `lifecycle_state` (machine code) and `lifecycle_state_label`, `is_commercially_active`, `advisory_message`, `recommended_next_action`, `can_open_revision`, `has_open_revision_awaiting_resubmission`, `can_record_customer_response`, `work_order_handoff_available`, `work_order_handoff_blocked_reasons`, `linked_work_orders`.

`work_order_handoff_available` also now accounts for the existing "at least one active Commercial Offer line" precondition already enforced by the Work Order handoff endpoint, in addition to Accepted status and Account traceability, so the derived view never contradicts the real guard.

The latest customer response (by the existing Slice 6L ordering) takes precedence for `REVISION_REQUESTED`, `CLARIFICATION_REQUESTED`, `ON_HOLD`, `PENDING_CUSTOMER_DECISION` and `OTHER`, even if `offer_status_code` alone would look eligible (for example, a follow-up non-final response recorded after an earlier acceptance).

## Frontend Changes

```text
frontend/app/commercial-offers/[commercialOfferId]/page.tsx
```

- Added a "Lifecycle Guidance" section in the Submission tab, positioned after Customer Response / Award Outcome and before Submission Evidence.
- The panel renders the backend-provided state label, advisory message, recommended next action, boolean flags and blocked reasons directly; it does not reimplement lifecycle rules in TypeScript.
- Existing linked Work Order shells are listed with an "Open Work Order shell" action reusing existing origin-aware navigation.
- The header button, Traceability tab and Lifecycle Guidance panel now share one derived `workOrderHandoffAvailable` value (backend flag once loaded, falling back to the pre-6M check only before it loads) so they cannot disagree.
- A separate `canOfferCreateWorkOrderAction` flag additionally requires zero existing linked Work Orders before showing the "Create Work Order shell" action anywhere on the page. This keeps the frozen contract's multi-shell/partial-award support intact (the backend guard is unchanged and an additional shell remains reachable by navigating to the Work Order create page directly) while the default UI never offers a duplicate-looking "Create" action next to an existing shell.

## Tests

`backend/tests/test_commercial_offers_api.py` gained:

```text
test_lifecycle_guidance_tracks_latest_customer_response_and_work_order_state
test_lifecycle_guidance_rejected_closed_and_blocked_by_missing_active_lines
```

covering: no response, all seven 6L outcomes, latest-wins-over-older ordering, Accepted+eligible, Accepted+existing-Work-Order (informational only), Accepted+blocked-by-missing-active-lines (a real, reachable precondition, exercised by cancelling the only active line after acceptance), Rejected/closed, revision-after-rejected rejection (regression), Work-Order-creation rejection when not Accepted and when blocked, missing offer 404, unauthenticated 401, and no `business_event` created by GET reads.

A local `cleanup_test_work_orders` helper was added because the shared `cleanup_test_records` helper does not clean `crm_work_order`/`crm_work_order_line`, which is required by the one new test that creates a real Work Order shell.

## Migration / Alembic

None. Fully derived from existing Slice 4E/6H/6I/6I.2/6J/6K/6L records and the existing `crm_work_order` table. Alembic head remains `20260712_0027`.

## Manual Smoke

Performed against the running app in the Browser pane with eight representative Commercial Offers created via API (no response, each of the six non-final/final 6L outcomes, Accepted with no Work Order, Accepted with an existing Work Order). See the acceptance checklist for the full point-by-point record.

## Frozen Handoff Contract

`docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` is byte-for-byte unchanged (verified with `git diff`). The Work Order handoff route, payload, permissions, event names and duplicate-shell allowance are all unchanged; Slice 6M only reads existing Work Order rows for display.

## Known Limitations / Deferred

```text
- The generic Commercial Offer PUT lifecycle endpoint can still move a Draft/Ready
  offer directly to Accepted/Rejected without a Slice 6L customer-response record,
  a pre-existing (Slice 4C/4F) capability that Slice 6M did not remove, since doing
  so was out of scope and risked breaking the existing Slice 5A/6A Work Order tests
  that rely on this path. The derived readiness view treats offer_status_code as
  authoritative in that case, matching the real Work Order handoff guard.
- Full award-to-Work-Order readiness gating beyond Account traceability and active
  lines (for example a future Commercial Offer credit/exposure gate) remains future
  work per Slice 6I.3/FUTURE_SLICES.
- Slice 6N (originally anticipated as a separate Accepted Offer -> Work Order handoff
  guard/UX slice) is substantially absorbed by this slice; see FUTURE_SLICES.md for
  the resulting renumbering.
```
