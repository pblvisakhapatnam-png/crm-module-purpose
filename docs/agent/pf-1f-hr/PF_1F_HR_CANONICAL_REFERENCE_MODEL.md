# PF-1F-HR Canonical HR Reference Model

## Status

Package: PF-1F-HR-E1, corrected under Correction 1 (C1-1, C1-3), Correction 2 (C2-1) and
Correction 3 (C3-1). Documentation/architecture only; no runtime code, migration or API
implements this model yet. See `docs/agent/ARCHITECTURE_DECISIONS.md` ADR-032.

**Correction 1 note.** The original version of this document put provider-specific reconciliation
fields directly on the canonical, consumer-facing Employee Reference record, and overclaimed that
every dataset supports full historical reconstruction. Corrected: provider-specific reconciliation
now lives only in the adapter-owned Source Binding model (section G).

**Correction 2 note (C2-1).** Correction 1 stated the *principle* (stable identity plus
effective-dated version records) but did not make it consistently implementable: the Organisation
Unit and Position "version" records reused the stable entity ID as if it were also the version row's
own primary key, with no field capable of representing more than one version per entity, and there
was no Employment Status History record for a person at all (only a single mutable
`employment_status` field). Both are corrected below by giving every version-record type its own
explicit version identifier, distinct from the stable entity identifier it belongs to, and by
adding an Employment Status History record. This correction also separates **business-effective
time** (`effective_from`/`effective_to`: what was true in the real world) from **recorded/system
time** (`recorded_at`/`superseded_at`: what the system knew and when), and defines corrected,
non-contradictory handling of backdated corrections. **SharePoint remains the approved Phase-1
interim provider for all of this; this correction changes the data model, not the technology.**
SharePoint's own built-in item-version history remains useful supplemental audit evidence (who
changed this SharePoint item and when) but is explicitly not the canonical business-effective
history contract (what business fact was effective during what period) - the two are different
concepts and only the second is what `ORA-001` and other consumers depend on.

