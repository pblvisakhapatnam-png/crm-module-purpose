# Slice 9D - Interaction Foundation

## Status

Implemented; correction pass 1 applied after independent review; awaiting re-review. Track 1 of
the post-E3 plan
(`docs/continuity/PF_1A_E3_INTEGRATION_CLOSURE_AND_WAY_FORWARD_2026-09-07.md`), first of the three
agreed CRM pilot minimums, ahead of 9C (document storage) and 9E (quotation generation).

## Objective

One shared, channel-agnostic conversation log - calls, emails, WhatsApp messages, meetings and
site visits - attached polymorphically to Lead, Account, Opportunity, Commercial Offer and Work
Order.

## Why this is next

- FRD line 177: activity logging for every Lead **and Opportunity**, covering calls, visits (with
  geo-coordinates) and WhatsApp/email. Today only Lead has anything.
- FRD line 855: communications in a time-stamped log **before a quote can be raised**, so 9D gates
  9E.
- FRD line 173: the **original communication** captured and stored.
- It is what a salesperson must be able to do on day one of the shadow-mode pilot without leaving
  the system.

## Owner decisions

| # | Decision |
| --- | --- |
| 1 | Order: 9D, then 9C, then 9E. |
| 2 | Lead history on conversion: recorded once against the Lead; **shown** on the Lead, Account and Opportunity as inherited history. Not copied. |
| 3 | Message content: **store the full text**. The original communication is the evidence. |
| 4 | Read permission: **split** into metadata and content, granted generously at first. The expensive half of the cost is deferred - see "Handling customer message content". |
| 5 | Module: new `interactions/`; delete the dead `activities/` stub; record the `crm_lead_activity` question (see the reconciliation note below). |
| 6 | Migration head: 9D takes `20260908_0033`. Hiring's `7C` builds on it at `0034`. One linear chain retained. |
| 7 | Package shape: issue whole. The Commercial Offer readiness row is **dropped from 9D** and moves to the next round. Correction-cycle cap stays at three. |
| 8 | Retention: store indefinitely for the pilot, no purge job, period set before production use, following the ADR-015 deferred-parameter pattern. |

Standing instruction applied throughout: time is of the essence. A working but imperfect system
beats a slow perfect one. Defer plumbing and hardening; keep only the shape that prevents
expensive rework later.

## Scope trims taken for speed

Each keeps the shape that would be costly to add afterwards.

| Trimmed | Kept | Why the deferral is safe |
| --- | --- | --- |
| Separate participant routes | The `interaction_participant` **table**, written and read as part of the interaction | The table exists from day one, so no later migration against a populated table of customer messages. Only the extra routes, permissions and tests are deferred. |
| Screens on Commercial Offer and Work Order | Backend support for all five record types | The API serves all five immediately. Mounting two more screens later is frontend-only, with no migration and no contract change. |
| Commercial Offer readiness row | Nothing needed now | It is the only place 9D would touch working code. |

Net effect: **9D changes no existing module's behaviour.** That property is what makes one package
with a three-round correction cap realistic.

## Interactions and Lead Activities are two different records, deliberately

`crm_lead_activity` (Slice 2D) records follow-ups against a Lead only. `interaction` (Slice 9D)
records a communication against any of five record types, in either direction, with the original
message content, participants and provider identifiers.

Slice 9D does **not** replace, migrate or deprecate `crm_lead_activity`. Lead activities keep
working exactly as before, through their existing routes, permissions and events. Nothing is copied
between the two tables.

Whether Lead activities should eventually fold into `interaction` is a **real open question with a
data migration behind it, and it has not been decided.** It is recorded here so it is decided
deliberately rather than assumed. Anyone proposing the consolidation must treat it as its own
package: the two tables carry different columns, different permissions and different events, and
the Lead contract documents existing behaviour that users depend on.

