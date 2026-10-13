# PF-1F-HR SharePoint Interim Starter Specification

## Status

Package: PF-1F-HR-E1, corrected under Correction 1 (C1-1, C1-4) and Correction 2 (C2-1). Practical
specification for PBL staff to begin populating governed SharePoint Lists immediately, per
ADR-032. No application/integration code exists yet; this is the data-entry target the future
HR-reference adapter/composition capability (`PF_1F_HR_CANONICAL_REFERENCE_MODEL.md`) will read
from in Phase 1. **SharePoint remains the approved Phase 1 interim provider; this correction
changes the list structure needed to represent history soundly, not the technology.**

**Correction 2 note (C2-1).** The four-list version of this spec conflated stable identity and
effective-dated version data in the same List (an Organisation Unit's name/parent/status lived in
the same row as its identity, with no way to add a second version without either overwriting the
first or relying on SharePoint's Item ID to distinguish versions - exactly the ambiguity C1-4
already ruled out for relationships). It also had no place at all to record employment-status
history; "Employment Status" was a single mutable field on the Employee Reference row. Both are
corrected by splitting each entity into a **stable identity List** and a separate **version List**
with its own explicit version-ID column, per
`PF_1F_HR_CANONICAL_REFERENCE_MODEL.md`'s corrected model. **SharePoint's own built-in item-version
history (who edited this SharePoint row and when) remains useful supplemental audit evidence but is
not, and was never intended to be, the canonical business-effective history; that is what the new
explicit version Lists below provide.**

## Purpose and scope

Seven Lists cover the Phase 1 interim structured HR reference:

```text
1. Employee Reference               (stable identity + current descriptive projection)
2. Employment Status History        (effective-dated version records)
3. Organisation Units                (stable identity)
4. Organisation Unit Versions        (effective-dated version records)
5. Positions                         (stable identity)
6. Position Versions                 (effective-dated version records)
7. Position Incumbency               (effective-dated version records; already inherently
                                       version-shaped, corrected to add recorded/superseded/
                                       correction fields)
```

This is more Lists than the original four, adopted deliberately because it is the cleanest
coherent way to make repeated, non-destructive effective-dated versions actually representable in
SharePoint, per `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md`'s corrected effective-dating pattern. It is
still a small, practical Phase 1 shape, not a general-purpose HRIS.

A Crew/Credentials list is **not** created by default. `PF_1F_HR_PLUM_GAP_ANALYSIS_PACKET.md`
section F must first show that a specific credential field has a genuine Plum gap before an eighth
list is added for it.

An **HR Change Event** list is **not** created. Change events are derived by the adapter/
composition capability (see `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` section E), not manually
maintained; asking staff to maintain both current state and a parallel change log invites drift
between the two.

## Golden rules for every list

- SharePoint's built-in Item ID (the auto-numbered `ID` column) is **never** the canonical business
  identifier and is **never** used to implement a relationship between lists.
- Every **identity** List (Employee Reference, Organisation Units, Positions) carries exactly one
  canonical identity GUID column (`person_id`, `org_unit_id`, `position_id` respectively), unique
  within that list.
- Every **version** List (Employment Status History, Organisation Unit Versions, Position
  Versions, Position Incumbency) carries its **own** unique version-ID column (e.g.
  `employment_status_history_id`), distinct from the stable entity ID it describes, plus a
  non-unique canonical FK column back to the entity's identity List. Multiple version rows sharing
  the same entity ID are expected and required; the entity ID column is deliberately **not** set
  unique in a version List.
- A GUID column is generated once, at first entry, and never edited afterward. If a record is
  wrong, follow the correction procedure below rather than editing the GUID or the historical
  effective dates in place.
- **Canonical relationships between lists (C1-4) are stored as plain text columns holding the
  target's canonical GUID value** (for example, a Position Version row's `org_unit_id` column
  holds the literal GUID text of the Organisation Unit it belongs to), **not** as a native
  SharePoint "Lookup" column. A native SharePoint Lookup column internally keys off the target
  list's Item ID; if that Item ID ever changes (list export/import/recreate, or a
  copy-to-another-site operation), a Lookup column's relationship silently breaks even though the
  canonical GUIDs on both sides are unchanged. Storing the plain GUID text avoids that failure mode
  entirely and is what the adapter validates/resolves against.
