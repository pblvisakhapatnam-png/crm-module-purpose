# Slice 6I Acceptance - Commercial Offer Submission Evidence Foundation

## Automated Checks

Required:

```powershell
git diff --check
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
docker compose exec backend alembic heads
docker compose exec backend pytest
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
```

## Backend Acceptance

Test user:

```text
sales1 / Sales User
```

Starting route:

```text
GET /api/commercial-offers/{public_id}
```

Positive path:

1. Use or create a Commercial Offer.
2. Call:

```text
GET /api/commercial-offers/{public_id}/submission-evidence
```

Expected:

- Response is `200`.
- Existing evidence records are returned.
- Read does not create a `business_event`.

3. Call:

```text
POST /api/commercial-offers/{public_id}/submission-evidence
```

Payload example:

```json
{
  "submission_reference": "EMAIL-001",
  "submission_channel": "EMAIL",
  "submitted_at": "2026-07-09T10:15:00",
  "recipient_summary": "Customer procurement contact",
  "document_reference_label": "Email metadata",
  "document_reference_url_or_path": "Outlook reference or external document path",
  "evidence_notes": "Submitted customer-format quote metadata only."
}
```

Expected:

- Response is `201`.
- Response includes `submission_evidence`.
- Response includes `CommercialOfferSubmissionEvidenceRecorded`.
- Amount/currency snapshot comes from the current Commercial Offer where available.
- A second POST can create another evidence record for the same Commercial Offer.

Negative and permission paths:

- Missing Commercial Offer returns `404`.
- Finance/read-only users can list evidence.
- Finance/read-only users cannot create evidence and receive `403`.
- Invalid channel returns `422`.
- Unauthenticated calls return `401`.

Readiness path:

1. Call:

```text
GET /api/commercial-offers/{public_id}/submission-readiness?recommendation_basis=HIRING
```

Expected:

- Response includes `SUBMISSION_EVIDENCE`.
- Missing evidence is `ATTENTION_REQUIRED`.
- Existing evidence is `PASS`.
- Quote/PDF generation and submission proof upload/storage remain deferred.
- Readiness read does not create a `business_event`.

## Frontend Acceptance

Test user:

```text
sales1 / Sales User
```

Starting URL:

```text
/commercial-offers/{commercialOfferId}
```

Positive path:

1. Open an existing Commercial Offer detail page.
2. Confirm the Submission Evidence section appears near Submission Readiness.
3. Confirm the section says it records metadata only and does not generate quote/PDF documents, upload/store files, run SharePoint automation, approve T&C wording or calculate credit exposure.
4. Add one evidence record with channel, submitted date/time, reference, recipient summary, document metadata and notes.
5. Confirm the action-specific success message appears near the action button.
6. Confirm the evidence appears in the list.
7. Confirm Submission Readiness refreshes and shows evidence recorded.

Permission path:

1. Login as `finance1` or `readonly1`.
2. Open the same Commercial Offer detail page.

Expected:

- Existing submission evidence is visible.
- Add-evidence controls are not offered as available actions.
- Backend still rejects direct create calls for read-only roles.

Regression checks:

- Existing Header T&C manual attach/remove still works.
- Existing Attach Recommended Clauses still works.
- Existing lifecycle/action area still loads and behaves as before.
- The page does not imply quote/PDF generation, SharePoint upload, credit approval or legal approval is complete.

## Deferred / Known Manual Gaps

Not part of Slice 6I:

```text
- quote/PDF/document generation;
- file upload/storage;
- SharePoint/document automation;
- credit exposure calculation;
- approval workflow;
- omitted mandatory T&C approval;
- T&C deviation/new-clause approval;
- line-level T&C selection;
- legal versioning;
- Work Order release/posting;
- billing logic;
- Customer Master activation.
```

## Handoff Contract Check

The frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract is unchanged.

## Current Run Notes

Automated checks run during implementation:

```text
git diff --check - pass
docker compose exec backend alembic upgrade head - pass after migration idempotency patch
docker compose exec backend alembic current - 20260709_0024 (head)
docker compose exec backend alembic heads - 20260709_0024 (head)
docker compose exec backend pytest - 127 passed
docker compose run --rm frontend npm run build - pass after PageAccess type fix
docker compose run --rm frontend npm test - pass; script reports frontend automated tests are not configured
```

Manual browser smoke was not completed in this run because the in-app browser surface was unavailable. A local HTTP reachability check for `http://localhost:3000/commercial-offers` returned `200`.
