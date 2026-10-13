# Slice 7C - Work Order Line Operational Detail

## Status

**MERGED, 14 September 2026** through PR #58 (merge commit `3fff30a`), then a small follow-up (below).
Owner decisions 1-6 and both follow-ups were agreed the same day.

Track 2 (Hiring) first package. Foundation Slice Mode.

**Changed by Slice 7D, 14 September 2026.** The billing basis and contracted hours described below
moved out of this slice's table and routes into the line's billing terms, as versioned terms
(`docs/agent/slices/slice-7d-work-order-line-billing-terms.md`). This document is kept as the record of
what 7C built; `docs/agent/contracts/work-order-contract.md` has the current shape.

```text
Branch                 hiring/slice-7c-work-order-line-detail
Worktree               <a separate worktree>
Baseline commit        79983e2 (origin/main)
Alembic parent         20260908_0035 (quotation generation)
Migration slot         20260908_0036, assigned by the owner to the Hiring lane
Frozen contract hash   accepted-offer-to-work-order-handoff-contract.md
                       sha256 70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a
Review                 one independent review (the slice carries a migration and a new permission)
Correction cap         three cycles; a fourth means split the package, not correct it again
```

## Why this slice exists

A Work Order line today is a copy of the accepted Commercial Offer line: scope, category,
quantity, quoted UOM and rate. It says nothing about **where** the work happens, **which GSTIN
and address the customer is billed on**, **on what basis the line is billed**, or **what the
customer calls the line** on their own order. Operations cannot plan against it and a later
release gate or billing slice has nothing to check.

What the source documents require (`docs/reference/erp-source-extracts/CRM_HIRING_RELEVANT_REQUIREMENTS_EXTRACT.md`,
source sections 2.3, 2.4 and 7):

```text
- Work Order line-level shipping addresses and billing GSTNs are required.        -> this slice
- Customer master should be PAN-based with GSTN billing addresses as children.    -> reuse Account data
- Billing UOMs include Hour, Shift, Day and Month.                                -> this slice
- Contracted hours ... before OT can be claimed.                                  -> hours only; OT deferred
- Line-level T&C customization ... with header defaults.                          -> DEFERRED
- Contract valid-from and valid-to dates are mandatory.                           -> header, DEFERRED (7B)
- Work Order line billing GSTN/address locks after E-Invoice.                     -> DEFERRED (billing)
```

`WBT-001` (APPROVED) settles the four billing bases and says missing terms produce an incomplete
result, never an invented default. `WRR-001` (APPROVED) needs "Account and site/location public
references" on every Resource Requirement - this slice is where the line gets them. Under ADR-013
the source rows are directional guidance; they are adopted as written, so no deviation record is
needed.

## Owner decisions, 14 September 2026

Put in plain business language, per `AGENTS.md`.

| # | Question | Owner answer |
| --- | --- | --- |
| 1 | Where do the site and billing details come from? | **Picked from the Account.** If the site or billing address on the customer's Work Order is not on the Account yet, enter it on the Account first, then pick it |
| 2 | Who may fill in and change these details? | **Sales User, Sales Manager, Operations and Admin.** Finance and Management see them read-only |
| 3 | Until when can they be changed? | **Until execution begins, i.e. before mobilisation.** Where an advance payment is involved the billing details are needed soon after the Work Order is received |
| 4 | When are billing terms entered? | **At the time the customer's Work Order is entered.** The Work Order contains all the information needed |
| 5 | Does missing information block anything? | **Yes, at Work Order release** - not in this slice |
| 6 | Must the site's state match the GST number's state? | **No** |

### Decision 3, and what it means today

Mobilisation does not exist in the application yet, so in this slice the only refusal is a
**Closed** Work Order. The owner confirmed that is right on its own terms: a Closed Work Order has
been completed and billed, so no change is permitted.

Owner follow-up, 14 September 2026 - the lock rule the later slices must implement:

- **Site, billing basis, contracted hours and customer line reference lock when mobilisation
  starts.** Changes after that go through a Work Order Amendment.
- **Billing GSTIN and billing address lock when the e-invoice is generated**, not at mobilisation,
  because a GSTIN can be found wrong after mobilisation and must still be correctable before
  billing. This matches the source rule "billing GSTN/address locks after E-Invoice".
- Release (7B) comes before mobilisation, so details may still change between release and
  mobilisation. Release checks completeness at the moment of release.

### Decision 4, and the question it leaves open

