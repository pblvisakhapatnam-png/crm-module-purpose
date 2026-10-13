# TE-2C - Migrated-Foundation Verification (working evidence record)

## Status

**TE-2C's defined migrated-foundation verification evidence is now assembled: SATISFIED / PASS.**
The protected-integration negative path that every prior revision of this document correctly
recorded as outstanding has now been demonstrated with real hosted evidence (section 10). This is
**not** a final production-candidate, deployment-readiness, SLA, disaster-recovery, or
production-security certification — those remain **LATER-GATE**, per
`PRODUCTION_READINESS_GATES.md` and ADR-025, and are not claimed here. Final repository
integration of *this specific documentation revision* is a separate, still-open step — see
"Closure-update integration status" immediately below. This closure-documentation delta is
subject to bounded independent review and final protected-integration validation before
integration; repository commit history and PR #5 are authoritative for whether those subsequent
process steps have completed, not this sentence.

### Accepted commit chain (implementation + JWT-mask correction)

Both of the following were independently reviewed under the bounded H.1 methodology
(`docs/agent/architecture/BOUNDED_INDEPENDENT_REVIEW_METHOD.md`) and bound to their resulting
commits by a deterministic pre/post canonical-diff SHA-256 equality check
(`INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md` section D), not merely asserted.

**1. TE-2C implementation candidate** — the backup/restore and timing-baseline tooling package
described in passes 1-5 below:

```text
Base:                          60fd68373ea910e6ac00ba945437d68a3e859d36
Accepted canonical SHA-256:    FE5D48F298229DECC2FBC062517DAC805971236A899624EB2963355F82C9B1D8
Bound commit:                  689fc6b456c64dfa98c6e2e672bff8f5aff565d6
Commit subject:                Add TE-2C migrated-foundation verification tooling
Review result:                 ACCEPTED
Review-to-commit result:       pre/post canonical diff hashes identical
```

**2. JWT-mask correction** — a separate, later, incremental commit on the same branch. It did
**not** ship as part of commit `689fc6b` above; it was reviewed and bound independently, against
`689fc6b` as its own base:

```text
Incremental base:              689fc6b456c64dfa98c6e2e672bff8f5aff565d6
Accepted incremental SHA-256:  42B0C27BB46B7DA4F05111C6B98E253B3F0A32E09920A8DC6F003C80C5B77906
Bound commit:                  3d6ff2807917e6ca4b31fa91c338c92b0c1e1f13
Commit subject:                Mask ephemeral CI JWT secret
Review result:                 ACCEPTED
Review-to-commit result:       pre/post canonical diff hashes identical
```

Why the JWT-mask correction was needed, stated narrowly: the `backend-regression` CI job
generates an ephemeral JWT signing secret for that run only. The value is fictional and
runner-scoped, never a production credential — but the original implementation wrote it to
`$GITHUB_ENV` without first registering it for masking, so the raw generated value was visible in
later hosted step environment output. The corrected workflow registers the value with GitHub
Actions `::add-mask::` before exporting it to `$GITHUB_ENV`. No production credential, repository
secret, or other persistent credential was introduced by either the defect or the fix, and this
correction is not a general production secrets-management certification.

