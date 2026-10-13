# Slice 2E Acceptance - Lead Qualification / Closure Decision Foundation

## Automated checks

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend alembic heads
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
docker compose exec backend pytest

docker compose stop frontend
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
Remove-Item -Recurse -Force .\frontend\.next -ErrorAction SilentlyContinue
docker compose up -d frontend
```

Expected Alembic head/current:

```text
20260705_0014 (head)
```

## Manual happy path

```text
1. Login as sales1 or admin1.
2. Open an existing Lead detail page.
3. Confirm Lead Details and Lead Activities still show correctly.
4. In Lead Qualification / Closure Decision, choose Qualified.
5. Enter reason and decision notes.
6. Save the decision.
7. Confirm the Lead status changes to QUALIFIED.
8. Confirm the decision reason/notes/decided-at fields are visible.
9. Confirm no Account or Opportunity was created by this action.
```

## Validation check

```text
1. Choose Unqualified or Closed.
2. Leave Reason blank.
3. Confirm the UI or API rejects the decision.
4. Enter a reason and save.
5. Confirm the decision succeeds.
```

## Permission check

```text
1. Login as finance1, ops1 or readonly1.
2. Open a Lead detail page.
3. Confirm Lead details, activities and current qualification decision information are visible.
4. Confirm the qualification decision form is not available.
```
