# 07 - Setting up and testing

This takes you from a clean computer to the system running and every test passing. PBL runs the same sequence on
every copy it hands out, and Phase 0 (doc 09) starts with you running it yourselves.

## What you need

- Git;
- Docker Desktop or Docker Engine, with Compose v2;
- PowerShell 7 (`pwsh`), for the repository's `.ps1` tools (practice data, demonstration data, browser tests);
- this repository.

Nothing else: no Python or Node.js on the machine (they run inside the containers), no old database, no old Docker
volumes, no files from anyone's computer. Ports 5432, 8000 and 3000 must be free, and only one copy of the system runs
on a machine at a time (`AGENTS.md`, "Only one stack runs at a time on a developer machine").

Windows and Linux both work. The commands below are PowerShell; on Linux use the same commands in `pwsh`, or their
shell equivalents.

## The sequence

| # | Step | Command | You should see |
| --- | --- | --- | --- |
| 1 | Settings | `Copy-Item .env.example .env` | A `.env` file. Its values are for a machine of your own only; the system refuses them anywhere else |
| 2 | Build and start | `docker compose up -d --build` | Three services running: the database, the server and the screens |
| 3 | Database built from empty | `docker compose exec backend alembic heads` and `docker compose exec backend alembic current` | Both end with `20260908_0055 (head)` |
| 4 | Health | Open `http://localhost:8000/api/health` | `{"status": "ok", ...}` |
| 5 | Sign in | Open `http://localhost:3000`, sign in as `admin1`, password `password` | The dashboard. The six practice users and their roles are in `backend/README.md`; they exist only on a machine of your own and in the automatic checks |
| 6 | Practice data | `docker compose exec backend python -m tooling.smoke_data seed --scenario vendor-demo-bundle` (or `pwsh scripts/vendor-demo.ps1 prepare`) | A run id and a summary of the records made. `... smoke_data scenarios` lists every scenario; `... cleanup --run-id <id>` removes one run's records |
| 7 | Server tests | `docker compose exec backend pytest -q` | No failures. Two tests are skipped inside the container because they read documents the container does not hold; the automatic checks run them. The full set takes a while |
| 8 | Screen tests and build | The three commands in `AGENTS.md`, "Checking a change", which run the type check, the tests and the production build | No errors |
| 9 | Repository checks | The `docker run ... python:3.12 ...` command in `README.md`, "Repository checks" (run from a normal clone) | "All contract fixture rules passed", "No committed-credential findings", and the scripts' own tests OK |
| 10 | Browser walk-throughs | `pwsh -NoProfile -File scripts/run-e2e.ps1` | No failures. Some are skipped by design |
| 11 | The frozen handoff | `Get-FileHash docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` (or `sha256sum`) | The value recorded in `docs/continuity/NEXT_STEPS.md` |
| 12 | Clear up | `docker compose down -v` | Everything removed, including the database |

The counts PBL saw on the copy delivered to you are recorded in `docs/vendor/VENDOR_BASELINE_MANIFEST.md`. If your
run differs, tell us: it is either something in your environment or something we missed, and either way we want to
know.

## The automatic checks

`.github/workflows/te-2ci-validation.yml` runs the same checks on every proposed change: the server tests against a
fresh database, the database built from empty, the screen checks, the repository checks, a check of the libraries
used, and the browser walk-throughs. They gather into one result, **`Required validation`**, which must succeed before
a change is accepted. On GitHub's machines the whole set takes about half an hour. A test that fails now and then is
diagnosed, never simply re-run until it passes.

## What each kind of test is for

| Kind | Proves |
| --- | --- |
| Server tests | The business rules and permissions. They are the authority on whether the system behaves correctly |
| Screen tests | The logic behind each screen. They do not yet draw the screens; screen-level tests are part of this package (doc 03) |
| Browser walk-throughs | That the main flows work through the real screens, for the flows they cover |
| Exploring by hand | New behaviour nothing yet covers |
| User testing by PBL's staff | That it suits the business |

`docs/agent/TESTING_STRATEGY.md` has the detail, including how a test that depends on today's date must be written.

## Running it somewhere other than a laptop

PBL's test sites run these same containers behind a web server with HTTPS, with a backup taken before every upgrade.
Production will be in PBL's Azure account, unless PBL accepts another cloud you propose; setting it up is part of
this package (doc 10). Two rules carry over
from the test sites, and are recorded in `db/notes/migration-rules.md`: **back up before every upgrade**, and **undo a
release by putting the previous release back and restoring that backup - never by stepping the database back**.