The answer settles **when** terms are entered: with the Work Order. It does not by itself settle
**how much this package builds**, which was the question intended. The full `WBT-001` term set -
normal rate and period, overtime rule, standby, breakdown treatment, minimum guarantee and
pro-rating, mobilisation/demobilisation, fuel, effective-dated versions - needs design against the
Annexure-10 billing examples and is at least as large as everything else in this document.

**Owner follow-up, 14 September 2026: agreed.** 7C stays as designed here (site, billing GSTIN
and address, billing basis, contracted hours, customer line reference). The rest of the billing
terms is the **next package, 7D - Work Order line billing terms**, before `WRR-001`. Both come
before release (7B), which is where decision 5 blocks, so a Work Order cannot be released
half-entered.

Decision 2 is implemented as a **new permission** holding exactly those four roles, not by reusing
`WORK_ORDER_CREATE`. Reusing it would mean that a later change to who may create a Work Order
silently changes who may edit billing details - the same coupling recorded against document upload
in `DEFERRED_REQUIREMENTS.md`. The cost is one seed row in the migration this slice already has.

## In scope

- One new table holding a line's operational detail, one row per Work Order line, created on first save.
- Per line: site address, billing GSTIN, billing address, billing basis, contracted hours per
  billing unit, customer line reference, operational notes.
- References validated against the Work Order's own Account.
- A version number on the detail, with a conflict check so two people cannot silently overwrite each other.
- Advisory completeness per line, computed on read.
- Two new routes, one new permission, one business event, migration `20260908_0036`.
- A minimal edit surface on the existing Work Order detail page.
- Smoke-data harness cleanup for the new table.

## Explicitly not in scope

- Any change to what `POST /api/work-orders/from-commercial-offer` accepts or returns, to
  `WorkOrderLineResponse`, or to `crm_work_order_line`.
- Overtime, breakdown, standby, minimum-guarantee, pro-rating, mobilisation, fuel and
  second-shift terms; term-set versions with effective periods (the rest of `WBT-001`, proposed
  as 7D - see decision 4).
- Refusing changes once mobilisation starts, and locking billing identity at e-invoice (neither
  event exists yet - see decision 3).
- Line-level T&C, contract validity dates, document checklist per line.
- Blocking anything on incompleteness; Work Order release (7B); Customer Master activation (7A).
- Capturing detail inside a Work Order Amendment, or applying an amendment (D-07, parked).
- GST determination, place-of-supply logic, e-invoice lock.
- A site master separate from Account addresses; Account address edit/deactivate.
- Resource Requirements (`WRR-001`) - the next package, with its own slice document.
- A new Playwright spec. Backend tests plus a manual browser check cover this foundation.

## Design

### Records

```text
crm_work_order_line_detail

id                                    integer identity PK
work_order_line_detail_public_id      UUID string, unique
work_order_line_id                    FK -> crm_work_order_line.id, UNIQUE (one detail per line)
site_address_public_id                FK -> business_party_address.address_public_id, nullable
billing_gstin_public_id               FK -> business_party_gstin.gstin_public_id, nullable
billing_address_public_id             FK -> business_party_address.address_public_id, nullable
billing_uom_code                      varchar(50), nullable
contracted_hours_per_billing_unit     numeric(9,2), nullable
customer_line_reference               unicode(255), nullable
operational_notes                     unicode text, nullable - never read by any calculation
detail_version                        integer not null, starts at 1
created_by / created_at / updated_by / updated_at
```

Constraints:

```sql
ck_wol_detail_billing_uom      billing_uom_code IS NULL OR billing_uom_code IN ('HOUR','SHIFT','DAY','MONTH')
ck_wol_detail_hours_positive   contracted_hours_per_billing_unit IS NULL OR contracted_hours_per_billing_unit > 0
ck_wol_detail_hours_not_hourly NOT (billing_uom_code = 'HOUR' AND contracted_hours_per_billing_unit IS NOT NULL)
ck_wol_detail_version          detail_version >= 1
```

The last one encodes `WBT-001`: hour-based billing uses actual hours, so a contracted-hours figure
on an hourly line is meaningless and must not be stored where a future billing engine could read it.

**Why a separate table rather than new columns on `crm_work_order_line`.** The handoff writes that
table and the frozen contract describes its output. A separate table means the handoff insert, the
handoff response and the 6O.2 amendment snapshot are untouched by construction, not by care. It
also gives the Hiring lane a table it wholly owns inside a module both lanes share.

