# Work Order Amendment Contract - Slice 6O.2 Foundation

## Purpose

Slice 6O.2 adds a Work Order Amendment record that captures a customer-requested
administrative or commercial change against an existing Work Order shell as an
**intake/review record only**. It is the natural follow-on to Slice 6O.1 (Supplementary
and Change Quotation Commercial Offer foundation): an accepted Supplementary Offer or
Change Quotation may now be cited as the *commercial basis* for a Work Order Amendment,
but neither creating nor accepting a related offer, nor recording, reviewing or
validating an amendment, ever mutates the Work Order or any Work Order line.

**Non-application rule (read this first):** nothing under this contract is ever applied
to `crm_work_order` or `crm_work_order_line`. "Validated" means the amendment is
validated for future downstream processing, not that it has been applied. Explicit
application of a validated amendment to a Work Order (versioning, line replacement,
effective totals) is deferred to a future slice and must not be added under this
contract without a separate contract-change record.

## Data model

```text
crm_work_order_amendment
crm_work_order_amendment_line
```

`crm_work_order_amendment` is subordinate to `crm_work_order` (`work_order_id`, `NOT
NULL`, no `CASCADE`). `crm_work_order_amendment_line` is subordinate to
`crm_work_order_amendment` (`amendment_id`, `NOT NULL`) and optionally references a
source `crm_work_order_line` row (`source_work_order_line_id`, nullable - `NULL` for
`ADD_LINE`).

### Amendment header fields

```text
id
amendment_public_id
work_order_id
amendment_sequence_no          -- 1-based, per Work Order, assigned server-side
amendment_type_code            -- ADMINISTRATIVE | COMMERCIAL | MIXED
amendment_status_code          -- RECEIVED | UNDER_REVIEW | VALIDATED | REJECTED | CANCELLED
customer_amendment_reference   -- optional; unique per Work Order when provided
customer_amendment_date        -- optional
received_date                  -- required
effective_date                 -- optional
amendment_reason                -- required, free text
administrative_change_summary  -- optional
commercial_change_summary      -- required for COMMERCIAL/MIXED, else optional
related_commercial_offer_id    -- optional FK to crm_commercial_offer (the commercial basis)
customer_document_reference    -- optional metadata reference, not a file upload
decision_notes
reviewed_at / validated_at / rejected_at / cancelled_at
decided_by
remarks
created_by / created_at / updated_at
```

### Amendment line fields

```text
id
amendment_line_public_id
amendment_id
line_number                     -- 1-based, per amendment
action_code                     -- ADD_LINE | CHANGE_LINE | CANCEL_LINE
source_work_order_line_id       -- NULL for ADD_LINE; required for CHANGE_LINE/CANCEL_LINE
change_summary                  -- required for CHANGE_LINE/CANCEL_LINE
proposed_scope_description / proposed_equipment_service_category / proposed_quantity /
proposed_uom / proposed_rate_amount / proposed_currency_code / proposed_amount
original_scope_description / original_equipment_service_category / original_quantity /
original_uom / original_rate_amount / original_currency_code / original_amount /
original_source_offer_line_public_id
created_by / created_at / updated_at
```

`original_*` fields are a **snapshot captured at proposal time** from the referenced
Work Order line (and, transitively, its own `source_offer_line_public_id`). They are
never re-read from the live Work Order line after the amendment line is created, and
they are never written back to `crm_work_order_line`. `proposed_amount` is the simple
product of `proposed_quantity * proposed_rate_amount` when both are present, matching
the existing Commercial Offer line / Work Order line calculation convention - it is not
a final billing calculation.

## Amendment types

```text
ADMINISTRATIVE   -- no commercial basis required; e.g. site contact, mobilisation date
COMMERCIAL       -- requires an accepted commercial basis before it can be validated
MIXED            -- Administrative + Commercial in one record; also requires an accepted
                    commercial basis before it can be validated
```

`WORK_ORDER_AMENDMENT_COMMERCIAL_BASIS_REQUIRED_TYPES = (COMMERCIAL, MIXED)`.

## Amendment statuses and transition matrix

```text
RECEIVED       -- initial status on creation
UNDER_REVIEW
VALIDATED      -- terminal
REJECTED       -- terminal
CANCELLED      -- terminal
```

```text
RECEIVED     -> UNDER_REVIEW | REJECTED | CANCELLED
UNDER_REVIEW -> VALIDATED | REJECTED | CANCELLED
```

