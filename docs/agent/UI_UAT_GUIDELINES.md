# UI UAT Guidelines

## Purpose

These guidelines define how each small UI slice should be manually tested by a human reviewer.

## Core rule

Each slice must be small enough that a human can test the main flow in about 10-20 minutes.

If a slice cannot be manually tested in that time, split it further.

## UI design approach

The UI should be workflow-style, not just database CRUD.

For Account / business_party, the initial UI should use tabs:

```text
Profile
Contacts
Addresses
PAN / GST
Classification
Documents
Events
```

Only the tabs included in the current slice need to be functional.

## Minimum UI acceptance checklist

Every UI slice acceptance file should specify:

- page or route to open;
- test user and role;
- data to create or use;
- positive-path steps;
- negative-path steps;
- expected messages;
- expected saved data;
- expected navigation;
- known limitations.

## Positive-path testing

Positive-path checks should confirm the normal intended workflow.

Example:

1. Login as Sales User.
2. Open Accounts.
3. Create a new Account with minimum required fields.
4. Save.
5. Confirm Account appears in list.
6. Open Account detail page.
7. Confirm created fields are displayed.

## Negative-path testing

Negative-path checks should confirm that invalid or unauthorized actions are handled properly.

Examples:

- required field missing;
- duplicate warning appears;
- invalid PAN/GST format is flagged;
- Read Only user cannot edit;
- unauthenticated user is redirected or blocked.

## Visual checks

For each screen, check:

- labels are understandable;
- mandatory fields are obvious;
- error messages appear near the field or action;
- tabs and navigation are clear;
- save/cancel behavior is clear;
- no raw internal model names like `business_party` appear in user-facing labels unless intended.

## Data checks

After saving data:

- reload the page;
- confirm saved values persist;
- confirm list/detail values match;
- confirm related tab counts or summaries are reasonable where used.

## Acceptance outcome

Use one of these statuses:

```text
Pass
Pass with minor issues
Fail - functional issue
Fail - usability issue
Blocked
```

Record issues in the acceptance checklist, and any rework they cause in the slice record.