The new module is named `interactions` rather than `activities` specifically so the two names stay
distinct while both exist. The pre-existing `backend/app/modules/activities/` stub - seven
byte-order-mark-only empty files with no router, model or behaviour - is deleted by this slice.

## Data model

### `interaction`

```text
id                       integer identity PK
interaction_public_id    varchar(36)  NOT NULL, unique          ADR-007 public UUID
linked_record_type       varchar(100) NOT NULL                  lead | business_party | opportunity
                                                                | commercial_offer | work_order
linked_record_public_id  varchar(36)  NOT NULL
channel_code             varchar(50)  NOT NULL                  CALL | EMAIL | WHATSAPP | MEETING
                                                                | SITE_VISIT | SMS | PORTAL
                                                                | LETTER | NOTE | OTHER
direction_code           varchar(20)  NOT NULL                  INBOUND | OUTBOUND | INTERNAL
occurred_at              timestamptz  NOT NULL                  when it happened, not when recorded
subject                  varchar(500) NULL
body_text                text         NULL                      RESTRICTED - stored original content
body_stored              boolean      NOT NULL default false     content held, or reference only
external_system          varchar(50)  NULL                      OUTLOOK | WHATSAPP | FREJUN
                                                                | RUNO | MANUAL
external_message_id      varchar(255) NULL                      provider's own message id
idempotency_key          varchar(255) NULL
request_fingerprint      varchar(64)  NULL                      SHA-256 of the normalized create
                                                                command; a retry must match it
                                                                before it may replay this row
external_reference_url   varchar(1000) NULL                     link back to the original
geo_latitude             numeric(9,6) NULL                      FRD line 177: visits carry these
geo_longitude            numeric(9,6) NULL
outcome                  varchar(255) NULL
next_follow_up_at        timestamptz  NULL
recorded_by              varchar(36)  NULL                      app_user.public_id
created_at               timestamptz  NOT NULL default now()
updated_at               timestamptz  NOT NULL default now()
is_deleted               boolean      NOT NULL default false     CODING_STANDARDS soft-delete rule
```

`occurred_at` and `created_at` are separate on purpose: a call logged the next morning happened
yesterday, and the FRD's "time-stamped log" means the communication's time, not the typing time.

`body_stored` is an explicit flag, not inferred from `body_text IS NULL`. A message whose content
was deliberately not kept and one that was genuinely empty must stay distinguishable, or a future
retention purge becomes indistinguishable from a blank note.

### `interaction_participant`

```text
id                       integer identity PK
participant_public_id    varchar(36)  NOT NULL, unique
interaction_id           integer      NOT NULL  FK -> interaction.id
party_role_code          varchar(20)  NOT NULL   FROM | TO | CC | BCC | ATTENDEE
contact_public_id        varchar(36)  NULL       -> business_party_contact.contact_public_id
app_user_public_id       varchar(36)  NULL       internal participant
display_name             varchar(255) NULL       the name as it appeared
address_or_number        varchar(255) NULL       RESTRICTED - email/phone as it appeared
created_at               timestamptz  NOT NULL default now()
```

A child table rather than a JSON column, because "every conversation involving this contact" is a
query the pilot will want, and because storing the raw address alongside the resolved contact link
preserves evidence when matching is wrong or absent - the same principle ADR-015 applies to
SurePass mismatches.

`contact_public_id` and `app_user_public_id` are deliberately **not** foreign keys. A participant
may be an external person who is not in `business_party_contact` at all, and a resolved link must
survive the contact being deactivated. The raw `display_name` and `address_or_number` remain the
evidence of record.

### Attachments - no new table

An interaction is a valid `linked_record_type` for the existing `document_metadata` table
(`linked_record_type = 'interaction'`). This reuses the polymorphic pattern exactly and needs no
join table. Until 9C lands, attachments remain metadata plus external link, which is what
`document_metadata` already does.

### Indexes

