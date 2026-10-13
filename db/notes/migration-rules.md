# Migration Rules

## Undoing a release: restore the backup, never `alembic downgrade`

Recorded 7 October 2026 (TB-1 finding TB1-405, corrective package CS-03 item 2). It applies to every database that
holds data people entered: the two hosted test sites, a vendor's, production.

1. **Take a backup immediately before every upgrade.** The backend applies a release's migrations as it starts, so on
   the hosted test sites the backup comes before `deploy.sh`, every time. Only a site's very first deployment, on an
   empty database, has nothing to back up. Note the backup's stamp: it is the point the release is undone to.
2. **Undo a release by restoring that backup, after putting the previous release back in place.** Everything entered
   since the backup is lost; tell the users. The steps, in their order, are in
   PBL's runbook for its test sites (not part of this copy); a production runbook must carry the same steps.
3. **Never run `alembic downgrade` on a populated database.** A downgrade is for a development or empty database only,
   such as the "downgrade one revision, then upgrade to head" check a migration's own acceptance records.

### Why a downgrade is not an undo

TB-1 read every revision's downgrade and ran two of them on a copy of seeded data. On a database that holds data, a
downgrade:

- deletes what its upgrade's tables and rows came to hold. TB-1 found that of every revision up to 0047 except
  `20260629_0005` and `20260906_0032` - and 0032 only because it refuses when governed authority data would be lost.
  `20260629_0002` has since stopped creating the demo users, and its downgrade no longer deletes them;
- removes what its upgrade did not create: revisions 0012, 0014, 0015, 0017 and 0021 insert their statuses only when
  absent, and 0044 creates the `btree_gist` extension only if missing, but each downgrade removes them
  unconditionally. Demonstrated: a Lead status that existed before 0012, and `btree_gist` installed before 0044, were
  both removed;
- leaves live rows inconsistent. Demonstrated: downgrading a seeded database below 0012 left a Lead holding a status
  the status list no longer has;
- can leave a database that no upgrade brings back. Demonstrated: once a document has been uploaded, a downgrade below
  `20260908_0034` drops the document's storage columns but keeps its row, and upgrading again then fails at 0034 on its
  own check - and the uploaded file has lost its record.

Making every downgrade safe on populated data is not planned, because no policy makes a downgrade the way back.

### Why the previous release goes back first

The backend applies migrations every time it starts. A backup restored while the newer release is still deployed is
therefore brought straight back up to the newer release's schema by the backend's next start - the restore undoes the
data, not the release. And the previous release's backend cannot start on the newer database at all: its migrations do
not know the newer revision. So the previous release is deployed first and fails to start - expected, and checked to be
that failure and no other before going on, as the runbook says - and the restore then replaces the database and starts
it on data it knows.

### Still to come

The rest of corrective package CS-03 (`docs/agent/tb-1/TB_1_CORRECTIVE_SLICE_REGISTER.md`): a migration that fails at
start is retried for two minutes as if the database were not ready, rather than stopping at once with its message
(TB1-405 item 1, before production); `btree_gist`, PostgreSQL 13 or later and the right to create an extension are
nowhere named as deployment prerequisites (item 3, before vendor handover); `alembic revision --autogenerate` would
propose dropping most tables and nothing stops it being run (TB1-400); and no test upgrades a populated database
(TB1-701).

*Reconciled 8 October 2026 (the TB-1 vendor-handover records package):* TB1-405 items 1 and 3 and TB1-400 are done -
the three sections below. Only TB1-701, a CI job that upgrades a populated database, is still to come.

## Migrations are written by hand

Recorded 8 October 2026 (TB-1 finding TB1-400, corrective package CS-03).

- **Write every migration by hand**, as `op.create_table`, `op.add_column` and the like, or as plain PostgreSQL SQL in
  `op.execute` (ADR-028: never T-SQL, never a second dialect). Name it `YYYYMMDD_NNNN_<what>.py` in
  `backend/alembic/versions/`, with `down_revision` the current single head, and check from an empty database before
  it is reviewed (`docs/agent/TESTING_STRATEGY.md`, section 6).
- **`alembic revision --autogenerate` and `alembic check` are refused** (`backend/alembic/env.py`, with a test,
  `backend/tests/test_tb1_400_autogenerate_refused.py`). They compare the database with the SQLAlchemy models, and the
  models are not the schema: the application reads and writes every table through SQL text, and the models describe
  only the platform tables and a few others - about a third of the tables, some of them out of date. Compared with the
  database, they would propose dropping every other table, its indexes and a uniqueness rule.
- **The `models.py` files are not the schema.** Do not add a model to describe a new table; the migration is the
  description. Making the models complete would be a large change for no use, and is not planned.
- **One chain, one head.** Parallel lanes take turns on it (`AGENTS.md`, "Parallel lanes and worktrees").

## When the backend starts

Recorded 8 October 2026 (TB-1 finding TB1-405 item 1, corrective package CS-03).

The backend applies the migrations itself each time it starts (`backend/app/startup.py`), in this order:

1. It waits for the database: a connection refused is retried every 2 seconds, up to 60 times.
2. Once the database answers, it runs `alembic upgrade head` once. If that fails - a migration's own error, or one that
   refuses by design, as `20260908_0037` does when line details hold hours with no basis - the backend stops at once:
   Alembic's error is in the log, then "The database migration failed (alembic exit status N) ... does not retry it".
   Every migration runs in one transaction, so the failed upgrade changed nothing.

A container with a restart policy (the hosted test sites: `restart: unless-stopped`) is then started again by Docker,
and fails the same way each time, with the same message, until the cause is dealt with or the release is undone (above).
Running migrations as a separate deployment step instead, before the new backend starts, remains an option for
production; nothing here depends on it.

## What the database must provide

Recorded 8 October 2026 (TB-1 finding TB1-405 item 3, corrective package CS-03). The local Compose stack and the hosted
test sites meet all of these; a vendor's or a managed database must too.

- **PostgreSQL 17**, the supported version (ADR-028). The migrations themselves need at least PostgreSQL 13:
  `20260908_0037` calls `gen_random_uuid()`, built in since 13.
- **The `btree_gist` extension**, available to install. `20260908_0044` runs `CREATE EXTENSION IF NOT EXISTS
  btree_gist` for the date-overlap rules of Eligibility and Resource Assignments (`EXCLUDE USING gist`). It ships with
  PostgreSQL's standard contrib package; some managed services list the extensions they allow.
- **The right to create it, and to create tables.** The backend migrates with the role it connects as. `btree_gist` is
  a trusted extension, so the CREATE privilege on the database is enough to install it - or a database administrator
  installs it beforehand, and the migration then finds it. Creating tables needs CREATE on the `public` schema, which
  since PostgreSQL 15 only the database's owner has unless granted. The simplest arrangement, and the one Compose makes,
  is a role that owns the database.

