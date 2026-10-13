# TE-2B Acceptance - PostgreSQL Migration

Technical-enablement work package, not a numbered CRM business slice.

**Status: TE-2B independently reviewed and accepted on 14 August 2026; committed and integrated on
`main` as commit `75fd4fc`.**

TE-2B Part 1 was independently reviewed and accepted as the intermediate checkpoint. Part 2 and its
correction passes are recorded below. The independent review accepted the combined package on
14 August 2026.

## Part 1 - automated checks performed

All Part 1 verification ran in an isolated Compose project (`pbl-te2b-part1`) with non-production
test credentials supplied through a scratchpad env file that was never written into the
repository. The normal project was never torn down and the old SQL Server volume was never
touched.

| # | Check | Command | Result |
| --- | --- | --- | --- |
| 1 | Compose config valid | `docker compose -p pbl-te2b-part1 --env-file <test.env> config` | Pass |
| 2 | Backend image builds from working tree | `docker compose -p pbl-te2b-part1 --env-file <test.env> build backend` | Pass |
| 3 | Isolated PostgreSQL starts | `docker compose -p pbl-te2b-part1 --env-file <test.env> up -d db` | Pass |
| 4 | Health check passes | `docker inspect -f '{{.State.Health.Status}}' pbl-te2b-part1-db-1` | `healthy` |
| 5 | Exactly one Alembic head | `alembic heads` | `20260713_0029 (head)` |
| 6 | Single linear chain, 28 revisions | `alembic history` | Pass, no branches |
| 7 | Database genuinely empty before upgrade | inspection script | 0 tables in `public` |
| 8 | Empty-database upgrade | `alembic upgrade head` | Pass, 28 revisions applied |
| 9 | Head recorded | `alembic current` | `20260713_0029 (head)` |
| 10 | Schema/constraint/index/seed inspection | inspection script (30 assertions) | All pass |
| 11 | Connection + foundation-table helpers | `verify_database_connection()`, `get_foundation_table_status()` | Pass |
| 12 | Downgrade to base | `alembic downgrade base` | Pass, only `alembic_version` remains |
| 13 | Re-upgrade to head | `alembic upgrade head` | Pass, schema re-verified identical |
| 14 | URL normalization / dialect rejection | inspection script (10 assertions) | All pass |
| 15 | FastAPI platform/database smoke | TestClient on 3 endpoints | 200, no password leakage |
| 16 | Isolated project and test volume removed | `docker compose -p pbl-te2b-part1 down -v` | Pass |
| 17 | Old SQL Server volume intact | `docker volume inspect pbl-crm-hiring_mssql-data` | Present, original creation timestamp |

Runtime observed: PostgreSQL 17.10, session `TimeZone` = `UTC`, dialect `postgresql+psycopg`.

### What check 10 asserted

- 28 tables, exactly the expected set, no extras.
- `alembic_version` = `20260713_0029` only.
- 6 roles / 6 users / 6 user-role assignments; all `is_active` real booleans; pbkdf2 hashes intact.
- 41 workflow statuses: business_party 10, commercial_offer 8, lead 11, opportunity 8,
  work_order 4. None inactive. The guarded triage insert preserved its public ID, display name and
  sort order.
- 15 T&C clauses, HIRING 7 / TRANSPORTATION 8. `HIRE-TC-007`'s mixed true/false flag combination
  preserved exactly, proving the BIT-to-boolean conversion did not flatten values.
- Every business table has a primary key.
- 34 named foreign keys, including the Slice 6O.1 self-referencing
  `fk_crm_commercial_offer_base_offer` (`base_offer_id` -> `crm_commercial_offer.id`).
- 28 unique constraints, 28 check constraints, 151 indexes **as measured during Part 1**. The
  TE-2B-C1 correction pass replaced the plain `uq_app_user_username` constraint with the
  `ux_app_user_username_lower` unique expression index, so the current figures are **27 unique
  constraints**, 28 check constraints and **151 indexes** (the total is unchanged, because a
  constraint-backed index was replaced by an expression index). See the Part 2 automated-checks
  table for the re-measured values.
- All 7 filtered/partial unique indexes present and unique.
- Flag columns are real PostgreSQL `boolean`; no BIT leftovers.
- `created_at` defaults render `now()`; no `SYSUTCDATETIME` survives.
- Live enforcement: duplicate workflow status rejected; invalid T&C business line rejected.

### Defect found and fixed during verification

`AmbiguousParameter` on the ported seed inserts. In
`INSERT INTO t (...) SELECT :a, :b ... WHERE NOT EXISTS (... WHERE col = :b)`, PostgreSQL deduces
`text` for the bare SELECT-list occurrence of `:b` and `character varying` for the comparison, and
rejects the statement. Fixed with an explicit `CAST(... AS VARCHAR)` on the affected parameters
(`:module`, `:status_code` in the five workflow-status seeds; `:clause_id` in the T&C seed), with a
comment at each site explaining why.