**Correction 3 note (C3-1).** Correction 2 introduced explicit version identifiers but left three
defects: (1) the "current" projection (`active_flag`, `current_flag`) was defined only from
`effective_to`/`superseded_at`, omitting `effective_from` - a row recorded today for a future
transfer effective next month would incorrectly resolve as "current" the moment it was created,
before its business-effective date arrived; (2) the ordinary-change boundary example set the
closing row's `effective_to` to "the day before" the new row's `effective_from`, which under a
correctly half-open interval creates a one-day gap rather than a clean boundary; (3) the backdated-
correction procedure only described replacing a single "wrong row," not the case where a corrected
boundary invalidates two or more adjacent rows at once. All three are corrected below: an explicit
half-open interval convention and as-of formula are defined once and used everywhere ("As-of
resolution rule"); the ordinary-change procedure is restated with the correct boundary date; the
backdated-correction procedure is extended to identify and supersede every non-superseded row a
corrected boundary affects, not only one; and a new "Fail-closed ambiguity validation" subsection
requires the adapter to detect and refuse to resolve a canonical timeline that is overlapping,
contradictory, or missing required state, rather than arbitrarily picking a row.

## Purpose

Define a provider-neutral canonical model for the structured HR reference data that Plum does not
currently supply (ADR-032), so that CRM/Hiring, PF-1A and any future consumer depend only on a
canonical contract and never on SharePoint List Item IDs, SharePoint column names, Plum field
names, or employee names as identity. This model is what a future provider-neutral adapter must
expose, whatever system implements it in a given phase (Phase 1 SharePoint + Plum raw fields,
Phase 2 `NEW_SHARED_PLATFORM`, Phase 3 Plum synchronization).

This document does not replace `RMR-001` (Equipment and Employee Master Reference Contract) or
`ORA-001` (Organization Authority and Authorization Contract). It defines the canonical shape of
the data those contracts already describe as coming from "Employee Master", so that the current
interim source (SharePoint + Plum) and the eventual source (`NEW_SHARED_PLATFORM`) can both
implement the same contract without CRM/Hiring code changing between phases.

## Boundary architecture (the invariant this document enforces)

```text
CRM / Hiring / ORA / PF-1A
        |
        v
PROVIDER-NEUTRAL CANONICAL HR CONTRACT   (sections A-F below: consumer-facing DTOs/events only)
        |
        v
HR reference adapter / composition / reconciliation layer   (owns section G: source bindings,
        |                                                     comparison, event derivation)
   +----+----------------+
   |                     |
Plum/basic source    SharePoint/interim
   |                     |
   +----------+----------+
              |
        canonical output


Later:

CRM / Hiring / ORA / PF-1A
        |
     SAME CONTRACT (sections A-F unchanged)
        |
NEW_SHARED_PLATFORM HR / Organisation Reference Master
        |
optional Plum synchronization
```

**Rule.** Sections A-F are the only things a consumer (CRM, Hiring, ORA, PF-1A) may read or
depend on. Section G (Source Binding) is owned exclusively by the HR-reference adapter/composition
capability (a shared-platform capability per ADR-030; in Phase 1 this may be simple scheduled
tooling reading SharePoint and Plum, not a dedicated service). **PF-1A never reads a source
binding, never compares Plum and SharePoint itself, and never receives a SharePoint Item ID, a
Plum field name, or a raw provider timestamp.** Phase-1 comparison and canonical-event derivation
(section E) is adapter/composition work, not PF-1A work.

## Canonical identity rule

The platform assigns its own stable identifiers. They are never:

```text
- an employee name (any form: full name, "first + last", display name)
- a SharePoint List Item ID (SharePoint's own auto-incrementing ID column)
- a mutable Plum text field (department name, designation text, free-text manager name)
```

Minimum canonical **stable entity** identifiers, each immutable and never reused once assigned:

```text
person_id        immutable platform identifier (UUID/GUID)
org_unit_id      immutable platform identifier (UUID/GUID)
position_id      immutable platform identifier (UUID/GUID)
```

`incumbency_id` is not a stable-entity identifier in this same sense; it identifies one occupancy
interval (see section D) and is structurally a version-type record, the same as the other
version-record identifiers introduced below.

## Effective-dating pattern (corrected, C2-1)

### Two kinds of record, and three kinds of time

```text
1. STABLE ENTITY IDENTITY
   person_id / org_unit_id / position_id. Immutable, never reused, never itself versioned. It is
   the thing later version rows and other records point to.

2. VERSION / ASSIGNMENT RECORDS
   A version record has its OWN unique identifier (distinct from the stable entity ID it
   describes), because more than one version row exists for the same entity over time and each
   one must be independently addressable. This document defines four version-record types:
   Employment Status History, Organisation Unit Version, Position Version, and Position
   Incumbency.
```

Every version record carries three distinct kinds of timestamp - do not conflate them:

```text
BUSINESS-EFFECTIVE TIME        effective_from / effective_to
    When the described fact was/is true in the real world (e.g. "this person was ACTIVE from
    1 June 2021").

RECORDED TIME                  recorded_at
    When this row was entered into the system - the system's own knowledge time, independent of
    when the fact actually became true.

SUPERSESSION TIME              superseded_at (nullable)
    When this specific recorded row stopped being the system's current asserted claim about that
    business-effective period, because it was corrected. Null while the row remains the system's
    current claim. This is not the same as effective_to reaching its end date through ordinary
    prospective change - see "Ordinary change vs. backdated correction" below.
```

This is the minimum bitemporal-adjacent model needed for authority-affecting corrections to be
handled soundly; it is deliberately not a general-purpose bitemporal HRIS. A consumer that only
needs "what is true now" or "what was true as of date X" uses `effective_from`/`effective_to` and
ignores `recorded_at`/`superseded_at`/`correction_of`. Those recorded-time fields exist only to
support the correction case below and routine audit, not routine queries.

### Interval convention (corrected, C3-1)

Every version record uses one unambiguous convention, applied identically to Employment Status
History, Organisation Unit Version, Position Version, Position Incumbency, and any other canonical
authority-relevant version relationship:

```text
effective_from    INCLUSIVE - the fact is true starting on/at this instant.
effective_to      EXCLUSIVE, nullable - the fact stops being true starting on/at this instant
                  (i.e. it is still true immediately before effective_to, and no longer true
                  from effective_to onward). Null means "no known end yet."
```

Where the repository's date-only convention is used instead of full timestamps (as in the
SharePoint starter spec's Date-only columns), the same half-open semantics apply at day
granularity: `effective_to` is the first day the fact is **no longer** true, so a row with
`effective_from = 2026-06-01` and the immediately preceding row's `effective_to = 2026-06-01`
meet exactly at that boundary with no gap and no overlap - they do **not** need to (and must not)
differ by one day.

### As-of resolution rule (corrected, C3-1)

A non-superseded version row for a given stable entity is **effective as of** a given instant
(`as_of`) if and only if:

```text
effective_from <= as_of
AND (effective_to IS NULL OR as_of < effective_to)
AND superseded_at IS NULL
```

This is the *only* correct definition of "current"/"as of" resolution and replaces any narrower
derivation. In particular, **do not** derive "current" merely from `effective_to IS NULL AND
superseded_at IS NULL` - that omits the `effective_from <= as_of` term and would incorrectly treat
a future-dated prospective row as already current before its own start date. `active_flag` (A1)
and `current_flag` (D) are convenience projections of this same as-of rule evaluated at
`as_of = now`, never a separately-derived shortcut.

**Worked example (prospective change, correctly represented):**

```text
Current incumbent:  effective_from = 2026-01-01, effective_to = 2026-09-01
Future incumbent:   effective_from = 2026-09-01, effective_to = null
```

At any `as_of` before 2026-09-01, only the first row satisfies the as-of rule and resolves. At or
after 2026-09-01, only the second row satisfies it. No manually-maintained "Current Flag" may
override this: if a steward-convenience Current Flag exists (as it does in the SharePoint starter
spec), it is derived from the as-of rule evaluated at `as_of = now`, is explicitly non-canonical,
and a future/prospective row is correctly left with Current Flag = No until its own
`effective_from` arrives - two rows are not both "current" merely because one is un-superseded and
open-ended.

### Non-overlap rule

For a given stable entity identity and a given version-record type, among rows where
`superseded_at` is null (i.e. the entity's **current asserted timeline**, excluding anything a
later correction has superseded), no two rows' `[effective_from, effective_to)` half-open
intervals may overlap for any instant - equivalently, for any two such rows, one row's
`effective_to` must be less than or equal to the other row's `effective_from`. An implementation
must reject a write that would create an overlap under this half-open definition. A superseded row
is retained for audit but is excluded from this check - it no longer belongs to the current
asserted timeline, precisely because it was found to be wrong and replaced.

### Ordinary change vs. backdated correction

```text
ORDINARY PROSPECTIVE CHANGE (the normal case - e.g. a transfer effective from next Monday)
    1. Close the currently effective version row: set its effective_to to exactly the instant
       (or, at date granularity, exactly the date) the new fact takes effect - the SAME value as
       the new row's effective_from, per the half-open convention above. This is not "the day
       before"; setting it to the day before would leave a one-day gap where neither row is
       effective. Its superseded_at stays null - it was correct for its own period; it simply
       ended, which is what effective_to already records.
    2. Create a new version row with effective_from = the change's effective date/instant,
       recorded_at = now. Its correction_of field stays null - this is not a correction, it is a
       new fact.

BACKDATED CORRECTION (a previously recorded row's business-effective claim was itself wrong -
    e.g. a transfer was recorded as June but should have been May, or the wrong org unit was
    recorded entirely)
    1. Do NOT edit any affected row's effective_from/effective_to/attribute values in place; that
       would destroy the only evidence of what the system previously believed.
    2. Identify EVERY non-superseded row on the entity's current asserted timeline whose interval
       is changed by the correction - not only the row that was itself wrong. Moving a shared
       boundary can affect two (or more) adjacent rows at once. For example, if the system
       previously recorded:
           A: effective_from = 2026-01-01, effective_to = 2026-06-01
           B: effective_from = 2026-06-01, effective_to = null
       and the correction establishes the true boundary was 2026-05-01, both A and B are affected
       - not just whichever one was "wrong" - because correcting the boundary changes what each of
       them asserts.
    3. Set superseded_at to now on every row identified in step 2. Their own
       effective_from/effective_to remain exactly as originally recorded - that is the audit trail
       of what was believed and when.
    4. Create corrected replacement rows for each superseded row, with the corrected
       effective_from/effective_to and attribute values, recorded_at = now, and correction_of set
       to the specific superseded row each replacement corrects (e.g. A' corrects A, B' corrects
       B; `correction_of_status_history_id`, `correction_of_org_unit_version_id`, etc., as
       appropriate to the record type). Continuing the example: A' = (2026-01-01, 2026-05-01,
       correction_of = A), B' = (2026-05-01, null, correction_of = B).
    5. The replacement row(s) become part of the current asserted timeline (superseded_at null)
       and are what the non-overlap rule and the as-of resolution rule check going forward.
    A correction batch/group identifier may additionally be recorded to show that A' and B' were
    corrected together as one boundary correction, if useful for audit; this is optional and must
    not be over-engineered beyond what the correction linkage in step 4 already provides.
```

### Fail-closed ambiguity validation (new, C3-1)

The HR-reference adapter/composition capability must validate, not merely trust, the canonical
timeline it is about to return. Before resolving a canonical query (directly, or as input to an
`ORA-001` authority decision) for a given `as_of`, it checks the relevant entity's non-superseded
rows for that version-record type. If it finds any of the following, it must **not** arbitrarily
pick one:

```text
- more than one non-superseded row satisfying the as-of resolution rule for the same as_of
  (an overlap that should have been rejected at write time but was not, or a corrected boundary
  left unresolved);
- more than one current incumbent for the same position where joint occupancy is not explicitly
  supported (see section D);
- required authority-relevant state missing entirely for the as_of requested (e.g. no Employment
  Status History row covers that instant at all);
- otherwise contradictory unsuperseded assertions for the same entity and instant.
```

In every such case, the adapter records a reconciliation validation error, withholds the ambiguous
canonical value from the caller, and the dependent authority decision **fails closed** - the same
fail-closed principle `ORA-001` already applies to a stale/unavailable HR feed applies equally to
an internally ambiguous one. Resolution requires a human/data-steward correction (per "Ordinary
change vs. backdated correction" above), not an automatic tie-break. Phase 1 SharePoint enforcement
of the underlying non-overlap/single-incumbent rules may remain process- or adapter-based (native
SharePoint list constraints are not required to enforce interval semantics), but this validation
and fail-closed behaviour in the adapter is mandatory regardless of enforcement mechanism.

**Historical authority decisions are immutable regardless of a later HR correction.** A decision
already made under `ORA-001` retains its own decision-time authority snapshot (the specific
version/incumbency rows it resolved against, by their own version identifiers) and is never
retrospectively rewritten because a later correction changes what the HR record now says was true
at that time. This is the same principle `ORA-001` already states for HR changes generally;
correction handling here does not weaken it. Clearly distinguish:

```text
CANONICAL HR AS-OF BUSINESS VIEW           answers "what does the current asserted timeline say
                                            was true as of date X" - can change if a correction is
                                            later recorded for that period.

IMMUTABLE HISTORICAL APPROVAL EVIDENCE     the specific version/incumbency identifiers an actual
                                            authority decision resolved against at the time it was
                                            made - never changes, even if HR data is later
                                            corrected.
```

### Current-descriptive projections are not authoritative for history

A small set of current, non-authority-bearing descriptive fields (name, code, employment type) may
be projected as a convenience "what is this called right now" read model (sections A1, B1, C1
below). These projections are not themselves version records, are not effective-dated, and must
never be used to answer a historical "what was true as of date X" question - only the named version
records (Employment Status History, Organisation Unit Version, Position Version, Position
Incumbency) answer that.

## A. Employee Reference (canonical, consumer-facing)

### A1. Employee identity + current descriptive projection

```text
person_id
employee_code    nullable
full_name
date_joined      nullable if unavailable; a simple descriptive fact, not itself effective-dated
employment_type  nullable
active_flag      derived convenience projection of "does an Employment Status History row (A2)
                 satisfy the as-of resolution rule at as_of = now, with employment_status =
                 ACTIVE"; not itself authoritative for history - see "As-of resolution rule"
```

`date_left` is deliberately not a separate A1 field: it would duplicate, and could drift from, the
effective date already carried by the person's `LEFT` row in Employment Status History (A2). A
consumer needing "when did this person leave" reads the effective-dated `LEFT` row, not a second,
independently-editable date on A1.

### A2. Employment Status History (version record, effective-dated)

```text
employment_status_history_id   stable unique identifier for this version row (distinct from
                                person_id)
person_id                      non-unique canonical FK to A1; multiple rows per person over time
                                are expected and required
employment_status              ACTIVE | INACTIVE | ON_LEAVE | LEFT
effective_from
effective_to                    nullable while current
recorded_at
superseded_at                   nullable; see "Ordinary change vs. backdated correction" above
correction_of_status_history_id nullable; set only on a corrected row, referencing the row it
                                 corrects
```

This is the record `ORA-001`'s authority-lifecycle rules (suspension on inactive/leaver,
re-evaluation of pending approvals) actually resolve against, and the record a historical
authorization decision cites for "was this person an active employee as of the decision's
effective time." `person_id` remains unchanged and is never duplicated merely because employment
status changes; only a new `employment_status_history_id` row is created.

No provider-specific field (Plum department/designation/manager text, SharePoint list metadata,
source record keys) appears anywhere in A1 or A2. See section G for where that information lives.

Do not copy payroll, bank, Aadhaar, family, medical or salary fields merely because Plum may hold
them, consistent with the existing master-reference rule in
`docs/agent/architecture/DATA_CLASSIFICATION_AND_HANDLING.md` ("Resource planning may copy only the
operational minimum from Employee Master ... It must not copy payroll, bank, Aadhaar, medical,
family, salary or unrelated HR fields."). These fields remain classified `Restricted
personal/statutory` per that document and are out of scope for this reference dataset.

## B. Organisation Unit

### B1. Org unit identity

```text
org_unit_id   stable, never reused; survives every attribute/hierarchy change below
```

### B2. Organisation Unit Version (version record, effective-dated)

```text
org_unit_version_id    stable unique identifier for this version row (distinct from org_unit_id)
org_unit_id             non-unique canonical FK to B1; multiple version rows per org unit over
                        time are expected and required
org_unit_code
org_unit_name
org_unit_type
parent_org_unit_id      nullable for root
active_status
effective_from
effective_to             nullable while current
recorded_at
superseded_at            nullable; see "Ordinary change vs. backdated correction" above
correction_of_org_unit_version_id  nullable; set only on a corrected row
notes                    nullable
```

A change to name, type, parent, or active status creates a new B2 version row for the same
`org_unit_id` (an ordinary prospective change), or supersedes-and-corrects a prior row (a
backdated correction), per the rules above - it never edits a version row's
`effective_from`/`effective_to`/attributes in place to represent a different business fact.
`org_unit_id` is deliberately **not** required to be unique within the version table; only
`org_unit_version_id` is unique. This is what lets a historical decision reconstruct "what was
this org unit's parent/status as of the decision's effective time," which matters wherever
organisation hierarchy affects authority scope.

Support only the organisational scope levels PBL genuinely needs (for example company / region /
branch / site / department, where repository or business evidence supports them). Do not build a
more elaborate hierarchy than PBL's actual reporting structure requires; the SharePoint starter
spec (`PF_1F_HR_SHAREPOINT_STARTER_SPEC.md`) keeps this deliberately simple for Phase 1.

## C. Position

### C1. Position identity

```text
position_id   stable, never reused; survives every attribute/reporting-line change below
```

### C2. Position Version (version record, effective-dated)

```text
position_version_id      stable unique identifier for this version row (distinct from position_id)
position_id               non-unique canonical FK to C1; multiple version rows per position over
                          time are expected and required
position_code
position_name
designation_code          nullable
designation_name
org_unit_id
reports_to_position_id    nullable
active_status
effective_from
effective_to               nullable while current
recorded_at
superseded_at              nullable; see "Ordinary change vs. backdated correction" above
correction_of_position_version_id  nullable; set only on a corrected row
notes                      nullable
```

A change to name, designation, org unit, reporting line, or active status creates a new C2 version
row for the same `position_id` (or supersedes-and-corrects a prior row for a backdated
correction), so that a historical decision can reconstruct which org unit or reporting line a
position had as of the decision's effective time. `position_id` is not required to be unique
within the version table; only `position_version_id` is.

**Position is distinct from Designation.** Designation is a job-title label ("Regional Manager");
Position is a specific organisational seat ("Regional Manager - South"). Wherever an authority is
intended to attach to an organisational role rather than to a specific named person, that authority
must reference a Position (`PF_1A_AUTHORITY_CONFIGURATION_MODEL.md`'s Person/Position -> Role
assignment supports either). Do not require formal Positions where PBL does not need them; a small
office with no succession/authority-by-seat need may reference `person_id` directly instead.

## D. Position Incumbency (version record, effective-dated)

```text
incumbency_id                stable unique identifier for this occupancy interval
position_id
person_id
effective_from
effective_to                  nullable while current
recorded_at
superseded_at                 nullable; see "Ordinary change vs. backdated correction" above
correction_of_incumbency_id   nullable; set only on a corrected row
current_flag                  derived convenience projection of "does this row satisfy the
                              as-of resolution rule at as_of = now" (see "As-of resolution rule"
                              above - this requires effective_from <= now, not only
                              effective_to/superseded_at being blank); never an independent
                              source of truth - the effective-interval and supersession fields
                              govern
change_reason                 nullable
source_reference               nullable
```

Non-overlap rule (authoritative, not merely a process convention): among incumbency rows for a
given `position_id` where `superseded_at` is null, at most one may have an open/current effective
interval at any time - i.e. one position does not have two simultaneous exclusive incumbents
unless PBL explicitly approves joint occupancy for a specific position type, which this document
does not assume or build for. Likewise, for a given exact `(position_id, person_id)` pair, rows
must not contain overlapping duplicate intervals. Answers "who occupied this position during a
given effective period?" - the record `ORA-001` consumes to resolve position-based authority as of
a decision's effective time, and the record that lets a historical decision retain its
decision-time incumbent even after a later transfer or correction.

## E. Canonical HR change event model

Minimum fields:

```text
event_id
person_id
event_type
effective_at
recorded_at
previous_org_unit_id       nullable
new_org_unit_id            nullable
previous_position_id       nullable
new_position_id            nullable
previous_designation       nullable
new_designation            nullable
previous_employment_status nullable
new_employment_status      nullable
previous_manager_person_id nullable
new_manager_person_id      nullable
correction_of_event_id     nullable
backdated_correction_flag
source_reference           nullable
```

Note: the earlier version of this field list included a raw `source_system` field. It is removed;
an event's provenance is a source-binding/adapter concern (section G), not a canonical-event field.
`source_reference` above is a canonical, provider-neutral reference (for example, an internal
change-record identifier), not a raw Plum/SharePoint field name.

Event types (minimum, matching `ORA-001`'s employment/position change lifecycle):

```text
JOINER
TRANSFER
PROMOTION_OR_DESIGNATION_CHANGE
ORG_OR_SCOPE_CHANGE
REPORTING_CHANGE
LEAVER_OR_INACTIVATION
CORRECTION
BACKDATED_CORRECTION
```

**Ownership of derivation.** These events are not maintained by PBL staff as a manually-edited
SharePoint List, and they are **not** derived by PF-1A. In Phase 1 they are derived by the
**HR-reference adapter/composition capability** comparing controlled SharePoint and Plum state
over time (a scheduled or triggered comparison job, owned by that capability, produces the event
records this model defines whenever an Employment Status History, Organisation Unit Version,
Position Version or Position Incumbency version row is created, closed, or superseded-and-
corrected). PF-1A and every other consumer only ever reads the resulting canonical events through
`list_hr_change_events` (section H); it never performs the Plum/SharePoint comparison itself. This
keeps the change-feed model canonical and reusable across phases even though no sophisticated Plum
change feed exists yet; when Plum (or `NEW_SHARED_PLATFORM`) can supply true change events
directly, the derivation step inside the adapter/composition capability is replaced without
changing this event shape or any downstream consumer.

## F. Crew / Credential reference (boundary, not a Phase 1 build target)

Candidate fields, to be validated against actual Plum availability before any interim source is
introduced for them:

```text
person_id
crew_classification
credential_id
credential_type
credential_number
issuing_authority
equipment_or_category_scope   nullable
valid_from
valid_to
credential_status
evidence_document_reference   nullable
verified_at                   nullable
verification_status           nullable
```

Do not move Crew/Credential data wholesale into SharePoint. `RMR-001` and `ELA-001` already assume
this data is Plum-sourced; `PF_1F_HR_PLUM_GAP_ANALYSIS_PACKET.md` section F must first establish
which of these fields Plum actually and reliably supplies before any interim SharePoint List is
considered for a specific missing field, and only for the fields shown to have a genuine gap. Every
field's current Plum availability is `UNKNOWN` until verified (see the gap packet); none is
assumed present or assumed absent.

## G. Source Binding (adapter-owned; never exposed to consumers)

This is where every provider-specific fact lives. Section G records are read and written only by
the HR-reference adapter/composition capability. CRM, Hiring, ORA and PF-1A never query this
model directly and never receive its fields in a canonical response.

```text
binding_id
entity_type                 PERSON | ORG_UNIT | POSITION
entity_id                   the corresponding stable person_id / org_unit_id / position_id
provider_code                e.g. PLUM, SHAREPOINT
provider_record_key          nullable; the provider's own key/Item ID/row identity, if any
provider_display_name        e.g. the raw employee name as Plum shows it
provider_reference_fields    free-form reference object, e.g. Plum's free-text department,
                              designation, or reporting-manager text; SharePoint List/Item
                              metadata (including SharePoint's own built-in item-version history
                              reference, kept here as supplemental audit evidence only - see
                              "SharePoint version history is not the canonical history" below);
                              other provider-specific facts with no canonical field yet
reconciliation_status        CONFIRMED | AMBIGUOUS | UNMATCHED
reconciliation_notes         nullable
last_seen_at
source_version_or_last_modified  nullable
```

This is a starting shape, not a frozen schema; the adapter/composition implementation may extend
it as needed provided the invariant above holds: nothing in this section crosses into a canonical
consumer-facing record (sections A-F) except as adapter-internal input used to *compute* a
canonical value (e.g., using `provider_reference_fields`'s department text to help populate a
canonical `org_unit_id` once matched - the text itself is never copied into the canonical Employee
Reference).

One `entity_id` may have more than one active binding (for example, a person tracked in both Plum
and SharePoint); the adapter reconciles them and is responsible for surfacing `AMBIGUOUS` or
`UNMATCHED` cases for human reconciliation rather than silently picking one.

### SharePoint version history is not the canonical history

SharePoint's own built-in item-version history (which SharePoint maintains automatically for every
list item) answers a different question than the canonical version records in sections A2, B2, C2
and D: it answers "who changed this SharePoint item, and when, in system terms," not "what business
fact was effective during what period." SharePoint version history is useful supplemental audit
evidence, and the adapter/composition layer may reference it (via `provider_reference_fields` above)
when reconciling or investigating a discrepancy, but it is never a substitute for the canonical
`effective_from`/`effective_to`/`recorded_at`/`superseded_at`/`correction_of_*` fields, which are
the only fields `ORA-001` and other consumers may rely on for point-in-time reconstruction. This
holds regardless of which technology implements Phase 1 - it is a property of the canonical model,
not of SharePoint specifically.

## H. Provider-neutral adapter contract (conceptual)

Consumer-facing operations - the only interface CRM, Hiring, ORA and PF-1A may call:

```text
get_employee_reference(person_id, as_of?) -> Employee Reference (A1) [+ current or as-of
    Employment Status History row (A2)]
list_employee_references(as_of, filters) -> Employee Reference records
get_org_unit(org_unit_id, as_of?) -> the Organisation Unit Version (B2) valid as_of for that
    org_unit_id
list_org_units(as_of)
get_position(position_id, as_of?) -> the Position Version (C2) valid as_of for that position_id
list_positions(as_of)
get_incumbency(position_id, as_of) -> current or historical incumbent (D)
list_hr_change_events(since, person_id?) -> canonical HR change events (E)
```

Every response carries a canonical, adapter-generated freshness indicator (for example
`canonical_snapshot_at`), never a raw provider timestamp and never a provider name. Consumers use
this indicator against their own configured staleness threshold (see "Source-unavailable /
staleness behaviour" below); they never see `source_last_updated_at`, `provider_code`, or any other
section G field.

Adapter-internal operations (section G territory, never exposed to consumers): binding
create/update, reconciliation comparison, ambiguous/unmatched routing, and canonical-event
derivation (section E).

## Source-unavailable / staleness behaviour

Consistent with `ORA-001`'s existing rule ("After a configured maximum source-data age, a stale or
unavailable HR feed fails closed for new authority-dependent decisions"), the adapter is
responsible for knowing, from its own section G bindings, whether the canonical record it is about
to return is fresh enough. It exposes this to a consumer only as a canonical, provider-neutral
freshness indicator (`canonical_snapshot_at`) or an explicit "canonical record currently
unavailable/stale" result - never as a raw provider staleness fact. A consumer applies its own
configured staleness threshold against that indicator. This model does not itself set that
threshold value; the threshold remains a deferred policy parameter (see
`PF_1F_HR_DECISION_GATE.md`). The staleness control applies to this canonical, provider-neutral
freshness indicator irrespective of which provider (Plum, SharePoint, or in a later phase
`NEW_SHARED_PLATFORM`) currently backs it - see also
`docs/agent/architecture/NFR_BASELINE_AND_VERIFICATION.md`.

## Phase progression summary

```text
PHASE 1 (current)  SharePoint-backed interim structured reference (PF_1F_HR_SHAREPOINT_STARTER_SPEC.md)
                   + Plum raw/basic fields (PF_1F_HR_PLUM_GAP_ANALYSIS_PACKET.md), reconciled
                   through the adapter/composition capability's section G source bindings
PHASE 2            NEW_SHARED_PLATFORM HR / Organisation Reference Master implements this same
                   canonical model (sections A-F) and adapter contract (section H) as the
                   production system of record; it may retain its own internal source-binding
                   concept but is no longer required to reconcile Plum vs. SharePoint specifically
PHASE 3            Plum synchronizes/feeds applicable raw HR data into that shared master;
                   SharePoint Lists are retired as a data source once the shared master is live
```

Consumer contracts (sections A-F and H of this document, `RMR-001`, `ORA-001`) remain stable across
all three phases. Only section G's internal composition changes between phases. This correction
(C2-1) changes only the internal shape of the version records (adding explicit version identifiers
and recorded/superseded/correction fields); it does not change which phase currently supplies the
data, and does not introduce a new storage technology - SharePoint remains the approved Phase 1
interim provider.
