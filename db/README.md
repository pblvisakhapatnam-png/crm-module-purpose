# Database

What this folder holds, as of 8 October 2026 (TB-1 REP-1, findings TB1-105 and TB1-903):

- `notes/migration-rules.md` - **current rules**: migrations are written by hand (never `alembic revision
  --autogenerate`), what the backend does with them when it starts, what a database must provide, and how a release
  is undone (restore the backup; never `alembic downgrade` on a populated database).
- `notes/naming-conventions.md` - **current conventions**: how tables, columns, keys, constraints and references are
  named, and the two older conventions the first CRM tables keep.

The schema itself is the Alembic migrations in `backend/alembic/versions/`. The reference data the database holds -
roles, permissions, workflow statuses - is inserted by those migrations too; code lists such as document types are
constants in each module's `contract.py`.
