# Slice 1C Acceptance - Account Frontend List UI

## Automated checks

Run from repository root.

### Backend regression

```powershell
docker compose exec backend pytest
```

Expected:

```text
All existing backend tests pass, including Slice 0, Slice 1A and Slice 1B tests.
```

### Frontend build

```powershell
docker compose exec frontend npm run build
```

Expected:

```text
Next.js build completes successfully.
```

### Frontend test command

```powershell
docker compose exec frontend npm test
```

Expected:

```text
The command completes. If the Slice 0 placeholder is still present, it may only print that automated frontend tests are not configured.
```

## Manual acceptance checklist

### 1. Login still works

1. Open the frontend.
2. Go to `/login`.
3. Login as `sales1 / password` or `admin1 / password`.

Expected:

```text
Login succeeds and token is stored in browser local storage as pbl_auth_token.
```

### 2. Accounts page shows Slice 1C list UI

1. Go to `/accounts`.

Expected:

```text
The page explains that Slice 1C is a minimal Account list UI.
The page has a Load recent Accounts button.
The page does not show an Account create/edit form.
```

### 3. Missing-token behavior

1. Clear browser local storage or open a fresh browser profile without logging in.
2. Go to `/accounts`.
3. Click `Load recent Accounts`.

Expected:

```text
The page shows a clear login/token error.
No Accounts are displayed.
```

### 4. Successful list behavior

1. Login as an allowed Account read role such as `sales1`, `finance1`, `ops1` or `readonly1`.
2. Go to `/accounts`.
3. Click `Load recent Accounts`.

Expected:

```text
The page calls GET /api/accounts?limit=20.
The page shows a success count.
If records exist, they appear in a table.
If no records exist, the empty state is clear.
```

### 5. Create a test Account if list is empty

If no Account records exist, create one using the Slice 1B backend API through Swagger/OpenAPI or another approved manual API method, then reload `/accounts`.

Expected visible values include:

```text
Account name
Legal name when present
Public ID
Status code
Qualification source
Segment / industry when present
Owner public ID when present
Created date/time
```

### 6. Scope check

Expected:

```text
No Account create UI is added.
No Account edit UI is added.
No Account detail tabs are implemented.
No backend API or database migration is added for Slice 1C.
```

### 7. Documentation check

Expected files exist or are updated:

```text
docs/agent/slices/slice-1c-account-frontend-list-ui.md
docs/agent/acceptance/slice-1c-account-frontend-list-ui-acceptance.md
docs/continuity/NEXT_STEPS.md
docs/agent/contracts/account-business-party-contract.md
```

### 8. Git hygiene

Expected:

```text
No helper .ps1 files are staged.
No ZIP files are staged.
No .env files are staged.
No node_modules, .next, dist or coverage output is staged.
No unrelated files are staged.
```