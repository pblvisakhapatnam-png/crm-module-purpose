# Slice 9C - Document Storage Foundation

## Status

Specification frozen 8 September 2026. Second of the three agreed CRM pilot minimums
(9D done, 9C now, 9E after). Foundation Slice Mode.

Branch: `slice-9c-document-storage-foundation`.
Baseline commit: `8896ffd`.
Alembic parent: `20260908_0033`. This slice takes **`20260908_0034`** by explicit owner
decision of 8 September 2026; Hiring `7C` moves to `20260908_0035`. See
`docs/continuity/NEXT_STEPS.md`.

## Why this slice exists

Two defects, both verified directly against `main` at `8896ffd` rather than taken on trust.

### 1. `local_upload` is a metadata lie

`backend/app/modules/documents/routes.py:30` declares:

```python
ALLOWED_STORAGE_MODES = {"local_upload", "external_link", "future_sharepoint"}
```

There is **no file upload anywhere in the backend**. `grep -rn "UploadFile" backend/app/`
returns nothing; so do `File(` and `multipart`. A caller can therefore record a document as
`storage_mode = "local_upload"` with `status = "Uploaded"` and nothing is stored anywhere.
The metadata asserts a file exists. No file does, and none ever did.

Verified harmless to fix: `document_metadata` holds 2 rows, both
`linked_record_type = 'account'`, and **zero** rows with `storage_mode = 'local_upload'`.
Closing the hole breaks no existing data.

### 2. Any logged-in user can read every document in the system

All four `/api/documents/*` routes appear in `BASELINE_UNGATED_ROUTES` in
`backend/tests/fixtures/pf_1a_e1_baseline_authorization.py:342-345` - authenticated-only,
with no role distinction at all. A `MANAGEMENT_READ_ONLY` user can today call
`GET /api/documents/recent` and enumerate every document in the system, including file names.
File names alone leak: `Acme-PAN-card.pdf` discloses both the customer and the nature of the
document.

### 3. Three further defects in the same module, all the same shape

Found while verifying the two above. All are in files this slice rewrites anyway, so they are
in scope under the "same module, not unrelated churn" rule - not scope creep.

- **A latent auth downgrade.** `_load_auth_dependency()` walks a list of candidate import
  paths and, if none resolve, falls back to `_fallback_current_user`, which accepts *any*
  string beginning with `bearer ` without validating it, returning `public_id: None` and
  `roles: []`. It resolves to the real dependency today (verified by importing it), so there
  is no live hole - but a rename of `app.modules.identity.dependencies` would silently
  downgrade every document route to "any bearer-shaped string is accepted".
- **JSON injection in the business event payload.** `routes.py:288-292` builds the event
  payload by raw f-string interpolation. A `document_type` containing a double quote forges or
  corrupts the stored JSON. This is the same class as the Slice 9D finding that a
  delimiter-joined string is not an unambiguous encoding.
- **Layering.** `routes.py` is 333 lines against a 1-line `service.py` and a 1-line
  `repository.py`, with raw `text()` SQL inline in the route handlers.

## Owner decisions, 8 September 2026

Put in plain business language before any design work, per `AGENTS.md`.

| # | Decision | Answer |
| --- | --- | --- |
| 1 | Who may download a file | Must be allowed to see the record it is attached to, **plus** a separate grant for files on customer conversations |
| 2 | Where files live, and backup | On the application server in a dedicated volume, backed up separately from the database |
| 3 | Size and type limits | Up to 25 MB; business documents and images only |
| 4 | Retention | Not decided now - record the shape, decide before real use (ADR-015 precedent) |
| 5 | Legacy route access | Close it too - tighten the four existing document routes |
| 6 | Migration slot | 9C takes `0034`; `7C` moves to `0035` |

Decision 5 changes PF-1A-E1 baseline evidence and was approved explicitly for that reason.
See "Baseline evidence" below for how it is recorded without corrupting the frozen snapshot.

## In scope

