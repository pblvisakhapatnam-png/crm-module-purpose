# Slice 0F Document Metadata Foundation - Acceptance Checklist

## Acceptance status

Not Started

## Target duration

10-15 minutes.

## Preconditions

- Docker Desktop is running.
- Slice 0E is committed or at least working locally.
- Local stack starts successfully.
- Login works.

## Manual checks

### 1. Start stack

```powershell
docker compose down
docker compose up --build
```

Expected:

- db is up;
- backend is up;
- frontend is up.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 2. Backend health

Open:

```text
http://localhost:8000/api/health
http://localhost:8000/api/platform/db-health
```

Expected:

- both respond with status ok.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 3. Login

Open:

```text
http://localhost:3000/login
```

Login:

```text
admin1 / password
```

Expected:

- login succeeds;
- token is stored in browser storage.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 4. Documents page

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

- sample document metadata is created;
- recent document metadata table displays at least one row;
- no binary file upload is required;
- no password or token is displayed.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

### 5. API smoke check

In browser or API client, call with a bearer token:

```text
GET /api/documents/types
GET /api/documents/recent?limit=20
```

Expected:

- authenticated request succeeds;
- anonymous request fails.

Result:

```text
Pass / Fail / Blocked:
Notes:
```

## Automated checks

Run:

```powershell
docker compose exec backend pytest
```

Expected:

```text
all tests pass
```

## Known limitations

- Stores metadata only.
- Does not upload files.
- Does not connect to SharePoint.
- Uses a sample Account UUID before Account module exists.

## Final decision

```text
Accepted / Not Accepted:
Accepted by:
Date:
Notes:
```