`VALIDATED`, `REJECTED` and `CANCELLED` are terminal for this foundation: no reopening
or supersession workflow exists. `RECEIVED` and `UNDER_REVIEW` are the only editable
statuses (header edit, line add/update/remove). A reason is required to move an
amendment to `REJECTED` or `CANCELLED`; it is optional for `UNDER_REVIEW`.

### Validation precondition (the `VALIDATED` gate)

An amendment can move to `VALIDATED` only when, checked live (never cached):

```text
1. Required header info is present: amendment_reason, and commercial_change_summary
   for COMMERCIAL/MIXED.
2. If commercial_basis_required (COMMERCIAL/MIXED): a related Commercial Offer is
   linked AND that offer's current offer_status_code is ACCEPTED. A DRAFT or
   SUBMITTED related offer may be linked as a *pending* basis at intake time - the
   amendment can still be moved to UNDER_REVIEW - but VALIDATED is blocked until the
   linked offer independently reaches ACCEPTED through its own Slice 6L Customer
   Response lifecycle.
3. If not ADMINISTRATIVE: at least one amendment line exists. This foundation has no
   separate non-line commercial-term model (e.g. payment terms) on the Work Order, so
   a Commercial/Mixed amendment always needs at least one line to describe what
   changed.
```

`GET /api/work-orders/{public_id}/amendments/{amendment_public_id}/readiness` exposes
this as a derived, read-only view (`can_move_to_under_review`, `can_move_to_validated`,
`blocking_reasons`, `advisory_message`, `applied_to_work_order` - always `false`). The
readiness route is guidance only; `POST .../decision` independently re-validates every
precondition itself rather than trusting a client-supplied readiness snapshot.

## Commercial basis (related Commercial Offer) validation

A Commercial Offer cited via `related_commercial_offer_public_id` must, checked at
intake time (structural checks) and again live at `VALIDATED`-transition time (status
check only):

```text
- offer_purpose in (SUPPLEMENTARY, CHANGE_QUOTATION) - never BASE.
- related_work_order_id (Slice 6O.1 field) equals this amendment's Work Order's
  internal id.
- Its Opportunity (and Account, where both sides carry a value) match this Work
  Order's own Opportunity/Account lineage, as a defense-in-depth check alongside the
  primary related_work_order_id equality check.
```

Rejections use precise wording distinguishing "Base Offer cannot be commercial basis"
from "not linked to this Work Order" from "different Opportunity/Account" so the UI can
surface the real reason rather than a generic 422.

## Amendment line actions

```text
ADD_LINE      -- proposes a brand-new line; must NOT reference a source Work Order line;
                 proposed_scope_description is required.
CHANGE_LINE   -- proposes revising an existing Work Order line; source_work_order_line_public_id
                 is required and must belong to this amendment's own Work Order;
                 change_summary is required.
CANCEL_LINE   -- proposes cancelling an existing Work Order line; same source-line and
                 change_summary requirements as CHANGE_LINE.
```

Amendment lines can be added, updated (proposed values / change summary only - `action_code`
and `source_work_order_line_public_id` are immutable after creation; delete and recreate
the line if the wrong action/source was chosen) or removed only while the parent
amendment is in an editable status (`RECEIVED` or `UNDER_REVIEW`).

## Routes

```text
GET    /api/work-orders/{public_id}/amendments
POST   /api/work-orders/{public_id}/amendments
GET    /api/work-orders/{public_id}/amendments/{amendment_public_id}
PUT    /api/work-orders/{public_id}/amendments/{amendment_public_id}
POST   /api/work-orders/{public_id}/amendments/{amendment_public_id}/decision
GET    /api/work-orders/{public_id}/amendments/{amendment_public_id}/readiness
GET    /api/work-orders/{public_id}/amendments/{amendment_public_id}/lines
POST   /api/work-orders/{public_id}/amendments/{amendment_public_id}/lines
PUT    /api/work-orders/{public_id}/amendments/{amendment_public_id}/lines/{line_public_id}
DELETE /api/work-orders/{public_id}/amendments/{amendment_public_id}/lines/{line_public_id}
```

`PUT .../amendments/{id}` is a header-field edit only, available while the amendment is
`RECEIVED` or `UNDER_REVIEW`. It deliberately excludes `amendment_type_code` and
`amendment_status_code`: type reclassification is not supported (create a new amendment
if the type was wrong), and status transitions must go through the dedicated `/decision`
action so every transition is validated and event-logged consistently.

## Authorization