- A SharePoint "Lookup" column MAY additionally be created purely for a human steward's editing
  convenience (e.g. to get a searchable picker and see the related row's display name inline). If
  used, it is explicitly **non-canonical**: it is rebuildable at any time from the plain GUID text
  column, it may rely internally on SharePoint Item IDs, and neither the adapter nor any export/
  migration step may treat its value as authoritative. The plain GUID text column is always the
  canonical relationship of record.
- **Effective From is inclusive; Effective To is exclusive (corrected, C3-1).** A row is effective
  starting exactly on its Effective From date and stops being effective exactly on its Effective To
  date (not the day after). This means an ordinary change's closing row and its successor row use
  the **same** date for the closing row's Effective To and the successor's Effective From - there
  is no one-day gap and no overlap. See `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` "Interval
  convention" and "As-of resolution rule" for the full rule, including the precise "is this row
  effective as of a given date" test (which always checks Effective From against that date, not
  only Effective To/Superseded At).
- **Ordinary change vs. backdated correction**, applied identically in every version List (see
  `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` "Ordinary change vs. backdated correction" for the full
  rule): for an ordinary prospective change, close the current version row's Effective To (to the
  same date the new row's Effective From uses) and add a new row. For a backdated correction (a
  previously entered row's business facts or dates were themselves wrong), do **not** edit the old
  row's Effective From/To or attribute values - identify **every** non-superseded row the
  correction affects (correcting a shared boundary between two adjacent rows affects both of them,
  not only the one that was "wrong"), set Superseded At to now on each, and add one corrected
  replacement row per superseded row, each with its Correction Of column pointing back to the
  specific row it replaces. This preserves the original rows as evidence of what was previously
  believed. See the worked boundary-correction example in the canonical model document.
- **Ambiguous timelines fail closed, not silently resolved.** If the adapter ever finds more than
  one non-superseded row satisfying the as-of test for the same date, more than one current
  incumbent for a position, or a gap where no row covers a required date, it must not guess - it
  records a validation error and withholds that canonical value until an HR data steward corrects
  the Lists (see `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` "Fail-closed ambiguity validation"). This
  is why the ordinary-change and backdated-correction procedures above must be followed precisely.
- SharePoint's automatic per-item version history (visible under each item's "Version History")
  remains available as supplemental audit evidence for every list, free of any extra configuration.
  It answers "who edited this SharePoint row and when," which is a different question from "what
  business fact was effective during what period" - only the canonical Effective From/To/Recorded
  At/Superseded At/Correction Of columns answer the second question, and only they are read by the
  adapter as canonical history.

## List 1: Employee Reference (stable identity)

Columns 1-5 feed the canonical Employee Reference identity/projection
(`PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` section A1). Columns 6-11 feed the adapter-owned Source
Binding (section G) and are **never** exposed to CRM/Hiring/PF-1A as canonical fields; this List
co-locates both groups in one SharePoint row purely for the HR data steward's convenience, since
only the adapter reads this List directly. **Employment status is not a column on this list** -
see List 2.

| # | Display name | Canonical or Source Binding | Canonical/internal name | SharePoint type | Required | Unique | Allowed values | Validation | Example | Maintained by | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Person ID | Canonical (A1 identity) | `person_id` | Single line of text (or a Power Automate-generated GUID) | Yes | Yes | GUID format | Must be a valid GUID; generated once at creation, never edited | `3fa2...c9e1` | HR data steward (system-generated) | Canonical platform generation |
| 2 | Employee Code | Canonical (A1) | `employee_code` | Single line of text | No | Yes (when present) | - | Free text; leave blank if Plum has none | `EMP-01234` | HR data steward | Plum (if available) |
| 3 | Full Name | Canonical (A1) | `full_name` | Single line of text | Yes | No | - | Non-blank | `Asha Rao` | HR data steward | Plum / HR record |
| 4 | Date Joined | Canonical (A1) | `date_joined` | Date only | No | No | - | Leave blank if unknown; a simple descriptive fact, not itself effective-dated | `2021-06-01` | HR data steward | Plum / HR record |
| 5 | Employment Type | Canonical (A1) | `employment_type` | Choice | No | No | `PERMANENT`, `CONTRACT`, `VENDOR_CREW`, `OTHER` | - | `PERMANENT` | HR data steward | HR record |
| 6 | Source Employee Name (Plum) | Source Binding (G: `provider_display_name`) | `provider_display_name` | Single line of text | Yes | No | - | Non-blank; the exact name string as it appears in Plum | `Rao, Asha` | HR data steward | Plum |
| 7 | Source Department Text | Source Binding (G: `provider_reference_fields`) | `provider_department_text` | Single line of text | No | No | - | Free text, as Plum shows it | `Operations - West` | HR data steward | Plum |
| 8 | Source Designation Text | Source Binding (G: `provider_reference_fields`) | `provider_designation_text` | Single line of text | No | No | - | Free text, as Plum shows it | `Regional Manager` | HR data steward | Plum |
| 9 | Source Reporting Manager Text | Source Binding (G: `provider_reference_fields`) | `provider_reporting_manager_text` | Single line of text | No | No | - | Free text, as Plum shows it | `Verma, Sanjay` | HR data steward | Plum |
| 10 | Match Status | Source Binding (G: `reconciliation_status`) | `reconciliation_status` | Choice | Yes | No | `CONFIRMED`, `AMBIGUOUS`, `UNMATCHED` | `AMBIGUOUS`/`UNMATCHED` requires Match Notes | `CONFIRMED` | HR data steward | Canonical platform generation |
| 11 | Match Notes | Source Binding (G: `reconciliation_notes`) | `reconciliation_notes` | Multiple lines of text | No | No | - | Required when Match Status is not `CONFIRMED` | `Two "A. Rao" entries in Plum export; confirmed by employee code lookup` | HR data steward | HR data steward |

