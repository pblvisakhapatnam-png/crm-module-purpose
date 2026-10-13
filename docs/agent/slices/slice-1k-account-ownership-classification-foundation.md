# Slice 1K - Account Ownership / Classification Foundation

## Objective

Add the minimum Sales-owned relationship and classification fields for Account / `business_party`.

This slice creates the guardrail for later Lead, Opportunity and Quote ownership logic without implementing territory management or reassignment workflows.

## Included

- Account owner / assigned sales user public ID.
- Segment.
- Industry.
- Strategic account flag.
- Classification notes.
- `GET /api/accounts/{public_id}/classification`.
- `PUT /api/accounts/{public_id}/classification`.
- Account detail page Ownership / Classification section.
- Role-aware update action.
- Business event `AccountClassificationUpdated`.
- Backend tests and foundation-slice acceptance notes.

## Excluded

- Full user assignment workflow.
- Sales hierarchy approval.
- Territory management.
- Account reassignment approval.
- Account scoring.
- Duplicate Account merge.
- Customer Master ownership.

## Roles

Read: Admin, Sales, Finance, Operations and Management Read-only.

Update: Admin, Sales User and Sales Manager only.

## Notes

`account_owner_user_public_id` is stored as a user public ID string. Slice 1K does not provide a user picker or validate sales hierarchy. Those are later UX/business-rule tasks.
