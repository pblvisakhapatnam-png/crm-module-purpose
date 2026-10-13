# Acceptance - Slice 4F Commercial Offer Lifecycle Closure Foundation

## Automated checks

- Backend pytest passes.
- Frontend build passes.
- Frontend tests pass.
- Alembic upgrade reaches head cleanly.

## Manual happy path

1. Login as `sales1 / password`.
2. Open `/commercial-offers`.
3. Open a Commercial Offer profile.
4. Click **Edit Commercial Offer / Status**.
5. Move status to **Submitted**.
6. Capture submitted date/time, submission reference and proof note.
7. Save and confirm `CommercialOfferSubmitted` and `CommercialOfferStatusChanged` are shown.
8. Edit again and move status to **Accepted** or **Rejected**.
9. Capture outcome date and outcome remarks.
10. Save and confirm the lifecycle event is shown.

## Permission check

1. Login as `finance1 / password`.
2. Open the same Commercial Offer profile.
3. Confirm lifecycle information is visible.
4. Confirm edit/status action is not available.

## Negative path check

1. Login as `sales1 / password`.
2. Try selecting **Revised** if visible anywhere.
3. Confirm it is not selectable in the Slice 4F edit form.
4. Try invalid date/value cases already covered by Slice 4C/4E checks.

## Deferred controls to verify in documentation

The page and docs must make clear that approval workflow, formal revision control, submitted document locking, Commercial Offer exposure/availability gate automation and Work Order handoff remain deferred.
