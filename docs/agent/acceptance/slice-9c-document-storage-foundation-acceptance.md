# Slice 9C Acceptance - Document Storage Foundation

Written so a later tester can perform regression/UAT without this session's chat history.

## Preconditions

Stack running, Alembic at `20260908_0033 (head)` before this slice. This slice adds a
migration and a new Python dependency (`python-multipart==0.0.32`, required for FastAPI
file-upload parsing); after merging, rebuild the backend image before testing:

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| New Slice 9C regression file | `docker compose exec backend pytest tests/test_slice_9c_document_storage_foundation.py -q` | 39 passed (21 as first delivered + 15 from correction pass 1 + 2 from pass 2 + 1 from pass 3) |
| Pre-existing documents API tests (unmodified) | `docker compose exec backend pytest tests/test_documents.py -q` | 4 passed |
| Route migration guard (pins all 6 document routes to their exact permissions - the 4 tightened via `POST_BASELINE_TIGHTENED_ROUTES` and the 2 new via `POST_BASELINE_NEW_ROUTES` - and the frozen counts) | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py -q` | 99 passed |
| Post-baseline permission catalogue | `docker compose exec backend pytest tests/test_authorization_post_baseline_catalogue.py -q` | 10 passed |
| Slice 9D foundation (2 assertions corrected by this slice - see continuity note) | `docker compose exec backend pytest tests/test_slice_9d_interaction_foundation.py -q` | 19 passed |
| Full backend regression | `docker compose exec backend pytest -q` | 1229 passed, 0 failed |
| **Committed-credential check** | `python scripts/check_tracked_secrets.py` | no findings |
| **Contract fixtures** | `python scripts/validate_contract_fixtures.py` | all rules passed |
| **Repository script tests** | `python -m unittest discover -s scripts/tests` | 58 passed |
| Alembic head | `docker compose exec backend alembic current` | `20260908_0034 (head)` |
| Migration reversible | `docker compose exec backend alembic downgrade -1` then `alembic upgrade head` | the 6 new columns, the CHECK constraint, the partial unique index and the 3 permissions/18 grants are removed then restored; `alembic current` returns to `20260908_0034 (head)` |
| Schema inspected directly | `psql -c "\d document_metadata"` | 6 new nullable columns, `ck_document_metadata_local_upload_has_bytes` CHECK constraint, `ux_document_metadata_storage_provider_key` partial unique index, all present exactly as designed |
| Permission seed inspected directly | `SELECT ... FROM authz_permission JOIN authz_role_permission ...` | 18 rows (3 permissions x 6 roles) for `DOCUMENT_READ`/`DOCUMENT_UPLOAD`/`DOCUMENT_CONTENT_READ` |
| Frontend typecheck | `MSYS_NO_PATHCONV=1 docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run typecheck` | clean |
| Frontend tests | same, `npm test` | 54 passed (unchanged - no new public URL was added) |
| Frontend build | same, `npm run build` | clean |
| **Dependency audit** (the gate that failed CI on the original `0.0.20` pin) | the workflow's `pip-audit --strict --requirement backend/requirements.txt` with the deferral list applied | `No known vulnerabilities found, 11 ignored` |
| **Storage root is configurable, not container-only** | `docker compose exec -e DOCUMENT_STORAGE_ROOT=/tmp/... backend pytest tests/test_slice_9c_document_storage_foundation.py -q` | 39 passed - proves the suite does not depend on the container-absolute default, which is what broke hosted CI |
| App import / route registration | `python -c "from app.main import app; ..."` | 6 `/api/documents/*` routes present; 98 total `/api/` routes (up from 96) |
| **Test suite leaves no stored objects** (correction pass 2) | `docker compose exec backend sh -c 'find /app/document-store -type f \| wc -l'`, before and after `pytest -q` | identical counts. The 9C module also polices this itself via a module-scoped autouse fixture, so a leaking test fails rather than accumulating files silently |

## Manual happy path

Test user `admin1` / `password` (ADMIN). Starting page: `/documents`.

1. Open `/documents`. Click **Load recent document metadata** - confirm the list loads (may be
   empty or show pre-existing rows).
2. Under **Upload a file**, choose a small PDF or image file (under 25 MB) and click **Upload**.
   Confirm a green "Uploaded ..." message appears directly under the Upload button (not only at
   the top of the page), and the list refreshes to show the new row with a **Download** button
   in its Content column.
3. Click **Download** on that row. Confirm the browser downloads the file with its original
   file name, and that its content matches what was uploaded.
4. Click **Create sample document metadata** (the pre-existing `external_link` sample). Confirm
   its row shows "Not stored by this application" in the Content column instead of a Download
   button - external_link records have no application-managed bytes to download.

Expected result: a real file round-trips through upload and download; a metadata-only pointer
record correctly shows it has nothing to download.

## Manual permission path

Test users: `admin1` / `password` (ADMIN) and `finance1` / `password` (FINANCE_USER).

1. As `admin1`, create a document via `POST /api/documents/metadata` (or the sample-create
   button) with `linked_record_type = "interaction"` and any UUID as
   `linked_record_public_id`.
2. As `finance1`, call `GET /api/documents/by-record/interaction/{that-uuid}`. Confirm the
   document is **listed** (Finance holds `INTERACTION_READ`).
3. As `finance1`, call `GET /api/documents/{public_id}/content` for that same document. Confirm
   this is **rejected with 403** (Finance lacks `INTERACTION_CONTENT_READ`, the Slice 9D grant
   that separately gates customer message content).
4. As `admin1` (who holds both grants), repeat step 3 and confirm it succeeds (or returns 409
   if the document is `external_link` rather than `local_upload`, which is the correct response
   for a document with no application-managed bytes).

Expected result: metadata visibility and content-download are governed by separate,
independently testable permission checks, exactly as designed.

## Manual validation path

1. Attempt `POST /api/documents/metadata` with `"storage_mode": "local_upload"`. Confirm `422`
   with a message directing the caller to the upload route instead.
2. Attempt `POST /api/documents/upload` with a file larger than 25 MB. Confirm `413`.
3. Attempt `POST /api/documents/upload` with a file named `something.exe`. Confirm `422`.
4. As any authenticated user without a specific document's linked-record permission (or against
   an unmapped `linked_record_type` such as a typo), attempt
   `GET /api/documents/by-record/{unmapped_type}/{uuid}`. Confirm `403` - fail-closed, not a
   silent empty list.

Added by correction pass 1 (each of these was a real defect, reproduced before it was fixed):

5. Upload a file whose multipart part declares **no** content type at all. Confirm `422` - a
   missing declared type is a rejection, not a skipped check. (Previously returned `201`.)
6. Upload with a `linked_record_type` longer than 100 characters. Confirm `422` with a clear
   message, **not** `500`. Then confirm nothing was left behind: no `document_metadata` row, no
   `business_event`, and no new file under `DOCUMENT_STORAGE_ROOT`.
7. Upload a file with a Unicode name such as `quotation-报价.pdf`, then download it. Confirm the
   download succeeds (`200`) and the `Content-Disposition` header is ASCII-only and carries
   `filename*=UTF-8''` with the percent-encoded original name. (Previously the download failed
   outright with `UnicodeEncodeError`.)
8. Take an uploaded document and set its `storage_provider_code` to a value this deployment does
   not register (for example `sharepoint_future`) directly in the database, then attempt the
   download. Confirm `409` with a message naming the unresolvable provider - the row's own
   recorded provider governs, and an unknown one fails closed rather than silently falling back
   to the configured provider.

## Known limitations / deferred (see `docs/agent/DEFERRED_REQUIREMENTS.md`)

- No audit record of who downloaded a document's content.
- Retention (`retention_due_at`) is shape-only; nothing purges against it.
- A document's `linked_record_type`/`linked_record_public_id` is not validated against the
  target record's actual existence - unchanged pre-9C behavior, not introduced by this slice.
- SharePoint integration, versioning/locking, and approval/verification workflow remain out of
  scope, as recorded in the frozen slice specification.
