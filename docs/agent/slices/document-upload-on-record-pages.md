# Document Upload on Record Pages

Before the UAT pilot, after the UI language pass (`docs/continuity/NEXT_STEPS.md`). Foundation
Slice Mode.

## Status

Complete. Implemented on branch `upload-control`, base commit `22ba9fc` (PR #35 merge), committed
as `1832bf4` after nine independent review rounds, and integrated on `main` through PR #36 (merge
commit `2c4dbae`) on 12 September 2026.

(As committed, this line read "Uncommitted, pending independent review and the project owner's
direction to commit": the commit had to reproduce the reviewed tree exactly, so the outcome is
recorded here afterwards. The package that followed, TE-5, did not pick this up, which is how the
line stayed wrong for a day - see the completion note.)

No migration: Alembic head unchanged at `20260908_0035`. No new route and no new permission; the
frozen baseline of 31 permissions, 110 grants and 76 routes is unchanged. The frozen Accepted
Offer -> Work Order handoff contract is unchanged.

## Owner decisions, 11 September 2026

| Question | Decision |
| --- | --- |
| Pilot uploads | Build an upload control before the pilot, as its own package. The pilot plan included uploads, and uploading a customer's work order is real daily work. |
| Who may upload | Only people who can change the record, enforced by the server. Account: Admin, Sales Executive, Sales Manager, Accounts. Commercial Offer: Admin, Sales Executive, Sales Manager, Operations. View only never. |

## Why this package exists

Reading the practice data sheet as a tester, during the language pass, showed that its Step 12 -
upload a file against the Kakinada Steel offer - could not be done: no screen offered an upload
against a chosen record. The only upload box, on the Documents page, was a developer test tool that
always filed to one fixed sample Account (`SAMPLE_RECORD_ID`) as document type KYC. The upload API
itself already existed (Slice 9C).

Looking at that API for this package showed two backend gaps:

1. Every role, View only included, could attach a file or document record to any record. Nothing
   checked the caller's rights on the linked record, or even that the record type was known; the
   record-scoped check covered only listing and downloading.
2. A user could upload a file typed `QUOTATION`, which the contract reserves for quotations the
   system generates.

## What changed

### Backend

- `DOCUMENT_LINK_WRITE_PERMISSION` in `documents/contract.py`: a fail-closed map from each linkable
  record type to the permission needed to attach documents to it, with exactly the read map's keys.
  Account types use `ACCOUNT_DOCUMENT_CAPTURE`, which already grants exactly the owner's Account
  roles. Lead, Opportunity, Work Order and conversation use their existing change permissions.
  Anything else is refused.
- **Commercial Offer reuses `COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE`**, which grants exactly the
  owner's offer roles. The plan was a dedicated `COMMERCIAL_OFFER_DOCUMENT_WRITE`, but grants are
  read from the seeded `authz_role_permission` table, so a new code needs a seed migration, and the
  next migration slot is reserved for the Hiring lane. The cost is coupling: changing who may
  record pricing evidence also changes who may attach files to an offer. It is recorded at the map
  entry, with how to split it later.
- The upload and metadata routes call new for-caller service functions: every check on the request
  itself, then the rights check (`403`), then the size limit while the file streams in. A refused
  upload never reads the file. `upload_document()` and `create_document_metadata()` stay
  authorization-free for trusted in-process callers such as the smoke-data harness.
- `QUOTATION` is refused on both user paths (`422`), in any capitalisation on the metadata route,
  which otherwise still accepts free-text types. Quotation generation is unaffected.
- On the metadata route, a whitespace-only `linked_record_type` is now a `422`; it used to create a
  row.
- The full table, the order of checks and the reasoning are in `docs/agent/contracts/documents.md`,
  "Record-scoped write rights (September 2026)".
- After independent review round 1, two limits an extension and a declared type could not give:
  every documents request is capped as its bytes arrive, before the body is parsed and before
  authentication (`_BoundedBodyRoute` in `routes.py`, at 25 MB plus 1 MB); and a file's opening
  bytes must match its extension's format before it is stored (`_check_upload_content`). Both are
  in the contract's "Upload limits".
- After review round 2, the content check is deeper where the signature alone proved too little. A
  `.doc` or `.xls` must be a compound file whose directory lists a `WordDocument`, or a `Workbook`
  or `Book`, stream - PowerPoint decks, Outlook messages and Windows installers carry the same
  signature. A `.pdf` must start with `%PDF-`, and a macro-enabled `.docm` or `.xlsm` renamed
  `.docx` or `.xlsx` is refused.
- After review round 3, the `.doc`/`.xls` reader walks the directory tree from the root entry
  through its child and sibling links, instead of reading every directory slot, so a Word or Excel
  name that no link reaches, or one inside a sub-storage, no longer counts.
