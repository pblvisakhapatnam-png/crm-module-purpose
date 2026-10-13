# Resource Assignment API Contract - own machines allocated to the resource requirements (8A core)

Implementation contract for 8A core (28 September 2026). The design and the owner's answers are
`docs/agent/slices/8a-core-equipment-allocation.md`; the logical contracts are `RPA-001`
(`resource-planning-assignment-contract.md`, `APPROVED`), whose Availability and Assignment halves this builds for
owned machines, `WRR-001` and `ELA-001`. This file states what the routes accept, return and refuse.

```text
backend/app/modules/resource_assignments/
  contract.py     statuses, reasons, billing cycles, warnings, compliance states, events, record types
  rules.py        pure: busy days, a unit's coverage, a machine meeting a requirement, candidate order,
                  the counted-set arithmetic - no database, no clock
  repository.py   its own four tables only: allocations, trips, kit lines and the request-key registry
  views.py        reading: the site, finding machines, answers, an allocation as shown, the kit options
  service.py      writing, and the port Resource Requirements reads coverage and frees machines through
  errors.py, schemas.py, routes.py
```

The code says *assignment* (`RPA-001`'s word); the screens say **allocation**, the word Eligibility's answers use
("can be allocated"). The reference is `AL-000001`.

**Boundaries.** It reads the requirement - and through it the Work Order line, its site and the contract - through
`resource_requirements.service`; machines and kit through `equipment_reference.service` (`machines_for_allocation`,
`allocation_asset`, `kit_for_machine`); answers through `eligibility.service` (`evaluate_asset`, `record_decision`,
`get_stored_decisions`, `jurisdiction_for_state_text`). It writes none of their tables. Resource Requirements never
imports it: this module registers `resource_requirements.ports.AssignmentPort` when it is loaded (`app.main` loads
it), and with none registered a requirement is neither read nor cancelled (fail closed). The port reads coverage,
frees a cancelled requirement's machines, and takes this module's write lock (`hold`) for Resource Requirements
before it reads coverage to store a status - after the Work Order's and the requirement's locks, the order below -
so a status is never worked out from an allocation write still in progress (independent review, 8A-FA-001).

## Permissions

| Code | Roles | Guards |
| --- | --- | --- |
| `RESOURCE_ASSIGNMENT_READ` (new) | the six roles (as `WORK_ORDER_READ`) | the list, one allocation, finding machines, the kit options |
| `RESOURCE_ASSIGNMENT_WRITE` (new) | `ADMIN`, `OPERATIONS_USER` | allocating, replacing, freeing, changing dates, checking again, trips and kit |
| `WORK_ORDER_LINE_BILLING_TERMS_WRITE` (exists) | Admin, Sales User, Sales Manager, Operations | the billing-cycle route; and a billing cycle sent when allocating or replacing (`403` without it) |

Every route is pinned in `backend/tests/fixtures/post_baseline_tightened_routes.py` (`POST_BASELINE_NEW_ROUTES`).

## Conventions

- Errors are `{"detail": "..."}` in plain words: `404` not found; `409` a stale version, a machine, piece or unit
  taken on some of the days, a warning not accepted, or a request key used for something else; `422` refused;
  `403` a permission missing. Unknown request fields are refused (`422`).
- A create takes a `create_request_key`: the same request again returns the first result with `replayed: true`
  and no event; the key used for anything else - another kind of request included - is `409`; a key of only spaces
  is `422`. "The same request" is the same kind (allocating, replacing or listing kit), the same fields sent with the
  same values - leaving a field out and sending it empty differ - and, for a replacement or kit, the same
  allocation. One table, `resource_assignment_request`, holds each key once across the three kinds with its kind
  and the request's SHA-256. Since 8 October 2026 (TB-1 TB1-102 part b) the SHA-256 is computed by
  `app/shared/request_keys.py`, which Equipment Reference's model and kit creates and Resource Requirements' create
  use too; it gives exactly what this module gave before, so a fingerprint already stored still matches.
- Every other write takes `expected_assignment_version`; a stale one is `409` ("Someone else changed this
  allocation after you opened it").
- Dates are whole days (`YYYY-MM-DD`); "today" is the day in Asia/Kolkata. A period's days are both ends
  included; an empty end runs on.
- Locks are always taken in one order: the Work Order's row, shared (`hold_work_order_status`, `FOR SHARE`); the
  requirement's row (`SELECT ... FOR UPDATE`); this module's write lock (a transaction advisory lock); Eligibility's
  (`record_decision`). Every write takes all of them in that order - the Work Order's first, so a change to the
  Work Order, its closure included, waits for the write or is seen by it. So do Resource Requirements' own writes
  (creating, changing and cancelling a requirement), and the end-dates listener runs inside a Work Order write that
  already holds the row; each takes this module's lock through the port before reading coverage for a status. A closed Work Order refuses every write - one that would change nothing, and a request
  replayed, included.
- Writes answer with `AssignmentActionResponse`: `assignment` (the allocation as it now stands), `replaced` (on a
  replacement, the one replaced), `replayed`, `events[]`.

## Routes

```text
GET  /api/resource-assignments?work_order_public_id&requirement_public_id&machine_public_id
                              &status_code&starts_from&starts_to&limit&offset&after          READ   200
GET  /api/resource-assignments/candidates?requirement_public_id&unit_number&period_from&period_to
                                          &replacing_assignment_public_id                    READ   200
GET  /api/resource-assignments/{id}                                                          READ   200
POST /api/resource-assignments                                                               WRITE  201
POST /api/resource-assignments/{id}/replace                                                  WRITE  201
POST /api/resource-assignments/{id}/release                                                  WRITE  200
PUT  /api/resource-assignments/{id}/dates                                                    WRITE  200
POST /api/resource-assignments/{id}/check                                                    WRITE  200
PUT  /api/resource-assignments/{id}/billing-cycle                              BILLING_TERMS_WRITE  200
GET  /api/resource-assignments/{id}/kit-options?trip_number                                  READ   200
POST /api/resource-assignments/{id}/trips                                                    WRITE  201
PUT  /api/resource-assignments/{id}/trips/{trip_number}/note                                 WRITE  200
POST /api/resource-assignments/{id}/kit                                                      WRITE  201
POST /api/resource-assignments/{id}/kit/{kit_line_id}/remove                                 WRITE  200
```

`/candidates` is registered before `/{id}`.

## The site

Read live from the requirement's line (Slice 7C): the site address on the Account and the line's
`site_central_government` answer. Its state is matched to one of Eligibility's 36 states and union territories by
name or code, ignoring case, spaces and punctuation ("Gujarat", "GJ", "IN-GJ"). `SiteFacts` gives the site, the
state as written and as matched, the central-government answer, and - when one of them is missing - its
`problem_code` (`SITE_NOT_RECORDED`, `STATE_NOT_RECOGNISED`, `CENTRAL_NOT_ANSWERED`) and a message naming the line.
Every write that asks Eligibility refuses (`422`) with that message; the finder answers with no eligibility.

## Finding machines

`GET /candidates`. `unit_number` must be 1 to the units required (`422`); a cancelled requirement is `422`. The
period defaults to the unit's first day not yet covered to the requirement's end - its own, else its line's, else
the contract's fixed end - and is checked as an allocation's is. `replacing_assignment_public_id` names an
allocation being replaced: it must be held and on the unit asked (`422` otherwise); its days do not count against
the unit, and the period defaults to its own days, to its end: before its first day, from that day; once started (its
first day on or before today, India date), from today - or its last day if that has passed - and never earlier than
the day after its first day, since a started allocation keeps its first day.

The response (`CandidatesResponse`): the requirement (`RequirementBrief`), the unit, the period, the site,
`unit_conflicts[]` (allocations already filling the unit on some of the days), `candidates[]` and `left_out`.

- A **candidate** is an active machine of the requirement's class whose type is the one asked (where one is), and
  whose own value - else its model's rating - meets every capability asked: a least value by one at least as large,
  a choice by the same choice. Each carries the machine (`AssetBrief`), `available`, `conflicts[]` (the allocations
  keeping it on some of the days, with their Work Order and days) and, when free and the site can be judged,
  today's `answer` (`evaluate_asset`; nothing is stored).
- **Left out**, counted by reason: `TYPE_UNKNOWN` (the requirement names a type and the machine's is not known),
  `RATING_UNKNOWN` (no value for a capability asked), `BELOW_REQUIREMENT`. Another type is not counted.
- **Order**, advisory only: free first; then can be allocated, with a warning, the rest; the smallest key capability
  first; then the registration.

## Allocating

`POST /api/resource-assignments` - `AssignmentCreate`:

```json
{
  "create_request_key": "one per form",
  "requirement_public_id": "...",
  "unit_number": 1,
  "machine_public_id": "...",
  "planned_from": "2026-10-03",
  "planned_to": "2026-11-27",
  "billing_cycle_code": "MONTHLY",
  "notes": "optional, up to 2000",
  "accept_warnings": false
}
```

Refused, each with a message naming what is wrong:

- `404` the requirement or the machine unknown;
- `422` the requirement cancelled or its Work Order closed; the unit outside 1 to the units required; the period
  before the requirement's start, after its end, or ending before it starts; the site's facts missing (above); the
  machine not a machine (kit goes on a trip; a part with its machine), retired, or not meeting the requirement;
  eligibility `BLOCKED` or `OVERRIDE_REQUIRED`, naming every result that stops it ("needs an approval that cannot be
  given yet" for an `OVERRIDE` result); a billing cycle other than `WEEKLY` or `MONTHLY`;
- `409` the machine kept by another allocation on some of the days (naming it, its Work Order and days); the unit
  filled on some of the days; a `WARNING` answer without `accept_warnings`, naming the warnings; the database's
  exclusion constraints, when two saves race ("Someone has just allocated this machine ...");
- `403` a billing cycle sent without `WORK_ORDER_LINE_BILLING_TERMS_WRITE`.

An empty `planned_to` means until the requirement's end, which is what is stored; it may stay empty only when
nothing bounds the requirement. The decision is stored by `record_decision` in the same transaction,
`requested_for_type: resource_assignment` and the new allocation's public id; a refusal rolls it back. The
allocation is written `HELD`, with trip 1, and the requirement's status is refreshed.

## An allocation

`AssignmentResponse`:

```text
assignment_public_id, assignment_reference, assignment_status_code (HELD | REPLACED | RELEASED)
requirement             RequirementBrief: reference, status, version, units required, covered and remaining,
                        required from and to, planned_end, class, type and capabilities asked, the Work Order's
                        status
unit_number, work_order_public_id, work_order_code, work_order_line_public_id, work_order_line_number,
source_offer_line_public_id
machine                 AssetBrief, as it stands now
allocated_machine_number, allocated_class_code, allocated_type_code, allocated_model_public_id,
allocated_asset_version                        the machine as allocated (RMR-001)
planned_from, planned_to, ended_on, effective_to (the last day it keeps the machine; empty: runs on)
billing_cycle_code, billing_cycle_set_by(+display name), billing_cycle_set_at
decision                Answer: the stored decision - its public id, answer, valid until, evaluated on, the site
                        and period it was for, and each result (asset, kind, outcome, effect, cover end)
today                   Answer worked out now for the site as it now is; empty when not held, the period is over,
                        or the site cannot be judged
compliance_state_code   CLEAR | WARNING | BLOCKED | SITE_UNKNOWN - the worst of the machine's and its listed
                        kit's today answers, in lists as on the page; empty when not held or over
warnings[]              SITE_CHANGED, OUTSIDE_REQUIREMENT, NO_LONGER_MATCHES, UNIT_NOT_REQUIRED, OUTSIDE_CONTRACT,
                        BILLING_CYCLE_NOT_STATED, KIT_DOES_NOT_FIT, ANSWER_CHANGED - only on a held one
site                    SiteFacts
replaces, replaced_by   AssignmentLink: reference, machine reference and registration, days
end_reason_code, end_note, ended_by(+display name), ended_at
trips[]                 on one allocation only: trip number, the day it goes (trip 1: the allocation's first),
                        note (what the load carries),
                        kit[]: the piece (AssetBrief), quantity, LISTED | REMOVED (who, when), busy from and to,
                        fits_machine, the stored decision and today's answer
kit_pieces_listed, notes, assignment_version, created and updated by (+display names) and at
```

The list (`GET /api/resource-assignments`) filters by Work Order, requirement, machine, status (`HELD`, `REPLACED`,
`RELEASED`; another is `422`) and start dates, in the order the allocations were recorded - an order no later write
changes; `limit` 1 to 200, default 100. `after` (an allocation's public id; an unknown one is `422`) returns only
those recorded after it: the next page. The screens fetch page after page, each after the last row read, until one
comes back short, so no list stops at a page, and a row changing or leaving the filter between two pages makes no
other row skipped or read twice (independent review, 8A-FB-004) - as `offset`, kept for callers that page by count,
would. The screens order the rows for display: held first, then by first day, Work Order, line and unit.

## Replacing, freeing, changing dates

- **Replace** (`AssignmentReplace`): `create_request_key`, `expected_assignment_version`, `machine_public_id`,
  `replace_from`, `planned_to` (left out: the old end; sent empty: until the requirement ends),
  `billing_cycle_code` (left out: the old one's), `reason_code` (`BREAKDOWN`, `COMPLIANCE`, `CUSTOMER_REQUEST`,
  `PLANNING`, `OTHER` with a `note`), `accept_warnings`. The first day must be a day of the old allocation, and
  once the old one's first day has come (on or before today, India date) a later day than its first: `422` saying
  to free it as recorded by mistake instead if it was (owner, 1 October 2026). The old one becomes `REPLACED`, ending the day before (with no days when replaced from its first); its kit lines end
  with it. The new one is checked as a new allocation, on the same unit, with `replaces` set. A held allocation is
  replaced once; the same machine is `422`.
- **Free** (`AssignmentRelease`): `last_day` (empty: it never goes; else a day of it), `reason_code`
  (`NOT_NEEDED`, `RECORDED_BY_MISTAKE`, `MACHINE_UNAVAILABLE`, `OTHER` with a `note`). Once its first day has come
  (on or before today, India date), `last_day` may be empty only with `RECORDED_BY_MISTAKE`; otherwise `422` asking
  for the last day, so the days it held stay on the record (owner, 1 October 2026). It becomes `RELEASED`; its
  kit lines end with it. `REQUIREMENT_CANCELLED` is set only by a requirement's cancellation.
- **Change dates** (`AssignmentDates`): checked as a new allocation, against every other allocation of the machine
  and of the unit, and its listed kit against the pieces' other lines; every later trip, with kit or without,
  must stay within them (`422` naming the trip: a Trip (Own Load) cannot be moved or removed yet). Fresh decisions for
  the machine and every listed piece; a blocked one refuses, a warning needs `accept_warnings`. The same dates again
  record nothing. Once its first day has come (on or before today, India date), the first day cannot change - only
  the last day: `422` saying to free it as recorded by mistake instead if it was (owner, 1 October 2026; TB-1 finding
  TB1-306, 4 October 2026).

## Checking again, the billing cycle

- **Check** (`AssignmentVersion`): stores a fresh decision for the machine and every listed piece, for the site as
  it now is - a `BLOCKED` one too: the allocation stays held and shows it.
- **Billing cycle** (`AssignmentBillingCycle`): `WEEKLY`, `MONTHLY` or empty (not stated yet); the same value again
  records nothing.

Every write on a replaced or freed allocation is `422`, and every write on an allocation of a closed Work Order -
one that would change nothing included.

## Trips (Own Load) and kit

A trip is shown as a **Trip (Own Load)** (owner, 29 September 2026): one load going to site for the allocation. A crane
may go in several - broken down into its parts - so an allocation has as many trips as it needs, several on one day
if need be; each says in its note what it carries (which part of the machine), and lists its kit. Trip 1 is written
with the allocation, on its first day; it is not "the machine". The field and route names stay `trip`.

- **Kit options** (`GET .../kit-options?trip_number`): the window is the trip's day to the allocation's end (a trip
  after the allocation's last day - it ended early - is `422`: no kit can be listed on it); the
  pieces are the active pieces of the kit models that fit the machine's model (none when it has no model:
  `machine_has_model: false`). Each has `available`, `quantity_free` (a counted set's quantity less the most listed
  on any one day of the window; 1 or 0 for a piece tracked one by one), `conflicts[]`, and today's `answer` when
  free. `assignment_version` is the allocation's version the options were worked out for: the screen shows them only
  under that version, and reads them again when the allocation changes (independent review, 8A-FB2-003).
- **A trip** (`TripCreate`): `goes_on` a day of the allocation, its first included (`422` otherwise), `note` - what
  the load carries - up to 500. Numbered next.
- **What a trip carries** (`TripNote`, `PUT .../trips/{trip_number}/note`): `expected_assignment_version`, `note` up to
  500 (empty clears it); `404` for a trip the allocation does not have. Only the note changes - the trip's day, and
  its kit's days, stay; the same note again records nothing. Written as every other write: refused on an allocation
  no longer held (`422`) or a closed Work Order (`422`), the version moves on.
- **Kit** (`KitAdd`): `create_request_key` (one lot), `expected_assignment_version`, `trip_number` (`404` unknown), `pieces[{piece_public_id,
  quantity}]` (1 to 50, none twice), `accept_warnings`. Each piece must be active kit held for the machine's model
  (`422`), a piece tracked one by one listed with 1 (`422`), and free over its days (`409`); each gets its own
  decision (`requested_for_type: resource_assignment_kit`), judged as a machine's is. The database refuses a piece
  tracked one by one on two listed lines on a common day.
- **Remove** (`AssignmentVersion`): the line becomes `REMOVED`, kept; removing it again records nothing.

## Resource Requirements, changed

- `requirement_status_code`: `OPEN`, `PARTLY_FULFILLED`, `FULFILLED`, `CANCELLED`. A unit is covered when the days
  its allocations kept - held, replaced or freed - cover every day of the requirement's period (an open-ended one
  needs an open-ended allocation at the end of the chain); OPEN when no unit has a machine, FULFILLED when every unit
  is covered, PARTLY_FULFILLED otherwise. Refreshed in the same transaction as every allocation write, every
  requirement change, and every Work Order write that moves the end a requirement without its own runs to (below);
  a change records `ResourceRequirementFulfilmentChanged`. It is not a user's edit: the version and who last
  changed the requirement stay as they are.
- `units_covered` and `units_remaining` on every requirement; `line.site_central_government`.
- The list's `status_code` takes `NEEDS_MACHINES` (open and partly allocated), or any of the four statuses.
- A requirement that is not cancelled may be changed and cancelled. A change is never refused because of its
  allocations; an allocation that no longer fits shows a warning. **Cancelling frees every held machine** in the
  same transaction (each `RELEASED`, `REQUIREMENT_CANCELLED`, from the day before its start, or today if started);
  the response's `machines_freed` says how many.

## Events

Source module `resource_assignments`, record type `resource_assignment`. Payloads carry public ids, references,
codes, dates, versions and counts - never a registration, a note or a reason's text; the event's reason is a fixed
sentence.

| Event | Payload |
| --- | --- |
| `RESOURCE_ASSIGNMENT_HELD` | allocation, requirement, Work Order, line and source offer line ids; unit; machine id, reference and version; dates; billing cycle; decision id and answer; the allocation it replaces |
| `RESOURCE_ASSIGNMENT_REPLACED` | the ids; the replacing allocation; the first day replaced; the day it ended; the reason code |
| `RESOURCE_ASSIGNMENT_RELEASED` | the ids; the last day, or `never_on_the_job`; the reason code |
| `RESOURCE_ASSIGNMENT_DATES_CHANGED` | the ids; dates before and after; the new decision's id and answer; kit lines checked |
| `RESOURCE_ASSIGNMENT_CHECKED` | the ids; decision ids before and after; the answer; kit lines checked and their answers counted |
| `RESOURCE_ASSIGNMENT_BILLING_CYCLE_SET` | the ids; the cycle before and after |
| `RESOURCE_ASSIGNMENT_TRIP_ADDED` | the ids; trip number and day |
| `RESOURCE_ASSIGNMENT_TRIP_NOTE_CHANGED` | the ids; trip number, and whether a note is now given - not the note, as an allocation's notes are not |
| `RESOURCE_ASSIGNMENT_KIT_LISTED` | the ids; trip; each line's id, piece id and reference, quantity, decision id and answer |
| `RESOURCE_ASSIGNMENT_KIT_REMOVED` | the ids; the line, piece, trip and quantity |
| `ResourceRequirementFulfilmentChanged` (requirements) | reference, Work Order and line ids, status, units required, covered and remaining |
| `ELIGIBILITY_EVALUATED` (exists) | one per stored decision |

## Data (migration `20260908_0045_equipment_allocation`)

`resource_assignment` (`AL-` reference generated; foreign keys by public id to `resource_requirement`,
`equipment_asset` and `eligibility_decision`; the generated `busy_range`; the exclusion constraints
`ex_resource_assignment_machine_overlap` and `ex_resource_assignment_unit_overlap`; CHECKs on every code, the unit,
`units_fulfilled = 1`, dates in order, the end fields present exactly when replaced or freed, the reason fitting the
status, `OTHER` with a note, the day it ended within its days), `resource_assignment_trip` (trip 1 with no day of
its own), `resource_assignment_kit` (a counted quantity only on a counted set; `ex_resource_assignment_kit_piece_overlap`
on listed pieces tracked one by one); `resource_requirement`'s status CHECK accepting `PARTLY_FULFILLED` and
`FULFILLED`; `crm_work_order_line_detail.site_central_government`; the two permissions and their grants;
`resource_assignment_request` (each request key once, its kind, the requirement it belongs to and its SHA-256,
checked). A kit line's tracking is its piece's class's (the trigger `resource_assignment_kit_matches_tracking`), and
its days are its trip's day (trip 1: the allocation's first) to its allocation's end, derived by the trigger
`resource_assignment_kit_days` whatever a write sends; a change to an allocation's dates or end, or to a trip's day,
moves its lines in the same statement. A later trip goes on a day of its allocation's planned period, and a change to
the period may not leave one outside it (`resource_assignment_trip_within_allocation`); replacing or freeing an
allocation early may end it before a later trip, whose kit then has no days. Every statement changing or removing an
allocation (any column), or adding, changing or removing a trip or a kit line, first takes the module's own transaction
lock (`WRITE_LOCK_KEY`), in a
statement-level trigger that runs before any row is locked (`resource_assignment_serialize`): two transactions
writing an allocation and its trips or kit are serialized even when one bypasses the service, in the service's own
order - the lock, then the rows - so neither can deadlock the other. Adding an allocation takes no part: it reads
no other table's dates, the exclusion constraints decide overlaps, and its foreign key locks the requirement's row,
which the service takes before the lock. The requirement an allocation fills never changes
(`resource_assignment_keeps_its_requirement`). An allocation is added, changed or removed only in a transaction the
service marks as its own - a transaction-local setting, `pbl.resource_assignment_writer`, set with the module's lock -
because the service keeps the requirement's stored status in step in the same transaction; any other statement on
allocations is refused (`resource_assignment_guard`, a statement trigger running before the lock trigger;
independent review, 8A-FA2-001). The test harness's cleanup marks its transaction when it removes a run's
allocations with their requirements. A kit line's trip is a
trip of its own allocation: a composite foreign key to the trip's `(id, resource_assignment_id)`. The downgrade
drops them, putting partly or fully allocated requirements back to `OPEN`; `btree_gist` stays (0044's).

## For Eligibility's reminders (ELG-2)

This module registers `eligibility.ports.AllocationSource` when it is loaded, as it registers `AssignmentPort`.
`hold(db)` takes this module's lock alone, unmarked, as `AssignmentPort.hold` does: marking reminders seen reads the
allocations under it. `held_for_reminders(db, today)` lists every held allocation whose last day has not passed - its machine over its days
- and each listed kit line of it with days left - its piece over the line's days - each with the site as it now is
(`SiteFacts`' state, central-government answer, label or problem) and the day it was recorded. The same machine, days
and site the allocation's "today's answer" uses. A read: nothing is written and no lock is taken. Eligibility judges
them for the reminders "Runs out before the job starts" and "Runs out during the job"
(`eligibility-api-contract.md`, "Reminders and escalation").

## What is unchanged

The frozen Slice 6D.1 handoff contract is byte-identical (SHA-256
`70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a`); `crm_work_order` and `crm_work_order_line` do
not change; the Equipment Reference's and Eligibility's tables do not change. **Reconciled 9 October 2026 (TB-1 TB1-102 part b):** that was its hash until CS-04 part 1 (8 October 2026) appended
the owner-approved dated amendment at its end; its SHA-256 is now `0f16ff221e897f6199c352204a0ecced6f9a67f0c6695ad97c08c9dc2cd39080`, the current value
recorded in `docs/continuity/NEXT_STEPS.md`. Neither this module nor TB1-102 part b changes it.