```text
ux_interaction_public_id                 unique (interaction_public_id)
ix_interaction_linked_record             (linked_record_type, linked_record_public_id)
ix_interaction_occurred_at               (occurred_at)
ix_interaction_next_follow_up            (next_follow_up_at) WHERE next_follow_up_at IS NOT NULL
ux_interaction_external_message          unique (external_system, external_message_id)
                                         WHERE external_system IS NOT NULL
                                           AND external_message_id IS NOT NULL
ux_interaction_idempotency_key           unique (idempotency_key) WHERE idempotency_key IS NOT NULL
ux_interaction_participant_public_id     unique (participant_public_id)
ix_interaction_participant_interaction   (interaction_id)
ix_interaction_participant_contact       (contact_public_id) WHERE contact_public_id IS NOT NULL
```

The two partial unique indexes are the deliberate build-ahead. Re-syncing a mailbox must not create
a second row for the same message, and that has to be a database constraint rather than a
service-layer check, because an ingestion job will eventually run concurrently with itself.

## Inherited history - a derived read, never a copy

Decision 2 is implemented as a read. Nothing happens on conversion and no row is ever duplicated.

```text
GET /api/interactions?linked_record_type=opportunity
                     &linked_record_public_id=<id>
                     &include_inherited=true
```

- **Opportunity** inherits from its originating Lead via `crm_opportunity.source_lead_id`.
- **Account** inherits from the Lead(s) that converted into it, resolved through the Opportunities
  sharing the Account's `business_party_id` that carry a non-null `source_lead_id`.
- Inherited rows carry `inherited_from` so the screen shows provenance and never implies the
  message was addressed to the Opportunity.
- `include_inherited=false` returns only rows recorded directly against that record.

`POST /api/leads/{id}/convert` gains no new behaviour, no new event and no interaction writes. The
alternative - copying history forward on conversion - would have meant changing a working
conversion flow and double-counting every message.

## API surface

```text
GET    /api/interactions                     list, filtered
POST   /api/interactions                     record one, with its participants
GET    /api/interactions/{public_id}         detail
PUT    /api/interactions/{public_id}         correct the mutable fields only
DELETE /api/interactions/{public_id}         soft delete
```

Filters: `linked_record_type`, `linked_record_public_id`, `include_inherited`, `channel_code`,
`direction_code`, `occurred_from`, `occurred_to`, `limit`, `offset`. Default order
`occurred_at DESC, id DESC`, matching the existing list convention.

Every route carries an explicit `require_permission(...)` dependency. The PF-1A-E1 guard accepts
genuinely new routes provided they are not ungated.

### Immutability

`body_text`, `subject`, `channel_code`, `direction_code`, `occurred_at`, `external_message_id` and
the participant set are **immutable once recorded**. `PUT` may change only `outcome` and
`next_follow_up_at`. A mistake is corrected by soft-deleting and re-recording, leaving both rows
and both events.

The reason is the FRD's own: the original communication is evidence. An editable body is not
evidence of what the customer said - it is evidence of what someone last typed.

## Permissions

```text
INTERACTION_READ           who, when, which channel, subject, outcome
                           ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER,
                           OPERATIONS_USER, MANAGEMENT_READ_ONLY

INTERACTION_CONTENT_READ   the stored message body and participant addresses
                           ADMIN, SALES_USER, SALES_MANAGER, OPERATIONS_USER,
                           MANAGEMENT_READ_ONLY
                           (deliberately excludes FINANCE_USER - see below)

INTERACTION_CREATE         ADMIN, SALES_USER, SALES_MANAGER
INTERACTION_UPDATE         ADMIN, SALES_USER, SALES_MANAGER
INTERACTION_DELETE         ADMIN, SALES_MANAGER
```

Finance sees that a conversation happened, its channel, subject and outcome, but not the
customer's message body or the participants' addresses. This is a deliberate asymmetry, not the
"everyone who can see a conversation can read it" simplification an earlier draft of this
document used - that wording was corrected during implementation because it directly
contradicted the exclusion above. Customer message bodies and participant addresses are
Restricted personal/statutory data under `DATA_CLASSIFICATION_AND_HANDLING.md` and are
need-to-know; Finance's work here - receivables, activation, invoicing - is served by the
metadata, not the content. If Finance is later found to need message bodies, widen the grant
explicitly rather than defaulting to broad access.