- A provider-neutral storage abstraction with one local provider behind it.
- Real file upload and download.
- A **database constraint** making the `local_upload` lie unrepresentable.
- Permission-gating every document route, including the four legacy ones.
- Record-scoped download authorization, fail-closed.
- Repairing the module's layering and the three defects above.

## Explicitly not in scope

SharePoint integration itself; document versioning and locking; approval/verification
workflow; OCR; 9E quotation generation; read-access auditing (see "Deferred" below).

## Design

### Storage abstraction

```text
backend/app/modules/documents/storage/
    __init__.py   get_storage_provider() factory, selected by configuration
    base.py       DocumentStorageProvider ABC, StoredObject, provider exceptions
    local.py      LocalFilesystemStorageProvider
```

```python
class DocumentStorageProvider(ABC):
    provider_code: str
    def save(self, *, storage_key: str, stream: BinaryIO, content_type: str) -> StoredObject: ...
    def open(self, *, storage_key: str) -> BinaryIO: ...
    def exists(self, *, storage_key: str) -> bool: ...
    def delete(self, *, storage_key: str) -> None: ...
```

`StoredObject` carries `storage_key`, `byte_size`, `checksum_sha256`.

Two rules make the later SharePoint move a provider swap rather than a rewrite:

- **The service generates `storage_key`, never the caller**, and the key is opaque to the
  provider's internal layout (`YYYY/MM/<uuid><ext>`). The local provider maps a key to a path
  under a configured root; a SharePoint provider would map the same key to a drive item. No
  filesystem concept appears in the interface or in `document_metadata`.
- **The provider refuses an escaping key.** It resolves the final path and verifies it is
  inside the configured root, rejecting anything that is not. "We only generate safe keys" is
  an assertion, not a control; the provider must be the thing that refuses.

Configuration: `DOCUMENT_STORAGE_ROOT`, default `/app/document-store`, backed by a named
Docker volume so files survive restarts and rebuilds. That volume is the backup unit under
decision 2.

### Schema - migration `20260908_0034`

New nullable columns on `document_metadata`:

```text
storage_provider_code   VARCHAR(50)    which provider holds the bytes
storage_key             VARCHAR(500)   opaque provider key, never a caller-supplied path
content_type            VARCHAR(255)
byte_size               BIGINT
checksum_sha256         CHAR(64)       integrity, and lets a future migration verify a copy
retention_due_at        TIMESTAMPTZ    shape only; never set in the pilot (decision 4)
```

And the single most important line in the slice:

```sql
CONSTRAINT ck_document_metadata_local_upload_has_bytes CHECK (
    storage_mode <> 'local_upload'
    OR (storage_provider_code IS NOT NULL
        AND storage_key IS NOT NULL
        AND byte_size IS NOT NULL
        AND checksum_sha256 IS NOT NULL)
)
```

A row cannot claim `local_upload` unless bytes were actually stored. A direct `INSERT` that
bypasses the API cannot create the lie either. Slice 9D established that Pydantic validation
is not a database constraint - a direct insert bypassed it - so the invariant that defines
this slice's whole premise is enforced in the database, not in a validator.

### Permissions

Three new codes, added to `POST_BASELINE_ROLE_PERMISSION_MATRIX` in
`backend/app/modules/authorization/contract.py` with descriptions, and seeded in this slice's
own migration. `ROLE_PERMISSION_COMPATIBILITY_MATRIX` and its frozen 31 / 110 / 76 counts are
**not touched**; the effective matrix is the calculated union. Slice 9D is the worked example.

```text
DOCUMENT_READ           use the documents API and see document metadata
DOCUMENT_UPLOAD         upload a file, or record document metadata
DOCUMENT_CONTENT_READ   download the stored bytes
```

