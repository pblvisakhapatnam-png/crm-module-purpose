# Slice 1A Account / business_party Data Model - Acceptance Checklist

## Acceptance status

Not Started

Change to one of:

```text
Pass
Pass with minor issues
Fail - functional issue
Blocked
```

## 1. Migration check

Command:

```powershell
docker compose exec backend alembic upgrade head
```

Expected:

- migration completes;
- `business_party` table exists.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 2. Backend tests

Command:

```powershell
docker compose exec backend pytest
```

Expected:

- all tests pass;
- new business_party foundation tests pass;
- Slice 0 tests remain green.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 3. Manual non-regression check

Open:

```text
http://localhost:3000/login
http://localhost:3000/accounts
http://localhost:3000/workflow-statuses
```

Expected:

- existing Slice 0 pages still work;
- no visible UI change is expected from Slice 1A.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## Final acceptance decision

```text
Accepted / Not Accepted:
Accepted by:
Date:
Notes:
```