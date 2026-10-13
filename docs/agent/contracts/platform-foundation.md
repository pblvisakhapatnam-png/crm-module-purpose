# Platform Foundation Contract

> **Reconciled 7 October 2026 (TB-1 TB1-904).** This is Slice 0's contract, kept as the record of
> what Slice 0 set out to build. Its technology choices are superseded and are not current:
>
> - the frontend is React 19 + Vite + React Router, not Next.js (ADR-016; TE-2A);
> - the database is PostgreSQL 17 with SQLAlchemy 2.x's `postgresql+psycopg` dialect and Psycopg 3,
>   not SQL Server with pyodbc (ADR-028, which supersedes ADR-006; TE-2B);
> - the database is configured by `DATABASE_URL` (and `POSTGRES_DB`, `POSTGRES_USER`,
>   `POSTGRES_PASSWORD` for the database container), not the `MSSQL_*` variables - `.env.example`
>   holds the current list;
> - `/api/platform/db-health` checks the PostgreSQL database, not SQL Server.
>
> The "Stack", "Required local services" and "Environment variables" sections and the SQL Server
> wording below are therefore historical. The rest - the endpoints, roles and the workflow-status,
> business-event and document-metadata foundations - describes foundations that still exist;
> `workflow-and-events.md`, `documents.md` and the module contracts are their current contracts.

## Contract ID

PF-001

## Purpose

Slice 0 must establish the minimum technical platform required before business module implementation begins.

This contract defines the required foundation for:

- local Docker Compose development;
- SQL Server database;
- FastAPI backend;
- Next.js frontend;
- basic authentication and roles;
- workflow status foundation;
- business event foundation;
- document metadata foundation;
- testing commands and conventions.

## Out of scope for Slice 0

Slice 0 must not implement the full Account module.

Out of scope:

- full Account CRUD;
- Lead workflow;
- Opportunity workflow;
- Commercial Offer;
- Work Order;
- Customer Master activation;
- Equipment Hiring execution;
- Billing and invoicing.

## Stack

```text
Backend: FastAPI
Frontend: Next.js
Database: SQL Server Developer Edition in Docker
ORM: SQLAlchemy 2.x
Migrations: Alembic
Driver: pyodbc
Repo: Monorepo
Local run: Docker Compose
```

## Required local services

Docker Compose should define:

```text
db        SQL Server Developer Edition
backend   FastAPI app
frontend  Next.js app
```

## Environment variables

Minimum expected variables:

```text
APP_ENV
BACKEND_PORT
FRONTEND_PORT
MSSQL_HOST
MSSQL_PORT
MSSQL_DATABASE
MSSQL_USER
MSSQL_PASSWORD
JWT_SECRET
```

## Required backend endpoints

### Health check

```text
GET /api/health
```

Expected response:

```json
{
  "status": "ok"
}
```

### Auth login

```text
POST /api/auth/login
```

Slice 0 may implement a simple seeded-user login.

Expected request shape:

```json
{
  "username": "sales1",
  "password": "password"
}
```

Expected response shape:

```json
{
  "access_token": "string",
  "token_type": "bearer",
  "user": {
    "public_id": "uuid",
    "username": "sales1",
    "display_name": "Sales User 1",
    "roles": ["Sales User"]
  }
}
```

**Refusals and limits, 7 October 2026 (TB-1 TB1-204 part a; record
`docs/continuity/TB1_204A_SIGN_IN_HARDENING.md`).**

- A wrong username or password: `401` with `{"detail": "Invalid credentials."}`, as before.
- A username or password holding a NUL character, or text that is not UTF-8 (a lone surrogate): `422`, FastAPI's
  usual list, before anything is counted. Every route's `422` is now written with non-ASCII characters escaped - the
  same JSON - because a lone surrogate in it used to turn the answer into a `500`.
- A username stopped after repeated wrong passwords: `429` with
  `{"detail": "Too many failed sign-ins for this username. Try again in N minutes."}` and a
  `Retry-After` header in seconds. The attempt that reaches the limit, if its password is wrong, is
  answered this way too; while stopped, even the right password is. The limit is five attempts for one
  username within any 15 minutes (a rolling window) with no successful sign-in among them, and the stop lasts
  15 minutes - fixed numbers, the owner's, not settings (since review round 9 of the package; they were
  settings before). Counted per typed username, case ignored, whether or not an account has it.
