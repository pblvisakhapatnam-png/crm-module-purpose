# Interaction Contract - Slice 9D Foundation

## Contract ID and status

`INT-001` - `APPROVED` - 8 September 2026. Contract version `2.0` since 11 October 2026 (`1.0` until then; see
"Times carry their zone").

Owner: Interactions module (`backend/app/modules/interactions/`).
Consumers: CRM (Lead, Account, Opportunity, Commercial Offer, Work Order surfaces), and any
future communication-ingestion adapter.

## Purpose

Define the shared, channel-agnostic conversation log: what was said to and by the customer,
recorded once and attached polymorphically to any of five business records. It is the record the
FRD requires (line 177 activity logging on Lead **and** Opportunity, line 855 communications
logged before a quote is raised, line 173 the original communication captured and stored).

## Relationship to Lead Activities - two different records, deliberately

`crm_lead_activity` (Slice 2D) records follow-ups against a Lead only. `interaction` records a
communication against any of five record types, in either direction, with the original message
content, participants and provider identifiers.

**Slice 9D does not replace, migrate or deprecate `crm_lead_activity`.** Nothing is copied
between the two tables. Whether Lead activities should eventually fold into `interaction` is an
open question with a data migration behind it and has not been decided; it must be its own
package, not a side effect of a later slice.

## Data model

```text
interaction
interaction_participant
```

Attachments reuse `document_metadata` with `linked_record_type = 'interaction'`. No join table.

Full column definitions are in `docs/agent/slices/slice-9d-interaction-foundation.md`; this
contract states the boundary, not the DDL.

### Participant identity - single, decided 8 September 2026

A participant must name at least one of `contact_public_id`, `app_user_public_id`,
`display_name` or `address_or_number`, and **may not carry both `contact_public_id` and
`app_user_public_id`.**

The two address different populations: `business_party_contact` is a person at the customer's
Account, `app_user` is a PBL staff login. A participant is the external party to the
conversation or the internal one, never simultaneously both. Two people on one conversation are
two participant rows - that is what the child table is for. A row needing both would be an
identity-resolution ambiguity to decide deliberately, not a dual identity to store silently.

Both identifiers are validated to resolve when supplied. They remain deliberately **not** foreign
keys: a participant may be an external person present in no table, and a resolved link must
survive the referenced contact being deactivated.

### Coordinate integrity

`geo_latitude` and `geo_longitude` are constrained **at the database**, not only by the API
schema: both-or-neither, latitude within -90 to 90, longitude within -180 to 180. API validation
protects the HTTP path and nothing else - a direct insert, a future ingestion job writing through
another path, or a data-repair script would otherwise bypass it. A direct insert with latitude
999 was accepted before these constraints existed.

## Polymorphic link

```text
linked_record_type    lead | business_party | opportunity | commercial_offer | work_order
linked_record_public_id
```

Deliberately not a foreign key - one column addresses five owning modules' tables. The owning
module of each target is unchanged and unaware; Interactions never writes to those tables. The
link target's existence **is** validated on create through a minimal read-only lookup against the
target's own public-id column, so a link can never dangle. That lookup is the smallest possible
cross-module read, permitted under `PRODUCTION_ARCHITECTURE_DIRECTION.md`'s allowance for an
explicitly approved immutable identifier/reference.

## Ownership boundary

- Interactions owns `interaction` and `interaction_participant` exclusively. No other module
  writes them.
- Interactions writes to no other module's tables, and reads other modules only to (a) prove a
  link target exists and (b) resolve Lead-to-Opportunity/Account conversion lineage for the
  inherited read below.
- `document_metadata` remains owned by the Documents capability. Interactions supplies only a
  `linked_record_type` value.

## Inherited history - a derived read, never a copy

An Opportunity inherits its originating Lead's interactions; an Account inherits from the Lead(s)
that converted into it. This is resolved at read time from existing conversion links
(`crm_opportunity.source_lead_id`). **No row is copied and nothing is written on conversion.**
Inherited rows carry `inherited_from` so provenance is explicit and never implies the message was
addressed to the inheriting record.

Lead conversion behaviour is unchanged by this contract.

## API

```text
POST   /api/interactions
GET    /api/interactions
GET    /api/interactions/{public_id}
PUT    /api/interactions/{public_id}
DELETE /api/interactions/{public_id}
```

Every route requires an explicit permission; see below. `GET` routes emit no business event.

### Immutability

`body_text`, `subject`, `channel_code`, `direction_code`, `occurred_at`, `external_message_id`
and the participant set are immutable once recorded. `PUT` accepts only `outcome` and
`next_follow_up_at`; **any other field, recognised-but-immutable or entirely unknown, is refused
with `422`.** The request is refused whole - a mixed request naming both an allowed and an
immutable field applies neither. A mistake is corrected by soft-deleting and re-recording,
leaving both rows and both events.