The failure itself produced useful evidence: the entire upgrade rolled back to a completely empty
database with no partial schema and no `alembic_version` row, confirming PostgreSQL transactional
DDL and validating the decision to drop the SQL Server idempotency workarounds.

## Part 1 - static checks

| Check | Result |
| --- | --- |
| Python compiles for every changed file | Pass |
| `git diff --check` (whitespace/conflict markers) | Clean |
| Only allowed files changed | Confirmed |
| Zero staged files | Confirmed |
| Untracked files are exactly the expected new TE-2B package files | Confirmed; enumerated in the Part 2 repository-state section below. The earlier "zero untracked files" wording was inaccurate: this package necessarily adds new files, which are untracked until commit. |
| Markdown fence parity in changed docs | Balanced |
| Prohibited SQL Server tokens in Part 1 scope | Zero |
| Revision IDs and `down_revision` edges unchanged | Confirmed, all 28 |
| No business/API/permission/event behavior change intended | Confirmed |

## Part 1 - not performed, and why

- **Full backend regression (`pytest`).** Deliberately not run. Active repository SQL is still
  T-SQL and belongs to Part 2; the suite cannot pass until that conversion lands. Running it now
  would produce failures that say nothing about Part 1's correctness.
- **Frontend build/tests, Playwright.** No frontend or E2E file changed in Part 1.
- **Docker clean start of the full stack, manual happy/permission paths.** These require the
  Part 2 application-layer conversion to be meaningful.
- **Data migration verification.** Out of scope by ADR-028; there is no row-level migration.

The FastAPI smoke check in row 15 proves only that the platform/database endpoints answer on
PostgreSQL. It is **not** evidence of full application compatibility.

## Part 2 - completed

- [x] Convert `SELECT TOP n` / `SELECT TOP (:limit)` to `LIMIT`.
- [x] Convert `OFFSET n ROWS FETCH NEXT n ROWS ONLY` to `LIMIT ... OFFSET ...`. The existing
      `safe_limit`/`safe_offset` clamping is unchanged; no raw interpolation was reintroduced.
- [x] Convert `SYSUTCDATETIME()` to `CURRENT_TIMESTAMP`.
- [x] Convert `ISNULL(x, 0)` to `COALESCE(x, 0)`.
- [x] All eleven files named in the Part 1 handoff converted.
- [x] Four further construct families found by repository-wide audit and converted: T-SQL `+`
      string concatenation in the `CO-`/`WO-` reference generators; integer literals and integer
      bind values against boolean columns; the T-SQL multi-table `DELETE alias FROM ... JOIN` form
      (28 sites, including 12 in the smoke-data harness the handoff predicted needed no change);
      and `JSON_VALUE`.
- [x] Two `AmbiguousParameter` defects found by the suite and fixed with explicit casts.
- [x] Case-sensitivity audit completed. Every business-meaningful value is already normalized at
      the service layer. Case-insensitive username login is **preserved**, not changed: the login
      lookup matches on `lower(username)`, responses and tokens carry the stored canonical
      username, and matching uniqueness is enforced by the `ux_app_user_username_lower` unique
      expression index. Pinned by three tests.
- [x] TE-1 smoke-data harness exercised on PostgreSQL: seed, status and cleanup.
- [x] Full backend regression passes.
- [x] Frontend typecheck, tests and production build pass.
- [x] Playwright regression passes with `retries: 0` unchanged.
- [x] Docker clean start on PostgreSQL from an empty volume.
- [x] Manual happy path, permission path, validation path, paging path, boolean path and
      timestamp/event path recorded, plus an exploratory browser smoke check.
- [x] Remaining SQL Server references in current (non-historical) documentation reconciled.
- [x] Decision recorded on when the preserved `mssql-data` volume may be deleted.
- [x] Continuity completion note written.
- [x] **Independent review of the combined Part 1 + Part 2 diff.** Accepted on 14 August 2026 after
      correction review and independent focused verification.

## Part 2 - automated checks performed

The old SQL Server project containers were removed with `docker compose down` (never `-v`), leaving
their volume intact. The PostgreSQL stack then started from a genuinely new, empty `postgres-data`
volume. Non-production credentials were supplied through a scratchpad env file and a scratchpad
Compose override outside the repository; the repository's real `.env` was never read, edited or
committed, and no password appears in any log or document.