`DOCUMENT_READ` is granted to all six roles. That is deliberate and is **not** where the
tightening happens: it reproduces today's authenticated-only reach so nothing regresses, and
the real narrowing is the record-scoped check below. `DOCUMENT_CONTENT_READ` is the download
grant and is narrower. *(Corrected 7 October 2026, TB-1 TB1-904: as a grant it is not narrower - it
is granted to the same six roles as `DOCUMENT_READ`. What narrows a download is the record-scoped
check below: every download needs the read permission of the record the document is linked to, and a
document linked to a conversation (`interaction`) also needs `INTERACTION_CONTENT_READ`, which
`FINANCE_USER` does not hold - `DOCUMENT_LINK_EXTRA_CONTENT_PERMISSION` in `documents/contract.py`.)*

### Record-scoped authorization, fail-closed

The route-permission guard permits **exactly one** `require_permission(...)` dependency per
route, and forbids reading `.role_codes` inside a route module. So the second, record-scoped
check happens in `service.py` via `has_permission(...)`, exactly as Slice 9D placed its
content-redaction check there for the same two reasons.

```python
DOCUMENT_LINK_READ_PERMISSION: dict[str, str] = {
    "account":          ACCOUNT_READ,
    "business_party":   ACCOUNT_READ,
    "lead":             LEAD_READ,
    "opportunity":      OPPORTUNITY_READ,
    "commercial_offer": COMMERCIAL_OFFER_READ,
    "work_order":       WORK_ORDER_READ,
    "interaction":      INTERACTION_READ,
}

DOCUMENT_LINK_EXTRA_CONTENT_PERMISSION: dict[str, str] = {
    "interaction": INTERACTION_CONTENT_READ,
}
```

**A `linked_record_type` absent from that map denies. It never allows.** This is the most
likely place in the slice for a silent bypass, because `linked_record_type` is free-text
`VARCHAR(100)` with no constraint and the two modules already disagree on vocabulary: existing
`document_metadata` rows say `account`, while Slice 9D's canonical Account link type is
`business_party`. Both are mapped above for that reason. The fail-closed rule gets its own
regression test, written to fail first.

The interaction rule implements decision 1's second half. A document attached to a customer
conversation inherits that conversation's sensitivity, so downloading it requires
`INTERACTION_CONTENT_READ` - the same grant that already controls who may read the message
body. Without this, a download route would reopen the leak 9D closed: the same
"redaction defeated by a pointer" shape, with an attachment as the pointer.

### Routes

Existing four, tightened:

```text
GET  /api/documents/types                                  require_permission(DOCUMENT_READ)
GET  /api/documents/recent                                 require_permission(DOCUMENT_READ)
                                                           + service filters out rows whose
                                                             linked record the caller may not read
GET  /api/documents/by-record/{record_type}/{public_id}    require_permission(DOCUMENT_READ)
                                                           + service record-scoped check
POST /api/documents/metadata                               require_permission(DOCUMENT_UPLOAD)
                                                           + REJECTS storage_mode=local_upload
```

`POST /api/documents/metadata` stores no bytes, so it may no longer claim `local_upload`.
That mode becomes reachable only through the upload route. This is the API-level half of the
fix; the CHECK constraint is the half that holds when the API is bypassed.

New two:

```text
POST /api/documents/upload                 multipart; require_permission(DOCUMENT_UPLOAD)
GET  /api/documents/{public_id}/content    require_permission(DOCUMENT_CONTENT_READ)
                                           + record-scoped + interaction-content check
```

### Limits

25 MB; PDF, Word, Excel, common images, plain text and CSV. Validated on **both** declared
content type and file extension, rejecting a mismatch. Size is enforced by **counting bytes as
they stream**, never by trusting the declared `Content-Length` header - a declared header is
an assertion, and this slice does not accept assertions as controls.

### Baseline evidence

Decision 5 tightens four routes the PF-1A-E1 snapshot records as ungated. The guard at
`backend/tests/test_authorization_route_migration_guard.py:995-1002` explicitly anticipates
this - "a formerly-ungated route may be deliberately tightened later" - and requires the
change be recorded rather than made silently.

