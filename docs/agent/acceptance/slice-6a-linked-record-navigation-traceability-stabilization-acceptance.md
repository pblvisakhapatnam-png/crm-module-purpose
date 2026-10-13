# Slice 6A Acceptance - Linked Record Navigation and Traceability Stabilization

## Automated checks

Backend:

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend pytest
```

Frontend, because frontend code changed:

```powershell
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
```

The usual `.next` cleanup sequence from `AGENTS.md` is preferred when allowed. If a task explicitly says not to touch `.next`, record that deviation in the final report.

## Manual happy path

```text
1. Login as sales1 / password.
2. Open an Accepted Commercial Offer with at least one active line.
3. Create a Work Order shell if one does not already exist.
4. Return to the Commercial Offer profile.
5. Confirm Linked Work Order shell(s) shows the generated WO code, status, customer WO reference, received date and source offer status.
6. Click Open Work Order shell.
7. Confirm the Work Order profile opens and has a Back to Commercial Offer action.
8. Use the Back to Commercial Offer action and confirm it returns to the originating Commercial Offer.
```

## Permission check

```text
1. Login as finance1 / password.
2. Open the same Commercial Offer profile.
3. Confirm linked Work Order shell(s) are visible.
4. Confirm Finance still cannot create a Work Order shell.
```

## API validation check

```text
1. Call GET /api/work-orders?commercial_offer_public_id={valid-commercial-offer-public-id}.
2. Confirm all returned rows, if any, belong to that Commercial Offer.
3. Call GET /api/work-orders?commercial_offer_public_id=not-a-uuid.
4. Confirm request validation rejects the invalid query value.
```

## Deferred items

```text
- WO release/posting.
- Customer Master activation.
- Equipment assignment.
- Crew assignment.
- Log sheets.
- Billing.
- Approval workflow.
```