| # | Check | Command | Result |
| --- | --- | --- | --- |
| 1 | Compose config valid with override | `docker compose -f docker-compose.yml -f <override> --env-file <test.env> config` | Pass |
| 2 | Backend image builds from working tree | `docker compose ... build backend` | Pass |
| 3 | PostgreSQL starts from an empty volume | `docker compose ... up -d db` | Pass, new `postgres-data` volume created |
| 4 | Health check | `docker inspect -f '{{.State.Health.Status}}' pbl-crm-hiring-db-1` | `healthy` |
| 5 | Database genuinely empty before upgrade | `SELECT count(*) ... information_schema.tables` | `0` |
| 6 | Migrations apply from empty on backend start | container startup log | Pass, all 28 revisions |
| 7 | Head recorded | `alembic heads` / `alembic current` | `20260713_0029 (head)` both |
| 8 | Schema shape | table / partial-index / boolean-column counts | 28 tables, 7 partial unique indexes, 25 boolean columns |
| 9 | Seed data | row counts | 6 users, 6 roles, 41 workflow statuses, 15 T&C clauses |
| 10 | Server version and session time zone | `SHOW server_version` / `SHOW TimeZone` | 17.10, `UTC` |
| 11 | Platform endpoints | `/api/health`, `/api/platform/config-summary`, `/api/platform/db-health` | 200; dialect `postgresql+psycopg`; no password leakage |
| 12 | Full backend regression | `docker compose exec backend pytest` | **231 passed**, 0 failed |
| 13 | Frontend typecheck | `docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run typecheck` | Pass |
| 14 | Frontend tests | same form, `npm test` | 54 passed (1 file) |
| 15 | Frontend production build | same form, `npm run build` | Pass |
| 16 | Frontend rebuilt and restarted from current source | `docker compose up -d --build frontend` | Pass |
| 17 | Smoke-data harness seed | `.\scripts\smoke-data.ps1 seed -Scenario core-regression-bundle` | Pass, run `te1-1f770070`, references `CO-001438` / `WO-000394` |
| 18 | Smoke-data status | `.\scripts\smoke-data.ps1 status -RunId ...` | All anchor records present |
| 19 | Smoke-data cleanup | `.\scripts\smoke-data.ps1 cleanup -RunId ...` | Pass, zero rows left for that run |
| 20 | Playwright regression | `.\scripts\run-e2e.ps1` | **12 passed, 9 skipped** (`@demo-preflight` is `--grep`-gated), 0 failed; all three seeded runs cleaned up |
| 21 | Playwright retries unchanged | `e2e/playwright.config.ts` | `retries: 0`, file unmodified |
| 22 | Generated skeleton verification | patched copy in a temp directory | README/env/Compose/Dockerfile all PostgreSQL; `docker compose config` valid; generated backend image builds; zero SQL Server content; temp directory and image removed |
| 23 | Old SQL Server volume after all testing | `docker volume inspect pbl-crm-hiring_mssql-data` | Present, original `2026-06-30T09:34:31Z` timestamp |

Backend regression detail: 218 pre-existing tests plus 13 new in
`tests/test_postgresql_dialect_regression.py`.

## Part 2 - static checks

| Check | Result |
| --- | --- |
| `SELECT TOP`, `FETCH NEXT`, `OFFSET ... ROWS`, `SYSUTCDATETIME`, `GETDATE`/`GETUTCDATE`, `ISNULL(`, `JSON_VALUE(`, `SCOPE_IDENTITY`, `NEWID()`, `dbo.`, T-SQL `DELETE alias FROM` in `backend/app`, `backend/tests`, `backend/tooling` | Zero |
| Integer compared or assigned to a boolean column | Zero |
| T-SQL `+` string concatenation in SQL | Zero |
| Remaining "SQL Server" text in backend code | Only intentional: the dialect-rejection comment in `core/database.py` and the migration descriptions in the new dialect regression test |
| `git diff --check` | Clean (only pre-existing CRLF advisories) |
| Conflict markers | None |
| Alembic chain | 28 revisions, single linear head `20260713_0029`, all revision IDs and `down_revision` edges unchanged from Part 1 |
| Frozen contracts | `accepted-offer-to-work-order-handoff-contract.md` and the Slice 6O.1 related-offer contract unchanged |
| Source/reference extracts | Unchanged |
| Zero staged files | Confirmed |

## Part 2 - manual checks

Backend base `http://localhost:8000`, frontend `http://localhost:3000`.

