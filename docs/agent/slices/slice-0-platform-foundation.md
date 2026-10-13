# Slice 0 - Platform Foundation

## Slice ID

S0

## Goal

Create the minimum working platform foundation for later CRM module development.

No business module should be fully implemented in this slice.

## Scope

Slice 0 includes:

```text
Docker Compose local stack
SQL Server Developer Edition container
FastAPI backend shell
Next.js frontend shell
SQLAlchemy/Alembic foundation
basic health endpoint
simple auth/role foundation
business_event foundation
workflow_status foundation
document_metadata foundation
test command structure
agent documentation structure
```

## Out of scope

```text
Full Account CRUD
Lead module
Opportunity module
Commercial Offer
Work Order
Customer activation
Equipment Hiring
Billing
Invoicing
```

## Backend tasks

1. Confirm FastAPI app starts.
2. Implement or preserve `GET /api/health`.
3. Set up config loading from environment variables.
4. Set up database connection structure.
5. Set up SQLAlchemy base model pattern.
6. Set up Alembic migration foundation.
7. Create identity module skeleton.
8. Create workflow module skeleton.
9. Create events module skeleton.
10. Create documents module skeleton.

## Frontend tasks

1. Confirm Next.js app starts.
2. Create simple application shell.
3. Create placeholder home/dashboard page.
4. Create placeholder login page.
5. Create placeholder Accounts navigation entry.

## Database tasks

If database schema is implemented in this slice, include migrations for:

```text
app_user
role
user_role
workflow_status
business_event
document_metadata
```

If schema is deferred, document that explicitly and keep migration foundation ready.

## Test tasks

1. Backend health test.
2. Backend import/startup test.
3. Docker Compose startup check.
4. Frontend startup check.
5. Auth test if login is implemented.
6. Migration check if migrations are implemented.

## Documentation tasks

Update or confirm:

```text
docs/agent/contracts/platform-foundation.md
docs/agent/contracts/workflow-and-events.md
docs/agent/contracts/documents.md
docs/agent/slices/slice-0-platform-foundation.md
docs/agent/acceptance/slice-0-platform-foundation-acceptance.md
```

## Files in likely scope

```text
docker-compose.yml
.env.example
backend/
frontend/
db/
docs/agent/
```

## Files not in scope

Do not implement:

```text
backend/app/modules/business_party/
frontend/app/accounts/
docs/agent/contracts/accounts.md
```

except for placeholder consistency if already present.

## Completion criteria

Slice 0 is complete when:

- local stack can start;
- backend health endpoint works;
- frontend page opens;
- database service starts and uses persistent volume;
- required documentation files exist;
- test commands are documented;
- no business module has been prematurely implemented.
