# Slice 1F - Account List Pagination and Session-Viewed Links

## Purpose

Slice 1F hardens the Account list before moving to Account child tabs such as Contacts.

It establishes two reusable list-screen rules:

1. Long lists must have simple page navigation.
2. Links opened during the current login session may be visually marked, but this must be application-controlled and must not rely on browser native visited-link history.

## Scope

Included:

```text
Backend offset support for GET /api/accounts
Frontend Account list page size of 20 records
Previous and Next controls
Refresh current page button
Session-viewed Account link state using sessionStorage
Viewed state reset on login and logout
Backend pagination test
Documentation updates
```

Excluded:

```text
Search
Sorting
Filters
Export
Total count
Grid framework
Account edit
Contacts
Addresses
PAN/GST
Documents/events tab implementation
```

## API contract

`GET /api/accounts` supports:

```text
limit        optional; default 20; min 1; max 100
offset       optional; default 0; min 0
status_code  optional; filters by account_status_code
```

Sort order remains:

```text
created_at DESC, id DESC
```

The response shape remains:

```text
list[AccountResponse]
```

No pagination wrapper or total count is added in this slice.

## Frontend behaviour

The Accounts page requests `limit=21` and displays only 20 records. The 21st record is used only to decide whether the Next button should be enabled.

The page displays:

```text
Refresh current page
Previous
Next
Clear
```

Account links opened during the current login session are shown as viewed. The viewed state resets on login and logout.

## Files changed

```text
backend/app/modules/accounts/repository.py
backend/app/modules/accounts/service.py
backend/app/modules/accounts/routes.py
backend/tests/test_accounts_api.py
frontend/app/accounts/page.tsx
frontend/app/accounts/[accountId]/page.tsx
frontend/app/login/page.tsx
frontend/components/layout/SessionActions.tsx
docs/agent/contracts/account-business-party-contract.md
docs/agent/slices/slice-1f-account-list-pagination-viewed-links.md
docs/agent/acceptance/slice-1f-account-list-pagination-viewed-links-acceptance.md
docs/continuity/SLICE_1F_LIST_PATTERN.md
docs/continuity/NEXT_STEPS.md
```

## Completion rule

Slice 1F is complete only when:

```text
Backend pytest passes
Frontend build passes using the safe .next clearing sequence
Frontend npm test command passes
Manual pagination checks pass
Manual session-viewed link checks pass
Documentation is committed with the code
```

## Test data hygiene

Slice 1F also hardens Account API tests so repeated pytest runs do not keep adding Account records to the shared development database.

Tests that create Accounts must clean up their own `business_party` and related `business_event` rows.