- After review round 4, the reader trusts less of a crafted file: the header's allocation-table
  counts must match what it lists, no table sector may be listed twice or more than the file's size
  needs, table entries are read only as they are needed, and every name it reaches must be well
  formed. Any failure while reading a compound file or a ZIP archive refuses the file rather than
  risking a server error.
- After review round 5, a `.docx` or `.xlsx` directory is bounded before it is read: the archive's
  end record must describe one disk, no ZIP64 extension, at most 10,000 entries and a directory of
  at most 1 MB, so a crafted archive cannot make the reader use more memory than the upload. The
  project owner decided that the check stops at how a file is built - it does not validate the
  document inside - and the contract, this record and the tester guide now say so.

### Frontend

- `DocumentsPanel` (`frontend/src/components/DocumentsPanel.tsx`), shared by the Account and
  Commercial Offer pages. It lists the record's files - type, file name, "Added (India time)",
  remarks - with a Download button that saves a stored file under its original name. A file stored
  elsewhere shows its reference instead; only an `http(s)` reference is a link.
- For the roles that may change the record, an **Add a file** form: File, Document type, Remarks
  (optional) and **Upload**. Document type has no default - the user must choose one - and
  `QUOTATION` is not offered. Before sending, the form refuses a file the server would refuse for
  its extension or its size, and it sends the file with the exact content type the server requires
  for that extension, because browsers do not always report it (Windows often reports a `.csv` as
  an Excel file). "File added: *name*." appears beside the button; a `403`, `413` or `422` is shown
  in plain words in the same place. Other roles see "Your role can view these files but cannot add
  new ones." Hiding the form is a convenience; the server decides.
- The Account page uses the panel in its Documents section, in place of the old read-only list. The
  form shows for Admin, Sales User, Sales Manager and Finance User - the page's existing
  `ACCOUNT_DOCUMENT_CAPTURE_ROLES`, which already gated the older form. That older form, which
  records a link to a file stored elsewhere, is unchanged except that it now sits under a closed
  "Record a link to a file stored elsewhere", its button reads **Record link**, and saving it
  reloads the panel.
- The Commercial Offer page shows the panel in a new **Documents** section on the Overview tab,
  after "Dates, value and notes". The form shows for Admin, Sales User, Sales Manager and
  Operations User, through a new constant, `COMMERCIAL_OFFER_DOCUMENT_UPLOAD_ROLES`, whose comment
  ties it to the pricing-evidence permission. The panel loads again each time the Overview tab
  opens, so a quotation generated on the Submission tab is listed there.
