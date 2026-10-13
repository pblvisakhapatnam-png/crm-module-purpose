# TE-2CI.1 Acceptance - GitHub Actions Validation Foundation

Technical-enablement work package, not a numbered CRM business slice. No application behaviour,
API contract, database schema, Alembic revision, permission rule, business event, frontend screen,
frozen contract or source document changed.

**Scope of this record: TE-2CI.1 (repository implementation), verified locally.** It is not
evidence that the workflow runs on GitHub-hosted runners, that the required check exists, or that
branch protection is enforced. Those are TE-2CI.2 outcomes and are listed as unverified below.

**TE-2CI.1 was independently reviewed and accepted on 14 August 2026.** TE-2CI remains incomplete
until TE-2CI.2 proves hosted execution and branch-protection enforcement.

**Reconciliation, 16 August 2026.** The two paragraphs above are historical and describe this
record's original TE-2CI.1 scope. TE-2CI.2 has since been performed and TE-2CI is **complete**; its
evidence is in "TE-2CI.2 hosted evidence" later in this document. One expectation stated above was
not met on 16 August 2026, and was not met by design at that time: **branch-protection enforcement
proved impossible on the repository's GitHub plan as it then stood**, and ADR-029 records the
approved interim manual merge gate that applied in its place. TE-2C is unblocked but not started.

**Current-status note, 17 August 2026.** The plan limitation above is closed; see "Required-check
registration and branch protection" near the end of this document and ADR-031 in
`docs/agent/ARCHITECTURE_DECISIONS.md`.

Baseline commit: `75fd4fc`, branch `main`. The tree was clean and level with `origin/main` before
implementation began. Afterwards it holds only the unstaged TE-2CI.1 package changes listed below;
`HEAD` and `origin/main` were both still `75fd4fc`, and nothing was committed, staged or pushed at
that point.

**Integration.** After independent acceptance, the package was committed under project-owner
direction as `1b4d08c` and integrated on `main`. This record's verification evidence describes the
reviewed working tree, which is what acceptance was granted against.

## Files changed

```text
A  .github/workflows/te-2ci-validation.yml
A  .github/dependency-audit-known-findings.txt
A  scripts/validate_contract_fixtures.py
A  scripts/check_tracked_secrets.py
A  scripts/tests/test_validate_contract_fixtures.py
A  scripts/tests/test_check_tracked_secrets.py
M  scripts/run-e2e.ps1          (one portability change; see "Portability change" below)
M  scripts/README.md
A  docs/agent/technical-enablement/TE_2CI_GITHUB_ACTIONS_VALIDATION_FOUNDATION.md
A  docs/agent/acceptance/te-2ci-github-actions-validation-foundation-acceptance.md
A  docs/continuity/TE_2CI_GITHUB_ACTIONS_VALIDATION_FOUNDATION.md
M  (status records: PBL's internal working instructions, AGENTS.md, PLAN.md, AGENT_HANDOFF.md, FUTURE_SLICES.md,
    SKILLS_AND_TOOLS.md, TESTING_STRATEGY.md, INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md,
    NEXT_STEPS.md, and the three TE-2B records)
```

## Workflow jobs and the required check

| Job id | Display name |
| --- | --- |
| `backend-regression` | Backend regression |
| `migrations` | Empty-database migrations |
| `frontend` | Frontend build and tests |
| `contract-fixtures` | Contract fixture validation |
| `security-checks` | Secret and dependency checks |
| `compose-e2e` | Compose build, health and E2E |
| `required-validation` | Required validation |

Branch protection and rulesets match on the ordinary job name, so the required status check is
exactly:

```text
Required validation
```

The workflow display name, `TE-2CI Validation`, is not part of that identifier. Renaming or
removing the aggregate job does not bypass protection: the expected check stops being reported and
integration blocks until the protection rule is updated. A job name used as a required check must
stay unique across every workflow in the repository, because protection matches on the name alone.

## Automated checks

### Workflow static validation

```powershell
docker run --rm -v "${PWD}:/repo" -w /repo `
  rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667 `
  -verbose -color
```

Result: **0 errors**. `actionlint 1.7.12`, which bundles `shellcheck` and `pyflakes`, so the
embedded shell steps and the inline Python heredoc were linted too.

```text
verbose: Linting .github/workflows/te-2ci-validation.yml
verbose: Found 0 parse errors in 1 ms
verbose: Found total 0 errors in 140 ms
```

### Validator unit tests

```powershell
docker run --rm -v "${PWD}:/repo" -w /repo <python-3.12-with-git> `
  python -m unittest discover -s scripts/tests
```

Result: **36 tests, OK**. The suites live in `scripts/tests/` and run in CI inside the
`contract-fixtures` and `security-checks` jobs, each filtered to its own module, before the
corresponding validator runs.

Coverage, as required by the correction package:

| Behaviour under test | Where |
| --- | --- |
| An untracked, non-ignored candidate file is inspected | both suites |
| An ignored `.env` never enters the candidate set and is not read | `DiscoveryScope` |
| An ignored directory's contents are excluded | `DiscoveryScope` |
| Forbidden credential-bearing paths, incl. `.env` force-added past `.gitignore` | `ForbiddenPaths` |
| PEM block, AWS / Slack / Stripe / Google tokens, JWT | `ContentRules` |
| GitHub fine-grained `github_pat_` token | `ContentRules` |
| Credential assignment in quoted-literal and environment-file form | `ContentRules` |
| Inline-URL credential | `ContentRules` |
| Matched credential values are withheld from all output | `ValueWithholding` |
| Placeholders, negative-test literals, identifier references and the documented seed credential are accepted | `AcceptedValues` |
| Malformed fixture JSON | `MalformedAndMissing` |
| Missing frozen-pack file | `MalformedAndMissing` |
| Identity mismatch and source-line mismatch | `HandoffInvariants` |
| Invalid shell status | `HandoffInvariants` |
| Selected/excluded line violations, non-awarded selected line | `HandoffInvariants` |
| Real-shaped PAN, non-documentation URL, falsified demo-data declaration | `RealDataMarkers` |
| The actual repository passes both checks | `RealRepository` (both suites) |

The sample credentials in the secret-check suite are assembled from string fragments at runtime.
That file is itself part of the proposed tree the checker scans, so a whole literal would make the
repository fail its own gate, and excluding the path is exactly what the check forbids. Building
the values at runtime keeps the tests honest without weakening the rule — a point worth preserving
if these tests are ever extended.

### Contract-fixture validator

```powershell
docker run --rm -v "${PWD}:/repo" -w /repo <python-3.12-with-git> `
  python scripts/validate_contract_fixtures.py
```

