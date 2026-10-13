# Slice 6B - Demo Navigation and UI Polish Foundation

## Purpose

Make the implemented Lead -> Account -> Opportunity -> Commercial Offer -> Work Order shell flow more vendor-demonstrable without adding deferred production functionality.

## In scope

```text
- Add a consistent application shell and primary navigation treatment.
- Add a lightweight visible demo-flow cue for the implemented business chain.
- Improve the dashboard as an operational demo entry point.
- Standardize status badge styling on implemented flow list pages.
- Standardize empty-state and action/message presentation through shared frontend styling.
- Preserve Slice 6A linked-record navigation and Slice 6A.1 Account traceability guard behavior.
```

## Out of scope

```text
- No T&C master or clause library.
- No Customer Master activation.
- No Finance approval.
- No Work Order release/posting.
- No equipment assignment.
- No crew assignment.
- No log sheets.
- No billing.
- No full approval workflow.
- No backend route, schema, service or database change.
```

## Frontend behavior

Slice 6B introduces a shared frontend styling layer and app shell that applies across the implemented prototype pages.

The UI should continue to use:

```text
- Account as the user-facing term.
- business_party only for internal/domain/database references.
- relative /api URLs in browser code.
- pbl_auth_token as the browser token key.
```

The demo dashboard and sidebar should make the implemented chain visible:

```text
Lead -> Account -> Opportunity -> Commercial Offer -> Work Order shell
```

List pages for Lead, Account, Opportunity, Commercial Offer and Work Order should use consistent status badge and empty-state treatment while preserving existing data loading, pagination, role visibility and action behavior.

## Backend behavior

No backend behavior changes are introduced by this slice. Backend permission checks, lifecycle guards, business-event rules and Account traceability validation remain authoritative.

## Events

No new `business_event` is created because this slice is UI/navigation polish only. Existing successful business actions continue to record their established events.

## Testing notes

Because frontend code changes, run:

```powershell
git diff --check
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
```

Run backend pytest only if backend files are touched.