For every other role, the split exists for a reason unrelated to restricting anyone today: *who
may read customer correspondence* becomes a grant that can change without a code change, on the
day a contractor, an auditor or a customer-facing login appears. Loosening later is a quiet
grant; tightening later means removing access people have had for months.

### What the split costs, and what is deferred

Built now: both permission codes, both grant sets, and redaction through **one serializer function
shared by the list and detail routes**, with a single check that blanks `body_text` and participant
addresses and sets `body_redacted: true` when the caller lacks `INTERACTION_CONTENT_READ`. One code
path, so hiding content on the detail screen while forgetting the list cannot happen structurally.

A caller without the content permission receives the interaction with the body blanked, not a 403.
The existence of the conversation is not the sensitive part.

Deferred: **no access audit** of who read a message body (deferred to the retention package, and
recorded as a known gap rather than silently omitted); **no grant-management screen** (permissions
are seeded and changed by migration, as every other permission in this system is); **no per-record
access rules**.

## Authorization foundation correction (discovered during implementation)

Adding a single permission exposed a real problem in `PF-1A-E1`'s permission contract, corrected
before this slice's own permissions could be added. This correction is not scope growth invented
by 9D; it is a one-time foundation fix that every later package adding a permission (9C, 9E, `7C`
and beyond) would otherwise have hit in turn.

**The problem.** `require_permission(...)` rejects any code absent from `ALL_PERMISSION_CODES`,
which derived from `ROLE_PERMISSION_COMPATIBILITY_MATRIX`. That matrix is PF-1A-E1's frozen
evidence that migrating every route guard to `require_permission` preserved the exact
pre-existing access matrix, verified against an independently-derived fixture
(`tests/fixtures/pf_1a_e1_baseline_authorization.py`). Adding a post-E1 permission to it would
make that comparison vacuous from then on - the proof would be checking a moved goalpost against
itself - and six count/equality assertions across five test files were pinned to the exact
pre-9D totals (31 permissions, 110 grants), so a naive addition would also have broken all six.

**The fix.** `app/modules/authorization/contract.py` now holds a disjoint union:

```text
ROLE_PERMISSION_COMPATIBILITY_MATRIX   frozen, unchanged by this slice: 31 permissions / 110 grants
POST_BASELINE_ROLE_PERMISSION_MATRIX   live; this slice's 5 permissions / 19 grants live here
EFFECTIVE_ROLE_PERMISSION_MATRIX       the disjoint union; what require_permission(...) enforces
```

`ALL_PERMISSION_CODES` now derives from the effective matrix. An import-time guard,
`assert_permission_matrices_are_disjoint(...)`, refuses any code present in both halves - it is a
named function specifically so a test can drive it with synthetic overlapping input, per the
Slice 9B lesson that a guard never shown to fail is an assertion of intent, not a control. No
effective total (36 permissions, 129 grants) is hardcoded anywhere; it is asserted as the
calculated union, so a future package adding a permission does not have to hand-edit a count.

Five test files were corrected to distinguish "the frozen baseline is unchanged" from "the live
system enforces more than it used to" - both real, different claims that had been conflated:
`test_authorization_baseline_equivalence.py` (both PROOF A and PROOF B needed **no changes** -
the strongest evidence the split is right; only the inverse/no-extra-grant test was narrowed, and
it classifies rather than skips: a grant matching neither matrix is still an offender),
`test_authorization_compatibility_matrix.py` (was iterating `ALL_PERMISSION_CODES` while indexing
the frozen matrix - a real bug 9D's own permissions would have surfaced at runtime even without
review), and three `business_authority` boundary tests reworded from "the system has exactly 31
permissions" to "the frozen baseline is exactly 31 permissions", which is what "unchanged by this
package" actually means once permissions can legitimately grow.