```text
Create amendment, edit header, line add/update/remove, decision:
  ADMIN, SALES_USER, SALES_MANAGER, OPERATIONS_USER
  (same set as WORK_ORDER_CREATE_ROLES - the existing Work Order shell creation roles)

Read (list/detail/lines/readiness):
  ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER, OPERATIONS_USER, MANAGEMENT_READ_ONLY
  (same set as WORK_ORDER_READ_ROLES)
```

Backend authorization is authoritative; the frontend hides mutation controls for
unauthorized roles as a usability aid only.

## Business events

```text
WorkOrderAmendmentRecorded
WorkOrderAmendmentUpdated
WorkOrderAmendmentMovedUnderReview
WorkOrderAmendmentValidated
WorkOrderAmendmentRejected
WorkOrderAmendmentCancelled
WorkOrderAmendmentLineAdded
WorkOrderAmendmentLineUpdated
WorkOrderAmendmentLineRemoved
```

Every amendment event uses `source_module = work_orders`, `record_type = work_order`
and `record_public_id = <the parent Work Order's own public_id>` - mirroring the
existing subordinate-metadata event pattern used by `commercial_offer_revision` /
`commercial_offer_customer_response` (see `commercial_offers/service.py`) rather than
inventing a new event `record_type` for a record that has no independent lifecycle
outside its parent. Every event payload that touches amendment state includes an
explicit `"applied_to_work_order": false` field so audit consumers never have to infer
non-application from absence of evidence. Read routes never create events; a rejected
mutation (failed validation, blocked transition, unauthorized attempt) creates no event
either.

## Readiness / guidance response shape

```text
GET /api/work-orders/{public_id}/amendments/{amendment_public_id}/readiness

{
  "amendment_public_id": "...",
  "amendment_type_code": "COMMERCIAL",
  "amendment_status_code": "UNDER_REVIEW",
  "is_editable": true,
  "has_required_header_info": true,
  "commercial_basis_required": true,
  "related_offer_linked": true,
  "related_offer_accepted": false,
  "has_required_change_detail": true,
  "can_move_to_under_review": false,
  "can_move_to_validated": false,
  "blocking_reasons": [
    "The linked Supplementary Offer / Change Quotation must be Accepted through its own lifecycle before this amendment can be validated."
  ],
  "advisory_message": "This amendment is not yet ready to be validated. See blocking reasons.",
  "applied_to_work_order": false
}
```

This is a derived read model only - nothing in it is persisted, and every mutation
route re-validates its own preconditions independently rather than trusting this
snapshot (the same discipline the Slice 6M lifecycle-guidance view follows for
Commercial Offers).

## Frontend surfaces

```text
/work-orders/{workOrderId}                              -- Work Order Amendments section (list + empty state)
/work-orders/{workOrderId}/amendments/new                -- intake form, locked Work Order/Account/
                                                              Opportunity/Base Offer context
/work-orders/{workOrderId}/amendments/{amendmentId}       -- header, source context, summary, lines,
                                                              lifecycle actions
```

The Commercial Offer detail page (Traceability tab) shows a restrained "Record Work
Order Amendment" action for a related offer (`offer_purpose != BASE`) only while it is
`ACCEPTED` and has a linked Work Order, plus a read-only list of amendments already
linked to that offer as commercial basis. It never appears for a Base Offer, a
non-accepted related offer, or a read-only role.

UI wording is deliberately restrained throughout: "Amendment intake", "Recorded
customer amendment", "Validated for future downstream processing", "Not yet applied to
the Work Order". No screen implies that recording or validating an amendment changed
the Work Order or its lines.

## Compatibility with frozen contracts

- The frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract
  (`docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md`) is
  unchanged; Work Order Amendments are a downstream, subordinate concept layered on
  top of an existing Work Order shell, not a change to how that shell is created.
- The Slice 6O.1 related-offer contract
  (`docs/agent/contracts/commercial-offer-contract.md`, Slice 6O.1 section) is
  unchanged; a related offer's own lifecycle routes are untouched. This contract only
  *reads* a related offer's purpose, lineage and live status to validate it as a
  commercial basis.

## Explicit exclusions from Slice 6O.2

```text
Application of a validated amendment to the Work Order (versioning, line replacement,
  effective totals)
Remaining-quantity / partial-award allocation logic
Equipment/crew assignment, scheduling, WO release/posting
Billing, invoicing, log sheets, overtime, breakdown processing
Amendment document generation or customer communication
Automatic creation of a Supplementary Offer, Change Quotation, Work Order or amendment
  application from any other action
Reopening or superseding a terminal (VALIDATED/REJECTED/CANCELLED) amendment
Full approval workflow beyond the RECEIVED -> UNDER_REVIEW -> VALIDATED/REJECTED/CANCELLED
  transition matrix above
```

