# TE-2CI - GitHub Actions Validation Foundation

## Status

**TE-2CI is COMPLETE.** Both parts are implemented, independently accepted and hosted-verified at
commit `8bb6af1`.

TE-2CI was deliberately split into two parts, because roughly half of what the package must prove
cannot be proved from a working tree:

| Part | Scope | Status |
| --- | --- | --- |
| TE-2CI.1 | Workflow, validation tooling, portability changes and documentation, verified locally | **Complete.** Independently accepted; integrated as `1b4d08c` |
| TE-2CI.2 | Hosted execution on GitHub-hosted runners, required-check behaviour and integration control | **Complete.** Hosted-verified at `8bb6af1`; enforced branch protection was unavailable on the plan at the time and replaced by the ADR-029 manual merge gate (see current-status note below) |

Two teardown defects were found on hosted runs during TE-2CI.2 and corrected: C1 (project-scoped,
deterministic teardown) integrated as `70f3c23`, and C2 (profile-aware teardown) integrated as
`8bb6af1`. Both corrections are now hosted-proven. See "Hosted evidence" below and "Teardown"
further down.

**One thing this package did not deliver at the time it was accepted.** Required-status-check
registration and enforced branch protection **could not be enabled on the repository's GitHub plan
as it stood on 16 August 2026**. Nothing in the repository technically prevented a push to `main`
that had not passed `Required validation`. ADR-029 records the approved interim manual merge gate
that provided the closest practical control at that time, and the reassessment it called for before
production.

**Current-status note, 17 August 2026.** The plan/configuration limitation described above is
closed. The repository owner upgraded to GitHub Pro and activated a repository ruleset
(id `20939060`) on `main`; its configuration — a pull-request requirement, `Required validation`
required, branch currency, no force pushes/deletion and resolved review conversations — was
independently inspected through the GitHub API on 17 August 2026 and is recorded as **ADR-031**,
which supersedes ADR-029 for the current enforcement mechanism. This closes the plan/configuration
limitation ADR-029 recorded; **it is not, by itself, end-to-end behavioral proof that the protected
integration path works as intended in practice.** TE-2CI remains complete under its historical
acceptance basis recorded in this document; end-to-end behavioral verification of the ruleset
against a real pull request — for example, confirming a non-compliant push or PR is genuinely
rejected — remains an explicit TE-2C evidence item, per `PRODUCTION_READINESS_GATES.md`. The first
real protected pull request performed after ADR-031 may supply preliminary operational evidence for
that verification, but it does not retroactively alter the historical TE-2CI.2 hosted evidence
recorded below, which was gathered under the ADR-029 interim gate and describes that period
accurately. ADR-029 remains the accurate historical record of the interim control that applied
while that evidence was gathered. See `docs/agent/ARCHITECTURE_DECISIONS.md` (ADR-031). The hosted
evidence, defect findings and 16 August status statements below are preserved as written and
describe the state at that time, not
the current enforcement mechanism.

TE-2C (migrated-foundation verification) is **unblocked** by this completion, per ADR-025. It has
**not started**. Neither TE-2CI's completion nor its hosted evidence is production readiness or
deployment readiness, and neither may be cited as such.

## Hosted evidence

### Evidence 0 — controlled failure, scratch branch (`te-2ci2-failure-proof`)