See `backend/tests/test_slice_9d_interaction_foundation.py` for the tests covering this split
directly, including the disjointness guard driven with synthetic bad input, and the commit
`5a4b9b1` message for the full defect-by-defect account.

**Why this belongs to 9D and not a separate package:** it was undiscoverable without a real
permission addition to trigger it, it blocks every later package that adds one, and deferring it
would have meant 9D shipping without any permissions at all. It does not change PF-1A-E1's
`ACCEPTED` status or reopen its own review; the baseline it froze is untouched.

## Handling customer message content

Storing message bodies puts this table in **Restricted personal/statutory**
(`docs/agent/architecture/DATA_CLASSIFICATION_AND_HANDLING.md`).

1. **Business events carry metadata only.** `InteractionRecorded` / `InteractionUpdated` /
   `InteractionDeleted` payloads contain the public ID, linked record, channel, direction and
   `occurred_at`. **Never `body_text`, never `subject`, never a participant address.** This is the
   first table in the programme that will actively tempt someone to include them, which is why it
   gets a guard and the guard gets its own tests.
2. **Fixtures are fictional.**
3. **Logs carry identifiers, not payloads.**
4. **Retention is a named open parameter, deliberately unset.** Store indefinitely, no purge job,
   no invented default - the ADR-015 precedent. `body_stored = false` with `body_text = NULL` is
   already the shape a future purge writes, so no schema change is needed when the period is set.

Any future Outlook / WhatsApp / IVR ingestion contract must name field classification, transport and
storage protection, and a retention owner before implementation.

## Manual entry and future ingestion share one path

Per ADR-030, an integration consumes a governed service; it never reimplements one. Manual entry
and a future connector write through the same service function and the same validation. The
connector supplies `external_system`, `external_message_id` and `idempotency_key`; manual entry
leaves them null and sets `external_system = 'MANUAL'`. No ingestion-only write path, no direct
repository access from a job, no second table.

This is why the idempotency columns exist now despite nothing populating them yet: adding them
later would mean a migration against a populated table of customer messages plus a backfill.

## Concurrency

Slice 9B left two locking patterns behind. 9D inherits neither, deliberately.

| Pattern | Established for |
| --- | --- |
| Lock the row before reading its status | `offer_status_code`; plus the parent Opportunity row on Base Offer creation |
| Lock the aggregate root | `amendment_status_code`, five mutators, plus the Work Order lock on intake |

**9D does not trip 9B's guards.** Both are scoped to specific modules and patterns - the
offer-update repository call, and amendment resolution by public id - and their own docstrings
record that they cannot see writes in another module. `interaction` touches neither
`offer_status_code` nor amendments, so the new module is correctly invisible to them. No known-set
needs updating.

**Within 9D no lock is needed.** Interactions are append-mostly, carry no cross-record status rule,
and an interaction plus its participants are written in one transaction. Idempotency is enforced by
the database's partial unique indexes, not by a lock - deliberately, because an ingestion job will
eventually run concurrently with itself and a service-layer check would not survive that.

Two futures would change this, both out of scope: an interaction *gating* a status change (a
read-then-write on `offer_status_code`, which must take `lock_commercial_offer_row` first and join
the known-writer set), and participants becoming separately mutable (which makes `interaction` a
header with independently editable children - follow the amendment aggregate-root pattern, do not
invent a third).

## Frontend

- A shared `InteractionLog` component (list, filter, record form), mounted on the **Lead, Account
  and Opportunity** detail pages. Commercial Offer and Work Order mounting is next round.
- Inherited rows visually distinguished and labelled with their origin.
- Bodies shown to holders of `INTERACTION_CONTENT_READ`; others see the metadata row and an
  explicit "message content not shown for your role" state, not a blank.
