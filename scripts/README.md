# Scripts

Durable, documented project tooling. These are the exception to the repository's "do not commit
throwaway helper scripts" rule; keep them up to date rather than treating them as scratch files.

| Script | Purpose | Introduced by |
| --- | --- | --- |
| `smoke-data.ps1` | Seed and clean up named smoke/regression scenarios through the backend harness | TE-1 |
| `run-e2e.ps1` | Build, seed, run the Playwright suite and always clean up afterwards | TE-1 |
| `vendor-demo.ps1` | `prepare` / `status` / `preflight` / `reset` / `cleanup` wrapper over the demo data pack | Slice 6P |
| `validate_contract_fixtures.py` | Validate every contract fixture and the frozen handoff pack's invariants | TE-2CI.1 |
| `check_tracked_secrets.py` | Basic committed-credential check over the proposed tree | TE-2CI.1 |
| `ci-compose-cleanup.sh` | Project-scoped Compose teardown for the CI `compose-e2e` job (CI only) | TE-2CI.2-C1 |
| `te-2c-backup-restore.ps1` | TE-2C migrated-foundation backup/restore evidence exercise (local, non-production only) | TE-2C |
| `te-2c-timing-baseline.ps1` | TE-2C migrated-foundation standard-interaction timing baseline (not a load test/certification) | TE-2C |
| `tests/` | Standard-library `unittest` cover for the validators and the cleanup helper | TE-2CI.1, TE-2CI.2-C1 |

## PowerShell scripts

Written for PowerShell 7+. `run-e2e.ps1` also runs on Linux under `pwsh`, which is how the CI
workflow invokes it.

```powershell
.\scripts\smoke-data.ps1 scenarios
.\scripts\run-e2e.ps1
.\scripts\vendor-demo.ps1 status
```

See `docs/agent/technical-enablement/TE_1_REUSABLE_SMOKE_FIXTURES_PLAYWRIGHT_REGRESSION_FOUNDATION.md`
and `docs/agent/slices/slice-6p-demo-data-vendor-walkthrough-scenario-pack.md`.

## TE-2C backup/restore evidence

```powershell
.\scripts\te-2c-backup-restore.ps1
.\scripts\te-2c-backup-restore.ps1 -KeepArtifacts
.\scripts\te-2c-backup-restore.ps1 -SelfTest
```

**Purpose and scope: TE-2C migrated-foundation evidence only, non-production.** This proves the
backup/restore *mechanism* works against the migrated PostgreSQL foundation (ADR-028). It does
**not** establish, and must never be cited as, a production backup strategy, retention policy, RPO
or RTO -- those remain genuine, still-open parameters recorded in
`docs/agent/architecture/NFR_BASELINE_AND_VERIFICATION.md`.

**Source identity is verified, not assumed.** Before touching anything, the script confirms
`-SourceContainer` actually carries the `com.docker.compose.project=pbl-crm-hiring` and
`com.docker.compose.service=db` labels, and refuses to run `pg_dump` (or anything else) against a
container that does not -- so a mistyped or overridden `-SourceContainer` can never cause it to back
up an arbitrary local container. The source is then read only (`pg_dump`, never a write). The
restore target is a brand-new, disposable PostgreSQL 17 container with a fixed name
(`pbl-crm-hiring-te2c-restore-target`) and a freshly generated, throwaway password used only for
that container and never printed. The normal development database is never overwritten and never
restored into.

**Cardinality-drift guard, precisely scoped -- read this before trusting what it proves.**
Per-table row counts are captured from the source immediately before and immediately after
`pg_dump`; if any table's row count differs, the run fails. This is a coarse safety net against
concurrent write activity making the comparison meaningless, **not** proof that the source was
quiescent or byte-for-byte unchanged: an `UPDATE` that leaves row counts unchanged, or an
equal-and-opposite insert/delete pair, is invisible to any row-count comparison, before/after or
otherwise, and this script makes no stronger claim than that. Do not read "no cardinality drift
detected" as "the source was proven quiescent" -- it is not.

