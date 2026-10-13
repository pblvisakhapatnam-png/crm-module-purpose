# Slice 1B Account Create/List API - Acceptance Checklist

## Acceptance status

Not Started

Change to one of:

```text
Pass
Pass with minor issues
Fail - functional issue
Blocked
```

## 1. Migration/head check

Command:

```powershell
docker compose exec backend alembic heads
```

Expected:

- one Alembic head;
- current head remains `20260630_0006` unless a later accepted slice has added a migration;
- no new migration is expected for Slice 1B.

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
- new Account API tests pass;
- Slice 0 and Slice 1A tests remain green.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 3. Create draft Account API

Manual check:

```text
POST /api/accounts
```

Use an authenticated `sales1` token.

Example body:

```json
{
  "account_name": "Manual Slice 1B Draft Account",
  "qualification_source": "enquiry",
  "source_remarks": "Manual acceptance check."
}
```

Expected:

- HTTP 201;
- response contains `account.public_id`;
- `account.account_status_code` is `DRAFT`;
- response event is `AccountCreated`;
- event `record_type` is `business_party`.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 4. Create qualified-prospect Account API

Manual check:

```text
POST /api/accounts
```

Use an authenticated `manager1` token.

Example body:

```json
{
  "account_name": "Manual Slice 1B Qualified Prospect",
  "account_status_code": "QUALIFIED_PROSPECT",
  "qualification_source": "rfq"
}
```

Expected:

- HTTP 201;
- response status is `QUALIFIED_PROSPECT`.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 5. List Accounts API

Manual check:

```text
GET /api/accounts?limit=20
```

Expected:

- HTTP 200 for authenticated operational/read users;
- response is a list;
- newly created Account appears in the list.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 6. Get Account API

Manual check:

```text
GET /api/accounts/{public_id}
```

Expected:

- HTTP 200 for an existing Account public ID;
- HTTP 404 for a valid UUID that does not exist;
- HTTP 422 for an invalid UUID path value.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 7. Validation checks

Checks:

```text
POST /api/accounts with CUSTOMER_ACTIVE should return 422.
POST /api/accounts with invalid PAN should return 422.
POST /api/accounts as finance1 should return 403.
GET /api/accounts without token should return 401.
```

Expected:

- backend enforces the rule;
- frontend-only validation is not relied upon.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## 8. Manual non-regression check

Open:

```text
http://localhost:3000/login
http://localhost:3000/accounts
http://localhost:3000/documents
http://localhost:3000/workflow-statuses
```

Expected:

- existing pages still load;
- no Account frontend create/list behavior is expected from this slice.

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