`BASELINE_UNGATED_ROUTES` is **left byte-identical**. It is a historical statement about what
was true at baseline, and that remains true forever. The tightening is recorded additively in
a new `POST_BASELINE_TIGHTENED_ROUTES` set, mirroring exactly how
`POST_BASELINE_ROLE_PERMISSION_MATRIX` sits alongside the frozen permission matrix. The
guard's ungated branch consults it. This preserves every frozen count and every frozen
snapshot while recording the deliberate decision.

### Layering repair

```text
contract.py     new - constants, the two permission maps, limits, allowed types
repository.py   all SQL (currently 1 line)
service.py      business rules, permission checks, storage orchestration
routes.py       HTTP wiring only
storage/        provider abstraction
```

Also: `_load_auth_dependency()` and its fallback are deleted in favour of importing
`require_permission` directly, as Slice 9D does. The hand-built JSON payload is replaced with
`record_business_event(..., event_payload={...})`, which encodes properly.

### Events

`DocumentUploaded` on a successful upload, carrying metadata only - never the file's bytes.
The existing `DocumentMetadataCreated` event is preserved.

## Deferred

**Read-access auditing.** No record is kept of who downloaded a file. Slice 9D took exactly
this position for message bodies and recorded it as an open policy item that must be resolved
before real customer correspondence is in production use. Documents attached to those
conversations inherit the identical question, so 9C extends that one existing
`DEFERRED_REQUIREMENTS.md` entry to cover documents rather than inventing a second, divergent
answer to the same policy question.

**Retention.** Shape only, per decision 4. `retention_due_at` exists and is never set. Nothing
is deleted automatically.

**Files and database drifting apart after a restore.** The volume and the database are backed
up on separate schedules under decision 2, so a restore can leave metadata referencing bytes
that are absent, or the reverse. `checksum_sha256` and `storage_key` make the mismatch
detectable. A reconciliation tool is not in this slice.

## Test plan - each written to fail first, against the defective code

1. A direct `INSERT` of `storage_mode='local_upload'` without bytes is refused by the
   **database constraint**, bypassing the API entirely.
2. `POST /api/documents/metadata` rejects `storage_mode=local_upload`.
3. Download denies when the caller lacks the linked record's own read permission.
4. Download of an interaction-attached document denies without `INTERACTION_CONTENT_READ`.
5. An unknown `linked_record_type` denies - fail-closed.
6. `GET /api/documents/recent` omits rows whose linked record the caller may not read.
7. The storage provider refuses a traversal-shaped `storage_key`.
8. An oversize upload is rejected by streamed byte count, with a **lying** `Content-Length`.
9. A `document_type` containing a double quote produces valid, unforged event JSON.
10. The route inventory guard passes, and the frozen 31 / 110 / 76 counts are unchanged.

## Implementation record

Implemented on branch `slice-9c-document-storage-foundation`, base commit `3faae84` (this
frozen specification). Model: PBL's design lead designed and froze the specification above and put the
five decisions to the project owner; PBL's development team built it.

### Files changed

The complete candidate is **25 paths: 16 modified, 9 new.** (Corrected in correction pass 1 -
the first version of this list omitted the acceptance record and continuity note, and collapsed
the three `storage/` files into one line, so it did not reconcile against `git status`.)

Modified (16):

```text
backend/app/core/config.py                                  additive (2 new settings)
backend/app/modules/authorization/contract.py               additive (3 new permission codes)
backend/app/modules/documents/models.py                     kept in sync with the migration
backend/app/modules/documents/repository.py                 rewritten (was a 1-line stub)
backend/app/modules/documents/routes.py                     rewritten (thin HTTP wiring only)
backend/app/modules/documents/schemas.py                    updated
backend/app/modules/documents/service.py                    rewritten (was a 1-line stub)
backend/requirements.txt                                    additive (python-multipart)
backend/tests/test_authorization_route_migration_guard.py   additive
backend/tests/test_slice_9d_interaction_foundation.py       2 assertions corrected (see below)
docker-compose.yml                                          additive (document-store volume)
docs/agent/DEFERRED_REQUIREMENTS.md                         extended, not duplicated
docs/agent/contracts/documents.md                           updated
docs/agent/slices/slice-9c-document-storage-foundation.md   this file
docs/continuity/NEXT_STEPS.md                               updated
frontend/src/pages/DocumentsPage.tsx                        upload/download UI
```