Before the teardown corrections, a scratch branch (`te-2ci2-failure-proof`, PR #1) carried an
intentionally failing Playwright spec, to prove the workflow detects and reports a real failure
correctly rather than only a cancellation. Hosted run `31865333180` showed:

- the `compose-e2e` job failed, on the intentional Playwright assertion failure;
- `Required validation` reported **failure** — correctly, not skipped;
- `playwright-failure-artifacts` was uploaded, with 14-day retention.

This is **TE-2CI.2 hosted evidence**, not a local simulation: the deliberately broken run this
package's local verification could only simulate through `toJSON(needs)` was performed for real on
a hosted runner. It stands separately from the C1 cancellation finding on the same run number,
which is a different attempt exercising a different condition (cancellation, not assertion
failure); see "Teardown" further down for that finding.

The remaining evidence below is from commit `8bb6af1` on `main`, workflow run
`<PBL's internal repository>/actions/runs/31930125170`.

### Ordinary run — attempt 1

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

Playwright: 12 passed / 9 skipped / 0 failed, with `retries: 0` unchanged — the same counts as the
local run, so the hosted environment introduced no flakiness and none was masked by a retry.

Teardown ran `docker compose --profile e2e down -v --remove-orphans` and removed `postgres-data`,
`e2e-node-modules` and the project network, ending with:

```text
no container, network or volume remains for 'pbl-crm-hiring-ci-31930125170'
```

No residue warning. **This proves correction TE-2CI.2-C2**: the profile-gated volume that survived
run `31871165805` is now removed.

Timings: the `compose-e2e` job's existing 45-minute timeout is comfortably sufficient against an
observed 2m 10s. No timeout retuning is required, which closes the timing item TE-2CI.1 left open
as a first estimate.

### Controlled cancellation — attempt 2

Same run, `.../runs/31930125170/attempts/2`. The run was cancelled deliberately at the point that
exercises the C1 defect: Compose build, start and health had completed, Playwright was actively
running, and `Tear down the stack` had not yet begun.

| Observation | Result |
| --- | --- |
| Playwright step | cancelled, as intended |
| Compose job | cancelled, as intended |
| `Tear down the stack` | ran under `if: always()` and **succeeded** |
| Project-labelled containers | 3 force-removed |
| `..._postgres-data` | removed |
| `..._e2e-node-modules` | removed |
| `..._default` network | removed |
| Final message | `no container, network or volume remains for 'pbl-crm-hiring-ci-31930125170'` |
| `Resource is still in use` / residual report | none |
| **Required validation** | **failure**, correctly reflecting the cancelled dependency |

**This proves correction TE-2CI.2-C1.** The original defect was a cancelled run whose teardown
reported success while leaving the project network attached; here the same cancellation point
leaves nothing behind, and says so.

### What the aggregate check has now demonstrated

`Required validation` has been shown to behave correctly in both directions on hosted runners:
**success** when every dependency succeeds (attempt 1), and **failure** when a dependency is
cancelled (attempt 2). Combined with the TE-2CI.1 evidence that a skipped dependency also fails the
aggregate, the check cannot pass while any dependency has not genuinely succeeded.

The controlled-failure evidence for Playwright failure artifacts and their 14-day retention is
**TE-2CI.2 hosted evidence** (Evidence 0 above, run `31865333180`), not a TE-2CI.1 local claim. It
remains valid and was not re-exercised on run `31930125170`, because nothing in C1 or C2 touched
artifact behaviour.

Technical-enablement work package, not a numbered CRM business slice.

## Objective

Create the repository-side continuous-integration validation foundation required by ADR-021
(GitHub Actions as the CI/CD platform), reproducing the documented local validation path as
automated checks and collapsing them into a single stable required check.

## Authority

- ADR-021 selects GitHub Actions and requires backend, frontend, migration, E2E, contract-fixture
  and container checks before TE-2C can pass.
- ADR-025 sequences TE-2CI before TE-2C completion and before the PF-1 lanes.
- `PRODUCTION_READINESS_GATES.md` defines the TE-2C Definition of Done that this workflow feeds.
- `NFR_BASELINE_AND_VERIFICATION.md` records the TE-2C NFR gate, of which "CI executes the
  documented backend/frontend/migration/E2E path" is the item this package addresses.

## Files added or changed

| File | Change |
| --- | --- |
| `.github/workflows/te-2ci-validation.yml` | New. The complete validation workflow. |
| `.github/dependency-audit-known-findings.txt` | New. Per-advisory deferral list for the Python dependency gate, with justification and remediation owner. |
| `scripts/validate_contract_fixtures.py` | New. Deterministic, cross-platform contract-fixture validator. |
| `scripts/check_tracked_secrets.py` | New. Deterministic, cross-platform committed-credential check. |
| `scripts/tests/test_validate_contract_fixtures.py` | New. Standard-library `unittest` cover for the fixture validator. |
| `scripts/tests/test_check_tracked_secrets.py` | New. Standard-library `unittest` cover for the credential check. |
| `scripts/run-e2e.ps1` | One portability change: the manifest directory path is built segment by segment instead of as an `"e2e\.manifest"` literal. |
| `scripts/ci-compose-cleanup.sh` | Added by correction TE-2CI.2-C1; teardown made profile-aware by TE-2CI.2-C2. Project-scoped Compose teardown for the `compose-e2e` job; see "Teardown" below. |
| `scripts/tests/test_ci_compose_cleanup.py` | Added by correction TE-2CI.2-C1; extended by TE-2CI.2-C2. Focused `unittest` cover for the cleanup helper, using a fake `docker` on `PATH`. |
| `.gitattributes` | Added by correction TE-2CI.2-C1. `*.sh text eol=lf` — the repository's first `.sh` file previously had no explicit line-ending rule. |

No application code, API contract, database schema, Alembic revision, permission rule, business
event, frontend screen, frozen contract or source document is changed by this package.

## Workflow design

### Triggers and controls

```text
on:                pull_request, push to main, workflow_dispatch
permissions:       contents: read (workflow level; no job raises it)
concurrency:       te-2ci-validation-<ref>, cancel-in-progress
timeouts:          every job carries an explicit timeout-minutes
```

Least privilege is set at the workflow level and never widened: no job writes contents, packages,
deployments, issues or pull requests. Concurrency cancellation means a superseded push stops
competing for runners with the commit that replaced it.

### Jobs

| Job id | Display name | What it proves |
| --- | --- | --- |
| `backend-regression` | Backend regression | The full `pytest` suite passes against PostgreSQL 17, the ADR-028 baseline |
| `migrations` | Empty-database migrations | The chain applies to a single head from a genuinely empty database |
| `frontend` | Frontend build and tests | `npm ci`, typecheck, Vitest and the production build all pass |
| `contract-fixtures` | Contract fixture validation | The validator's own tests pass, every fixture in the proposed tree parses, and the frozen handoff pack's invariants hold |
| `security-checks` | Secret and dependency checks | The credential check's own tests pass; the CI Compose cleanup helper's own tests pass, proving its fail-closed gates and removal-race tolerance; no committed credential; no new dependency advisory |
| `compose-e2e` | Compose build, health and E2E | The Compose stack builds, starts, reports healthy, and the Playwright suite passes |
| `required-validation` | **Required validation** | Every job above succeeded |

### The stable required-check name

```text
Required validation
```

Branch protection rules and rulesets match on the ordinary **job name**, so `Required validation`
is the whole identifier. The workflow's display name, `TE-2CI Validation`, is not part of it and is
not referenced by protection at all.

**Status of enforcement, 16 August 2026 (historical; see the current-status note above).** The check
existed and behaved correctly on hosted runners, but at that time it was **not registered as a
required check and no branch protection was enforced**, because the repository's GitHub plan as it
then stood did not permit that configuration. The rest of this section describes how protection
behaves once registered; on 16 August it was the specification for the ADR-029 manual merge gate,
which named the same check and applied the same pass/fail rules by process instead. As of
17 August 2026 (ADR-031) the check is registered and the consequences below are active enforcement,
not only design intent.

It is deliberately one aggregate rather than six separate required checks, so that adding or
renaming a validation job later does not require editing the protection rule.

Two consequences follow, and neither is a bypass:

- **Renaming or removing the aggregate job does not weaken protection.** The configured check
  simply stops being reported, so pull requests block on a check that never arrives. Integration
  stays blocked until the protection rule is updated to the new name. The failure mode is a stuck
  pull request, not an unguarded merge.
- **A job name used as a required check must be unique across every workflow in the repository.**
  Protection matches on the name alone, so a second job called `Required validation` in another
  workflow would be indistinguishable from this one and could satisfy the rule. Keep the name
  unique when adding workflows.

The aggregate job carries `if: always()`. Without it, a failed dependency would leave the
aggregate *skipped* rather than failed, and GitHub can treat a skipped required check as
satisfied. The job reads `toJSON(needs)` and fails unless every dependency reports exactly
`success`, so `failure`, `cancelled` and `skipped` all fail the gate.

### Action pinning

Every action is pinned to an immutable commit SHA with its readable release version in a trailing
comment, so a moved tag cannot change what executes:

| Action | Release | Pinned commit |
| --- | --- | --- |
| `actions/checkout` | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` |
| `actions/setup-python` | v7.0.0 | `5fda3b95a4ea91299a34e894583c3862153e4b97` |
| `actions/setup-node` | v7.0.0 | `820762786026740c76f36085b0efc47a31fe5020` |
| `actions/upload-artifact` | v7.0.1 | `043fb46d1a93c77aae656e7c1c64a875d1fc6a0a` |

All four are first-party GitHub actions. **No third-party action is used anywhere in this
workflow.** The only non-GitHub tool introduced is `pip-audit`, installed as a version-pinned
Python package rather than as an action; it is PyPA's own auditing tool, free and open source.

Each SHA was resolved from the GitHub API and confirmed to be a commit object rather than an
annotated tag object, since a tag-object SHA is not usable in `uses:`.

## Contract-fixture validation

`scripts/validate_contract_fixtures.py` uses only the Python standard library, needs no database,
network or running application, and produces identical output on Windows, Linux and in a
container.

### What it enumerates

Discovery uses `git ls-files --cached --others --exclude-standard`, restricted to
`docs/agent/fixtures`. That covers the **proposed tree**: fixtures already committed, plus new
fixtures that are not ignored. A fixture added on a working branch is part of the change under
review and is validated before it is committed, not after. The same rule excludes ignored paths,
so local scratch files never enter the check, and unrelated JSON elsewhere in the repository is out
of scope entirely. In CI, where the tree is a clean checkout, this is exactly the set of committed
fixtures.

Where git is unavailable — a minimal Python container, for instance — discovery falls back to a
sorted directory walk and prints which source it used, so a run can never be misread as having
covered more than it did.

Failures are reported as `<file>: [<RULE-ID>] <message>`, so the affected file and the violated
rule are always both explicit.

### Rule families

| Rules | Cover |
| --- | --- |
| `FIX-000` | A file git knows about cannot be read — most often deleted from the working tree while still in the index |
| `FIX-001`, `FIX-002` | Every candidate fixture parses (which also rejects JSON comments and trailing commas) and is pretty-printed, tab-free, newline-terminated text |
| `FIX-010` … `FIX-017` | No credential-named key carrying a value, no falsified `safe_demo_data` / `contains_real_customer_data` declaration, no PEM key, no JWT, no real-shaped PAN or GSTIN, no link or email outside the reserved documentation hosts |
| `HOF-001` … `HOF-005` | Core identity continuity: Commercial Offer, Opportunity and Account public IDs, the accepted-offer reference and the correlation ID are stable between the handoff and output examples |
| `HOF-006` | Account traceability is present in every valid example |
| `HOF-007` … `HOF-010` | Commercial Offer line identity: every line carries a public ID, sequence and status; IDs are unique; sequences are unique and ascending |
| `HOF-011`, `HOF-012` | Work Order source-line identity: every Work Order line traces to a handoff Commercial Offer line, and none is invented |
| `HOF-013` … `HOF-015` | Partial award: selected lines exist and are `AWARDED`, Work Order lines are created for exactly the selected lines, and an excluded line never produces one |
| `HOF-016` | The production MVP shell status is `HANDOFF_RECEIVED`, and `PENDING_CUSTOMER_MASTER` is never the initial status |
| `HOF-017` … `HOF-022` | Negative paths: the missing-Account example has a null Account and expects rejection; the invalid-line example expects rejection, forbids silent partial success, and names a reason for every invalid line; neither records a success business event |

These are the invariants already written down in
`docs/planning/HANDOFF_FIXTURE_VALIDATION_CHECKLIST.md`. The validator mechanises that checklist;
it does not invent new contract rules.

### Deliberately out of scope

The validator does not create the `CF-0` … `CF-4B` fixture packs described in
`CONTRACT_FIXTURE_AND_FREEZE_PLAN.md`, and it does not promote any `APPROVED` contract to
`FROZEN`. Contract maturity remains the independent reviewer's to change, through the freeze
checklist in `PRODUCTION_READINESS_GATES.md`. When those packs are created, this validator is the
natural place to extend, and its per-pack structure anticipates that.

## Security checks

### Committed-credential check

`scripts/check_tracked_secrets.py` is standard library only and enumerates the proposed tree with
`git ls-files --cached --others --exclude-standard`: committed files plus new, non-ignored files.
A credential added on a working branch is therefore caught before it is committed rather than
after.

Ignored paths are excluded by that same rule, which is what keeps the local `.env`, virtualenvs,
caches and build artifacts out of scope — `.env` is gitignored, so this check never opens it. In
CI, where the tree is a clean checkout, this is exactly the set of committed files.

It is a **guard against committing a credential, not a history scanner**: it cannot find a secret
that was committed and later removed.

| Rule | Covers |
| --- | --- |
| `SEC-001` | A credential-bearing path is present at all (`.env`, private keys, key stores, `.npmrc`, `.pypirc`). `.env.example` is the one permitted template, and its values are still checked by `SEC-004`. |
| `SEC-002` | PEM private-key block |
| `SEC-003` | Issued provider credentials: AWS, GitHub classic (`ghp_`/`gho_`/`ghu_`/`ghs_`/`ghr_`) **and fine-grained (`github_pat_`)** tokens, Slack, Google, Stripe, and JSON Web Tokens |
| `SEC-004` | A credential-named field assigned a credential-shaped value, in quoted-literal or environment-file form |
| `SEC-005` | A connection URL carrying an inline credential |

No matched value is ever echoed. A finding reports the rule, the file, the line and the value's
*length* only, so detecting a secret never copies it into a CI log or artifact.

**There are no path or directory exclusions.** Every file in the proposed tree is scanned. False
positives are suppressed by *shape*, uniformly, and each rule is written down:

- an environment-style assignment must have an upper-case name and no whitespace around `=`,
  which is what separates `API_KEY=…` from the Python constant `PASSWORD_ITERATIONS = 240000` and
  from the identifier reference `password=settings.postgres_password`;
- a name whose last segment describes a credential rather than holding one (`…_ALGORITHM`,
  `…_ITERATIONS`, `…_HEADER`) is not a finding, and `key` is deliberately absent from that list
  so `API_KEY` and `PRIVATE_KEY` stay in scope;
- a value must look like issued credential material — sixteen characters, or eight characters
  mixing letters and digits — so an English literal such as `wrong-password` in a negative test is
  not reported;
- a value matching a placeholder shape (`change…`, `example`, `placeholder`, `${VAR}`, `{VAR}`,
  `{{VAR}}`, `%VAR%`, `<value>`, `not-real`, and the archetypal literals `password` / `changeme` /
  `test`) is not a finding. The single-brace `{VAR}` form covers Python format strings and
  f-strings, where the value is a variable name rather than a secret; every interpolation shape is
  anchored to the whole value, so a real credential that merely contains a brace is still reported.

That last point covers the documented prototype seed password, which is public in the repository,
seeded by Alembic revision `20260629_0002` (since 7 October 2026, TB-1 TB1-203, by
`tooling.user_admin seed-demo-users` in development and CI only), and displayed on the login page
itself. It is a
value-shape judgement applied to every file equally, not an exemption for `e2e/tests/fixtures/`.

### Automated cover for the validators and the CI cleanup helper

`scripts/tests/` holds standard-library `unittest` suites for three scripts. The fixture
validator's suite runs in `contract-fixtures` and the credential check's suite in
`security-checks`, each immediately before the validator it covers. The CI Compose cleanup
helper's suite (added by correction TE-2CI.2-C1; see "Teardown" below) also runs in
`security-checks`, though the helper itself runs in `compose-e2e` — the jobs are parallel, so the
suite gates the aggregate check rather than the teardown step. **58 tests total.**

The fixture-validator and credential-check suites (36 tests between them) each build a throwaway
git repository in a temporary directory, because both checks are defined over git's view of the
tree and mocking that away would test nothing. Among others, they cover:

- an untracked, non-ignored file is inspected, and an ignored `.env` never enters the candidate set;
- forbidden credential-bearing paths, including `.env` force-added past `.gitignore`;
- PEM blocks, issued tokens (including `github_pat_`), credential assignments and inline-URL
  credentials;
- matched values are withheld from every message;
- placeholders, negative-test literals, identifier references and the documented seed credential
  are accepted;
- malformed fixture JSON, a missing frozen-pack file, identity and source-line mismatches, an
  invalid shell status, selected/excluded line violations, real-shaped PANs and
  non-documentation URLs;
- the actual repository passes both checks.

The sample credentials inside the secret-check tests are assembled from string fragments at
runtime. That file is itself part of the proposed tree the checker scans, so a whole literal would
make the repository fail its own gate — and excluding the path is precisely what the check
forbids.

The third suite, `scripts/tests/test_ci_compose_cleanup.py` (22 tests, added by TE-2CI.2-C1 and
extended by TE-2CI.2-C2), covers the CI Compose cleanup helper the same way: a fake `docker` placed
first on `PATH` records every invocation, so the tests assert on the exact command sequence rather
than touching a real daemon. It proves both fail-closed gates reject an out-of-scope project name
or a non-CI environment before any Docker command is issued, that removal precedes `down` and is
never invoked with an empty argument list, that every query is scoped to the exact project label,
that a container vanishing mid-removal is tolerated while a genuine survivor still fails the step,
and that the bounded settle re-check (see "Teardown" below) both clears a transiently-settling
resource and still fails a permanently stuck one once its attempts are exhausted.

The two tests added by C2 are behavioural rather than string comparisons. The fake `docker compose
down` can be told to model the real profile rule — a profile-gated service's volume is removed only
when its profile is named — so a teardown that drops `--profile e2e` leaves the volume behind,
verification reports residue and the test fails on the exit code. A second test drives the fake
directly to prove that gate really gates, so the first cannot pass vacuously.

```bash
python -m unittest discover -s scripts/tests -v
```

### Dependency checks

| Check | Scope | Threshold |
| --- | --- | --- |
| `pip-audit` (report) | `backend/requirements.txt` including transitive packages | Advisory, always prints the complete picture |
| `pip-audit` (gate) | Same, minus the named deferrals | Blocking |
| `npm audit --omit=dev` | `frontend` | Blocking at `high` |
| `npm audit` | `e2e` | Blocking at `high`; the workspace has no runtime dependencies, so `--omit=dev` would audit nothing |

The Python audit runs twice on purpose. The report step always prints every finding, including the
deferred ones, so the deferral list can never quietly hide the real state from a reviewer. The gate
step then excludes only the specific advisory IDs recorded in
`.github/dependency-audit-known-findings.txt`, each with a written justification and a named
remediation owner.

**Nine pre-existing Python advisories are deferred, not fixed.** They are reported in full in the
acceptance record. None was introduced by TE-2CI.1, and the starlette fixes require a major-version
move that pulls FastAPI with it — which would change application behaviour and is therefore
explicitly outside this package. This is a per-advisory list, not a blanket exclusion: any new or
unlisted advisory fails the gate immediately.

**Reviewer disposition: the nine named deferrals are accepted temporarily for TE-2CI.1.** The
conditions attached to that acceptance are:

- the unfiltered audit report remains a visible step, so the real state is never hidden;
- every new or unlisted advisory remains blocking;
- this is **not** production acceptance of the underlying risk;
- TE-2C must carry the residual risk explicitly in its own record rather than inheriting it
  silently; and
- remediation, or a fresh reassessment, is required before the final production-candidate gate.

## Compose, health and E2E

The `compose-e2e` job creates an ephemeral `.env` in the runner, validates the Compose
configuration, builds the backend and frontend images from the commit under test, starts the
stack, polls both the backend health endpoint and the frontend until they respond, and only then
runs the Playwright suite.

`scripts/run-e2e.ps1` is invoked unmodified, through `shell: pwsh` (preinstalled on the Ubuntu
runner image), with `-SkipServiceStart`. That switch is correct here precisely because the
preceding steps already built the images from this commit and started the stack, which is the
condition the switch's own warning is about — the suite is not testing a stale frontend bundle.

Everything the E2E path already guarantees is preserved and none of it was touched:

- `retries: 0` in `e2e/playwright.config.ts` is unchanged;
- the mandatory pre-seed `business_event` boundary capture, which aborts the run rather than
  creating login events it cannot clean up;
- the explicit E2E actor allowlist passed at the call site;
- the residual-login-event report that fails the run rather than deleting an unrecognised actor's
  events;
- the `finally` block that cleans up all three seeded manifests whether the suite passes or fails.

### Teardown (corrected by TE-2CI.2-C1 and TE-2CI.2-C2)

Teardown runs under `if: always()`, after success, failure or cancellation.

`docker compose down -v --remove-orphans` on its own turned out to be insufficient in two separate
ways, each found on a hosted run and each leaving a different resource behind. C1 addressed the
first; C2 addressed the second, which C1's own verification step is what exposed.

#### C1 — a cancelled one-off container keeps the network attached

`down` on its own is not sufficient after a **cancellation**. On hosted run `31865333180`, job
`94968525849`, Playwright was cancelled while running; the teardown step reported success and
removed the frontend, backend and database containers and the PostgreSQL volume, but its log also
recorded:

```text
Network pbl-crm-hiring_default  Resource is still in use
```

The cancelled `docker compose --profile e2e run --rm e2e` process left its one-off container
attached long enough to block network removal, and `down` exited `0` regardless. A GitHub-hosted
runner is disposable, so nothing accumulated there — but the workflow claimed the stronger
guarantee that a cancelled run leaves nothing behind on a reused or self-hosted runner, and that
guarantee was not actually established.

Two changes make it deterministic:

**A CI-only Compose project name.** The `compose-e2e` job sets

```yaml
COMPOSE_PROJECT_NAME: pbl-crm-hiring-ci-${{ github.run_id }}
```

at job level, so it is scoped to that job alone and affects neither local Compose usage nor any
other job. Without it, Compose derives the project from the directory — which on a runner is the
same `pbl-crm-hiring` a developer uses locally, giving teardown no way to distinguish the two.
`github.run_id` already separates concurrent workflow runs on a reused or self-hosted runner.

`github.run_attempt` is deliberately **not** part of the name. A per-attempt label looks safer but
is worse: a rerun would get a fresh label, so attempt 2 could pass while attempt 1's residue sat
untouched under a label nothing ever looks for again. Sharing one label across attempts is what
makes that residue findable, and the job therefore runs the same cleanup **before** starting the
stack ("Remove residue from an earlier attempt") as well as after it. On a fresh hosted runner
that pre-run step is a no-op; on a reused one it guarantees the attempt starts from a
verified-clean project and fails loudly if it cannot.

**A project-scoped cleanup helper**, `scripts/ci-compose-cleanup.sh`, invoked as
`bash scripts/ci-compose-cleanup.sh "$COMPOSE_PROJECT_NAME"` (through `bash`, so it does not
depend on the checked-out file mode). It performs three steps:

1. **Remove every container carrying the exact `com.docker.compose.project` label** for this CI
   project, with `docker rm --force --volumes`. This is the step `down` alone does not perform: a
   one-off `compose run` container left by a cancelled step is removed here, so nothing is still
   attached to the network. The id list is built with `mapfile` into a real array, and the
   removal is skipped entirely when the array is empty, so `docker rm` is never invoked with an
   empty argument list and nothing depends on word splitting.

   A `--rm` container can also exit and auto-remove itself between discovery and removal — the
   very cancellation case this exists for — and `docker rm` then returns non-zero for a container
   that is already gone. Under `set -e` that would abort before teardown and before verification,
   turning a harmless race into a failed step *and* skipping the cleanup still owed. The failure
   is therefore tolerated with a warning, and step 3 decides the outcome.
2. **Run `docker compose --profile e2e down -v --remove-orphans`**, which can now remove the
   network and volumes cleanly. The profile is required rather than decorative; see C2 below.
3. **Verify, rather than assume — with a bounded re-check for a resource still settling.** It
   re-queries containers, networks and volumes by the same exact label, up to 6 times, 5 seconds
   apart, breaking out as soon as nothing remains. A single query was not enough on its own: a
   container the daemon is still auto-removing, or a network `down` is still releasing, can
   briefly still appear in these queries even though it is clearing itself, which a one-shot check
   would have reported as residue. Only after all 6 attempts still show something does the step
   print label-scoped diagnostics and exit non-zero. Tolerating the race in step 1 is therefore
   not tolerating a genuine failure: a container that really survives removal still exhausts the
   re-checks and still fails the step here.

   This means teardown's failure path can now take up to roughly 25 seconds longer than a
   single-shot check would have (5 idle re-checks at 5 seconds each, before the final one reports
   and exits) — relevant to the `timeout-minutes` re-tuning already listed as open in the
   TE-2CI.2 sequence below. The success path is unaffected: the loop exits on its first pass once
   nothing remains.

The helper **fails closed outside its intended scope**, on two independent gates, both checked
before a single Docker command is issued:

- the project name must match `^pbl-crm-hiring-ci-[0-9]+$` exactly — the literal CI prefix plus a
  numeric run id, anchored at both ends. A prefix test alone was too broad: it accepted the bare
  `pbl-crm-hiring-ci-` and any hand-typed suffix.
- `GITHUB_ACTIONS` must be `true`. This is CI-only tooling with no legitimate local use, so a
  valid-looking project name typed on a workstation is still refused.

The local `pbl-crm-hiring` project fails both gates, so this script can never remove a developer's
containers, networks or volumes — and the retained `mssql-data` TE-2B rollback volume is not even
declared in `docker-compose.yml`. It acts only on exact label matches: it never runs
`docker system prune`, never prunes containers, networks or volumes globally, and never names a
resource explicitly.

`-v` remains safe here and only here: the CI project is created fresh by this job in an ephemeral
runner. It must never be run against a development machine holding a retained volume — the
`mssql-data` retention note in `docker-compose.yml` exists for exactly that reason.

#### C2 — a profile-gated service's volume is out of scope for `down -v`

C1 was committed as `70f3c23` and pushed, and the next hosted run, `31871165805`, exercised it.
That run passed every substantive check — backend regression, migrations, frontend, security
checks, and Playwright at 12 passed / 9 skipped — and then **failed at teardown**, because one
resource survived:

```text
pbl-crm-hiring-ci-31871165805_e2e-node-modules
```

`down -v` removes named volumes only for services that are **in scope**, and the `e2e` service is
gated behind the Compose `e2e` profile in `docker-compose.yml`. With the profile inactive that
service is out of scope, so its `e2e-node-modules` volume was never considered — while
`postgres-data`, belonging to the always-active `db` service, was removed normally. Teardown
therefore called:

```bash
docker compose --profile e2e down -v --remove-orphans
```

The profile is required, not decorative. `down` only removes, so naming it never starts the E2E
container.

Two things are worth recording about how this defect surfaced, because both are the design working
rather than failing:

- **C1's verification step is what caught it.** Before C1, this teardown would have exited `0` and
  left the volume behind silently on every run, hosted or self-hosted. The job failed loudly
  instead, which is precisely what "verify, rather than assume" was added to do.
- **The failure was in teardown only.** Run `31871165805` is real hosted evidence that the workflow
  triggers, that all six validation jobs execute, and that the full Compose build/health/Playwright
  path passes on a hosted runner. That evidence stands; only the teardown step's guarantee did not.

Reproduced and fixed against real Docker in an isolated throwaway project
(`pbl-crm-hiring-ci-99000001`, e2e-profile resources only): the profileless command exited `0`
while leaving the E2E container and `e2e-node-modules` behind, and the corrected helper removed
every container, the network and both named volumes, exiting `0` with no residue. The local
`pbl-crm-hiring` project, its three running containers and the retained `mssql-data` volume were
confirmed unchanged before and after.

#### Both corrections are hosted-proven

Both were verified on run `31930125170` at commit `8bb6af1`, and the full evidence is in "Hosted
evidence" near the top of this document.

- **C2** is proven by attempt 1: teardown ran the profile-aware command, removed `postgres-data`,
  `e2e-node-modules` and the network, and reported no residue.
- **C1** is proven by attempt 2: a deliberate cancellation with Playwright running and teardown
  still pending left no container, network or volume behind, with no `Resource is still in use`
  report.

The "leaves nothing behind" guarantee is therefore hosted-proven, not merely asserted and tested.

## Artifact retention

| Artifact | When | Retention |
| --- | --- | --- |
| `playwright-failure-artifacts` (`e2e/playwright-report/`, `e2e/test-results/`) | `if: failure()` only | 14 days |
| Compose logs (last 400 lines) | `if: failure()` only | Job log only; not uploaded as an artifact |

Nothing is uploaded on a successful run. Playwright traces and screenshots can contain seeded
business data, so they are kept only long enough to investigate a failure and are never retained
indefinitely. `if-no-files-found: ignore` prevents a failure in a job that produced no report from
being masked by a second, unrelated artifact error.

## Secret handling

- **The local `.env` is never read, never uploaded and never referenced by the workflow.** The
  `compose-e2e` job writes its own `.env` in the runner from fictional values. `.env` is
  gitignored, so it cannot be committed from CI either.
- Every credential in the workflow is fictional, ephemeral and clearly labelled as such. The
  PostgreSQL service credentials are non-secret literals in the workflow file because GitHub does
  not expose the `env` context to `services:` blocks; they exist only for the life of the runner.
- JWT signing secrets are generated inside the runner with `openssl rand -hex 32` and discarded
  with it. No signing key is committed.
- No `secrets.*` value is referenced anywhere in this workflow, because validation needs none.
- The committed-credential check reports value lengths, never values, so a detection cannot leak the
  credential into a log or artifact.

When production secrets eventually become necessary, they must use GitHub environment or
repository secret mechanisms, or an approved external secret store, per ADR-021. They must never
be committed, and they must never be introduced into this validation workflow, which has no
legitimate need for them.

## Deployment: explicitly not created

This workflow validates and does not deploy. It defines no environment, references no production
secret, and contains no deployment step. ADR-021 records that it "does not create a workflow or
authorize production deployment by itself", and TE-2CI.1 holds that line.

### Requirements a future deployment workflow must satisfy

Recorded here so the next package starts from the agreed position rather than rediscovering it:

- deployment is never automatic; a protected GitHub Environment with required reviewers gates
  every production deployment, and the approval is recorded against the specific commit;
- `Required validation` must have passed on the exact commit being deployed;
- production secrets come from the environment's own secret scope or an approved external store,
  are never printed, and are never copied into a validation workflow;
- deployment permissions are raised at the job level only, never at the workflow level;
- database migrations are applied as an explicit, reviewable step with its own recorded outcome,
  never as an implicit side effect of application startup in production; and
- the deploying workflow records the deployed commit, the approver, the timestamp and the
  migration head reached.

### Required deployment and rollback evidence

The final production-candidate gate in `PRODUCTION_READINESS_GATES.md` requires rollback evidence.
A deployment package must be able to produce, per deployment:

- the deployed commit or tag, and the Alembic head before and after;
- the environment approval record: who approved, when, and for which commit;
- the validation run that gated it;
- a tested rollback procedure with a dated exercise, covering both the application version and the
  database state, including the case where a migration has already been applied;
- backup and restore evidence taken before the deployment, per the NFR baseline; and
- post-deployment health, log and monitoring confirmation.

None of that exists yet, and TE-2CI.1 does not claim any of it.

## Portability

The GitHub runner is Ubuntu; local development is Windows. One narrowly scoped change was needed.

`scripts/run-e2e.ps1` built its manifest directory as `Join-Path $repoRoot "e2e\.manifest"`. A
backslash is an ordinary filename character on Linux, so PowerShell 7 on the runner would have
created a single file named `e2e\.manifest` instead of the directory, and every later
`Join-Path`/`Set-Content` against it would have failed. The path is now built one segment at a
time, and `Join-Path` emits the correct separator for the host.

Nothing else changed. Windows behaviour is identical, and the E2E actor allowlist, cleanup
boundaries, record-residue protection, exit-code semantics and every warning message are
untouched. The remaining backslashes in the script are inside human-readable messages that quote
Windows commands, which is correct for its primary audience.

`Invoke-WebRequest`, `Set-Content -Encoding utf8`, `New-Item -ItemType Directory` and the
`docker compose exec -T` calls are all cross-platform in PowerShell 7 and needed no change.

## Local verification

Full commands and results are in
`docs/agent/acceptance/te-2ci-github-actions-validation-foundation-acceptance.md`. Summary:

| Check | Result |
| --- | --- |
| `actionlint` 1.7.12, digest-pinned (with shellcheck and pyflakes) | 0 errors |
| Validator unit tests (`python -m unittest discover -s scripts/tests`) | 36 passed |
| Contract-fixture validator | 7 fixtures checked, all rules pass |
| Committed-credential check | Proposed tree scanned, no findings |
| Backend regression | 253 passed |
| Empty-database migration | 0 tables before, single head, `20260713_0029` applied, 28 tables, UTC |
| Frontend typecheck / tests / build | Pass, 54 tests passed, build succeeded |
| Compose config and build | Valid; backend and frontend images built |
| Playwright E2E | Passed, `retries: 0` unchanged, cleanup succeeded |
| Residue comparison | Identical before and after |
| `git diff --check` | Clean |

## Known limitations and hosted-only behaviour

**Scope note.** The list below was written for TE-2CI.1 and records what could not be established
from a working tree. It is preserved as written. The resolution of each item follows it.

These cannot be established from a working tree and are TE-2CI.2's job:

- **The workflow has never executed on a GitHub-hosted runner.** Static analysis and locally
  reproduced job logic are strong evidence, not proof. Service-container networking, runner tool
  availability, cache behaviour, action resolution at the pinned SHAs and total wall-clock time
  are all unverified.
- **The required check does not exist yet.** A check name only becomes selectable in branch
  protection after the workflow has run at least once on the default branch.
- **Branch protection is not configured**, so protected integration is not enforced today.
- **`pwsh` availability on the runner image** is documented behaviour of `ubuntu-latest`, not
  something this package verified.
- **Job timeouts are first estimates.** The backend suite takes about four minutes locally and the
  E2E path several more; hosted timings will differ.
- **No hosted run has yet completed with a successful teardown.** Run `31871165805` passed every
  substantive check, including Playwright, and then failed teardown on the profile-gated
  `e2e-node-modules` volume that correction TE-2CI.2-C2 addresses. C2 is covered by focused tests,
  `shellcheck`, `actionlint` and an isolated real-Docker reproduction, but an ordinary hosted run
  ending in a green teardown is still required.
- **The corrected cancellation teardown has not been revalidated on a hosted runner.** Correction
  TE-2CI.2-C1 is covered by focused tests and its fail-closed guard was exercised against the real
  local project, but a further controlled hosted cancellation — after the ordinary run above — is
  required before the "a cancelled run leaves nothing behind" guarantee may be recorded as proven.
- The nine deferred Python advisories remain open and need their own dependency-upgrade package.
- The workflow runs a single Chromium Playwright project, unchanged from TE-1. Cross-browser
  coverage remains out of scope.

### Resolution of the list above, 16 August 2026

| Item | Outcome |
| --- | --- |
| Workflow never executed on a hosted runner | **Resolved.** Executed and green on run `31930125170` at `8bb6af1`; networking, tooling, caching and pinned-SHA resolution all worked |
| Required check does not exist yet | **Partly resolved, then blocked.** The check runs and reports on hosted runs, but it cannot be registered as required on the current GitHub plan |
| Branch protection is not configured | **Not resolvable on the current plan.** Replaced by the ADR-029 interim manual merge gate |
| `pwsh` availability on the runner | **Resolved.** The Playwright step ran under `pwsh` successfully |
| Job timeouts are first estimates | **Resolved.** Hosted timings are well inside every limit; `compose-e2e` took about 2m 10s against a 45-minute timeout. No retuning required |
| No hosted run with a successful teardown | **Resolved.** Attempt 1 tore down cleanly and reported no residue, proving C2 |
| Corrected cancellation teardown not hosted-revalidated | **Resolved.** Attempt 2's controlled cancellation left nothing behind, proving C1 |
| Nine deferred Python advisories | **Still open.** Unchanged; needs its own dependency-upgrade package before the final production-candidate gate |
| Single Chromium Playwright project | **Still out of scope.** Unchanged from TE-1 |

## TE-2CI.2 - hosted validation and branch protection

**Executed, 16 August 2026.** This was the plan; the outcome of each step is recorded after the
list. Steps 7 and 8 could not be completed and are replaced by the ADR-029 manual merge gate. The
plan text is preserved as written so the intended end state stays visible for the reassessment
owed before production.

Perform in this order, after TE-2CI.1 is independently reviewed, committed and pushed.

1. **Push and observe the first run.** Push the branch and open a pull request. Confirm the
   workflow appears and every job runs. Expect first-run issues to be timing or environment
   related rather than logical.
2. **Confirm each job independently.** Backend regression green against the service container;
   migrations reaching the single head from empty; frontend gate green; contract fixtures green;
   security checks green with exactly the nine documented deferrals and no new advisory;
   `compose-e2e` building, reporting healthy and passing Playwright with `retries: 0`.
3. **Confirm the aggregate.** `Required validation` reports success when all six pass. Then prove
   it fails correctly: on a scratch branch, break one job deliberately and confirm the aggregate
   fails rather than being skipped. Do not merge that branch.
4. **Confirm artifact behaviour.** A failing E2E run uploads `playwright-failure-artifacts` with
   14-day retention; a passing run uploads nothing.
5. **Confirm cleanup.** The teardown step runs on failure and on cancellation.
6. **Record timings** for each job and adjust `timeout-minutes` if any job runs close to its
   limit. Record the adjustment as part of TE-2CI.2.
7. **Register the required check.** In Settings → Branches, add a protection rule for `main`
   requiring the status check named exactly:

   ```text
   Required validation
   ```

   Also enable "Require branches to be up to date before merging", so the check reflects the
   merged result rather than a stale base.
8. **Prove enforcement.** Confirm a pull request with a failing check cannot be merged, and that a
   passing one can.
9. **Record the evidence** — run URLs, timings, the protection-rule screenshot or settings export,
   and any adjustment made — in the TE-2CI acceptance document, and only then mark TE-2CI complete
   and unblock TE-2C.

### Outcome of each step

| Step | Outcome |
| --- | --- |
| 1. Push and observe the first run | Done. Three hosted runs in total; the first two each exposed a real teardown defect, corrected as C1 (`70f3c23`) and C2 (`8bb6af1`) |
| 2. Confirm each job independently | Done on run `31930125170` attempt 1; all six green, Playwright 12 passed / 9 skipped at `retries: 0` |
| 3. Confirm the aggregate both ways | Done, twice over. A deliberately broken scratch branch (`te-2ci2-failure-proof`, PR #1, run `31865333180`) proved `Required validation` fails on a real assertion failure rather than being skipped (Evidence 0). Run `31930125170` then proved success (attempt 1) and failure on a cancelled dependency (attempt 2) |
| 4. Confirm artifact behaviour | Done. `playwright-failure-artifacts` uploaded with 14-day retention on the scratch-branch failure run (Evidence 0); C1 and C2 changed nothing about artifacts, so this was not re-exercised on `31930125170` |
| 5. Confirm cleanup on failure and cancellation | Done. Attempt 2 proves the cancellation path; the earlier failed teardowns proved the failure path |
| 6. Record timings and retune if needed | Done. No retuning required |
| 7. Register the required check | **Not possible on the GitHub plan as of 16 August 2026.** Replaced by ADR-029 at that time. **Resolved 17 August 2026:** the check is registered as required via ruleset `20939060` — see ADR-031 |
| 8. Prove enforcement | **Not possible on 16 August 2026**, for the same reason; the manual gate was a process control and could not be technically proven. **Partly resolved 17 August 2026:** the ruleset's configuration (pull request required, branch current, `Required validation` required, no force push/deletion, no bypass actor) was activated and independently inspected through the GitHub API — see ADR-031 — which closes the plan/configuration limitation, but end-to-end behavioral proof against a real pull request remains an explicit TE-2C evidence item, not established by this configuration inspection alone |
| 9. Record evidence and mark complete | Done. Evidence is in "Hosted evidence" above and in the acceptance record; TE-2CI is marked complete and TE-2C is unblocked |

### What remains for the plan upgrade (historical framing, partly resolved 17 August 2026)

This section was written on 16 August 2026, when steps 7 and 8 above could not be completed and the
manual gate stood as the only available control; it is preserved as written for that reason. **As
of 17 August 2026, the GitHub plan was upgraded**, and by activating repository ruleset `20939060`,
recorded as ADR-031:

- **Step 7 (register the required check) is complete.** `Required validation` is registered as a
  required status check on `main`.
- **Step 8 (prove enforcement) is not fully complete.** The enforcement *configuration* was
  established and independently inspected through the GitHub API — pull request required, branch
  current, `Required validation` required, no force push/deletion, no bypass actor — which closes
  the plan/configuration limitation this section describes. That configuration inspection is not,
  by itself, the end-to-end behavioral proof step 8 originally called for (confirming a real pull
  request with a failing check cannot be merged and a passing one can); that behavioral
  verification remains an explicit TE-2C evidence item.

ADR-029 is not revised or withdrawn — it remains the accurate historical record of the interim gate
that applied through 16 August 2026 — but current guidance in this repository must now follow
ADR-031. Integration into `main` may be described as technically enforced, at the configuration
level, from 17 August 2026 onward; it may not yet be described as end-to-end behaviorally proven
until TE-2C records that evidence.

Step 9 was recorded by the independent reviewer on 16 August 2026 against the evidence in this
document; **TE-2CI remains complete under that historical acceptance basis**, unaffected by the
later plan upgrade. TE-2C remains unblocked but not started.