Correction, 8 September 2026: an earlier version of this contract claimed immutability was
structural because the request schema declared no field for the immutable columns. That was
wrong. Pydantic's default `extra="ignore"` meant a `PUT` carrying `body_text` returned `200`,
silently discarded the attempted replacement, applied any other supplied field, and still
emitted an `InteractionUpdated` event - a false audit record of a change that never happened.
Declaring no field is not the same as refusing one. `extra="forbid"` on the request schemas is
what makes the claim true, and `InteractionCreate` and `InteractionParticipantCreate` carry it
too, for the same reason.

A `PUT` writes only the fields the caller actually supplied. Omitting a field leaves it
untouched; sending it explicitly as `null` clears it. These are different requests and must
remain distinguishable.

### Times carry their zone (11 October 2026)

`occurred_at` and `next_follow_up_at` on `POST`, `next_follow_up_at` on `PUT`, and the `GET`
filters `occurred_from` and `occurred_to` take a date and time only with its zone (`Z` or an
offset such as `+05:30`), as ISO text; a number or digits, which would otherwise be read as
seconds since 1970, are refused too. One with no zone is refused with `422` ("Give the date and
time with its time zone, ..."); until this date it was accepted and read as UTC. Any offset is
converted to UTC, as the command fingerprint already did.

**This is an intentional, breaking tightening of the request contract**, so
`INTERACTION_CONTRACT_VERSION` is `2.0` (the rule in `contract.py`: the major part for a breaking
change). A caller that sent a time with no zone is now refused and must send its zone. What
changes in responses is that version alone: the `contract_version` of the create, update and
delete responses reads `2.0`. Every field keeps its name and type, the times in responses keep
their form, events and their `schema_version` are unchanged, and the stored command fingerprint
of an earlier request is unchanged (a time with no zone was fingerprinted as UTC). The
application's own page always sent a zone; it now reads the time typed as India's time
whatever the browser's own zone (before, it used the browser's zone). The rule is the platform's,
not this module's: ADR-028 "Timestamps" and `docs/agent/slices/entered-times-in-india.md`.

## Permissions

```text
INTERACTION_READ           metadata: who, when, channel, subject, outcome
INTERACTION_CONTENT_READ   message body, participant addresses, and the external references
                           that ADDRESS the body (external_reference_url, external_message_id)
INTERACTION_CREATE
INTERACTION_UPDATE
INTERACTION_DELETE
```

Who holds each (added 7 October 2026, TB-1 TB1-904; the grants are in
`backend/app/modules/authorization/contract.py`):

```text
INTERACTION_READ           ADMIN, SALES_USER, SALES_MANAGER, FINANCE_USER, OPERATIONS_USER,
                           MANAGEMENT_READ_ONLY
INTERACTION_CONTENT_READ   ADMIN, SALES_USER, SALES_MANAGER, OPERATIONS_USER, MANAGEMENT_READ_ONLY
INTERACTION_CREATE         ADMIN, SALES_USER, SALES_MANAGER
INTERACTION_UPDATE         ADMIN, SALES_USER, SALES_MANAGER
INTERACTION_DELETE         ADMIN, SALES_MANAGER
```

`INTERACTION_CONTENT_READ` is deliberately narrower than `INTERACTION_READ` and excludes
`FINANCE_USER`. A caller holding only `INTERACTION_READ` receives the record with content and
content-addressing references blanked and `body_redacted: true` - not a 403, because the
existence of the conversation is not the sensitive part.

Redaction is applied in exactly one serializer shared by the list and detail routes, so it
cannot be applied on one and forgotten on the other.

## Data classification

`body_text` and `interaction_participant.address_or_number` are **Restricted
personal/statutory** under `DATA_CLASSIFICATION_AND_HANDLING.md`. Consequences that are part of
this contract, not implementation detail:

- Business events carry metadata only - never the body, the subject, or a participant address.
  Enforced by a fail-closed allowlist guard over every event-emission site.
- Committed fixtures use fictional content.
- Retention is an unset policy parameter (ADR-015 precedent): stored indefinitely for the pilot,
  no purge job, no invented default. `body_stored = false` with `body_text = NULL` is already the
  shape a future purge writes.
- Read-access auditing of message bodies is **not** implemented and is recorded as a known gap.

## MCF-001 conformance

| MCF-001 guarantee | Status in `INT-001` v1.0 |
| --- | --- |
| Stable public identity and explicit contract/schema version | **Met.** `contract_version` on every mutating response; `schema_version` in every event payload. |
| Server-derived actor identity, backend-authoritative authorization | **Met.** Actor from the authenticated session; every route gated by `require_permission`. |
| Correlation across command/event/job | **Met.** `X-Correlation-Id` honoured when supplied, generated when absent, persisted on the business event. |
| Idempotency for retryable commands | **Met.** See "Idempotency key scope" below - a retry replays only when it is provably the same command. |
| Structured non-sensitive errors with retryability | **NOT met - recorded exception, see below.** |
| Append-only durable facts through business events | **Met.** `InteractionRecorded` / `InteractionUpdated` / `InteractionDeleted`. |
| No direct cross-module repository/table writes | **Met.** Interactions writes only its own two tables. |

