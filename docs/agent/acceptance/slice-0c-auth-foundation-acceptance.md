# Slice 0C Authentication Foundation - Acceptance Checklist

## Acceptance status

Not Started

## Target duration

15-25 minutes.

## Preconditions

- Slice 0B has been committed and pushed.
- Docker Desktop is running.
- Current working directory is repository root.
- `.env` exists.

## Manual checks

### 1. Start stack

```powershell
docker compose down
docker compose up --build
```

Expected:

- SQL Server starts;
- backend applies Alembic migrations through `20260629_0002`;
- backend starts;
- frontend starts.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 2. Backend health regression

Open:

```text
http://localhost:8000/api/health
http://localhost:8000/api/platform/db-health
```

Expected: both return `status: ok`.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 3. Login from frontend

Open:

```text
http://localhost:3000/login
```

Use:

```text
admin1 / password
```

Expected:

- login succeeds;
- signed-in user details are shown;
- roles show Admin.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 4. Protected endpoint from frontend

Open:

```text
http://localhost:3000/accounts
```

Click:

```text
Check current user
```

Expected:

- current user loads from `/api/auth/me`;
- user details are shown.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 5. Backend auth API negative check

In PowerShell:

```powershell
curl.exe -X POST http://localhost:8000/api/auth/login -H "Content-Type: application/json" -d "{\"username\":\"admin1\",\"password\":\"wrong\"}"
```

Expected: 401 response.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 6. Automated backend tests

Run:

```powershell
docker compose exec backend pytest
```

Expected: tests pass.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## Known limitations

- Seed passwords are for development only.
- No password reset or user management UI yet.
- No login business event is recorded yet.
- No production identity provider integration.

## Final decision

```text
Accepted / Not Accepted:
Accepted by:
Date:
Notes:
```