- The Documents page lists the 50 most recent files the user may open, each with the record it
  **Belongs to** (a link to that record's page) and a download. Its developer test tools - a
  sample-document button and an upload box that always filed to one fixed sample Account - are
  removed.
- After review round 1: when the connection fails, or the server answers 500 or above, the form says
  the upload could not be confirmed and reloads the list, instead of saying the file was not added.
- After review round 2: each file row shows the file's reference under its name again, as the older
  Account list did; the Documents page does the same.

### Tests

- A new module, `backend/tests/test_document_upload_rights.py`, runs 89 cases: the owner's two role
  sets on both routes, the other record types, an unknown type refused even to Admin, malformed
  types refused as invalid before rights are checked, a refused upload that never reads its file,
  the write and read maps' keys kept identical, and `QUOTATION` refused while every other type is
  still accepted and generated quotations are still stored. Checked against the old behaviour in
  process: removing the rights check fails 29 cases, and removing the `QUOTATION` refusal fails 6.
- Two Slice 9C tests created documents linked to an unknown record type through the metadata route
  to test read denial; they now create the same rows through the service, because the route now
  correctly refuses them. Their read-denial assertions are unchanged.
- One Slice 9E test uploaded an HTML file typed `QUOTATION` to prove HTML is refused. `QUOTATION`
  is now refused first, so it uses `COMMERCIAL` to keep testing the HTML refusal.
- The smoke-data harness has a new record set, `document_upload_target`, and a test that files
  uploaded to it after seeding, and their stored bytes, are removed by the run's cleanup.
- A new Playwright spec, `e2e/tests/document-upload.spec.ts`: a Sales User uploads a file to an
  Account, sees it listed and downloads it, checking its name and exact bytes; uploads a file to an
  offer on its Overview tab and sees it listed; and View only sees both files but no upload form.
- After review round 1, `backend/tests/test_document_upload_limits.py`: the request cap, driven
  through the real application with a body that does not end and no token; every documents route
  using the bounded route class; each accepted format accepted with real opening bytes; mismatched
  content refused with nothing written; and content checked only after the rights check. The two
  Slice 9C oversize tests now send a PDF header before their padding - otherwise the body is
  refused as not a PDF before its size is counted - and their `413` assertions are unchanged.
- After review round 2, the same module builds compound files to the [MS-CFB] layout - including
  4096-byte sectors and a directory spanning three sectors - and checks the reader lists exactly
  their streams. It refuses a header-only `.doc`, PowerPoint decks under both names, a workbook
  named `.doc` and a document named `.xls`, a looping directory, a PDF header found only in a
  comment, and renamed macro-enabled files. The Playwright spec checks each file row shows its
  reference.
- After review round 3, the built compound files link each directory as a red-black tree in
  [MS-CFB] order, and a test checks those links. New refusals: an unlinked Word or Excel entry, a
  Word stream inside a sub-storage, a looping tree, a root entry that is not one, and a link to an
  entry that does not exist. Four short test files the owner saved from Word and Excel - `.doc`,
  `.xls`, `.docx` and `.xlsx`, in `backend/tests/fixtures/documents` with the author's name
  replaced - are accepted, and refused under each other's extension.
- After review round 4, eight more refusals: a table sector listed 109 times, one listed twice, a
  table count the list does not match, a Word name without its closing NUL, an odd name length, a
  name that is not valid UTF-16, a name with a NUL inside, and a `.docx` whose part name cannot be
  decoded - the last refused with `422`, not a server error.
- After review round 5, three more refusals: a `.docx` with more than 10,000 parts, one whose
  directory is over 1 MB, and one with a ZIP64 locator.
- After review round 7, three test/wording strengthenings, none a code-behaviour change: the
  Playwright spec adds Finance User and Operations User, the two roles where the Account and offer
  upload-role sets diverge, checking each is offered the form on one page and not the other;
  `test_document_upload_rights.py` pins the exact set of `/api/documents` routes and each route's
  permission; and the Documents page and tester guide now say a stored file can be downloaded
  unless it belongs to a conversation whose messages the reader's role may not read. The route
  guard's `>= 70`-floor and removed-ungated-route gap is a pre-existing PF-1A-E1 matter, recorded
  as a known limitation rather than changed here. The new Finance and Operations logins made
  `scripts/run-e2e.ps1` add `finance1` and `ops1` to its login-event cleanup actor allowlist
  (TE-2B-C3), or the run's own login audit rows would be reported and left behind.
- After the ninth review, the two Slice 9C size-limit tests, which the content check had made send
  a PDF header plus a full-limit body (9 bytes over), are corrected to send a body exactly one byte
  over the 25 MB limit, so a single-byte relaxation still fails them; a new test pins the limit from
  both sides (exactly 25 MB accepted, one byte more rejected). No behaviour change. This was the
  last review; the project owner kept the full content check rather than narrowing it.
- After review round 7 (the eighth review), one more ZIP gap closed: an archive with data
  prepended before it is refused, because its stored directory offset no longer meets its end
  record. Without this, the bounded check could validate a small decoy directory while `zipfile`,
  which follows a concatenation offset, opened a larger real one. A prepended valid archive and a
  prepended 12,000-part archive are both refused; a clean archive still passes.
- After review round 6, two more resource gaps closed: a `.docx` whose end-record entry count is
  forged below the directory's real size (the directory's entries are now counted and cross-checked
  against the claim), and a `.doc` whose allocation-table (DIFAT) chain points back at itself under
  an attacker-controlled count (the list-sector count must now equal exactly what the table needs,
  and no list sector may be read twice). Two direct unit tests prove each is refused by structure,
  not by running to the claimed count.

### Documents

The practice data sheet's Step 12 asks testers to upload a file again. The tester guide, its
published page, the runbook and the carry-forward list describe where files are attached. The UI
language pass's own record, which could not change before its commit, is completed: round 4's
result, its merge and its status lines.

## Deliberately not changed

- The linked record's existence is still not checked on upload (Slice 9C left it out of scope). The
  screens always send a real record, and the rights check does not depend on it.
- `DOCUMENT_UPLOAD` is still granted to every role; as with `DOCUMENT_READ`, the real narrowing is
  the record-scoped check. The catalogue descriptions of `DOCUMENT_UPLOAD` and
  `COMMERCIAL_OFFER_PRICING_EVIDENCE_WRITE` are unchanged and now understate what those grants
  govern.
- The metadata route still accepts free-text document types other than `QUOTATION`.
- Read-access auditing and retention remain deferred (`docs/agent/DEFERRED_REQUIREMENTS.md`).
- No upload control on the Lead, Opportunity or Work Order pages; the server rules for those types
  are in place for when one is added.
- Uploads carry no idempotency key; after an unconfirmed upload the list is reloaded instead.
  Storing a key needs a schema change, and the next migration slot is reserved for the Hiring lane.
- A caller without rights can still make the server receive one request, up to the cap, before the
  `403`. Checking rights before the body is read would need the record in the URL or a two-stage
  upload.
- The content check confirms how a file is built, not that the document inside is complete, valid
  or uncorrupted (owner decision after review round 5); it is not a malware scan.

## Checks

See `docs/agent/acceptance/document-upload-on-record-pages-acceptance.md`.
