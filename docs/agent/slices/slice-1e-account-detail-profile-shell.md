# Slice 1E - Account Detail/Profile Shell

## Purpose

Slice 1E adds the first read-only Account detail/profile shell.

The page uses the existing Slice 1B backend route:

```text
GET /api/accounts/{public_id}
```

The browser route is:

```text
/accounts/<public_id>
```

The frontend folder uses the existing dynamic segment name:

```text
frontend/app/accounts/[accountId]/page.tsx
```

In this slice, `accountId` is treated as the Account `public_id`.

## Scope

Included:

```text
Add read-only Account detail/profile shell
Link Account names in the list page to the detail shell
Fetch Account details from GET /api/accounts/{public_id}
Use browser token key pbl_auth_token
Use relative API paths
Show loading, missing-token, permission, not-found and invalid-link errors
Display existing Account fields from Slice 1B response
Show planned Account tabs as placeholders only
Update documentation and NEXT_STEPS
```

Excluded:

```text
Account edit form
Contacts tab implementation
Addresses tab implementation
PAN/GST tab implementation
Classification tab implementation
Documents/events tab implementation
Duplicate detection workflow
Lead conversion
Opportunity creation
Customer activation
Credit checks
File upload
Backend schema/API changes
Large UI redesign
```

## Files changed

```text
frontend/app/accounts/[accountId]/page.tsx
frontend/app/accounts/page.tsx
frontend/app/page.tsx
docs/agent/slices/slice-1e-account-detail-profile-shell.md
docs/agent/acceptance/slice-1e-account-detail-profile-shell-acceptance.md
docs/continuity/NEXT_STEPS.md
docs/agent/contracts/account-business-party-contract.md
```

## Implementation notes

- The backend remains the authority for read permission.
- The frontend provides user-friendly error messages for common API failures.
- This slice does not create additional API routes or database migrations.
- Planned tabs are deliberately placeholders so later agents can implement one bounded tab at a time.

## Acceptance criteria

Automated:

```text
backend pytest passes
frontend build passes using the safe .next cleanup sequence
frontend npm test stub passes
```

Manual:

```text
Login as sales1 or admin1
Open /accounts
Refresh Accounts
Click an Account name
Confirm /accounts/<public_id> opens
Confirm profile summary fields are displayed
Confirm Back to Accounts works
Login as finance1, ops1 or readonly1
Confirm they can open Account detail because read access is allowed
Clear token or logout and confirm Account detail shows login/session message
Open an invalid UUID-like Account URL and confirm friendly not-found/invalid-link message
```

## Completion rule

Slice 1E is complete only after:

```text
tests pass
manual detail-page acceptance passes
documentation is updated
changes are committed and pushed
helper scripts/ZIP files are not committed
```

## UX hardening follow-up

After manual review, Slice 1E added a small UX hardening follow-up:

```text
Accounts page auto-loads recent Accounts when an active token is present
Refresh Accounts remains available for manual reload
Left navigation includes a Logout action for prototype session testing
Hydration warning with fdprocessedid is documented as likely browser-extension interference unless reproduced without extensions
```

## Session-state UX hardening addendum

Manual review after the first Slice 1E UX hardening found that the navigation session action did not update immediately after login. This was corrected by dispatching a `pbl-session-changed` event after successful login and making the navigation session action listen for that event.

The login form and logout button also suppress hydration warnings caused by browser-injected form attributes such as `fdprocessedid`.

## Follow-up: dashboard role-aware action visibility

A Slice 1E follow-up hardened the dashboard so that `Create Account` is shown only to roles that are allowed to create Accounts: `ADMIN`, `SALES_USER` and `SALES_MANAGER`.

This preserves the rule that backend authorization is authoritative, while frontend navigation and visible actions should guide users according to their role and should not advertise unavailable actions as normal workflow choices.
