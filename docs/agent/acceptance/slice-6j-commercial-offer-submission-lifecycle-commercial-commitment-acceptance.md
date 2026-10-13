# Slice 6J - Commercial Offer Submission Lifecycle / Commercial Commitment Acceptance

## Test Users

```text
sales1 / password      authorized lifecycle action
finance1 / password    read-only / forbidden action
```

## Starting Route And Test Data

Open an existing Draft or Ready for Review Commercial Offer at `/commercial-offers/{public_id}`. Use test data with Account and Opportunity traceability.

## Happy Path

1. Login as `sales1` and open the Submission tab.
2. Confirm the controlled action card shows current status, evidence availability and latest manual credit-review status.
3. Ensure at least one active line exists.
4. Add submission evidence metadata.
5. Optionally add a favourable manual credit/exposure review.
6. Click `Record as Submitted / Commercially Committed`.
7. Confirm local success feedback and any advisory credit-review warning.
8. Confirm status becomes `SUBMITTED` and Submission Readiness shows commercial commitment passed.
9. Confirm submission evidence count is unchanged by the action.
10. Confirm no Work Order is created and no quote/PDF is generated.
11. Confirm event/audit traceability includes `CommercialOfferCommerciallyCommitted` where role access permits.

## Negative And Permission Paths

- Missing Commercial Offer returns `404`.
- `finance1` action returns `403`.
- Missing Account traceability returns `422`.
- Missing active line returns `422`.
- Missing submission evidence returns `422`.
- `WITHDRAWN`, `REJECTED`, `CLOSED`, `ACCEPTED` and already `SUBMITTED` cannot use the action.
- Current `REJECTED_OR_ON_HOLD` manual credit review returns `422` and creates no commitment event.
- Direct PUT transition into `SUBMITTED` returns `422` and directs callers to the controlled action.

## Warning Paths

Missing, `NOT_ASSESSED` or `APPROVAL_REQUIRED` manual credit review does not become a new hard block. The action returns an explicit warning that exposure calculation and Finance workflow remain deferred.

## Regression Checks

- All tabs still work.
- Submission Evidence and Credit / Exposure Review still work.
- T&C readiness/attachment behavior is unchanged.
- Accepted-offer Work Order handoff behavior is unchanged.
- The UI does not imply quote sending/generation, exposure calculation, Finance approval, legal approval or Work Order release/posting.

## Automated Gate

```text
git diff --check
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
docker compose exec backend alembic heads
docker compose exec backend pytest
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
```

## Acceptance Result

Pending final full regression gate and manual browser smoke.