Branch `te-2c-migrated-foundation-verification` — at the accepted implementation/JWT-mask head
before this documentation delta, `3d6ff2807917e6ca4b31fa91c338c92b0c1e1f13` — was pushed to
`origin` and opened as **PR #5**. **Status update, 18 August 2026: PR #5 has since been merged.**
`main` now carries it as commit `7f5a05dca3ea93921e5a9f11a8c8dd0156c59c2f` ("Merge PR #5: TE-2C
migrated-foundation verification"), closing the "Closure-update integration status" steps
recorded immediately below exactly as they specify. The steps themselves are preserved as written
because they record what integration required, not merely a fact that has since changed; per that
section's own instruction, repository commit history is authoritative over any fixed sentence
here for whether they completed. See section 10a for the hosted validation evidence the
pre-closure-documentation head received.

### Closure-update integration status (historical record of what integration required; now satisfied)

This documentation-only revision (the one you are reading) records evidence that already exists
and has already been independently reviewed at the code/commit level, as described immediately
above. It does **not** by itself complete TE-2C's own integration requirements. Before this
revision may be integrated into `main`, it remains subject to, in full:

- independent review of this documentation-only delta;
- a fresh, hosted `Required validation` run on the exact PR head that includes this revision (run
  `32097159958` / #14 validated commit `3d6ff2807917e6ca4b31fa91c338c92b0c1e1f13`; it did **not**,
  and cannot, validate a later commit that did not yet exist when it ran — a documentation commit
  added after it creates a new PR head requiring its own fresh run, consistent with ADR-031's
  required-check semantics: the check must report on the exact commit proposed for merge);
- the branch remaining current with `main`;
- explicit project-owner integration approval;
- merge-commit-only integration, per the active repository ruleset (ADR-031).

**Pass 5 update (18 August 2026): third independent H.1 review correction, scoped to the timing
baseline's test-token helper only.** A third independent review of the pass-4 candidate returned
`CORRECTION_REQUIRED` against exactly two remaining points in
`backend/tooling/smoke_data/auth_tokens.py` and `scripts/te-2c-timing-baseline.ps1`. The
backup/restore corrections and the redirect correction from pass 4 were explicitly accepted and
were not touched further in this pass.

1. **P2 — `APP_ENV` was not actually required to be explicit.** `auth_tokens.py`'s guard read
   `get_settings().app_env`, whose own Pydantic field defaults to `"development"` when the
   variable is simply unset — so a genuinely missing `APP_ENV` passed the guard undetected,
   contradicting the stated "explicit environment" guarantee. Corrected to read
   `os.environ.get("APP_ENV")` directly: a missing variable is now refused outright, and a
   secondary consistency check refuses if the explicit process-environment value and the
   application's resolved `settings.app_env` disagree. `app.core.config.Settings` itself and real
   application authentication are both unchanged.
   *Reconciliation, 7 October 2026 (TB-1 TB1-204 part d):* `Settings` no longer defaults `app_env`;
   a missing or blank `APP_ENV` now stops the backend from starting. The tooling's own check is
   kept.
2. **P2 — the token boundary had no permanent regression coverage.** Added
   `backend/tests/test_smoke_data_auth_tokens.py`, 12 focused pytest tests, running as part of the
   existing backend regression suite (no new test framework). See section 12 below for what each
   proves.

**Documentation-precision correction (this pass, not a new finding):** every place that said or
implied "the token is never printed on any code path" is corrected to the precise guarantee:
`issue-test-token` intentionally writes the token to stdout as its interface; the timing script
captures that stdout and never displays/echoes it on any path; the helper itself writes no token
to stderr or diagnostic text. Corrected in `backend/tooling/smoke_data/auth_tokens.py`,
`scripts/te-2c-timing-baseline.ps1`, `scripts/README.md`, and this document (section 12 below).

**Pass 4 update (17 August 2026, same date as passes 1-3): second independent H.1 review
correction.** A second independent review of the pass-3 candidate returned `CORRECTION_REQUIRED`
against the same two scripts. Five further findings (one P1, four P2) were corrected; sections 11
and 12 below are again **fully rewritten**. **The pass-3 evidence text is superseded and removed**
— specifically, pass 3's claims of "certified source state at backup time" / "source confirmed
quiescent" (finding 2) and its container-cleanup/token-issuance descriptions (findings 1, 3, 4)
must not be read as current, since the underlying guarantees were incomplete or, in finding 2's
case, overstated relative to what the mechanism actually proves.

Findings corrected in this pass, in brief (full detail in sections 11-12):

1. **P1 — Docker cleanup verification still had false-success states.** `docker ps`/`docker exec`
   verification commands' own exit codes are now checked; a failed verification command is never
   treated as "absent" merely because its output happened to look empty. A shared
   `Resolve-AbsenceVerification` function makes this an explicit three-state contract (verified
   absent / verified present / could-not-verify), and the source temp-file check now uses a
   two-marker probe (`TE2C_PRESENT`/`TE2C_ABSENT`) rather than a bare `test -e` exit code.
2. **P2 — row-count equality did not prove source quiescence.** The claim is narrowed rather than
   technically strengthened: before/after per-table counts remain a *cardinality-drift guard*
   only, explicitly not proof of quiescence or byte-for-byte equivalence; restore verification is
   now described as structural/data-presence verification associated with a successful PostgreSQL
   consistent backup snapshot, not a "certified" state.
3. **P2 — the test-token helper was too broad.** `issue_test_bearer_token()` no longer takes a
   username parameter (only the fixed `readonly1` identity can ever receive a token), refuses to
   run unless `APP_ENV` is an explicit local development/test value, and issues short-lived
   (5-minute) tokens. The `actors.py` trust-boundary comparison pass 3 made is retracted as
   inaccurate.
4. **P2 — restore-target destructive ownership was name-only.** The disposable restore container
   now carries a fixed ownership label at creation; before force-removing anything with the fixed
   name, the script inspects that label and refuses (fails closed) if it is missing, rather than
   trusting the name alone.
5. **P2 — the loopback guarantee did not control redirects.** Every request (health probe,
   warm-up, measured) now uses `-MaximumRedirection 0`, so an unexpected 3xx fails rather than
   being followed.

**Pass 3 update (17 August 2026, same date as passes 1-2): independent H.1 review correction.**
An independent CI/scripts/tooling review of the pass-2 candidate (base `60fd683...`, branch
`te-2c-migrated-foundation-verification`) returned `CORRECTION_REQUIRED` against
`scripts/te-2c-backup-restore.ps1` and `scripts/te-2c-timing-baseline.ps1`, per
`docs/agent/architecture/BOUNDED_INDEPENDENT_REVIEW_METHOD.md`. Six findings (two P1, four P2)
were corrected; sections 11 and 12 below are **fully rewritten** to describe the corrected
mechanisms and carry fresh execution evidence. **The pass-2 evidence text describing the
pre-correction implementation is superseded and removed** — it must not be read as current proof
of anything, per the review's own instruction not to retain defective-implementation language as
current evidence. A short summary of what each finding was and how it was fixed is kept at the
start of each section as a historical correction note, since that is useful for a future reader
without restating superseded evidence as if it were still valid.

Findings corrected, in brief (full detail in sections 11-12):

1. **P1 — cleanup was not actually fail-closed.** Every removal (restore-target container, local
   dump file, source container's temp dump file) is now independently *verified* absent, not
   merely attempted; an unverified cleanup failure now makes the overall run fail.
2. **P1 — a non-zero `pg_restore` exit was wrongly tolerated as advisory.** Any non-zero exit is
   now an unconditional hard failure; `pg_restore` now runs with `--single-transaction
   --exit-on-error` alongside the existing `--no-owner --no-privileges`.
3. **P2 — the row-count comparison was not actually tied to backup-time source state.** The
   script now captures per-table row counts immediately before and after `pg_dump` and fails if
   they differ (source not quiescent), and compares per table rather than only an aggregate
   total.
4. **P2 — `-SampleCount 0` falsely passed the timing script.** Parameter validation now requires
   `-SampleCount >= 1` and `-WarmupCount >= 0`.
5. **P2 — the timing script's local/state boundary was not enforced.** `-BaseUrl` is now
   restricted to a loopback target, and authentication no longer creates any login audit event at
   all (a new, narrow `backend/tooling/smoke_data` addition issues a valid test bearer token
   directly, reusing the real login route's own identity-lookup and token-signing code without
   calling that route) — removing the earlier broad "delete every `readonly1` event above a
   boundary" concurrency risk entirely rather than narrowing it.
6. **P2 — the backup script's source boundary was not enforced.** The script now positively
   verifies, via Docker Compose labels, that `-SourceContainer` actually is the `pbl-crm-hiring`
   project's `db` service before touching it in any way, and uses a unique per-run temp dump path
   on the source container.

**Protected-integration negative-path evidence is now demonstrated** (section 10) — this is the
one substantive change from every prior revision recorded above, each of which correctly stated
it remained outstanding at the time it was written. That historical wording is preserved as
written in the dated pass blocks above; it was accurate when it was recorded. As of this
closure-update revision, TE-2C's migrated-foundation verification evidence is assembled and
recorded as PASS/SATISFIED — see the Status header at the top of this document and the "Final
classification" section near the end. This still does **not** declare final production-candidate
readiness.

TE-2C verifies the migrated technical foundation (PostgreSQL, React + Vite, GitHub Actions
validation, TE-1 tooling). **It is not the final production-candidate product tag** and this
record must not be cited as production or deployment readiness, per `PRODUCTION_READINESS_GATES.md`
and ADR-025.

- Baseline commit: `60fd68373ea910e6ac00ba945437d68a3e859d36` (`main`/`origin/main`, verified equal
  before branching).
- Branch: `te-2c-migrated-foundation-verification`, pushed to `origin` and open as PR #5 (not
  merged).
- Execution-evidence dates: passes 1-4 (sections 1-13 below) were executed 17 August 2026; pass 5
  was executed 18 August 2026; the JWT-mask correction, its independent review and commit
  binding, the controlled protected-integration negative-path probe (PR #4), the hosted
  validation of this branch's accepted implementation/JWT-mask head before this documentation
  delta (PR #5, run #14), and this closure-documentation revision itself all followed on
  18 August 2026.
- Author/mode: internal implementation-agent pass, per
  `docs/agent/architecture/INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md`. The implementation
  candidate (commit `689fc6b`) and the JWT-mask correction (commit `3d6ff28`) have each been
  independently reviewed, ACCEPTED, and bound to their resulting commits by an exact pre/post
  canonical-diff hash match — see "Accepted commit chain" above. Both commits are pushed to
  `origin` as part of open PR #5. This closure-documentation delta is itself subject to the same
  bounded independent review and review-to-commit binding discipline before it may be committed
  and integrated; repository commit history and PR #5 are authoritative for whether that has
  happened by the time this record is read.

## Purpose of this document

This is a working evidence record for TE-2C's Definition of Done, reconstructed from
`PRODUCTION_READINESS_GATES.md` and `NFR_BASELINE_AND_VERIFICATION.md`. It records, per DoD
requirement: what evidence already exists and is reused, what was freshly executed, what was a
genuine gap that has since been closed, what remains a deliberately unresolved production
parameter, and what remains explicitly out of TE-2C's scope (LATER-GATE). As of this
closure-update revision, the one requirement previously classified GAP for behavioral
protected-integration evidence has been closed (section 10); TE-2C's migrated-foundation
verification evidence is therefore assembled and PASS/SATISFIED. This document does not declare
final production-candidate readiness, which remains a separate, later gate — see "Final
classification" near the end of this document.

## Reconstructed TE-2C Definition of Done (authoritative source: `PRODUCTION_READINESS_GATES.md`)

> TE-2C verifies the technology migration and shared technical baseline. It is not the final
> production-candidate product tag. It must prove: all supported migrations apply from an empty
> confirmed production database; backend regression, frontend build/tests and E2E regression pass;
> Docker clean start and health checks pass; TE-2CI GitHub Actions required checks reproduce the
> documented validation path and are required for protected integration (TE-2C must independently
> verify the active ADR-031 ruleset, not treat its existence alone as satisfying this item);
> secrets/configuration, backup/restore evidence, logs/metrics and failure diagnostics meet the
> TE-2C NFR gate; a repeatable standard-interaction timing baseline and dependency-failure checks
> are recorded; obsolete Next.js and SQL Server assumptions are removed or explicitly documented;
> contract registry and architecture records match the repository; known residual risks and
> still-unset production parameters are recorded without claiming final production compliance.

The NFR gate in `NFR_BASELINE_AND_VERIFICATION.md` adds: CI executes the documented path;
representative standard interactions have a repeatable timing baseline; auth/authz, secret
handling, TLS deployment design and dependency-failure behaviour are reviewed; backup/restore
commands/runbook exist and one non-production restore is demonstrated where the environment is
available; logs/health/jobs/integration failures are diagnosable; unresolved parameters and
residual risk are recorded without claiming compliance.

## Classification legend used below

```text
PASS             fresh TE-2C evidence now exists (produced in this pass)
REUSED           prior evidence (TE-2B/TE-2CI/PR #3) is valid and cited, not re-executed
GAP              bounded implementation/evidence correction needed; not implemented in this pass
HUMAN-PARAMETER  a genuine PBL/production decision remains, and is not a TE-2C blocker
LATER-GATE       explicitly outside TE-2C scope (final production gate or later package)
```

This mirrors the preparation pass's A/B/C/D/E scheme (A→REUSED, B→PASS-after-execution, C→GAP,
D→HUMAN-PARAMETER, E→LATER-GATE).

## Known production parameters deliberately not invented in this pass

Per `NFR_BASELINE_AND_VERIFICATION.md` ("Required parameters before production deployment"), none
of the following are invented, assumed, or given a default value anywhere in this record: production
availability SLA / maintenance exclusions; RPO/RTO; normal/peak concurrency, branch/site and
data-volume profile; backup frequency, retention and restore-test frequency; maximum accepted age
of Plum HR employee/position data and controlled-import fallback timing; support response/resolution
targets and escalation matrix; data-category retention/disposal periods; mobile offline duration and
conflict policy. These are final-production-gate parameters, not TE-2C blockers, per that same
document's own TE-2C NFR gate wording.

---

## Execution log and evidence

### 1. Empty-database migration path — **PASS**

Executed against a throwaway PostgreSQL 17 container (`te2c-verify-db`) on the `pbl-crm-hiring_default`
network, isolated from the persistent dev database, then removed after the exercise. This is a
**fresh empty-database exercise**, not a reuse of the already-migrated persistent dev volume.

```text
docker run -d --name te2c-verify-db --network pbl-crm-hiring_default \
  -e POSTGRES_DB=te2c_verify -e POSTGRES_USER=te2c_ci \
  -e POSTGRES_PASSWORD=te2c-not-a-real-secret-placeholder -e TZ=UTC -e PGTZ=UTC postgres:17
```

```text
=== Confirm empty schema before upgrade ===
 count
-------
     0
(1 row)

=== Confirm exactly one Alembic head ===
20260713_0029 (head)

=== Upgrade empty DB to head ===
[... 28 revisions applied in order, 20260629_0001 -> ... -> 20260713_0029 ...]

=== Confirm current == head ===
20260713_0029 (head)

=== Table count and timezone after upgrade ===
 count = 28
 TimeZone = UTC
```

28 tables created (matches the schema list recorded in TE-2CI.1's acceptance record exactly).
Container removed afterward; the persistent dev `postgres-data`/`mssql-data` volumes were never
touched by this exercise.

### 2. Backend regression — **PASS**

```text
docker compose exec -T backend pytest -q
253 passed in 311.01s (0:05:11)
```

Matches the documented TE-2B-C3 baseline (253 passed) exactly. No test skipped, weakened or
deselected.

### 3. Frontend — **PASS**

```text
docker compose run --rm --no-deps -v "$(pwd)/frontend:/app" -v /app/node_modules frontend npm run typecheck
-> exit 0, no errors

docker compose run --rm --no-deps -v "$(pwd)/frontend:/app" -v /app/node_modules frontend npm test
-> Test Files 1 passed (1); Tests 54 passed (54); Duration 4.21s

docker compose run --rm --no-deps -v "$(pwd)/frontend:/app" -v /app/node_modules frontend npm run build
-> 69 modules transformed, built in 8.37s; pre-existing >500kB chunk-size advisory unchanged (non-blocking)
```

(Note: on this Windows/Git-Bash host, `MSYS_NO_PATHCONV=1` was required before the `docker compose
run` invocations, otherwise Git Bash mangles the `/app/node_modules` volume path into a Windows path
and Docker rejects it. This is a host-shell quirk, not a repository defect, and does not affect the
PowerShell-based commands documented in `AGENTS.md`.)

### 4. E2E / Docker — **PASS** (with an explicit scope note)

Executed via the documented entry point, full path (not `-SkipServiceStart`), against the current
source tree:

```text
.\scripts\run-e2e.ps1
```

Result:

```text
Building the current frontend image...        (cache-hit rebuild, current source)
Ensuring db/backend/frontend Compose services are up...
Container pbl-crm-hiring-frontend-1  Recreated
Waiting for backend health endpoint... OK
Waiting for frontend... OK
business_event boundary: 4
Seeded run id: te1-ebf2ad2e / te1-04e59fc8 / te1-2002f622

Running 21 tests using 1 worker
  12 passed, 9 skipped (demo-preflight suite, correctly not run in the default full pass)

Cleanup complete for run te1-ebf2ad2e: ... (all counts reconciled to zero net)
Cleanup complete for run te1-04e59fc8: ... (all counts reconciled to zero net)
Cleanup complete for run te1-2002f622: ... (all counts reconciled to zero net)
Deleted 12 login event(s) above id 4 for actor(s): admin1, sales1, readonly1.
E2E run complete: tests passed and cleanup succeeded.
EXIT_CODE=0, ELAPSED_SECONDS=81.4
```

Post-run residue check:

```text
docker ps -a  -> only pbl-crm-hiring-{frontend,backend,db}-1 remain; the one-off
                 pbl-crm-hiring-e2e-run-* container is gone (--rm auto-removal confirmed)
docker volume ls -> pbl-crm-hiring_{postgres-data,e2e-node-modules,mssql-data} present, as expected
docker network ls -> pbl-crm-hiring_default present, as expected
```

**Scope note — what this proves and what it does not.** This is a *warm* Compose exercise: it
rebuilds and recreates the `frontend` container and confirms health/Playwright/business-data
cleanup against the **existing, already-running** `db`/`backend` containers and their persistent
volumes, matching normal local-developer use per `AGENTS.md`. It is genuine, fresh evidence that
the current source (a) builds, (b) starts healthy, (c) passes the full Playwright suite, and (d)
cleans up seeded business data and login-audit events deterministically (all cleanup counts
reconciled to the exact seeded totals, confirmed above).

It is **not** a from-empty-volume, isolated-Compose-project "cold start", and it does **not**
exercise `scripts/ci-compose-cleanup.sh` (that script is deliberately fail-closed to
`GITHUB_ACTIONS=true` plus the exact `pbl-crm-hiring-ci-<run-id>` project-name shape, by design —
see its own header comment — so it correctly refuses to run against this local project, and was not
forced to run here). That specific claim — "an isolated Docker Compose project starts from nothing,
runs, and tears down leaving zero residual containers/networks/volumes" — is **REUSED** from hosted
CI evidence (TE-2CI.2 corrections C1/C2, hosted-proven on run `31930125170`; further reconfirmed on
every subsequent `Required validation` run, most recently `8334244` per PR #3). See item 9 below.

The **cold, empty-database** half of "clean start" — the part TESTING_STRATEGY.md itself identifies
as the meaningful check, since PostgreSQL applies DDL transactionally — is independently and freshly
proven in item 1 above, using a genuinely empty, isolated database.

### 5. Contract fixtures — **PASS**

Run via `python:3.12-slim` with `git` installed, matching the TE-2CI.1 local-verification method
(the fixture validator and secret checker are standard-library-only and git-tree-aware):

```text
Contract fixture validation: 7 candidate fixture file(s) checked
(discovered via git ls-files --cached --others --exclude-standard).
  - docs/agent/fixtures/accepted-offer-work-order/accepted-commercial-offer-handoff-example.json
  - docs/agent/fixtures/accepted-offer-work-order/negative-invalid-line-selection-example.json
  - docs/agent/fixtures/accepted-offer-work-order/negative-missing-account-traceability-example.json
  - docs/agent/fixtures/accepted-offer-work-order/partial-award-selected-lines-example.json
  - docs/agent/fixtures/accepted-offer-work-order/work-order-shell-output-example.json
  - docs/agent/fixtures/terms-and-conditions/tc-clause-library-demo.json
  - docs/agent/fixtures/terms-and-conditions/tc-selection-example-commercial-offer.json
All contract fixture rules passed.
EXIT=0
```

Same 7 fixtures as every prior recorded run; no new fixture added.

### 6. Secrets / configuration — **PASS**

```text
Committed-credential check: 644 file(s) in the proposed tree
(git ls-files --cached --others --exclude-standard); 641 scanned as text, 3 skipped as binary
or oversized.
No committed-credential findings.
EXIT=0
```

(File count is higher than TE-2CI.2's recorded 635 because more files have been committed to the
repository since — expected, not a defect.)

Validator/secret-checker/cleanup-helper unit test suites, run together:

```text
python -m unittest discover -s scripts/tests
Ran 58 tests in 13.075s
OK
```

**Configuration contract, inspected directly** (`backend/app/core/config.py`,
`backend/app/core/database.py`):

- `DATABASE_URL` is the single source of truth; `normalize_database_url()` accepts only
  `postgresql`, `postgres` and `postgresql+psycopg` and **rejects every other dialect with a raised
  `ValueError`** — a stale SQL Server URL fails loudly at startup rather than being silently
  accepted or ignored.
- `JWT_SECRET` (default `change-this-in-real-use`) and `POSTGRES_PASSWORD` (default
  `ChangeThisStrongPassword123!`) are clearly-labeled development placeholders, matching
  `.env.example`, not real secrets — and both are already covered by the credential-check's
  placeholder-shape rules (confirmed no finding above).
- `.env` is gitignored and was not read or modified by this pass (the harness itself declined to
  read it — a working safety control, not a gap).

**Deliberately unset production-only values, identified without inventing them**: production JWT
signing secret, production database credentials, and — more broadly — **no deployment workflow,
environment, or production secret-store integration of any kind exists yet** anywhere in the
repository (`.github/workflows/` contains only the validation workflow; no `deploy*.yml` exists).
This matches `TE_2CI_GITHUB_ACTIONS_VALIDATION_FOUNDATION.md`'s own explicit "Deployment: explicitly
not created" section. **Classified LATER-GATE** — this is deployment-package scope, and the task's
scope control explicitly excludes introducing deployment infrastructure in this pass.

**Local hygiene note (not a TE-2C blocker):** every command against the live dev stack emitted
`"POSTGRES_USER"/"POSTGRES_DB"/"POSTGRES_PASSWORD" variable is not set` warnings from Docker
Compose, consistent with the pre-existing local `.env` staleness already flagged in the TE-2CI.1
acceptance record's "Local environment incident" section. The dev stack itself continues to run
correctly (confirmed healthy throughout this pass), so this is cosmetic noise from Compose
re-resolving variables for services not being touched, not a functional defect; it remains a
developer follow-up outside TE-2C's scope.

### 7. Stack-migration consistency — **PASS**

Grep sweep of active source (excluding `docs/` historical/continuity records, which are
deliberately preserved as-written) for `pyodbc|mssql|sql server|next.config|next/navigation|from
'next'|require('next')`, across `backend/app`, `backend/tooling`, `backend/alembic`,
`frontend/src`, `frontend/*.json|*.ts`, `e2e/tests`, `scripts/`, `docker-compose.yml`,
`.github/workflows/`.

Every match inspected individually. All seven matches are **comments explaining that SQL Server is
no longer used**, none is an active dependency, import, or runtime code path:

```text
backend/app/core/database.py:19        — "...rejected rather than silently accepted, so a stale
                                           SQL Server URL fails loudly..." (explains the rejection above)
backend/app/modules/identity/repository.py:40 — "SQL Server's default collation did this [case-
                                           insensitive match]..." (explains why an equivalent
                                           PostgreSQL expression index was added)
backend/alembic/versions/20260705_0014_...py:66 — "The original SQL Server implementation guarded
                                           every statement with COL_LENGTH/sys.indexes..." (historical)
backend/alembic/versions/20260705_0016_...py:25 — "...the SQL Server filtered [index]..." (historical)
backend/alembic/versions/20260709_0022_...py:379 — "...the SQL Server 1/0 coercion is no longer
                                           needed." (explicitly says it's gone)
backend/alembic/versions/20260712_0028_...py:117 — "...The SQL Server chain..." (historical, about
                                           preserved revision identity, ADR-028)
docker-compose.yml:2-4,78,81            — comments explaining the mssql-data volume is deliberately
                                           NOT declared/reused (rollback evidence only)
```

Additional confirmation:

```text
backend/requirements.txt   -> no pyodbc, no mssql-related package
frontend/package.json      -> no "next" dependency
backend/Dockerfile         -> "No Microsoft ODBC driver ... is required since ADR-028 moved the
                               database to PostgreSQL" (explanatory, not an active dependency)
```

**No active stale SQL Server or Next.js assumption was found.** The active production-oriented
foundation is confirmed React + Vite (frontend/package.json: react 19.0.0, react-router-dom
7.18.2, vite 7.3.6, vitest 4.1.10 — no Next.js) and PostgreSQL-only (backend rejects any other
dialect at startup, as shown above).

### 8. Failure / diagnostic evidence — **PASS**, with one precise finding recorded

**Database-unavailable failure, exercised live** (isolated one-off container, image
`pbl-crm-hiring-backend:latest`, `DATABASE_URL` pointed at a nonexistent host, no impact on the dev
stack):

```text
docker run -d --rm --name te2c-dbfail-test -p 18099:8000 \
  -e DATABASE_URL="postgresql+psycopg://nouser:nopass@nonexistent-host-te2c:5432/nodb" \
  -e JWT_SECRET=te2c-scratch-not-real pbl-crm-hiring-backend:latest
```

Observed: `backend/app/startup.py`'s `wait_for_database_and_prepare()` gates `uvicorn.run(...)` — the
HTTP port **never opens** until the database is reachable and `alembic upgrade head` succeeds. While
unreachable:

```text
Database not ready yet or migration failed temporarily (attempt 1/60): (psycopg.OperationalError)
[Errno -2] Name or service not known
(Background on this error at: https://sqlalche.me/e/20/e3q8)
```

repeated every 2 seconds, up to 60 attempts (~120s), with the **exact SQLAlchemy error class and
DNS-resolution reason** printed each time and **no username or password ever appearing in the log**
(confirmed by reading every log line). After the 60th attempt the loop re-raises
(`if attempt == max_attempts: raise`, `backend/app/startup.py:32-33`) and the process crashes; the
container (run with `--rm`) exited and was removed automatically before the last poll — consistent
with a Python-level unhandled exception terminating the entrypoint, not a hang.

**Finding, recorded for completeness (not a TE-2C gap):** `docker-compose.yml`'s `backend` service
declares no `restart:` policy, so under plain `docker compose up`, a backend that exhausts its
60-attempt DB-wait would exit and **stay exited** rather than auto-retry, unless an external
orchestrator restarts it. This is a legitimate deployment-configuration decision (restart policy,
orchestration platform) that belongs to the not-yet-created deployment package, **classified
LATER-GATE**, consistent with this pass's scope control against introducing deployment
infrastructure. Recorded here so it is not silently rediscovered later.

**Health-endpoint behaviour, reviewed precisely:** `GET /api/health` (`backend/app/main.py:48-54`)
is a pure liveness check — it returns `{"status": "ok", ...}` unconditionally and never calls
`verify_database_connection()`. A separate route, `GET /api/platform/db-health`, does call it. In
practice this distinction is largely moot **at container startup**, because `startup.py`'s retry
gate (above) already prevents the HTTP port from opening at all until the database is reachable —
so every orchestration health-wait in this repository (`docker-compose.yml`'s implicit dependency
ordering, `scripts/run-e2e.ps1`'s `Wait-ForHttp`, and the CI workflow's `wait_for` step) is
effectively already gated on DB readiness through this mechanism, not bypassed by it. The residual,
narrower point — `/api/health` would **not** reflect the database going unreachable *after* the
process has already started and is running — was not empirically exercised in this pass (it would
require killing the live dev `db` container mid-session, which this pass deliberately avoided as
unnecessarily disruptive to the running dev stack for a point already establishable by direct code
reading). Recorded as a precise, narrow, non-blocking observation for the final NFR gate's
"Monitoring" work (health-check richness), not a TE-2C gap.

**Backend error visibility, exercised live** against the running dev stack (read-only, no data
created):

```text
GET /api/accounts (no Authorization header)      -> 401 {"detail":"Authentication required."}
POST /api/auth/login {"username":"","password":""} -> 422 {"detail":[{"type":"string_too_short", ...}]}
GET /api/accounts/00000000-0000-0000-0000-000000000000 (no auth) -> 401 {"detail":"Authentication required."}
```

Every response is a structured JSON body with no stack trace, no internal path, no secret. Errors
are diagnosable without exposing sensitive detail, consistent with `CODING_STANDARDS.md` §8/§9.
**Minor consistency note** (not a defect): the actual envelope is FastAPI's default `{"detail":
...}` shape, not the `{"error": {"code", "message", "details"}}` envelope shown as the "recommended
format" in `CODING_STANDARDS.md` §8. This is a documentation-vs-implementation wording mismatch,
not a security or diagnosability problem — recorded under residual/consistency findings (§10 below),
not fixed in this pass.

**Compose/service-failure diagnosability**: already proven by the standing CI design (`Capture
Compose logs on failure` step, exercised for real on the intentionally-failing scratch run
`31865333180`, per `TE_2CI_GITHUB_ACTIONS_VALIDATION_FOUNDATION.md`) — **REUSED**, not re-executed.

**External-integration failure paths** (e.g. SurePass/`AIV-001`): **not applicable** — no such
integration is implemented anywhere in the current codebase (confirmed by the absence of any
SurePass client/adapter code; `ADR-015`/`DEFERRED_REQUIREMENTS.md` both record this as deliberately
deferred). **Classified LATER-GATE.**

**Migration-failure rollback** (PostgreSQL's transactional DDL guarantee): architecturally
guaranteed per ADR-028 and asserted throughout `TESTING_STRATEGY.md`, but not empirically
re-demonstrated with a deliberately broken migration in this pass. **Classified GAP, low priority /
optional** — cheap to prove later in an isolated throwaway database if the independent reviewer
wants full coverage; not manufactured as required work here per the task's explicit "do not create
work merely to make the package look substantial" instruction.

### 9. Auth / authz / TLS design review — **PASS** (review only, no certification claimed)

**Authentication mechanism**, read directly from `backend/app/core/security.py`:

- Password hashing: PBKDF2-HMAC-SHA256, 260,000 iterations, random 16-byte salt per password,
  constant-time comparison (`hmac.compare_digest`). Stored as
  `pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`.
- Tokens: a hand-rolled HS256 JWT (not a third-party library) — header/payload base64url-encoded,
  HMAC-SHA256 signature over `header.payload` using `settings.jwt_secret`, signature verified with
  `hmac.compare_digest` before the payload is trusted, expiry (`exp`) checked, `sub`/`user_public_id`
  required. No obvious cryptographic flaw was found in this reading (proper salting, proper
  iteration count, constant-time compares, signature verified before parsing payload as trusted).

**Authorization**, read directly from `backend/app/modules/identity/dependencies.py`:

- `get_current_user` re-validates the token's `user_public_id` **against the database on every
  request** (`get_user_with_roles_by_public_id`) and rejects if the user is missing or
  `is_active` is false — so a deactivated user's still-unexpired token is rejected immediately,
  not only at next login.
- `require_roles(*codes)` is a per-route FastAPI dependency enforcing role membership server-side
  (403 if the current user's roles don't intersect the required set). This is the mechanism behind
  every module's documented role table (e.g. `WORK_ORDER_CREATE_ROLES`,
  `COMMERCIAL_OFFER_...` role constants) — confirming `AGENTS.md`'s repeated claim that "backend
  authorization is authoritative" is actually implemented this way, not merely asserted in docs.

**Secret handling**: covered by item 6 above (no committed credential findings; clearly-labeled dev
placeholders; production secret strategy correctly deferred and explicitly unimplemented).

**TLS**: is a **deployment-environment design requirement**, not something the local development
Compose stack terminates today — `docker-compose.yml` exposes plain HTTP on `8000`/`3000` for local
development only, and no TLS termination, certificate, or reverse-proxy configuration exists
anywhere in the repository. This is correctly out of scope for local Compose and is **not**
introduced by this pass (per the task's explicit instruction not to add deployment infrastructure
merely to terminate TLS locally). **Classified LATER-GATE** for the actual TLS-terminating
deployment design; the review itself (this paragraph) is the TE-2C-level evidence required.

**What remains for the final security/production gate, stated plainly**: SSO/MFA (NFR baseline
"Authentication" row — not implemented, correctly deferred), a vetted JWT library versus the current
hand-rolled implementation (worth an independent security review before production, not re-derived
here), TLS termination design, production secret-store integration, and the nine deferred Python
dependency advisories (item 11 below). None of these are invented or resolved by this paragraph;
they are named so the final gate does not have to rediscover them.

### 10. Protected integration — **PASS** (positive and negative paths both hosted-proven)

**Status change from every prior revision of this document.** Every earlier pass correctly
recorded the negative case as `GAP` — outstanding, not yet attempted, and explicitly deferred
pending a controlled exercise performed deliberately and separately from routine pass work. That
controlled exercise (PR #4) has since been performed and has succeeded. This section preserves
the original PR #3 positive-path evidence exactly as recorded, adds the PR #4 negative-path
evidence, and updates the classification accordingly. See section 10a immediately after this one
for the separate hosted validation of this branch's accepted implementation/JWT-mask head before
this documentation delta (PR #5).

#### 10.1 Positive-path evidence — PR #3 (unchanged, reused)

**PR #3 evidence, reused and cited exactly, with its precise identity:**

```text
Reviewed PR head:     833424424da501befda9b94ebb44eeffe1bc9a38
Merge commit:          60fd68373ea910e6ac00ba945437d68a3e859d36
Workflow run:          32030845107
```

**What this evidence establishes (classified precisely):**

- **REUSED — positive-path behavioural proof.** While `Required validation` was incomplete on
  commit `8334244`, the PR's `mergeable_state` was `blocked`; `TE-2CI Validation` ran on that exact
  commit; every validation job succeeded; `Required validation` concluded success;
  `mergeable_state` became `clean`; the project owner then gave explicit approval; the merge-commit
  integration succeeded and `main` advanced to `60fd683`. This is real, already-happened evidence
  that a compliant PR with a green required check becomes mergeable and merges only after explicit
  owner action.
- **Ruleset configuration, independently inspected and recorded separately on 17 August 2026
  (ADR-031).** The live ruleset (id `20939060`) was independently inspected through the GitHub API
  and its configuration recorded as ADR-031, distinct from and prior to the PR #3/#4 evidence
  below. The earlier local/sandboxed documentation-authoring pass that first drafted this section
  could not itself re-run that `gh api` inspection directly (no `gh` CLI or outbound network
  access from that specific sandboxed session) — a narrow, historical fact about that one pass,
  not a claim about every session in this repository's history. PR #3 (positive path) and PR #4
  (negative path, section 10.2) separately supply real hosted **behavioural** evidence of the same
  ruleset actually enforcing in both directions. That behavioural evidence is complementary to,
  not a substitute in principle for, direct configuration inspection — a future session with `gh`
  access re-running `gh api repos/<PBL's internal repository>/rulesets/20939060` remains a cheap,
  useful, independent confirmation. **Reclassified REUSED** for TE-2C's purposes: between the
  recorded ADR-031 configuration inspection and the PR #3/#4 behavioural evidence, this item is no
  longer an unresolved `GAP`. This does not claim every conceivable bypass or direct-update route
  has been behaviourally disproven — see section 10.2's own conclusion for the precise, bounded
  scope of what the negative-path evidence establishes.

#### 10.2 Negative-path evidence — PR #4 (new, closes the prior GAP)

**Controlled negative-path exercise, performed deliberately and separately, per the plan every
prior pass deferred to:**

```text
Controlled negative-path PR:  #4 — TE-2C protected-integration negative-path probe — DO NOT MERGE
Base:                          main at 60fd68373ea910e6ac00ba945437d68a3e859d36
Probe branch:                  te-2c-required-validation-negative-proof
Probe commit:                  f668d06a04e062d00ae17769bed2f2c75139076b

TE-2CI run:                    32093987389 (run #13)
Result:                        completed / failure

Backend regression job:        95581647378
Backend regression result:     completed / failure
Pytest result:                 1 failed, 253 passed
Sole failing test:             tests/test_te2c_required_validation_negative_probe.py
                                (failure was the intentional TE-2C assertion, not a genuine
                                 regression)

All other upstream validation jobs: success

Required validation job:       95582178345
Required validation result:    completed / failure
Aggregate diagnostic:          "Required validation FAILED. Jobs not reporting success:
                                 backend-regression"

GitHub PR state after checks completed:
  mergeable:        true
  mergeable_state:  blocked
  merged:           false

The merge endpoint was NOT invoked. PR #4 was closed without integration after evidence capture.
```

**Conclusion, stated precisely (do not read more into this than what is written):** this proves
that, under the active repository ruleset and the current TE-2CI workflow, a completed failure in
an upstream validation job (here, one intentionally failing test in `backend-regression`)
propagates to the required `Required validation` aggregate check and leaves the pull request
blocked from protected integration (`mergeable_state: blocked`, `merged: false`), with the merge
endpoint never invoked. This does **not** prove that every conceivable GitHub bypass or update
mechanism is impossible — see ADR-031's own "Direct push semantics" note, which this record does
not contradict or extend. **Reclassified PASS** (previously `GAP`).

**Force-push / branch-deletion rejection**: still never demonstrated behaviourally post-ADR-031.
**Remains classified GAP, low priority** — unchanged from every prior pass; force-push discipline
is already enforced by process (`AGENTS.md`, PBL's local working notes) independent of the ruleset, and
this repository's own ruleset inspection (ADR-031) already lists non-fast-forward-update rejection
as a verified *configuration* rule. A live behavioural demonstration remains available at low
priority if a future reviewer wants full coverage; it is not manufactured here merely to close a
line item.

### 10a. Hosted positive validation — PR #5 (accepted implementation/JWT-mask head, before this documentation delta)

Separate from the PR #3/#4 protected-integration mechanism evidence above, this subsection records
the hosted `Required validation` run against the accepted implementation/JWT-mask head this branch
carried before this documentation delta — the same commit chain recorded in "Accepted commit
chain" at the top of this document. Committing this documentation delta creates a later PR head
that this run did not and cannot cover; see "Closure-update integration status" at the top of this
document.

```text
PR:                    #5 — TE-2C migrated-foundation verification
PR base:               main
Base SHA:              60fd68373ea910e6ac00ba945437d68a3e859d36
Validated PR head:     3d6ff2807917e6ca4b31fa91c338c92b0c1e1f13

TE-2CI run:            32097159958 (run #14), event: pull_request
Result:                completed / success

Jobs completed success:
  - Backend regression
  - Empty-database migrations
  - Frontend build and tests
  - Contract fixture validation
  - Secret and dependency checks
  - Compose build, health and E2E
  - Required validation

Backend regression job:  95590643302
Backend result:          265 passed, 1 warning
```

The one warning is the previously noted cosmetic `PytestCollectionWarning` for `TestTokenError`
(pytest's default heuristic flags any class whose name starts with `Test`; it is an exception
class, not a test class, and pytest correctly declines to collect it — see section 12). It is
recorded here rather than silently omitted, and is not a new failure.

```text
Required validation job:      95591211146
Required validation result:   success
```

**Hosted proof of the JWT-masking correction specifically:**

- the JWT generation step (`Generate an ephemeral JWT secret for this run`) completed success;
- the subsequent `Apply migrations` and `pytest` steps' logged environment output displayed
  `JWT_SECRET: ***` rather than the raw generated value;
- the raw generated JWT secret was not visible in those later environment logs on this hosted run.

**This hosted run validates commit `3d6ff2807917e6ca4b31fa91c338c92b0c1e1f13` specifically** — the
exact bound commit recorded in "Accepted commit chain" above, including both the TE-2C tooling
package and the JWT-mask correction together.

**This documentation-only closure update does not reuse run #14 as its own final check.** Once
this revision is committed, it creates a new PR head distinct from `3d6ff280`, which run #14 never
saw and cannot have validated. That new head requires its own fresh `Required validation` run
before this revision may be integrated — see "Closure-update integration status" at the top of
this document.

### 11. Backup / restore — **PASS** (mechanism corrected under a second independent review, pass 4, and re-executed for real)

**Mechanism**: `scripts/te-2c-backup-restore.ps1`. Documented in `scripts/README.md` under
"TE-2C backup/restore evidence". **This section replaces the pass-3 evidence in full** — pass 3's
implementation had one further P1 and two further P2 defects found by a second independent H.1
review (findings 1, 2, 4 in the status section above); do not treat pass-3 output shown in an
earlier revision of this document as current proof of anything. In particular, pass 3's language
"source confirmed quiescent" and "certified source-at-backup-time state" is retracted as
overstated relative to what a row-count comparison actually proves — see finding 2 below.

**Corrected design (this pass).**

- **Cleanup verification now has an explicit three-state contract, not just "empty output = absent"
  (finding 1).** A shared `Resolve-AbsenceVerification` function distinguishes: the verification
  command itself succeeded and confirmed absence (only this is success); the verification command
  itself succeeded and found the resource present (failure); or the verification command itself
  failed to run (also failure — absence is **never** inferred from empty/missing output when the
  command that produced it did not itself succeed). `Remove-AndVerifyContainer` now checks the
  verification `docker ps` call's own exit code. `Remove-AndVerifySourceTempFile` now uses an
  explicit two-marker shell probe (`echo TE2C_PRESENT` / `echo TE2C_ABSENT`, itself always exiting
  0) rather than reading a bare `test -e` exit code, so a `docker exec`/container/daemon failure
  can never be misread as "file gone".
- **The quiescence claim is narrowed, not technically strengthened (finding 2).** Per the
  independent review's own guidance to prefer narrowing over adding complexity "unless
  [establishing a stronger guarantee is] genuinely simple" (it is not — a true snapshot-correspondence
  proof would need a held, coordinated background transaction via `pg_export_snapshot()`, which
  this script deliberately does not add), the before/after per-table row-count comparison is now
  described precisely as a **cardinality-drift guard**: it fails the run if any table's row count
  changed during the backup window, but it does **not** detect content-preserving `UPDATE`s or an
  equal-and-opposite insert/delete pair, and the script's own output and comments say so explicitly.
  Restored-vs-source comparison is now described as **structural/data-presence verification
  associated with a successful PostgreSQL logical backup** (`pg_dump` itself runs inside one
  transaction, so the dump file is internally point-in-time consistent independent of anything this
  script separately measures) — explicitly **not** byte-for-byte or row-content equivalence proof.
  The variable and message names that implied a "certified" state are removed.
- **Restore-target destructive actions are now ownership-label-guarded, not name-only (finding 4).**
  Every restore-target container this script creates is stamped with a fixed label
  (`com.pbl-crm-hiring.te2c-backup-restore=owned`) at creation. Before force-removing anything named
  `pbl-crm-hiring-te2c-restore-target` — in the pre-run defensive cleanup or end-of-run cleanup —
  `Test-ContainerOwnership` inspects that label first: absent name → nothing to protect, proceed;
  present with the exact label → this script's own, safe to remove; present **without** the label →
  refuse and abort, since the name may belong to something else. `-KeepArtifacts` leaves the label
  in place so a later normal run's defensive cleanup still recognises the container safely.
- Everything else from the pass-3 design is unchanged: source-identity verification via Compose
  labels before any `pg_dump`; a unique per-run source temp-dump path; `pg_restore
  --no-owner --no-privileges --single-transaction --exit-on-error` with any non-zero exit an
  unconditional hard failure; no password ever printed; the only Docker resource ever force-removed
  is the one fixed container name, guarded by `Test-SafeResourceName`.

**Self-test** (`-SelfTest`, no Docker involved) — now also covers `Resolve-AbsenceVerification`'s
fail-closed contract directly:

```text
.\scripts\te-2c-backup-restore.ps1 -SelfTest
Running self-test of safety-critical guard functions (no Docker involved)...
Self-test PASSED (20 assertions, no Docker used).
EXIT_CODE=0
```

**Negative test (source identity, unchanged mechanism, re-verified): a deliberately non-Compose
source container is rejected before any `pg_dump`.**

```text
.\scripts\te-2c-backup-restore.ps1 -SourceContainer "te2c-fake-source"
Verifying 'te2c-fake-source' is actually the pbl-crm-hiring Compose 'db' service (by label, not name alone)...
TE-2C backup/restore evidence exercise: FAIL
Refusing to operate: 'te2c-fake-source' does not carry com.docker.compose.project='pbl-crm-hiring'
and com.docker.compose.service='db'. ...
EXIT_CODE=1
```

**Negative test (finding 4): an identically-named but unowned container is refused, not deleted.**
A throwaway container was created with the exact fixed name `pbl-crm-hiring-te2c-restore-target`
but deliberately **without** the ownership label (confirmed via `docker inspect` before the test:
the label lookup returned empty). The real backup/restore script was then run normally against the
genuine source:

```text
Defensive pre-run cleanup: checking for any leftover restore target from an earlier interrupted run...
WARNING: A container named 'pbl-crm-hiring-te2c-restore-target' exists but does NOT carry this
tool's ownership label (com.pbl-crm-hiring.te2c-backup-restore=owned). Refusing to remove it --
it may belong to something else. This script never force-removes a resource it does not own, even
one matching its own fixed disposable name.
TE-2C backup/restore evidence exercise: FAIL
Defensive pre-run cleanup could not confirm 'pbl-crm-hiring-te2c-restore-target' is safely absent
(or is present but not owned by this tool). Refusing to proceed.
EXIT_CODE=1
```

The script aborted **before** ever attempting `pg_dump` (no backup was created against an unusable
target). `docker ps -a --filter name=pbl-crm-hiring-te2c-restore-target` immediately afterward
confirmed the fake container was still present (`Up 26 seconds`) — it was not deleted. The fake
container was then removed manually (`docker rm -f`), since the script correctly refused to touch
it; no real resource was ever put at risk by this test.

**Real execution, run 1** (`.\scripts\te-2c-backup-restore.ps1`, against the real
`pbl-crm-hiring-db-1`):

```text
Verifying 'pbl-crm-hiring-db-1' is actually the pbl-crm-hiring Compose 'db' service (by label, not name alone)...
Source container identity confirmed.
Confirming source database is reachable (local trust auth, no password)... Source reachable.
Defensive pre-run cleanup: checking for any leftover restore target from an earlier interrupted run...
Source: 28 table(s), Alembic revision 20260713_0029, 81 total row(s) (pre-dump snapshot).

Backing up source database (pg_dump -Fc, inside the source container, read-only)...
Backup complete: <temp path>\te2c-backup-restore-....dump (154981 bytes) in 1.31s.
Checking for cardinality drift during the backup window (before/after per-table row-count comparison)...
No cardinality drift detected (identical per-table row counts and Alembic revision before and after
pg_dump). This is a coarse drift guard, not proof the source was fully unchanged.

Creating disposable restore-target container (postgres:17), labelled com.pbl-crm-hiring.te2c-backup-restore=owned...
Copying the backup artifact into the restore target and running pg_restore...
Restore step complete in 8.28s (pg_restore exit 0).

--- Verification summary (structural/data-presence, not byte-for-byte equivalence) ---
Table count:       source=28 target=28
Alembic revision:  source=20260713_0029 target=20260713_0029
Total row count:   source=81 target=81 (per-table comparison is the authoritative check, not this total)
Verification PASSED: restored target's per-table row counts, table set and Alembic revision match the source's pre-dump state.

--- Timings ---
Backup  :   1.31s
Restore :   8.28s
Verify  :  17.07s
Total   :  62.98s

TE-2C backup/restore evidence exercise: PASS
Cleaning up...
Removed and verified absence of the source container's temporary dump file.
Removed and verified absence of the local backup artifact.
Removed and verified absence of the disposable restore-target container.
EXIT_CODE=0
```

Residue check immediately after: `docker ps -a --filter name=pbl-crm-hiring-te2c-restore-target`
returned nothing; `docker exec pbl-crm-hiring-db-1 sh -c "ls /tmp/te2c-source-backup-*.dump"`
returned nothing.

**Real execution, run 2** (immediately after run 1, no manual cleanup in between): identical PASS
(table count 28=28, Alembic revision match, row count 81=81 per table), timings ~73.1s total,
`EXIT_CODE=0`, cleanup again explicitly verified for all three artifacts. Final residue check after
both runs: no restore-target container, no source temp-dump file, no local dump file.

**What this proves and what it does not.** This is genuine, fresh, real evidence that the
backup/restore *mechanism* works against the migrated PostgreSQL foundation, with source identity,
ownership-guarded destructive cleanup, restore success, and structural verification all
independently confirmed via an explicit fail-closed contract rather than inferred. It does **not**
prove the source was quiescent in every sense (only that row cardinality did not drift), does
**not** prove byte-for-byte restore equivalence, and does **not** establish production backup
frequency, retention, RPO or RTO — those remain **HUMAN-PARAMETER**, per
`NFR_BASELINE_AND_VERIFICATION.md`'s own "Required parameters before production deployment" list.

**Recommended independent-review overlay**: H.1 (CI/scripts/tooling — destructive-operation
boundaries, documented invocation path). This overlay is what surfaced every finding across both
review passes.

### 12. Timing baseline — **PASS** (test-token guard corrected and regression-tested, pass 5)

**Mechanism**: `scripts/te-2c-timing-baseline.ps1` (unchanged this pass), plus
`backend/tooling/smoke_data/auth_tokens.py` (corrected this pass) and its new permanent regression
coverage, `backend/tests/test_smoke_data_auth_tokens.py`. Documented in `scripts/README.md` under
"TE-2C timing baseline". **This section's `APP_ENV`-related content replaces pass 4's in full** —
pass 4's guard read `get_settings().app_env`, which defaults to `"development"` when `APP_ENV` is
simply unset, so a genuinely missing `APP_ENV` passed undetected; do not treat pass 4's "APP_ENV
refusal" claims as proof that an *unset* variable was ever actually tested — it was not, only
`APP_ENV=production` was. The pass-4 design and evidence for `-SampleCount`/`-WarmupCount`
validation, the loopback `-BaseUrl` check and `-MaximumRedirection 0` are unchanged and not
repeated here in full; see the previous pass's summary in the status section above.

**Corrected design (this pass).**

- **`APP_ENV` is now read from the process environment directly, not through `Settings`
  (finding 1).** `issue_test_bearer_token()` now calls `os.environ.get("APP_ENV")` itself. A
  `None` result (the variable is genuinely absent) is refused outright with its own distinct error
  message, before the permitted-values check ever runs. As a secondary consistency check, the
  explicit value is also compared against the application's resolved `get_settings().app_env`; a
  disagreement is refused rather than trusted. `app.core.config.Settings` itself is unchanged, and
  real `/api/auth/login` authentication behaviour is unchanged.
- **Permanent regression coverage added (finding 2).** `backend/tests/test_smoke_data_auth_tokens.py`,
  12 tests, runs as part of the existing backend regression suite that CI already executes — no new
  test framework introduced. See the results table below for what each proves.
- **Printing-contract wording corrected (documentation precision, not a code change).** Every
  place that said or implied "the token is never printed on any code path" now states the precise
  guarantee: `issue-test-token` intentionally writes the token to stdout as its interface; the
  timing script captures that stdout and never displays or echoes it, on any path; the helper
  itself writes no token to stderr or diagnostic text. Corrected in `auth_tokens.py`'s own
  docstring, the timing script's docstring and `Write-Host` message, `scripts/README.md`, and this
  document.

**New automated tests, `backend/tests/test_smoke_data_auth_tokens.py` (12 tests), and what each proves:**

| Test | Proves |
| --- | --- |
| `test_missing_app_env_is_refused` | A genuinely absent `APP_ENV` (via `monkeypatch.delenv`) is refused — the exact gap finding 1 identified |
| `test_production_app_env_is_refused` | `APP_ENV=production` is refused |
| `test_unknown_app_env_is_refused` | An unrecognised value (`staging`) is refused |
| `test_development_app_env_is_permitted` | `APP_ENV=development`, with `get_settings` agreeing, issues a token for the fixed identity |
| `test_ci_app_env_is_permitted` | `APP_ENV=ci`, with `get_settings` agreeing, issues a token |
| `test_mismatched_explicit_env_and_settings_is_refused` | The secondary consistency check: an explicit, permitted env value that disagrees with `get_settings().app_env` is refused |
| `test_helper_has_no_username_parameter` | Structural proof via `inspect.signature` that zero parameters exist — not merely a documented convention |
| `test_token_expiry_is_the_short_te2c_duration` | Decodes a real issued token and asserts `exp - iat` equals exactly `TEST_TOKEN_EXPIRES_MINUTES * 60`, and that this is `< 480` minutes |
| `test_missing_identity_is_refused` | A lookup returning no user is refused |
| `test_inactive_identity_is_refused` | A lookup returning an inactive user is refused |
| `test_issuing_a_token_creates_no_business_event` | `business_event` max id is identical before and after a real successful issuance |
| `test_app_env_is_read_from_process_environment_not_cached_settings_default` | Direct proof against the real process environment (`os.environ.pop`, not just `monkeypatch`) that this module reads `os.environ`, not a cached `Settings` default |

```text
docker compose exec -T backend pytest tests/test_smoke_data_auth_tokens.py -v
12 passed, 1 warning in 4.62s
```

(The one warning is `PytestCollectionWarning: cannot collect test class 'TestTokenError'` — pytest's
default collection heuristic flags any class whose name starts with `Test`; `TestTokenError` is an
exception class, not a test class, and pytest correctly declines to collect it. Cosmetic only, not
a defect, and out of this pass's scope to rename.)

**Full backend regression, re-run with the new module included:**

```text
docker compose exec -T backend pytest -q
265 passed, 1 warning in 306.98s (0:05:06)
```

265 = the existing 253-test baseline + the 12 new tests. No pre-existing test was weakened, skipped
or deselected.

**Direct CLI-level negative/positive evidence** (in addition to, not instead of, the pytest
coverage above — exercising the real `issue-test-token` CLI wrapper end-to-end):

```text
business_event boundary before: 4

=== APP_ENV genuinely absent, via `env -u APP_ENV` (not merely unreferenced) ===
docker compose exec -T backend env -u APP_ENV python -m tooling.smoke_data issue-test-token
EXIT=2
"Could not issue a test token: Refusing to issue a test token: APP_ENV is not set in the process
environment. This tool requires APP_ENV to be explicitly present and equal to one of
['ci', 'development'] -- an unset value is never treated as 'development' merely because the
application's own configuration default happens to be 'development'."

=== APP_ENV=production ===
docker compose exec -T -e APP_ENV=production backend python -m tooling.smoke_data issue-test-token
EXIT=2
"Could not issue a test token: Refusing to issue a test token: APP_ENV='production' is not one of
the permitted local development/test values ['ci', 'development']."

=== APP_ENV=development ===
docker compose exec -T -e APP_ENV=development backend python -m tooling.smoke_data issue-test-token
EXIT=0
token acquired (277 characters)

=== token works against the readonly protected endpoint ===
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/accounts?limit=5
[]
HTTP_STATUS=200

=== business_event boundary unchanged ===
business_event boundary after: 4

=== real container's own environment confirmed unaffected by any of the above overrides ===
curl http://localhost:8000/api/health
{"status":"ok","service":"pbl-crm-hiring-backend","environment":"development"}
```

**Real timing-baseline execution, once, end to end with the corrected helper**
(`.\scripts\te-2c-timing-baseline.ps1`, default warm-up 3 / sample 20):

```text
Issuing a short-lived test bearer token for the fixed readonly1 identity (no login audit event is
created; this script never displays or echoes the token, on success or failure)...
Token acquired (not displayed); no business_event was created to obtain it.

--- Results ---
GET /api/health (unauthenticated): n=20/20 success, min=11.1ms median=19.8ms p95=51.7ms max=53.8ms
GET /api/accounts?limit=20 (authenticated read): n=20/20 success, min=13.4ms median=21.8ms p95=48.2ms max=286.9ms

TE-2C timing baseline: PASS (repeatable baseline recorded; this is NOT an NFR/production performance certification).
EXIT_CODE=0
```

(Latencies are again somewhat elevated versus earlier passes, consistent with general host load
from the extensive Docker activity across five correction passes today rather than any change in
the mechanism; 20/20 success on both interactions, well under the 2-second local-context marker.)

**What this proves and what it does not.** The `APP_ENV` guard is now proven, not merely asserted,
to distinguish "genuinely unset" from "explicitly development" — both by unit test (mocking the
process environment directly) and by a real CLI invocation with the variable genuinely stripped.
The helper's narrowness (fixed identity, no username parameter, short expiry, zero event creation)
now has permanent, CI-executed regression coverage rather than resting on manual exercises repeated
each pass. This remains a migrated-foundation timing baseline, not a load test or production
performance certification, and must never be cited as evidence that the ERP source's "95% within 2
seconds" NFR is met.

**Recommended independent-review overlay**: H.1 (CI/scripts/tooling). This overlay is what
surfaced every finding against this script and its helper across all three review passes.

### 13. Residual risks / production parameters — **PASS** (recorded, not remediated)

**Nine deferred Python dependency advisories**, re-confirmed unchanged in this pass by directly
reading `.github/dependency-audit-known-findings.txt`:

```text
PYSEC-2026-2270  python-dotenv 1.0.1 -> 1.2.2   (not reached: set_key/unset_key never called)
PYSEC-2026-1845  pytest 8.3.4 -> 9.0.3            (test-time only, never shipped)
PYSEC-2026-161   starlette 0.41.3 -> 1.0.1        (not reached: no request.url authorization decision)
PYSEC-2026-248   starlette 0.41.3 -> 1.3.0        (not reached: same reason)
PYSEC-2026-249   starlette 0.41.3 -> 1.3.1        (limited: API consumes JSON, not urlencoded forms)
PYSEC-2026-1941  starlette 0.41.3 -> 0.47.2       (not reached: no file-upload route)
PYSEC-2026-1942  starlette 0.41.3 -> 0.49.1       (not reached: no StaticFiles/FileResponse)
PYSEC-2026-2280  starlette 0.41.3 -> 1.1.0        (not reached: no HTTPEndpoint class-based routes)
PYSEC-2026-2281  starlette 0.41.3 -> 1.1.0        (not reached: no StaticFiles; Linux containers)
```

**Status: unchanged since 14 August 2026.** All nine are carried forward exactly, per the explicit
condition already attached to their temporary acceptance in `TE_2CI_GITHUB_ACTIONS_VALIDATION_FOUNDATION.md`
("TE-2C must carry the residual risk explicitly in its own record rather than inheriting it
silently"). **Not remediated in this pass**, consistent with the task's explicit scope control.
Confirmation that no *new* advisory has appeared is REUSED via the standing `security-checks` CI job,
which runs automatically on this branch's own future PR.

*Reconciled 8 October 2026 (TB-1 finding TB1-200, corrective package CS-15):* three of the notes carried
forward above were no longer true. `PYSEC-2026-249` and `PYSEC-2026-1941` are reached through the
document upload (Slice 9C) and the Plum report upload (ERT-1), which take form fields and a file
before authentication; each request is bounded by its route's body cap.
`.github/dependency-audit-known-findings.txt` now says so. Both stay deferred to the FastAPI/Starlette
upgrade, before production. `PYSEC-2026-1845`'s "never shipped" was not true either - the backend image
installs pytest with the other requirements (TB-1 TB1-901) - though the application and the hosted
servers never run it; its note is corrected too. The block above is kept as this record wrote it.

**Documentation/implementation consistency note** (minor, recorded, not fixed): `CODING_STANDARDS.md`
§8 documents a `{"error": {"code","message","details"}}` recommended error envelope; the actual
implementation returns FastAPI's default `{"detail": ...}` shape (confirmed live in item 8 above).
Not a security issue — no secret or internal detail is exposed either way — but a real
documentation-vs-code mismatch worth a future small correction (outside this pass's scope; not a
TE-2C blocker).

**All other production parameters** (availability SLA, RPO/RTO, load profile, backup
frequency/retention, HR-feed staleness threshold, support targets, retention/disposal periods,
mobile offline policy): **HUMAN-PARAMETER**, listed in full in the "Known production parameters"
section above, none invented.

---

## Final classification

**TE-2C technical verification evidence: SATISFIED / PASS**, subject to two remaining procedural
steps that are about *this document*, not about the evidence itself: independent review of this
documentation-only delta, and a fresh hosted `Required validation` run on whatever PR head
eventually includes it (see "Closure-update integration status" at the top of this document).
**All blocking TE-2C DoD requirements are `PASS` or `REUSED`.** Separately, two explicitly
non-blocking, optional evidence items remain `GAP` and are deliberately not resolved by this
closure update: the force-push / branch-deletion behavioural demonstration noted in section 10.2,
and the migration-failure-rollback demonstration noted in section 8. Both retain their existing
low-priority/optional treatment recorded where they are discussed — this update does not silently
reclassify either of them `PASS`, and does not promote either into a TE-2C blocker.

**Final production-candidate readiness: NOT CLAIMED / LATER-GATE.** This record does not certify,
and must not be cited as certifying, final production readiness, deployment authorization, SLA
compliance, disaster-recovery capability, or production-grade security posture. Those require the
applicable PF-1 lanes and the final production-candidate gate defined in
`PRODUCTION_READINESS_GATES.md`, per ADR-025.

**Still-unset production parameters**: remain `HUMAN-PARAMETER` or `LATER-GATE` exactly as
classified throughout this document (see "Known production parameters deliberately not invented
in this pass" near the top, and section 13). Nothing new is invented by this closure update:
production availability SLA/maintenance exclusions, RPO/RTO, concurrency/volume profile, backup
frequency/retention/restore-test cadence, HR-feed staleness parameters, support targets, data
retention/disposal periods, and mobile offline policy all remain genuinely open PBL/production
decisions.

**The nine accepted/deferred Python dependency advisories** (section 13): unchanged by this
closure update. They remain residual risk carried forward for the future dependency-upgrade
package and reassessment before the final production-candidate gate, exactly as this document
already classified them — this update does not roll their remediation into TE-2C.

---

## Full command/results log references

All commands and their exact output are reproduced in the sections above rather than in a separate
appendix, per the task's request for "exact commands/results" recorded inline per DoD item.
