# Eligibility API Contract - machines' certificates, "not applicable" marks, rules and the decision (ELG-1)

Implementation contract for ELG-1 (27 September 2026), the machine half of the Eligibility foundation, and ELG-2 (1
October 2026), its certificate reminders and escalation. The designs and the owner's answers are
`docs/agent/slices/elg-1-machine-eligibility.md` and `docs/agent/slices/elg-2-certificate-reminders.md`; the logical
contract is `ELA-001` (`eligibility-assignment-contract.md`, `APPROVED`), whose machine half this builds. This file
states what the routes accept, return and refuse, and what 8A calls.

```text
backend/app/modules/eligibility/
  contract.py      the codes: kinds, outcomes, basis, lapse, "not applicable", bands, events, record types
  evaluation.py    the decision, pure (no database, no clock): choosing rules, cover, marks, outcomes
  repository.py    its own tables only
  service.py       reads, writes, the check, record_decision (for 8A), Certificates due, rules, the fleet read once
  reminders.py     ELG-2, pure (no database, no clock): reminder days, the steps reached, a short certificate's date
                   and reason, which reminder an outcome raises, the refusals of a setting
  alerts.py        ELG-2: the Alerts, "seen" marks and the reminder settings
  ports.py         ELG-2: AllocationSource, which Resource Assignments registers
  schemas.py, routes.py
```

The module is the **Compliance / Eligibility** row of `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`. It reads the
Equipment Reference only through `equipment_reference.service` - `get_asset_with_fitted_parts` and
`list_active_assets_with_fitted_parts`, and the structure - and keys its records on an asset's public id. The
Equipment Reference never reads it, and its tables do not change. Copies are Slice 9C documents.

"Fleet Admin" means whoever holds `EQUIPMENT_REFERENCE_MANAGE`: Admin, until a Fleet Admin role exists.

## Permissions

| Code | Roles | Guards |
| --- | --- | --- |
| `EQUIPMENT_REFERENCE_READ` | all six | certificates (kind, issuer, dates, status, whether the copy is attached), marks, the check, Certificates due, the rules |
| `EQUIPMENT_IDENTITY_READ` | `ADMIN` | certificate numbers, withdrawal reasons, a mark's reasons, and reading and downloading copies - no route of its own |
| `EQUIPMENT_REFERENCE_MANAGE` | `ADMIN` | recording and withdrawing certificates and marks; attaching copies |
| `ELIGIBILITY_RULE_MANAGE` (new) | `ADMIN` | adding and ending rules (owner, Q7) |

Every route is pinned in `backend/tests/fixtures/post_baseline_tightened_routes.py` (`POST_BASELINE_NEW_ROUTES`).
Granting `ELIGIBILITY_RULE_MANAGE` to a compliance officer, or `EQUIPMENT_IDENTITY_READ` to Operations, needs no
code change.

**Numbers are withheld** from a caller without `EQUIPMENT_IDENTITY_READ`: a certificate's `number` is `null`
with `number_withheld: true`, and its `withdrawn_reason` is `null` too (the Fleet Admin may repeat the number
in it). A mark's `reason` and `withdrawn_reason` are `null` too, with `reason_withheld: true`: they are free
text and may repeat a number. The asset view says `numbers_withheld: true`. Nothing else carries a number: the
check, Certificates due and events never do.

## Conventions

- Errors are `{"detail": "..."}` in plain words: `404` not found, `409` a request key used for another asset,
  a mark already in force, an overlapping rule, a rule already ended on another day; `422` refused; `401` /
  `403` as elsewhere. Unknown request fields are refused (`422`).
- Every create takes a `create_request_key`. The same request again - every field the same, as stored - returns
  what the first made, with `replayed: true` and no event; the key used for anything else is `409`; a key of only
  spaces is `422`, and nothing is written.
- Withdrawing twice, or ending a rule twice on the same day, changes nothing the second time (`event: null`,
  or `replayed: true` for a rule).
- Every write takes the module's one write lock for its transaction.
- Dates are whole days (`YYYY-MM-DD`). "Today" is the day in Asia/Kolkata.

## Reference lists

```text
GET /api/eligibility/jurisdictions         READ   IN, then the 36 states and union territories
GET /api/eligibility/certificate-kinds     READ   the eight kinds
```

