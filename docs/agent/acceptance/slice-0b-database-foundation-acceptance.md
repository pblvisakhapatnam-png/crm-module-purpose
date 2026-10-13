# Slice 0B Database Foundation - Acceptance Checklist

## Acceptance status

Not Started

## Target duration

15-25 minutes.

## Preconditions

- Slice 0A has been committed and pushed.
- Docker Desktop is running.
- Current working directory is repository root.
- `.env` exists and SQL Server password meets complexity requirements.

## Manual checks

### 1. Start stack

```powershell
docker compose down
docker compose up --build
```

Expected:

- SQL Server starts.
- Backend installs ODBC dependencies during build.
- Backend waits for DB if needed.
- Backend applies Alembic migration.
- Backend starts Uvicorn.
- Frontend starts.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 2. Backend health

Open:

```text
http://localhost:8000/api/health
```

Expected status: `ok`.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 3. DB health

Open:

```text
http://localhost:8000/api/platform/db-health
```

Expected:

- status is `ok`;
- database is `pbl_crm_hiring`;
- foundation tables are present.

Required tables:

```text
app_user
role
user_role
workflow_status
business_event
document_metadata
alembic_version
```

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 4. Frontend regression

Open:

```text
http://localhost:3000
http://localhost:3000/login
http://localhost:3000/accounts
```

Expected: all Slice 0A frontend pages still load.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 5. Automated backend tests

Run in a second PowerShell window:

```powershell
docker compose exec backend pytest
```

Expected: tests pass.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 6. Git check

Run:

```powershell
git status
```

Expected:

- only intended Slice 0B files are modified/untracked;
- `.env` is not staged;
- helper `.ps1` files are not staged.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## Known limitations

- No real authentication yet.
- No Account/business_party tables yet.
- Workflow and event tables exist but are not yet used by business modules.
- Document metadata table exists but upload/link routes are not yet implemented.

## Final decision

```text
Accepted / Not Accepted:
Accepted by:
Date:
Notes:
```