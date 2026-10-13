# Slice 1E Acceptance - Account Detail/Profile Shell

## Automated checks

Run from repository root.

```powershell
docker compose exec backend pytest

docker compose stop frontend
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

Expected:

```text
backend pytest passes
frontend build passes
frontend npm test command passes, even if currently a configured stub
frontend dev server restarts cleanly
```

## Manual acceptance checks

### Sales/Admin user

```text
Login as sales1 or admin1
Open /accounts
Click Refresh Accounts
Click an Account name
Confirm /accounts/<public_id> opens
Confirm Account name, legal name, public ID, status, qualification source, segment, industry, owner and dates are visible
Confirm planned tab placeholders are shown but not implemented
Confirm Back to Accounts works
```

### Read-only operational users

```text
Login as finance1, ops1 or readonly1
Open /accounts
Click Refresh Accounts
Open an Account detail page
Confirm the Account detail page opens because these roles have Account read access
Confirm Create Account action is still unavailable for disallowed create roles
```

### Missing/invalid session

```text
Clear browser local storage key pbl_auth_token
Open a known /accounts/<public_id> URL
Confirm the page shows a friendly login/session message
Confirm no raw token or technical stack trace is displayed
```

### Not-found / invalid URL

```text
Open /accounts/00000000-0000-0000-0000-000000000000
Confirm a friendly Account not found message is displayed
Open /accounts/not-a-uuid
Confirm a friendly invalid-link or validation message is displayed
```

## Out-of-scope checks

Do not expect these in Slice 1E:

```text
Edit Account
Contacts tab
Addresses tab
PAN/GST tab
Classification tab
Documents/events tab
Duplicate detection
Customer activation
Lead/opportunity/offer/work-order integration
```

## Acceptance decision

Accepted only if:

```text
all automated checks pass
manual read/detail checks pass
no helper scripts or ZIP files are staged
documentation updates are included in the commit
```

## UX hardening acceptance addendum

```text
Open /accounts after login and confirm recent Accounts load without requiring the first Refresh click
Open an Account detail page and return to /accounts; confirm the list reloads automatically
Use the Logout action and confirm pbl_auth_token is removed and /login is shown
After logout, open /accounts and confirm a friendly no-session message appears
If a hydration warning shows fdprocessedid attributes, retest in an extension-free/incognito browser before treating it as an application defect
```

## Session-state UX hardening acceptance addendum

```text
Click Logout and confirm the left navigation shows Not signed in / Login without requiring browser developer tools.
Login successfully and confirm the left navigation changes to Signed in / Logout without requiring a browser refresh.
Repeat login/logout twice and confirm no application-owned hydration mismatch appears.
If hydration warnings still show extension-injected attributes, retest in an extension-free browser before treating it as an application defect.
```

## Follow-up acceptance: dashboard role-aware action visibility

```text
Login as admin1, sales1 or manager1.
Confirm dashboard shows View Accounts and Create Account.

Login as finance1, ops1 or readonly1.
Confirm dashboard shows View Accounts but does not show Create Account.

Logout.
Confirm dashboard does not show Create Account and asks the user to login to see role-available actions.
```
