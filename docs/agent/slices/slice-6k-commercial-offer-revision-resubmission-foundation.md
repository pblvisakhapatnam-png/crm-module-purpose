# Slice 6K - Commercial Offer Revision / Resubmission Foundation

## Status

Implemented; final automated and manual results are recorded in the matching acceptance checklist.

## Objective

Record lightweight revision/resubmission cycles after a Commercial Offer has been submitted/shared with the customer, while preserving the original submission evidence and Commercial Offer identity.

This is traceability metadata only. It is not a full quote versioning engine.

## Implemented Scope

Database:

```text
commercial_offer_revision
```

The record stores label, reason, notes, status, optional source submission evidence, optional resubmission evidence, opened/resubmitted/cancelled timestamps and audit identities.

Backend routes:

```text
GET  /api/commercial-offers/{public_id}/revisions
POST /api/commercial-offers/{public_id}/revisions
POST /api/commercial-offers/{public_id}/revisions/{revision_public_id}/mark-resubmitted
POST /api/commercial-offers/{public_id}/revisions/{revision_public_id}/cancel
```

Revision statuses:

```text
OPEN
RESUBMITTED
CANCELLED
```

Revision reasons:

```text
CUSTOMER_CLARIFICATION
RATE_CORRECTION
SCOPE_CHANGE
TENDER_CORRIGENDUM
INTERNAL_CORRECTION
OTHER
```

Rules:

- Only a `SUBMITTED` Commercial Offer can open a revision.
- Only one `OPEN` revision cycle is allowed per Commercial Offer. A user must mark it resubmitted or cancelled before starting the next cycle.
- `revision_label` is optional on create. Blank/missing labels are generated as `Rev N` from the existing revision sequence; users may override the suggestion with a descriptive label.
- Source and resubmission evidence must be active submission-evidence records for the same Commercial Offer.
- Mark Resubmitted requires an existing evidence record and does not create evidence automatically.
- Only an `OPEN` revision can become `RESUBMITTED` or `CANCELLED`.
- Revision records are not deleted.
- The Commercial Offer remains the same record and retains its existing lifecycle status.
- No Commercial Offer lines or Work Orders are created by revision actions.

## Readiness Integration

Submission Readiness includes `REVISION_RESUBMISSION_TRACEABILITY`:

- latest `OPEN` revision on a `SUBMITTED` offer: `ATTENTION_REQUIRED` with “Open revision exists; resubmission evidence not yet recorded.”;
- latest `RESUBMITTED` revision: `PASS` with “Latest revision has resubmission evidence.”;
- latest `CANCELLED` revision or no revision: informational `PASS`.

This row is advisory and is not a hard lifecycle block.

## Business Events

```text
CommercialOfferRevisionOpened
CommercialOfferRevisionResubmitted
CommercialOfferRevisionCancelled
```

Event metadata includes Commercial Offer public ID, revision public ID/label, previous/new revision status and linked source/resubmission evidence public IDs where present. Revision reads create no events.

## Frontend

The Commercial Offer Submission tab includes a `Revisions / Resubmissions` section with:

- a latest/original submission-evidence summary;
- a `Start revision / resubmission cycle` form with an auto-suggested next `Rev N` label that can be overridden;
- overflow-safe form controls and long evidence/reference display;
- history cards titled `Revision cycle: <label>`;
- actions only on the current OPEN card; and
- local feedback beside the triggering create or transition action.

Historical RESUBMITTED/CANCELLED cards remain visible without active actions or irrelevant empty timestamp rows.

The section explicitly states that full quote versioning, quote/PDF generation, file storage and legal versioning are deferred.

## Authorization

Commercial Offer read roles can list revision history. Commercial Offer manage roles (`ADMIN`, `SALES_USER`, `SALES_MANAGER`) can open, mark resubmitted and cancel. Backend enforcement is authoritative.

## Explicit Boundaries

Slice 6K does not:

- clone Commercial Offers or create new lines;
- implement a full quote/legal versioning engine or version comparison;
- generate, send, upload or store quote/PDF documents;
- automate SharePoint or email;
- calculate or aggregate credit exposure;
- implement Finance, commercial, legal or T&C approval;
- change Work Order handoff, release/posting, billing or Customer Master activation.

## Handoff Contract Impact

The frozen Slice 6D.1 Accepted Commercial Offer -> Work Order handoff contract is unchanged.
