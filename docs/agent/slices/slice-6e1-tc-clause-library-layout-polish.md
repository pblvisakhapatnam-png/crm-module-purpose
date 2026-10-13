# Slice 6E.1 - T&C Clause Library Layout Polish

## Status

Implemented.

## Objective

Improve the T&C Clause Library page layout so the selected clause detail is visible near the top instead of below the full clause table.

## Implemented Scope

Frontend-only layout polish:

```text
- Filter/search panel remains at the top left on wide screens.
- Selected clause detail panel now appears at the top right on wide screens.
- Clause list/table remains below both panels.
- On smaller screens, the page stacks filter/search, selected detail and clause list vertically.
- Loaded clause count remains visible in the filter/search panel.
- View action still selects a clause and updates the same detail fields.
- Source-derived/prototype warning remains visible.
- Frontend still uses relative /api/tc-clauses URLs.
```

Error handling:

```text
- Successful clause load/filter now explicitly clears any old page-level error message.
- Real API/network/auth errors are still shown.
```

## Out Of Scope

```text
- no backend code;
- no database migrations;
- no API route changes;
- no seed data changes;
- no business behavior change;
- no contract changes;
- no change to the frozen Accepted Offer -> Work Order handoff contract.
```

## Checks

Required:

```powershell
git diff --check
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
```

Backend tests are not required unless backend files change unexpectedly.

