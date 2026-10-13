# Slice 6K - Commercial Offer Revision / Resubmission Foundation Acceptance

## Test Users

```text
sales1 / password      create/view/transition
manager1 / password    create/view/transition
finance1 / password    view only; write actions forbidden
readonly1 / password   view only
```

## Starting URL And Data

Open `/commercial-offers/{public_id}` for a Commercial Offer with Account/Opportunity traceability, at least one active line, submission evidence and lifecycle status `SUBMITTED`.

## Happy Path

1. Login as `sales1` and open the Submission tab.
2. Confirm `Revisions / Resubmissions` appears near Submission Evidence.
3. Confirm the Original submission summary shows the latest evidence reference, channel, submitted time and available document reference.
4. Start the first cycle without entering a label; confirm the backend assigns `Rev 1`. Repeat later with a descriptive override to confirm custom labels remain supported.
5. Confirm it appears as `OPEN` and the readiness row warns that resubmission evidence is not recorded.
6. Confirm starting a second cycle while `Rev 1` is OPEN is rejected with guidance to resubmit or cancel the current cycle.
7. Record a second Submission Evidence entry representing the resubmission; revision actions do not create this evidence automatically.
8. Select that evidence and mark `Rev 1` resubmitted.
9. Confirm status `RESUBMITTED`, evidence reference and resubmitted time persist after reload, with no active buttons on the historical card.
10. Confirm readiness says the latest revision has resubmission evidence.
11. Start another cycle without a label; confirm `Rev 2`, then cancel it.
12. Start another cycle after cancellation; confirm `Rev 3` and that only its OPEN card has active actions.
13. Confirm event/audit traceability includes opened, resubmitted and cancelled events where the role can view events.

## Negative And Permission Paths

- Opening a revision for `DRAFT`, `READY_FOR_REVIEW`, `WITHDRAWN`, `REJECTED`, `CLOSED` or `ACCEPTED` is rejected; this foundation accepts only `SUBMITTED`.
- Missing Commercial Offer or missing revision returns `404`.
- Evidence from another offer or an unknown evidence ID is rejected.
- Mark Resubmitted without existing submission evidence is rejected.
- Missing or blank revision labels safely generate the next `Rev N` label.
- A second OPEN revision is rejected until the current OPEN revision is resubmitted or cancelled.
- `RESUBMITTED` or `CANCELLED` records cannot transition again.
- `finance1` and `readonly1` can view history but backend writes return `403`.
- Reads do not create business events.

## Regression Checks

- Commercial Offer public ID, offer code, line records and status remain unchanged by revision actions.
- No Commercial Offer clone is created.
- No Work Order is created.
- Tabs, Submission Readiness, Submission Evidence, Credit / Exposure Review, T&C and Slice 6J controlled submission remain usable.
- Accepted-offer Work Order shell behavior remains unchanged.
- No quote/PDF/document is generated or stored.
- Long evidence references, select values and card text remain inside form/card boundaries on desktop and narrow/mobile layouts.

## Automated Gate

```powershell
git diff --check
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
docker compose exec backend alembic heads
docker compose exec backend pytest
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
```

## Acceptance Result

Automated foundation gate: Pass.

```text
git diff --check - pass
docker compose exec backend alembic upgrade head - pass
docker compose exec backend alembic current - 20260711_0026 (head)
docker compose exec backend alembic heads - 20260711_0026 (head)
docker compose exec backend pytest - 136 passed
docker compose run --rm frontend npm run build - pass
docker compose run --rm frontend npm test - pass; script reports frontend automated tests are not configured
backend route confirmation - all four Slice 6K revision routes registered
```

Focused Commercial Offer gate also passed with `39 passed`.

Manual browser smoke: Blocked in this run because the in-app browser reported no available browser instances. The happy path, permission path, tab regression and visual/action-feedback checks above remain pending human browser UAT and are not inferred from automated tests or the successful production build.

## Deferred / Known Manual Gaps

Full quote cloning/versioning, version comparison, submitted-version lock/tamper evidence, quote/PDF generation, file upload/storage, legal approval/versioning, calculated credit exposure, Work Order release/posting, billing and Customer Master activation remain deferred.

## Handoff Contract Check

The frozen Slice 6D.1 Accepted Commercial Offer -> Work Order handoff contract is unchanged.