| # | Check | User / role | Result |
| --- | --- | --- | --- |
| 1 | Happy path: create Account | `sales1` / SALES_USER | 201; PAN normalized `abcde9876z` -> `ABCDE9876Z`; `is_strategic_account` real boolean `false`; `AccountCreated` event returned |
| 2 | Backend-enforced permission denial | `finance1` / FINANCE_USER | `POST /api/accounts` -> **403**; `GET /api/accounts` -> 200 |
| 3 | Validation rejection | `sales1` | Invalid PAN -> "PAN must be a valid 10-character Indian PAN if provided."; missing `account_name` -> 422 |
| 4 | Paging path converted from OFFSET/FETCH | `sales1` | `limit=2&offset=0/2/4` return correctly sized, disjoint, correctly ordered pages |
| 5 | Boolean-filtered path | `sales1` | T&C `active=true` 15, `applies_to_header=true` 10, `applies_to_line=true` 10; contact created with `is_active: true` / `is_primary: true` and listed by the `IS TRUE` filter |
| 6 | Timestamp + business event on update | `sales1`, `admin1` | Classification update flipped `is_strategic_account` to `true`, advanced `updated_at`, emitted `AccountClassificationUpdated`; the filtered `/api/events/recent` route returned both events for the record |
| 7 | Exploratory browser smoke check | `sales1`, `readonly1` | Dashboard, Accounts list, Account detail, T&C library all render; booleans display as Yes/No; `HIRE-TC-003` shows mixed Header No / Line Yes, confirming boolean values were not flattened; read-only role sees data with no mutation controls and an explicit "your current role cannot update it" message |

All manual-check records were removed afterwards.

### Test-run residue: measured, not asserted

An earlier draft of this checklist claimed the database was "left holding seed data only". That
claim was not supported by a measurement at the time and has been replaced with the actual figures.

Two distinct sources of residue were found and handled differently:

1. **Business records left by pytest runs that failed mid-test** during the Part 2 debugging cycle.
   These were measured and removed: 144 `TE1-SMOKE`-tagged accounts across roughly 30 harness run
   ids, plus 64 accounts, 75 leads, 93 opportunities, 93 commercial offers and 6 work orders from
   failed module-test runs. A subsequent **passing** run was then measured to confirm it leaks no
   business records (`business_party` 64 before -> 64 after), establishing that the leakage came
   from failed runs, not from normal operation.
2. **`business_event` rows accumulating across every run**, including passing ones. This was a real
   ongoing defect, not debugging residue: the module test files clean up their business records but
   not every event those records emitted. The working database had reached **2,448** rows. Fixed by
   the session-scoped boundary fixture in `backend/tests/conftest.py` (TE-2B-C1).
3. **`document_metadata` accumulating at 1 row per run**, and **login audit events accumulating per
   E2E run**. Both fixed by TE-2B-C2; see its verification section for measured evidence.

No residue claim in this checklist is asserted without a measurement. The database used for the
TE-2B-C2 verification was rebuilt from an empty volume and then deliberately seeded with
pre-existing rows, so every "unchanged" claim below is a comparison against known contents rather
than an assumption of emptiness.

## Part 2 - repository state at handoff

- Zero staged files.
- Exactly four untracked files, all expected new TE-2B package files - one new test module and
  three package documents:
  - `backend/tests/test_postgresql_dialect_regression.py` (new test module)
  - `docs/agent/technical-enablement/TE_2B_POSTGRESQL_MIGRATION.md` (package record)
  - `docs/agent/acceptance/te-2b-postgresql-migration-acceptance.md` (this file)
  - `docs/continuity/TE_2B_POSTGRESQL_MIGRATION_COMPLETION.md` (continuity note)
- No generated Playwright artifacts, smoke-data run manifests, scratch env files or temporary
  scripts are tracked or untracked in the repository; all validation scratch material lived outside
  it and the generated artifacts remain gitignored.
- No commit, merge, rebase, branch switch or push was performed.

## Part 2 - defects found and fixed

1. **Integer literals and integer binds against boolean columns.** `DatatypeMismatch` on
   PostgreSQL. Largest single failure source in the first full run (130 failures).
2. **T-SQL multi-table `DELETE alias FROM ... JOIN`**, 28 sites, including 12 in
   `backend/tooling/smoke_data/cleanup.py` that the Part 1 handoff predicted needed no conversion.
3. **T-SQL `+` string concatenation** in the `CO-`/`WO-` business-reference generators.
4. **`JSON_VALUE`** in a test-cleanup query.
5. **Two `AmbiguousParameter` defects** on the revision status update: a parameter used both as a
   bare assignment and in a comparison, and a bare parameter under `IS NULL`. Both fixed with
   explicit casts and an explanatory comment.
