# Slice 6G Acceptance - Commercial Offer T&C Readiness And Recommended Clauses

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
2. Open an existing Commercial Offer public ID or create a test Commercial Offer.
3. Call:

```text
GET /api/commercial-offers/{public_id}/tc-clause-readiness?recommendation_basis=HIRING
```

Expected:

- Response is `200`.
- Response includes `recommendation_basis = HIRING`.
- Only active header-applicable HIRING clauses are listed.
- Each recommended clause has status `ATTACHED` or `NOT_ATTACHED`.
- Line-only clauses are excluded.

4. Call with invalid basis:

```text
GET /api/commercial-offers/{public_id}/tc-clause-readiness?recommendation_basis=LEGAL
```

Expected:

- Response is `422`.

5. Login as `finance1` and read readiness.

Expected:

- Finance can read readiness.

6. Login as `finance1` and call:

```text
POST /api/commercial-offers/{public_id}/tc-clauses/attach-recommended
```

Expected:

- Response is `403`.

7. Login as `sales1` and call `attach-recommended` with `HIRING`.

Expected:

- Missing recommended clauses are attached.
- Attachment snapshots are preserved from the source library at attachment time.
- `CommercialOfferTcClauseAttached` events are emitted for newly attached clauses.
- A second call returns successfully without duplicates and without new events.

## Frontend Acceptance

1. Login as `sales1`.
2. Open a Commercial Offer detail page:

```text
/commercial-offers/{commercialOfferId}
```

Expected:

- Header T&C clauses section still appears.
- Recommended header T&C readiness panel appears near the top of the section.
- Recommendation basis selector is visible.
- Source-derived/prototype and deferred-scope guidance remains visible.

3. Select `Equipment Hiring` or `Transportation`.

Expected:

- Recommended clauses load for the selected basis.
- Counts show total, attached recommended, missing recommended and attached optional.
- Clause statuses show `ATTACHED` or `NOT ATTACHED`.

4. Click `Attach recommended clauses`.

Expected:

- Missing recommended clauses are attached.
- Existing 6F attached-clause list refreshes.
- Repeating the action does not create duplicates.

5. Use the existing manual attach/remove controls.

Expected:

- Manual 6F attach/remove behavior still works.
- Readiness refreshes after manual attach/remove.

## Deferred / Known Manual Gaps

- This slice does not make T&C readiness a submission block.
- This slice does not approve legal wording.
- This slice does not implement line-level T&C, clause editing, deviation approval, quote/PDF generation, legal versioning or SharePoint/document automation.
- This slice does not change Work Order handoff, release, posting, execution or billing.
