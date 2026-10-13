# TE-2B - SQL Server to PostgreSQL Migration

## Status

**TE-2B implemented, independently reviewed and accepted on 14 August 2026; committed and
integrated on `main` as commit `75fd4fc`.**

TE-2B Part 1 was independently reviewed and accepted as the intermediate checkpoint. The combined
Part 1 and Part 2 package was independently reviewed and accepted on 14 August 2026, then
committed under project-owner direction.

Part 1 delivered the confirmed database decision, the PostgreSQL runtime and configuration, and the
full Alembic chain ported to PostgreSQL and verified against an empty database. Part 2 converts the
active repository SQL, tooling, tests and generated skeleton, and runs the full validation
sequence. Part 2 implementation and testing are complete and the accepted work is committed.

Independent review verified the correction passes, focused safety tests and residue preservation.
TE-2CI followed TE-2B; see
`docs/agent/technical-enablement/TE_2CI_GITHUB_ACTIONS_VALIDATION_FOUNDATION.md` for its current
status. See `docs/continuity/NEXT_STEPS.md` for the active package.

Technical-enablement work package, not a numbered CRM business slice.

## Objective

Record PostgreSQL as the frozen production database (ADR-028) and convert the database/runtime
foundation from SQL Server to PostgreSQL, preserving every existing Alembic revision ID, its
dependency order and its logical schema.

## Confirmed decision

PBL confirmed PostgreSQL. This is recorded as ADR-028 in `docs/agent/ARCHITECTURE_DECISIONS.md`,
which supersedes ADR-006 for the production baseline while preserving ADR-006 as historical
evidence of the prototype's SQL Server implementation.

Key points, in full in ADR-028:

- PostgreSQL 17, latest supported minor release.
- SQLAlchemy `postgresql+psycopg` dialect, Psycopg 3.
- Single supported runtime after TE-2B; no permanent dual-dialect code.
- Revision IDs and order preserved; their implementation may be ported from T-SQL, because no
  production database was ever released from the SQL Server chain.
- Fresh schema from migrations. No row-level data migration. Local prototype/demo rows are
  recreated with existing seed migrations and TE-1 smoke-data tooling.
- The old local SQL Server Docker volume is preserved untouched as rollback/reference evidence.
- Database timestamps stored in UTC; UI display convention (Asia/Kolkata) unchanged.

## Part 1 scope

### Runtime and configuration

| File | Change |
| --- | --- |
| `docker-compose.yml` | SQL Server service replaced with `postgres:17`; new `postgres-data` volume; `pg_isready` health check; backend `depends_on` uses `condition: service_healthy`; all `container_name` entries removed |
| `backend/Dockerfile` | Microsoft ODBC repository/key setup, `msodbcsql18`, `unixodbc`, `unixodbc-dev`, `gcc`, `g++`, `curl`, `gnupg` and `apt-transport-https` removed |
| `backend/requirements.txt` | `pyodbc==5.2.0` removed; `psycopg[binary]==3.2.3` added. SQLAlchemy and Alembic pins unchanged |
| `backend/app/core/config.py` | MSSQL settings replaced by `database_url` plus `postgres_*` fallback fields |
| `backend/app/core/database.py` | Psycopg 3 URL building and normalization; `current_database()`; UTC session; `ensure_database_exists()` and `build_pyodbc_connection_string()` removed; summary reports dialect/host/port/database/user |
| `backend/app/startup.py` | Waits for a reachable database with `SELECT 1` then runs migrations; no longer creates the database |
| `backend/app/main.py` | `/api/platform/db-health` docstring made database-neutral |
| `backend/alembic/env.py` | Applies migrations on a UTC session using the shared `CONNECT_ARGS` |
| `.env.example` | `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` for container initialization, plus a canonical `DATABASE_URL` |

### Connection URL handling

`postgresql+psycopg://` is canonical. A hosted or legacy provider URL using the bare
`postgresql://` scheme or the deprecated `postgres://` alias is normalized to Psycopg 3. Any other
dialect raises `ValueError` at startup rather than being silently accepted, so a stale SQL Server
URL fails loudly instead of producing a confusing driver error.