`date_left` and `active_flag` (A1) are not separate SharePoint columns here: `date_left` would
duplicate the effective date already carried by the person's `LEFT` row in List 2, and
`active_flag` is derived by the adapter from the current List 2 row.

## List 2: Employment Status History (effective-dated version records)

Feeds the canonical Employment Status History (section A2). One person has one or more rows over
time.

| # | Display name | SharePoint type | Required | Unique | Allowed values | Validation | Example | Maintained by | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Employment Status History ID | Single line of text (GUID) | Yes | Yes | GUID format | Generated once, never edited; distinct from Person ID | `a1c2...` | HR data steward (system-generated) | Canonical platform generation |
| 2 | Person ID | **Single line of text holding the Employee Reference List's `person_id` GUID** (not a SharePoint Lookup column) | Yes | No (multiple rows per person are expected) | - | Must reference an existing person in List 1 | `3fa2...c9e1` | HR data steward | HR record |
| 3 | Employment Status | Choice | Yes | No | `ACTIVE`, `INACTIVE`, `ON_LEAVE`, `LEFT` | Must be one of the listed values | `ACTIVE` | HR data steward | HR record |
| 4 | Effective From | Date only | Yes | No | - | Must not overlap another non-superseded row for the same Person ID | `2021-06-01` | HR data steward | HR record |
| 5 | Effective To | Date only | No | No | - | Blank while current | - | HR data steward | HR record |
| 6 | Recorded At | Date and Time | Yes | No | - | Auto-set on save | - | System (list default) | System |
| 7 | Superseded At | Date and Time | No | No | - | Set only when a later row corrects this one (see Golden Rules) | - | HR data steward | HR record |
| 8 | Correction Of (Employment Status History ID) | **Single line of text holding another row's Employment Status History ID in this same List** (not a SharePoint Lookup column) | No | No | - | Set only on a corrected row; must reference an existing row in this List | `a1c2...` | HR data steward | HR record |

## List 3: Organisation Units (stable identity)

Feeds the canonical Organisation Unit identity (section B1). This List is intentionally minimal -
name, type, hierarchy and status live in List 4, because they can change over time while the
identity does not.

| # | Display name | SharePoint type | Required | Unique | Validation | Example | Maintained by | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Org Unit ID | Single line of text (GUID) | Yes | Yes | Generated once, never edited | `7c1e...` | HR data steward (system-generated) | Canonical platform generation |
| 2 | Reference Label (display only) | Single line of text | No | No | Non-canonical convenience only - the steward may keep this mirroring the current org unit name/code from List 4 for easier browsing; the adapter never reads this column | `OPS-WEST - Operations - West Region (display only)` | HR data steward | Derived/manual convenience |

## List 4: Organisation Unit Versions (effective-dated version records)

Feeds the canonical Organisation Unit Version (section B2). One org unit has one or more rows over
time, plus one Source Binding column at the end.

