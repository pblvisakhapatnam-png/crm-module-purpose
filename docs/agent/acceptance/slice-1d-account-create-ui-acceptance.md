# Slice 1D Acceptance - Minimal Account Create UI

## Automated checks

Run from repository root.

### Backend regression

```powershell
docker compose exec backend pytest
```

Expected:

```text
All existing backend tests pass, including Slice 0, Slice 1A, Slice 1B and Slice 1C regression expectations.
```

### Frontend build and placeholder test

Use the safe frontend build sequence because the Next.js dev server and production build both use `.next`.

```powershell
docker compose stop frontend
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

Expected:

```text
Next.js build completes successfully.
Frontend npm test command completes. If still configured as the Slice 0 placeholder, it may only print that automated frontend tests are not configured.
Frontend dev server restarts cleanly after `.next` is cleared.
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

### 2. Create Account page exists

1. Go to `/accounts`.
2. Click `Create Account`.

Expected:

```text
The browser opens `/accounts/new`.
The page shows a minimal create form.
The page does not show edit UI, detail tabs, PAN/GST workflow, duplicate detection or customer activation controls.
```

### 3. Required Account name validation

1. On `/accounts/new`, leave Account name blank.
2. Submit the form.

Expected:

```text
The page shows that Account name is required.
No Account is created.
```

### 4. Successful Draft Account create

1. Login as `sales1 / password` or `admin1 / password`.
2. Go to `/accounts/new`.
3. Enter an Account name.
4. Leave status as `Draft`.
5. Select a qualification source such as `Enquiry` or `Manual`.
6. Submit.

Expected:

```text
The page shows Account created successfully.
The created Account summary includes public ID, status DRAFT, qualification source and business event AccountCreated.
The form resets after successful create.
```

### 5. Successful Qualified Prospect create

1. Go to `/accounts/new`.
2. Enter an Account name and legal name.
3. Select status `Qualified Prospect`.
4. Select qualification source `RFQ`, `Tender`, `Registration` or another allowed source.
5. Enter optional segment/industry/remarks if desired.
6. Submit.

Expected:

```text
The page shows Account created successfully.
The created Account summary includes status QUALIFIED_PROSPECT.
```

### 6. Account list refresh shows created records

1. After creating an Account, go to `/accounts`.
2. Click `Refresh Accounts`.

Expected:

```text
The new Account appears in the recent Account list.
The Account list does not show PAN or GSTIN.
```

### 7. Missing-token behavior

1. Clear browser local storage or open a fresh browser profile without logging in.
2. Go to `/accounts/new`.
3. Fill Account name and submit.

Expected:

```text
The page shows a clear login/session error.
No Account is created.
```

### 8. Role negative check

1. Login as a user that should not be able to create Accounts, such as `finance1`, `ops1` or `readonly1`.
2. Go to `/accounts/new`.
3. Fill Account name and submit.

Expected:

```text
The backend returns 403.
The page shows a user-friendly permission message.
No Account is created.
```

### 9. Scope check

Expected:

```text
No backend API or database migration is added for Slice 1D.
No Account edit UI is added.
No Account detail/profile shell is added.
No Contacts, Addresses, PAN/GST, Documents or Events tabs are implemented.
No duplicate detection UI is implemented.
No lead conversion, opportunity creation, customer activation or credit controls are implemented.
```

### 10. Documentation check

Expected files exist or are updated:

```text
docs/agent/slices/slice-1d-account-create-ui.md
docs/agent/acceptance/slice-1d-account-create-ui-acceptance.md
docs/continuity/NEXT_STEPS.md
docs/agent/contracts/account-business-party-contract.md
```

### 11. Git hygiene

Expected:

```text
No helper .ps1 files are staged.
No ZIP files are staged.
No .env files are staged.
No node_modules, .next, dist or coverage output is staged.
No unrelated files are staged.
```

## Slice 1D follow-up acceptance - permission UX hardening

### Account create form should not render for disallowed roles

1. Login as `finance1`, `ops1` or `readonly1`.
2. Go to `/accounts`.
3. Confirm the primary `Create Account` action is not shown as an available action.
4. Directly open `/accounts/new`.

Expected:

```text
The page shows that Account creation is not available for the current role.
The Account create form is not rendered.
No POST /api/accounts call is needed to learn that the user cannot create Accounts.
```

### Backend remains authoritative

Even though the frontend hides the create form for disallowed users, the backend must still return `403` for a direct `POST /api/accounts` request from a disallowed role.
