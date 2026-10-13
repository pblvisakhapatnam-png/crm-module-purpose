# PF-1F-HR Plum HR data: field availability packet

## Status

Package: PF-1F-HR-E1. Documentation only. This packet does not itself contain Plum's answers; it is the
structured question set, and what PBL has already confirmed, for a short conversation with Plum's implementer to fill
in. See ADR-032. Only the four structures named in the next section are confirmed absent; every other field marked
`UNKNOWN` or `ASSUMED_NEEDS_VALIDATION` must not be treated as absent until Plum is asked. The `source_*` fields in the
Employee Reference table are adapter-owned Source Binding fields (`PF_1F_HR_CANONICAL_REFERENCE_MODEL.md` section G),
not canonical fields.

## What PBL has confirmed Plum does not hold (no need to ask again)

```text
Structured Organisation Unit Master:  NO (confirmed)
True Position Master:                 NO (confirmed)
Position Incumbency/effective-dating: NO (confirmed)
Sophisticated HR change feed:         NO (confirmed)
Stable immutable Employee ID:         UNKNOWN / LIKELY ABSENT until verified
```

The immediate Plum exercise is therefore: **what fields does Plum actually have, and in what
form?** — not "can Plum build the target architecture before we continue?"

## Field-by-field analysis table

Columns, in order: canonical dataset, canonical field, required/optional, business reason,
expected current source, Plum entity/screen/table (if known), Plum field (if known), available in
Plum (YES/PARTIAL/NO/UNKNOWN), stable identifier available?, controlled code available?, effective
dating available?, last-modified/version available?, interface/export available?, data-quality
concern, SharePoint interim source required?, future shared-master field?, Plum enhancement
desirable?, blocks PF-1A?, notes/evidence.

### Employee Reference

| Canonical field | Req/Opt | Business reason | Expected source | Plum entity/screen | Plum field | Available in Plum | Stable ID? | Controlled code? | Effective dating? | Last-modified? | Interface/export? | Data-quality concern | SharePoint interim required? | Future shared-master field? | Plum enhancement desirable? | Blocks PF-1A? | Notes/evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `person_id` | Required | Canonical platform identity | Platform-generated | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | None - never sourced from Plum | No | Yes | No | No | Generated once at first reconciliation, never from Plum |
| `employee_code` | Optional | Human-readable reference where one exists | Plum (if available) | HR/Employee Master screen | Employee Code/No. | UNKNOWN | UNKNOWN | UNKNOWN | n/a | UNKNOWN | UNKNOWN | Reliability unconfirmed | No (captured directly if Plum has it) | Yes | Desirable: make it stable/immutable | No | Ask Plum: does an employee code exist, is it ever reissued/reused? |
| `full_name` (canonical) / `provider_display_name` (adapter Source Binding field, section G) | Required | Human identification, reconciliation anchor | Plum | HR/Employee Master screen | Employee Name | YES (assumed - Plum is understood to identify employees by name today, per the human owner decision; not itself in question) | n/a (name is not an identifier) | n/a | n/a | UNKNOWN | UNKNOWN | Name formatting/duplicates | Yes (as an adapter-owned reconciliation anchor only - never a canonical field, see Correction 1) | No (name stays a Source Binding reconciliation field, never canonical identity) | No | No | Confirm exact name format/casing Plum stores |
| `employment_status` | Required | Determines active authority eligibility | Plum | HR/Employee Master screen | Status field | UNKNOWN | n/a | UNKNOWN (status codes may be inconsistent) | UNKNOWN | UNKNOWN | UNKNOWN | Reliability unconfirmed - PBL flagged this as a desirable enhancement target | Yes, until confirmed reliable | Yes | Desirable: a reliable, controlled status code | No (SharePoint captures it in the interim) | See "high-value improvements" below |
| `date_joined` | Optional | Tenure/eligibility context | Plum | HR/Employee Master screen | Date of Joining | UNKNOWN | n/a | n/a | UNKNOWN | UNKNOWN | UNKNOWN | - | If unavailable | Yes | No | No | - |
| `date_left` | Optional | Leaver cutoff for authority revocation | Plum | HR/Employee Master screen | Date of Leaving/Relieving | UNKNOWN | n/a | n/a | UNKNOWN | UNKNOWN | UNKNOWN | Timeliness of update is critical for `ORA-001` revocation | Yes, until confirmed reliable and timely | Yes | Desirable: effective leaver date recorded promptly | No (interim SharePoint + manual process fills the gap) | High-value improvement candidate #3 below |
| `employment_type` | Optional | Distinguish permanent/contract/vendor crew | Plum | HR/Employee Master screen | Employment Type | UNKNOWN | n/a | UNKNOWN | n/a | UNKNOWN | UNKNOWN | - | If unavailable | Yes | No | No | - |
| `source_department_text` (adapter Source Binding field, section G - see Correction 1 note below) | Optional | Reconciliation aid to Organisation Unit | Plum | HR/Employee Master screen | Department (free text) | UNKNOWN (assumed free text pending verification; not confirmed) | UNKNOWN | UNKNOWN / ASSUMED_NEEDS_VALIDATION - not confirmed absent, only PBL's four named structural gaps are confirmed (ADR-032) | n/a | UNKNOWN | UNKNOWN | Free-text drift, renaming, if assumption holds | Yes, as an adapter-owned reconciliation aid only (never a canonical field - see Correction 1) | No (superseded by `org_unit_id` once matched) | Possible: stable Department code, once verified absent | No | High-value improvement candidate #4 below; verify before treating as a confirmed gap |
| `source_designation_text` (adapter Source Binding field, section G) | Optional | Reconciliation aid to Position/Designation | Plum | HR/Employee Master screen | Designation (free text) | UNKNOWN (assumed free text pending verification; not confirmed) | UNKNOWN | UNKNOWN / ASSUMED_NEEDS_VALIDATION - not confirmed absent | n/a | UNKNOWN | UNKNOWN | Free-text drift, if assumption holds | Yes, as an adapter-owned reconciliation aid only | No (superseded by `designation_code`/`position_id` once matched) | Possible: stable Designation code, once verified absent | No | High-value improvement candidate #5 below; verify before treating as a confirmed gap |
| `source_reporting_manager_text` (adapter Source Binding field, section G) | Optional | Reconciliation aid to reporting line | Plum | HR/Employee Master screen | Reporting Manager (free text name) | UNKNOWN (assumed free text/name pending verification; not confirmed) | UNKNOWN | UNKNOWN / ASSUMED_NEEDS_VALIDATION - not confirmed absent | n/a | UNKNOWN | UNKNOWN | Name-based reference would be fragile if the assumption holds (renames, duplicate names) | Yes, as an adapter-owned reconciliation aid only | No (superseded by `reports_to_position_id` once matched) | Possible: manager stored/retrievable by Employee ID, once verified absent | No | High-value improvement candidate #6 below; verify before treating as a confirmed gap |
| `source_last_updated_at` (adapter Source Binding field, section G) | Optional | Staleness/freshness detection | Plum | n/a | Record last-modified timestamp | UNKNOWN | n/a | n/a | n/a | UNKNOWN / ASSUMED_NEEDS_VALIDATION - not confirmed absent | UNKNOWN | Cannot detect silent Plum edits without this, if the capability is in fact absent | Yes, adapter-side, until Plum's actual capability is verified | Yes | Possible: reliable last-modified/version value, once verified absent | No | High-value improvement candidate #7 below; verify before treating as a confirmed gap |

