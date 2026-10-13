# Slice 6E Acceptance - T&C Master / Clause Library Foundation

## Acceptance Scope

Validate that users can browse source-derived prototype T&C clauses and that the implementation remains read-only and bounded.

## Automated Checks

Run:

```powershell
git diff --check
docker compose exec backend alembic current
docker compose exec backend alembic head
docker compose exec backend pytest
docker compose stop frontend
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

## API Acceptance

| Scenario | Role/User | Route | Expected Result |
| --- | --- | --- | --- |
| Unauthenticated list | None | `GET /api/tc-clauses` | 401 |
| Authorized list | Sales User / `sales1` | `GET /api/tc-clauses` | 200 with at least 15 clauses |
| Read-only list | Management Read Only / `readonly1` | `GET /api/tc-clauses?limit=5` | 200 |
| Filter/search | Sales User / `sales1` | `GET /api/tc-clauses?business_line=HIRING&applies_to_line=true&search=overtime` | Returns Hiring line-applicable Overtime clause |
| Detail lookup | Sales User / `sales1` | `GET /api/tc-clauses/{public_id}` | 200 with full clause text/source reference |
| Missing detail | Sales User / `sales1` | `GET /api/tc-clauses/00000000-0000-0000-0000-000000009999` | 404 |
| Invalid filter | Sales User / `sales1` | `GET /api/tc-clauses?business_line=LEGAL` | 422 |

## UI Acceptance

Scenario:

```text
Browse T&C Clause Library.
```

Role:

```text
Sales User or Sales Manager.
```

Starting URL:

```text
/terms-and-conditions
```

Steps:

```text
1. Login as a Sales user.
2. Open the dashboard.
3. Open T&C Clause Library from the dashboard or sidebar.
4. Confirm the page loads source-derived prototype clauses.
5. Filter by Equipment Hiring.
6. Search for overtime.
7. Open/view the Overtime clause detail.
8. Confirm the page states that attachment, line-level selection, approval and document generation are deferred.
```

Expected result:

```text
- Clause table shows clause ID, business line, category, title, mandatory/default flags and active status.
- Detail panel shows clause text, source clause, risk category, approval flags and source reference.
- UI does not imply legal approval or final quote output.
```

Negative/permission check:

```text
- Logout and open /terms-and-conditions.
- Expected: page asks user to login and does not show clause data.
```

## Deferred Checks

Do not test these in Slice 6E:

```text
- attaching clauses to Commercial Offers;
- line-level T&C selection;
- deviation/new-clause approval;
- legal versioning;
- quote PDF/document generation;
- Work Order release/posting;
- billing.
```

## Known Manual Gaps

The seeded clause text is source-derived prototype wording. PBL legal/business review is required before production use.