### Idempotency key scope

**Scope.** `idempotency_key` is unique across the whole module, not per record or per caller.
`(external_system, external_message_id)` is likewise unique across the module. Either identifies
**one specific create command**, not a licence to receive whichever row currently holds that key.

**Command identity.** On create, the service computes a SHA-256 over the normalized command
serialized as **canonical JSON** (sorted keys, compact separators, no NaN). The fields are the
contract constant `INTERACTION_FINGERPRINT_FIELDS`:

```text
linked_record_type      external_system            geo_latitude
linked_record_public_id external_message_id        geo_longitude
channel_code            external_reference_url     outcome
direction_code          subject                    next_follow_up_at
occurred_at             body_text                  participants (see below)
```

Adding a field to that constant is a deliberate decision about what "the same command" means.

Normalization, all of it deliberate and tested:

```text
datetimes      converted to UTC, so the same instant in two offsets is one command
decimals       trailing zeros stripped, so 19.076 and 19.076000 are one coordinate
external_system  fingerprinted at its EFFECTIVE value - the service stores MANUAL when the
                 caller omits it, so omitted and explicit "MANUAL" are the same command
participants     each serialized canonically, then the list sorted, so ordering is not identity
```

**Excluded: `idempotency_key` only.** It is the key, not the command. Also outside the command
is the acting user - the same command retried by a different authenticated user is still the
same command, and the original actor stays recorded.

**Canonical JSON, not a delimited string.** The encoding must be injective. An earlier version
joined `name=value` pairs with a control character, which let a value containing that delimiter
forge a field boundary: `subject="u"` with `body_text="v<US>body_text="` and
`subject="u<US>body_text=v"` with `body_text=""` produced identical bytes, so a retry could
replay an incompatible command despite the comparison being present. JSON escapes control
characters and quotes structurally, so ambiguity is impossible by construction rather than by
assuming no value contains the separator. That exact pair is now a regression test.

**Outcomes of a create whose key already exists:**

```text
same fingerprint, record active     201 with replayed: true, the original record, no new event
different fingerprint               409 - the key identifies one request; reusing it with a
                                    changed payload is refused, never silently replayed
record soft-deleted                 409 - a retry does not resurrect a deleted conversation and
                                    must not return deleted content as an active record
stored fingerprint absent           409 - fails closed; an unattributable row is not replayable
```

A different `linked_record_public_id` therefore yields `409`, not a cross-record replay: the
linked record is part of command identity.

**Correction, 8 September 2026.** The first implementation returned whichever row held the key
without comparing commands at all, so reusing a key with a different payload returned the
*original* record reported as the caller's own successful create. The fingerprint is what makes
the replay guarantee real, and the soft-delete case was undefined.

### Recorded compatibility exception: structured error envelope

`INT-001` returns FastAPI's `{"detail": "..."}` rather than the
`{"error": {"code", "message", "details"}}` envelope `CODING_STANDARDS.md` specifies and MCF-001
requires.

**Why this is an exception rather than a fix in 9D:** all nine existing route modules return
`{"detail": ...}` *(nine when 9D was built; seventeen by 7 October 2026, every one still on that
shape - TB-1 TB1-110)*. Adopting the envelope in Interactions alone would put two different error
shapes in one API surface, which is worse for a consumer than one consistent non-conforming
shape. This is precisely the cross-cutting retrofit ADR-025 assigns to PF-1B: "existing
APIs/events are explicitly inventoried and retrofitted under PF-1B/per-module packages; they are
not permanent exceptions to MCF-001."

```text
Scope         error response shape only; every other MCF-001 guarantee above is met
Owner         PF-1B API/event retrofit package
Retires with  the PF-1B error-envelope retrofit, applied across all modules at once
Review by     the final production-candidate gate, per PRODUCTION_READINESS_GATES.md, which
              already requires every release-scope API to adopt MCF conventions or carry a
              reviewed exception with a retirement date
Not permanent this exception expires with PF-1B and must not be renewed by a later slice
              silently adopting the same shape
```

Consumers must therefore **not** build error handling on the current shape expecting it to last.

## Events

```text
InteractionRecorded
InteractionUpdated
InteractionDeleted
```

`source_module = interactions`, `record_type = interaction`, `record_public_id` =
`interaction_public_id`. Payload keys are restricted to a reviewed allowlist; adding one is a
contract change.

## Explicitly out of scope for v1.0

```text
Ingestion connectors (Outlook, WhatsApp, Frejun/Runo IVR) - the idempotency columns exist for
    them, but no connector is implemented
File upload and stored attachments - 9C
Hard enforcement of the FRD logging rule before quoting - after the pilot habit forms
Retention purge and read-access auditing
Participant management after creation
Consolidating crm_lead_activity into interaction
```

## Change control

See `docs/agent/architecture/CONTRACT_REGISTRY.md`. Bump `INTERACTION_CONTRACT_VERSION` for any
change to the request/response shape, and record it here before implementing it.