### Organisation Unit

| Canonical field | Req/Opt | Business reason | Expected source | Plum entity/screen | Plum field | Available in Plum | Stable ID? | Controlled code? | Effective dating? | Last-modified? | Interface/export? | Data-quality concern | SharePoint interim required? | Future shared-master field? | Plum enhancement desirable? | Blocks PF-1A? | Notes/evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `org_unit_id` | Required | Canonical structural identity | Platform-generated (SharePoint Phase 1) | n/a | n/a | NO (confirmed - no structured master exists) | NO | NO | NO | n/a | n/a | Confirmed absent | Yes | Yes | Desirable long-term (structured org master) | No (SharePoint bridges it) | ADR-032 confirmed gap |
| `org_unit_code` / `org_unit_name` / `org_unit_type` / `parent_org_unit_id` | Required | Organisational hierarchy for scope-based authority | Platform-generated (SharePoint Phase 1) | n/a | n/a | NO | NO | NO | NO | n/a | n/a | Confirmed absent as a structured hierarchy | Yes | Yes | Desirable long-term | No | ADR-032 confirmed gap |
| `provider_department_mapping` (adapter Source Binding field, section G, `entity_type = ORG_UNIT`) | Optional | Reconciliation link back to Plum's free-text department | Plum | HR/Employee Master screen | Department (free text) | UNKNOWN (assumed free text pending verification; not confirmed) | No | UNKNOWN / ASSUMED_NEEDS_VALIDATION - not confirmed absent | n/a | UNKNOWN | UNKNOWN | Free-text drift, if assumption holds | n/a (this is the reconciliation field itself) | No | Possible: stable Department code, once verified absent | No | Same as `source_department_text` above; verify before treating as a confirmed gap |

### Position / Position Incumbency

