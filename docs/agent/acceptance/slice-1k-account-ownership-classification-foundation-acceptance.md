# Slice 1K Acceptance - Account Ownership / Classification Foundation

Use foundation-slice testing only. Do not perform exhaustive UX or business-rule testing in this slice.

## Automated checks

- Alembic head is `20260704_0010`.
- `docker compose exec backend pytest` passes.
- Frontend production build passes.
- Frontend tests pass if present.

## Manual checks

- Login as `sales1` or `admin1`.
- Open an Account detail page.
- Confirm Ownership / Classification section appears.
- Save segment, industry, strategic account flag and notes.
- Confirm updated values are visible.
- Confirm Contacts, Addresses, PAN/GST and Documents still load.
- Login as `finance1`, `ops1` or `readonly1`.
- Confirm Ownership / Classification is visible but the update form is unavailable.

## Deferred checks

- Owner user picker.
- Sales hierarchy validation.
- Territory assignment.
- Account reassignment approval.
- Duplicate Account merge.
- Account scoring/classification automation.