Result: **exit 0**.

```text
Contract fixture validation: 7 candidate fixture file(s) checked
(discovered via git ls-files --cached --others --exclude-standard).
```

```text
docs/agent/fixtures/accepted-offer-work-order/accepted-commercial-offer-handoff-example.json
docs/agent/fixtures/accepted-offer-work-order/negative-invalid-line-selection-example.json
docs/agent/fixtures/accepted-offer-work-order/negative-missing-account-traceability-example.json
docs/agent/fixtures/accepted-offer-work-order/partial-award-selected-lines-example.json
docs/agent/fixtures/accepted-offer-work-order/work-order-shell-output-example.json
docs/agent/fixtures/terms-and-conditions/tc-clause-library-demo.json
docs/agent/fixtures/terms-and-conditions/tc-selection-example-commercial-offer.json
```

Every rule family is additionally proved in the failing direction by the unit suite above, which
injects one defect at a time into a temporary copy of the real pack. The repository's own fixtures
are never modified.

### Committed-credential check

```powershell
docker run --rm -v "${PWD}:/repo" -w /repo <python-3.12-with-git> `
  python scripts/check_tracked_secrets.py
```

Result: **exit 0**.

```text
Committed-credential check: 633 file(s) in the proposed tree
(git ls-files --cached --others --exclude-standard); 630 scanned as text, 3 skipped as binary
or oversized.
No committed-credential findings.
```

The count covers the committed baseline plus this package's own new files, because discovery spans
the proposed tree. The two validators and both test modules are therefore in scope and confirm they
do not report themselves.

Three genuine false positives were found and fixed during development rather than excluded by path:

| False positive | Resolution |
| --- | --- |
| `password=settings.postgres_password` in `backend/app/core/database.py` — an identifier reference, not a literal | Environment-form rule requires an upper-case name and no whitespace around `=` |
| `password = "password"` in `e2e/tests/fixtures/auth.ts` — the documented prototype seed credential, public in the repository, seeded by Alembic revision `20260629_0002` and shown on the login page | Archetypal non-secret literals accepted by value shape |
| `f'API_KEY = "{GOOGLE_API_KEY}"'` in the new tests — a format-string placeholder, not a value | Single-brace `{VAR}` added to the interpolation shapes, alongside `${VAR}`, `{{VAR}}` and `%VAR%` |

All three are value-shape or name-shape rules applied uniformly to every file in scope. No path or
directory exclusion was added.

### Dependency audit

```powershell
docker run --rm -v "${PWD}/backend:/b" -w /b python:3.12-slim `
  sh -c "pip install -q pip-audit==2.10.1 && pip-audit --strict --requirement requirements.txt"
```

Result: **11 findings across 3 packages (9 unique advisories); pip-audit exit 1.**

Re-run with the deferral list applied, exactly as the gate step does:

```text
No known vulnerabilities found, 11 ignored
GATE_EXIT=0
```

```powershell
docker run --rm -v "${PWD}/frontend:/app" -w /app node:20-alpine npm audit --omit=dev --audit-level=high
docker run --rm -v "${PWD}/e2e:/app" -w /app node:20-alpine npm audit --audit-level=high
```

Result: **`found 0 vulnerabilities`** for both workspaces.

### Backend regression

```powershell
docker compose exec -T backend pytest -q
```

Result: **253 passed in 249.95s**, matching the TE-2B baseline exactly. No test was added,
weakened, skipped or deselected by this package.

### Empty-database migration

Run against a dedicated PostgreSQL 17 container on its own Docker network, using fictional CI
credentials, so neither the developer database nor the retained `mssql-data` volume was touched.
The steps are the same ones the `migrations` job runs, including the shell parsing.

```text
--- empty-schema precondition ---
Confirmed: 0 tables in the public schema before upgrade.
--- alembic heads ---
20260713_0029 (head)
head_count=1
--- upgrade head from empty ---
INFO  [alembic.runtime.migration] Running upgrade 20260712_0028 -> 20260713_0029, work order amendment intake foundation
--- alembic current ---
20260713_0029 (head)
head=20260713_0029 current=20260713_0029
--- schema summary after upgrade ---
tables=28 alembic_version=20260713_0029 session_timezone=UTC
EMPTY_DB_MIGRATION_OK
```

Result: **exit 0**. Single head, current matches head, 28 tables, UTC session. The isolated
container and network were removed afterwards and both retained volumes were confirmed present.

### Frontend gate

```powershell
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run typecheck
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm test
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run build
```

Results: typecheck **exit 0**; tests **54 passed (1 file)**; build **succeeded** (`built in 4.21s`).
The pre-existing chunk-size advisory is unchanged and is not an error.

### Compose configuration, build and health

```powershell
docker compose --env-file <ci-style env> config --quiet
docker compose --env-file <ci-style env> build backend frontend
```

Results: config **exit 0 with no interpolation warnings**, confirming that a CI-style environment
file resolves every variable the Compose file references; both images **built**.

Health after starting the stack:

```text
http://localhost:8000/api/health -> 200
http://localhost:3000/login      -> 200
```

### Playwright E2E

```powershell
.\scripts\run-e2e.ps1
```

Result: **exit 0** — `E2E run complete: tests passed and cleanup succeeded.`
`e2e/test-results/.last-run.json` reports `{"status": "passed", "failedTests": []}`.
`retries: 0` in `e2e/playwright.config.ts` is unchanged.