A jurisdiction: `jurisdiction_code` (`IN`, or ISO 3166-2:IN such as `IN-GJ`), `jurisdiction_label`,
`jurisdiction_kind_code` (`CENTRAL`, `STATE`, `UNION_TERRITORY`), `gst_state_code`.

A kind: `kind_code`, `kind_label`, `end_date_optional`, `valid_in_required`, `is_examination`,
`states_registration`. The kinds are `REGISTRATION`, `INSURANCE`, `POLLUTION_UNDER_CONTROL`, `ROAD_TAX` (end
optional), `FITNESS`, `PERMIT` (valid in a place), `THOROUGH_EXAMINATION` and `LOAD_TEST` (examinations, end
optional).

## An asset's certificates

```text
GET  /api/eligibility/assets/{asset_public_id}/certificates                   READ     200
POST /api/eligibility/assets/{asset_public_id}/certificates                   MANAGE   201
     {create_request_key, kind_code, number, issued_by, issued_on, valid_from, valid_until,
      valid_in_code, registered_as_code}
POST /api/eligibility/certificates/{certificate_public_id}/withdraw           MANAGE   200   {reason}
POST /api/eligibility/assets/{asset_public_id}/not-applicable                 MANAGE   201
     {create_request_key, kind_code, reason, until}
POST /api/eligibility/not-applicable/{mark_public_id}/withdraw                MANAGE   200   {reason}
```

**The view** (`AssetCertificatesResponse`), for a machine, a fitted part or a piece of kit:

```text
asset                   public id, reference, kind, origin, class and type with labels, machine number,
                        serial number (a piece's own mark), status
fitted_to               the machine a part is fitted to, or null
fitted_parts            the active parts fitted below it
numbers_withheld
statuses[]              one per kind required of the asset today by the baseline rules, then any kind
                        recorded on it that it is not required to hold (a carrier's road papers, which count
                        for its crane): kind, required, rule (public id, jurisdiction, basis, lapse, interval,
                        "not applicable" and its limit, source, note), outcome_code (VALID, RUNS_OUT_SOON,
                        RUN_OUT, MISSING, COPY_MISSING, NOT_APPLICABLE; null where not required),
                        cover_ends_on, the certificate in force and the mark counted
certificates[]          every certificate on the asset and its fitted parts - in force, earlier, withdrawn -
                        newest first, each with in_force and has_copy
marks[]                 every mark on them
recordable_kind_codes   the kinds any rule could require of it, or of the machine a part is fitted to
markable_kinds[]        the kinds a rule in force today allows it to mark and that carry no mark yet, each with
                        the rule letting a mark run longest - all of India's or a jurisdiction's own; no limit,
                        else the longest; of equals, all of India's, then by code - and the latest end a mark
                        recorded today may have under it (null: no limit)
```