The password is never rendered in configuration summaries, health responses or logs.
`build_safe_database_url_summary()` uses SQLAlchemy's `render_as_string(hide_password=True)`, and
`get_database_settings_summary()` returns only dialect, host, port, database and user.

### Database provisioning

`ensure_database_exists()` is removed. The database is provisioned by the PostgreSQL container
(`POSTGRES_DB`) or by the managed provider. Application startup only waits for connectivity and
applies migrations. This also removes the `master`-database connection and the
`_validate_database_name()` guard that existed solely to make `CREATE DATABASE [name]` string
interpolation safe.

### Old SQL Server volume

`mssql-data` is deliberately **not** declared in the `volumes:` block. Leaving it undeclared takes
it out of Compose's management, so `docker compose down -v` cannot delete it and it survives as
rollback/reference evidence. Declaring it would have had the opposite effect. Delete it manually
only after TE-2B is accepted.

## Migration chain

All 28 revisions from `20260629_0001` through `20260713_0029` were ported. **Every revision ID,
every `down_revision` edge and the single linear head are unchanged.** Verified head:
`20260713_0029`.

### Conversion patterns applied

| SQL Server construct | PostgreSQL replacement |
| --- | --- |
| `INT IDENTITY(1,1)` raw DDL | `sa.Column(..., sa.Integer(), autoincrement=True)` via `op.create_table` (PostgreSQL sequence-backed) |
| `BIT` with `DEFAULT 0` / `DEFAULT 1` | `sa.Boolean()` with `server_default=sa.text("false"/"true")` |
| Literal `1` / `0` in seed INSERTs | `TRUE` / real Python booleans |
| `SYSUTCDATETIME()` | `sa.func.now()` (renders `now()`) / `CURRENT_TIMESTAMP` |
| `NVARCHAR(n)` / `NVARCHAR(MAX)` | `sa.Unicode(length=n)` / `sa.UnicodeText()` |
| `DATETIME`, `DATETIME2` | `sa.DateTime()` |
| `DECIMAL(18,2)` | `sa.Numeric(precision=18, scale=2)` |
| `dbo.` qualification | unqualified names in the default `public` schema |
| `CREATE UNIQUE INDEX ... WHERE ...` | `op.create_index(..., unique=True, postgresql_where=sa.text(...))` |
| `IF OBJECT_ID(...) IS NULL BEGIN CREATE TABLE ... END` | plain `op.create_table(...)` |
| `IF COL_LENGTH(...) IS NULL BEGIN ALTER TABLE ... ADD ... END` | plain `op.add_column(...)` |
| `IF NOT EXISTS (SELECT 1 FROM sys.indexes ...) BEGIN CREATE INDEX ... END` | plain `op.create_index(...)` |
| `EXEC(N'...')` wrappers | removed entirely |
| `sys.foreign_keys` / `sys.check_constraints` / `sys.default_constraints` guards | `op.create_foreign_key`, `op.create_check_constraint`, `op.drop_constraint` |
| `DROP CONSTRAINT df_*` for a column default | not needed; PostgreSQL attaches defaults to the column, so `op.drop_column` removes them |

### Idempotency workarounds removed

Several revisions were written defensively because interrupted T-SQL DDL could partially survive a
failed run, leaving a half-created table or column behind. PostgreSQL runs DDL transactionally: a
failed migration leaves nothing behind. Those `IF ... BEGIN ... END` guards are therefore replaced
with plain transactional operations rather than translated into PostgreSQL equivalents, exactly as
the work package required. No broad catch-and-ignore logic was introduced.

This behaviour was demonstrated during verification: the first upgrade attempt failed partway
through revision `20260704_0012`, and the entire upgrade rolled back to an empty database with no
partial schema and no `alembic_version` row.

### Seed-insert guards retained

The `IF NOT EXISTS (SELECT 1 FROM workflow_status WHERE ...)` guards around workflow-status and
T&C clause seeding are **DML** guards protecting seed content, not DDL-interruption workarounds.
They are preserved as `INSERT ... SELECT ... WHERE NOT EXISTS`, which keeps the original logical
behaviour. They were also converted from f-string interpolation to bound parameters, which removes
an injection-shaped pattern in code that embeds seed values directly into SQL text.

### Explicit parameter casts