**What is verified.** Per-table row counts (not only an aggregate total), the full table name set,
and the Alembic current revision, compared between the source's own pre-dump state and the restored
target. This is **structural/data-presence verification** associated with a successful PostgreSQL
logical backup taken via `pg_dump`'s own internally-consistent transactional snapshot -- explicitly
**not** byte-for-byte or full row-content equivalence proof. `pg_restore` runs with `--no-owner
--no-privileges --single-transaction --exit-on-error`, and **any non-zero `pg_restore` exit is an
unconditional hard failure** -- it is never reinterpreted as an advisory warning, regardless of what
the later structural checks show.

**Ownership-label-guarded destructive actions.** The restore-target container's fixed name alone is
never treated as authorization to force-remove whatever currently holds it. Every restore-target
container this script creates is stamped with a fixed ownership label
(`com.pbl-crm-hiring.te2c-backup-restore=owned`) at creation time. Before force-removing anything
named `pbl-crm-hiring-te2c-restore-target` -- in the defensive pre-run cleanup or in end-of-run
cleanup -- the script inspects that label first: no container with that name is trivially safe;
a container carrying the exact label is this tool's own and safe to remove; a container with that
name but **without** the label is presumed to belong to something else and is **never** removed --
the script fails closed and aborts instead. `-KeepArtifacts` leaves the label on the preserved
container, so a later normal invocation's defensive pre-run cleanup still safely recognises and
removes it.

**Cleanup behaviour and verification, with an explicit fail-closed contract.** Every artifact this
script creates -- the source container's own temporary dump file (unique per run, so
concurrent/interrupted runs cannot collide), the local temporary dump file, and the (ownership-label-
checked) disposable restore-target container -- is removed in a `finally` block (so it runs even on
failure) and its removal is verified through `Resolve-AbsenceVerification`, a shared decision
function with three distinguishable outcomes: the verification command itself succeeded and
confirmed absence (success); the verification command itself succeeded and found the resource still
present (failure); or the verification command itself failed to run cleanly, in which case absence
is **never** inferred from empty or missing output (also failure). The source temp file's own
absence check additionally uses an explicit two-marker probe (`TE2C_PRESENT` / `TE2C_ABSENT`) run
inside the source container, so a generic non-zero `test -e` exit can never be misread as "file
gone" -- it is only ever read as "could not verify". Any cleanup step that cannot positively confirm
a safe final state makes the overall run **fail** (non-zero exit), even if backup/restore/verify
themselves passed. `-KeepArtifacts` exempts only the two documented evidence artifacts (the local
dump file and the restore-target container, which keeps its ownership label) from end-of-run
removal; the source container's own temporary dump file is always removed and verified regardless,
since it is working-directory tidiness on a live, shared, non-disposable container, not evidence.

**Secrets.** No password is ever printed. The source connection relies on this repository's
already-confirmed local trust authentication (127.0.0.1, no password required); the target's
generated password is used only inline for that container's own `docker exec` calls.

**`-SelfTest`** exercises the script's safety-critical naming/parsing/comparison/verification guard
functions (`Test-SafeResourceName`, `ConvertTo-PositiveInteger`, `Test-PerTableCountsEqual`,
`Resolve-AbsenceVerification`) without touching Docker at all. `Test-SourceContainerIdentity` (the
Compose-label check) and `Test-ContainerOwnership` (the ownership-label check) inherently require
Docker and are instead exercised for real -- against the genuine source, a deliberately non-Compose
container, and a deliberately unowned same-named container -- as part of the recorded execution
evidence. No new test framework is introduced (this repository has none established for
PowerShell); it is a small, dependency-free assertion block in the same spirit as the CI Compose
cleanup helper's own fail-closed gates.

See `docs/agent/technical-enablement/TE_2C_MIGRATED_FOUNDATION_VERIFICATION.md` for recorded
execution evidence.

## TE-2C timing baseline

```powershell
.\scripts\te-2c-timing-baseline.ps1
.\scripts\te-2c-timing-baseline.ps1 -SampleCount 50 -WarmupCount 5
```