**Why declared foreign keys to Account tables, on public IDs.** `crm_work_order` already declares
one to `business_party`; this follows it. Account addresses and GSTINs have no delete route, so the
keys cannot strand a Work Order. The keys target the Account tables' unique public-ID columns
(`ux_business_party_address_public_id`, `ux_business_party_gstin_public_id`) rather than their
integer ids, so a read needs no join into Account tables: the Work Order module resolves display
detail through the `accounts` service, keeping Account's tables Account's (ADR-017).

### What the existing `uom` becomes

`crm_work_order_line.uom` stays exactly as copied from the offer - the quoted unit, often free
text. `billing_uom_code` is the controlled billing basis `WBT-001` defines. The payload spec already
anticipates this split ("current prototype has `uom`; production should treat this as billing UOM
when appropriate"). The UI shows both, labelled "Quoted unit" and "Billing basis". Neither is
derived from the other.

### Validation, all against the Work Order's own Account

The Work Order's Account is `crm_work_order.business_party_id`, which the handoff guarantees.

| Field | Rule |
| --- | --- |
| `site_address_public_id` | an active address of type `SITE` on that Account |
| `billing_gstin_public_id` | an active GSTIN on that Account, verification state not `REJECTED_INCORRECT` |
| `billing_address_public_id` | an active address of type `REGISTERED_OFFICE` or `BILLING_DRAFT` on that Account |
| `billing_uom_code` | one of `HOUR`, `SHIFT`, `DAY`, `MONTH` |
| `contracted_hours_per_billing_unit` | > 0; must be empty when the basis is `HOUR` |
| line | belongs to the Work Order in the path |
| Work Order | not `CLOSED` |

A reference to another Account's address or GSTIN returns `422` with a message that names the
field, never the other Account. Account data is read through the `accounts` **service** layer, not
its repository, so this slice does not add to the ADR-030 rule-4 gap already recorded for other
modules.

`BILLING_DRAFT` is CRM-stage information, not Finance-approved billing master data (Account
contract, Slice 1H). Accepting it here is consistent with that: this slice records what Sales and
Operations know. Customer Master activation (`CMA-001`) is where Finance approves the billing
identity, and it can read these references.

### Save semantics

`PUT` replaces the whole detail. The request carries `expected_detail_version`: `null` when no
detail exists yet, otherwise the version the caller last read.

```text
lock the Work Order row (existing lock_work_order_row)
read the current detail for the line
expected version does not match      -> 409, nothing written
nothing would change                 -> 200 with the current detail, no event, no version bump
first save                           -> insert at version 1, event WorkOrderLineDetailRecorded
changed                              -> update, version + 1,  event WorkOrderLineDetailUpdated
```

The Work Order lock serializes two first saves for the same line; the unique constraint on
`work_order_line_id` is the backstop. The no-op rule exists because Slice 9D shipped the opposite
and recorded it as a defect: an event that looks like an edit when nothing changed.

### Completeness, advisory and computed on read

Each line reports `is_complete` and `missing_items`, drawn from:

```text
SITE_ADDRESS            no site chosen, or the chosen address is no longer active
BILLING_GSTIN           no GSTIN chosen, or it is inactive or now REJECTED_INCORRECT
BILLING_ADDRESS         no billing address chosen, or it is no longer active
BILLING_BASIS           no billing basis chosen
CONTRACTED_HOURS        basis is SHIFT, DAY or MONTH and no hours recorded
```

Computed on every read, never stored, so the line reflects the GSTIN's state now, not when it was
picked.

This is what makes the owner's correction process visible on the Work Order. When a GSTIN fails
validation - by SurePass, whether CRM or Plum runs the check - the Sales Executive obtains the
correct GSTIN, enters it on the Account and picks it on the line. Until they do, every Work Order
line still using the rejected GSTIN shows "Billing GSTIN missing (rejected)", so they can see
which lines need re-picking, and release (7B) will refuse it.

**The gap this depends on, outside this slice.** The Account module today can only *create* a
GSTIN, with its verification state fixed at creation. Nothing can later record that an existing
GSTIN was rejected, and SurePass is parked (relay through Plum later,
`DEFERRED_REQUIREMENTS.md`). So the line check cannot fire on a real rejection until either
SurePass lands or the Account module gains a way to mark an existing GSTIN rejected - the audited
manual route ADR-015 already permits. That is Account (CRM-lane) work; it is recorded here so the
dependency is not lost. 7C's tests set the state directly in the database. Addresses have the same
shape: no route deactivates one today, and the same check covers it when one does.

Customer line reference and notes are optional and never listed. Nothing is blocked.

### Routes

```text
GET  /api/work-orders/{public_id}/line-details
     require_permission(WORK_ORDER_READ)
     one entry per Work Order line, in line order, detail fields null where not yet recorded

PUT  /api/work-orders/{public_id}/lines/{line_public_id}/detail
     require_permission(WORK_ORDER_LINE_DETAIL_WRITE)
```

`GET /api/work-orders/{public_id}/lines` is **not** changed. Both routes are new and go in
`POST_BASELINE_NEW_ROUTES` in `backend/tests/fixtures/post_baseline_tightened_routes.py`, never in
the frozen PF-1A-E1 inventory. That file fails silently on a bad merge; it is read by eye after any
merge that touches it.

Response entry:

```text
work_order_line_public_id, line_number, source_offer_line_public_id
detail_public_id | null, detail_version | null
site_address:     { public_id, address_type_code, address_line1, city, state, postal_code } | null
billing_gstin:    { public_id, gstin, state_code, verification_state_code } | null
billing_address:  { public_id, address_type_code, address_line1, city, state, postal_code } | null
billing_uom_code, contracted_hours_per_billing_unit, customer_line_reference, operational_notes
is_complete, missing_items[]
updated_by, updated_by_display_name, updated_at
```

A resolved object is present only while its Account record is usable (active, of the right type,
and for a GSTIN not rejected); otherwise it is null, the bare `*_public_id` still shows what was
picked, and the item is listed in `missing_items`. That is why the objects carry no `is_active`
flag: it would always be true. (Corrected in review round 1, which found the earlier draft of this
list promised an `is_active` field the design makes redundant.)

Showing the GSTIN value is not a widening: every role holding `WORK_ORDER_READ` already holds
`ACCOUNT_READ` and can see the same number on the Account.

### Permission

```text
WORK_ORDER_LINE_DETAIL_WRITE   ADMIN, SALES_USER, SALES_MANAGER, OPERATIONS_USER
  "Record or change a Work Order line's site, billing GSTIN, billing address and billing basis."
```

Added to `POST_BASELINE_ROLE_PERMISSION_MATRIX` and seeded in `20260908_0036`, following the
`20260908_0035` seed pattern. The frozen 31 permission / 110 grant / 76 route baseline is unchanged.

### Events

```text
WorkOrderLineDetailRecorded    first save
WorkOrderLineDetailUpdated     later changing save
source_module = work_orders, record_type = work_order, record_public_id = Work Order public id
payload: work_order_line_public_id, detail_version, changed_fields[],
         site_address_public_id, billing_gstin_public_id, billing_address_public_id,
         billing_uom_code
```

`record_type = work_order` follows the 6O.2 amendment precedent for subordinate records. The
payload carries **public IDs, never the GSTIN value or address text**: the Account contract keeps
unnecessary statutory identifiers out of events.

### Frontend

On the existing Work Order detail page only; no new URL, so `frontend/src/routes.tsx` is not touched.

- The line table gains a compact "Site and billing" column: site city, billing basis, and a
  "Details complete" or "Missing: ..." badge.
- A "Site and billing details" section with one card per line. Users holding the write permission
  get dropdowns filled from the Account's addresses and GSTINs, a billing basis selector, an hours
  field that is disabled for Hour, and a Save button with its success or error message directly
  beneath it. Everyone else sees the same card read-only.
- A `409` reads: "Someone else changed these details. Reload to see their version."
- If the Account has no site address: "Add a site address on the Account first", linked to the
  Account page.

## The work_orders boundary, and how it is proven

CRM owns the handoff (5A, frozen by 6D.1) and amendment intake (6O.2). This slice adds detail
consumed **after** handoff and changes nothing the handoff produces. Proven, not asserted:

1. **Hash.** The frozen contract file is hashed before (recorded above) and after; the two must match.
2. **Shape pin.** A test calls the handoff and asserts the exact key set of `work_order` and of each
   `lines[]` entry equals today's set. A field added to either fails it.
3. **Untouched table.** A test asserts the handoff inserts no `crm_work_order_line_detail` row.
4. **Diff.** `create_work_order_from_commercial_offer`, `WorkOrderLineResponse`,
   `WorkOrderResponse` and `WORK_ORDER_LINE_SELECT_COLUMNS` show no change in the diff.

The shape pin in (2) includes `source_offer_line_number`, which the pilot screen review
(12 September) added to the handoff's `lines[]` output. That is consistent with the frozen
contract, not a departure from it: its line payload table already requires "Stable line sequence"
alongside the Commercial Offer line public ID. (An earlier draft of this document flagged it as an
open question; on re-reading the contract it is not one.)

## Test plan - each written to fail against code that lacks the rule

`backend/tests/test_slice_7c_work_order_line_detail.py`:

```text
Save and read
  first save creates version 1 and records WorkOrderLineDetailRecorded
  a changing save moves to version 2 and records WorkOrderLineDetailUpdated with changed_fields
  an identical save returns 200, no event, version unchanged
  stale expected_detail_version returns 409 and writes nothing
  expected_detail_version null when a detail already exists returns 409
  line-details lists every line in order, null detail where none recorded
  response entry and resolved objects have exactly the contract shape
  the returned detail is the version its event records
  a failure building the response leaves nothing written (response read before commit)
  a concurrent save cannot change the version another save reports (two paused sessions)

Validation
  another Account's site address / GSTIN / billing address -> 422 each
  address of the wrong type for site, and for billing address -> 422
  GSTIN in REJECTED_INCORRECT -> 422
  billing basis outside HOUR/SHIFT/DAY/MONTH -> 422
  contracted hours with HOUR -> 422; zero or negative hours -> 422
  line from a different Work Order -> 404
  unknown Work Order -> 404
  CLOSED Work Order -> 422

Completeness
  empty detail lists the four unconditional missing items (contracted hours only once a basis is chosen)
  SHIFT without hours lists CONTRACTED_HOURS; HOUR never does
  a GSTIN set to REJECTED_INCORRECT in the database after saving reappears as BILLING_GSTIN

Permissions
  SALES_USER, SALES_MANAGER, OPERATIONS_USER, ADMIN may save
  FINANCE_USER and MANAGEMENT_READ_ONLY get 403 on PUT and 200 on GET
  unauthenticated gets 401 on both

Boundary
  handoff response key sets for work_order and lines[] are exactly the pinned sets
  handoff inserts no crm_work_order_line_detail row
  event payload contains no GSTIN value and no address text

Database
  each CHECK constraint rejects a direct INSERT that bypasses the API
  UNIQUE(work_order_line_id) rejects a second detail row
```

Also: the existing route-permission guard recognises both new routes; a migration test covers
upgrade from empty, `downgrade -1`, and upgrade again; a smoke-data cleanup test removes a seeded
Work Order whose line has a detail row.

## Allowed files

```text
backend/alembic/versions/20260908_0036_work_order_line_operational_detail.py   new
backend/app/modules/work_orders/contract.py, schemas.py, repository.py,
    service.py, routes.py                                                       additive only
backend/app/modules/authorization/contract.py                                   one permission
backend/tests/fixtures/post_baseline_tightened_routes.py                        two new routes
backend/tests/test_slice_7c_work_order_line_detail.py                           new
backend/tooling/smoke_data/cleanup.py and its existing test file                 new table
frontend/src/pages/work-orders/WorkOrderDetailPage.tsx                          wiring only
frontend/src/pages/work-orders/WorkOrderLineDetailsSection.tsx                  new component
frontend/src/pages/work-orders/workOrderLineDetailState.ts and .test.ts          pure state rules and their tests (round 2)
docs/agent/contracts/work-order-contract.md                                     a 7C section
docs/agent/slices/slice-7c-work-order-line-operational-detail.md                this file
docs/agent/acceptance/slice-7c-work-order-line-operational-detail-acceptance.md new
docs/continuity/SLICE_7C_WORK_ORDER_LINE_OPERATIONAL_DETAIL.md                  new
docs/continuity/NEXT_STEPS.md                                                   a short Track 2 entry
docs/agent/DEFERRED_REQUIREMENTS.md                                             7C done items, lock rules, GSTIN dependency
docs/agent/FUTURE_SLICES.md                                                     7C status, new 7D entry
backend/tooling/smoke_data/builders.py                                          a line-detail builder
```

Shared files the CRM lane may also touch, and this package's handling: `authorization/contract.py`
and the route fixture (read by eye after any merge); `main.py` and `routes.tsx` are not touched.

Stop and report if: the migration parent is no longer `20260908_0035` at merge time; any handoff
key-set assertion would need changing; a CHECK or FK cannot be expressed without altering an
existing table; or the frozen contract hash differs.

## Verification gate before proposing the candidate

```text
1. Frozen contract hash equal to the baseline above.
2. Empty-database migration in a scratch database inside the running Postgres: upgrade to head,
   constraint assertions, downgrade -1, upgrade again. Not a second Compose stack - port 5432.
3. Backend image rebuilt (alembic/ is baked in), alembic current = 20260908_0036.
4. Full backend regression, run alone - never two suites at once on the shared database.
5. Frontend typecheck, test and build (MSYS_NO_PATHCONV=1 from Git Bash).
6. python scripts/check_tracked_secrets.py and python scripts/validate_contract_fixtures.py.
7. git diff --check.
8. Manual browser check as sales1 (save, conflict message) and finance1 (read-only).
9. Stored-document file count unchanged (this slice stores none; confirms no leaked run).
```

## Next package, flagged now so it is not discovered later

If decision 4's proposal is accepted, **7D - Work Order line billing terms** comes first, with its
own slice document, migration slot and Annexure-10 design work.

`WRR-001` Resource Requirement from an unreleased Work Order shell line then gets its own slice
document. Two things it will need from the owner:

- **Its own migration slot.** It adds tables. `20260908_0037` is the natural next number, but the
  owner allocates it.
- **Where resource categories come from.** `WRR-001` forbids a duplicate category catalogue and
  names the Equipment and Employee/Crew Masters as authoritative (`RMR-001`). Neither is
  integrated. The 7 September way-forward note sequences "catalogue/availability against fixtures"
  after WRR, so the likely answer is a versioned fixture reference standing in for Plum - but that
  is a genuine question for that document, not a default to assume here.

7C supplies what `WRR-001` needs from the line: Account and site public references, the source
offer line, and a detail version the requirement can record.

## Review record

External bounded independent review (read-only, no tools, one hashed packet),
under the three-round cap.

### Round 1 - CORRECTION_REQUIRED (packet sha256 e828b282...ffcb0b, candidate tree 5b28607)

Three material findings and one advisory. All four were checked against the code, held, and were
corrected in the same round:

1. **Save response read after commit.** `save_work_order_line_detail` committed, releasing the Work
   Order lock, and only then re-read the detail. A second save could land in between, so the first
   response could pair an event for version N with a detail at version N+1; and a failure in the
   post-commit read would report an error for a change already written, which a retry would then
   hit as a conflict. Now the response is read and built inside the transaction, under the lock,
   before commit (`_captured_line_detail_response`), and the no-op path captures it before rollback.
   Tests: `test_a_failure_building_the_response_leaves_nothing_written` (shown to fail against the
   pre-fix code) and `test_the_returned_detail_is_the_version_the_event_records`.
2. **Form ignored the save response.** The card started an unawaited reload and re-enabled Save at
   once, so a quick second save sent the old version and got a false 409, and input typed while the
   reload was pending could be overwritten. Now the PUT response's `line_detail` is applied to page
   state immediately, and the card's inputs are disabled while a save is in flight.
3. **Response shape mismatch.** This document promised `is_active` on the resolved address and GSTIN
   objects; the API did not return it, and no test pinned those shapes. The design makes the flag
   redundant - a resolved object exists only while its record is usable - so the document was
   corrected rather than the API, and
   `test_the_response_entry_and_resolved_objects_have_exactly_the_contract_shape` now pins the entry
   and all three objects.
4. **Advisory: empty-detail test name.** The test plan and test name claimed five missing items for
   an empty detail; four is right, because contracted hours are missing only once a Shift, Day or
   Month basis is chosen. Name and plan corrected. Nothing left to carry forward.

Residual uncertainty reported by the reviewer: the Account `GET` routes the form reads were not in
the packet. Round 2 carries them.

### Round 2 - CORRECTION_REQUIRED (packet sha256 4852f78c...32df4, candidate tree d4b6638)

One material finding and one advisory; both checked against the code, held, and were corrected in
the same round. The reviewer confirmed the backend otherwise preserves the frozen handoff, applies
the stated permissions and grants, and implements the migration, validation, transaction, no-op and
event-payload rules as described.

1. **Page state could still disagree with the server.** Line forms became editable before the
   line-details load finished, so a save in that window sent no version and got a false `409`; a
   first save's result was dropped because the page only replaced entries it already held; and a
   slow initial load could overwrite a newer save. Now a line's form is editable only once the page
   holds that line's entry (`canEditLine`), the save response is upserted (`upsertLineDetail`), and
   list loads and applied saves share a newest-wins gate (`createLatestGate`) so an older load never
   overwrites a later save. The rules live in `workOrderLineDetailState.ts` as pure functions with
   their own Vitest file, because the frontend still has no component-test capability; the wiring in
   the two components is covered by typecheck and reading only.
2. **Advisory: the version test did not exercise concurrency.** Added
   `test_a_concurrent_save_cannot_change_the_version_another_save_reports`: two sessions, the first
   paused at its response read while the second saves the same line. Run against the round-1
   (post-commit read) service it fails with `assert 2 == 1`, the exact defect; against the corrected
   code it passes. Nothing left to carry forward.

Residual uncertainty reported by the reviewer: no manual browser walk-through or Playwright run. That
stands, and is owed by the owner's manual check before merge (see the acceptance checklist).

### Round 3 - CORRECTION_REQUIRED (packet sha256 a8a110bf...43f690, candidate tree 8fe3cea)

One material finding, checked and held: the Lines table's "Site and billing" cell showed the site
city and the completeness badge but not the billing basis this document promised. Corrected: the
cell now also reads "Billed by shift" (or hour, day, month) through a shared `billingBasisLabel`.
Typecheck, frontend tests and build re-run after the fix. The reviewer found nothing else; its
residual uncertainty is again the absent manual browser check.

This was the third round, so the three-round cap was reached. The project owner authorised a fourth
round on 14 September 2026, and a backup of the round-3 candidate was pushed first as
`backup/hiring-slice-7c-r3-wip` (`3b69715`, not a reviewed commit).

### Round 4 - ACCEPTED (packet sha256 1ccccf6c...969f4a, candidate tree bb8850e)

Authorised by the project owner beyond the three-round cap. No blocking or material finding; the
reviewer confirmed the request shape, immediate application of the save response, conflict handling,
loading gate, billing-basis display and button-local feedback by inspection.

One advisory: the shared `cleanup_test_work_orders` helper in `test_commercial_offers_api.py` did not
delete line details before Work Order lines, so a future test using it alone after saving a detail
would fail in teardown. Not corrected in the reviewed commit (the commit had to reproduce the reviewed
tree); corrected in the follow-up below, with a test.

### Integration

- `884202c` committed with tree `bb8850ec`, identical to the round-4 reviewed tree.
- Hosted CI failed in *Compose build, health and E2E*: `amendment-read-only-role.spec.ts` clicks
  `getByRole("link", { name: "Open" })`, which Playwright matches by case-insensitive substring, and
  this section's "open the Account" link made it resolve to two elements. The E2E suite had not been
  run locally before the pull request; it should have been.
- `8e11263` renamed the link "go to the Account" (text only; spec unchanged). Full E2E locally 17
  passed, 9 skipped, 0 failed. **Not independently re-reviewed**: the project owner accepted this
  one-line change on their own authority rather than a fifth review round.
- Hosted CI then passed every job and `Required validation`; merged as `3fff30a` on the owner's
  instruction. The owner's screen check was done before the merge.

## Follow-up after merge (7C.1), 14 September 2026

A small package from the owner's screen check and the round-4 advisory. Frontend, one shared test
helper and records only; no migration, route, permission or contract change, so self-review plus CI
rather than an independent review, as agreed with the owner.

1. **Labels touched their inputs.** `field-stack` was on the fieldset instead of on each label, so
   each label sat inline against its control (and the Notes label fell to the textarea's baseline).
   It is now on each label, as the rest of the application uses it, with more space between fields.
2. **Line cards collapse and expand.** Each card is a disclosure whose summary shows the line, the
   site city and billing basis, and the completeness badge. A line with missing details starts open
   and a complete line starts closed; once the user opens or closes a card it stays as they left it,
   so saving a line to complete does not snap it shut. "Expand all lines" and "Collapse all lines"
   appear when there is more than one line. The rules are pure functions (`lineCardOpen`,
   `isUserToggle`) with Vitest tests, because the frontend still has no component-test capability.
3. **Round-4 advisory.** `cleanup_test_work_orders` now deletes line details first;
   `test_the_shared_work_order_cleanup_helper_removes_line_details_first` covers it.
