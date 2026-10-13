# Slice 0D Business Events Foundation - Acceptance Checklist

## Acceptance status

Not Started

## Target duration

15-20 minutes.

## Preconditions

- Slice 0C has been committed and pushed.
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
- backend starts;
- frontend starts.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 2. Regression checks

Open:

```text
http://localhost:8000/api/health
http://localhost:8000/api/platform/db-health
http://localhost:3000/login
http://localhost:3000/accounts
```

Expected: prior Slice 0A-0C checks still pass.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 3. Login event

Open:

```text
http://localhost:3000/login
```

Login as:

```text
admin1 / password
```

Expected:

- login succeeds;
- a `UserLoginSucceeded` event is created.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 4. Recent events page

Open:

```text
http://localhost:3000/events
```

Click:

```text
Load recent events
```

Expected:

- recent events are listed;
- at least one `UserLoginSucceeded` event is visible;
- no passwords or tokens are visible.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 5. Negative role check

Login as:

```text
sales1 / password
```

Open `/events` and click `Load recent events`.

Expected:

- access is denied or events are not loaded.

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

- Recent events page is a smoke-test page, not a final audit viewer.
- Filtering, CSV export and detailed audit search are not implemented.
- Only login success/failure events are recorded in this slice.

## Final decision

```text
Accepted / Not Accepted:
Accepted by:
Date:
Notes:
```