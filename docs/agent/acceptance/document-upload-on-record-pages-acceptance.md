# Document Upload on Record Pages - Acceptance

Package record: `docs/agent/slices/document-upload-on-record-pages.md`. Branch `upload-control`,
base `22ba9fc`.

## Commands

```text
docker compose exec backend pytest                                                 backend regression
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run typecheck
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm test
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run build
.\scripts\run-e2e.ps1                                                              Playwright
python scripts/validate_contract_fixtures.py
python scripts/check_tracked_secrets.py
python -m unittest discover -s scripts/tests
```

## Acceptance checks

| # | Check | How it is checked |
| --- | --- | --- |
| 1 | Admin, Sales User, Sales Manager and Finance User may attach a file or document record to an Account; everyone else is refused with 403 | `test_document_upload_rights.py`, both routes |
| 2 | Admin, Sales User, Sales Manager and Operations User may attach to a Commercial Offer; everyone else is refused | same |
| 3 | Management Read Only can attach to nothing | same |
| 4 | An unknown record type is refused even to Admin; a blank or over-length one is refused as invalid before rights are checked | same |
| 5 | A refused upload never reads the file, stores no bytes and writes no row | same, with a file stream that fails if read |
| 6 | `QUOTATION` is refused on both user paths, and generated quotations are still stored | same, and the Slice 9E module |
| 7 | Testers can upload, list and download files on the Account and Commercial Offer pages; View only sees the files but no upload form | Playwright `document-upload.spec.ts`, and the browser |
| 8 | The Documents page lists recent files with downloads and has no developer tools | the browser |
| 9 | This package adds, removes and re-gates no route, and adds no permission or grant; the six `/api/documents` routes keep their exact permissions, and the frozen handoff contract is unchanged | `test_document_upload_rights.py` pins the documents route set and each route's permission; the authorization guard tests pin every protected route's permission; `git diff` shows no `@router` change and no permission/grant change; `git diff --stat` on the contract file is empty |
| 10 | The regression suites pass | the commands above; results below |
| 11 | A documents request is refused with 413 once its body passes 25 MB plus 1 MB, before the body is parsed and before authentication | `test_document_upload_limits.py`, through the real application with a body that does not end and no token |
| 12 | A file whose opening bytes do not match its extension is refused with 422 and nothing is written; each accepted format is accepted with real opening bytes; content is checked only after rights | same |
| 13 | After a failed connection or an answer of 500 or above, the upload form says the upload could not be confirmed and reloads the list | code review only: the frontend has no component tests |
| 14 | A `.doc` or `.xls` is accepted only when a Word or Excel stream sits at the top of its compound-file directory tree; a PowerPoint deck, a header-only file, an unlinked or nested Word or Excel entry, a looping chain or tree, a missing root entry, a broken link, a crafted allocation table, a malformed name and a renamed macro-enabled file are refused; so is a `.docx` whose part names cannot be read, with `422`, not a server error | `test_document_upload_limits.py` |
| 15 | Each file row shows the file's reference under its name, as the older Account list did | Playwright `document-upload.spec.ts` |
| 16 | Short test files saved by Word and Excel - `.doc`, `.xls`, `.docx` and `.xlsx` - are accepted, and each is refused under the other program's extension | `test_document_upload_limits.py`, with the files in `backend/tests/fixtures/documents` |
| 17 | A `.docx` or `.xlsx` whose directory holds more than 10,000 entries or 1 MB, or which carries a ZIP64 locator, is refused before its directory is read | `test_document_upload_limits.py` |
| 18 | A `.docx` whose end-record entry count is forged below its real directory size, and a `.doc` whose DIFAT chain points back at itself under a huge count, are refused by structure without a long loop | `test_document_upload_limits.py` |
| 19 | Finance User is offered the upload form on an Account but not on an offer; Operations User the reverse - the two record types' upload-role sets diverge exactly there | Playwright `document-upload.spec.ts` |
| 20 | A `.docx` with data prepended before it is refused - its directory no longer meets its end record - so a decoy directory can never be validated while zipfile opens a larger one | `test_document_upload_limits.py` |
| 21 | The 25 MB limit is pinned exactly: a body one byte over is rejected on both the HTTP route and the direct service path, and exactly 25 MB is accepted by the counting mechanism | `test_slice_9c_document_storage_foundation.py` |