| # | Display name | Canonical or Source Binding | SharePoint type | Required | Unique | Allowed values | Validation | Example | Maintained by | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Org Unit Version ID | Canonical | Single line of text (GUID) | Yes | Yes | GUID format | Generated once, never edited; distinct from Org Unit ID | `d4e5...` | HR data steward (system-generated) | Canonical platform generation |
| 2 | Org Unit ID | Canonical | **Single line of text holding the Organisation Units List's `org_unit_id` GUID** (not a SharePoint Lookup column) | Yes | No (multiple rows per org unit are expected) | - | Must reference an existing org unit in List 3 | `7c1e...` | HR data steward | HR record |
| 3 | Org Unit Code | Canonical | Single line of text | Yes | No | - | Short stable code | `OPS-WEST` | HR data steward | HR record |
| 4 | Org Unit Name | Canonical | Single line of text | Yes | No | - | Non-blank | `Operations - West Region` | HR data steward | HR record |
| 5 | Org Unit Type | Canonical | Choice | Yes | No | `COMPANY`, `REGION`, `BRANCH`, `SITE`, `DEPARTMENT` | Only the levels PBL actually needs | `REGION` | HR data steward | HR record |
| 6 | Parent Org Unit ID | Canonical | **Single line of text holding another org unit's `org_unit_id` GUID from List 3** (not a SharePoint Lookup column) | No (required except for root) | No | - | Must be a valid `org_unit_id` in List 3; must not create a cycle | `<GUID of OPS company root>` | HR data steward | HR record |
| 7 | Active Status | Canonical | Choice | Yes | No | `ACTIVE`, `INACTIVE` | - | `ACTIVE` | HR data steward | HR record |
| 8 | Effective From | Canonical | Date only | Yes | No | - | Must not overlap another non-superseded version row for the same Org Unit ID | `2020-04-01` | HR data steward | HR record |
| 9 | Effective To | Canonical | Date only | No | No | - | Blank while current | - | HR data steward | HR record |
| 10 | Recorded At | Canonical | Date and Time | Yes | No | - | Auto-set on save | - | System (list default) | System |
| 11 | Superseded At | Canonical | Date and Time | No | No | - | Set only when a later row corrects this one | - | HR data steward | HR record |
| 12 | Correction Of (Org Unit Version ID) | Canonical | **Single line of text holding another row's Org Unit Version ID in this same List** | No | No | - | Set only on a corrected row | `d4e5...` | HR data steward | HR record |
| 13 | Notes | Canonical | Multiple lines of text | No | No | - | - | - | HR data steward | HR data steward |
| 14 | Plum Department Mapping | Source Binding (G: `provider_reference_fields`, `entity_type = ORG_UNIT`) | Single line of text | No | No | - | Free text, as Plum shows it | `WEST-OPS` | HR data steward | Plum |

A change to name/type/parent/status follows the Golden Rules' ordinary-change or backdated-
correction procedure for the same `org_unit_id`; it never edits a version row's Effective
From/To/attributes in place to represent a different business fact.

## List 5: Positions (stable identity)

Feeds the canonical Position identity (section C1). As minimal as List 3, for the same reason.

| # | Display name | SharePoint type | Required | Unique | Validation | Example | Maintained by | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Position ID | Single line of text (GUID) | Yes | Yes | Generated once, never edited | `9ab0...` | HR data steward (system-generated) | Canonical platform generation |
| 2 | Reference Label (display only) | Single line of text | No | No | Non-canonical convenience only, mirrors current Position Name from List 6; the adapter never reads this column | `RM-SOUTH - Regional Manager - South (display only)` | HR data steward | Derived/manual convenience |

## List 6: Position Versions (effective-dated version records)

Feeds the canonical Position Version (section C2). One position has one or more rows over time.