New (9):

```text
backend/alembic/versions/20260908_0034_document_storage_foundation.py
backend/app/modules/documents/contract.py
backend/app/modules/documents/storage/__init__.py
backend/app/modules/documents/storage/base.py
backend/app/modules/documents/storage/local.py
backend/tests/fixtures/post_baseline_tightened_routes.py            NOT frozen evidence
backend/tests/test_slice_9c_document_storage_foundation.py
docs/agent/acceptance/slice-9c-document-storage-foundation-acceptance.md
docs/continuity/SLICE_9C_DOCUMENT_STORAGE_FOUNDATION.md
```

### What changed from the frozen design, and why

Two corrections made during the build itself, both caught by self-review before any test ran
against them:

- **`db.rollback()` was missing on the upload failure path.** The first draft of
  `upload_document` deleted the orphaned file on an insert failure but never rolled back the
  session, which would have left it in a failed-transaction state for whatever the caller did
  next. Fixed by wrapping insert + event + commit in one try/except that rolls back and cleans
  up the file on any failure in that block, matching the interactions module's own pattern.
- **A dead `ALLOWED_STORAGE_MODES` tuple.** The design's `contract.py` sketch implied a
  full-three-value storage-mode tuple; nothing in the actual service layer ever needed it once
  `METADATA_ROUTE_ALLOWED_STORAGE_MODES` and `STORAGE_MODE_LOCAL_UPLOAD` existed separately.
  Removed rather than left as unused code.

Everything else matches the frozen design exactly: the six routes, the three permission codes,
the two link-permission maps, the CHECK constraint, the `POST_BASELINE_TIGHTENED_ROUTES`
mechanism, and the 25 MB / extension-plus-content-type upload limits.

### Test results

```text
docker compose exec backend pytest -q
```

Test counts for `test_slice_9c_document_storage_foundation.py`, stated plainly because an
earlier version of this record got the arithmetic wrong (independent review, correction pass 2):

```text
21   as first delivered
+15  correction pass 1 regression tests          -> 36
+2   correction pass 2 cleanup regression tests  -> 38
```