A write returns `CertificateActionResponse`: `certificates` (the view of the asset the certificate or mark is
on - a carrier's certificate withdrawn from its crane's page answers with the carrier's view), the new
`certificate_public_id` or `mark_public_id`, `replayed`, `event`.

**A certificate is refused** (`422`) when: its kind is not one any rule could require of the asset; the number
or issuer is blank; it was issued in the future; it runs out before it starts; "valid until" is missing on a
kind that needs one; "valid in" (a state, or `IN` for a national permit) is missing on a permit or given on
another kind; "registered as" (`TRANSPORT`, `NON_TRANSPORT`) is missing on a registration or given on another
kind; the asset is retired. The database holds the same through CHECKs and a composite key carrying the kind's
flags.

**A mark is refused** when no rule in force today allows it for that asset and kind (`422`, "The law is clear
..."); it has no reason; its end is in the past, or missing or later than the most generous rule allows
where every rule allowing one limits how long (the first-year pollution certificate: at most 12 months under all
of India's rule); the asset is retired; or one is already in force for that asset and kind (`409`). It is
recorded under that most generous rule; at a site it counts only where the site's own rule allows it.

**A copy** goes through `POST /api/documents/upload` with `linked_record_type=eligibility_certificate`,
`linked_record_public_id` the certificate's public id and `document_type=CERTIFICATE`. Attaching needs
`EQUIPMENT_REFERENCE_MANAGE`; reading and downloading need `EQUIPMENT_IDENTITY_READ`
(`documents/contract.py`). Through the attach check Eligibility registers with the documents module, a
certificate refuses (`422`) a file of any other type, a link to a file kept elsewhere
(`POST /api/documents/metadata`), and any copy once withdrawn or when unknown. The check takes the module's write
lock, held until the documents module's transaction ends, so a copy and a withdrawal never cross. A certificate counts only with a
copy (Q5): an uploaded `CERTIFICATE` document linked to it, not rejected or archived.

## The check

```text
GET /api/eligibility/assets/{asset_public_id}/check
    ?state_code&central_government_site&period_from&period_to                    READ   200
```

`state_code` a state or union territory (not `IN`); `central_government_site` true at a central public sector
plant, railway, major port, oil field or mine; `period_to` empty for open-ended. A machine is judged with its
active fitted parts, a piece of kit alone; a Plum part is refused (`422`: "A part is checked with the machine it
is fitted to"). Nothing is kept and no event is recorded.

**The answer** (`EligibilityCheckResponse`): the asset, the site, the period, `evaluated_on`, `overall_code`
(`ELIGIBLE`, `WARNING`, `BLOCKED`, `OVERRIDE_REQUIRED`), `valid_until` (the earliest required cover or mark end;
null when none ends or when blocked), `outcome_counts`, and `results[]`: for each certificate required of each
asset of the unit - and the asset's own check when retired (`RETIRED`) - the asset, kind, `outcome_code`,
`effect_code` (`NONE`, `WARNING`, `OVERRIDE`, `BLOCK`), the rule's lapse, basis, public id and jurisdiction
(null: the baseline), the certificate and where it is recorded, the mark, and `cover_ends_on`.

How it is decided is design section 6 and `evaluation.py`:

- **The rule** for each kind: the site's jurisdiction's if in effect on the later of today and the start -
  `IN`'s for the examinations at a central-government site, the state's otherwise - else the baseline's;
  within that, the asset's type before its class. None, or `NOT_REQUIRED`: not required.
- **Transport-only rules** apply when a registration recorded on an asset of the unit says transport (the owner,
  1 October 2026, replacing the cautious reading that applied them whenever no registration stood). A registration
  standing - in force and not run out - today or on the rule day decides: transport if one says so, otherwise not.
  With none standing, a transport registration that has run out still applies them, unless the registration itself
  is marked not applicable by a mark still standing on the rule day and allowed by the registration rule the check
  uses - the site's state's, in effect on the rule day. With no registration recorded, or the last one
  non-transport, they do not apply; the registration itself is still required.
- **A registration in force wins over its mark** (owner, 28 September 2026): while a registration is in force and
  not run out, today or on the rule day, a "not applicable" mark on the registration does not count - the
  registration is judged by the certificate, and the mark is listed as not counted. Once the registration runs
  out or is withdrawn, the mark counts.
- **Cover:** each asset's certificates of a kind (and each permit place's) are their own sequence: the
  certificate not withdrawn with the latest "valid from" on or before today, if it has its copy; until the
  earlier of its "valid until" and, for an examination, its day plus the rule's interval (the day before the
  anniversary). Day by day the certificate in force counts: a renewal takes over on its own start date - also
  one starting before the current one ends; of two starting the same day, the one recorded last - and the cover
  runs through a takeover only when the renewal has its copy and covers its start date. The sequence covering
  longest counts.
- **Outcomes**, first that applies: a mark the rule allows, standing through the period (`NOT_APPLICABLE`, no
  effect) - a mark ending before the start, during the period or with an open-ended period warns as a cover
  would, with the mark named in the result; none in force
  (`MISSING`) or no copy (`COPY_MISSING`) or ended before today (`RUN_OUT`) - the rule's lapse; ends before the
  start (`RUNS_OUT_BEFORE_START`), before the period's end or with an open end (`RUNS_OUT_IN_PERIOD`), or
  within 15 days (`RUNS_OUT_SOON`) - a warning; otherwise `VALID`.
- **Overall:** any block, then any override, then any warning, else eligible.

## For 8A (no route)

```python
service.evaluate_asset(db, asset_public_id=..., state_code=..., central_government_site=...,
                       period_from=..., period_to=...) -> EligibilityCheckResponse
service.record_decision(db, asset_public_id=..., state_code=..., central_government_site=...,
                        period_from=..., period_to=..., requested_by=<user public id>,
                        requested_for_type=None, requested_for_public_id=None)
                        -> (decision_public_id, EligibilityCheckResponse)
```

`record_decision` takes the module's write lock, held until the caller commits or rolls back, and stores the
decision (`eligibility_decision`: asset and its version, site, period, evaluated on
and at, who asked, what for, overall, valid until) and one `eligibility_decision_result` per result, naming the
rule, certificate and mark rows used - never edited, so the decision stays explained - and records
`ELIGIBILITY_EVALUATED`, all in the caller's transaction; the caller commits. It refuses what the check
refuses, and a `requested_for_type` without its id or the reverse. 8A cannot turn `BLOCKED` into an allocation
(`ELA-001`).

8A core (28 September 2026) uses these as written, with `requested_for_type` `resource_assignment` (the machine) or
`resource_assignment_kit` (a piece of kit on a trip) and the allocation's or kit line's public id. It added two
read-only functions, still with no route:

```python
service.jurisdiction_for_state_text(db, text) -> JurisdictionResponse | None
service.get_stored_decisions(db, public_ids) -> dict[str, StoredDecision]
```

- `jurisdiction_for_state_text` matches an address's free-text state to one of the 36 states and union territories
  by its name or its code ("Gujarat", "GJ", "IN-GJ"), ignoring case, spaces and punctuation and reading "&" as
  "and"; `None` when it names none, so the caller asks for the address to be corrected rather than guess. It never
  answers `IN`: a central-government site is a separate answer (`site_central_government` on the Work Order line).
- `get_stored_decisions` returns stored decisions by public id, each with its site, period, evaluated on and at,
  overall, valid until and its results (asset and its reference, kind, outcome, effect, cover end); the rows
  behind each result stay in `eligibility_decision_result`. A stored decision is never edited, so an allocation
  shows what was decided when it was made.

## Certificates due

```text
GET /api/eligibility/certificates-due?band&class_code&kind_code&search&limit&offset      READ   200
```

For every active asset, every certificate its baseline rules require today that is missing, has no copy, has
run out, or runs out within 60 days, and every mark ending within 60 days. Bands: `MISSING`, `COPY_MISSING`,
`RUN_OUT`, `WITHIN_15`, `WITHIN_30`, `WITHIN_60` (an unknown band is `422`). `search` matches the machine
number, reference or a piece's own number. `limit` 1 to 500, default 100. The response: `today`, `band_counts`
(after the class, kind and search filters, before the band filter), `total`, `limit`, `offset`, `items[]`
(asset, kind, band, outcome, cover end, the certificate and where it is recorded - a crane's papers on its
carrier - and the mark). Worked out when read; nothing is stored or sent.

## Rules

```text
GET  /api/eligibility/rules?jurisdiction_code&kind_code&class_code&in_effect_on      READ           200
POST /api/eligibility/rules                                                          RULE_MANAGE    201
     {create_request_key, kind_code, class_code, type_code, applies_when_code, jurisdiction_code,
      effective_from, renew_every_months, basis_code, lapse_code, not_applicable_code,
      not_applicable_max_months, source, note}
POST /api/eligibility/rules/{rule_public_id}/end      {effective_to, reason}         RULE_MANAGE    200
```

`jurisdiction_code=BASELINE` lists the rules for all of India. A rule: its fields, labels, `state_code`
(`IN_EFFECT`, `NOT_YET`, `ENDED`), who recorded and ended it. Ended rules stay listed: past decisions are
explained by them.

**A rule is refused** (`422`) when: its kind, class, type or jurisdiction is unknown; it is statutory with a
lapse other than `BLOCK` or `NOT_REQUIRED`; it is an examination (and required) without an interval, or has an
interval on a kind that states its own end; it allows "not applicable" where nothing is required, or limits a
mark it does not allow; it is a registration rule "only for transport vehicles" (the registration decides
whether those rules apply); it is a rule for the central government's sites (`IN`) for anything but an
examination (road papers follow the site's state there); it has no source. **An overlap** - another rule for the same kind, class, type,
"applies when" and jurisdiction in effect on a common day - is `409`; the database refuses it too (an exclusion
constraint, `btree_gist`). **Ending** before the rule's start is `422`; a rule already ended on another day is
`409`.

The first rules (section 5.4) are loaded by migration `20260908_0044`: 43 baseline rules from 21 November 2025,
every one blocking.

## Events

Source module `eligibility`. Payloads carry public ids, references, codes, dates and counts only - never a
certificate or machine number, an issuer, a source text or a reason's text. A certificate's and a mark's events
carry fixed reasons (the Fleet Admin's may repeat a number, and stay on the record); a rule's ending carries the
reason given.

| Event | Record type | Payload |
| --- | --- | --- |
| `ELIGIBILITY_CERTIFICATE_RECORDED` | `eligibility_certificate` | asset public id and reference, kind, issued on, valid from and until, valid in, registered as |
| `ELIGIBILITY_CERTIFICATE_WITHDRAWN` | `eligibility_certificate` | asset public id and reference, kind. Its reason is fixed: the Fleet Admin's may repeat the number, and stays on the certificate |
| `ELIGIBILITY_NOT_APPLICABLE_RECORDED`, `ELIGIBILITY_NOT_APPLICABLE_WITHDRAWN` | `eligibility_not_applicable` | asset public id and reference, kind, until, the rule that allowed it. Their reasons are fixed: the Fleet Admin's stay on the mark |
| `ELIGIBILITY_RULE_RECORDED`, `ELIGIBILITY_RULE_ENDED` | `eligibility_rule` | kind, class, type, applies when, jurisdiction, dates, interval, basis, lapse, "not applicable" and its limit |
| `ELIGIBILITY_EVALUATED` | `eligibility_decision` | decision public id, asset, version, site, period, overall, valid until, the count of each outcome, what asked for it |

Attaching a copy records `DocumentUploaded`, as every upload does.

## Data (migration `20260908_0044_machine_eligibility`)

`eligibility_jurisdiction` (37 rows), `eligibility_certificate_kind` (8), `eligibility_certificate`,
`eligibility_not_applicable` (at most one in force per asset and kind), `eligibility_rule` (the exclusion
constraint `ex_eligibility_rule_overlap`), `eligibility_decision`, `eligibility_decision_result`; the permission
`ELIGIBILITY_RULE_MANAGE` granted to Admin. Records key on `equipment_asset.asset_public_id`,
`equipment_class.class_code` and `equipment_type (class_code, type_code)`. The downgrade removes the tables, the
permission and `btree_gist`; copies stay in the documents table, unreadable by the revision below.

## Reminders and escalation (ELG-2)

Design: `docs/agent/slices/elg-2-certificate-reminders.md` (agreed 1 October 2026). The reminders are **worked out
each time they are read**; what is stored is each kind of reminder's settings, versioned, and people's "seen" marks.
Nothing is sent: the screen is the only channel until the notification service (`NTF-001`) is built.

**Five kinds of reminder** (`reminder_kind_code`) - four since ELG-2, and since HOL-1 a fifth, about PBL's holiday
calendar rather than a machine:

| Code | Label | Raised for |
| --- | --- | --- |
| `CERTIFICATE_RUNNING_OUT` | A certificate running out | every active asset, by the baseline rules today (Certificates due's results, out to the schedule's reach): a cover run out or ending within reach, a mark ending or ended or withdrawn, a renewal recorded without its copy |
| `NOT_YET_RECORDED` | A certificate not yet recorded | the same assets: a certificate required that has not been recorded with its copy since it became needed - the machine added, the rule in effect, the registration saying transport (Q19a) |
| `BEFORE_JOB_STARTS` | Runs out before the job starts | a machine held on an allocation not yet started, or a piece listed on one of its trips, judged for the allocation's site and days: `RUNS_OUT_BEFORE_START`, and `RUN_OUT`, `MISSING`, `COPY_MISSING` while the first day is after today |
| `DURING_JOB` | Runs out during the job | the same: `RUNS_OUT_IN_PERIOD`, and `RUN_OUT`, `MISSING`, `COPY_MISSING` once the job has started |
| `HOLIDAY_CALENDAR_NOT_SET_UP` | PBL's holiday calendar not set up | HOL-1, Q2: this year and next, each until Admin marks it complete in PBL's holiday calendar (`holiday-calendar-api-contract.md`); only years the calendar keeps, 2000 to 2100 |

Held allocations whose last day has not passed, and their listed kit lines with days left, are read through
`ports.AllocationSource`, which Resource Assignments registers when loaded (`resource-assignment-api-contract.md`);
with none registered, reading the reminders fails (fail closed). An allocation whose site cannot be judged, and a
retired machine, raise no allocation reminder. Everything is judged against **one** reading of the fleet's evidence
(`service.read_fleet`, which Certificates due now uses too; what it returns is unchanged).

**A reminder's date and reason** (`date_on`, `reason_code`): `RUNS_OUT` (the cover's last day), `MARK_ENDS` (the
mark's last day), `MARK_WITHDRAWN` (the day it was withdrawn) - for a mark ended or withdrawn, only one that stood for
the requirement: the rule in force on its last day allowed marks, within its limit on how long - `COPY_MISSING` (the day the cover before an uncopied
certificate ends - for one in force, or a renewal recorded ahead whose missing copy ends the cover the day before it
takes over - so a renewal without its copy changes the reason, not the date; walking back through any before it also
without its copy, so further ones leave the date as it was; with no cover before them, the day before the first takes
over),
`CALENDAR_NOT_COMPLETE` (HOL-1: 1 January of the year), `MACHINE_ADDED` (the day the asset was added to the Equipment Master), `RULE_IN_EFFECT` (the day the rule took
effect, walking back through a predecessor of the same scope ending the day before), `REGISTERED_TRANSPORT` (the day
the transport registration took effect - in force today, or, for a job, on the day its rules are chosen for). Of several, the latest; on a tie, not one of the "not yet recorded" reasons,
which are the last three.

**Reminder days.** A schedule is bands of `from_days_before` (negative: after the date) and `every_days`; each band
runs to the next, the last runs on. The reminder days are those from the day the reminder began (`began_on`: the asset
added; the allocation or kit line recorded; for a calendar year, the day the reminder came with the package - its
setting's first version, loaded by migration `20260908_0047` - so the year then running is reminded from that day, not
from before the calendar existed), and that day too when it falls inside the schedule's reach (flagged at once). `reminder_on` is the latest up to today; `reminders_so_far` counts them. A step reaches its audience from the
first reminder day, or from `from_days_before` days before the date if later. A person sees a reminder when one of
their roles is on a step reached by today; the allocation reminders also need `RESOURCE_ASSIGNMENT_READ`.

```text
GET  /api/eligibility/alerts?reminder_kind_code&unseen_only&search&limit&offset     READ          200
GET  /api/eligibility/alerts/count                                                 READ          200
POST /api/eligibility/alerts/seen        {items: [{reminder_key, reminder_on}]}     READ          200
GET  /api/eligibility/alert-settings                                               READ          200
POST /api/eligibility/alert-settings/{reminder_kind_code}                          RULE_MANAGE   201
     {expected_version, bands: [{from_days_before, every_days}],
      steps: [{role_code, starts_code, from_days_before, channel_codes}]}
```

- **`GET /alerts`**: `today`; `counts` (`total`, `unseen`, `by_kind`) of what has reached the caller, before the
  filters; `total`, `limit` (1 to 500, default 100), `offset`; `items[]`, earliest date first: `reminder_key` (the
  kind, what it is about, the asset, the certificate kind and the date, joined by `|`), `reminder_kind_code` and
  label, the asset (`AssetSummary`; `null` for a calendar reminder), `certificate_asset_reference` (a carrier holding the crane's paper), the kind
  and its label, `outcome_code`, `date_on`, `reason_code`, `mark_public_id`, `allocation` (allocation, Work Order,
  line, unit, trip and kit line, site, days) or `null`, `calendar_year` (HOL-1: the year a calendar reminder is about;
  `null` otherwise), `began_on`, `first_reminder_on`, `reminder_on`,
  `reminders_so_far`, `reached[]` (step, role and label, `reached_on`), `seen_by_me`, `seen_by[]` (display name,
  time) on the current reminder day. `search` matches the machine number, reference, a piece's own number, the Work
  Order code and the allocation reference - and a calendar reminder's year or label. A calendar reminder's key is
  `HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|<year>|||<year>-01-01`: no asset and no certificate kind, and its
  kind, certificate kind and outcome read as empty strings. An unknown `reminder_kind_code` is `422`. No answer carries a
  certificate's number, issuer or reason, or a mark's reason.
- **`GET /alerts/count`**: `{unseen, total}`, as the list's counts.
- **`POST /alerts/seen`**: marks each reminder seen by the caller on its current reminder day - all or none. `404` a
  reminder that has not reached the caller; `409` one whose current reminder day is not the one sent; `422` none
  sent; at most 200. A mark already made changes nothing: `{marked, already}`. No business event: the mark is the
  record. Under `EQUIPMENT_REFERENCE_READ` because it writes only the person's own mark. The reminders are worked out
  under Resource Assignments' lock (taken through the port's `hold`), the Equipment Reference's
  (`hold_equipment_writes`), the holiday calendar's (HOL-1, through `ports.CalendarYearSource.hold`; a calendar save
  takes no other of these locks) and then this module's - the locks the writes that change a reminder take, in an order
  no write reverses - so a certificate or its copy, a mark, rule or setting, an allocation, its dates or kit, or an asset
  retired, fitted or re-mapped meanwhile is seen, or waits. A Work Order line's site changed in the same instant is not
  serialized: a mark made then records that the person saw that reminder - its key - on that day, which is true.
- **`GET /alert-settings`**: `settings[]`, one per kind in the order above - `current` and `earlier` versions (newest
  first), each with its bands, steps (with role labels), who saved it and when (`saved_by` empty: loaded with the
  package) - `roles` (the active roles a step may name) and `channel_codes` (`SCREEN`).
- **`POST /alert-settings/{kind}`**: a new version (`201`, with `ELIGIBILITY_ALERT_SETTING_CHANGED`); the same as the
  current one is `200` with `unchanged: true` and no event; `404` an unknown kind; `409` `expected_version` not the
  current one; `422` refused: no band or more than 10; a band starting more than 365 days before or after the date or
  repeating less than every day or more than every 365; two bands on the same day; no band on or after the date; no
  step or more than 10; a role unknown, inactive or on two steps; a first step not from the first reminder; a step
  starting before the first band or more than 365 days after; days given for a step from the first reminder, or
  missing for one from some days; a channel other than `SCREEN`. Under the module's write lock.

**Events.** `ELIGIBILITY_ALERT_SETTING_CHANGED`, record type `eligibility_alert_setting`, record id the new version's
public id: the kind, the version before and after, the bands and the steps (role, start, days, channels). Its reason
is fixed ("Reminder setting changed.").

**HOL-1 (migration `20260908_0047_holiday_calendar`):** the fifth kind joins the setting and "seen" CHECKs, with version
1 of its setting - the standard schedule counted to 1 January of the year; Admin from the first reminder, Management
from 1 January. A "seen" mark gains the subject type `holiday_calendar_year`; its asset and certificate kind are empty
for that subject and only for it, its subject is the year, its date 1 January of that year (a CHECK by subject), and the
key is compared whole: exactly its six parts joined by `|` - the asset and certificate kind parts empty when they are -
and nothing more. (0046 compared it part by part, and an empty seventh part reads the same as none, so a key ending
`|`, or `||` and more, passed and could sit beside the real one; HOL-1's review, HOL1-R2-002.) Which years are not
complete is read through `ports.CalendarYearSource`, which the holiday calendar registers when loaded; with none
registered, reading the reminders fails (fail closed). The downgrade removes the fifth kind's settings and marks and
puts the CHECKs back exactly as 0046 had them.

**Data (migration `20260908_0046_certificate_reminders`):** `eligibility_alert_setting` (unique kind and version;
`saved_by` a key to the user, empty for the loaded versions), `eligibility_alert_band` (CHECKs on the days; unique band
number and start per setting), `eligibility_alert_step` (role a key to `role.role_code`; days given exactly with
`DAYS_BEFORE`; channels non-empty and `SCREEN` only; unique step number and role per setting),
`eligibility_alert_acknowledgement` (asset and certificate kind keys; what it is about by type and public id, no key;
`reminder_date_on`, the date the reminder is about; the key's parts must be exactly its kind, subject type, subject,
asset, certificate kind and that date as `YYYY-MM-DD`; unique key, reminder day and person), and version 1 of each
kind: the standard schedule (60/30, 15/7, 7/1, 0/1) and paths (Admin from the first reminder; Operations from 15 days
before, or from the first reminder on a job; Management from 7 days before), and for `NOT_YET_RECORDED` every day from
the date, Operations 7 and Management 14 days after it. The downgrade drops the four tables. `AssetFacts` (the
Equipment Reference's read for Eligibility) gains `added_on`; its tables do not change.
