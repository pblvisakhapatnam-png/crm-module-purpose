# Resource Requirement and Equipment Reference API Contract

Implementation contract for the WRR-001 foundation (24 September 2026). The logical contract is
`work-order-resource-requirement-contract.md` (`WRR-001`, `APPROVED`); the design and the owner's
answers are `docs/agent/slices/wrr-001-resource-requirement-foundation.md`; the equipment structure's
ownership is ADR-037. This file states what the routes accept, return and refuse.

Two modules:

```text
backend/app/modules/equipment_reference/     the platform's equipment structure (read only)
backend/app/modules/resource_requirements/   what a Work Order line needs on site
```

Neither writes a Work Order table. Resource Requirements reads Work Order facts only through the
`work_orders` service (`get_work_order_line_reference`, `get_work_order`, `list_work_order_lines`,
`list_work_order_line_details`, `list_work_order_billing_terms`, `get_work_order_contract_period`).

## Permissions

| Code | Roles | Guards |
| --- | --- | --- |
| `EQUIPMENT_REFERENCE_READ` | all six (as `WORK_ORDER_READ`) | the structure route |
| `RESOURCE_REQUIREMENT_READ` | all six (as `WORK_ORDER_READ`) | list, defaults, one requirement |
| `RESOURCE_REQUIREMENT_WRITE` | `ADMIN`, `OPERATIONS_USER` (owner, Q6) | create, change, cancel |

All seven routes are pinned in `backend/tests/fixtures/post_baseline_tightened_routes.py`
(`POST_BASELINE_NEW_ROUTES`). The structure has no write route: it changes only by migration (version 2,
ERT-1, added the crane carrier; version 3, ERT-2, the four kinds of detachable kit and the depth setting).
ERT-1's models, machines and the Plum report import, ERT-2's kit, and their permission
`EQUIPMENT_REFERENCE_MANAGE`, are in `equipment-reference-api-contract.md`. A requirement's class list is
unchanged: every part class, kit included, is offered to no business line.

## The equipment structure

```text
GET /api/equipment-reference/structure       200
```

Returns the whole structure as it stands:

```text
taxonomy_version      the current (highest) version number
component_depth       the depth setting in force: how many levels fitted parts nest to, the machine
                      being level 1 (ERT-2)
versions[]            version_number, version_label, source_note, loaded_at, component_depth (ERT-2)
units[]               unit_code, unit_label, unit_symbol, whole_numbers_only
classes[]             class_code, class_label, class_kind_code (MACHINE | PART; ERT-1),
                      tracking_code (SINGLE | COUNTED; ERT-2),
                      fits_class_codes[] (for a part class, the classes it may be fitted to by a dated
                      link; ERT-1), kit_for_class_codes[] (for a kind of kit, the machine classes it is
                      kit for; ERT-2), display_order, business_line_codes[],
                      introduced_in_version, retired_in_version, is_active,
                      types[]:        type_code, type_label, display_order, introduced/retired, is_active
                      capabilities[]: capability_code, capability_label, unit_code, unit_symbol,
                                      whole_numbers_only, value_kind_code (MINIMUM | CHOICE),
                                      allowed_values (CHOICE only), is_key, display_order, is_active
capabilities[]        every capability, with its unit, kind, allowed values and version fields
aliases[]             term, normalized_term, source_code (PLUM_CATEGORY | ANNEXURE_21 | TRADE_TERM),
                      class_code, type_code, is_active
```

Retired rows are returned, marked `is_active: false`, so anything saved with them still reads. A
class's `business_line_codes` lists only live business lines; empty means neither Hiring nor
Transportation deploys it - true of every part class, so a requirement can never ask for one. Units: `TONNE` t, `KILOGRAM` kg, `METRE` m, `CUBIC_METRE` m³,
`KILOWATT` kW, `KILOVOLT_AMPERE` kVA, `COUNT` (whole numbers only).

## Resource Requirements