## Results - first candidate

```text
Full backend regression        1419 passed, 0 failed, 582.51s
                               (1329 before this package, 89 new upload-rights cases, 1 new
                               harness cleanup test)
Stored document files          14 before, 14 after the full regression
Alembic                        current == heads == 20260908_0035 (no migration)
Frontend typecheck             exit 0
Frontend tests                 1 file, 54 passed
Frontend build                 exit 0 (main bundle 697.50 kB)
Playwright                     15 passed, 9 skipped, 0 failed, 1.3 min; cleanup succeeded. The 3 new
                               tests are document-upload.spec.ts; the other 21 ran as 12 passed,
                               9 skipped
Contract fixtures              7 files, all rules passed
Tracked-secret check           888 files, no findings
Validator unit tests           58 passed
Frozen handoff contract        git diff --stat against the base: empty
```

Checked against the old behaviour, in process: with the rights check removed, the 29 refusal cases
fail; with the `QUOTATION` refusal removed, 6 cases fail.

## Results - after review round 1

```text
Affected test files            405 passed (upload limits, upload rights, Slice 9C, documents,
                               Slice 9E, harness and three authorization files)
Full backend regression        1446 passed, 0 failed, 1398.48s (1419 before; 27 new in
                               test_document_upload_limits.py)
Stored document files          14 before and 14 after the full regression; 14 after Playwright
Alembic                        20260908_0035 (head), after rebuilding the backend
Frontend typecheck             exit 0
Frontend tests                 1 file, 54 passed
Frontend build                 exit 0 (main bundle 697.78 kB)
Playwright                     first attempt 14 passed, 1 failed, 9 skipped; rerun unchanged:
                               15 passed, 9 skipped, 0 failed (1.9 min); cleanup succeeded
Contract fixtures              all rules passed
Tracked-secret check           889 files, no findings
Validator unit tests           58 passed
Frozen handoff contract        git diff --stat against the base: empty
```

The first Playwright attempt failed at its first step: a login still showed "Signing in..." when the
10-second limit expired. The backend log shows every login in that run answered `200`, with no
error; the host had 579 MB of free memory and was running about four times slower than earlier the
same day. Nothing in the corrections touches login, and the unchanged rerun passed.

## Results - after review round 2

```text
Upload limits tests            41 passed (27 after round 1)
Full backend regression        1460 passed, 0 failed, 857.73s (1419 before the corrections;
                               41 in test_document_upload_limits.py)
Stored document files          14 before and after the full regression; 14 after Playwright
Alembic                        20260908_0035 (head), after rebuilding the backend
Frontend typecheck             exit 0
Frontend tests                 1 file, 54 passed
Frontend build                 exit 0 (main bundle 697.94 kB)
Playwright                     15 passed, 9 skipped, 0 failed (1.9 min); cleanup succeeded
Contract fixtures              all rules passed
Tracked-secret check           889 files, no findings
Validator unit tests           58 passed
Frozen handoff contract        git diff --stat against the base: empty
```

## Results - after review round 3

```text
Upload limits tests            77 passed (41 after round 2), four of them on files saved by Word
                               and Excel
Full backend regression        1496 passed, 0 failed, 774.65s (1419 before the corrections;
                               77 in test_document_upload_limits.py)
Stored document files          14 before and after the full regression; 14 after Playwright
Alembic                        20260908_0035 (head), after rebuilding the backend
Frontend                       unchanged since round 2, when typecheck, 54 tests and build were
                               clean
Playwright                     15 passed, 9 skipped, 0 failed (1.1 min); cleanup succeeded
Contract fixtures              all rules passed
Tracked-secret check           894 files, no findings; 7 skipped as binary, the four Office
                               fixtures among them
Validator unit tests           58 passed
Frozen handoff contract        git diff --stat against the base: empty
```