All three manifests seeded and cleaned successfully (`te1-ea5e716d`, `te1-c0ee7643`,
`te1-026aeb5a`), the pre-seed `business_event` boundary was captured before seeding as designed,
and the login-audit cleanup deleted exactly the 12 login events the run created, with no residual
unlisted actor.

### Residue comparison

Row counts immediately before the E2E run and immediately after it completed:

| Table | Before | After |
| --- | --- | --- |
| `business_party` | 0 | 0 |
| `crm_opportunity` | 0 | 0 |
| `crm_commercial_offer` | 0 | 0 |
| `crm_work_order` | 0 | 0 |
| `crm_work_order_amendment` | 0 | 0 |
| `business_event` | 4 | 4 |
| `document_metadata` | 2 | 2 |

Identical. `alembic current` remained `20260713_0029 (head)` throughout.

### Repository hygiene

```powershell
git diff --check      # clean
git status --short    # M scripts/run-e2e.ps1; ?? .github/; ?? scripts/*.py (plus new docs)
git diff --cached --name-only   # empty
```

Nothing staged, nothing committed, nothing pushed. `HEAD` and `origin/main` both remain `75fd4fc`.

## Portability change

One functional change to `scripts/run-e2e.ps1`:

```powershell
# before
$manifestDir = Join-Path $repoRoot "e2e\.manifest"
# after
$manifestDir = Join-Path (Join-Path $repoRoot "e2e") ".manifest"
```

On Ubuntu a backslash is an ordinary filename character, so the original literal would have
created a file named `e2e\.manifest` rather than a directory, and every later path operation
against it would have failed. Windows behaviour is identical either way; the local E2E run above
was performed on Windows with the change in place.

Nothing else in the script changed. The E2E actor allowlist, the mandatory pre-seed boundary
capture, the residual-event reporting, the cleanup boundaries, the `finally` block and every exit
code are untouched. The remaining backslashes are inside human-readable messages quoting Windows
commands, which is correct for that audience.

## Dependency audit findings

**These are reported, not silently suppressed.** Nine pre-existing advisories are deferred by
`.github/dependency-audit-known-findings.txt`, each named individually with a justification. The
full report step in the workflow always prints them. None was introduced by TE-2CI.1.

| Advisory | Package | Pinned | Fix | Reachability in this application |
| --- | --- | --- | --- | --- |
| `PYSEC-2026-2270` | python-dotenv | 1.0.1 | 1.2.2 | Not reached. `set_key`/`unset_key` are never called; configuration is read only. |
| `PYSEC-2026-1845` | pytest | 8.3.4 | 9.0.3 | Test-time only, never shipped. |
| `PYSEC-2026-161` | starlette | 0.41.3 | 1.0.1 | Not reached. No middleware or endpoint decides authorization from `request.url`. |
| `PYSEC-2026-248` | starlette | 0.41.3 | 1.3.0 | Not reached; same reason. |
| `PYSEC-2026-249` | starlette | 0.41.3 | 1.3.1 | Limited. The API consumes JSON bodies, not urlencoded forms. |
| `PYSEC-2026-1941` | starlette | 0.41.3 | 0.47.2 | Not reached. No route accepts a file upload; document handling is metadata only. |
| `PYSEC-2026-1942` | starlette | 0.41.3 | 0.49.1 | Not reached. No `StaticFiles`, no `FileResponse`. |
| `PYSEC-2026-2280` | starlette | 0.41.3 | 1.1.0 | Not reached. No `HTTPEndpoint` class-based routes. |
| `PYSEC-2026-2281` | starlette | 0.41.3 | 1.1.0 | Not reached. No `StaticFiles`; Linux containers. |

Reachability evidence: a search of `backend/app` for `StaticFiles`, `FileResponse`,
`HTTPEndpoint`, `request.url`, `set_key`, `unset_key` and middleware registration returns only
`CORSMiddleware` in `backend/app/main.py`. No other match exists.

*Reconciled 8 October 2026 (TB-1 finding TB1-200, corrective package CS-15):* the two starlette rows
above for `PYSEC-2026-249` and `PYSEC-2026-1941` were true on 14 August 2026 and stopped being true
when Slice 9C added the document upload (8 September 2026) and ERT-1 the Plum report upload
(26 September 2026): both routes take form fields and a file, which FastAPI parses before
authentication. Both advisories are now **reached**, bounded by each route's body cap (26 MiB and
5.25 MiB); `.github/dependency-audit-known-findings.txt` carries the corrected notes. They stay
deferred to the FastAPI/Starlette upgrade, which TB-1 schedules before production. The `PYSEC-2026-1845`
row's "never shipped" was not true either: the backend image installs `requirements.txt`, test tools
included (TB-1 TB1-901). The application never runs pytest and the hosted servers never do (the UAT
runbook forbids it), so it stays not reached; its note now says so, and taking the test tools out of
the runtime image is CS-15, before production. The table above is kept as it was accepted.

**Why they are deferred rather than fixed here:** the starlette fixes require a move to the 1.x
line, which pulls FastAPI with it. That is a substantive dependency upgrade with real regression
risk, and TE-2CI.1 must not change application behaviour. It needs its own work package with its
own regression evidence.

### Reviewer disposition

**The nine named deferrals are accepted temporarily for TE-2CI.1**, so that the gate starts
meaningful rather than permanently red. The acceptance is conditional:

- the unfiltered `pip-audit` report remains a visible step in the workflow, so the real state is
  never hidden behind the deferral list;
- every new or unlisted advisory remains blocking;
- **this is not production acceptance** of the underlying risk;
- **TE-2C must carry this residual risk explicitly** in its own record rather than inheriting it
  silently; and
- remediation, or a fresh reassessment, is **required before the final production-candidate
  gate**.

The deferral list is reviewed again in the dependency-upgrade package and on every TE-2C run.

## Local environment incident during verification

Recorded because it affected the developer machine and the reviewer should know what happened.

