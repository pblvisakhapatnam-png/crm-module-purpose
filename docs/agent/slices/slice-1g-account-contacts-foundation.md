# Slice 1G - Account Contacts Foundation

## Objective

Add the first Account sub-record foundation: Contacts linked to Account / `business_party`.

## Scope

This slice adds:

- `business_party_contact` table through Alembic.
- Backend create/list Contact API under Account.
- Backend tests for create/list, permissions, missing Account and validation.
- Minimal frontend Contacts section on Account detail page.
- Role-aware Contact create form visibility.
- `AccountContactCreated` business event.
- Contract, acceptance and continuity documentation.

## API routes

```text
GET  /api/accounts/{public_id}/contacts
POST /api/accounts/{public_id}/contacts
```

## Files changed

Backend:

- `backend/alembic/versions/20260702_0007_account_contacts_foundation.py`
- `backend/app/modules/accounts/contract.py`
- `backend/app/modules/accounts/schemas.py`
- `backend/app/modules/accounts/repository.py`
- `backend/app/modules/accounts/service.py`
- `backend/app/modules/accounts/routes.py`
- `backend/tests/test_accounts_api.py`

Frontend:

- `frontend/app/accounts/[accountId]/page.tsx`

Docs:

- `docs/agent/contracts/account-business-party-contract.md`
- `docs/agent/slices/slice-1g-account-contacts-foundation.md`
- `docs/agent/acceptance/slice-1g-account-contacts-foundation-acceptance.md`
- `docs/continuity/SLICE_1G_CONTACTS_FOUNDATION.md`
- `docs/continuity/NEXT_STEPS.md`

## Exclusions

Do not implement in this slice:

- Contact edit/delete.
- Contact duplicate detection.
- Contact approval workflow.
- Contact import.
- Email/phone validation beyond basic required/format checks.
- Contact activity history.
- Opportunity/Lead linkage.
- Addresses, PAN/GST, Documents or Events tabs.

## Completion rule

Slice 1G is complete only when:

- Alembic has one head after migration.
- Backend pytest passes.
- Frontend build/test commands pass.
- Manual create/list Contact checks pass.
- Role and negative-path checks pass.
- Documentation is committed with the code.