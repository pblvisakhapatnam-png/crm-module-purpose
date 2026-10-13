# Slice 9E - Quotation Generation

## Status

Specification frozen 8 September 2026. Last of the three agreed CRM pilot minimums
(9D done, 9C done, 9E now). Foundation Slice Mode.

Branch: `slice-9e-quotation-generation`.
Baseline commit: `2cc03c5`.
Alembic parent: `20260908_0034`. This slice takes **`20260908_0035`** by explicit owner
decision of 8 September 2026; Hiring `7C` moves to `20260908_0036`. See
`docs/continuity/NEXT_STEPS.md`.

Model plan: PBL's design lead designed and froze this specification and put the six decisions below to the
project owner; PBL's development team builds it; independent review by the independent reviewer.

## Why this slice exists

Everything needed to *prepare* a quotation exists. Nothing produces the document a customer
actually receives.

Already built, and reused rather than rebuilt: offer lines with stable identity (Slice 4E),
pricing evidence and selected basis rate (4D), header T&C attachment with **snapshotted clause
text** (6F/6G), submission readiness (6H), submission evidence (6I), controlled submission (6J),
revisions (6K), customer responses (6L), lifecycle guidance (6M), and - since Slice 9C - a
provider-neutral storage abstraction with real upload/download, record-scoped fail-closed
download authorization, and `document_metadata` columns for `storage_provider_code`,
`storage_key`, `content_type`, `byte_size` and `checksum_sha256`.

`docs/agent/DEFERRED_REQUIREMENTS.md` parks "customer-facing quote document generation" under
"Commercial Offer approvals and submission", and "Quote/PDF generation and legal/version
approval controls" under "Commercial Offer revisions". This slice takes the generation half.

### What the source documents actually require

`docs/reference/erp-source-extracts/CRM_HIRING_RELEVANT_REQUIREMENTS_EXTRACT.md:107-121`
(source section 2.2, Quotation & Commercial Rule Engine):

```text
- Quotations must support multiple equipment items in one quote.     -> already met by 4E lines
- PBL T&C master library must support clause selection...            -> already met by 6E/6F/6G
- Users should cross-check historical rates...                       -> already met by 4D
- Quoted margins should be evaluated against thresholds...           -> DEFERRED (needs APR-001)
- Only approved quotations may be shared with customers.             -> DECISION 3 below
- Quote revisions require versioning and audit trail.                -> DECISION 2 below
```

Two of those six drive this slice. The margin-threshold rule is deliberately not attempted: it
needs `APR-001` and the PF-1A-E3 authority configuration, and PF-1A stops at E3.

Under ADR-013 these are **directional guidance**, not frozen contract. Both are adopted here
substantially as written, so no deviation record is required.

## Owner decisions, 8 September 2026

Put in plain business language before any design work, per `AGENTS.md`.

| # | Decision | Answer |
| --- | --- | --- |
| 1 | What the generated file is | A frozen, self-contained **HTML** document; the user prints it to PDF from the browser |
| 2 | Frozen at generation, or re-rendered on each view | **Frozen**, plus an advisory staleness marker when the offer has since changed |
| 3 | Approval before issue | **A one-step attested issue gate** - Draft, then Approved for Issue, recording who and when |
| 4 | Who may approve for issue | **Sales Manager and Admin only** - a Sales User may generate but not approve |
| 5 | UAT pilot data | **Synthetic only**, so the retention/read-access gate is not triggered by this pilot |
| 6 | Migration slot | 9E takes `0035`; `7C` moves to `0036` |

### Decision 1, and what it honestly costs

There is no PDF library in `backend/requirements.txt` - ten packages, none of them a renderer.
WeasyPrint additionally needs cairo/pango system libraries in the backend image. Both were
offered and both were declined in favour of HTML, on the basis that the pilot's purpose is
layout feedback rather than a production document pipeline.

The limitation this accepts, stated plainly rather than buried: **the artifact the system
freezes and checksums is the HTML. The PDF a customer receives is produced by the user's
browser, outside the system, and is not itself stored, checksummed or reproducible.** If PBL
later needs the delivered PDF to be the artifact of record, a server-side renderer replaces
`quote_render.render_quote_html` behind the same seam - the stored-artifact plumbing, the
versioning, the fingerprint and the approval gate do not change.

### Decision 3, and what the gate does and does not do

The gate records that a **named person authorised a specific version for issue**, with a
timestamp and an event. That is a procedural control with an audit record.

It is **not** an access control, and this specification does not pretend otherwise. Three
things follow, and all three are deliberate:

- A Draft quote is downloadable by anyone who can already open the Commercial Offer. It has to
  be - you cannot approve a document you cannot read. It leaks nothing new: every figure in the
  quote is already on the offer screen for the same audience.
- No system can stop a human emailing a file. "Only approved quotations may be shared with
  customers" is enforced by the record of which version was approved, not by preventing bytes
  from moving.
- Because a Sales Manager may both prepare and approve, decision 4 separates the *Sales User*
  from approval but does not achieve full maker-checker. True maker-checker is `APR-001` work
  and is deferred.

An earlier draft of this design proposed a cross-module hook so the generic documents download
route would refuse an unapproved quote. It was **removed before freezing**: it would have given
the appearance of enforcement over data the same users can already see on screen, added a
documents -> commercial_offers dependency, and introduced a fail-open risk if the hook were ever
not registered. A control that only appears to control is worse than an honestly-labelled
procedural one.

## In scope

- A frozen, versioned quotation document generated from a Commercial Offer.
- Storage through Slice 9C's abstraction, as a `document_metadata` row linked to the offer.
- A source-data fingerprint, so a quote that no longer matches its offer is detectable.
- A one-step Draft -> Approved for Issue gate, enforced in the database as well as the API.
- Two advisory submission-readiness rows, including the FRD "communications logged before
  quoting" row deliberately deferred out of Slice 9D.
- Commercial Offer detail UI for generate / approve / download / staleness.

## Explicitly not in scope

