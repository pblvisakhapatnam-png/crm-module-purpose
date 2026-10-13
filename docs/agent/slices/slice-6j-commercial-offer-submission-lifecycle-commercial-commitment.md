# Slice 6J - Commercial Offer Submission Lifecycle / Commercial Commitment Foundation

## Status

Implemented.

## Objective

Provide one controlled action that records a Commercial Offer as submitted/shared with the customer and therefore commercially committed for business traceability.

## Implemented Scope

Backend action:

```text
POST /api/commercial-offers/{public_id}/mark-submitted
```

No migration was required. The action uses the existing `SUBMITTED` lifecycle status, Commercial Offer lines, Slice 6I submission evidence and Slice 6I.2 manual credit/exposure review records.

Allowed starting statuses:

```text
DRAFT
READY_FOR_REVIEW
```

Hard validation requires:

- an existing Commercial Offer;
- manage-role authorization;
- an allowed starting status;
- Account traceability;
- Opportunity traceability;
- at least one active Commercial Offer line;
- at least one active submission evidence record;
- no current `REJECTED_OR_ON_HOLD` manual credit/exposure review.

Missing, `NOT_ASSESSED` or `APPROVAL_REQUIRED` manual credit review remains a returned warning, not a new hard block. T&C readiness remains advisory.

Generic Commercial Offer PUT updates may no longer transition a record into `SUBMITTED`; callers must use the controlled action.

## Successful Action

The action:

- sets status to `SUBMITTED`;
- copies submitted date/time and available reference from the latest submission evidence into existing Commercial Offer lifecycle fields;
- does not create submission evidence;
- emits `CommercialOfferCommerciallyCommitted`;
- returns the updated Commercial Offer, event and advisory warnings.

Event metadata includes previous/new status, latest submission evidence ID, latest manual credit review ID/status and explicit flags confirming commercial commitment, no automatic evidence, no exposure calculation and no Work Order creation.

## Submission Readiness

The advisory checklist now includes:

```text
COMMERCIAL_COMMITMENT_STATUS
```

`SUBMITTED` is a pass. Evidence without submitted lifecycle status remains attention-required and directs the user to the controlled action.

## Frontend

The Submission tab contains a local `Record as Submitted / Commercially Committed` action card showing current status, evidence count and latest manual credit-review status. Success, warnings and errors remain beside the action.

## Explicit Boundaries

The action does not generate or send quote/PDF documents, upload/store files, run SharePoint automation, calculate exposure, aggregate PAN-level exposure, complete Finance or legal/T&C approval, select line-level T&C, release/post a Work Order, bill, invoice or activate Customer Master.

## Handoff Contract Impact

The frozen Slice 6D.1 Accepted Commercial Offer -> Work Order handoff contract is unchanged. Marking an offer submitted does not create a Work Order.

