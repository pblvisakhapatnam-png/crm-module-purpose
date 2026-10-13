# Slice 6E.1 Acceptance - T&C Clause Library Layout Polish

## Scope Confirmation

This is a frontend/UI polish slice only.

Expected result:

```text
- No backend/API/migration/seed/business behavior changes.
- T&C Clause Library filters remain functional.
- Selected clause detail is visible near the top of the page.
- Clause list/table remains below the filter and detail panels.
```

## UI Acceptance

Scenario:

```text
Review T&C Clause Library layout.
```

Role:

```text
Sales User or Sales Manager.
```

Starting URL:

```text
/terms-and-conditions
```

Positive path:

```text
1. Login as a Sales user.
2. Open /terms-and-conditions.
3. Confirm the filter/search panel appears near the top.
4. Confirm the selected clause detail panel appears beside it on a wide screen.
5. Confirm the clause list/table appears below both panels.
6. Click View on another clause.
7. Confirm the detail panel updates without changing API behavior.
8. Apply a filter/search.
9. Confirm loaded clause count remains visible and old page errors are cleared after successful load.
```

Small-screen check:

```text
1. Narrow the browser viewport.
2. Confirm the layout stacks as filter/search, selected detail, then clause list/table.
```

Expected result:

```text
- The same detail fields remain visible: business line, source clause, risk category, approval flags, clause text and source reference.
- The source-derived/prototype warning remains visible.
- Real API/auth/network errors still appear if the API call fails.
```

Deferred checks:

```text
- no Commercial Offer attachment;
- no line-level T&C selection;
- no deviation/new-clause approval;
- no backend permission changes;
- no Work Order handoff changes.
```

## Automated Checks

Run:

```powershell
git diff --check
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
```