While running the Compose verification steps, `docker compose` commands recreated the running
containers. The repository's local `.env` predates TE-2B: it still carries `MSSQL_*` variables and
has no `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` / `DATABASE_URL` entries, which is
why Compose emits "variable is not set" warnings for every PostgreSQL interpolation. The recreated
backend therefore fell back to the defaults in `backend/app/core/config.py`, and those did not
match the password stored in the existing PostgreSQL volume, so the backend exited on startup with
`password authentication failed for user "pbl_app"`.

Investigation confirmed the data was never at risk: `pbl-crm-hiring_postgres-data` remained
attached with the `pbl_crm_hiring` database, 28 tables and `pbl_app` as owner, and
`pbl-crm-hiring_mssql-data` was untouched throughout. `pg_hba.conf` shows
`host all all 127.0.0.1/32 trust`, so a password test from inside the container proves nothing
about the stored credential; the stored password was not discovered and no attempt was made to
read `.env`.

With the project owner's explicit choice, the role password was reset to the documented
development default from `.env.example` / `config.py` through the container's local trust socket:

```powershell
docker exec pbl-crm-hiring-db-1 psql -U pbl_app -d postgres -c "ALTER USER pbl_app PASSWORD '<documented default>'"
docker compose up -d backend
```

The backend then returned `200` from `/api/health`. The three manifests seeded by the interrupted
run were cleaned up through `cleanup --manifest`, restoring the exact pre-run baseline
(`business_event` 4, `document_metadata` 2, all business tables 0) before the successful E2E run
reported above.

Two follow-ups for the project owner, neither of them TE-2CI work:

1. The local `.env` should be brought up to date with `.env.example` so the PostgreSQL settings
   are explicit rather than relying on `config.py` defaults, and so Compose stops warning.
2. `backend/.smoke-runs/` lives inside the backend container and is not bind-mounted, so
   recreating the container discards the local run manifests and `cleanup --run-id` can no longer
   find them. The host copies under `e2e/.manifest/` made recovery possible via
   `cleanup --manifest`. Worth considering a bind mount, or documenting the recovery path, in a
   future TE-1 tooling change.

## Not verified - hosted-only behaviour

These cannot be established from a working tree and are TE-2CI.2's scope:

- the workflow has never executed on a GitHub-hosted runner; service-container networking, runner
  tool availability, cache behaviour, action resolution at the pinned SHAs and wall-clock timings
  are all unconfirmed;
- the required check `Required validation` does not exist yet, because a check
  name only becomes selectable after the workflow has run once on the default branch;
- branch protection is not configured, so protected integration is not enforced today;
- `pwsh` availability on `ubuntu-latest` is documented runner behaviour, not something verified
  here;
- the `timeout-minutes` values are first estimates and should be re-tuned against real timings;
- artifact upload and 14-day retention behaviour has not been observed on a real failing run.

The exact TE-2CI.2 sequence is in the "TE-2CI.2 - hosted validation and branch protection" section
of `docs/agent/technical-enablement/TE_2CI_GITHUB_ACTIONS_VALIDATION_FOUNDATION.md`.

## TE-2CI.2 hosted finding: incomplete Compose cleanup after a cancelled run

**Status when this finding was recorded: corrected in the repository by TE-2CI.2-C1; hosted
revalidation pending. TE-2CI.2 is not complete and TE-2C remains blocked.**

**Status now, 16 August 2026: closed.** C1 is integrated as `70f3c23` and hosted-proven by the
controlled cancellation on run `31930125170` attempt 2. TE-2CI.2 and TE-2CI are complete and TE-2C
is unblocked; see "TE-2CI.2 hosted evidence" below.

### What was observed

During the controlled cancellation of hosted run
`<PBL's internal repository>/actions/runs/31865333180`, job `94968525849`,
Playwright was cancelled while running. The `Tear down the stack` step ran under `if: always()`,
**reported success**, and removed the frontend, backend and database containers together with the
PostgreSQL volume. Its log then recorded:

```text
Network pbl-crm-hiring_default  Resource is still in use
```

The cancelled `docker compose --profile e2e run --rm e2e` process left its one-off E2E container
attached long enough to prevent the project network being removed, and `docker compose down -v
--remove-orphans` exited `0` anyway.

### Why it mattered

GitHub's disposable runner removes the leftover itself, so nothing accumulated on the hosted
runner and no validation result was wrong. The defect was in the **guarantee**: the workflow and
the technical document both stated that a cancelled run leaves no containers or volumes behind on
a reused or self-hosted runner. That claim was not established, and a teardown that reports
success while leaving a resource behind cannot establish it.

### What was changed

- The `compose-e2e` job now sets a CI-only, job-scoped
  `COMPOSE_PROJECT_NAME: pbl-crm-hiring-ci-${{ github.run_id }}`, so teardown can target this
  run's resources by exact `com.docker.compose.project` label instead of the directory-derived
  default, which on a runner is the same `pbl-crm-hiring` used locally. `github.run_attempt` is
  deliberately excluded: a per-attempt label would let a rerun pass while the previous attempt's
  residue sat under a label nothing looks for again. The job therefore runs the same cleanup
  **before** starting the stack as well as after it, so a rerun on a reused runner removes the
  earlier attempt's residue or fails loudly.
- `scripts/ci-compose-cleanup.sh` force-removes every container carrying that exact label — the
  one-off `compose run` container included — then runs `docker compose down -v --remove-orphans`,
  then re-queries containers, networks and volumes by the same label and **fails the step** with
  label-scoped diagnostics if any residue remains. A `docker rm` failure caused by a `--rm`
  container removing itself between discovery and removal is tolerated with a warning rather than
  aborting the script under `set -e`; verification still decides the outcome, so a container that
  genuinely survives removal still fails the step.
- The helper fails closed on two independent gates, both before any Docker command: the project
  name must match `^pbl-crm-hiring-ci-[0-9]+$` exactly (a prefix test alone accepted the bare
  prefix and any hand-typed suffix), and `GITHUB_ACTIONS` must be `true`. It never prunes globally
  and never names a resource explicitly.

Nothing else changed. Triggers, `permissions: contents: read`, concurrency, pinned action SHAs,
job names, `Required validation`, timeouts, `retries: 0`, artifact behaviour and every validation
command are unchanged, and no application code, schema, migration, contract or Playwright scenario
was touched.

