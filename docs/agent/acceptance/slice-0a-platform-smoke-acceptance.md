# Slice 0A Platform Smoke - Acceptance Checklist

## Acceptance status

Not Started

## Target duration

10-15 minutes.

## Preconditions

- Docker Desktop is running.
- Local `.env` exists.
- Current working directory is repository root.

## Manual checks

### 1. Start stack

```powershell
docker compose up --build
```

Expected:

- SQL Server container starts.
- Backend starts.
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

Expected:

```json
{
  "status": "ok",
  "service": "pbl-crm-hiring-backend",
  "environment": "development"
}
```

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 3. Backend config summary

Open:

```text
http://localhost:8000/api/platform/config-summary
```

Expected:

- non-sensitive environment/database summary;
- no password shown.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 4. Frontend dashboard

Open:

```text
http://localhost:3000
```

Expected:

- page loads;
- PBL CRM sidebar visible;
- dashboard text visible.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 5. Frontend login placeholder

Open:

```text
http://localhost:3000/login
```

Expected:

- login placeholder page visible.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 6. Frontend accounts placeholder

Open:

```text
http://localhost:3000/accounts
```

Expected:

- accounts placeholder page visible;
- planned Account tabs listed.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## Automated checks

From backend container or local backend environment:

```powershell
pytest
```

Expected:

- backend health tests pass.

## Known limitations

- Auth is placeholder only.
- Database connection is not yet verified by backend.
- Alembic migrations are not yet implemented.
- Account module is not implemented.

## Final decision

```text
Accepted / Not Accepted:
Accepted by:
Date:
Notes:
```