In `INSERT INTO t (...) SELECT :a, :b, ... WHERE NOT EXISTS (... WHERE col = :b)`, a parameter used
in both the SELECT list and the WHERE comparison is ambiguous to PostgreSQL: it deduces `text` for
the bare SELECT-list occurrence and `character varying` for the comparison, and rejects the
statement with `AmbiguousParameter`. The affected parameters (`:module` and `:status_code` in the
five workflow-status seeds, `:clause_id` in the T&C seed) carry an explicit `CAST(... AS VARCHAR)`
with a comment explaining why. This was found by the empty-database verification run, not
predicted.

### Type-mapping notes for review

- `submitted_at` on `crm_commercial_offer` was `DATETIME2` in the SQL Server chain while every
  other timestamp was `DATETIME`. Both map to `sa.DateTime()` (`timestamp without time zone`), so
  the logical type is preserved and the incidental SQL Server precision difference disappears.
- `sa.Unicode` / `sa.UnicodeText` are portable SQLAlchemy types, not raw `NVARCHAR`. They render
  `NVARCHAR` only on SQL Server and `VARCHAR` / `TEXT` on PostgreSQL. They are retained because
  they preserve the original intent (these columns hold user-entered business text) without
  carrying any SQL Server-specific syntax.
- Platform-foundation timestamps already used `sa.DateTime(timezone=True)` with `sa.func.now()` and
  were left unchanged.

## Verification

Performed in an isolated Compose project named `pbl-te2b-part1`, using non-production test
credentials supplied through a scratchpad env file that was never written into the repository. The
normal project was never torn down and its old SQL Server volume was never touched.

### Sequence and results

| Step | Result |
| --- | --- |
| `docker compose -p pbl-te2b-part1 config` | Valid |
| Build backend image from working tree | Success |
| Start isolated PostgreSQL only | Success |
| Health check | `healthy` (pg_isready) |
| `alembic heads` | `20260713_0029 (head)` — exactly one head |
| `alembic history` | 28 revisions, single linear chain, no branches |
| Empty-database confirmation | 0 tables in `public` before upgrade |
| `alembic upgrade head` from empty | Success, all 28 revisions applied |
| `alembic current` | `20260713_0029 (head)` |
| Schema/constraint/index/seed inspection | 30 checks, all passed |
| Database connection + foundation-table helpers | Pass |
| `alembic downgrade base` then `upgrade head` | Both succeed; schema re-verified identical |
| URL normalization and dialect rejection | 10 checks, all passed |
| FastAPI platform/database smoke | 3 endpoints return 200, no password leakage |
| Teardown of isolated project and its test volume | Success |
| Old SQL Server volume after teardown | Present and unmodified |

### What the inspection confirmed

- 28 tables, exactly the expected set, no extras.
- `alembic_version` contains exactly `20260713_0029`.
- 6 roles, 6 users, 6 user-role assignments; all `is_active` are real booleans; pbkdf2 password
  hashes intact.
- 41 workflow statuses with the expected per-module split
  (business_party 10, commercial_offer 8, lead 11, opportunity 8, work_order 4); no seeded status
  inactive; guarded triage insert preserved its public ID, name and sort order.
- 15 T&C clauses, split HIRING 7 / TRANSPORTATION 8; the mixed true/false flag combination on
  `HIRE-TC-007` preserved exactly, proving the boolean conversion did not flatten values.
- Every business table has a primary key; 34 named foreign keys including the Slice 6O.1
  self-referencing `fk_crm_commercial_offer_base_offer`; 28 unique constraints; 28 check
  constraints; 151 indexes.
- All 7 filtered/partial unique indexes present and unique:
  `ux_crm_opportunity_source_lead_id_not_null`, `ux_crm_commercial_offer_code_not_null`,
  `ux_crm_work_order_code_not_null`, `ux_crm_commercial_offer_pricing_evidence_one_selected`,
  `uq_commercial_offer_tc_clause_active_clause`, `ux_commercial_offer_credit_review_current`,
  `ux_crm_work_order_amendment_customer_reference`.
- Flag columns are real PostgreSQL `boolean`; no `BIT` leftovers.
- `created_at` defaults render `now()`; no `SYSUTCDATETIME` survives.
- Live enforcement spot checks: the workflow-status module/code unique constraint and the T&C
  business-line check constraint both reject invalid rows.