### Review pass on the first draft of this correction

An independent review of the first draft of TE-2CI.2-C1 (before any of it had been verified
against this section's checks) found five further issues, all addressed here rather than in a
separate document:

1. **The project label included `github.run_attempt`.** On a reused runner, a rerun would get a
   fresh label while the previous attempt's residue sat under the old one, findable by nothing.
   Fixed as described above: `run_id` only, plus the explicit pre-run cleanup step.
2. **`docker rm --force` failing under `set -e` for a container mid-self-removal aborted the
   script before teardown or verification ran**, turning a harmless race into a failed step that
   also skipped the cleanup still owed. Fixed as described above: the failure is tolerated with a
   warning, and verification decides the outcome.
3. **The fail-closed guard used a prefix test**, which accepted the bare prefix
   `pbl-crm-hiring-ci-` and any hand-typed suffix and went on to issue Docker commands — confirmed
   directly against the pre-fix script. Fixed with the anchored `^pbl-crm-hiring-ci-[0-9]+$`
   pattern plus the independent `GITHUB_ACTIONS=true` gate.
4. **`scripts/tests/test_ci_compose_cleanup.py` was not wired into any workflow job**, so a future
   change that widened the project-name pattern or dropped the `GITHUB_ACTIONS` gate would pass
   CI silently — the same principle the workflow already states for its sibling validators
   ("a validator that has only ever been seen to pass is not evidence of anything") applied with
   more force here, since this script force-removes Docker resources. Fixed by adding a
   `security-checks` step: `python -m unittest discover -s scripts/tests -p
   "test_ci_compose_cleanup.py" -v`.
5. **Verification queried residue exactly once**, immediately after `down`. A container still in
   `Removal In Progress` — precisely the cancellation scenario this correction exists to prove —
   can still appear in `docker ps --all` for a moment after `down` has already logged its own
   "Resource is still in use" for the network it was holding, which would have failed the step on
   residue that was actually clearing itself. Fixed with a bounded re-check: up to 6 attempts,
   5 seconds apart in production (overridable only for the test suite, via
   `CI_COMPOSE_CLEANUP_POLL_SECONDS`), breaking as soon as nothing remains. The diagnostics and
   final `exit 1` on genuine residue are unchanged; a fixture that clears on the second poll and
   one that never clears both have dedicated tests.

A sixth, unrelated finding from the same review pass is recorded separately in "TE-2CI.2 hosted
finding" below the reviewer checklist: **the pre-run cleanup step originally ran before Compose
config validation**, so a broken `docker-compose.yml` would fail under the cleanup step's name
instead of the validation step's. Fixed by reordering; validation now runs first.

Also from that review: **the repository's first `.sh` file had no `.gitattributes` rule.** Every
other scripted extension (`.py`, `.ts`, `.md`, `.sql`, `.yml`) has an explicit `eol=lf` rule; `.sh`
fell through to `text=auto` with an unspecified line ending, and `core.autocrlf=true` on this
machine would materialise a CRLF copy on a fresh Windows checkout. Tested directly: a CRLF copy
still ran correctly under Git Bash's MSYS bash (both the reject and accept paths), and the Linux
runner checks out LF regardless of local settings, so nothing was actually broken by this gap —
but a genuine (non-MSYS) bash, such as under WSL, does not tolerate CRLF, so a WSL user on a
Windows checkout could have hit it. Closed with `*.sh text eol=lf`.

### Verification performed for the correction

| Check | Result |
| --- | --- |
| `actionlint` 1.7.12, digest-pinned (bundles shellcheck/pyflakes) | 0 errors |
| `shellcheck --shell=bash scripts/ci-compose-cleanup.sh`, same pinned image | 0 findings |
| New focused tests `scripts/tests/test_ci_compose_cleanup.py` | 20 passed |
| Full `python -m unittest discover -s scripts/tests` | 56 passed (36 pre-existing + 20 new) |
| Bash-candidate probe on Windows | `C:\WINDOWS\system32\bash.exe` (WSL launcher, what `shutil.which` returns here) rejected; both Git Bash locations accepted |
| `python scripts/validate_contract_fixtures.py` | 7 fixtures checked, all rules pass |
| `python scripts/check_tracked_secrets.py` | 635 files in the proposed tree, no findings |
| Fail-closed guard against the real local project, real Docker on `PATH` | Refused `pbl-crm-hiring`, the bare prefix `pbl-crm-hiring-ci-`, and a valid-shaped name outside `GITHUB_ACTIONS`, each with exit `2` and no Docker command issued |
| Local stack and volumes after that guard test | `db`/`backend`/`frontend` still up; `postgres-data`, `e2e-node-modules` and the retained `mssql-data` volume all intact |
| `git diff --check` | Clean |

The focused tests place a fake `docker` first on `PATH` and assert on the exact commands issued:
that removal precedes `down`, that `docker rm` is never invoked with an empty argument list, that
every query is scoped to the exact project label, that no call contains `prune` or `system`, that
surviving containers, networks or volumes each fail the step, that a container vanishing between
discovery and removal does not stop teardown while a genuinely surviving one still fails, that a
network still settling clears within the bounded re-check window (asserted by counting the exact
number of poll queries, not just the final result) while a permanently stuck one exhausts all 6
attempts and still fails, and that every out-of-scope input issues no Docker command at all — the
bare prefix, a non-numeric run id, a trailing attempt suffix, the local project name, a malformed
name, and a missing or non-`true` `GITHUB_ACTIONS`. The suite forces the poll interval to `0` so
the 6-attempt exhaustion case runs in under two seconds rather than 25.

The suite selects bash by probing each candidate against the real script rather than trusting
`shutil.which("bash")`, which on Windows resolves to the WSL launcher
`C:\WINDOWS\system32\bash.exe`; that binary starts but cannot open a Windows path, so an
existence check passed while every test failed for an unrelated reason. Probing rejects it and
selects Git Bash instead. `CI_COMPOSE_CLEANUP_TEST_BASH` forces a specific executable, and the
suite skips only when no candidate works.

Full backend, frontend and E2E regression was not run and was not required: this correction
changes only the workflow's teardown step, a new CI-only shell script and its tests.

### Still pending

- **A controlled hosted cancellation has not yet been repeated against the corrected workflow.**
  Until it is, the "a cancelled run leaves no containers, networks or volumes behind" guarantee
  remains asserted-and-tested rather than hosted-proven.
- The hosted evidence already gathered for the aggregate check, artifact retention and teardown
  behaviour is recorded in the TE-2CI.2 reconciliation, not here. TE-2CI.2 is **not** marked
  complete by this correction, no ADR-029 is created, and the manual merge gate is not claimed to
  be active.

**Update, 16 August 2026.** Correction TE-2CI.2-C1 was independently accepted, committed as
`70f3c23` and pushed. The next hosted run then found a second, unrelated teardown defect, recorded
in the section below. The "still pending" items above remain accurate and are superseded only in
sequencing: the controlled hosted cancellation now waits behind an ordinary hosted run with a
successful teardown.

## TE-2CI.2 hosted finding 2: profile-gated E2E volume survives teardown

**Status when this finding was recorded: corrected in the repository by TE-2CI.2-C2; hosted
revalidation pending. TE-2CI.2 is not complete and TE-2C remains blocked.**

**Status now, 16 August 2026: closed.** C2 is integrated as `8bb6af1` and hosted-proven by the
green teardown on run `31930125170` attempt 1. TE-2CI.2 and TE-2CI are complete and TE-2C is
unblocked; see "TE-2CI.2 hosted evidence" below.

### What was observed

Hosted run `<PBL's internal repository>/actions/runs/31871165805`, the first run
after correction TE-2CI.2-C1 was integrated as `70f3c23`, **passed every substantive check**:

| Job | Result |
| --- | --- |
| Backend regression | Passed |
| Empty-database migrations | Passed |
| Frontend build and tests | Passed |
| Contract fixture validation | Passed |
| Secret and dependency checks | Passed |
| Compose build, health and Playwright | Suite passed, 12 passed / 9 skipped |

The `compose-e2e` job then **failed at the teardown step**, because one resource survived and the
verification loop correctly refused to report success:

```text
pbl-crm-hiring-ci-31871165805_e2e-node-modules
```

### Why it happened

`docker compose down -v` removes named volumes only for services that are **in scope**. The `e2e`
service is gated behind the Compose `e2e` profile in `docker-compose.yml`, so with the profile
inactive it is out of scope and its `e2e-node-modules` volume is never considered. `postgres-data`,
owned by the always-active `db` service, was removed normally — which is why only one volume
survived.

Two observations worth keeping, because both are the C1 design working rather than failing:

- **C1's verification step is what caught this.** Before C1 the teardown would have exited `0` and
  left the volume behind silently on every run. The job failed loudly instead.
- **The failure was confined to teardown.** Run `31871165805` is genuine hosted evidence that the
  workflow triggers, that all six validation jobs execute on hosted runners, and that the whole
  Compose build/health/Playwright path passes there. That evidence stands.

### What was changed

Teardown in `scripts/ci-compose-cleanup.sh` now runs:

```bash
docker compose --profile e2e down -v --remove-orphans
```

`down` only removes, so naming the profile never starts the E2E container. Nothing else in the
helper changed: the two fail-closed gates, exact-label discovery, the `docker rm` race tolerance,
the bounded settle re-check and the final residue failure are all preserved unmodified. No workflow
trigger, permission, action SHA, job name, timeout, retry setting, artifact behaviour or the
`Required validation` aggregation was touched, and no application code, schema, migration, contract
or Playwright scenario was changed.

### Verification performed for the correction

| Check | Result |
| --- | --- |
| Focused tests `scripts/tests/test_ci_compose_cleanup.py` | 22 passed (20 pre-existing + 2 new) |
| Full `python -m unittest discover -s scripts/tests` | 58 passed (36 + 22) |
| `python scripts/validate_contract_fixtures.py` | 7 fixtures checked, all rules pass |
| `python scripts/check_tracked_secrets.py` | 635 files in the proposed tree, no findings |
| `actionlint` 1.7.12, digest-pinned | 0 errors |
| `shellcheck --shell=bash scripts/ci-compose-cleanup.sh`, same pinned image | 0 findings |
| `git diff --check` | Clean |
| Mutation check: `--profile e2e` removed from the script | 4 tests fail, including the residue-exit-code assertion — the suite detects the regression rather than asserting a string |
| Isolated real-Docker reproduction and proof | See below |

The two new tests are behavioural, not string comparisons. The fake `docker compose down` models
the real profile rule, so dropping `--profile e2e` leaves the volume behind, verification reports
residue and the test fails on the exit code. A second test drives the fake directly to prove the
gate really gates, so the first cannot pass vacuously.

### Isolated real-Docker evidence

Performed against a throwaway project named to match the helper's required shape,
`pbl-crm-hiring-ci-99000001`, created with e2e-profile resources only (`db` and `e2e` via
`up --no-start --no-deps`, so no image build and nothing started):

| Step | Result |
| --- | --- |
| Created | 2 containers, 1 network, 2 volumes including `pbl-crm-hiring-ci-99000001_e2e-node-modules` |
| Old command, `docker compose down -v --remove-orphans` (no profile) | Exited `0`, removed `postgres-data` and the network, **left the E2E container and `e2e-node-modules` behind** — the hosted defect reproduced locally |
| Corrected helper, `GITHUB_ACTIONS=true bash scripts/ci-compose-cleanup.sh pbl-crm-hiring-ci-99000001` | Force-removed 2 containers, ran the profile-aware `down`, removed the network and **both** named volumes, reported no residue, exit `0` |
| Throwaway project after | No container, network or volume carries its label |
| Local `pbl-crm-hiring` project after | `db`/`backend`/`frontend` still up, unchanged from the baseline captured before the proof |
| Local volumes after | `pbl-crm-hiring_postgres-data`, `pbl-crm-hiring_e2e-node-modules` and the retained `pbl-crm-hiring_mssql-data` all intact |

Full backend, frontend and E2E regression was not run and was not required: this correction changes
one command in a CI-only shell script, that script's tests, and documentation.

An unrelated local observation, recorded so it is not rediscovered as a defect: `docker compose`
run from this Windows development machine emits `POSTGRES_* variable is not set` interpolation
warnings whether or not the helper is involved. It is pre-existing, is not caused by this change,
does not affect teardown, and does not occur with the `.env` the workflow generates on the runner.

### Still pending, as recorded when C2 was prepared

- **An ordinary hosted run ending in a successful teardown.** This is the immediate next step and
  proves C2.
- **A controlled hosted cancellation**, after that run, proving C1's guarantee end to end. It is
  deliberately not attempted first: a cancellation cannot demonstrate a clean teardown while an
  ordinary run has not yet done so.
- Required-check registration and branch protection enforcement.
- TE-2CI.2 is **not** complete, TE-2CI is **not** complete, TE-2C remains blocked, no ADR-029 is
  created, and the manual merge gate is not claimed to be active.

**Reconciliation, 16 August 2026.** The list above is historical. C2 was committed as `8bb6af1`,
both hosted runs were performed, and the results are recorded in "TE-2CI.2 hosted evidence" below.
Required-check registration and branch protection turned out to be unavailable on the repository's
current GitHub plan and are replaced by the ADR-029 manual merge gate. TE-2CI.2 and TE-2CI are now
complete, and TE-2C is unblocked but not started.

### Reviewer checklist for TE-2CI.2-C2

The independent local review accepted the implementation and repository-record criteria below.
The final box was completed on 16 August 2026 against the hosted evidence recorded in the next
section.

```text
[x] Teardown activates the e2e profile and the command is exactly
    docker compose --profile e2e down -v --remove-orphans.
[x] Both fail-closed gates (project-name shape, GITHUB_ACTIONS) are unchanged and still tested.
[x] Exact-label discovery, the docker rm race tolerance, the bounded settle re-check and the
    final residue failure are all preserved and still tested.
[x] No global Docker pruning or cleanup was introduced.
[x] The new tests fail when the profile flag is removed, and cannot pass vacuously.
[x] Workflow triggers, permissions, action SHAs, job names, timeouts, retries, artifact behaviour
    and Required validation aggregation are unchanged.
[x] No application code, schema, migration, contract or Playwright scenario changed.
[x] The current records state TE-2CI.2 is in progress, and neither TE-2CI.2 nor TE-2C is
    marked complete.
[x] Independent review accepts the corrected hosted evidence.
```

The last box was ticked on 16 August 2026 against run `31930125170` at commit `8bb6af1`. The
box above it recorded the correct repository state at the time it was ticked; the records have
since moved on, as the reconciliation note in this section explains.

## TE-2CI.2 hosted evidence

**Status: TE-2CI.2 and TE-2CI are COMPLETE. TE-2C is UNBLOCKED and NOT STARTED.**

### Evidence 0 — controlled failure, scratch branch (`te-2ci2-failure-proof`)

Before the teardown corrections, a scratch branch (`te-2ci2-failure-proof`, PR #1) carried an
intentionally failing Playwright spec, to prove the workflow detects and reports a real failure
correctly rather than only a cancellation. Hosted run `31865333180` showed:

- the `compose-e2e` job **failed**, on the intentional Playwright assertion failure;
- `Required validation` reported **failure** — correctly, not skipped;
- `playwright-failure-artifacts` was uploaded, with 14-day retention.

This is **TE-2CI.2 hosted evidence**, performed for real on a hosted runner, not a local
simulation. It is a separate finding from the C1 cancellation defect recorded on the same run
number (a different attempt, exercising a different condition — cancellation, not assertion
failure); see "TE-2CI.2 hosted finding: incomplete Compose cleanup after a cancelled run" earlier
in this document.

Evidence 1 and 2 below are from commit `8bb6af127d857d67c3097893d69a143697f7f84f` on `main`,
workflow run `<PBL's internal repository>/actions/runs/31930125170`.

### Evidence 1 — ordinary hosted run (attempt 1)

Overall workflow result: **success**, about 3m 26s total.

| Job | Result | Approximate duration |
| --- | --- | --- |
| Backend regression | success | 3m 16s |
| Empty-database migrations | success | 44s |
| Frontend build and tests | success | 34s |
| Contract fixture validation | success | 5s |
| Secret and dependency checks | success | 44s |
| Compose build, health and E2E | success | 2m 10s |
| **Required validation** | **success** | 4s |

- Playwright: **12 passed / 9 skipped / 0 failed**, `retries: 0` unchanged — identical to the local
  counts, so the hosted environment introduced no flakiness and none was hidden by a retry.
- Teardown ran `docker compose --profile e2e down -v --remove-orphans`.
- `postgres-data` removed; `e2e-node-modules` removed; project network removed.
- Final message: `no container, network or volume remains for 'pbl-crm-hiring-ci-31930125170'`.
- No teardown residue warning.

**This proves correction TE-2CI.2-C2.** The profile-gated volume that survived run `31871165805` is
now removed.

**Timings.** The existing 45-minute `compose-e2e` timeout is comfortably sufficient against an
observed 2m 10s. No timeout retuning is required, closing the item TE-2CI.1 recorded as a first
estimate.

### Evidence 2 — controlled cancellation (attempt 2)

`<PBL's internal repository>/actions/runs/31930125170/attempts/2`

Cancelled deliberately at the point that exercises the C1 defect: Compose build, start and health
complete; Playwright actively running; `Tear down the stack` not yet begun.

| Observation | Result |
| --- | --- |
| Playwright step | cancelled, as intended |
| Compose job | cancelled, as intended |
| `Tear down the stack` | ran under `if: always()` and **succeeded** |
| Project-labelled containers | 3 force-removed |
| `pbl-crm-hiring-ci-31930125170_postgres-data` | removed |
| `pbl-crm-hiring-ci-31930125170_e2e-node-modules` | removed |
| `pbl-crm-hiring-ci-31930125170_default` network | removed |
| Final message | `no container, network or volume remains for 'pbl-crm-hiring-ci-31930125170'` |
| `Resource is still in use` or residual report | none |
| **Required validation** | **failure**, correctly reflecting the cancelled dependency |

**This proves correction TE-2CI.2-C1.** The original defect was a cancelled run whose teardown
reported success while leaving the project network attached. At the same cancellation point,
nothing is left behind and the step says so.

### The aggregate check, demonstrated both ways

`Required validation` has now been shown on hosted runners to report **failure** on a real
assertion failure (Evidence 0, run `31865333180`), **success** when every dependency succeeds
(Evidence 1, attempt 1) and **failure** when a dependency is cancelled (Evidence 2, attempt 2).
Together with the TE-2CI.1 local evidence that a skipped dependency also fails the aggregate, the
check cannot pass while any dependency has not genuinely succeeded — proven for every failure mode
that matters: assertion failure, cancellation and skip.

The controlled-failure evidence for Playwright failure artifacts and their 14-day retention is
Evidence 0 above, hosted on run `31865333180`. It remains valid and was not re-exercised on
`31930125170`, because neither C1 nor C2 touched artifact behaviour.

### Required-check registration and branch protection: not possible on the plan as it stood on 16 August 2026 (historical)

At the time this acceptance was recorded, the repository's GitHub plan did not permit the required
branch-protection configuration. `Required validation` therefore **existed and behaved correctly,
but was not registered as a required check, and no branch protection was enforced**. Nothing in the
repository technically prevented a push to `main` that had not passed it.

This was recorded as **ADR-029**, which established an approved interim manual merge gate providing
the closest practical control: branch and pull request, branch current with `main`,
`Required validation` succeeding for the exact commit proposed for merge, recorded independent
review, and explicit project-owner confirmation before merge. A failed, cancelled, skipped or
missing check blocked the merge. Direct pushes to `main` were prohibited except under a documented,
approved emergency exception. ADR-029 called for the GitHub plan and enforcement options to be
reassessed before production.

The manual gate was an interim process control, not equivalent to technical enforcement, and no
record was permitted to describe integration as protected or enforced while it was what stood.

**Current-status note, 17 August 2026.** That reassessment happened: the repository owner upgraded
to GitHub Pro and activated a repository ruleset (id `20939060`) on `main`; its configuration — a
pull-request requirement, `Required validation` required, branch currency, no force
pushes/deletion and resolved review conversations — was independently inspected through the GitHub
API on 17 August 2026. This is recorded as **ADR-031**, which supersedes ADR-029 for the current
enforcement mechanism. ADR-029 is not withdrawn — it remains the accurate historical record of the
interim gate that applied while the hosted evidence in this document was gathered. Confirming the
ruleset's configuration closes the plan limitation; it is not, by itself, end-to-end behavioral
proof that the protected integration path rejects a non-compliant change in practice — that
verification remains an explicit TE-2C evidence item. Current guidance about how integration is
controlled must now follow ADR-031. See `docs/agent/ARCHITECTURE_DECISIONS.md`.

### What this completion does and does not mean

- TE-2CI.2 is complete; TE-2CI is complete.
- The ADR-029 manual merge gate was active from this decision until 17 August 2026, when it was
  superseded by the ADR-031 technically-enforced gate; see the current-status note above.
- TE-2C (migrated-foundation verification) is **unblocked** under ADR-025. It has **not started**.
- This is **not** production readiness or deployment readiness. No deployment workflow, environment,
  production secret or deployment step exists, and none is authorized by this record.
- The nine deferred Python dependency advisories remain open and still need their own
  dependency-upgrade package before the final production-candidate gate.

## Explicitly out of scope and confirmed unchanged

- No `CF-0` … `CF-4B` fixture pack was created, and no `APPROVED` contract was promoted to
  `FROZEN`.
- No deployment workflow, environment, production secret or deployment step was created.
- `docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` is unchanged, as is the
  Slice 6O.1 related-offer contract.
- No application behaviour, API, schema, migration, permission, business event or frontend screen
  changed.

## Reviewer checklist

This checklist covers **TE-2CI.1 only**. It was written while that package was still awaiting
review, which is why its original wording said the final acceptance box was deliberately left
unticked.

**Reconciliation, 16 August 2026.** That wording is now historical. The independent reviewer
subsequently accepted TE-2CI.1, and every box below — including the final acceptance box — was
ticked by the reviewer at that point; the package was committed as `1b4d08c` and integrated. The
boxes are therefore correctly ticked, and the sentence above is preserved as a record of the
checklist's state before review rather than as a current instruction. The still-open acceptance box
for the current work is in the TE-2CI.2-C2 checklist above, not here.

```text
[x] The required status check is recorded as the job name "Required validation", with the
    uniqueness requirement and the block-on-missing-check consequence stated.
[x] Every actions/checkout step sets persist-credentials: false, and contents: read is unchanged.
[x] Both validators enumerate the proposed tree and still exclude ignored paths.
[x] Both validators have standard-library unittest cover, run in CI before the validator itself.
[x] Issued-token detection includes GitHub fine-grained github_pat_ tokens.
[x] Local tooling evidence uses a digest-pinned actionlint image.
[x] The nine deferred dependency advisories are accepted temporarily, with the conditions and the
    TE-2C residual-risk requirement recorded.
[x] Workflow triggers, permissions, concurrency and timeouts are appropriate.
[x] Action pins are immutable SHAs and the recorded release versions match.
[x] The aggregate job cannot pass while any dependency fails, is cancelled or is skipped.
[x] The contract-fixture rules match the documented handoff checklist and add no new contract rule.
[x] The credential-check rules contain no path exclusion, and the value-shape rules are acceptable.
[x] The run-e2e.ps1 portability change preserves Windows behaviour and every safeguard.
[x] Local verification evidence is sufficient for the parts that can be verified locally.
[x] TE-2CI remains incomplete and TE-2C remains blocked until TE-2CI.2 is recorded.
[x] Independent review accepts the package.
```