6. **Pre-existing `init-skeleton.ps1` escaping defect.** `\${VAR}` inside a PowerShell
   double-quoted here-string does not escape; PowerShell interpolated the variable and emitted a
   bare `\`. The original `\${MSSQL_SA_PASSWORD}` line had the same flaw. Fixed with the correct
   backtick escape and verified by generating into a temporary directory.

## Part 2 - observations for the reviewer, not fixed here

- ~~**`document_metadata` accumulates at 1 row per run.**~~ **RESOLVED by TE-2B-C2.**
  `tests/test_documents.py` now deletes its own row from a `finally` block, scoped to the
  per-run generated `linked_record_public_id`. Verified over two consecutive runs and one
  deliberately failing run: count and ids identical before and after each.
- ~~**Playwright login events are outside the pytest fixture.**~~ **RESOLVED by TE-2B-C2.**
  `scripts/run-e2e.ps1` now captures a `business_event` boundary before Playwright starts and, in
  its existing `finally` cleanup path, deletes only login events above that boundary for the named
  E2E actors. Verified over two consecutive runs: `business_event` count, max id and full id list
  identical before and after each.
- **Naive-timestamp display.** The API returns naive UTC ISO strings, exactly as it did on SQL
  Server. In a browser whose local time zone is not UTC, `new Date(<naive string>)` is interpreted
  as local time before any Asia/Kolkata formatting. This behaviour is byte-for-byte unchanged by
  TE-2B - both `SYSUTCDATETIME()` and `CURRENT_TIMESTAMP` on a UTC session produce the same naive
  UTC value and the same serialization - so it is pre-existing UI carry-forward, not a migration
  regression. Flagged rather than fixed, because changing it would alter API/UI behaviour outside
  this package's scope.
- **`init-skeleton.ps1` trailing hint** still prints `cd <your checkout>` regardless of
  `$Root`. Pre-existing and consistent with the hard-coded `$Root` limitation the work package
  required be preserved; left alone.

## TE-2B-C1 - correction pass

A bounded correction pass applied after the Part 2 handoff. It preserves authentication behaviour,
fixes test-run event accumulation, and reconciles records that overstated or misstated the position.

### 1. Case-insensitive login preserved

The Part 2 handoff recorded case-sensitive login as an accepted behaviour change. That has been
reversed: the pre-migration behaviour is preserved instead.

| Change | Detail |
| --- | --- |
| Login lookup | `lower(u.username) = lower(CAST(:username AS VARCHAR))` in `identity/repository.py` |
| Canonical identity | The stored username is returned unchanged, so responses and the JWT subject carry the canonical form whatever case was submitted |
| Uniqueness | `uq_app_user_username` replaced by unique expression index `ux_app_user_username_lower` on `lower(username)` in revision `20260629_0001` |
| Revision strategy | Revision `20260629_0001` amended in place, not a new revision, per the ADR-028 unreleased-chain treatment. Revision IDs, `down_revision` edges and the single head are unchanged |
| Not used | `citext`, and no dual-dialect layer |
| Reconciled | `identity/models.py` (`__table_args__` expression index, `unique=True` removed from the column), the `20260629_0002` seed lookups, and `tooling/smoke_data/actors.py` |

Matching uniqueness is not incidental: case-insensitive matching without it would let `sales1` and
`SALES1` coexist and make the login lookup ambiguous.

### 2. `business_event` accumulation fixed

`backend/tests/conftest.py` gains a session-scoped autouse fixture that snapshots the maximum
`business_event` id before any test runs and deletes only rows above that boundary in its
finalizer. Events stay visible for the whole session so existing event assertions still pass, and
pre-existing rows are never touched. `business_event` has no foreign key to any business table, so
an id-range delete is FK-safe.

### 3. TE-2B-C1 verification

| # | Check | Command | Result |
| --- | --- | --- | --- |
| 1 | Old PostgreSQL volume removed by name (never `mssql-data`, never `down -v`) | `docker compose down` then `docker volume rm pbl-crm-hiring_postgres-data` | Pass |
| 2 | Database genuinely empty before upgrade | `SELECT count(*) ... information_schema.tables` | `0` |
| 3 | Fresh empty upgrade to head | backend startup migrations | Pass, all 28 revisions |
| 4 | One head, chain unchanged | `alembic heads` / `alembic current` / `alembic history` | `20260713_0029 (head)` both; 28 revisions |
| 5 | Unique expression index present | `\d app_user` | `"ux_app_user_username_lower" UNIQUE, btree (lower(username::text))` |
| 6 | Constraint counts re-measured | `pg_constraint` by `contype` | check 28, foreign key 34, primary key 28, **unique 27** (was 28) |
| 7 | Index/table/seed counts | `pg_indexes`, `information_schema` | **151 indexes** (unchanged), 7 partial unique indexes, 28 tables, 6 users / 6 roles / 41 workflow statuses / 15 T&C clauses |
| 8 | Focused auth + dialect tests | `pytest tests/test_auth.py tests/test_postgresql_dialect_regression.py` | **21 passed** |
| 9 | Full backend regression, serial | `docker compose exec -T backend pytest -q -p no:randomly` | **233 passed, 0 failed** |
| 10 | `business_event` before/after the full suite | direct `count(*)` / `MAX(id)` | **4 before, 4 after**; ids `37,38,39,40` identical; `max_id` 40 both |
| 11 | Finalizer runs on the failure path | temporary probe test that creates a real event then fails | `1 failed, 6 passed`; `business_event` **4 before, 4 after**. Probe file deleted and confirmed absent from `git status` |
| 12 | Playwright regression (authentication touched) | `.\scripts\run-e2e.ps1` | See result below |
| 13 | `git diff --check` | - | Clean |
| 14 | Static SQL/boolean scans | repository-wide | Zero T-SQL constructs, zero integer-versus-boolean comparisons |
| 15 | Old SQL Server volume | `docker volume inspect pbl-crm-hiring_mssql-data` | Present, original `2026-06-30T09:34:31Z` timestamp |

The four pre-existing `business_event` rows in checks 10 and 11 were created deliberately through
the real API before the run, so the fixture had genuine pre-existing data to preserve rather than
being trivially satisfied by an empty table.

### 4. Records reconciled

- Every claim that case-sensitive login is an accepted behaviour change removed from the migration
  document, this checklist, `AGENT_HANDOFF.md` and `NEXT_STEPS.md`.
- `NEXT_STEPS.md` corrected: the TE-2B completion note exists.
- Reviewer note corrected: the running stack is PostgreSQL, not SQL Server.
- The unsupported "seed data only" claim replaced with measured before/after residue figures.
- Part 1's schema-count evidence annotated with the re-measured unique-constraint figure.

TE-2B status is unchanged by this pass: **implementation and testing complete, awaiting independent
review**. The final independent-review checkbox remains unchecked.

## TE-2B-C2 - test-residue and operational-documentation correction

A second bounded correction pass. It resolves the two accumulation findings TE-2B-C1 reported but
left open, and corrects operational records. It changes no business behaviour, permission,
frontend application behaviour, frozen contract or source document.

### 1. `document_metadata` test accumulation - fixed

`backend/tests/test_documents.py` wraps its create/list assertions in `try/finally` and deletes its
own row in the finalizer, scoped to the `linked_record_public_id` it generates fresh per run. That
identity cannot collide with a pre-existing row, so the deletion is narrow by construction rather
than by convention. There is no unrestricted `document_metadata` deletion. The associated
`DocumentMetadataCreated` event is left to the existing conftest boundary fixture.

### 2. E2E login-event accumulation - fixed

`backend/tooling/smoke_data/audit_events.py` (new) provides `capture_business_event_boundary()` and
`delete_login_events_after()`. `scripts/run-e2e.ps1` captures the boundary and calls the cleanup
inside its existing `finally` block, so it runs whether the suite passes or fails. Three conditions
must all hold before a row is deleted:

1. `id` strictly above the pre-run boundary;
2. `event_name` in `UserLoginSucceeded` / `UserLoginFailed` and `source_module = 'identity'`;
3. payload username on the E2E actor allowlist (`admin1`, `sales1`, `readonly1`).

The helper refuses an empty actor list and refuses non-identifier actor values, both verified.
Values are bound with expanding `bindparam`, not interpolated. Cleanup failure is reported through
the script's exit status via the existing `$cleanupExitCode` path, which never masks a Playwright
failure. No production API route was added and no credentials are embedded.

TE-2B-C3 hardened two weaknesses in this first implementation; see its section below.

### 3. TE-2B-C2 verification

Run against the disposable local `pbl-crm-hiring_postgres-data` volume, rebuilt from empty for this
pass. `pbl-crm-hiring_mssql-data` was never removed or modified, and `docker compose down -v` was
never used - the PostgreSQL volume was removed by explicit name.

**Baseline deliberately seeded with pre-existing rows before any run**, so "unchanged" is a real
comparison: `business_event` 4 rows (ids 1,2,3,4); `document_metadata` 2 rows
(`da05e6fe-dabd-4593-87c2-f5014fe11119`, `ab238f74-714c-49c3-a744-413eb0aa8ed8`).

| # | Check | Result |
| --- | --- | --- |
| 1 | Focused case-insensitive login + duplicate-username + auth suite | **9 passed** |
| 2 | `test_documents.py` run 1 | 4 passed; documents **2 → 2**, ids identical |
| 3 | `test_documents.py` run 2 | 4 passed; documents **2 → 2**, ids identical |
| 4 | `test_documents.py` with an injected failing assertion | 1 failed / 3 passed; documents **2 → 2**, ids identical - the `finally` cleanup ran on the failure path |
| 5 | Full backend regression, serial | **233 passed, 0 failed** |
| 6 | `business_event` across the full suite | **4 → 4**, max_id 4 → 4, ids `[1,2,3,4]` identical |
| 7 | `document_metadata` across the full suite | **2 → 2**, ids identical |
| 8 | E2E run 1 | **12 passed, 9 skipped, 0 failed**; boundary 4640; 12 login events deleted; `business_event` **4 → 4**, ids `[1,2,3,4]`; exit 0 |
| 9 | E2E run 2 | **12 passed, 9 skipped, 0 failed**; boundary 4845; 12 login events deleted; `business_event` **4 → 4**, ids `[1,2,3,4]`; `document_metadata` **2 → 2**; seeded business records 0 → 0; exit 0 |
| 10 | Playwright `retries` | Still `0`; `e2e/playwright.config.ts` unmodified |
| 11 | Helper safety guards | Empty actor list rejected (exit 2); non-identifier actor value rejected (exit 2) |
| 12 | Alembic | `heads` and `current` both `20260713_0029 (head)`; 28 revisions |
| 13 | `git diff --check` | Clean |
| 14 | Frontend checks | Not run - no frontend source changed |
| 15 | Old SQL Server volume | `pbl-crm-hiring_mssql-data` present, original `2026-06-30T09:34:31Z` |

An ordinary successful backend run and an ordinary successful E2E run each leave `business_event`
and `document_metadata` exactly as they found them.

### 4. Records corrected

- Volume-rebuild warning added to the migration document, the completion note and `NEXT_STEPS.md`:
  a PostgreSQL volume created before the in-place amendment of `20260629_0001` must be rebuilt from
  empty, because Alembic will not re-run an already-recorded revision. Acceptable only because the
  chain is unreleased; explicitly never to be applied to a production database.
- `NEXT_STEPS.md`: PostgreSQL recorded as the active runtime. The active recommendations to use a
  SQL Server runtime path and to treat a PostgreSQL conversion as future work are withdrawn, while
  the Slice 6C.3 record is preserved as history with a supersession note.
- `mssql-data` retention through TE-2C restated in all three records.
- The `document_metadata` and Playwright login-event observations marked resolved.
- Residue claims replaced with measured before/after evidence.

TE-2B is **independently reviewed, accepted and integrated on `main` as commit `75fd4fc`**.
TE-2CI is the next technical-enablement package.

The following sentence is preserved as a record of the TE-2CI position **as it stood on
14 August 2026, when TE-2B was accepted**, and is not current status:

> TE-2CI.1 (repository implementation) is implemented and awaiting independent review, and
> TE-2CI.2 (hosted validation and branch protection) has not started.

**Reconciliation, 16 August 2026.** TE-2CI has moved on since: TE-2CI.1 was independently accepted
and integrated as `1b4d08c`, and TE-2CI.2 has begun — hosted runs have executed, two Compose
teardown defects were found and corrected, and required-check registration and branch protection
remain pending. This acceptance record is TE-2B's and is not maintained as a TE-2CI status source;
see `docs/agent/technical-enablement/TE_2CI_GITHUB_ACTIONS_VALIDATION_FOUNDATION.md` for the
current position.

## TE-2B-C3 - fail-loud E2E audit cleanup and focused safety tests

A third bounded correction pass. It hardens the TE-2B-C2 login-event cleanup against two ways it
could fail quietly, and adds automated cover for the helper. It changes no migration, application
business behaviour, permission, frontend source, frozen contract or source document, and does not
alter the PostgreSQL-volume rebuild rule.

### 1. Boundary capture is now mandatory

Previously the script warned and continued when `event-boundary` failed. That allowed Playwright to
create login events that could not then be cleaned safely, while the run could still exit 0.

Boundary capture now runs **before seeding** and is a hard prerequisite:

- a non-zero exit from `event-boundary` throws immediately, before any records exist, so there is
  nothing to clean up on that path;
- the captured value must match `^\d+$`, so an empty, non-numeric, negative or fractional value
  also aborts before seeding;
- there is no remaining "warn and continue" path, so Playwright cannot start without a valid
  numeric boundary.

### 2. Explicit allowlist plus drift detection

The actor list is still a narrow hand-maintained allowlist - deliberately **not** derived by parsing
TypeScript spec source, since parsing would silently widen deletion scope whenever a spec changed.
Two corrections:

- `scripts/run-e2e.ps1` now passes `--actors admin1,sales1,readonly1` explicitly at the call site
  rather than relying on the CLI default. The earlier claim in this checklist that actors were
  "explicitly passed" was inaccurate when written; this is what makes it true.
- `find_unlisted_login_events_after()` (new) runs after the allowlisted deletion and reports any
  identity login event still above the boundary. Those rows are **never deleted** - an unrecognised
  actor may be a real user - but they set CLI exit code 3, which `run-e2e.ps1` propagates through
  `$cleanupExitCode`. A future spec logging in as a seed user missing from the allowlist therefore
  fails the run loudly instead of leaking audit rows, while the fail-safe rule that unknown audit
  events are never removed is preserved. A login event whose payload carries no username is also
  reported rather than deleted, since it cannot be attributed.

### 3. Focused automated tests

`backend/tests/test_smoke_data_audit_events.py` (new, 20 tests) covers: both login event names
deleted for an allowlisted actor; pre-boundary rows preserved; non-login business events preserved;
`source_module` restricted to `identity`; unlisted-actor events preserved *and* reported as
residual; no false positives when every actor is listed; a login event with no payload username
preserved and reported; empty, blank, non-identifier, negative and non-integer arguments rejected;
and boundary capture returning a non-negative int that tracks new rows. Every test inserts probe
rows with generated identities and deletes them in a `finally` block, so the shared database is
unchanged even when an assertion fails.

### 4. TE-2B-C3 verification

Baseline held constant throughout: `business_event` 4 rows ids `[1,2,3,4]`; `document_metadata`
2 rows (`da05e6fe-dabd-4593-87c2-f5014fe11119`, `ab238f74-714c-49c3-a744-413eb0aa8ed8`).

| # | Check | Result |
| --- | --- | --- |
| 1 | Audit-event helper tests | **20 passed**; database identical afterwards |
| 2 | Focused auth tests | **9 passed** |
| 3 | `test_documents.py` run 1 | 4 passed; documents **2 → 2**, ids identical |
| 4 | `test_documents.py` run 2 | 4 passed; documents **2 → 2**, ids identical |
| 5 | Full backend regression, serial | **253 passed, 0 failed** (233 + 20 new) |
| 6 | Residue across the full suite | `business_event` **4 → 4** ids `[1,2,3,4]`; `document_metadata` **2 → 2**, ids identical |
| 7 | E2E run 1 | **12 passed, 9 skipped, 0 failed**; boundary 4; 12 login events deleted; exit **0**; both tables unchanged |
| 8 | E2E run 2 | **12 passed, 9 skipped, 0 failed**; boundary 4; 12 login events deleted; exit **0**; both tables unchanged; seeded business records 0 → 0 |
| 9 | Playwright `retries` | Still `0`; `e2e/playwright.config.ts` unmodified |
| 10 | Unlisted-actor probe (CLI, controlled) | Allowlisted `sales1` event deleted; unlisted `finance1` event **preserved** and reported as `id=4890 event_name=UserLoginSucceeded payload_username='finance1'`; CLI exit **3**. Probe row removed afterwards |
| 11 | Boundary-failure abort (dynamic, patched copy in a temp directory) | "Capturing business_event boundary before seeding..." printed, then threw; **"Seeding" never printed**, Playwright never started, exit non-zero, database unchanged. Probe copy deleted |
| 12 | Boundary numeric guard (logic) | `0`, `4`, `4640` accepted; empty, `abc`, `-1`, `1.5`, `null` rejected |
| 13 | Alembic | `heads` and `current` both `20260713_0029 (head)`; 28 revisions |
| 14 | `git diff --check` | Clean |
| 15 | Frontend checks | Not run - no frontend source changed |
| 16 | Old SQL Server volume | `pbl-crm-hiring_mssql-data` present, original `2026-06-30T09:34:31Z` |

An ordinary successful backend run and an ordinary successful E2E run each leave `business_event`
and `document_metadata` exactly as they found them.

TE-2B status is unchanged: **implementation and testing complete, awaiting independent review**.
The final independent-review checkbox remains unchecked and the current gate has not advanced.

## Reviewer notes

- Independent review reran the 20 focused audit-cleanup tests and a 33-test focused auth/document/
  audit set, with `business_event` and `document_metadata` IDs unchanged before and after.
- The work was committed under project-owner direction after acceptance and is integrated on
  `main` as commit `75fd4fc`.
- `mssql-data` is intentionally absent from the `volumes:` block in `docker-compose.yml`. That is
  not an oversight: leaving it undeclared removes it from Compose's management so
  `docker compose down -v` cannot delete it.
- The running local development stack is now the PostgreSQL project. The old SQL Server containers
  were removed with `docker compose down` (never `-v`) during Part 2, and their volume is intact.
- The frozen Slice 6D.1 handoff contract and the Slice 6O.1 related-offer contract were not
  touched.