- Action feedback beside the triggering button, per the standing UI rule.
- No new public URLs, so `frontend/src/routes.tsx` and its tests are untouched.
- `CommercialOfferDetailPage.tsx` is deliberately not touched; its decomposition is on the deferred
  register and this slice adds nothing to it.

## Out of scope

```text
Commercial Offer readiness row                                    - next round (decision 7)
Commercial Offer and Work Order screens                           - next round
Separate participant routes                                       - next round if wanted
Ingestion connectors (Outlook, WhatsApp, Frejun/Runo IVR)          - later integration package
File upload and stored attachments                                - 9C
Quotation generation and controlled release                       - 9E
Hard enforcement of the FRD logging rule                          - after the pilot habit forms
Retention purge job and content-read access audit                 - with the retention decision
Consolidating crm_lead_activity into interaction                  - open, see the note above
Notifications, reminders, task assignment                         - parked
Approval workflow                                                 - APR-001, parked
Any change to Lead conversion behaviour
Any change to the frozen Slice 6D.1 handoff contract
```

## Correction pass 1, 8 September 2026

The first independent review returned `CORRECTION_REQUIRED`: the authorization split, regression
suite, migration and browser paths were all verified sound, but the validation gate was red and
several contract/data-integrity issues needed fixing before later slices build on this API.

**Gate.** `check_tracked_secrets.py` and `scripts/tests` both failed on two SEC-004 findings in
`test_interactions_api.py`: variables named `secret_body` and `secret_subject`. They were test
markers, never credentials - but the honest fix is the one the scanner asks for, not an
exclusion. Renamed to `marker_*` with `PROBE-` literals, so the file carries no
credential-shaped token at all. Both checks now pass.

**Four data-integrity/security corrections, each with a regression test proven to fail without
the fix:**

- **Partial update destroyed data.** `PUT {"outcome": "..."}` nulled `next_follow_up_at`, because
  both columns were written unconditionally from a schema whose fields both default to `None`. A
  scheduled follow-up the caller never mentioned simply vanished. Now only supplied fields are
  written (`exclude_unset`), keeping "omitted" and "explicitly null" distinguishable, with the
  updatable column set closed and validated in the repository.
- **Redaction was defeated by a pointer.** A caller denied `body_text` still received
  `external_reference_url` - a deep link straight to the message - and `external_message_id`, the
  provider key that retrieves it. Both now redact with the body. `external_system` stays visible:
  it names the channel, it does not address the content.
- **Coordinates were unvalidated.** A lone latitude was accepted as a location, and out-of-range
  values reached a `numeric(9,6)` column. Now paired-or-absent, and range-checked.
- **Participant references were unvalidated.** `contact_public_id` / `app_user_public_id` were
  accepted without checking they resolve, and a participant naming nobody at all was accepted.
  These are deliberately not foreign keys - an external participant may exist in no table, and a
  resolved link must survive deactivation - but "not a foreign key" is not "unvalidated".

**MCF-001 reconciliation.** Four of the five gaps are now implemented rather than excepted:
explicit `contract_version` on every mutating response and `schema_version` in every event
payload; `X-Correlation-Id` honoured when supplied and generated when not, persisted onto the
business event; and **idempotent replay** - a retry carrying the same `idempotency_key` or the
same `(external_system, external_message_id)` now replays the original record with
`replayed: true` and emits no second event, instead of returning `409`. The old behaviour was
exactly what the review warned 9E must not build on: an ingestion job whose call timed out after
the row committed would have had to reconcile a false failure by hand.

The fifth, the structured error envelope, is a **recorded, owned, time-bounded exception** rather
than a fix, because all nine existing route modules return `{"detail": ...}` and adopting the
envelope in Interactions alone would put two error shapes in one API surface. It is owned by and
retires with the PF-1B retrofit ADR-025 already assigns. Full record in
`docs/agent/contracts/interaction-contract.md`.