## Slice 9B concurrency requirement, 7 September 2026

Slice 9B adds no field, route, status or transition here. It records one normative requirement
that the Slice 6O.2 implementation left implicit.

Two invariants are read-then-write and must be locked.

**1. The commercial basis.** `decide_work_order_amendment` requires the cited Supplementary Offer
or Change Quotation to be currently `ACCEPTED` before it may write `VALIDATED`. `ACCEPTED` is not
immutable - the Slice 6L customer-response route can move an accepted offer to `REJECTED` - so a
concurrent rejection could land between the readiness check and the commit, validating an
amendment against a rejected basis. The decision now calls the Work Order module's
`lock_commercial_offer_row` on that offer **before** the readiness read.

**2. The amendment itself.** Five functions read `amendment_status_code`, check it is
non-terminal, and then write: `update_work_order_amendment`, `decide_work_order_amendment`,
`create_work_order_amendment_line`, `update_work_order_amendment_line` and
`delete_work_order_amendment_line`. Without a lock, a line could be added, changed or deleted
while a decision was committing `VALIDATED`, so the validated amendment would not be the amendment
that was reviewed.

All five now obtain the amendment through `_get_amendment_and_id(..., for_update=True)`, which
calls `lock_work_order_amendment_row` before the read. **Any future mutating path must pass
`for_update=True`.** The lock is taken on the amendment **header**, which is the aggregate root:
locking individual line rows would leave add and delete raceable, because a row that does not
exist yet cannot be locked.

The three read-only paths - `get_work_order_amendment`, `get_work_order_amendment_readiness` and
`list_work_order_amendment_lines` - deliberately take no lock, so ordinary reads are not
serialized behind a review.

Unchanged: the transition matrix, the amendment types, the line actions, the snapshot behaviour,
the events, the permissions, and the rule that nothing here is ever applied to `crm_work_order` or
`crm_work_order_line`.

### Amendment creation, added 8 September 2026

Intake is a third read-then-write path, and it cannot lock the row it is about to insert.
`create_work_order_amendment` computes `amendment_sequence_no` as `MAX(...) + 1` for the Work
Order and checks that `customer_amendment_reference` is not already used on it, then inserts.
Both reads are over that Work Order's existing amendments, so **creation locks the parent Work
Order row** through `_get_work_order_and_id(..., for_update=True)` before either read.

Without it, two concurrent valid intakes read the same maximum and the same "no duplicate
reference" answer, and the second insert violates
`uq_crm_work_order_amendment_wo_sequence` or
`ux_crm_work_order_amendment_customer_reference` - constraints neither user broke - surfacing as
an unhandled database error instead of a business message. Any future path that derives a value
from a Work Order's existing amendments and then inserts must take the same lock.

## UI cleanup package (September 2026): display names

Recorded 11 September 2026. One additive, read-only field so the screen can show a name instead of
a user public ID:

```text
WorkOrderAmendmentResponse   (GET /api/work-orders/{public_id}/amendments,
                              GET /api/work-orders/{public_id}/amendments/{amendment_public_id},
                              and the create, update and decision responses that embed it)
    created_by_display_name   beside created_by
```

The field is `string | null`, resolved from `app_user.display_name` matched on
`app_user.public_id` in the same query (a LEFT JOIN), and `null` when `created_by` is null or does
not match any user; the amendment is still returned in that case. `created_by` is unchanged.
`decided_by` and amendment lines are not resolved by this package. Nothing here changes the
non-application rule. No route, permission, request field, business event or migration change.

## TB-1 fix TB1-600 (4 October 2026): the currency list

`proposed_currency_code` on an amendment line (`WorkOrderAmendmentLineCreate`, `WorkOrderAmendmentLineUpdate`) is
checked against the one list in `backend/app/shared/currency.py`: INR, USD, GBP, EUR. Empty still means none
proposed; any other code is refused with `422` and `Currency must be one of INR, USD, GBP, EUR.` The screen offers the
list with "None proposed" first. `original_currency_code` is still copied from the Work Order line. No route,
permission, response field, business event or migration change, and the non-application rule is untouched. The
decision is recorded in the Commercial Offer contract's TB1-600 section.
