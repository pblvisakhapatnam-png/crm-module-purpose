# Slice 0A - Platform Smoke

## Goal

Make the platform skeleton runnable before database migrations, auth and business modules are added.

## Scope

Includes:

- Docker Compose stack definition.
- Backend FastAPI startup.
- Backend `/api/health`.
- Non-sensitive platform config summary endpoint.
- Frontend application shell.
- Frontend dashboard, login placeholder and accounts placeholder.
- Basic backend smoke tests.
- `.gitattributes` for consistent line endings.

## Out of scope

- Real authentication.
- Database connection validation.
- Alembic migrations.
- Account module implementation.
- Workflow/event table implementation.
- Document upload implementation.

## Human acceptance

Use:

```text
docs/agent/acceptance/slice-0a-platform-smoke-acceptance.md
```
