# Slice 0B - Database Foundation

## Goal

Add the database foundation needed before implementing real CRM business objects.

## Scope

Includes:

- SQL Server ODBC driver in backend container.
- SQLAlchemy engine and session setup.
- Alembic migration setup.
- Automatic local database creation for Docker development.
- First platform migration.
- Foundation tables:
  - app_user
  - role
  - user_role
  - workflow_status
  - business_event
  - document_metadata
- Role seed data.
- `/api/platform/db-health` endpoint.

## Out of scope

- Real login UI.
- JWT authentication.
- Account/business_party implementation.
- Lead, Opportunity, Commercial Offer or Work Order implementation.
- Document upload implementation.
- Full audit engine.

## Main files in scope

```text
backend/Dockerfile
backend/requirements.txt
backend/alembic.ini
backend/alembic/env.py
backend/alembic/versions/20260629_0001_platform_foundation.py
backend/app/core/config.py
backend/app/core/database.py
backend/app/startup.py
backend/app/main.py
backend/app/models_metadata.py
backend/app/modules/identity/models.py
backend/app/modules/workflow/models.py
backend/app/modules/events/models.py
backend/app/modules/documents/models.py
backend/tests/test_health.py
backend/README.md
docs/agent/slices/slice-0b-database-foundation.md
docs/agent/acceptance/slice-0b-database-foundation-acceptance.md
docs/continuity/NEXT_STEPS.md
```

## Completion criteria

Slice 0B is complete when:

- `docker compose up --build` starts all services.
- Backend startup applies Alembic migration successfully.
- `/api/platform/db-health` returns status `ok`.
- Foundation table status shows all required tables as present.
- Initial roles are seeded.
- Existing Slice 0A URLs still work.
- Backend tests pass.