# PBL CRM + Equipment Hiring Prototype

Production-style prototype for CRM first, preserving future Equipment Hiring and Transportation integration paths.

## Stack

- Backend: FastAPI
- Frontend: React 19 + Vite + React Router
- Database: PostgreSQL 17 in Docker, via Psycopg 3 (ADR-028)
- Repository: Monorepo
- Development: Docker Compose local first

## Setting up a local copy

Written 8 October 2026 (TB-1 REP-1, findings TB1-105 and TB1-903) for a newcomer starting from the repository alone.

**What you need on the machine:** Git; Docker Desktop (or Docker Engine) with Compose v2; and PowerShell 7 (`pwsh`)
for the repository's `.ps1` tools. Python and Node.js run inside the containers, not on the host. The stack publishes
fixed host ports - 5432 (PostgreSQL), 8000 (backend) and 3000 (frontend) - so they must be free, and only one copy of
the stack can run on a machine at a time (`AGENTS.md`, "Only one stack runs at a time on a developer machine").

**Steps, from the repository root:**

1. Create `.env` from the example. Compose refuses to start without it, and the backend refuses to start without the
   `APP_ENV` it sets. Its values are for a local stack only - `APP_ENV=development`, a placeholder database password,
   a placeholder token secret and fewer password-hashing rounds (`PASSWORD_HASH_ITERATIONS`, so the tests run fast) -
   and the backend refuses all three in any other environment.

   ```powershell
   Copy-Item .env.example .env
   ```

2. Build and start the three services:

   ```powershell
   docker compose up -d --build
   ```

   The database is PostgreSQL 17. The backend waits for it, applies every migration (`alembic upgrade head`), creates
   the six demo users because `APP_ENV` is `development`, and listens on port 8000. The frontend serves the built
   application on port 3000.

3. Check it: `http://localhost:8000/api/health` answers `{"status": "ok", ...}`; open `http://localhost:3000` and sign
   in as `admin1` with the password `password`. The six demo users and their roles are listed in `backend/README.md`;
   they exist only in development and CI.

**Afterwards:**

- Pulled a change that adds a migration? `docker compose up -d --build --force-recreate backend` - the migrations are
  built into the backend image, not read from the working tree.
- A frontend change reaches the running site only through `docker compose up -d --build --no-deps frontend`.
- Stop the stack with `docker compose stop`. `docker compose down -v` also deletes its database and stored documents.

**Tests:** the backend's with `docker compose exec backend pytest` (the whole suite takes a long time; CI runs it on
every pull request); the frontend's typecheck, tests and build with the three commands in `frontend/README.md`; the
browser regression with `pwsh -NoProfile -File scripts/run-e2e.ps1`. `docs/agent/TESTING_STRATEGY.md` says what each
layer is for, and `AGENTS.md` gives the order a change runs them in.

**Repository checks** - the contract fixtures, the committed-credential check and the scripts' own tests, which CI also
runs - need Python 3 and Git. With neither on the host, run them in a container from a normal clone (not a `git
worktree`, whose `.git` file points outside the folder the container sees):

```powershell
docker run --rm -v "${PWD}:/repo" -w /repo python:3.12 sh -c "git config --global --add safe.directory /repo && python -B scripts/validate_contract_fixtures.py && python -B scripts/check_tracked_secrets.py && python -B -m unittest discover -s scripts/tests"
```

**A database outside Compose** - a vendor's or a managed one - must provide PostgreSQL 17 (the migrations need at least
13), the `btree_gist` extension, and a role that may install it and create tables: `db/notes/migration-rules.md`, "What
the database must provide". Migrations are written by hand; `alembic revision --autogenerate` is refused (same file).

**Where to read next:** `VENDOR_START_HERE.md`, then `docs/agent/PROJECT_OVERVIEW.md` and
`docs/continuity/NEXT_STEPS.md` (where the project stands). PBL's runbook for its own hosted test sites is not part of
this copy.

## Documentation Structure

- docs/vendor/ - the vendor evaluation pack; start at `VENDOR_START_HERE.md`.
- docs/agent/ - architecture decisions, contracts, slices and acceptance records.
- docs/continuity/ - where the project stands, and the open and decided questions.

## Vendor Demo Data Pack

```powershell
.\scripts\vendor-demo.ps1 prepare    # seed a fresh vendor-demo-bundle and generate a launch sheet
.\scripts\vendor-demo.ps1 status     # check the active run's records still exist
.\scripts\vendor-demo.ps1 preflight  # health checks + non-destructive Playwright preflight
.\scripts\vendor-demo.ps1 reset      # clean up and reseed a fresh run
.\scripts\vendor-demo.ps1 cleanup    # remove the active run
```

`scripts/vendor-demo.ps1` describes each command at its top; the scenario it seeds is `vendor-demo-bundle`.