**Contract and boundary records.** ADR-005 requires a contract before module implementation, and
9D had none. Added `docs/agent/contracts/interaction-contract.md` (`INT-001`, version `1.0`),
registered in `CONTRACT_REGISTRY.md`, with an ownership/boundary row in
`MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`.

**Acceptance-script correction.** The manual script told the tester to tick the inherited-history
checkbox. It is ticked by default wherever a record can inherit, so the script did not match the
delivered UI. Corrected, and the untick/re-tick step now carries its purpose: proving the row was
never copied.

Eleven further items were accepted as parkable and recorded rather than fixed - the 500-row
inherited-history ceiling, frontend pagination and filters, audit semantics, timestamp policy,
the alias bypass in the event-payload guard, and the retention/read-audit decisions. They are in
`docs/agent/DEFERRED_REQUIREMENTS.md` under "Interactions (Slice 9D)", with the UI ones also in
`UI_UX_CARRY_FORWARD.md`.

## Correction pass 2, 8 September 2026

Round 2 returned `CORRECTION_REQUIRED` with a recommendation to split the package. This section
records the corrections; the split is tracked separately.

**P1 - immutable fields were silently accepted, and emitted a false audit record.**
`InteractionUpdate` used Pydantic's default `extra="ignore"`. A `PUT` carrying `body_text`
returned `200`, silently discarded the attempted replacement, applied any other supplied field,
and **still emitted an `InteractionUpdated` event** - recording a change that never happened.

This contradicted the contract, which claimed immutability was structural "because the request
schema declares no field for anything else". That reasoning was wrong: **declaring no field is
not the same as refusing one.** `extra="forbid"` is what makes the claim true.

The regression test was written first and confirmed to fail against the defective code before
the fix was applied. It covers every immutable field individually, an entirely unknown field, a
mixed request (allowed + immutable, refused whole so neither applies), that the stored row is
byte-for-byte unchanged afterwards, that no `InteractionUpdated` event was emitted by any refused
request, and that a legitimate update still succeeds and does emit exactly one.

**Extended beyond the required correction, deliberately:** `InteractionCreate` and
`InteractionParticipantCreate` carried the identical `extra="ignore"` defect. On create it is
arguably worse - a caller sending `body` instead of `body_text` would have the content silently
dropped while `body_stored` truthfully reported `false` and nobody noticed. Both now forbid
extras. The frontend sends only declared fields, so nothing breaks. This is scope growth of about
four lines to close the same defect class the reviewer flagged; leaving the sibling schemas
holed would have invited the finding again next round.

**Two documentation corrections** followed from the same root cause: INT-001's structural-
immutability claim is rewritten to say what is actually true and why the earlier claim was
wrong, and a test named `test_the_update_schema_has_no_fields_for_immutable_data` - which
asserted only the field list and was therefore evidence of nothing on its own - is renamed and
strengthened to pin `extra="forbid"` on all three request schemas.

**P1 - idempotent replay did not verify command compatibility.** The service returned whichever
row owned the supplied key without comparing the retry against the original command, so reusing
a key with a different subject returned the *original* record reported as the caller's own
successful create. Correction pass 1 made replay possible; it did not make it safe.

The migration now stores `request_fingerprint`, a SHA-256 over the normalized create command
(field list in `INTERACTION_FINGERPRINT_FIELDS`, participants sorted, timestamps normalized to
UTC). A retry replays only on a fingerprint match. A different payload, a different linked
record, or an absent stored fingerprint each yield `409` rather than a wrong record. The
soft-delete case, previously undefined, is now explicit: a retry whose original was deleted is
refused, does not resurrect the conversation, and does not return the deleted content - the test
asserts the removed body does not appear anywhere in the refusal. Scope is documented in INT-001
under "Idempotency key scope".

**P1 - coordinate integrity was enforced only by the API.** A direct insert with latitude 999
succeeded during review. Pydantic protects the HTTP path and nothing else - not a direct insert,
a future ingestion job writing through another path, or a repair script. The migration now
carries three CHECK constraints (paired, latitude -90..90, longitude -180..180), amended into
`20260908_0033` in place because it is unreleased, following the TE-2B-C1 precedent. The test
proves them by direct SQL insert rather than through the API that already validates, and
confirms a legitimate pair is still accepted.

