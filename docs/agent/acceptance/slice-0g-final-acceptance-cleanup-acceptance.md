# Slice 0G Final Acceptance / Cleanup - Acceptance Checklist

## Acceptance status

Not Started

Change to one of:

```text
Pass
Pass with minor issues
Fail - functional issue
Fail - usability issue
Blocked
```

## Preconditions

- Slice 0A through 0F are committed and pushed.
- Docker Desktop is running.
- Current directory is repository root.
- `.env` exists and SQL Server passwords match.

Check:

```powershell
Get-Content .env | Select-String "MSSQL"
```

Expected:

```text
MSSQL_SA_PASSWORD=ChangeThisStrongPassword123!
MSSQL_PASSWORD=ChangeThisStrongPassword123!
```

## 1. Git pre-check

Command:

```powershell
git status
```

Expected:

- no unexpected modified files before Slice 0G;
- helper scripts may be untracked but should not be committed.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 2. Fresh rebuild

Warning: this deletes local dev database volume.

Commands:

```powershell
docker compose down -v
docker compose up --build
```

Expected:

- db starts;
- backend starts;
- frontend starts;
- no crash loop.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 3. Service status

In a second PowerShell window:

```powershell
cd <your checkout>
docker compose ps
```

Expected:

- db: Up / healthy;
- backend: Up;
- frontend: Up.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 4. Backend health

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

## 5. Database health

Open:

```text
http://localhost:8000/api/platform/db-health
```

Expected:

- `status` is `ok`;
- database is `pbl_crm_hiring`;
- foundation tables are true:
  - app_user
  - role
  - user_role
  - workflow_status
  - business_event
  - document_metadata
  - alembic_version

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 6. Login smoke test

Open:

```text
http://localhost:3000/login
```

Login:

```text
admin1 / password
```

Expected:

- login successful;
- signed in user shown as Admin User 1;
- role shown as Admin.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 7. Account authentication smoke

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
- shows Admin User 1.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 8. Events smoke test

Open:

```text
http://localhost:3000/events
```

Click:

```text
Load recent events
```

Expected:

- Admin can load events;
- at least `UserLoginSucceeded` appears after login.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 9. Workflow status smoke test

Open:

```text
http://localhost:3000/workflow-statuses
```

Click:

```text
Load Account statuses
Load workflow modules
```

Expected:

- Account statuses appear;
- workflow modules appear;
- statuses include Draft, Qualified Prospect, Customer Activation Pending, Customer Active and Blacklisted.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 10. Document metadata smoke test

Open:

```text
http://localhost:3000/documents
```

Click:

```text
Create sample document metadata
Load recent document metadata
```

Expected:

- sample metadata is created;
- recent document metadata table shows at least one row;
- no binary file upload occurs.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 11. Role check spot test

Logout is not yet implemented. Clear token manually in browser console if needed:

```javascript
localStorage.removeItem("pbl_auth_token")
```

Login as:

```text
sales1 / password
```

Checks:

- workflow statuses should load;
- events should not load for unauthorized role if route is admin/read-only restricted.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 12. Automated backend tests

Command:

```powershell
docker compose exec backend pytest
```

Expected:

- all tests pass.

Actual result:

```text
Pass / Fail / Blocked:
Notes:
```

## 13. Helper files cleanup

Do not commit local helper scripts.

Optional local exclusion:

```powershell
Add-Content .git\info\exclude "apply-slice0*.ps1"
Add-Content .git\info\exclude "update-slice0-agent-docs.ps1"
```

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 14. Final Git check

Command:

```powershell
git status
```

Expected:

- only intended Slice 0G documentation files modified;
- helper scripts are untracked/ignored and not staged.

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

## Slice 1 readiness

Proceed to Slice 1 only if:

- this checklist passes;
- changes are committed and pushed;
- no unresolved Slice 0 regression remains.