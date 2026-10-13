# Slice 1H - Account Addresses Foundation

## Scope

Slice 1H adds CRM Account address support linked to the existing `business_party` Account foundation.

## Included

- `business_party_address` table linked to `business_party`.
- `GET /api/accounts/{public_id}/addresses`.
- `POST /api/accounts/{public_id}/addresses`.
- Role-aware create access: Admin, Sales User and Sales Manager may create.
- Finance, Operations and Read Only users may view but not create.
- `AccountAddressCreated` business event.
- Minimal Addresses section on the Account detail page.
- Backend tests including authentication, permission, missing Account and invalid type paths.

## Excluded

- Address edit/delete.
- Duplicate address detection.
- Finance approval workflow.
- GSTN-wise billing address approval.
- Customer Master activation.
- Work Order site address control.
- Address import/export.

## Important boundary

Slice 1H addresses are CRM Account addresses only. `BILLING_DRAFT` is draft CRM information and must not be treated as Finance-approved billing master data.

## Address types

- `REGISTERED_OFFICE`
- `COMMUNICATION`
- `SITE`
- `BILLING_DRAFT`
- `OTHER`

## Files changed

- `backend/alembic/versions/20260702_0008_account_addresses_foundation.py`
- `backend/app/modules/accounts/contract.py`
- `backend/app/modules/accounts/schemas.py`
- `backend/app/modules/accounts/repository.py`
- `backend/app/modules/accounts/service.py`
- `backend/app/modules/accounts/routes.py`
- `backend/tests/test_accounts_api.py`
- `frontend/app/accounts/[accountId]/page.tsx`
- `docs/agent/contracts/account-business-party-contract.md`
- `docs/agent/slices/slice-1h-account-addresses-foundation.md`
- `docs/agent/acceptance/slice-1h-account-addresses-foundation-acceptance.md`
- `docs/continuity/SLICE_1H_ADDRESSES_FOUNDATION.md`
- `docs/continuity/NEXT_STEPS.md`

## Completion rule

Slice 1H is complete only after Alembic is at `20260702_0008`, backend tests pass, frontend build passes and manual Account detail address checks pass for both creator and read-only roles.
