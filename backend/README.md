# Backend

FastAPI backend for the PBL CRM + Equipment Hiring prototype.

## Local Docker run

From repository root:

```powershell
docker compose up --build
```

Create `.env` from `.env.example` first; the root `README.md`, "Setting up a local copy", has the steps.

The backend starts with `python -m app.startup` (`app/startup.py`), which:

1. Waits for PostgreSQL to accept a connection, retrying every 2 seconds up to 60 times. The database itself is
   created by the PostgreSQL container (`POSTGRES_DB`) or the hosting provider, never by the application.
2. Runs `alembic upgrade head` once. A failed migration stops the start at once, with Alembic's error in the log; it is
   not retried (TB-1 TB1-405; `db/notes/migration-rules.md`, "When the backend starts").
3. In development and CI only, creates the six demo users (below).
4. Starts Uvicorn on `BACKEND_PORT` (8000).

*(Corrected 8 October 2026, TB-1 TB1-903: this list said the start waits for SQL Server and creates the application
database, as it did before TE-2B moved the project to PostgreSQL - ADR-028.)*

Migrations are written by hand; `alembic revision --autogenerate` is refused (`db/notes/migration-rules.md`).

## Smoke URLs

```text
http://localhost:8000/api/health
http://localhost:8000/api/platform/config-summary
http://localhost:8000/api/platform/db-health
```

## Auth smoke endpoints

```text
POST http://localhost:8000/api/auth/login
GET  http://localhost:8000/api/auth/me
GET  http://localhost:8000/api/auth/roles
```

Seed users for local development:

```text
admin1 / password       Admin
sales1 / password       Sales User
manager1 / password     Sales Manager
finance1 / password     Finance User
ops1 / password         Operations User
readonly1 / password    Management / Read Only
```

These are development seed users only. Since 7 October 2026 (TB-1 TB1-203) the migrations do not
create them: the backend creates them, or restores them, when it starts with `APP_ENV` set to a
development value (`development` in a local `.env`, `ci` in CI), by running
`python -m tooling.user_admin seed-demo-users`. That command refuses in any other environment, and
the backend refuses to start at all when `APP_ENV` is missing (TB-1 TB1-204 part d).

## Local tests

From inside the backend container:

```powershell
docker compose exec backend pytest
```