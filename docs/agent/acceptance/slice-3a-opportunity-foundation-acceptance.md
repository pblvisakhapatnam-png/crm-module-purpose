# Slice 3A - Opportunity Foundation Acceptance

## Slice status

```text
Prepared for implementation
```

## Automated checks

Run from repo root:

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend alembic heads
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
docker compose exec backend pytest
docker compose stop frontend
Remove-Item -Recurse -Force .rontend\.next -ErrorAction SilentlyContinue
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
Remove-Item -Recurse -Force .rontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

Expected result:

```text
- Alembic reaches 20260705_0015.
- Backend tests pass.
- Frontend production build passes.
- Frontend test script completes.
```

## Manual happy path

Test user:

```text
sales1 / password
```

Steps:

```text
1. Login as sales1.
2. Open /opportunities.
3. Click Create Opportunity.
4. Create an Opportunity with a unique name, manual source, requirement summary, optional estimate and expected close date.
5. Confirm success message appears near the Create Opportunity button.
6. Open the created Opportunity profile.
7. Confirm list/detail/profile values are visible.
8. Confirm profile states that Lead conversion, Account linkage, quote/commercial offer, approvals, credit checks and Work Order handoff are deferred.
```

Expected result:

```text
Opportunity is created, listed and viewable. OpportunityCreated business event is created. No Lead conversion or quote is created.
```

## Manual permission check

Test user:

```text
finance1 / password
```

Steps:

```text
1. Login as finance1.
2. Open /opportunities and confirm the list loads.
3. Open an Opportunity profile and confirm it loads.
4. Open /opportunities/new.
```

Expected result:

```text
Finance can list/view Opportunities but cannot create an Opportunity. Backend POST /api/opportunities returns 403 for finance1.
```

## Manual validation check

Test user:

```text
sales1 / password
```

Steps:

```text
1. Open /opportunities/new.
2. Try to create without an Opportunity name.
3. Try backend/API creation with an invalid source or status, if needed.
4. Try a negative estimated value.
```

Expected result:

```text
Required name is blocked. Invalid source/status/value returns validation error. No invalid Opportunity is saved.
```

## Deferred checks

```text
- Opportunity update and stage movement.
- Lead conversion to Account + Opportunity.
- Account linkage and duplicate treatment.
- Quote/commercial offer creation.
- Credit exposure and approval gates.
- Work Order handoff.
- Rich filtering/search and pagination UX refinement.
```