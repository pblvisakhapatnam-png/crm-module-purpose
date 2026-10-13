# Slice 6B.2 - Demo Readiness UI Consistency Pass

## Purpose

Improve the professional appearance and consistency of the existing prototype demo surfaces without adding new business features or changing backend behavior.

## In scope

```text
- Dashboard demo-readiness wording.
- Shared frontend styling for page actions, form cards, list cards, table containment, record cards and action-local feedback.
- Consistency pass on Lead, Account, Opportunity, Commercial Offer and Work Order shell list/create screens.
- Small user-facing terminology cleanup where an internal record type was displayed on Account/Commercial Offer surfaces.
```

## Out of scope

```text
- No backend route, schema, service, repository, migration or authorization change.
- No Customer Master activation.
- No Work Order release/posting.
- No equipment assignment.
- No crew assignment.
- No log sheets.
- No billing.
- No approval workflow.
- No Opportunity lines or Commercial Offer revision/versioning.
- No test-data filtering.
```

## Frontend behavior

The slice adds reusable CSS classes for:

```text
- consistent page action rows;
- primary and secondary button links;
- contained list/content/form cards;
- responsive form field grids;
- horizontally contained data tables;
- consistent record-card spacing;
- action-local feedback spacing.
```

The existing pages keep their current API calls, role-aware visibility and business behavior. Browser API calls continue to use relative `/api` URLs.

## Backend behavior

No backend files are changed. Backend permissions, lifecycle guards, business events and Account traceability rules remain authoritative.

## Events

No new `business_event` is created because this is a UI-only consistency slice.

## Testing notes

Run:

```powershell
git diff --check
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
```

Run backend pytest only if backend files are changed.
