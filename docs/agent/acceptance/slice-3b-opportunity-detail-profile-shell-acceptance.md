# Slice 3B - Opportunity Detail / Profile Shell Acceptance

## Slice status

```text
Prepared for implementation
```

## Automated checks

Run from repo root after applying the script:

```powershell
docker compose stop frontend
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

Recommended regression check:

```powershell
docker compose exec backend pytest
```

Expected result:

```text
- Frontend production build passes.
- Frontend test script completes.
- Backend regression tests pass if run.
```

No Alembic command is required for this slice because Slice 3B does not add a migration.

## Manual happy path

Test user:

```text
sales1 / password
```

Steps:

```text
1. Login as sales1.
2. Open /opportunities.
3. Create an Opportunity if no test Opportunity exists.
4. Open one Opportunity profile from the list.
5. Confirm the profile shell shows:
   - Profile snapshot
   - Workflow position
   - Account context
   - Source / enquiry context
   - Customer requirement
   - Commercial readiness
   - Next workflow boundaries
   - Audit and traceability
6. Confirm the page clearly says stage updates, Lead conversion, quote/commercial offer, approvals, credit checks and Work Order handoff are deferred.
7. Confirm Back to Opportunities and Refresh profile work.
```

Expected result:

```text
Opportunity profile loads with structured read-only sections. No status update, conversion, quote or Work Order action is available.
```

## Manual permission check

Test user:

```text
finance1 / password
```

Steps:

```text
1. Login as finance1.
2. Open /opportunities.
3. Open an Opportunity profile.
4. Confirm profile loads.
5. Confirm the page states that the profile is read-only for the current role.
6. Confirm no create/update/stage action appears on the detail page.
```

Expected result:

```text
Finance can view the Opportunity profile only. Backend permissions remain authoritative.
```

## Manual event-link role check

Test users:

```text
admin1 / password
readonly1 / password
sales1 / password
```

Steps:

```text
1. Login as admin1 and open an Opportunity profile.
2. Confirm View recent business events is visible.
3. Login as readonly1 and confirm the link is visible.
4. Login as sales1 and confirm the profile states that event viewing is restricted.
```

Expected result:

```text
Event-page navigation is role-aware. The Opportunity page does not expose event data directly and does not bypass /api/events/recent permissions.
```

## Deferred checks

```text
- Opportunity update and stage movement.
- Lead conversion to Account + Opportunity.
- Account linkage and duplicate treatment.
- Quote/commercial offer creation.
- Credit exposure and approval gates.
- Work Order handoff.
- Rich event filtering by record.
- Rich Opportunity search/filtering and pagination UX refinement.
```
