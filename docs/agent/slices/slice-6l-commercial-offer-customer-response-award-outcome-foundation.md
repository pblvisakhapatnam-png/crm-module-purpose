# Slice 6L - Commercial Offer Customer Response / Award Outcome Foundation

## Status

Implemented; final check results and pending manual items are recorded in the matching acceptance checklist.

## Objective

Record append-only customer response / award outcome metadata after Commercial Offer submission or resubmission, with clear lifecycle alignment for accepted/awarded and rejected/lost outcomes.

## Implemented Scope

Database table `commercial_offer_customer_response` stores multiple response records per Commercial Offer, optional same-offer submission-evidence/revision links, award snapshots and audit metadata.

Routes:

```text
GET  /api/commercial-offers/{public_id}/customer-responses
POST /api/commercial-offers/{public_id}/customer-responses
```

Outcomes:

```text
ACCEPTED_AWARDED
REJECTED_LOST
REVISION_REQUESTED
CLARIFICATION_REQUESTED
ON_HOLD
PENDING_CUSTOMER_DECISION
OTHER
```

Channels:

```text
EMAIL
TENDER_PORTAL
CUSTOMER_PO
LETTER_OF_AWARD
PHONE_OR_VERBAL
MEETING
OTHER
```

Only `SUBMITTED`, `ACCEPTED` and `REJECTED` offers accept response records. Draft, Ready for Review, Withdrawn and Closed offers are rejected. Same-offer ownership is required for linked submission evidence and revisions.

`ACCEPTED_AWARDED` aligns the offer to `ACCEPTED`; `REJECTED_LOST` aligns it to `REJECTED`. Other outcomes preserve the current offer status. The response and any status change are committed in one transaction.

Recording creates `CommercialOfferCustomerResponseRecorded` with previous/new offer status, link metadata, `status_changed` and `work_order_created: false`. Reads create no events.

Submission Readiness includes advisory `CUSTOMER_RESPONSE_AWARD_OUTCOME`. It does not add a Work Order handoff block.

The Submission tab lists latest/history records and provides a role-aware create form with local feedback, overflow-safe linked-record selectors and explicit no-automatic-Work-Order wording.

## Authorization

All Commercial Offer read roles can list. `ADMIN`, `SALES_USER` and `SALES_MANAGER` can record. Backend authorization is authoritative.

## Explicit Boundaries

No Work Order is created automatically. Existing accepted-offer-to-Work-Order shell creation remains a separate action. No Customer Master activation, Finance approval, Work Order release/posting, billing/execution, quote/PDF generation, file storage, SharePoint automation, full document management or full legal/versioning is implemented.

The frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract is unchanged. Full award-to-Work-Order readiness gating remains future work.