```text
GET  /api/resource-requirements                      READ   200; 422 unknown status
GET  /api/resource-requirements/defaults             READ   200; 404 unknown line
GET  /api/resource-requirements/{public_id}          READ   200; 404
POST /api/resource-requirements                      WRITE  201; 404 unknown line; 409 key reused; 422
PUT  /api/resource-requirements/{public_id}          WRITE  200; 404; 409 version; 422
POST /api/resource-requirements/{public_id}/cancel   WRITE  200; 404; 409 version; 422
```

`/defaults` is registered before `/{public_id}`. Unknown request fields are refused with `422`
everywhere, including a `unit_code` sent with a capability. Refusal messages name the dates or codes
they refuse over.

### The list

Query: `work_order_public_id`, `work_order_line_public_id`, `status_code` (`OPEN` | `PARTLY_FULFILLED` |
`FULFILLED` | `CANCELLED`, or `NEEDS_MACHINES` for the first two - 8A core; case-insensitive), `equipment_class_code` (case-insensitive), `limit` (1-200, default 50), `offset`.
Order: `URGENT` first, then the earliest `required_from`, then the order recorded.

### Defaults for a new requirement

Query: `work_order_line_public_id` (required), `required_from` (optional). Returns the line's identity
(`work_order_public_id`, `work_order_code`, `work_order_line_public_id`, `work_order_line_number`,
`source_offer_line_public_id`, `account_public_id`), `taxonomy_version`, `line` (below),
`existing_requirement_count`, and `suggested`:

```text
units_required               1
required_from                the date given; else the line's own start; else the contract start; else null
required_to                  null (until the line ends)
crew_operators_required      the Work Order's Part 4 numbers in force on required_from:
crew_helpers_required          STATED -> its numbers; NONE (equipment only) -> 0; not answered -> null
priority_code                NORMAL
equipment_class_code         a live Hiring class matched by the line's category text, or null
equipment_type_code          a type, only where the matching word names one ("Hydra" -> PICK_AND_CARRY)
equipment_class_matched_term the class label or alias that matched
```

