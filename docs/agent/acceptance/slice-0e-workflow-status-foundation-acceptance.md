# Slice 0E Workflow Status Foundation - Acceptance Checklist

## Acceptance status

Not Started

## Target duration

15-20 minutes.

## Preconditions

- Slice 0D has been committed and pushed.
- Docker Desktop is running.
- Current working directory is repository root.
- `.env` exists and SQL Server passwords match.

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
http://localhost:3000/events
```

Expected: prior Slice 0A-0D checks still pass.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 3. Workflow status page

Open:

```text
http://localhost:3000/login
```

Login as:

```text
admin1 / password
```

Then open:

```text
http://localhost:3000/workflow-statuses
```

Click:

```text
Load Account statuses
```

Expected:

- Account statuses load;
- `Draft`, `Qualified Prospect`, `Customer Activation Pending`, `Customer Active`, and `Blacklisted` are visible.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 4. Workflow modules

On `/workflow-statuses`, click:

```text
Load workflow modules
```

Expected:

- `business_party` is visible.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 5. Sales user read access

Login as:

```text
sales1 / password
```

Open `/workflow-statuses` and load Account statuses.

Expected:

- statuses load successfully.

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

- Statuses are seeded through migration, not editable in UI.
- This slice does not implement status transition rules.
- This slice does not implement Account records.

## Final decision

```text
Accepted / Not Accepted:
Accepted by:
Date:
Notes:
```