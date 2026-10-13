# Slice 6I - Commercial Offer Submission Evidence Foundation

## Status

Implemented.

## Objective

Allow users to record metadata evidence that a Commercial Offer, customer-format quote or tender bid has been submitted/shared with the customer.

This supports the business concept that submitted/shared offers are commercially committed, while keeping this a foundation slice.

## Implemented Scope

Backend:

```text
- SQL Server-compatible Alembic migration for commercial_offer_submission_evidence.
- GET /api/commercial-offers/{public_id}/submission-evidence.
- POST /api/commercial-offers/{public_id}/submission-evidence.
- Backend read/write role enforcement.
- Multiple evidence records per Commercial Offer.
- Amount/currency snapshot from the current Commercial Offer.
- CommercialOfferSubmissionEvidenceRecorded business_event on create.
- Submission readiness checklist item for evidence present/missing.
```

Frontend:

```text
- Commercial Offer detail page shows a Submission Evidence section near Submission Readiness.
- Existing evidence records are listed.
- Sales/Admin users can add evidence metadata.
- Read-only roles can view evidence but cannot add it.
- Submission readiness refreshes after evidence is recorded.
```

## Data Model

New table:

```text
commercial_offer_submission_evidence
```

Fields:

```text
public_id
commercial_offer_id
submission_reference
submission_channel
submitted_at
submitted_by
recipient_summary
submitted_amount_snapshot
submitted_currency_snapshot
submitted_version_snapshot
document_reference_label
document_reference_url_or_path
evidence_notes
active
created_by
created_at
updated_at
```

Allowed submission channels:

```text
EMAIL
PORTAL
HAND_DELIVERY
CUSTOMER_FORMAT_UPLOAD
TENDER_PORTAL
OTHER
```

## Readiness Integration

`GET /api/commercial-offers/{public_id}/submission-readiness` now includes:

```text
SUBMISSION_EVIDENCE
```

Readiness meaning:

```text
- PASS when active submission evidence exists.
- ATTENTION_REQUIRED when no submission evidence metadata is recorded.
```

The checklist remains advisory and does not hard-block lifecycle actions.

## Lifecycle Decision

Slice 6I intentionally does not automatically change `offer_status_code`.

Existing Slice 4F lifecycle status capture remains available. Recording evidence is traceability metadata only. Formal submission workflow, document locking, approvals and exposure handling are deferred.

## Business Events

Create evidence emits:

```text
CommercialOfferSubmissionEvidenceRecorded
```

Event metadata includes:

```text
commercial_offer_public_id
submission_evidence_public_id
submission_channel
submitted_at
submission_reference
```

Evidence reads do not create events.

## Boundaries

Not implemented:

```text
- quote/PDF/document generation;
- file upload/storage;
- SharePoint/document automation;
- credit engine or exposure calculation;
- approval workflow;
- omitted mandatory T&C approval;
- T&C deviation/new-clause approval;
- line-level T&C selection;
- legal versioning;
- Work Order release/posting;
- billing logic;
- Customer Master activation;
- any change to the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract;
- dependency/security upgrades.
```

## Handoff Contract Impact

No change was made to the frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract.