A class is suggested on a whole match of the category text (case and spacing ignored) against a class
label or an alias; failing that, on a class label or alias found as whole words inside it ("250MT
Crane") - but only when every match names the same class. Two candidate classes give no suggestion.

### Creating

```json
{
  "work_order_public_id": "...",
  "work_order_line_public_id": "...",
  "create_request_key": "uuid generated once by the form",
  "units_required": 2,
  "required_from": "2027-01-10",
  "required_to": null,
  "crew_operators_required": 1,
  "crew_helpers_required": 1,
  "crew_notes": "Operator with a valid crane licence",
  "priority_code": "NORMAL",
  "planning_notes": "Tide allows about 8 working hours a day",
  "items": [
    {
      "equipment_class_code": "CRANE",
      "equipment_type_code": "CRAWLER",
      "equipment_specification": "Luffing fly jib, 60 m",
      "capabilities": [{ "capability_code": "RATED_CAPACITY", "minimum_value": "220" }]
    }
  ]
}
```

- `units_required` a whole number from 1; crew numbers whole from 0; both up to the integer column's
  range. `crew_notes` up to 2000 characters, `planning_notes` 4000, `equipment_specification` 1000.
- `priority_code` `NORMAL` (default) or `URGENT`.
- `items`: exactly one in this slice (owner, Q15); none or several is refused.
- The class must exist, be live and be deployed by Hiring - Prime Mover, Generator and the other
  classes Hiring does not use are refused. A type must belong to the class and be live; blank means any
  type. Each capability must apply to the class, be given once, and be live.
- A `MINIMUM` capability takes `minimum_value` only: greater than 0, at most nine digits before the
  point and three after, not NaN; a `COUNT` one whole. A `CHOICE` capability takes `choice_value` only, one of its
  `allowed_values` (case-insensitive).
- `required_to`, when given, is on or after `required_from`. Both must sit inside the contract and
  outside its gaps (Slice 7D Part 3's `classify_date_against_contract`), and inside the line's own
  dates; a blank `required_to` is not checked against the line's end. A bound not recorded is never
  treated as broken. A requirement may span a gap, as a line's own dates may.
- The line must be on the Work Order named; otherwise `404` with the same message as an unknown line.
- A Closed Work Order refuses every write (`422`).
- **Idempotent** - the platform's one replay rule (MCF-001: a retry or repeated submission has no duplicate
  effect; TB-1 finding TB1-102 part b, 8 October 2026; `app/shared/request_keys.py`, the rule Resource
  Assignments built first). The requirement keeps the SHA-256 of the request that made it: the fields sent with
  their values - a field left out is not the field sent empty - without the key. The same request with the same
  `create_request_key` again returns the first requirement, `201` with `replayed: true` and `event: null`. The key
  with any other request - on the same line or another - is `409` ("This form was already used to record a
  requirement ..."), and nothing is recorded. A requirement made before migration `20260908_0050` kept no
  fingerprint, so its key is `409` whatever is sent. Two simultaneous creates with one key are settled by the
  unique constraint: the loser is answered as above, so they make one requirement. **Reconciled 8 October 2026:**
  until then a second create returned the first requirement "whatever else it carries", refusing only another
  line, so a changed request was answered with the first requirement and the change dropped silently.

Response (`201`): `{ "resource_requirement": <requirement>, "event": <business event> | null, "machines_freed": 0,
"replayed": <true on a repeat> }`.

### Changing

`PUT` body: the create body's fields except the three identifying ones, plus
`expected_requirement_version`. Whole replacement of the requirement and its item. Checked exactly as a
create is, with one allowance: a class, type or capability retired since it was saved may stay on the
requirement (anything saved with a retired code keeps it) but may not be newly chosen. The row is
locked; a version other than the current one is `409`. An identical save records nothing: no version
change, no event, `event: null`. A cancelled requirement is `422`.

8A core: a requirement that is partly or fully allocated may be changed like an open one. A change is never refused
because of its allocations - fewer units, other dates, another class; an allocation that no longer fits shows a
warning on the allocation (`resource-assignment-api-contract.md`). The status is worked out again in the same
transaction.

### Cancelling

`POST .../cancel` body: `expected_requirement_version`, `cancellation_reason` (required, not blank, up
to 2000). From any status but `CANCELLED`; final - there is no un-cancel route. Who cancelled is recorded, and
must be a real user (`fk_resource_requirement_cancelled_by`). The version moves by one.

8A core applies `WRR-001`'s release rule: cancelling frees every machine held for the requirement, in the same
transaction and through the port Resource Assignments registers (`resource_requirements/ports.py`) - each
allocation `RELEASED` with the reason `REQUIREMENT_CANCELLED`, its last day the day before its start, or today when
it has started, and each recording `RESOURCE_ASSIGNMENT_RELEASED`. The response's `machines_freed` says how many
(0 on every other action). With no port registered the cancellation fails with a server error rather than leave machines held.

### A requirement

```text
requirement_public_id, requirement_reference ("RR-000001", derived from the id)
work_order_public_id, work_order_code, work_order_line_public_id, work_order_line_number,
source_offer_line_public_id, account_public_id          copied once at creation; immutable
units_required, required_from, required_to, crew_operators_required, crew_helpers_required,
crew_notes, priority_code, planning_notes
requirement_status_code (OPEN | PARTLY_FULFILLED | FULFILLED | CANCELLED), requirement_version, taxonomy_version
units_covered, units_remaining                           8A core, worked out on every read (below)
covered_unit_numbers                                     8A core: the units covered on every day (below); the
                                                         screens offer allocation on the others
items[]      item_number, equipment_class_code, equipment_class_label, equipment_type_code,
             equipment_type_label, equipment_specification,
             capabilities[]: capability_code, capability_label, unit_code, unit_symbol,
                             value_kind_code, is_key, minimum_value, choice_value
warnings[]   computed on every read; empty for a cancelled requirement (below)
line         the Work Order line as it stands now (below)
cancellation_reason, cancelled_by, cancelled_by_display_name, cancelled_at
created_by, created_by_display_name, created_at, updated_by, updated_by_display_name, updated_at
```

`line` is read live, never stored: `work_order_status_code`, `scope_description`,
`equipment_service_category`, `quantity` and `uom` (billing units, for reference only - Q2), `site`
(public id, address line, city, state, postal code; null when none usable), `site_central_government`
(8A core: `true`, `false` or `null` when not answered), `line_start_date`,
`line_end_date`, `contract_start_date`, `contract_end_basis_code`, `contract_end_date`,
`contract_gaps[]`, and from the billing-terms period in force on `required_from`:
`billing_terms_period_number`, `billing_uom_code`, `shifts_per_day`, `work_order_crew_code`,
`work_order_crew_operators`, `work_order_crew_helpers`. No rate, amount or commercial term.

*Changed by Slice 7D Part 5 (10 October 2026):* `night_shift_charged` (true while Part 2's night shift was charged) is
replaced by `shifts_per_day` - 1, 2 or 3 as the period's shift pattern states them, null when the Work Order states no
shifts ("not in the Work Order"), when it is not recorded, or when the line is billed by the hour. The night shift became the shift pattern
(`work-order-contract.md`, "Slice 7D Part 5").

### How far it is allocated (8A core)

A unit is covered when the days its allocations kept - held ones, and replaced or freed ones up to their last day - cover every day
of the requirement's period: `required_from` to its end, which is `required_to`, else the line's end, else the
contract's fixed end, else open. An open-ended period needs an open-ended allocation at the end of the unit's chain.
`units_covered` counts the covered units among `1..units_required`; `units_remaining` the rest.

```text
OPEN              no unit has a machine on any day
PARTLY_FULFILLED  some days of some units have one, but not every day of every unit
FULFILLED         every unit is covered
CANCELLED         final
COMPLETED         RPA-001's, reserved for execution; not used by 8A
```

The status is stored, and worked out again in the same transaction as every allocation write and every change to
the requirement - and, for a requirement without its own end, whenever the end it runs to moves: the Work Orders
module calls the listener Resource Requirements registers (`register_end_dates_listener`) from saving the contract
period, adding or removing an extension, and saving a line's details with a new line end, in its own transaction.

8A core also puts every requirement write - creating, changing, cancelling - behind the Work Order's row, taken
shared first and its status read there (`hold_work_order_status`), before the requirement's row: a Work Order change,
its closure included, waits for the write or is seen by it. Creating reads the request key's replay, the fields'
checks and the Work Order's dates only after that lock, so none of them works from a copy read before a change. The order is the one allocations keep: Work Order,
requirement, allocations, Eligibility. It is not a user's edit: `requirement_version` and who last changed the requirement stay as they
are, so a form open on it is not made stale by an allocation. A replaced or freed allocation keeps the days it
held, so freeing a machine partway leaves the days it kept covered and the rest to find.

### Warnings

Advisory only - never a refusal, never stored.

```text
SITE_NOT_RECORDED              the line has no usable site (Slice 7C)
OUTSIDE_CONTRACT               a date is now outside the contract, in a gap, or outside the line's dates (Q8)
CREW_DIFFERS_FROM_WORK_ORDER   operators or helpers differ from the Part 4 numbers in force (not when unanswered)
KEY_CAPABILITY_NOT_STATED      the item gives no value for its class's key capability
```

## Events

```text
ResourceRequirementCreated | ResourceRequirementUpdated | ResourceRequirementCancelled
source_module = resource_requirements, record_type = resource_requirement,
record_public_id = the requirement's public id
status_before / status_after: none -> OPEN, the status -> the same, the status -> CANCELLED. An update records
no move of its own: a move its new units or dates cause is ResourceRequirementFulfilmentChanged's, recorded
just before it (8A core), and the update's pair is the status it leaves.
payload: requirement_reference, work_order_public_id, work_order_line_public_id,
         source_offer_line_public_id, site_address_public_id (as read at the time),
         requirement_version, requirement_status_code, units_required, required_from, required_to,
         crew_operators_required, crew_helpers_required, priority_code, taxonomy_version,
         items[]: item_number, equipment_class_code, equipment_type_code,
                  capabilities[]: capability_code, value
         changed_fields[]   in the order: units_required, required_from, required_to,
                            crew_operators_required, crew_helpers_required, crew_notes,
                            priority_code, planning_notes, items (the whole item list)
```

8A core adds `ResourceRequirementFulfilmentChanged`, recorded when the status moves between `OPEN`,
`PARTLY_FULFILLED` and `FULFILLED`: status before and after, and a payload of `requirement_reference`,
`work_order_public_id`, `work_order_line_public_id`, `requirement_status_code`, `units_required`, `units_covered`,
`units_remaining`.

No free text - specification, notes or cancellation reason - and no amounts. The event's `reason`
column carries a fixed sentence, never the user's reason. The structure records no events: only a
migration changes it.

## Data

Migration `20260908_0041_resource_requirement_foundation`: `equipment_taxonomy_version`,
`equipment_class`, `equipment_class_business_line`, `equipment_type`, `equipment_capability`,
`equipment_class_capability`, `equipment_term_alias`, `resource_requirement`,
`resource_requirement_item`, `resource_requirement_item_capability`; version 1 of the structure; the
three permissions. The database itself refuses: a type of another class, a capability that does not
apply to the item's class (composite foreign keys), a second item, a capability given twice, a
non-positive or NaN value, both or neither of a value and a choice, an end before the start, a status
outside `OPEN`/`CANCELLED`, cancellation fields present on an open requirement or missing on a
cancelled one (who cancelled included, and it must be a user), two live key capabilities for a class, and an alias whose
normalized form disagrees with its term. A trigger, `trg_rr_item_capability_matches_kind`, refuses a
value that does not fit its capability - a least value for a fixed-list capability or a choice for a
measured one, a choice not on the list, a fraction of a count - as a check violation named
`ck_rr_item_capability_matches_kind`. What the database does not hold, the service does: the class
must be one Hiring deploys, a retired code may not be newly chosen, and a requirement has one item.

Migration `20260908_0045_equipment_allocation` (8A core) widens the status CHECK to `OPEN`, `PARTLY_FULFILLED`,
`FULFILLED` and `CANCELLED`; its downgrade puts partly or fully allocated requirements back to `OPEN`.

Migration `20260908_0050_create_request_fingerprints` (TB-1 TB1-102 part b) adds
`resource_requirement.create_request_fingerprint` - 64 hexadecimal digits, only with a request key
(`ck_resource_requirement_create_request_fingerprint`), null on a requirement made before it - and the trigger
`trg_resource_requirement_create_request_kept`, which refuses a change to a requirement's key or fingerprint. The
same revision adds the column to Equipment Reference's `equipment_model` and `equipment_asset`
(`equipment-reference-api-contract.md`, "Data").

## What is unchanged

The frozen Accepted Offer -> Work Order handoff: its contract file is byte-identical (SHA-256
`70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a`) and its response shape is pinned
by test. No Work Order table gains a column. The one Work Order change is a read-only service function,
`get_work_order_line_reference`, never exposed as a route. (8A core later added one column to the line's detail,
`site_central_government`; see `work-order-contract.md`.) **Reconciled 9 October 2026 (TB-1 TB1-102 part b):** that was its hash until CS-04 part 1 (8 October 2026) appended
the owner-approved dated amendment at its end; its SHA-256 is now `0f16ff221e897f6199c352204a0ecced6f9a67f0c6695ad97c08c9dc2cd39080`, the current value
recorded in `docs/continuity/NEXT_STEPS.md`. Neither this module nor TB1-102 part b changes it.
