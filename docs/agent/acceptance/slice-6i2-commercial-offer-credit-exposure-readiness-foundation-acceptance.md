# Slice 6I.2 - Commercial Offer Credit / Exposure Readiness Foundation Acceptance

## Test Users

```text
sales1 / password      create/view
finance1 / password    view only
readonly1 / password   view only
```

## Starting Route And Data

Use an existing Commercial Offer at `/commercial-offers/{public_id}` with a known lifecycle status. Record that status before testing.

## Happy Path

1. Login as `sales1` and open the Commercial Offer.
2. Open the Submission tab.
3. Confirm Submission Readiness, Credit / Exposure Review and Submission Evidence are visible.
4. Record `WITHIN_LIMIT_AS_PER_MANUAL_REVIEW` with reviewed date/time and a clearly marked test note.
5. Confirm the review appears as Current and the local success message appears beside the form.
6. Confirm Submission Readiness shows `CREDIT_EXPOSURE_REVIEW` as passed.
7. Add a second `APPROVED_WITH_REFERENCE` review with a reference.
8. Confirm the new record is Current and the prior record is Superseded.
9. Reload the page and confirm both records persist.
10. Confirm the Commercial Offer lifecycle status is unchanged.

## Advisory Status Paths

- No review: readiness is `ATTENTION_REQUIRED` and says manual review is not recorded.
- `APPROVAL_REQUIRED`: readiness is `ATTENTION_REQUIRED` and does not imply approval completion.
- `REJECTED_OR_ON_HOLD`: readiness uses blocking-style advisory language but lifecycle actions are not newly blocked by this slice.
- `APPROVED_WITH_REFERENCE` without reference: create is rejected with clear validation feedback.

## Permission Path

1. Login as `finance1` or `readonly1`.
2. Confirm review history is visible.
3. Confirm the add form is not offered by the UI.
4. Direct POST as a non-manage role must return `403`; backend enforcement is authoritative.

## Regression Checks

- All Slice 6I.1 tabs remain usable.
- Submission Evidence still lists/adds according to role.
- T&C readiness and attachment actions remain unchanged.
- Linked records and lifecycle actions remain unchanged.
- No UI text implies calculated exposure, Finance workflow completion, quote/PDF generation or Work Order release/posting.

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

Automated foundation gate: Pass.

```text
git diff --check - pass
docker compose exec backend alembic upgrade head - pass
docker compose exec backend alembic current - 20260710_0025 (head)
docker compose exec backend alembic heads - 20260710_0025 (head)
docker compose exec backend pytest - 130 passed
docker compose run --rm frontend npm run build - pass
docker compose run --rm frontend npm test - pass; script reports frontend automated tests are not configured
```

Manual browser smoke was performed by the user and passed all 11 smoke-test points for the Slice 6I.2 Credit / Exposure Review section, Submission Readiness integration, tabs, Submission Evidence, T&C tab, lifecycle non-change and deferred-scope wording.

The final validation documentation update changed no backend, API, migration or business behavior.
