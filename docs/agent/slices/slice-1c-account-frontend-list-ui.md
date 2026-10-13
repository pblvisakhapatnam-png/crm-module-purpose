# Slice 1C - Account Frontend List UI

## Goal

Add a minimal frontend Accounts list page that consumes the stable Slice 1B backend Account API.

This slice proves frontend-to-backend Account API integration without adding create/edit UI or wider Account tabs.

## Scope

Included:

- replace the Accounts placeholder/auth smoke page with a minimal Account list UI;
- call `GET /api/accounts?limit=20` using a relative API path;
- read the browser token from `pbl_auth_token`;
- show loading, empty, success and error states;
- display key Account fields returned by the Slice 1B API;
- update dashboard status text;
- update Slice 1C documentation, acceptance checklist and continuity next steps.

Excluded:

- Account create form;
- Account edit form;
- Account detail/profile shell;
- Contacts, addresses, PAN/GST, classification, documents or events tabs;
- lead conversion;
- opportunity creation;
- customer activation;
- credit checks;
- PAN/GST duplicate workflow;
- file upload or document linkage;
- large UI redesign;
- backend API changes;
- database migration.

## Frontend behavior

Route:

```text
/accounts
```

The page must show a simple explanation of the Slice 1C scope and a button to load recent Accounts.

API call:

```text
GET /api/accounts?limit=20
Authorization: Bearer <pbl_auth_token>
```

The frontend must use the relative API path and must not hard-code `localhost` for this Account API call.

## Displayed fields

The list should display at least:

```text
account_name
legal_name
public_id
account_status_code
qualification_source
segment
industry
account_owner_user_public_id
created_at
```

PAN and GSTIN are deliberately not displayed in the Slice 1C list because they are not necessary for the minimal list view and should not be exposed casually before the PAN/GST tab and role rules are designed.

## State handling

The page must handle:

```text
No token found
Loading
Successful load with one or more Accounts
Successful load with no Accounts
HTTP/API error
Network error
Clear list
```

## Files changed

```text
frontend/app/accounts/page.tsx
frontend/app/page.tsx
docs/agent/slices/slice-1c-account-frontend-list-ui.md
docs/agent/acceptance/slice-1c-account-frontend-list-ui-acceptance.md
docs/continuity/NEXT_STEPS.md
docs/agent/contracts/account-business-party-contract.md
```

## No backend change

Slice 1C consumes the Slice 1B API. It should not modify backend Account routes, schemas, services, repositories or migrations.

## Test and acceptance commands

Backend regression:

```powershell
docker compose exec backend pytest
```

Frontend build check:

```powershell
docker compose exec frontend npm run build
```

Frontend test command, if still configured as the Slice 0 placeholder:

```powershell
docker compose exec frontend npm test
```

Manual UI checks are required because no real frontend automated test framework has been configured yet.

## Completion rule

Slice 1C is complete only after:

1. backend regression tests pass;
2. frontend build passes;
3. manual UI checks pass for token missing, successful list load and error handling;
4. slice documentation and `NEXT_STEPS.md` are updated;
5. no helper `.ps1`, ZIP, `.env`, build output, `.next`, `node_modules` or unrelated file is committed.