- The token carries `ver`, the account's sign-in number when it was issued. A token without one,
  issued before this change, counts as `0`: every account active when the change is deployed starts at `0`, so
  the deploy ends no active account's sign-in; one already disabled or retired starts at `1`, so its older
  tokens stay ended if it is enabled again.

### Current user

```text
GET /api/auth/me
```

Expected response shape:

```json
{
  "public_id": "uuid",
  "username": "sales1",
  "display_name": "Sales User 1",
  "roles": ["Sales User"]
}
```

Every authenticated route refuses with `401`, before anything else, a token that is malformed - since
7 October 2026 including one holding a non-ASCII character, which used to answer `500` - expired, for
an account no longer active, or whose `ver` is older than the account's: a password reset, disabling or
retiring the account, and the account tool's `end-sign-ins` raise the account's number, so
`{"detail": "This sign-in has ended. Sign in again."}` (TB-1 TB1-204 part a).

## Initial roles

Seed or define:

```text
Admin
Sales User
Sales Manager
Finance User
Operations User
Management / Read Only
```

## Initial database entities

Minimum expected foundation tables:

```text
app_user
role
user_role
workflow_status
business_event
document_metadata
```

This contract does not finalize exact columns. Exact schema must be defined in migrations and documented when implemented.

## Workflow status foundation

Purpose:

Provide a reusable status structure for later modules.

Minimum concept fields:

```text
status_code
status_name
module
is_active
sort_order
```

## Business event foundation

Purpose:

Record important business events for traceability even before full audit is implemented.

Minimum concept fields:

```text
event_name
source_module
record_type
record_public_id
user_public_id
event_timestamp
status_before
status_after
reason
remarks
correlation_id
event_payload
```

## Document metadata foundation

Purpose:

Allow business records to link documents without final SharePoint integration.

Minimum concept fields:

```text
document_public_id
document_type
linked_record_type
linked_record_public_id
file_name
storage_mode
storage_path_or_url
version_no
status
uploaded_by
uploaded_at
remarks
```

Storage modes may include:

```text
local_upload
external_link
future_sharepoint
```

## Frontend foundation

Slice 0 frontend should include:

- application shell;
- placeholder dashboard/home page;
- login page or placeholder login flow;
- navigation placeholder for Accounts;
- clear indication that this is a prototype.

No full Account UI is required in Slice 0.

## Testing expectations

Minimum tests/checks:

- backend health endpoint test;
- backend app starts;
- frontend app starts;
- Docker Compose services start;
- basic auth path if implemented;
- migration setup exists if schema is implemented.

## Acceptance evidence

Slice 0 is accepted when:

- `docker compose up` starts the local stack;
- backend health endpoint responds;
- frontend home page opens;
- simple login works if included;
- database container persists data through Docker volume;
- required folders and docs exist;
- test commands are documented.

## Slice 0B implemented database health endpoint

```text
GET /api/platform/db-health
```

Expected purpose:

- confirm backend can connect to SQL Server;
- confirm application database exists;
- confirm Alembic migration table exists;
- confirm platform foundation tables are present.

This endpoint is for platform smoke testing and early development diagnostics.
## Two routes no other contract names

*Added 8 October 2026 (TB-1 finding TB1-107).* Both are live and were in no contract.

```text
GET /api/auth/roles                IDENTITY_ROLE_CATALOG_READ (Admin)   the active roles, by name:
                                                                         [{"role_code", "role_name"}]
GET /api/platform/config-summary   no sign-in                           {"app_env", "database": {"dialect",
                                                                         "host", "port", "database", "user"}}
```

`/api/auth/roles` lists the roles a user can be given (`identity/routes.py`, `list_active_roles`); without the
permission, `403`; without a sign-in, `401`.

`/api/platform/config-summary` is a smoke-testing aid. It never carries a password
(`test_platform_config_summary_does_not_expose_password`), but like `/api/health` and `/api/platform/db-health` it
answers anyone who can reach the backend: the pilots rely on their site login in front of it. Gating these diagnostics
in the application is TB-1 corrective package CS-08 (TB1-204 part b, formerly TB1-205), before production.
