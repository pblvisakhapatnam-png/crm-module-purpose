# Slice 1B - Account Create/List API

## Goal

Add backend Account API routes using the existing `business_party` table from Slice 1A.

This slice creates the first usable backend Account behavior without adding frontend Account UI.

## Scope

Included:

- Account create API;
- Account recent-list API;
- Account get-by-public-id API;
- backend Account schemas, repository, service, and routes;
- Account creation validation for Slice 1B-safe statuses;
- Account creation business event;
- backend tests;
- contract and continuity documentation updates.

Excluded:

- frontend Account create/list UI;
- lead conversion;
- opportunity creation;
- customer activation;
- credit limit checks;
- PAN/GSTN duplicate workflow beyond format validation;
- document linkage UI;
- file upload;
- database schema changes.

## API routes

```text
POST /api/accounts
GET  /api/accounts
GET  /api/accounts/{public_id}
```

## Key rules

1. User-facing API route uses `accounts`.
2. Database table remains `business_party`.
3. Create API may create only `DRAFT` or `QUALIFIED_PROSPECT` Accounts.
4. Customer activation statuses are not created directly in Slice 1B.
5. Account status must exist as an active `workflow_status` for module `business_party`.
6. Account creation must record a business event named `AccountCreated`.
7. Account creation event must not include passwords, tokens, secrets, or unnecessary statutory identifiers.
8. No frontend Account UI is part of this slice.

## Files changed

```text
backend/app/main.py
backend/app/modules/accounts/contract.py
backend/app/modules/accounts/schemas.py
backend/app/modules/accounts/repository.py
backend/app/modules/accounts/service.py
backend/app/modules/accounts/routes.py
backend/tests/test_accounts_api.py
docs/agent/contracts/account-business-party-contract.md
docs/agent/slices/slice-1b-account-create-list-api.md
docs/agent/acceptance/slice-1b-account-create-list-api-acceptance.md
docs/continuity/NEXT_STEPS.md
```

## No Alembic migration

Slice 1B uses the Slice 1A `business_party` table.

No Alembic migration is expected for this slice.

## Implementation notes

The router is included in `backend/app/main.py`.

Role behavior:

```text
Create: ADMIN, SALES_USER, SALES_MANAGER
Read/list: ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER, OPERATIONS_USER, MANAGEMENT_READ_ONLY
```

The service layer normalizes and validates:

```text
party_type
account_name
PAN
GSTIN
account_status_code
qualification_source
account_owner_user_public_id
created_by
```

## Acceptance criteria

1. `POST /api/accounts` requires authentication.
2. Sales user can create a draft Account.
3. Sales manager can create a qualified-prospect Account.
4. Finance user can list Accounts but cannot create an Account.
5. Create rejects direct `CUSTOMER_ACTIVE` status.
6. Create rejects invalid PAN format.
7. Created Account can be listed through `GET /api/accounts`.
8. Created Account can be fetched through `GET /api/accounts/{public_id}`.
9. Account creation creates an `AccountCreated` business event.
10. Existing Slice 0 and Slice 1A tests continue to pass.
11. No `.env` or helper `.ps1` file is committed.

## Commands

Apply existing migrations if needed:

```powershell
docker compose exec backend alembic upgrade head
```

Run tests:

```powershell
docker compose exec backend pytest
```

Manual API smoke checks can be done from Swagger/OpenAPI or PowerShell after login.

## Completion rule

Commit only after backend tests pass and manual non-regression checks are acceptable.