| # | Display name | SharePoint type | Required | Unique | Allowed values | Validation | Example | Maintained by | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Position Version ID | Single line of text (GUID) | Yes | Yes | GUID format | Generated once, never edited; distinct from Position ID | `f6a7...` | HR data steward (system-generated) | Canonical platform generation |
| 2 | Position ID | **Single line of text holding the Positions List's `position_id` GUID** (not a SharePoint Lookup column) | Yes | No (multiple rows per position are expected) | - | Must reference an existing position in List 5 | `9ab0...` | HR data steward | HR record |
| 3 | Position Code | Single line of text | Yes | No | - | Short stable code | `RM-SOUTH` | HR data steward | HR record |
| 4 | Position Name | Single line of text | Yes | No | - | Non-blank | `Regional Manager - South` | HR data steward | HR record |
| 5 | Designation Code | Single line of text | No | No | - | - | `RM` | HR data steward | HR record |
| 6 | Designation Name | Single line of text | Yes | No | - | Non-blank; the job-title label, distinct from Position Name | `Regional Manager` | HR data steward | Plum / HR record |
| 7 | Org Unit ID | **Single line of text holding the Organisation Units List's `org_unit_id` GUID (List 3)** (not a SharePoint Lookup column) | Yes | No | - | Must be a valid `org_unit_id` in List 3 | `<GUID of OPS-SOUTH>` | HR data steward | HR record |
| 8 | Reports To Position ID | **Single line of text holding another position's `position_id` GUID from List 5** (not a SharePoint Lookup column) | No | No | - | Must be a valid `position_id` in List 5; must not create a reporting cycle | `<GUID of HEAD-OPS>` | HR data steward | HR record |
| 9 | Active Status | Choice | Yes | No | `ACTIVE`, `INACTIVE` | - | `ACTIVE` | HR data steward | HR record |
| 10 | Effective From | Date only | Yes | No | - | Must not overlap another non-superseded version row for the same Position ID | `2021-01-01` | HR data steward | HR record |
| 11 | Effective To | Date only | No | No | - | Blank while current | - | HR data steward | HR record |
| 12 | Recorded At | Date and Time | Yes | No | - | Auto-set on save | - | System (list default) | System |
| 13 | Superseded At | Date and Time | No | No | - | Set only when a later row corrects this one | - | HR data steward | HR record |
| 14 | Correction Of (Position Version ID) | **Single line of text holding another row's Position Version ID in this same List** | No | No | - | Set only on a corrected row | `f6a7...` | HR data steward | HR record |
| 15 | Notes | Multiple lines of text | No | No | - | - | - | HR data steward | HR data steward |

A change to name/designation/org unit/reporting line/status follows the same ordinary-change or
backdated-correction procedure for the same `position_id`.

## List 7: Position Incumbency (effective-dated version records)

Feeds the canonical Position Incumbency (section D). `incumbency_id` is already, by design, a
version-level identifier (one row per occupancy interval), so this List does not need a separate
identity/version split - it is corrected here only by adding the Recorded At / Superseded At /
Correction Of columns the other version Lists have, for the same reason.

| # | Display name | SharePoint type | Required | Unique | Allowed values | Validation | Example | Maintained by | Source |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Incumbency ID | Single line of text (GUID) | Yes | Yes | GUID format | Generated once, never edited | `21fd...` | HR data steward (system-generated) | Canonical platform generation |
| 2 | Position ID | **Single line of text holding the Positions List's `position_id` GUID (List 5)** (not a SharePoint Lookup column) | Yes | No | - | Must reference an existing position | `<GUID of RM-SOUTH>` | HR data steward | HR record |
| 3 | Person ID | **Single line of text holding the Employee Reference List's `person_id` GUID (List 1)** (not a SharePoint Lookup column) | Yes | No | - | Must reference an existing, active person | `3fa2...c9e1` | HR data steward | HR record |
| 4 | Effective From | Date only | Yes | No | - | Must not overlap another non-superseded, current-tracked incumbency row for the same Position ID (see validation note below) | `2024-09-01` | HR data steward | HR record |
| 5 | Effective To | Date only | No | No | - | Blank while current | - | HR data steward | HR record |
| 6 | Recorded At | Date and Time | Yes | No | - | Auto-set on save | - | System (list default) | System |
| 7 | Superseded At | Date and Time | No | No | - | Set only when a later row corrects this one | - | HR data steward | HR record |
| 8 | Correction Of (Incumbency ID) | **Single line of text holding another row's Incumbency ID in this same List** | No | No | - | Set only on a corrected row | `21fd...` | HR data steward | HR record |
| 9 | Current Flag | Yes/No | Yes | No (only one `Yes` per active Position at a time among non-superseded rows - see validation note) | - | Derived from the as-of test (Effective From <= today AND (Effective To is blank OR today < Effective To) AND Superseded At is blank) - **not** merely from Effective To/Superseded At being blank; a future-dated row must show `No` until its own Effective From arrives | `Yes` | HR data steward | Derived |
| 10 | Change Reason | Choice | No | No | `JOINER`, `TRANSFER`, `PROMOTION`, `LEAVER`, `CORRECTION`, `OTHER` | - | `TRANSFER` | HR data steward | HR record |
| 11 | Source Reference | Single line of text | No | No | - | Free text, e.g. HR memo reference | `Memo/HR/2024/118` | HR data steward | HR record |