**P1 - dual participant identity, decided.** A participant may no longer carry both
`contact_public_id` and `app_user_public_id`. They address different populations: a person at
the customer's Account, and a PBL staff login. A participant is the external party or the
internal one; two people are two rows, which is what the child table is for. Recorded in
INT-001 with a positive test proving the two-row case still works.

**P2 - deferred items were inaccurately described.** The preamble claimed none was a defect in
delivered behaviour. That was wrong: the list includes accepted defects (a no-op update emitting
an event; an empty interaction labelled "content redacted"), a delivered limitation (the
silently truncating pagination cap) and a compatibility nonconformance (the MCF error envelope).
Every item is now labelled with what it actually is. The count was also wrong: **nine** items are
in `DEFERRED_REQUIREMENTS.md` and **two further distinct** UI items in `UI_UX_CARRY_FORWARD.md`,
eleven in total - the continuity note had claimed all eleven were in the first document.

## Correction pass 3, 8 September 2026

Round 3 confirmed the four round-2 findings closed, but found the *new* fingerprint materially
defective, and directed that the package be split rather than take a fourth combined round.

**P1 - the fingerprint encoding permitted collisions.** Pass 2 joined `name=value` pairs with
U+001F. That is not an injective encoding: a value containing the delimiter forges a field
boundary. The review supplied a concrete pair, reproduced exactly here before fixing -

```text
subject="u"                  body_text="v<US>body_text="
subject="u<US>body_text=v"   body_text=""
```

both render as `subject=u<US>body_text=v<US>body_text=`. So a retry could still replay an
*incompatible* command despite pass 2 adding the comparison. The comparison was real; the thing
being compared was ambiguous.

`external_message_id` was also wrongly excluded, on the reasoning that it was "part of the key".
It is immutable provider identity: excluding it let a retry reusing one idempotency key change
which provider message the record claimed to be, and still match.

The fingerprint is now canonical JSON (sorted keys, compact separators) over a typed, normalized
structure. JSON escapes control characters and quotes structurally, so ambiguity is impossible by
construction rather than by assuming no value contains the separator. `external_message_id` is
included; `idempotency_key` is the only exclusion. Normalization is explicit and tested: UTC
datetimes, decimal trailing zeros stripped, the *effective* `external_system` (omitted and
explicit `MANUAL` are one command), and participants canonicalized then sorted.

Proved directly rather than assumed: the old implementation was reconstructed verbatim alongside
the new one and shown to collide on the review's pair while the new one does not. Eleven
regression tests cover the collision family, provider-identity change, key exclusion, equivalent
offsets, trailing zeros, participant reordering, default normalization, and a guard asserting
every declared fingerprint field actually changes the result - so a field added to the command
but forgotten in the fingerprint fails the suite.

INT-001's fingerprint section is rewritten to match the implementation exactly, including why
canonical JSON rather than a delimited string.

**Split.** The reviewer directed splitting into an authorization prerequisite and 9D proper,
keeping revision `0033` (Package A carries no migration, nothing else is in flight, and `0033`
has never been integrated, so renumbering would add risk without improving lineage). See
`docs/continuity/SLICE_9D_INTERACTION_FOUNDATION.md` for the resulting package boundary.

## Migration

```text
revision       20260908_0033
down_revision  20260906_0032
```

Creates `interaction` and `interaction_participant`, their indexes, and seeds the new permissions
and grants. PostgreSQL only, no dialect branching, transactional DDL so no `IF NOT EXISTS` guards.

After merging, rebuild the backend image - `alembic/` is baked in, not bind-mounted:

```powershell
docker compose up -d --build --force-recreate backend
```

Hiring's `7C` takes `20260908_0034` with `down_revision = "20260908_0033"`.