**Purpose and scope: a migrated-foundation timing baseline, not a load test or production
performance certification.** It measures round-trip latency for two representative, already-existing
interactions (`GET /api/health` unauthenticated, and an authenticated `GET /api/accounts?limit=20`
read) from a single local client against the local Compose stack -- no agreed normal-load profile,
no production-like concurrency or data volume is represented. Whether observed samples fall above or
below the ERP source's "95% within 2 seconds" figure is reported for local context only and must
never be cited as evidence that NFR is met; see `docs/agent/architecture/NFR_BASELINE_AND_VERIFICATION.md`.

**Method.** A fixed warm-up count (default 3, untimed) followed by a fixed sample count (default
20, timed via `System.Diagnostics.Stopwatch`) per interaction. `-SampleCount` is validated `>= 1`
and `-WarmupCount` is validated `>= 0` by PowerShell parameter validation, so e.g. `-SampleCount 0`
fails immediately with a clear error rather than silently reporting a meaningless "0/0 succeeded"
PASS. Percentiles use the nearest-rank method: for `P` iterations and target percentile `p`, the
reported value is the element at 1-indexed position `ceil(p/100 * P)` of the ascending-sorted
sample array, clamped to `[1, P]`. Raw per-iteration samples, plus min/median/p95/max and
success/failure counts, are printed both as human-readable text and as a machine-readable JSON
summary.

**Local-development-only boundary, applied to the actual requests made.** `-BaseUrl` is validated as
a loopback URL (`http://localhost[:port]` or `http://127.0.0.1[:port]`) before any request is made;
anything else is refused. Every request -- the health probe, warm-up requests, and measured requests
-- is additionally made with `-MaximumRedirection 0`, so an unexpected 3xx response fails the
request rather than being silently followed to wherever it points. This is local-development
tooling and must never be pointed at (or redirected to) a remote or production URL merely because
the parameter happens to be configurable.

**Authentication without an audit-event side effect, narrowly scoped.** A real login through
`/api/auth/login` always writes a `UserLoginSucceeded` business event, by design -- correct for a
real login, but not something this script should create every time it measures a baseline (and
broadly deleting "every `readonly1` login event above a boundary" afterward would risk deleting a
concurrent, genuine login by someone else). Instead the script obtains its bearer token via
`python -m tooling.smoke_data issue-test-token` (`backend/tooling/smoke_data/auth_tokens.py`), which
reuses the exact identity-lookup and token-signing code the real login route uses but never calls
that route and never writes a business event. That tool is deliberately narrow, not a general
"impersonate any user" capability:

- **no username parameter** -- it will only ever issue a token for the fixed, already-documented
  `readonly1` seed identity; an earlier version accepted an arbitrary `--username` and was
  independently reviewed as too broad, so the parameter was removed entirely rather than merely
  restricted;
- **environment-gated on an explicitly-present process-environment value, not a configuration
  default** -- it refuses to run unless `APP_ENV` is present in the process environment (read via
  `os.environ` by the tool itself) and equal to `development` or `ci`. An entirely unset `APP_ENV`
  is demonstrably rejected -- see the backend regression tests in
  `backend/tests/test_smoke_data_auth_tokens.py` and the direct CLI evidence in
  `docs/agent/technical-enablement/TE_2C_MIGRATED_FOUNDATION_VERIFICATION.md`. (When this was
  written, `app.core.config.Settings` defaulted `app_env` to `development`; since TB-1 TB1-204
  part d, 7 October 2026, the application refuses a missing `APP_ENV` too, and the tool keeps its
  own, narrower check);
- **short-lived** -- issued tokens expire in 5 minutes, not the application's normal long-lived
  session duration, since this exists only to cover one timing-baseline run;
- **not an HTTP route** -- CLI/tooling only, never reachable through the application's API surface.

**Printing contract, stated precisely.** `issue-test-token` intentionally writes exactly the
bearer token to stdout -- that is its whole purpose as a command the timing script can capture.
The timing script captures that stdout and never displays or echoes it, on the success path or on
any failure path. The underlying helper itself writes no token to stderr or to any surrounding
human-readable diagnostic text.