## Results - after review round 4

```text
Upload limits tests            85 passed (77 after round 3)
Full backend regression        1504 passed, 0 failed, 601.77s (1419 before the corrections;
                               85 in test_document_upload_limits.py)
Stored document files          14 before and after the full regression; 14 after Playwright
Alembic                        20260908_0035 (head), after rebuilding the backend
Frontend                       unchanged since round 2, when typecheck, 54 tests and build were
                               clean
Playwright                     15 passed, 9 skipped, 0 failed (1.1 min); cleanup succeeded
Contract fixtures              all rules passed
Tracked-secret check           894 files, no findings; 7 skipped as binary
Validator unit tests           58 passed
Frozen handoff contract        git diff --stat against the base: empty
```

## Results - after review round 5

```text
Upload limits tests            88 passed (85 after round 4)
Full backend regression        1507 passed, 0 failed, 639.92s (1419 before the corrections;
                               88 in test_document_upload_limits.py)
Stored document files          14 before and after the full regression; 14 after Playwright
Alembic                        20260908_0035 (head), after rebuilding the backend
Frontend                       unchanged since round 2, when typecheck, 54 tests and build were
                               clean
Playwright                     15 passed, 9 skipped, 0 failed (1.0 min); cleanup succeeded
Contract fixtures              all rules passed
Tracked-secret check           894 files, no findings; 7 skipped as binary
Validator unit tests           58 passed
Frozen handoff contract        git diff --stat against the base: empty
```

## Results - after review round 6

```text
Upload limits tests            92 passed (88 after round 5), the whole file in 98.72s - no long loop
Full backend regression        1511 passed, 0 failed, 640.17s (1419 before the corrections;
                               92 in test_document_upload_limits.py)
Stored document files          14 before and after the full regression; 14 after Playwright
Alembic                        20260908_0035 (head), after rebuilding the backend
Frontend                       unchanged since round 2, when typecheck, 54 tests and build were
                               clean
Playwright                     15 passed, 9 skipped, 0 failed (1.0 min); cleanup succeeded
Contract fixtures              all rules passed
Tracked-secret check           894 files, no findings; 7 skipped as binary
Validator unit tests           58 passed
Frozen handoff contract        git diff --stat against the base: empty
```

## Results - after review round 7

```text
Targeted tests                 182 passed (test_document_upload_rights.py + test_document_upload_limits.py)
Full backend regression        1512 passed, 0 failed, 596.08s
Stored document files          14 before and after the full regression; 14 after Playwright
Alembic                        20260908_0035 (head), after rebuilding the backend
Frontend typecheck / tests / build   exit 0 / 1 file, 54 passed / exit 0
Playwright                     17 passed, 9 skipped, 0 failed; the 5 document-upload tests include
                               the new finance1 and ops1 divergence cases. First run exited 3 - the
                               login-event cleanup flagged the two new actors, absent from the
                               run-e2e.ps1 allowlist; added them, cleaned the leaked rows, re-ran
                               clean
Contract fixtures              all rules passed
Tracked-secret check           894 files, no findings; 7 skipped as binary
Validator unit tests           58 passed
Frozen handoff contract        git diff --stat against the base: empty
```

## Results - after review round 8