- Session `TimeZone` is `UTC`; server version 17.10.

### Downgrade

All 28 downgrade functions are supported and were exercised. `alembic downgrade base` succeeds and
leaves only Alembic's own `alembic_version` table, and `alembic upgrade head` then rebuilds the
full verified schema. No revision has an unsupported or silently-skipped downgrade.

## Part 2 - application, tooling and test cutover

Part 2 converted every remaining T-SQL construct in the active layer, then proved the whole
application against PostgreSQL. No API contract, response shape, permission rule, business event,
public ID, visible business reference or workflow rule changed, and both frozen contracts are
untouched.

### Conversions applied

| T-SQL construct | PostgreSQL replacement | Where |
| --- | --- | --- |
| `SELECT TOP 1 ... WHERE ...` | `SELECT ... WHERE ... LIMIT 1` placed after the WHERE/ORDER BY | 18 sites across commercial_offers, work_orders, opportunities, leads, events, documents and one test |
| `SELECT TOP {n}` / `SELECT TOP (:limit)` | `LIMIT {n}` / `LIMIT :limit` after `ORDER BY` | events, documents |
| `OFFSET {n} ROWS FETCH NEXT {m} ROWS ONLY` | `LIMIT {m} OFFSET {n}` | accounts, commercial_offers, leads (x2), opportunities, work_orders, terms_and_conditions |
| `SYSUTCDATETIME()` | `CURRENT_TIMESTAMP` | 80 occurrences across 5 repositories, 2 route/test files |
| `ISNULL(MAX(col), 0)` | `COALESCE(MAX(col), 0)` | work_orders amendment sequence/line numbering |
| `'CO-' + RIGHT('000000' + CAST(id AS VARCHAR(20)), 6)` | same expression with `\|\|` concatenation | commercial_offers, work_orders business-reference generation |
| `is_active = 1` / `active = 1` | `IS TRUE` | accounts, commercial_offers, identity, workflow, leads, opportunities, one test |
| `SET active = 0` / `SET is_selected_basis = 1` | `SET ... = FALSE` / `= TRUE` | commercial_offers, one test |
| Literal `1` in an INSERT `VALUES` list for a boolean column | `TRUE` | 6 sites (accounts x3, commercial_offers x3) |
| `params[...] = 1 if x else 0` bound to a boolean column | `bool(x)` / `False` | terms_and_conditions, accounts, leads, opportunities services |
| `DELETE alias FROM t alias INNER JOIN ...` | `DELETE FROM t alias USING ... WHERE ...` | 12 sites in the TE-1 cleanup harness, 16 across four test files |
| `JSON_VALUE(col, '$.key')` | `(NULLIF(col, '')::json ->> 'key')` | one test-cleanup query |

### Constructs the Part 1 handoff did not predict

Part 1 forecast four construct families (`SELECT TOP`, `OFFSET/FETCH`, `SYSUTCDATETIME`, `ISNULL`)
in ten files. The repository-wide audit found four more that a token count for those four patterns
could not surface, and each would have failed at runtime:

- **T-SQL `+` string concatenation** in the `CO-` and `WO-` business-reference generators. These
  produce ADR-007 visible references, so the `||` translation deliberately preserves the original
  `RIGHT('000000' || ...)` padding, including its behaviour above 999999, rather than switching to
  `LPAD`, which truncates from the other end.
- **Integer literals and integer bind values against boolean columns.** PostgreSQL raises
  `DatatypeMismatch`; SQL Server's `BIT` accepted `1`/`0` silently. This class was the single
  largest source of failures in the first full regression run.
- **The T-SQL multi-table `DELETE alias FROM ... JOIN` form**, used 28 times. Twelve of those are in
  `backend/tooling/smoke_data/cleanup.py`, which the Part 1 handoff explicitly predicted would need
  no conversion. That prediction was wrong: the harness's SQL is dialect-specific, just not in any
  of the four scanned patterns.
- **`JSON_VALUE`**, one occurrence in test cleanup.

Two further failures surfaced only by running the suite, both `AmbiguousParameter` on the revision
status update - the same class Part 1 hit in the seed inserts. A parameter used both as a bare
assignment and in a comparison is deduced as `text` in one place and `character varying` in the
other; and a bare parameter under `IS NULL` carries no type information at all. Both now carry an
explicit `CAST`, with a comment at the site explaining why.