The pass-1 figure was previously written as "22 original + 14", which is wrong twice over: the
file had 21 tests, not 22, and the pass added 15, not 14. (The confusion came from the
watch-it-fail run, where 14 of the 15 new tests failed and the fifteenth -
`test_upload_with_a_mismatched_declared_content_type_is_still_rejected` - already passed against
the defective code, so it was counted in that run's "22 passed" rather than among the failures.)

Full backend regression: **1229 passed, 0 failed** after correction pass 3 (1228 after pass 2, 1226 after pass 1,
1211 as first delivered). The pass-2 run also started and finished with **zero** files in the
configured storage root - the direct proof that the leak is closed, since the same run would
previously have left two behind.
The full run surfaced two pre-existing failures in `test_slice_9d_interaction_foundation.py` -
not a 9C defect, but a real bug in 9D's own tests exposed by 9C's use of the shared,
by-design-growing `POST_BASELINE_ROLE_PERMISSION_MATRIX`. See "A real bug found in Slice 9D's
own tests" in `docs/continuity/SLICE_9C_DOCUMENT_STORAGE_FOUNDATION.md` for the full account;
both are corrected in that same test file, restoring it to 19 passed while preserving 9D's
original intent exactly.

Per-file: `test_slice_9c_document_storage_foundation.py` 39 passed;
`test_documents.py` (pre-existing, unmodified) 4 passed;
`test_authorization_route_migration_guard.py` 99 passed;
`test_authorization_post_baseline_catalogue.py` 10 passed;
`test_slice_9d_interaction_foundation.py` 19 passed (post-correction).

Repository validators: `python scripts/check_tracked_secrets.py` (no findings, 857 files
scanned), `python scripts/validate_contract_fixtures.py` (all rules passed, 7 fixtures),
`python -m unittest discover -s scripts/tests` (58 passed).

Frontend: `npm run typecheck` clean, `npm test` 54 passed (unchanged - no new public URL),
`npm run build` clean.

### Manual verification

- `docker compose up -d --build --force-recreate backend` rebuilt cleanly; the new migration
  (`20260908_0034`) applied automatically on container startup, taking `alembic current` to
  `20260908_0034 (head)`, matching `alembic heads`.
- `app.main.app` imports without error; all six `/api/documents/*` routes are present in the
  live route table (98 total `/api/` routes, up from 96 pre-9C).
- `alembic downgrade -1` then `alembic upgrade head`: both clean; schema inspected directly
  afterward (`\d document_metadata`) shows all 6 new columns, the
  `ck_document_metadata_local_upload_has_bytes` CHECK constraint and the
  `ux_document_metadata_storage_provider_key` partial unique index exactly as designed.
  Permission seed verified directly: 18 grants (3 permissions x 6 roles).
- The `document-store` named volume was created by Compose and is writable by the container.
- **Real end-to-end HTTP smoke test against the live running backend** (not a unit test - actual
  `curl` requests against `http://localhost:8000`, a real 9600-byte file, real bearer tokens
  from real logins as `admin1` and `finance1`):
  - Uploaded a real file: `201`, response `byte_size` and `checksum_sha256` both matched the
    file's actual SHA-256 exactly.
  - Downloaded it back: `200`, correct `Content-Disposition: attachment; filename="..."` header,
    and the downloaded bytes were **byte-for-byte identical** (`sha256sum` match) to the
    original file.
  - Created a document linked to a fake interaction id; `finance1` could list it
    (`INTERACTION_READ`, 200) but was denied its content (`INTERACTION_CONTENT_READ` absent,
    `403`).
  - `storage_mode: "local_upload"` via `POST /api/documents/metadata`: `422`.
  - Uploading a file named `virus.exe`: `422`.
  - `GET /api/documents/recent` with no `Authorization` header: `401`.
  - All smoke-test rows deleted from the database afterward. (The stored *files* from that
    manual session were deleted too - but note that a later full-suite run then recreated two
    of its own, which is the leak correction pass 2 fixes. Any statement about the storage
    root's contents is only true as of the run it was taken after; see correction pass 2.)

## Correction pass 1 (independent review, 8 September 2026)

The independent review returned `CORRECTION_REQUIRED` with five material findings. All five were
confirmed by reading the candidate, and the two the reviewer had reproduced were independently
reproduced again here against the running backend before anything was changed. Every fix has a
regression test that was written first and watched failing against the defective code (14 new
tests, all failing before the fix, all passing after).

**1. An upload with no declared content type was accepted.** The check read
`if declared_content_type and declared_content_type != expected_content_type:` - the `and`
short-circuited on an absent or empty MIME type, so a multipart part carrying no content type
skipped that half of the validation entirely. Reproduced: `201`. The frozen specification
requires both halves ("Validated on **both** declared content type and file extension"), so a
missing type is now a rejection, not a skipped check. Now `422`.

**2. A Unicode filename broke the download outright.** `Content-Disposition` was built by
interpolating the raw filename, and ASGI encodes response headers as latin-1, so an ordinary
name such as `quotation-报价.pdf` raised `UnicodeEncodeError` and failed the response. Replaced
with an RFC 6266/5987 header built by `routes._content_disposition`: a sanitised ASCII
`filename` fallback plus `filename*=UTF-8''<percent-encoded>`. The sanitiser also strips quotes,
backslashes and control characters, so a crafted filename cannot terminate the quoted string
early and inject further header parameters - covered by its own unit test.

**3. Content was opened through the configured provider, not the one recorded on the row.**
`get_document_content_for_caller` called `get_storage_provider()` and ignored
`storage_provider_code` entirely - contradicting this slice's own migration docstring, which
says that column exists so an object can be resolved back to the provider holding it after a
provider swap. Storage now exposes two distinct lookups: `get_storage_provider()` for writes
(the configured provider) and `get_storage_provider_by_code(code)` for reads (the recorded one),
with a new `UnknownStorageProviderError` so an unresolvable code fails closed rather than
falling back. A row naming an unknown provider now returns `409`, verified live.

**4. Multipart form fields bypassed length validation.** The JSON route gets its bounds from
`DocumentMetadataCreate`'s Pydantic `max_length`; the upload route's `Form(...)` parts had none,
so a 101-character `linked_record_type` reached PostgreSQL and surfaced as `500`. Reproduced.
`_validate_upload_fields` now applies the column-width and non-blank bounds (kept in
`contract.py` alongside the widths they mirror) **before any bytes are stored**, so a rejection
cannot leave an orphaned file. Now `422`, with a test asserting the rejection leaves no row, no
event and no stored bytes. (The pre-existing cleanup path was already correct - the reproduced
`500` left nothing behind - but the status code was wrong and the guarantee was untested.)

**5. The two new routes were never pinned to their exact permissions.** The route-inventory
guard's fallback branch only requires a genuinely new route to carry *some* permission, so
upload and content-download could have had their permissions swapped, or replaced with any
other registered code, undetected - while the acceptance record claimed they were proved. Added
`POST_BASELINE_NEW_ROUTES` (with its own `assert_new_routes_are_genuinely_new` invariant: an
entry must be absent from *both* baseline structures, unlike a tightening) and merged it into
the guard's expected-permission lookup, so both new routes now go through the same
missing/wrong/multiple classification as any baseline-protected route. A second, independent
introspection test asserts all six document routes each carry exactly one permission dependency,
matching exactly what the fixtures pin.

**Documentation reconciliation.** The "Files changed" list above was incomplete (it predated the
acceptance and continuity records and collapsed the `storage/` package into one line); it now
reconciles against `git status` at 25 paths. The acceptance record's claim about what the guard
proves is corrected to match what it now actually checks.

## Correction pass 2 (independent review, 8 September 2026)

Round 1's five fixes were confirmed correct. One new material finding, this time in the tests
rather than the application.

**[P1] Successful-upload tests leaked their stored files.** The cleanup helpers deleted only the
`document_metadata` row, never the stored object - and deleted the row *first*, which destroyed
the `storage_key` needed to locate the file afterwards. Two tests upload real files, so every
full run leaked two objects; four orphans had accumulated (two 17-byte, two 21-byte) against
zero `local_upload` rows in the database. Confirmed here before changing anything: sizes and
counts matched exactly.

**The round-1 handoff's "storage volume empty" claim was therefore wrong as presented.** It was
a true observation at the time it was taken - the files had just been deleted during live
verification - but two further full-suite runs recreated them, and the earlier measurement was
reported as current state. A stale measurement presented as a current fact is the same class of
error as an untested assertion.

Fixed in two halves, deliberately:

- `_purge_stored_objects` reads `storage_provider_code`/`storage_key` **before** the rows are
  deleted, resolves the provider and deletes the object. It falls back to the configured
  provider when the recorded code is unresolvable, because
  `test_content_download_resolves_the_provider_recorded_on_the_row` deliberately writes an
  unregistered code to prove the read path fails closed - refusing to clean that up would leak
  the very object that test creates. Both cleanup helpers now route through it.
- A **module-scoped autouse fixture** compares the stored-object count at module start and end.
  Repairing the helpers stops the two known leaks; the fixture stops the next one, because a
  future test that uploads and forgets to clean up fails loudly rather than leaking silently on
  every run - which is exactly how this leak survived a full-suite run, a targeted file run and
  a manual volume inspection without being noticed.

Both halves were proven by temporarily disabling the purge: the two new cleanup regressions
failed and the module fixture errored on teardown. The four pre-existing orphans were removed,
and the storage root is empty after a clean run of the file.

Two record corrections in the same pass: the test-count arithmetic above, and a line in
`post_baseline_tightened_routes.py` still saying a brand-new route needs "no entry in this file
at all" - left over from before `POST_BASELINE_NEW_ROUTES` existed, and directly contradicting
it.

## Correction pass 3 (hosted CI, after local acceptance)

The independent review accepted the candidate, but the first hosted run of
`.github/workflows/te-2ci-validation.yml` on PR #29 failed two jobs. Both were real defects that
every local check had passed over, for the same underlying reason: **hosted CI is a different
environment from the Compose container, and two of this slice's assumptions were only true
inside the container.**

**1. `python-multipart==0.0.20` carried six advisories.** The dependency-audit gate reported
`PYSEC-2026-1852/3036/3037/3038/3039/3040`, fixed across releases up to `0.0.31`. The version
was chosen when the dependency was added and never audited locally, because the audit runs only
in CI. Pinned to `0.0.32` (current latest, above every listed fix version), **not** added to
`.github/dependency-audit-known-findings.txt` - the standing repository rule is that a scanner
finding gets fixed, never excluded, and here a fix was simply available. Re-running the exact CI
audit command locally against the same deferral list now reports "No known vulnerabilities
found, 11 ignored".

**2. `DOCUMENT_STORAGE_ROOT`'s default is a container-absolute path.** `/app/document-store`
matches the Compose volume mount and is correct inside the container, but the backend-regression
job runs pytest directly on the runner, where `/app` does not exist and is not writable. Nine
tests failed with `PermissionError: [Errno 13] Permission denied: '/app'` raised from inside
`pathlib`. Two changes:

- The CI job now sets `DOCUMENT_STORAGE_ROOT: ${{ runner.temp }}/document-store`. This is
  configuration, not a workaround - the setting exists precisely so each environment points at
  a valid location, exactly as `DATABASE_URL` is already set in the same `env:` block.
  `runner.temp` rather than a workspace path, so uploaded test files can never appear in
  `git status` or in the proposed-tree enumeration the secret and contract-fixture validators
  walk.
- `LocalFilesystemStorageProvider.__init__` now raises `DocumentStorageError` naming the setting
  when the root cannot be created, instead of surfacing a bare `PermissionError: '/app'` from
  deep inside `pathlib` - a message that is accurate and tells the reader nothing about what to
  change. Covered by its own regression test.

The default itself is deliberately unchanged: it is correct for the container, which is the
deployment target, and changing it would break the match with the Compose volume mount.

**Correction pass 3a: the first attempt at the CI fix was itself broken.** The environment
variable was written as `${{ runner.temp }}/document-store`, but the `runner` context is not
available in a job-level `env:` block. GitHub rejected the whole workflow at parse time - the
run failed in 0s having created no jobs at all, so `Required validation` never reported and the
PR showed no checks rather than a failure. Replaced with a literal `/tmp/pbl-crm-document-store`,
which needs no context and is equally outside the workspace.

**`actionlint` catches this, and it is already documented in `SKILLS_AND_TOOLS.md` as a local
check with a pinned image - it simply was not run before pushing a workflow change.** It names
the error exactly (`context "runner" is not allowed here`). Any future edit to
`.github/workflows/` should run it first:

```bash
docker run --rm -v "${PWD}:/repo" -w /repo \
  rhysd/actionlint:1.7.12@sha256:b1934ee5f1c509618f2508e6eb47ee0d3520686341fec936f3b79331f9315667
```

**This pass changed the candidate after acceptance.** The reviewer's acceptance was explicitly
bound to a content hash, so it no longer covers this content. The changes are narrow and
mechanical - one dependency version, one CI environment variable, one error message and its
test - but that is a judgement for the reviewer and the project owner, not for the implementer
to assert.