| Canonical field | Req/Opt | Business reason | Expected source | Plum entity/screen | Plum field | Available in Plum | Stable ID? | Controlled code? | Effective dating? | Last-modified? | Interface/export? | Data-quality concern | SharePoint interim required? | Future shared-master field? | Plum enhancement desirable? | Blocks PF-1A? | Notes/evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `position_id` / `position_code` / `reports_to_position_id` | Required | Stable authority-attachment point independent of who currently holds the seat | Platform-generated (SharePoint Phase 1) | n/a | n/a | NO (confirmed - no Position Master; Plum has only Designation-style labels) | NO | NO | NO | n/a | n/a | Confirmed absent | Yes | Yes | Desirable long-term (true Position Master) | No | ADR-032 confirmed gap |
| `incumbency_id` / effective-dated occupancy | Required | Historical authority resolution as of a decision's effective time | Platform-generated (SharePoint Phase 1) | n/a | n/a | NO (confirmed - no incumbency/effective-dating model) | NO | n/a | NO | n/a | n/a | Confirmed absent | Yes | Yes | Desirable long-term | No | ADR-032 confirmed gap |

### Crew / Credential reference (section F)

| Canonical field | Req/Opt | Business reason | Expected source | Plum entity/screen | Plum field | Available in Plum | Stable ID? | Controlled code? | Effective dating? | Last-modified? | Interface/export? | Data-quality concern | SharePoint interim required? | Future shared-master field? | Plum enhancement desirable? | Blocks PF-1A? | Notes/evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `crew_classification` | Optional | Distinguish operator/crew categories for assignment eligibility | Plum (assumed) | HR/Employee or Fleet screen | Crew Category / Role | UNKNOWN | UNKNOWN | UNKNOWN | n/a | UNKNOWN | UNKNOWN | Not yet validated | Only if a genuine gap is demonstrated | Yes | Possible | No (not yet a scheduled dependency) | Must be validated before any interim source is added; do not move wholesale to SharePoint |
| `credential_id` / `credential_type` / `credential_number` / `issuing_authority` | Required for `ELA-001` eligibility | Statutory licence/certification evidence for assignment eligibility | Plum (assumed) | HR/Employee or Compliance screen | Licence/Certification records | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | UNKNOWN | Not yet validated | Only if a genuine gap is demonstrated | Yes | Possible | No | Same as above |
| `valid_from` / `valid_to` / `credential_status` | Required for `ELA-001` eligibility | Expiry-driven hard-block on assignment | Plum (assumed) | HR/Employee or Compliance screen | Licence expiry fields | UNKNOWN | n/a | n/a | UNKNOWN | UNKNOWN | UNKNOWN | Timeliness/accuracy of expiry data is safety-critical | Only if a genuine gap is demonstrated | Yes | Possible | No | Same as above; this is the most safety-sensitive field in this section and should be prioritised for early validation even though it is not yet scheduled |

## Fields that would make the integration simpler

Recorded separately: PBL may ask for these while the new system is built. They are
conveniences, not prerequisites; PF-1A and unrelated functional development must **not** depend on Plum
implementing them first.

```text
1. Stable, immutable Employee ID/code (never reissued/reused).
2. Reliable employment-status code (controlled values, not free text).
3. Effective leaver/termination date recorded promptly.
4. Stable Department code (not free text).
5. Stable Designation code (not free text).
6. Reporting Manager stored/retrievable by Employee ID, not employee name.
7. Reliable last_modified_at / version value on the employee record.
8. A controlled export/API endpoint exposing the above fields.
```

## Concise Plum/vendor question list

For the next Plum/vendor conversation, ask only:

```text
1. What employee identifier do you actually use internally today, and is it ever reused or
   reissued when someone rejoins?
2. What employment-status values exist, and how promptly is a leaver's status/date updated?
3. Is Department stored as a code, a free-text field, or both? If a code exists, is it stable
   over time?
4. Is Designation stored as a code, a free-text field, or both?
5. Is Reporting Manager stored as a reference to another employee record, or only as a name?
6. Does any record carry a reliable last-modified timestamp or version number?
7. Is there any export, report or API that can return the above fields in a structured (not
   printed/PDF) form, and on what schedule?
8. For Crew/Credentials: what licence/certification/expiry fields do you actually hold today, in
   what form, and how are they currently identified against an employee?
```

Do not ask Plum to build or describe an Organisation Unit Master, Position Master, Position
Incumbency model or HR change feed - those are confirmed absent (ADR-032) and are not the subject
of this conversation.

## PF-1A impact

None of the confirmed absences above blocks PF-1A. See `PF_1F_HR_DECISION_GATE.md` for the full gate
statement: PF-1A proceeds once the canonical contract, SharePoint-backed reference fixtures, the
provider-neutral adapter boundary and staleness behaviour are accepted, independent of whether any
Plum enhancement above has been implemented.