### Case-sensitivity audit

SQL Server's default collation compared case-insensitively; PostgreSQL does not. The audit found
that the values which matter are already normalized at the service layer before they reach the
database, so the change is safe:

| Value | Normalization | Verdict |
| --- | --- | --- |
| PAN, GSTIN | `_clean_code()` upper-cases | Safe |
| Email | lower-cased | Safe |
| Status codes (lead, opportunity, offer, work order) | `.strip().upper()` | Safe |
| Offer mode/type, qualification source, party type | `.strip().lower()` | Safe |
| Currency | `.strip().upper()`, default INR | Safe |
| T&C business line / category | `.upper().replace(" ", "_")` | Safe |
| T&C search | already `LOWER(col) LIKE lower(:param)` | Safe, unchanged |
| Public IDs, `CO-`/`WO-` references | generated, round-tripped verbatim | Safe |
| Username (login) | none at the service layer; matched case-insensitively in SQL | Preserved, see below |

#### Username login behaviour is preserved, not changed

Under SQL Server's default collation, `SALES1` matched the stored `sales1` at login. PostgreSQL
compares case-sensitively, so preserving that behaviour required making the rule explicit rather
than relying on a collation default. TE-2B therefore keeps case-insensitive login rather than
silently tightening authentication as a migration side effect:

- `get_user_with_roles_by_username` matches on `lower(u.username) = lower(CAST(:username AS VARCHAR))`.
- The stored username is returned unchanged, so API responses and the JWT subject always carry the
  canonical form regardless of the case submitted.
- Uniqueness is enforced on the same basis by a PostgreSQL unique expression index,
  `ux_app_user_username_lower` on `lower(username)`, which replaces the former plain
  `uq_app_user_username` constraint in revision `20260629_0001`.

The uniqueness change is not optional detail. Case-insensitive matching without matching uniqueness
would allow `sales1` and `SALES1` to coexist and make the login lookup ambiguous, so the two must
move together. The expression index subsumes plain username uniqueness: if `lower(username)` is
unique, the raw value necessarily is too. `citext` was deliberately not used, because it would add
an extension dependency for a single column, and no dual-dialect layer was introduced.

Because the SQL Server chain was never released, revision `20260629_0001` was amended in place
rather than adding a new revision, consistent with the ADR-028 migration-chain treatment. Revision
IDs, `down_revision` edges and the single linear head are unchanged.

> **Existing PostgreSQL volumes must be rebuilt.** Alembic records applied revisions by id and will
> not re-run one it has already recorded, so a PostgreSQL volume created before this amendment
> keeps the old `uq_app_user_username` constraint and never receives the new index. Rebuild any such
> local volume from an empty database: `docker compose down` (never `-v`), then
> `docker volume rm pbl-crm-hiring_postgres-data`, then `docker compose up -d`. This is acceptable
> only because the PostgreSQL chain is **unreleased** - no deployed database was ever created from
> it. **Never apply this to a production database**; once any environment is released from this
> chain, an equivalent change requires its own new forward revision. The command above does not
> touch `pbl-crm-hiring_mssql-data`, which is kept through TE-2C.

Two tests pin the behaviour: one proves `SALES1`, `Sales1` and `sAlEs1` all authenticate as the
stored `sales1` and that the issued token identifies the canonical user; the other proves the
database rejects a case-only duplicate username.

The only measurable schema effect is that unique constraints drop from 28 to 27, because one
`UNIQUE` constraint became a unique expression index. Total index count is unchanged at 151.

### New regression cover

`backend/tests/test_postgresql_dialect_regression.py` (15 tests) pins the conversion itself:
LIMIT/OFFSET paging returning disjoint ordered pages, `LIMIT {n}` on the events feed, single-row
lookups returning the requested record, flag columns being real booleans, boolean insert-default
plus `IS TRUE` filtering, UTC session and UTC-aligned `created_at`, `COALESCE(MAX(...), 0)` over an
empty set, business-reference padding, service-layer case normalization, case-insensitive login
returning the canonical username, the token identifying the canonical user, database rejection of a
case-only duplicate username, and two static guards that fail if T-SQL or an integer-versus-boolean
comparison is reintroduced into `backend/app` or `backend/tooling`.