This is a materially different, and more scoped, trust boundary than
`backend/tooling/smoke_data/actors.py`, which resolves a username for direct in-process
service-layer calls and never produces anything replayable as an HTTP credential -- the two must not
be described as equivalent. Running the timing script repeatedly creates **zero** persistent
audit/business state -- there is nothing to clean up, and no concurrency race to reason about.
`readonly1` remains the repository's already publicly-documented local seed identity.

**Failure behaviour.** Exits non-zero if `-BaseUrl` is not a loopback URL, `-SampleCount`/`-WarmupCount`
fail parameter validation, the backend is unreachable, token issuance fails (including the
`APP_ENV` gate refusing to run), any measured request returns an unexpected non-2xx status or an
unexpected redirect, or fewer than the requested sample count succeeds for either interaction.

See `docs/agent/technical-enablement/TE_2C_MIGRATED_FOUNDATION_VERIFICATION.md` for recorded
execution evidence.

## Python validation scripts

Both use only the Python standard library. They need no database, no network and no running
application, and they behave identically on Windows, Linux and inside a container. The CI workflow
runs exactly these commands.

```bash
python scripts/validate_contract_fixtures.py
python scripts/check_tracked_secrets.py
python -m unittest discover -s scripts/tests -v
```

Exit codes: `0` pass, `1` at least one finding, `2` the check could not run.

Both enumerate the **proposed tree** with
`git ls-files --cached --others --exclude-standard`: everything committed, plus new files that are
not ignored. A file added on your working branch is checked before it is committed, while ignored
paths — `.env`, virtualenvs, caches, build output — stay out of scope entirely.

With no Python on the host, run them in a container from the repository root:

```bash
docker run --rm -v "${PWD}:/repo" -w /repo python:3.12-slim python scripts/validate_contract_fixtures.py
```

`check_tracked_secrets.py` additionally needs `git` on `PATH`, because it is defined over tracked
files; use an image that provides it, or run it on the host.

`validate_contract_fixtures.py` mechanises the checklist in
`docs/planning/HANDOFF_FIXTURE_VALIDATION_CHECKLIST.md`. It does not create fixture packs and does
not change any contract's maturity. `check_tracked_secrets.py` is a guard against committing a
credential, not a history scanner: it cannot find a secret that was committed and later removed,
it never opens an ignored path such as the local `.env`, and it reports value lengths rather than
values so a finding cannot leak the secret.

## CI-only shell script

`ci-compose-cleanup.sh` is called by the `compose-e2e` job's teardown step and is not intended for
local use. It removes every container carrying this run's exact `com.docker.compose.project` label
— including a one-off `compose run` container left behind by a cancelled step — then runs
`docker compose --profile e2e down -v --remove-orphans`, then re-checks that no container, network
or volume with that label survives. That check is bounded and repeats (up to 6 attempts, 5 seconds
apart) before failing the step, so a resource the daemon is still auto-removing is not mistaken for
permanent residue; only a survivor that is still present after every attempt fails the step.

`--profile e2e` is load-bearing. `down -v` removes named volumes only for services in scope, and
the `e2e` service is profile-gated in `docker-compose.yml`, so without the profile its
`e2e-node-modules` volume survives teardown. `down` only removes, so naming the profile never
starts the E2E container.

It fails closed on two gates, both checked before any Docker command: the project name must match
`^pbl-crm-hiring-ci-[0-9]+$`, and `GITHUB_ACTIONS` must be `true`. Anything else exits `2`, so it
cannot remove local containers, networks or retained volumes. It acts only on exact label matches
and never prunes globally.

```bash
bash scripts/ci-compose-cleanup.sh pbl-crm-hiring-ci-<run-id>
```

Its tests run the real script, so they need a working bash. On Windows, `bash` on `PATH` is often
the WSL launcher, which cannot open a Windows path; the suite probes candidates and selects Git
Bash instead. Set `CI_COMPOSE_CLEANUP_TEST_BASH` to force a specific executable.

See `docs/agent/technical-enablement/TE_2CI_GITHUB_ACTIONS_VALIDATION_FOUNDATION.md`.
