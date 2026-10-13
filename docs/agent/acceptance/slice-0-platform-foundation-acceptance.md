# Slice 0 Platform Foundation - Acceptance Checklist

## Acceptance status

```text
Not Started
```

Change to one of:

```text
Pass
Pass with minor issues
Fail - functional issue
Fail - usability issue
Blocked
```

## Preconditions

- Repository exists locally.
- Git repository has initial skeleton committed.
- Docker Desktop is installed and running.
- `.env` file exists, copied from `.env.example`.
- SQL Server password meets SQL Server complexity requirements.

## Human test duration target

10-20 minutes.

## Test user

If auth is implemented:

```text
username: admin1
role: Admin
```

or seeded demo user specified by implementation.

## Manual acceptance steps

### 1. Start local stack

Command:

```powershell
docker compose up --build
```

Expected:

- SQL Server container starts.
- Backend container starts.
- Frontend container starts.
- No immediate crash loop.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 2. Backend health endpoint

Open:

```text
http://localhost:8000/api/health
```

Expected response:

```json
{
  "status": "ok"
}
```

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 3. Frontend home page

Open:

```text
http://localhost:3000
```

Expected:

- Page loads.
- Prototype/project name is visible.
- No major console/runtime error.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 4. Login page or placeholder

Open:

```text
http://localhost:3000/login
```

Expected:

- Login page or placeholder is visible.
- If login is implemented, valid seeded user can log in.
- Invalid login is rejected.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 5. Database persistence check

Stop and restart:

```powershell
docker compose down
docker compose up
```

Expected:

- SQL Server volume persists.
- App still starts.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 6. Documentation check

Confirm these files exist and have real content:

```text
docs/agent/PROJECT_OVERVIEW.md
docs/agent/ARCHITECTURE_DECISIONS.md
docs/agent/CODING_STANDARDS.md
docs/agent/TESTING_STRATEGY.md
docs/agent/UI_UAT_GUIDELINES.md
docs/agent/AGENT_WORKFLOW.md
docs/agent/contracts/platform-foundation.md
docs/agent/contracts/workflow-and-events.md
docs/agent/contracts/documents.md
docs/agent/slices/slice-0-platform-foundation.md
docs/agent/acceptance/slice-0-platform-foundation-acceptance.md
```

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 7. Git check

Run:

```powershell
git status
```

Expected:

- Only intended Slice 0 changes are present before commit.
- No unrelated generated junk such as `node_modules`, `.venv`, `.next`, or local DB files are staged.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## Automated tests

Record commands run:

```text
Backend tests:
Frontend tests:
Other checks:
```

Expected:

- Tests pass or missing tests are explicitly documented as not yet implemented in Slice 0.

## Known limitations

Record any limitations accepted for Slice 0:

```text
-
-
```

## Final acceptance decision

```text
Accepted / Not Accepted:
Accepted by:
Date:
Notes:
```