### E2E audit-event hygiene

The Playwright suite authenticates through the real `/login` form, so each spec writes genuine
`UserLoginSucceeded` rows that the TE-1 manifest cleanup cannot know about - they belong to
`app_user`, not to a seeded record. `backend/tooling/smoke_data/audit_events.py` removes only the
login events one run produced, and `scripts/run-e2e.ps1` calls it from its existing `finally` block
so it runs whether the suite passes or fails.

Three conditions must all hold before a row is deleted: id strictly above a boundary captured
before the run; `event_name` in `UserLoginSucceeded`/`UserLoginFailed` with
`source_module = 'identity'`; and payload username on the E2E actor allowlist, passed explicitly at
the call site.

Two properties make this safe rather than merely narrow:

- **Boundary capture is mandatory and happens before seeding.** A failed or non-numeric capture
  aborts the run before any records exist, so the suite can never create login events it has no way
  to clean up. There is no warn-and-continue path.
- **Drift fails loudly.** The allowlist is hand-maintained, deliberately not derived by parsing spec
  source, because parsing would silently widen deletion scope whenever a spec changed. Instead,
  after the allowlisted deletion any identity login event still above the boundary is reported and
  sets a non-zero exit - never deleted, since an unrecognised actor may be a real user. A future
  spec using a seed user missing from the allowlist therefore breaks the run visibly.

`backend/tests/test_smoke_data_audit_events.py` (20 tests) covers the deletion scope, the
preservation rules, the residual reporting and the argument validation.

### Test-run event hygiene

`backend/tests/conftest.py` adds a session-scoped autouse fixture that snapshots the maximum
`business_event` id before any test runs and, in its finalizer, deletes only rows above that
boundary. Pre-existing events are never touched.

This closes a real accumulation problem rather than a cosmetic one: the module test files clean up
their own business records but not every event those records emitted, so repeated runs grew
`business_event` without limit - the working database had reached 2,448 rows before this fixture
existed. Cleanup happens at session teardown rather than per test because several tests assert on
events emitted earlier in the same test, so events must stay visible for the whole run.
`business_event` has no foreign key to any business table, so deleting by id range is FK-safe.

### Generated skeleton

`init-skeleton.ps1` now generates a PostgreSQL 17 Compose service with `pg_isready`, UTC, a
`postgres-data` volume and `service_healthy` dependency; a `POSTGRES_*` plus `DATABASE_URL`
`.env.example`; a `psycopg[binary]` backend image; and a PostgreSQL stack line in the generated
README. The hard-coded `$Root`, safe re-run behaviour and all unrelated generated content are
preserved. Generated `container_name` entries were dropped to match the real Compose file.

A pre-existing defect was fixed while doing this: the generator used `\${VAR}` inside a PowerShell
double-quoted here-string to try to emit a literal Compose variable. Backslash is not an escape
character there, so PowerShell interpolated the variable and emitted a bare `\`. The original
`\${MSSQL_SA_PASSWORD}` line had the same flaw. The correct backtick escape is now used, verified
by generating into a temporary directory and confirming `${POSTGRES_DB}` survives into the output.

## Explicitly out of scope

Part 1 changed no active repository, service, route or schema file other than removing
`func.sysutcdatetime()` from the two model files that used it, and deliberately did not run the
backend regression suite, because the active repository SQL was still T-SQL and belonged to Part 2.

Part 2 changed no business rule, route contract, schema or migration: the Alembic chain is exactly
as Part 1 left it, still 28 revisions ending at head `20260713_0029`.

TE-2CI (GitHub Actions) and TE-2C (migrated-foundation verification) remain out of scope and not
started. Nothing in TE-2B constitutes production readiness.

## Retained SQL Server volume

The old `pbl-crm-hiring_mssql-data` volume is preserved untouched and remains undeclared in
`docker-compose.yml`, so Compose cannot delete it. It was confirmed intact after all Part 2
testing, with its original `2026-06-30T09:34:31Z` creation timestamp.

**Retention decision: preserve `pbl-crm-hiring_mssql-data` through TE-2C. Delete it only after
TE-2C acceptance and an explicit project-owner instruction.** TE-2B does not delete it.