```text
Upload limits tests            95 passed (92 after round 6), the four real Office files still pass
Full backend regression        1515 passed, 0 failed, 632.65s
Stored document files          14 before and after the full regression; 14 after Playwright
Alembic                        20260908_0035 (head), after rebuilding the backend
Frontend                       unchanged since round 7 (typecheck, 54 tests and build clean there)
Playwright                     17 passed, 9 skipped, 0 failed; cleanup succeeded
Contract fixtures              all rules passed
Tracked-secret check           894 files, no findings; 7 skipped as binary
Validator unit tests           58 passed
Frozen handoff contract        git diff --stat against the base: empty
```

## Final verification - after the ninth review's correction

```text
Full backend regression        1516 passed, 0 failed, 739.39s (1329 at the package's base;
                               ~187 new across the upload-rights, upload-limits and boundary tests)
Stored document files          14 before and after the full regression; 14 after Playwright
Alembic                        20260908_0035 (head), after rebuilding the backend
Frontend                       unchanged since round 7 (typecheck, 54 tests and build clean there)
Playwright                     17 passed, 9 skipped, 0 failed; cleanup succeeded
Contract fixtures / secrets / validator unit tests   all passed / 894 files, no findings / 58 passed
Frozen handoff contract        git diff --stat against the base: empty
```

Nine independent review rounds (the independent reviewer). The project owner kept the full content check
and directed the ninth round be the last, which accepted the package. It was committed as `1832bf4`
and integrated on `main` through PR #36 (merge commit `2c4dbae`) on 12 September 2026.

## Manual browser check

In the in-app browser at `http://localhost:3000`, logged in as `admin1` (the login page's prefilled
test user), against a seeded `core-regression-bundle` run, record set `document_upload_target`:

```text
Account page     The Documents box shows "No files yet.", the Add a file form, and the older form
                 folded under "Record a link to a file stored elsewhere".
Offer page       Overview tab: a .txt file, type Commercial, remarks "Copy of customer work order
                 received by email." -> "File added: customer-work-order-browser-check.txt." beside
                 the Upload button; type and remarks cleared; the new row reads Commercial, the file
                 name, 11 Sept 2026, 04:28 pm, the remarks and Download.
Documents page   The new file first, belonging to a Commercial Offer; generated quotations listed as
                 Quotation; files stored elsewhere show their link; no developer tools.
Cleanup          The run's cleanup removed the file and its stored bytes; stored files back to 14.
```

The browser pane was hidden and did not pass clicks or key presses to the page, so the file was
chosen and the form submitted through the page's own script (`requestSubmit`). Real clicks, the
download and the View only view are covered by the Playwright spec; they were not repeated by hand.

## Known gaps

- Commercial Offer uploads reuse `COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE`, so changing who may
  record pricing evidence also changes who may attach files to an offer. A dedicated permission
  needs a seed migration; the next migration slot is reserved for the Hiring lane.
- The permission catalogue's descriptions of `DOCUMENT_UPLOAD` and
  `COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE` are unchanged and now understate what those grants
  govern.
- The linked record's existence is still not checked on upload.
- No upload control on the Lead, Opportunity or Work Order pages; the server rules for those
  record types are in place.
- The shared authorization guard pins every protected route's exact permission and flags a new
  ungated route, but bounds the total route count by a `>= 70` floor, not an exact number, and does
  not detect a removed *ungated* route. This is a pre-existing PF-1A-E1 limitation, not changed by
  this package; this package's own routes are pinned exactly by `test_document_upload_rights.py`.
- Uploads carry no idempotency key, so a retry after an unconfirmed upload can store a second copy;
  the form reloads the list so the user can see. A key needs a schema change.
- A caller without rights can still make the server receive one request, up to the cap, before the
  `403`.
- The content check confirms how a file is built, not that the document inside is complete, valid
  or uncorrupted: a damaged or hand-assembled file built as a Word, Excel or PDF file is accepted
  (owner decision after review round 5). It is not a malware scan, and text is not interpreted.
  Besides files built to the published formats, the tests use four short files the
  owner saved from one installation of Word and Excel, with the author's name replaced; they do not
  cover every program that writes these formats.