**"Only one current incumbent per position" is the canonical non-overlap rule
(`PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` section D), enforced by process/adapter validation in
Phase 1, not by a native SharePoint list constraint.** SharePoint Lists cannot natively enforce
"exactly one non-superseded row satisfies the as-of test per Position ID at any given date." Until
a later implementation enforces this server-side, the HR data steward must, for an ordinary
transfer, set the prior incumbency row's `Effective To` to the same date the new row's
`Effective From` uses (so the two intervals meet with no overlap and no gap) before adding the new
row; for a backdated correction, set `Superseded At` on every affected row (see the boundary-
correction procedure above) rather than leaving two rows simultaneously satisfying the as-of test.
If a steward mistake nonetheless produces an overlap, the adapter's fail-closed validation
(`PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` "Fail-closed ambiguity validation") is expected to catch
it and withhold that Position's canonical incumbency until corrected, rather than a native
SharePoint constraint preventing it up front. A future Phase 1 refinement may add a Power Automate
flow to catch this earlier; it is not required to start populating the lists.

## Access and governance (Phase 1)

- Each list has a named HR data steward maintainer role. Only the steward (and IT admins for
  schema changes) can edit; other staff have read access appropriate to their role.
- GUID columns are populated by a simple Power Automate flow or a manual GUID-generation
  convention at record creation; either is acceptable for Phase 1 as long as GUIDs are never
  reused or edited after creation.
- These Lists hold employment/organisational reference data classified `Internal operational` in
  `docs/agent/architecture/DATA_CLASSIFICATION_AND_HANDLING.md`, not `Restricted personal/
  statutory` data — do not add payroll, bank, Aadhaar, medical or salary columns to these Lists.
- Only the HR-reference adapter/composition capability reads these Lists directly. CRM, Hiring,
  ORA and PF-1A never query SharePoint directly and never see a Source Binding column (List 1
  columns 6-11, or List 4's Plum Department Mapping); they consume only the canonical adapter
  contract in `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` section H.
- SharePoint's own automatic item-version history remains enabled on every list as supplemental
  audit evidence; it requires no extra configuration and is not itself read by the adapter as
  canonical history (see Golden Rules).

## Operational summary for staff (plain-language)

**First, know which List actually holds the fact you are changing (corrected, C3-1).** A person's
own name, employee code, date joined and employment type live on List 1 (Employee Reference), an
**identity** List with no version history - fixing a typo in someone's name is a direct edit to
that one field on List 1, not a version-List procedure, because List 1 does not track name history
and is not itself effective-dated. Employment status, org unit definitions (including an org
unit's own name), position definitions (including a position's own name) and position incumbency
are the things that actually go through the version-List procedures below, because those are the
facts the approval system needs to reconstruct as of a past date. Do not follow the version-List
procedure for a field that has no version List.

```text
Ordinary change to an effective-dated fact (e.g. a routine transfer, an employment-status change,
an org unit or position name/reporting-line change effective from a known date):
    1. Find the current version row for the person/org unit/position in the relevant version List
       (List 2, 4, 6 or 7).
    2. Set its Effective To to the SAME date the change takes effect (not the day before - see
       "Effective From is inclusive; Effective To is exclusive" above).
    3. Add a new row with the new facts, Effective From = that same effective date.
    Nothing about the old row's other fields is edited.

Backdated correction (e.g. "we recorded the wrong date last month" or "we recorded the wrong org
unit entirely", including a shared boundary between two adjacent rows both being wrong):
    1. Find every non-superseded row the correction actually affects - if the correction moves a
       boundary shared by two adjacent rows, both rows are affected, not only the one that seems
       "wrong."
    2. Set Superseded At to today on each affected row. Do not change anything else on those rows.
    3. Add one corrected replacement row per superseded row, with the corrected facts and dates,
       and set each replacement's Correction Of column to the specific row it replaces.

If, after following either procedure, two rows still both look current, or a gap appears where no
row covers a needed date, stop and re-check the dates rather than leaving it for the adapter to
guess - the adapter will refuse to resolve an ambiguous timeline (see "Ambiguous timelines fail
closed" above) rather than picking one.
```

## What this spec does not cover

- No SharePoint automation, workflow, or integration code is created by this spec.
- No Power Platform / Graph API adapter is built; that is future HR-reference adapter/composition
  implementation work consuming the canonical model in
  `PF_1F_HR_CANONICAL_REFERENCE_MODEL.md`.
- No Crew/Credentials list, pending the gap analysis in
  `PF_1F_HR_PLUM_GAP_ANALYSIS_PACKET.md` section F.
- No server-side enforcement of the non-overlap/single-current-incumbent rules; Phase 1 relies on
  the steward following the procedure above, with a Power Automate enforcement flow as optional
  future hardening.
