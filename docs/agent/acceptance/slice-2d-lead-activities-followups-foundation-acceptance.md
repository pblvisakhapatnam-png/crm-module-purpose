# Slice 2D Acceptance - Lead Activities / Follow-ups Foundation

## Automated checks

- [ ] Backend container rebuilt/recreated after route/migration changes.
- [ ] `alembic heads` shows `20260704_0013 (head)`.
- [ ] `alembic upgrade head` succeeds.
- [ ] `alembic current` shows `20260704_0013 (head)`.
- [ ] Backend tests pass.
- [ ] Frontend build passes.
- [ ] Frontend tests pass.

## Manual foundation checks

- [ ] Login as `sales1` or `admin1`.
- [ ] Open a Lead detail page.
- [ ] Record one Lead Activity / Follow-up.
- [ ] Confirm the activity appears in the Activities / Follow-ups list.
- [ ] Record a second activity and confirm the first activity remains visible.
- [ ] Login as `finance1`, `ops1` or `readonly1`.
- [ ] Confirm activities are visible.
- [ ] Confirm the activity create form is not available.

## Deferred checks

- Activity edit/delete.
- Reminder/task generation from next follow-up date.
- Calendar/notification integration.
- WhatsApp/email ingestion.
- Full activity timeline filtering/searching.
