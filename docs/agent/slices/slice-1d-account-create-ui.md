# Slice 1D - Minimal Account Create UI

## Goal

Add a minimal frontend Account create flow that consumes the existing Slice 1B backend Account API.

This slice proves that operational users can create a Draft Account or Qualified Prospect from the frontend without adding edit screens, Account detail tabs or downstream CRM objects.

## Scope

Included:

- add `/accounts/new` frontend route;
- call `POST /api/accounts` using a relative API path;
- read the browser token from `pbl_auth_token`;
- support only Slice 1B-safe Account create fields;
- show client-side required-field validation for Account name;
- show user-friendly API, permission and network errors;
- show a created Account summary after successful creation;
- add a Create Account link from the Account list page;
- update dashboard status text;
- improve the Account list page's user-facing error and empty-state messages;
- update slice documentation, acceptance checklist, Account contract and continuity next steps.

Excluded:

- Account edit form;
- Account detail/profile shell;
- Contacts tab;
- Addresses tab;
- PAN/GST tab;
- Classification tab;
- Documents/events tabs;
- duplicate detection UI;
- lead conversion;
- opportunity creation;
- customer activation;
- credit checks;
- document upload or linkage;
- backend API changes;
- database migration;
- large UI redesign.

## Route

```text
/accounts/new
```

## API call

```text
POST /api/accounts
Authorization: Bearer <pbl_auth_token>
Content-Type: application/json
```

The frontend must use a relative API path and must not hard-code `localhost` for this Account API call.

## Form fields

Slice 1D supports these fields:

```text
account_name             required
legal_name               optional
account_status_code      DRAFT or QUALIFIED_PROSPECT only
qualification_source     manual, enquiry, rfq, tender, registration, external_intelligence
segment                  optional
industry                 optional
source_remarks           optional
```

The page sends `party_type = organization` because Slice 1B supports organization Accounts only.

PAN and GSTIN are deliberately excluded from the Slice 1D create UI. PAN/GST handling belongs to a later Account tab and must include stronger role and workflow treatment.

## Success behavior

On successful creation, the page shows:

```text
Account name
Legal name when present
Public ID
Status
Qualification source
Segment / industry
Owner public ID
Created date/time
Business event name and record type
```

The form is reset after successful creation.

## Error behavior

The page must handle:

```text
No token found
Required Account name missing
401/expired login
403/role not allowed
404 route not found
422 backend validation error
Network error
Other HTTP/API error
```

Do not show raw JSON response bodies in the normal UI.

## Files changed

```text
frontend/app/accounts/page.tsx
frontend/app/accounts/new/page.tsx
frontend/app/page.tsx
docs/agent/slices/slice-1d-account-create-ui.md
docs/agent/acceptance/slice-1d-account-create-ui-acceptance.md
docs/continuity/NEXT_STEPS.md
docs/agent/contracts/account-business-party-contract.md
```

## No backend change

Slice 1D consumes the Slice 1B API. It should not modify backend Account routes, schemas, services, repositories or migrations.

## Test and acceptance commands

Backend regression:

```powershell
docker compose exec backend pytest
```

Safer frontend build/test sequence during development:

```powershell
docker compose stop frontend
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

Manual UI checks are required because no real frontend automated test framework has been configured yet.

## Completion rule

Slice 1D is complete only after:

1. backend regression tests pass;
2. frontend build/test commands pass using the safe `.next` handling sequence;
3. manual UI checks pass for missing token, allowed user create, disallowed user create, and Account list refresh;
4. slice documentation and `NEXT_STEPS.md` are updated;
5. no helper `.ps1`, ZIP, `.env`, build output, `.next`, `node_modules` or unrelated file is committed.

## Slice 1D follow-up hardening

Manual testing found that a disallowed user could open `/accounts/new` and see the create form before receiving a backend `403` on submit.

The backend control was correct, but the frontend flow was misleading. A follow-up hardening patch now decodes the browser token payload for `role_codes` and renders the create form only for:

```text
ADMIN
SALES_USER
SALES_MANAGER
```

This frontend check is only a user-experience guard. Backend role checks remain authoritative and mandatory.

The issue is documented in:

```text
docs/continuity/SLICE_1D_ISSUE_LOG.md
```