Server-side PDF rendering. Margin-threshold evaluation and approval (`APR-001`). Full
maker-checker. Emailing or otherwise transmitting the quote. Line-level T&C. T&C deviation or
new-clause approval. GST/tax calculation. Offer cloning or immutable offer-version snapshots
(Slice 6K's deferred deeper work). Hard enforcement of the FRD interaction-logging rule -
advisory only, per `interaction-contract.md:283`. Retention purge and read-access auditing -
see "Deferred". The two synthetic UAT datasets, which are their own package after this one.

## Design

### Records

One new table, owned by the Commercial Offer module. The bytes live in `document_metadata`;
this table holds only what is quote-specific and therefore has no home there.

```text
crm_commercial_offer_quote_document

id                          integer identity PK
quote_document_public_id    VARCHAR(36)   UUID, unique
commercial_offer_id         FK -> crm_commercial_offer.id, NOT NULL
version_no                  INT NOT NULL          1, 2, 3... per offer
quote_reference             VARCHAR(100) NOT NULL derived, e.g. "CO-000042/V1"
document_public_id          VARCHAR(36) NOT NULL  -> document_metadata.document_public_id
source_fingerprint          CHAR(64) NOT NULL     sha256 over the canonical source data
quote_status_code           VARCHAR(50) NOT NULL  DRAFT | APPROVED_FOR_ISSUE
generated_by                VARCHAR(36)
generated_at                TIMESTAMPTZ NOT NULL
approved_by                 VARCHAR(36) NULL
approved_at                 TIMESTAMPTZ NULL
approval_note               VARCHAR(1000) NULL
superseded_at               TIMESTAMPTZ NULL
created_at / updated_at
```

**`superseded_at` is a separate column, not a third status value.** Generating version 2 must
not erase the fact that version 1 was approved and issued - that is the record of what was sent
to the customer. Status and supersession are two independent facts and are stored as two.

Constraints, in the database rather than only in a validator - the Slice 9C lesson:

```sql
UNIQUE (commercial_offer_id, version_no)

CONSTRAINT ck_quote_document_status CHECK (
    quote_status_code IN ('DRAFT', 'APPROVED_FOR_ISSUE')
)

CONSTRAINT ck_quote_document_approval_is_complete CHECK (
    (quote_status_code = 'DRAFT'
        AND approved_by IS NULL AND approved_at IS NULL)
    OR (quote_status_code = 'APPROVED_FOR_ISSUE'
        AND approved_by IS NOT NULL AND approved_at IS NOT NULL)
)
```

A row cannot claim approval without recording who approved it and when. A direct `INSERT` that
bypasses the API cannot create that lie either. This is the same shape as 9C's
`ck_document_metadata_local_upload_has_bytes`, and for the same reason: the invariant that
gives the gate its meaning is the one that must survive the API being bypassed.

Additive elsewhere: `QUOTATION` joins `DOCUMENT_TYPE_CODES` in the documents contract, so a
generated quote is distinguishable from any other commercial document.

### Storage - one shared path, without widening the upload surface

`.html` is deliberately **not** added to `ALLOWED_UPLOAD_EXTENSIONS`. Letting users upload
arbitrary HTML through `POST /api/documents/upload` would put attacker-controlled markup into
the store, and this slice must not buy its own convenience with that.

Instead the documents service gains an internal, non-HTTP entry point:

```python
def store_generated_document(
    db, *, linked_record_type, linked_record_public_id, document_type,
    file_name, content_type, content: bytes, current_user_public_id,
) -> dict: ...
```

- It accepts only content types in a separate `GENERATED_CONTENT_TYPES = {"text/html": ".html"}`
  map, which is not reachable from any route.
- It shares one private helper with `upload_document` covering storage-key generation,
  `provider.save`, the `document_metadata` insert, the event, and - critically - the
  **rollback-and-delete compensation on failure**, so a failed insert can never leave an
  orphaned object in the store. That compensation was a build-time correction in 9C and must
  not be re-derived here.
- It does **not** commit. The caller owns the transaction, because the quote-document row and
  the document row must land together or not at all. `upload_document` keeps its own commit.
- Its event is `DocumentGenerated`, **not** `DocumentUploaded`. Reusing the upload event would
  record that a user uploaded a file they never uploaded - a small lie of exactly the kind
  Slice 9C existed to remove.

File name: `Quotation-CO-000042-V1.html`. It deliberately **excludes the customer name**: 9C
established that a file name alone leaks ("`Acme-PAN-card.pdf` discloses both the customer and
the nature of the document"), and the documents list is visible more widely than the offer.

`quote_reference` reuses the offer code plus a version suffix rather than opening a new number
series, because production Commercial Offer numbering is explicitly deferred and inventing a
second series now would have to be undone.

### Rendering

`backend/app/modules/commercial_offers/quote_render.py`:

```python
def render_quote_html(payload: QuoteSnapshotPayload) -> str: ...
```

- A **pure function**: no database access, no I/O, no clock, no randomness. The same payload
  renders byte-identical output. That is what makes it directly testable and what makes the
  fingerprint meaningful.
- **Every interpolated value passes through `html.escape(value, quote=True)`. No exceptions.**
  Account names, offer titles, remarks, line descriptions and T&C snapshot text are all
  customer- or user-supplied free text. This is the single largest risk in the slice.
- The output contains **no `<script>` element and no event-handler attribute**, ever. A test
  asserts this against rendered output containing hostile input, rather than trusting the
  template's shape.
- Self-contained: one inline `<style>`, no external stylesheet, font, image or script, so the
  file renders identically from disk with no network. Includes `@media print` rules so the
  browser's Print dialog produces a sensible page.

### What the document contains

```text
Header        PBL identity; "QUOTATION"; quote_reference; version; generated date; prepared by
Customer      Account name, legal name, registered/communication address, GSTIN(s)
Reference     Offer code, offer date, valid until, customer request reference
Lines         line number, scope description, equipment/service category, quantity, UOM,
              rate, line amount
Total         sum of active line amounts, INR, marked EXCLUSIVE OF GST - but only when EVERY
              active line carries an amount; otherwise "Not priced" / "Not fully priced"
Terms         the attached header T&C clauses, using the 6F snapshot text - never the live
              master text, because a later master edit must not change an issued quote
Footer        prepared-by, signature block, and an instruction to verify the current
              issue-approval status in the CRM - NOT the approval status itself
```

**Two reconciliations to this block, made during correction pass 2** (independent review of
correction pass 1), recorded rather than silently edited:

- The footer originally said **approval status**. It cannot carry one: the bytes are frozen at
  generation, which always precedes approval, so any status rendered there is either false
  immediately (claiming approval) or false later (claiming Draft). Both were shipped and both
  were caught. The footer carries an instruction to verify instead, which is true in both states.
- The reference block originally said **opportunity reference**. `crm_opportunity` has no
  customer-meaningful reference - only `opportunity_public_id` (a UUID) and an internal
  `opportunity_name`. Printing either on a customer-facing document would be worse than omitting
  it, so the block is reconciled to what the document actually and sensibly shows. If PBL later
  wants an Opportunity reference on quotations, the Opportunity needs a business reference code
  first, which is its own change.

**Excluded deliberately:** pricing evidence, the selected basis rate, the selection rationale,
credit review outcomes and margin data. Those are internal commercial records; a document
rendered for a customer must not carry them. Cancelled lines are excluded; only `ACTIVE` lines
appear.

GST is shown as an explicit exclusion line rather than calculated, because GST determination is
deferred and stating a computed tax the system cannot yet compute correctly would be worse than
stating none.

### Snapshot and staleness

```python
def build_quote_snapshot(db, *, offer_public_id) -> QuoteSnapshotPayload: ...
```

Gathers the offer header, Account identity, Opportunity reference, active lines and header T&C
snapshots. Serialised canonically (sorted keys, fixed separators, decimals as strings) and
hashed: `source_fingerprint = sha256(canonical_json)`.

On read, the fingerprint is recomputed from current data and compared. A mismatch sets
`is_stale = true` on the response. **This is advisory**, and the response and the UI say so: the
control is that the stored bytes are immutable, and staleness is a convenience that tells a user
to generate a new version. It is not a block.

The fingerprint is taken over the **source data**, not over the rendered HTML. Hashing the
output would only prove the file had not changed - which is already guaranteed - and would say
nothing about whether the offer had moved underneath it.

### Routes

```text
POST /api/commercial-offers/{public_id}/quote-documents
                                        require_permission(COMMERCIAL_OFFER_QUOTE_GENERATE)
GET  /api/commercial-offers/{public_id}/quote-documents
                                        require_permission(COMMERCIAL_OFFER_READ)
POST /api/commercial-offers/{public_id}/quote-documents/{quote_document_public_id}/approve
                                        require_permission(COMMERCIAL_OFFER_QUOTE_APPROVE)
```

Download reuses the existing `GET /api/documents/{public_id}/content`. **No new download route
and no second authorization path** - 9C's record-scoped, fail-closed check already maps
`commercial_offer` to `COMMERCIAL_OFFER_READ`, and that path has been independently reviewed
three times.

All three routes are new, so all three go in `POST_BASELINE_NEW_ROUTES`
(`backend/tests/fixtures/post_baseline_tightened_routes.py`), never in the frozen baseline
inventory. `BASELINE_UNGATED_ROUTES` and the frozen 31 / 110 / 76 counts are not touched.

### Permissions

Two new codes in `POST_BASELINE_ROLE_PERMISSION_MATRIX`, seeded by this slice's migration.
`ROLE_PERMISSION_COMPATIBILITY_MATRIX` is not touched; Slice 9D is the worked example.

```text
COMMERCIAL_OFFER_QUOTE_GENERATE   ADMIN, SALES_USER, SALES_MANAGER
COMMERCIAL_OFFER_QUOTE_APPROVE    ADMIN, SALES_MANAGER
```

`COMMERCIAL_OFFER_QUOTE_APPROVE` is deliberately narrower, and deliberately excludes
`SALES_USER`, implementing decision 4. The residual limitation - a Sales Manager may approve
their own quote - is recorded here rather than hidden, and is `APR-001`'s to close.

### Preconditions, and the row lock

Generation requires, checked in this order:

```text
1. Offer status is DRAFT, READY_FOR_REVIEW or SUBMITTED.
   ACCEPTED, REJECTED, WITHDRAWN and CLOSED are refused - a customer-facing quotation for a
   concluded offer is not a meaningful document.
2. Account traceability resolves (the existing Slice 6A.1 rule, reused, not reimplemented).
3. At least one ACTIVE offer line exists.
```

Anything else is `422`.

**`lock_commercial_offer_row` is taken before `offer_status_code` is read.** Slice 9B's contract
requires this of every operation that reads the status and then inserts a dependent record, and
names four such dependants today; quote generation is a fifth.

Note for the implementer, because getting this wrong would be silent: the discovery guard in
`backend/tests/test_slice_9b_pilot_hardening.py` (`EXPECTED_STATUS_WRITING_FUNCTIONS`) detects
functions that **write** `offer_status_code`. Quote generation only reads it, so **that guard
will not catch a missing lock here.** This slice therefore adds its own AST ordering test for
the generation path, mirroring `test_the_mark_submitted_path_takes_the_row_lock_before_reading_status`.
Relying on the existing guard would be assuming a control that does not cover this case.

Approval requires the quote document to be `DRAFT` and not superseded. Approving an already
approved, or a superseded, version is `422`.

Generating version N+1 sets `superseded_at` on every earlier version of the same offer in the
same transaction, leaving their status and approval facts untouched.

### Events

```text
CommercialOfferQuoteDocumentGenerated
CommercialOfferQuoteDocumentApprovedForIssue
DocumentGenerated                      (documents module, for the stored artifact)
```

`source_module = commercial_offers`, `record_type = commercial_offer_quote_document`,
`record_public_id = quote_document_public_id` for the first two. Payloads carry metadata only -
version, reference, fingerprint, byte size - never the rendered document and never its content.

### Submission readiness

Two advisory rows added to `GET /api/commercial-offers/{public_id}/submission-readiness`:

```text
QUOTATION_DOCUMENT   PASS if a non-superseded APPROVED_FOR_ISSUE version exists;
                     ATTENTION_REQUIRED otherwise
INTERACTION_LOG      PASS if at least one interaction is recorded against the offer or its
                     Opportunity/Account chain; ATTENTION_REQUIRED if none
```

`INTERACTION_LOG` is the FRD row (source line 855, "communications ... in a time-stamped log
before a quote can be raised") that Slice 9D deferred out of its own package to avoid touching
another module, and whose closure note assigned it to this round. It is **advisory, not
blocking**, exactly as `interaction-contract.md:283` records: hard enforcement waits until the
pilot habit forms.

The readiness route creates no `business_event`, as today.

### Frontend

A "Quotation document" section on the Commercial Offer detail page's **Submission** tab
(Slice 6I.1 tab structure preserved): version list with status, generated by/at, approved by/at;
Generate and Approve actions, each role-gated and each with its **own** local success/error
message beside its own button, per the `AGENTS.md` UI action-feedback rule; a Download link per
version; and a staleness notice on any version whose fingerprint no longer matches.

Two known constraints, both recorded rather than worked around:

- This lands in `CommercialOfferDetailPage.tsx`, already ~5,700 lines and named in
  `UI_UX_CARRY_FORWARD.md` as needing decomposition. This slice adds to that file rather than
  decomposing it, because that document explicitly says the decomposition must not happen before
  a frontend component-test capability exists.
- The section therefore has **no component test**, for the same reason 9B's and 9D's UI does
  not. See `docs/agent/DEFERRED_REQUIREMENTS.md`.

## Test plan - each written to fail first, against the defective code

A test never shown to catch its defect is an assertion of intent, not a control.

1. A `<script>` payload in the Account name, offer title, line description and T&C snapshot is
   escaped; the rendered output contains no `<script` and no `on...=` handler attribute.
2. `render_quote_html` is deterministic: the same payload rendered twice is byte-identical.
3. The stored bytes are unchanged after the offer is edited, and the version is then reported
   `is_stale = true`.
4. Generation is refused for `ACCEPTED`, `REJECTED`, `WITHDRAWN` and `CLOSED` offers.
5. Generation is refused with no active line, and with Account traceability missing.
6. AST ordering: the generation path calls `lock_commercial_offer_row` before it first touches
   `offer_status_code`.
7. A concurrent transition defeats an in-flight generation (the Slice 9B concurrency pattern).
8. `SALES_USER` is refused approval (`403`); `SALES_MANAGER` and `ADMIN` succeed.
9. Approving an already-approved version, and approving a superseded version, are both `422`.
10. Generating V2 sets `superseded_at` on V1 **and leaves V1's `APPROVED_FOR_ISSUE` status,
    `approved_by` and `approved_at` intact.**
11. A direct `INSERT` of `quote_status_code = 'APPROVED_FOR_ISSUE'` with a null `approved_by`
    is refused by the **database constraint**, bypassing the API entirely.
12. `.html` is not in `ALLOWED_UPLOAD_EXTENSIONS`: `POST /api/documents/upload` refuses an
    HTML file, before and after this slice.
13. A failure of the quote-document insert leaves **no** orphaned object in the storage root
    (measured, start and end, as 9C's module-scoped fixture does).
14. The generated document's event is `DocumentGenerated`, not `DocumentUploaded`.
15. Both readiness rows report correctly in present and absent states.
16. The route inventory guard passes; the three new routes are in `POST_BASELINE_NEW_ROUTES`;
    the frozen 31 / 110 / 76 counts are unchanged.

## Deferred

**Retention and read-access auditing.** Unchanged and *not* triggered by this pilot: owner
decision 5 confirms the UAT pilot uses synthetic data only, so no real customer correspondence
or customer-identifying quotation enters the system. The single existing
`DEFERRED_REQUIREMENTS.md` entry - which already spans 9D message bodies and 9C documents - is
extended to name generated quotations as a third thing it covers, rather than a fourth entry
being created. It stays one policy question with one trigger: **real customer data**.

**Server-side PDF.** Decision 1. Replaceable behind `render_quote_html`.

**Margin thresholds, and full maker-checker.** Both need `APR-001` and the PF-1A-E3 authority
configuration. Named in the FRD, out of scope here.

**Emailing the quote.** Recording that it was sent is already covered by Slice 6I submission
evidence; transmitting it is not in this system.

**A component test for the new UI.** Blocked on the frontend component-test capability, which
is the package immediately after this one.

## Verification gate before proposing the candidate

Beyond the standard gate in `AGENTS.md`:

- If `backend/requirements.txt` changes, run `pip-audit` **outside** the Compose container.
  This slice is not expected to add a dependency; if it does, that check is mandatory.
- If `.github/workflows/` changes, run the pinned `actionlint` image.
- Re-measure the document storage root immediately before asserting anything about it. A
  measurement is true only as of when it was taken.
- Confirm `alembic current` equals `alembic heads` after the migration, and that the empty-
  database upgrade succeeds - the new CHECK constraints are DDL that a stale local volume will
  not exercise.

## Implementation record

Implemented on branch `slice-9e-quotation-generation`, base commit `9648c9e` (this frozen
specification). Model: PBL's design lead designed and froze the specification above and put the six
decisions to the project owner; PBL's development team built it.

### Files changed

The complete candidate is **24 paths: 19 modified, 5 new.** (This count grew from an earlier
20/17/3 draft of this section as the acceptance document, continuity note and two rounds of
full-suite-driven test corrections were added; restated here to reconcile against
`git status` rather than leave a stale count standing.)

Modified (19):

```text
backend/app/models_metadata.py                                       additive (register the new model)
backend/app/modules/authorization/contract.py                        additive (2 new permission codes)
backend/app/modules/commercial_offers/contract.py                    additive (quote-document constants)
backend/app/modules/commercial_offers/models.py                      additive (CommercialOfferQuoteDocument)
backend/app/modules/commercial_offers/repository.py                  additive (quote-document queries, 2 locks)
backend/app/modules/commercial_offers/routes.py                      additive (3 new routes)
backend/app/modules/commercial_offers/schemas.py                     additive (quote-document schemas)
backend/app/modules/commercial_offers/service.py                     additive (generate/list/approve, snapshot,
                                                                       fingerprint, 2 readiness rows)
backend/app/modules/documents/contract.py                            additive (QUOTATION type, GENERATED_CONTENT_TYPES)
backend/app/modules/documents/service.py                             refactored (shared _persist_stored_document
                                                                       helper; upload_document rebuilt on top of it;
                                                                       store_generated_document added)
backend/tests/fixtures/post_baseline_tightened_routes.py             additive (3 new routes pinned)
backend/tests/test_commercial_offers_api.py                          2 pre-existing tests corrected (see below)
backend/tests/test_slice_9c_document_storage_foundation.py           2 pre-existing tests corrected (see below)
docs/agent/DEFERRED_REQUIREMENTS.md                                  extended, not duplicated
docs/agent/contracts/commercial-offer-contract.md                    updated (Slice 9E section)
docs/agent/contracts/documents.md                                    updated (Slice 9E extension)
docs/agent/slices/slice-9e-quotation-generation.md                   this file (implementation record appended)
docs/continuity/NEXT_STEPS.md                                        status updated to implemented/self-tested
frontend/src/pages/commercial-offers/CommercialOfferDetailPage.tsx   Quotation Document section, generate/approve/
                                                                       download actions, role gating; 3 stale
                                                                       "document generation ... deferred" mentions
                                                                       corrected on the same page (found live
                                                                       during manual browser testing - see below)
```

New (5):

```text
backend/alembic/versions/20260908_0035_quotation_generation.py
backend/app/modules/commercial_offers/quote_render.py
backend/tests/test_slice_9e_quotation_generation.py                  (42 test functions, 46 collected cases with
                                                                        parametrization, after correction pass 2;
                                                                        28 functions / 32 cases as first delivered)
docs/agent/acceptance/slice-9e-quotation-generation-acceptance.md
docs/continuity/SLICE_9E_QUOTATION_GENERATION.md
```

### A third connective-tissue fix, found during manual browser testing

The Commercial Offer Overview tab carries a static banner ("Slice 4F adds thin Commercial Offer
lifecycle closure... document generation... remain deferred") and two "Deferred boundaries"
list items mentioning "quote/PDF document generation" and "Document generation and formal
tender/customer-format submission proof workflow". This text predates Slice 9E by many slices
and was already broadly stale (it still names only Slice 4F/5A while dozens of slices since
added functionality); a full rewrite of that legacy banner is out of scope for this slice. The
specific "document generation" claims, however, are now directly, factually false because of
this slice's own change, on the very page this slice adds its own new section to - discovered
live while manually walking through the feature in the browser, where the new Quotation
Document section sat directly below text saying document generation "remain[s] deferred". This
narrow, targeted correction (not a broader banner rewrite) is in scope because this slice is
what makes the existing wording wrong.

### Two pre-existing tests corrected, and why this is not scope creep

`docs/agent/DEFERRED_REQUIREMENTS.md`'s "Commercial Offer approvals and submission" entry was
already parked here as work this slice would implement; the deferred-item removal it required
in `COMMERCIAL_OFFER_SUBMISSION_READINESS_DEFERRED_ITEMS` broke two pre-existing tests in
`test_commercial_offers_api.py` that asserted `QUOTE_DOCUMENT_GENERATION` stayed `DEFERRED` and
that `deferred_count == 3`. Both are fixed to assert the new reality (2 deferred items, plus
real `QUOTATION_DOCUMENT`/`INTERACTION_LOG` rows) - this is required correction of a test this
slice's own change made stale, not unrelated churn.

Separately, the full-suite run surfaced a real pre-existing scoping bug in two Slice 9C tests
(`test_the_two_new_document_routes_are_pinned_to_their_exact_permissions` and
`test_every_document_route_requests_exactly_the_permission_the_fixtures_pin`): both asserted
exact equality/length against the **whole, shared** `POST_BASELINE_NEW_ROUTES` /
`POST_BASELINE_TIGHTENED_ROUTES` fixture dicts, rather than filtering to `/api/documents/*`
entries the way the neighbouring introspection code in the same test already does. That made
both tests fragile to *any* later slice adding a new route anywhere in the app, not specific to
Slice 9E. Both are corrected to filter by path prefix, matching the pattern the same file
already uses elsewhere - a genuine fix to a latent bug in 9C's own test, found and fixed here
because this is the first slice to exercise it, not a deviation from this slice's own scope.

### What changed from the frozen design, and why

- **`render_quote_html`'s input shape.** The frozen design named a
  `payload: QuoteSnapshotPayload`. The build instead passes the SAME canonical dict
  `compute_source_fingerprint()` hashes directly into `render_quote_html()`, rather than
  maintaining two independently-shaped structures (one dict for hashing, one dataclass for
  rendering). This removes an entire class of "the hash checks shape A but the render was
  built from shape B" drift bug, at the cost of a less strongly-typed render function
  signature. Recorded in `quote_render.py`'s own module docstring. No business meaning, output
  content or field name changes.
- **Quote-document approval concurrency.** The frozen design's "Preconditions, and the row
  lock" section covers generation in detail but does not spell out an equivalent lock for
  approval. Approval reads `quote_status_code` and `superseded_at` then conditionally writes -
  the same read-then-write shape Slice 9B's contract requires a lock for - so the build adds
  `lock_commercial_offer_quote_document_row`, a second lock scoped to the quote-document row
  itself (a distinct row from the parent offer, so `lock_commercial_offer_row` does not cover
  it). Without it, two concurrent approvals of the same version could both read `DRAFT` and
  both write, with the second approver's identity silently overwriting the first's - exactly
  the "asserted, not enforced" gate shape decision 3 explicitly disclaims wanting to build.

### Test plan mapping

Every numbered item in the frozen "Test plan" above has at least one test in
`test_slice_9e_quotation_generation.py`; items 1 and 2 are additionally covered as pure unit
tests against `render_quote_html` directly (no database), and two tests spot-check that the
escaping test and the AST ordering test are not vacuous by deliberately disabling the real
control and confirming the test would then fail - the "watch it fail" discipline applied
retroactively to the finished tests rather than only during development.

### Verification performed

```text
docker compose exec backend alembic upgrade head          - applied cleanly to 20260908_0035
docker compose exec backend pytest tests/test_slice_9e_quotation_generation.py -q
    -> 32 passed
docker compose exec backend pytest tests/test_authorization_route_migration_guard.py -q
    -> 99 passed (frozen 31/110/76 counts unchanged)
docker compose exec backend pytest -q                      (full backend regression, twice)
    -> see "Full regression" below
```

A direct `INSERT` against `crm_commercial_offer_quote_document` claiming
`quote_status_code = 'APPROVED_FOR_ISSUE'` with a null `approved_by` was verified rejected by
the database (`ck_quote_document_approval_is_complete`) both manually, before any test existed,
and again as an automated regression test.

`backend/requirements.txt` was not changed by this slice, so `pip-audit` was not required by
the verification gate above. No `.github/workflows/` file was changed.

Frontend: `npm run typecheck`, `npm test` (54 passed - the route table is unchanged since this
slice adds no new public URL, only backend routes and a new section on the existing Commercial
Offer detail page) and `npm run build` all pass.

### Manual browser walkthrough

Performed against a freshly seeded Draft offer with one active line whose description
deliberately contained `<b>bold</b> & "quoted"` text, as `sales1` then `manager1`:

1. Generated V1 as `sales1` (`201 Created`); confirmed the version card renders with no Approve
   button for that role, and the local success message appears beside the Generate button.
2. Downloaded V1's content directly through `GET /api/documents/{id}/content` and confirmed the
   hostile line description round-tripped through the real database -> snapshot -> render ->
   store -> download pipeline fully escaped (`&lt;b&gt;bold&lt;/b&gt; &amp; &quot;quoted&quot;`),
   not merely in the isolated unit test.
3. Logged in as `manager1`; confirmed the Approve for Issue button now appears; clicked it
   (`200 OK`); confirmed the status badge changed to Approved for Issue, Approved at populated,
   and the per-version success message appeared beside that specific card.
4. Refreshed Submission Readiness; confirmed `QUOTATION_DOCUMENT` moved from
   `ATTENTION_REQUIRED` to `PASS` with the approved reference named in its message.
5. Generated V2; confirmed V1 now shows "(superseded)" while **retaining** its Approved for
   Issue status, approver and timestamp - the live proof of the supersede-without-erasing
   behaviour the database CHECK constraint and the automated test both also cover.
6. Found and fixed a real, if narrow, documentation-staleness defect live: the Commercial Offer
   Overview tab's static banner and "Deferred boundaries" list still said document generation
   "remain[s] deferred", directly beneath this slice's own new section proving otherwise - see
   "A third connective-tissue fix" above.

All test data created for this walkthrough was cleaned up afterward (`document-store` root
confirmed at 0 files) and is not part of the committed candidate.

### Full regression

Three full-suite runs were performed. The first surfaced 6 failures and 1 error, all diagnosed
and fixed or accounted for as described above: 4 were pre-existing tests this slice's own
connective-tissue changes made stale or exposed and are corrected in this candidate; the
remaining 2 failures plus the 1 error - an account-paging test, a business-authority atomicity
test, and a business-authority atomicity setup error, none touching any file this slice
changed - were confirmed pre-existing full-suite ordering flakiness against the shared
development database, not caused by this slice, by reproducing them in isolation and alongside
the new 9E test file and seeing them pass cleanly. A clean run after all corrections:
**1261 passed, 0 failed, 0 errors, in 607.17s (0:10:07)** - every one of the previously-flaky
cases passed on its own in this run too, consistent with ordering flakiness rather than a
deterministic defect.


## Correction pass 1

Independent review returned `CORRECTION_REQUIRED` with four findings. All four are corrected
below. Every correction test was written **before** its fix and confirmed failing against the
pre-correction code; the captured pre-fix failures are quoted with each finding.

### Finding 1 [P1] - an approved quotation still presented itself as Draft

`render_quote_html` was called once, at generation, with `approval_status_display="Draft"` and
`approved_status_is_final=False` hard-coded. Approval updates only the quote-document row and
never re-renders, so **every** document ever generated said "Draft" for the life of the file,
including after it was approved and issued. The issued document therefore contradicted its own
approval record.

Worse than a missing feature: the render function *took* approval-status parameters, which read
as though they tracked current state, while nothing ever supplied a value other than "Draft".
Infrastructure that looks like a control and is not one.

Pre-fix failure:

```text
assert "Draft" not in issued
AssertionError: the issued document still presents itself as Draft after approval
```

**Correction.** The frozen bytes are not rewritten on approval - that would destroy the
immutability the checksum and fingerprint exist to prove. Instead the document no longer asserts
any mutable status at all. Both parameters are removed from `render_quote_html` (a dead parameter
that looks live is what caused this), and the document carries an immutable pointer instead:
"Issue approval for this quotation is recorded in the PBL CRM system against quote reference
...". Approval status now lives only in the system record and the UI.

**Recorded residual, not silently accepted:** a Draft download and an approved download are now
byte-identical, so the document itself cannot signal that it was never approved. The UI is where
that distinction is made. If PBL wants the issued document to assert "Approved for Issue" on its
face, that is a separate approved-artifact design (generate-at-approval, or a second artifact)
and needs owner confirmation - it is not a defect fix, and this pass deliberately did not invent
it.

### Finding 2 [P1] - a failed commit leaked the stored file

The single most serious finding, because it **regressed a working Slice 9C guarantee**. Slice 9C
kept `db.commit()` inside the try block that deleted the stored object on failure. This slice's
refactor moved the commit out into `upload_document`, so a failing commit rolled the transaction
back but left the bytes on disk, unreferenced by any row and unreachable through the application.

The code comment at that site claimed the opposite - that the handler "covers a failure in
db.commit() itself" - while the code did not do it. An asserted control, exactly the failure mode
this project keeps naming.

Pre-fix failure (fault-injecting a failing commit, asserting on the storage-object count):

```text
AssertionError: a failed db.commit() left the stored object behind
assert 2 == 1
```

The module-scoped storage-leak fixture adopted from Slice 9C caught it independently:

```text
AssertionError: this module leaked 1 stored object(s) (started with 1, ended with 2)
```

**Correction.** A shared `delete_stored_document_object(row)` helper in `documents/service.py`,
called after rollback by **both** `upload_document` and Slice 9E's generation path. The duplicate
`_delete_orphaned_generated_document` this slice had written in `commercial_offers/service.py` is
deleted in favour of it - one compensation path, not two. The documents contract now states the
rule for any future caller: *if you commit after `_persist_stored_document` returns, you own the
compensation for that commit failing.*

The reviewer's second point here is also taken: this slice's original orphan test asserted only
that the `document_metadata` row had rolled back, which a rollback gives for free and which
proves nothing about the bytes. Both orphan tests now assert on the **storage-object count**, and
the module-scoped leak fixture catches the next one regardless of what any individual test checks.

### Finding 3 [P2] - unrelated addresses and known-invalid GSTINs could be frozen in

`build_quote_snapshot` took every active Account address and every active GSTIN. That let a
`SITE`, `BILLING_DRAFT` or `OTHER` address, or a GSTIN marked `REJECTED_INCORRECT`, be frozen
into a customer-facing quotation. `BILLING_DRAFT` is the sharpest case: the Account contract
defines it as draft CRM information explicitly *not* Finance-approved billing master data.

Because the artifact is frozen, correcting the Account afterwards cannot repair a version that
already captured the wrong value - it can only be superseded.

**Correction.** Addresses are filtered to `REGISTERED_OFFICE` and `COMMUNICATION` and carry their
type label so a reader can tell them apart; GSTINs marked `REJECTED_INCORRECT` are excluded, while
every other verification state stays quotable (an unverified GSTIN is the customer's stated
number, which is what a prototype-stage quotation legitimately carries).

### Finding 4 [P2] - the preparer and approver were not visible

The API returned `generated_by` and `approved_by`, but the version card displayed neither, and the
frozen document omitted the specification's required prepared-by value. A one-step attested gate
whose whole purpose is recording that a *named* person approved a *specific* version is weakened
if the normal application cannot show who that was.

**Correction.** The listing query resolves both actors to `display_name` through `LEFT JOIN`s in
the same query (one round trip, and a version whose actor was later removed still lists with a
null name rather than disappearing). The API exposes `generated_by_display_name` and
`approved_by_display_name`; the version card shows Prepared by and Approved by; and the frozen
document carries the prepared-by identity - safe to freeze, unlike approval status, because the
preparer is known and immutable at generation time.

## Found during correction pass 1, not raised by review

Three further items were found while working the findings above. Recorded because "the reviewer
did not mention it" is not evidence that it is right.

1. **An unpriced quotation asserted a zero price.** Lines with no rate rendered
   "Total (INR) 0.00" - a customer document stating a price the system does not have. Now renders
   "Not priced", derived from the lines so the canonical snapshot shape is unaffected. Whether
   generation should be *blocked* without rates is a business rule, not an engineering default,
   and is left for the owner rather than invented here.
2. **The document's timestamp and the record's timestamp came from two different clocks.** The
   HTML rendered a Python `datetime.now()` while the row took the database's `CURRENT_TIMESTAMP`
   - two sources for one fact, which disagree whenever the application and database clocks do,
   leaving an audit record that contradicts the document it describes. Now one value, computed
   once and bound into the insert.
3. **Quotation feedback survived navigation between offers.** Generating or approving on one
   offer left its confirmation visible after navigating to another. Cleared in
   `loadCommercialOffer`'s canonical reset block - deliberately *not* in `loadQuoteDocuments`,
   because the approve and generate handlers reload the list immediately after setting their
   success message and clearing there would wipe the confirmation the user needs to see. That is
   the Slice 9B lesson, and the first version of this fix made exactly that mistake before it was
   caught.

Additionally, one safety property that had only been *reasoned* about is now proven: approval
locks the quote-document row while generation locks the offer row - two different rows - so their
interlock is not self-evident. They do interlock, because `supersede_earlier_quote_documents`
UPDATEs the same quote-document rows an in-flight approval holds locked. A concurrency test now
pins it: a superseded version cannot be approved for issue by a racing request.

## A shape-change hazard this pass surfaced

Correction pass 1 changed the canonical snapshot shape - addresses are now filtered and labelled,
GSTINs filtered. **Any change to that shape invalidates staleness comparison for every previously
generated version**, because each stored `source_fingerprint` was computed over the shape in force
when it was generated; those versions would all begin reporting `is_stale = true` despite their
offers being unchanged.

Harmless here only because the slice is unreleased and no stored quotation exists outside test
data. Recorded in the Commercial Offer contract so a future maintainer treats a shape change
against released data as a migration concern, and bumps the snapshot's own `schema_version`.

## Recorded for the owner, not decided here

- **Should generating a quotation require priced lines?** Today an unpriced quotation generates
  and prints "Not priced".
- **Should approving for issue be blocked when the offer itself has since become terminal?**
  Approval currently checks only the quote document's own state, so a quote can be approved for
  issue against an offer that has since been rejected or withdrawn. Arguable both ways -
  approving for record after the fact may be legitimate - so it is recorded rather than silently
  ruled on.

## Correction pass 1 verification

```text
docker compose exec backend pytest tests/test_slice_9e_quotation_generation.py -q
    -> 43 passed (39 functions; 32 cases as first delivered + 11 correction tests)
docker compose exec backend pytest -q                      (full backend regression)
    -> 1272 passed, 0 failed, 0 errors, in 596.76s (0:09:56)
       exactly +11 over the pre-correction 1261, matching the 11 tests added
docker compose exec backend pytest tests/test_slice_9e... tests/test_slice_9c... tests/test_documents.py -q
    -> 86 passed, and the storage root measured 0 files before and after, with 0
       document_metadata rows carrying a storage_key and 0 quote-document rows
Frontend: npm run typecheck / npm test (54 passed) / npm run build   -> all clean
alembic current == alembic heads == 20260908_0035
```

### A harness weakness this pass exposed

While re-measuring the storage root after the correction run it held 2 orphaned `.txt` files and
one `document_metadata` row whose bytes were missing. Traced rather than assumed: all of it was
residue from this pass's own **pre-fix failing runs** - the `.txt` files from the commit-leak
before it was fixed, and the row-without-bytes from a fixture teardown that aborted on the
`business_party_address` foreign key before that cleanup gap was fixed. None of it was produced
by the corrected code; after clearing the residue, the three storage-touching modules run to
completion leaving the root at 0 files and 0 rows.

Two things are worth recording anyway, because "it was only debugging residue" is a reason to
explain it, not a reason to stop looking:

- `_delete_records` in the 9E test module deletes stored files **before** deleting rows, so an
  aborted row-delete leaves rows referencing bytes that are already gone. Deleting rows first
  would invert the failure into orphaned files instead. There is no ordering that is safe under
  an arbitrary mid-cleanup failure without two-phase logic; the practical mitigation is that the
  cleanup no longer fails (the FK gap is fixed), and this note so the next person recognises the
  shape.
- The module-scoped leak fixtures compare before and after **within one run**, so they cannot see
  residue a previous run left behind. They are still worth having - they caught this slice's own
  leak the moment it appeared - but a genuinely empty storage root is a separate check, worth
  making explicitly when asserting current state.


## Correction pass 2

Independent review of correction pass 1 returned `CHANGES REQUIRED` with two P1 findings. Both
are corrected, and both are cases where a pass-1 fix introduced a *different* wrong statement
rather than removing the wrongness.

### Finding 1 [P1] - a Draft document claimed that issue approval was recorded

Pass 1 removed the "Draft" badge because it became false after approval, and replaced it with
"Issue approval for this quotation is recorded in the PBL CRM system...". That is false for every
Draft - and every document is Draft at the moment its bytes are frozen. Read away from the
application UI, the sentence works as confirmation that the quotation was approved, undermining
the gate inside the very artifact the gate governs.

The error is instructive: pass 1 reasoned explicitly that the wording had to "remain true for the
life of the file", then checked only the end of that life and not its beginning.

Pre-fix failure:

```text
assert "approval for this quotation is recorded" not in draft_html.lower()
AssertionError: a Draft document claims an issue approval that does not exist
```

**Correction.** The footer now reads "Verify the current issue-approval status for this quotation
in the PBL CRM system against quote reference ...", which is an instruction rather than an
assertion and is therefore true before and after approval. Two tests pin it: one proves a
pre-approval document makes no approval claim, the other proves the wording survives approval
**and** that the bytes are byte-for-byte unchanged.

### Finding 2 [P1] - mixed priced and unpriced lines produced a false partial total

Pass 1's `_format_total` returned "Not priced" only when *every* line amount was missing, while
the snapshot total independently summed whichever amounts existed. One priced line at INR 100
plus one unpriced line therefore printed **"Total (INR) 100.00"** - a partial sum presented as
the complete quotation total. Reachable because `rate_amount` is optional on an active line.

Reproduced by runtime probe before the fix, and then as a failing test:

```text
assert "100.00" not in total_cell
AssertionError: assert '100.00' not in 'Total (INR).../td>'
```

**Correction.** Any missing active-line amount now prevents a numeric grand total. The two
non-numeric outcomes stay distinct because each is exactly true of its own case: "Not priced"
when no line is priced, "Not fully priced" when some are. Still derived from the lines rather
than a new snapshot key, so the canonical shape - and every stored fingerprint - is untouched.

### A test-quality defect found in this pass's own test

The first version of the partial-total test sliced the total cell using
`html.index("gst-note")` as its end anchor. That matched the `.gst-note` CSS rule inside the
`<style>` block, which appears *before* the table, producing an empty slice - so the test's
central assertion passed against an empty string and proved nothing. Caught because the test was
run against the unfixed code and its failure message did not match the defect being reproduced.
Anchoring now searches forward from the total label. Worth recording: "the test failed" is not
the same as "the test failed for the reason I intended", and only the second one is evidence.


## Owner decisions, 9 September 2026 (correction pass 2)

Independent review of correction pass 1 raised two questions as business decisions rather than
implementation choices. Both were put to the project owner in plain language.

| # | Decision | Answer |
| --- | --- | --- |
| 7 | May a quotation be generated when some or all lines have no rate? | **Allowed for now, with honest wording; block later, after pilot testing** |
| 8 | May a quotation be approved for issue once the offer has concluded? | **No - blocked for Accepted, Rejected, Withdrawn and Closed** |

### Decision 7 - deferred deliberately, with a trigger

Independent review recommended blocking generation outright. The owner chose to allow it during
the pilot and block it afterwards, and asked whether phasing it that way was feasible. It is:

- The honest wording is already in place, so nothing false is printed in the meantime - the
  total reads "Not priced" or "Not fully priced" rather than a number.
- Adding the block later is a self-contained precondition in
  `generate_commercial_offer_quote_document`, returning `422` exactly as the existing
  "no active lines" check does, plus a test. No migration, no data-shape change, no contract
  freeze implication, nothing that gets harder by waiting.
- There is a positive reason to wait: the pilot exists partly to watch PBL users enter data
  themselves, and refusing to generate until every rate is filled would obstruct exactly the
  exploratory data entry the pilot is meant to observe.

The one consequence, recorded rather than glossed: partly-priced versions generated during the
pilot stay frozen as they are once the block is added. Harmless here because the pilot is
synthetic-only (decision 5).

**Trigger for revisiting: before the CRM pilot's findings are actioned, and in any case before
any real customer data enters the system.** Carried in
`docs/agent/DEFERRED_REQUIREMENTS.md` so it is not lost with this slice's own record.

**Superseded, recorded 11 September 2026.** Decision 7 was superseded by the owner on
9 September 2026: incomplete pricing is gated at **approval for issue** instead of generation,
and in the UI cleanup package (step 4 of the road to the pilot) rather than after the pilot. On
11 September 2026 the owner added that approval must also refuse a version the offer has changed
since, because a check of current lines alone would let a version frozen as "Not fully priced"
be approved once the missing rate was filled in. Generation is unchanged and still allowed with
incomplete pricing. Decision 7 above is left as written, per ADR-013, as the record of what was
decided on 9 September; the control now in force is described in the "Slice 9E" section of
`docs/agent/contracts/commercial-offer-contract.md` and in the superseded entry of
`docs/agent/DEFERRED_REQUIREMENTS.md`.

### Decision 8 - implemented in this pass

Approval is refused when the Commercial Offer is `ACCEPTED`, `REJECTED`, `WITHDRAWN` or
`CLOSED`. "Approved for Issue" is a present authorisation to send the document to a customer;
applying it after the offer has concluded asserts an authorisation that no longer means
anything. Retrospective confirmation of which version was actually sent, if ever wanted, needs
its own archival action rather than reusing this one.

This turned approval into a read-then-write against `offer_status_code`, so it now takes the
parent offer's row lock **before** reading the status, and the quotation row lock after -
deliberately the same order generation uses, so the two paths cannot deadlock against each
other. Six tests cover it: four for the blocked statuses, an AST ordering guard, and a
concurrency test that holds the offer lock, proves approval blocks on it, transitions the offer
to `REJECTED`, and then proves approval is refused and the version is still `DRAFT`.


## Correction pass 2 verification

```text
docker compose exec backend pytest tests/test_slice_9e_quotation_generation.py -q
    -> 52 passed (32 as first delivered, +11 pass 1, +9 pass 2)
docker compose exec backend pytest (5 directly affected modules)  -> 275 passed
docker compose exec backend pytest -q   (full backend regression) -> 1281 passed, 0 failed
       exactly +9 over the pass-1 total of 1272, matching the 9 tests added
Frontend: npm run typecheck / npm test (54 passed) / npm run build -> all clean
alembic current == alembic heads == 20260908_0035
Storage root 0 files; 0 quote-document rows; 0 document rows carrying bytes
```

### Two process notes from this pass

**A background full-suite run was invalidated by editing source while it ran.** The run reported
9 failures, which reflected a moving target rather than any state of the code - source files were
being edited mid-run. It was discarded and rerun cleanly. Same shape as the earlier mistake of
rebuilding a container during a run. The rule: once a full-suite run starts, change nothing until
it finishes.

**Run duration is highly variable on this host and should not be read as a signal without
repetition.** The same 52 tests measured 23.6s, 54.9s and 97.6s across runs of identical code,
and one overnight full-suite run took 1:35:40 against a normal ~10 minutes. Investigated rather
than assumed: no table bloat (dead tuples in the tens, tables in KB), no accumulated data (1275
business_event rows, 6 offers), no resource pressure, and no per-test regression once the
deliberate costs are accounted for. The three concurrency tests each spend ~2s by design, because
each proves a worker genuinely blocks on a lock by waiting on `join(timeout=2.0)` - that wait
*is* the proof, and shortening it would weaken the test rather than optimise it.
