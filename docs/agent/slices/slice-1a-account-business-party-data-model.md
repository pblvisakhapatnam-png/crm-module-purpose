# Slice 1A - Account / business_party Contract and Data Model

## Goal

Create the first real CRM domain foundation: Account / business_party.

This slice establishes the database table, naming convention, contract document, and regression tests.

## Scope

Included:

- Account / business_party contract documentation;
- `business_party` table migration;
- minimal account contract constants;
- backend tests proving the table exists and accepts a minimal draft Account record.

Excluded:

- frontend Account UI;
- create/list APIs;
- lead conversion;
- customer activation;
- credit checks;
- document linking UI.

## Acceptance criteria

1. Alembic migration upgrades cleanly.
2. `business_party` table exists.
3. Table includes Slice 1A foundation columns.
4. A minimal draft Account can be inserted.
5. Existing Slice 0 tests still pass.
6. No frontend behavior changes.
7. No helper scripts or `.env` files are committed.

## Commands

Apply migration:

```powershell
docker compose exec backend alembic upgrade head
```

Run tests:

```powershell
docker compose exec backend pytest
```

Optional SQL Server column check:

```powershell
docker compose exec backend python -c "from app.core.database import SessionLocal; from sqlalchemy import text; db=SessionLocal(); rows=db.execute(text(\"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='business_party' ORDER BY ORDINAL_POSITION\")).fetchall(); print([r[0] for r in rows]); db.close()"
```

## Completion rule

Commit only after tests pass.