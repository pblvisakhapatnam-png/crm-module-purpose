# Slice 6I.2 - Commercial Offer Credit / Exposure Readiness Foundation

## Status

Implemented.

## Objective

Record manual credit/exposure review evidence for a Commercial Offer and include the latest review in the advisory submission-readiness checklist.

This is not a credit engine and not the initial Account/PAN prospect credit assessment.

## Implemented Scope

Database:

```text
commercial_offer_credit_review
```

The table stores append-only review history. Recording a new review supersedes the prior active record; history remains readable and the latest active record drives readiness.

Fields include review status, basis, reference, reviewed date/user, approved amount snapshot, credit days snapshot, exposure note, active/current state and audit timestamps.

Backend routes:

```text
GET  /api/commercial-offers/{public_id}/credit-review
POST /api/commercial-offers/{public_id}/credit-review
```

Read access follows Commercial Offer view roles. Create access follows Commercial Offer manage roles (`ADMIN`, `SALES_USER`, `SALES_MANAGER`). Backend authorization is authoritative.

Allowed statuses:

```text
NOT_ASSESSED
WITHIN_LIMIT_AS_PER_MANUAL_REVIEW
APPROVAL_REQUIRED
APPROVED_WITH_REFERENCE
REJECTED_OR_ON_HOLD
```

`APPROVED_WITH_REFERENCE` requires a review reference.

Creating a review emits:

```text
CommercialOfferCreditReviewRecorded
```

Reads do not create events. Review creation does not change Commercial Offer lifecycle status.

## Submission Readiness

The former deferred credit/exposure row is replaced by `CREDIT_EXPOSURE_REVIEW`:

```text
No review / NOT_ASSESSED                 -> ATTENTION_REQUIRED
WITHIN_LIMIT_AS_PER_MANUAL_REVIEW        -> PASS
APPROVED_WITH_REFERENCE                  -> PASS
APPROVAL_REQUIRED                        -> ATTENTION_REQUIRED
REJECTED_OR_ON_HOLD                      -> BLOCKING advisory
```

`BLOCKING` is advisory checklist language only. This slice adds no lifecycle or submission block.

## Frontend

The Commercial Offer Submission tab includes a Credit / Exposure Review section with current review summary, preserved history and a local-feedback add form.

After create, the UI refreshes review history and Submission Readiness.

## Explicit Boundaries

Not implemented:

- actual exposure or credit-limit calculation;
- PAN-level limit consumption;
- overdue, due, WIP, open quote or open Work Order aggregation;
- Finance ledger integration;
- Finance approval workflow;
- hard submission blocking;
- automatic lifecycle status changes;
- Customer Master activation;
- quote/PDF generation, uploads or SharePoint automation;
- legal/T&C approval or line-level T&C;
- Work Order release/posting or billing;
- dependency/security upgrades.

## Handoff Contract Impact

No change was made to the frozen Slice 6D.1 Accepted Commercial Offer -> Work Order handoff contract. The manual review reference is future-ready metadata only and is not added to the current thin handoff payload by this slice.

