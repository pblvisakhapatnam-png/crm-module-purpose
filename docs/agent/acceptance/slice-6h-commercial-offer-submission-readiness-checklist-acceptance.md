# Slice 6H Acceptance - Commercial Offer Submission Readiness Checklist

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

1. Login as `sales1`.
2. Open or create a Commercial Offer.
3. Call:

```text
GET /api/commercial-offers/{public_id}/submission-readiness?recommendation_basis=HIRING
```

Expected:

- Response is `200`.
- Response includes `commercial_offer_public_id`.
- Response includes `readiness_status`.
- Response includes summary counts for passed, warning, blocking and deferred.
- Response includes checklist rows for Account traceability, Opportunity traceability, Commercial Offer lines, pricing evidence and header T&C readiness.
- Response includes deferred rows for credit/exposure gate, approval workflow, quote/PDF/document generation and submission proof.

4. Call without recommendation basis.

Expected:

- Response is `200`.
- Header T&C readiness row asks the user to select a recommendation basis.
- Missing basis is attention/not assessed, not a system failure.

5. Call with an invalid recommendation basis.

Expected:

- Response is `422`.

6. Call with a missing Commercial Offer public ID.

Expected:

- Response is `404`.

7. Call without authentication.

Expected:

- Response is `401`.

8. Confirm read-only behavior.

Expected:

- Readiness read does not create a `business_event`.
- Readiness read does not attach T&C clauses.

## Frontend Acceptance

1. Login as `sales1`.
2. Open:

```text
/commercial-offers/{commercialOfferId}
```

Expected:

- Submission Readiness panel appears near the Commercial Offer lifecycle/action area.
- Overall status is visible.
- Checklist rows render clearly.
- The panel says readiness is guidance and not legal approval, credit approval, quote/PDF generation or submission proof.

3. Select a T&C recommendation basis.

Expected:

- Submission readiness refreshes.
- Header T&C readiness row reflects attached/missing recommended clauses.
- Existing 6G recommended T&C readiness section still works.

4. Use existing 6F manual attach/remove and 6G attach-recommended controls.

Expected:

- Existing controls still work.
- Submission readiness can be refreshed and remains coherent.

5. Use existing lifecycle/action area.

Expected:

- Existing Commercial Offer edit/status actions are not broken.
- This slice does not add a new hard submission block.

## Deferred / Known Manual Gaps

- No quote/PDF generation.
- No actual quote submission workflow.
- No submission proof upload/capture.
- No credit/exposure calculation.
- No approval workflow.
- No legal T&C approval.
- No line-level T&C selection.
- No Work Order release/posting or billing.
- No Customer Master activation.
- No change to the frozen Slice 6D.1 handoff contract.
