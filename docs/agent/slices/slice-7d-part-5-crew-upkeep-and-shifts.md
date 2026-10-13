# Slice 7D Part 5 - crew food, accommodation and travel, and the shift pattern

## Status

**Designed and built 9-10 October 2026**, from the owner's answers of 9 October 2026. Recording only: nothing is
calculated. The owner was away for the weekend; every point the answers did not settle is taken the way most
faithful to "record what the Work Order says, charge nothing it doesn't" and listed under "Assumptions for the
owner's screen check".

```text
Branch                hiring/slice-7d-part-5-crew-upkeep-shifts
Worktree              <a separate worktree>
Baseline              f0eb393 (origin/main)
Alembic               20260908_0052; parent 20260908_0051 (CS-05a, merged 9 October; built on 0050 until then)
Frozen contract hash  0f16ff221e897f6199c352204a0ecced6f9a67f0c6695ad97c08c9dc2cd39080, unchanged
Review                the independent reviewer, external; cap 5 rounds (owner, relayed 9 October 2026)
```

Parts 1 and 2 (`slice-7d-work-order-line-billing-terms.md`), Part 3 (`slice-7d-part-3-contract-period.md`) and
Part 4 (`slice-7d-part-4-remaining-billing-terms.md`) are merged and not re-asked. `WBT-001` is the binding
contract: only explicitly recorded terms may be calculated.

## Authority and required reading

```text
WBT-001                         work-order-billing-terms-contract.md (APPROVED): term set, versions, INR, nothing guessed
Slice 7D Parts 1-4              the four slice documents above; decisions 1-31
work-order-contract.md          "Slice 7D Part 1", "Part 2", "Part 3" (copying terms), "Part 4"
resource-requirement-api-contract.md   the line facts a requirement shows (it read the night shift)
DEFERRED_REQUIREMENTS.md        "Work Order lines", "Billing terms deferred by Slice 7D", "Operators' pay",
                                "Contracts are independent of each other"
FUTURE_SLICES.md                7D, 7D Part 4, 8B, 8D
UI_UX_CARRY_FORWARD.md          "Work Order billing terms (Slice 7D.1)"
CODING_STANDARDS.md             "When a service outgrows one file" (services/billing_terms.py)
```

## Why

Slice 7D Part 2 listed "food and accommodation" as out of scope, and nothing tracked it. Some customers provide the
crew's food, accommodation and travel, or provide them at a cost they recover from PBL; a Work Order that says so
must be recorded.

A line could not record "8 hours a shift, 2 shifts a day" as written, nor one monthly rate that covers two shifts:
the second shift's hours existed only while that shift was charged separately (Part 2's night shift).

## The owner's answers, 9 October 2026

1. **Food and accommodation.** Usually the Work Order just says they are provided: the customer builds
   accommodation on site and runs a mess. It can also say "provided at a cost of Rs X". That cost is per person,
   per day or per month, separate for operators and helpers. It is either deducted from PBL's invoice or billed to
   PBL separately by the customer, as negotiated. Nothing is ever paid to the worker.
2. **Travel** has the same choices. It may cover the trip at the start and end of the job (a cost per trip), daily
   travel to site (a cost per day), or both.
3. Every one of these can differ between operators and helpers.
4. **Shifts.** Up to 3 shifts a day, each with its own hours (for example a 12-hour 1st shift and an 8-hour 2nd
   shift). The rate is either the same for every shift or set per shift. This extends the existing night-shift
   option (a rate per shift or hour, or a % of the day rate).
5. **Overtime** is counted per shift or per day, as the Work Order says.

"Not in the Work Order" stays a choice everywhere.

Carried from 7D: terms belong to each period; null means not recorded yet and `NONE` means not in the Work Order;
amounts in INR; every number finite and greater than zero; the database checks mirror the API's rules; missing
items are reported as 7D's completeness list does; the existing billing-terms permission.

## Assumptions for the owner's screen check

Each is a reading of the answers above where they did not decide the point. Each can be changed without losing
anything already recorded, unless it says otherwise.

| # | Point the answers left open | Reading taken |
| --- | --- | --- |
| A1 | Travel "at the start and end" and "daily travel" | Two separate items, each answered on its own: "travel to and from the job" (a cost per trip) and "daily travel to site" (a cost per day). "Both" is both items answered |
| A2 | Whether a cost is per person | **Recorded, not assumed** (review round 1, 7D5-R1-003): every cost states its basis. Food and accommodation are per person per day or per month, as the owner said. Travel to and from the job is per person per trip, or per trip whatever the number of people; daily travel per person per day, or per day whatever the number. (Until round 1 travel was assumed per person.) |
| A3 | Deducted or billed separately: once for the Work Order, or per item | **Per item, and per operators/helpers**, beside each cost. "As negotiated" could differ by item, and a single answer would record the wrong arrangement for the item that differs. A **Same as for operators** button copies the operators' answers to the helpers |
| A4 | A line recorded as **equipment only** (no crew) | It has no crew, so it has no crew upkeep: nothing is asked and nothing may be recorded. Upkeep is asked once the Work Order states its crew (Part 4) |
| A5 | A Work Order that states **0 helpers** (or 0 operators) | Nothing is asked for the people it has none of |
| A6 | A Work Order that says the **contractor (PBL) arranges** food or travel | Recorded as "Not in the Work Order": no money moves either way. If it should be its own answer, say so |
| A7 | **Not in the Work Order** for shifts | **States no shifts at all** - an answer, so the period is complete, but no shift count is read from it (review round 2, 7D5-R2-002). A Work Order that does state its shifts - even one - is recorded as one, two or three shifts (A8). Part 2's narrower "night shift not in the Work Order" is **not** mapped to it: the migration asks for the shift pattern again and keeps that old answer on the period (rounds 3 and 4; "The migration" below) |
| A8 | A Work Order stating **one** shift | Recorded as **one shift** with its hours ("one shift of 10 hours"), as written - the hours sit beside the contracted hours, which keep their meaning (A10). Two or three shifts record every shift's hours. One shift has no rate choice and no "per shift or per day" (review round 2; until then one shift was folded into "not in the Work Order" and its hours could not be recorded) |
| A9 | **"The same rate for every shift"** | The Work Order rate covers every shift, counted in the line's own billing unit: a monthly or daily rate covers all the shifts of the month or day; a rate per shift applies to each shift. "Set per shift" is Part 2's night-shift choice for each later shift: the first shift at the Work Order rate, each later shift per shift, per hour or as a % of the Work Order rate, with its own working days on a monthly line (Part 2, decision 10). **Bears on money** (review round 5): the screen records the Work Order's words - "the same rate for every shift" or "a rate set for each later shift" - and billing (8D) may not count shifts by this reading until the owner confirms it |
| A10 | The line's **contracted hours** beside the shift hours | Unchanged in meaning: the hours the Work Order rate buys per billing unit. With one rate for every shift they cover every shift; with a rate per shift, the first shift only - exactly what they meant beside Part 2's night shift. They are not checked against the shift hours: both are recorded as the Work Order states them, and billing (8D) and Billing UAT reconcile them. **Bears on money** (round 5): which hours the rate buys decides overtime; 8D may not apply it until the owner confirms it |
| A11 | A ceiling on shift hours | The shifts of one day add up to **no more than 24 hours**. A day has no more; a typed 80 for 8 is refused instead of recorded |
| A12 | When "per shift or per day" is asked | **Wherever overtime is charged on two or three shifts**, monthly lines included whichever way they count overtime: the answer was not limited (review round 1, 7D5-R1-001; until then a monthly line counted over the whole month was not asked). Like the other sub-choices of a charged term (monthly overtime, fuel charge), it has no "not in the Work Order": a Work Order that charges overtime on several shifts must say how. **Bears on money** in its whole-month part (round 5): 8D may not apply a per-shift or per-day answer to whole-month counting until the owner confirms it |
| A13 | Hourly lines | No shift pattern, as they had no night shift: hourly billing uses the hours actually worked (`WBT-001`). Crew upkeep applies to every basis, as crew does |
| A14 | The resource requirement page | It said ", night shift charged"; it now says how many shifts a day the Work Order states (1, 2 or 3), and nothing when it states none or is not recorded |
| A15 | **"A % of the day rate"** for a later shift | **Settled by owner decision 7 of 14 September 2026, kept for confirmation because the wording differs.** Decision 7 agreed the night/second shift's choices as "rate per shift or hour, or % of normal" on shift, day and month lines (`slice-7d-work-order-line-billing-terms.md`, "The choices offered"); "normal" is `normal_rate_amount`, the Work Order rate per the line's billing unit - the rate the first (day) shift is charged at. The owner's answer 4 describes that existing option ("This extends the existing night-shift option ... a % of the day rate"), so Part 5 keeps it unchanged and migrated percentages keep their meaning exactly. The screen says "% of the first shift's rate (the Work Order rate)". **It bears on money**: if a real Work Order on a monthly or shift line means a percentage of a rate per day - which no line records - the owner must say so before billing (8D) is built; nothing is calculated before then |

## Design (engineering)

### Records

New columns on `crm_work_order_line_billing_term`, per period, in the Parts 2 and 4 pattern: every term column
nullable, null = not recorded (reported missing), `NONE` = not in the Work Order (an answer). Copying terms between
lines copies them column by column with the rest (Part 3); a later period made on screen copies them from the latest.

**Shift pattern** (SHIFT, DAY and MONTH lines; null on HOUR):

```text
shift_pattern_code              NONE (not in the Work Order: no shifts stated) | ONE_SHIFT | TWO_SHIFTS | THREE_SHIFTS
shift_1_hours                   > 0, the first shift's hours in a day; with ONE_SHIFT, TWO_SHIFTS or THREE_SHIFTS
shift_2_hours                   > 0; with TWO_SHIFTS or THREE_SHIFTS
shift_3_hours                   > 0; with THREE_SHIFTS
shift_rate_code                 SAME_FOR_ALL_SHIFTS | PER_SHIFT; with TWO_SHIFTS or THREE_SHIFTS
shift_2_rate_method_code        RATE_PER_SHIFT | RATE_PER_HOUR | PERCENT_OF_NORMAL (of the Work Order rate, A15); with PER_SHIFT
shift_2_rate_amount / _percent  exactly the value the method asks for, in the same save (Part 2's night-shift rule)
shift_2_working_days_per_month  > 0; MONTH, with PER_SHIFT
shift_3_rate_method_code, shift_3_rate_amount, shift_3_rate_percent, shift_3_working_days_per_month
                                as shift 2's, and only with THREE_SHIFTS
overtime_counted_per_code       PER_SHIFT | PER_DAY; overtime charged on two or three shifts (A12)
shift_1_hours + shift_2_hours + shift_3_hours <= 24 (A11)
```

**These replace Part 2's five night-shift columns**, which the migration converts and drops (below). A charged night
shift was exactly a second shift with its own rate, and a night shift "not in the Work Order" is kept on its period as
`legacy_night_shift_not_in_work_order` while the shift pattern is asked again, so nothing the night shift held is lost.

**Crew upkeep** - four items for each of operators and helpers, only while the Work Order states its crew (A4), and
not for operators or helpers it states 0 of (A5):

```text
upkeep_<item>_<role>_code           NONE | PROVIDED (by the customer, no cost) | PROVIDED_AT_COST
upkeep_<item>_<role>_amount         > 0, INR; with PROVIDED_AT_COST
upkeep_<item>_<role>_unit_code      the cost's basis (A2); with PROVIDED_AT_COST:
                                      food, accommodation   PER_PERSON_PER_DAY | PER_PERSON_PER_MONTH
                                      job_travel            PER_PERSON_PER_TRIP | PER_TRIP
                                      daily_travel          PER_PERSON_PER_DAY | PER_DAY
upkeep_<item>_<role>_recovery_code  DEDUCTED_FROM_INVOICE | BILLED_SEPARATELY; with PROVIDED_AT_COST (A3)

<item>   food | accommodation | job_travel (to and from the job, at its start and end) | daily_travel
<role>   operator | helper
```

Thirty-two columns (twenty-eight until review round 1 gave travel costs a basis too) from one specification, `WORK_ORDER_LINE_CREW_UPKEEP_ITEMS` × `..._ROLES` in
`work_orders/contract.py`; the schemas, the column list, the rules and the screen are all generated from it, so the
eight cells cannot drift apart. A cost, or its basis, left blank after "at a cost" is reported missing, not refused (Part 4's
pattern for the kilometres included and the crew numbers).

**Why columns, not a child table.** A period is one row: the revision check, whole replacement, copying terms
between lines and the event's `changed_fields` all work on its columns already. A child table would need its own
copy, replace and conflict handling for no business gain.

### Rules, refused by the API (`422`) and by a CHECK

- Every code in its domain; every number finite and greater than zero; shift hours of a day at most 24.
- Shift pattern null on an hourly line and before a billing basis.
- Each shift value only with its parent: shift 1's hours with one, two or three shifts; shift 2's hours, the rate
  choice and "per shift or per day" with two or three; shift 3's values with three; a later shift's rate and working days with "per shift"; working days on a monthly line only;
  a later shift's rate method carrying exactly its value.
- "Per shift or per day" only where overtime is charged on two or three shifts (A12).
- Crew upkeep only while the Work Order states its crew; a role's upkeep null when the crew number for it is 0;
  each cost's amount, basis and recovery only with "at a cost"; each basis one its item allows.

The service mirrors every CHECK with a readable message; `term_notes` stays the free text no rule reads.

### Completeness

```text
SHIFTS        replaces NIGHT_SHIFT, in its place: SHIFT, DAY or MONTH with no shift choice; or stated shifts without
              each shift's hours; or two or three without the rate choice; or "per shift" without each later shift's
              rate, or (MONTH) its working days
OVERTIME      also: overtime charged on two or three shifts and no "per shift or per day" (A12)
CREW_UPKEEP   new, after CREW: the Work Order states its crew and an item for operators (unless 0) or helpers
              (unless 0) is unanswered, or a cost lacks its amount, its basis or its recovery
```

A period saved before Part 5 reports `CREW_UPKEEP` where its crew is stated - correct, it was never recorded.

### The migration, `20260908_0052`

The night shift is converted, never dropped:

```text
night shift not recorded            -> shift pattern not recorded
night shift NONE                    -> not recorded: the shift pattern is asked again (round 3, 7D5-R3-002), and the
                                       old answer kept as legacy_night_shift_not_in_work_order (round 4, 7D5-R4-001)
night shift charged                 -> TWO_SHIFTS, PER_SHIFT; shift 2's rate method and value and (MONTH) working
                                       days carried; shift 2's hours from the night hours per billing unit
                                       (SHIFT, DAY: the same; MONTH: divided by the night working days);
                                       shift 1's hours from the contracted hours the same way
```

**A night shift "not in the Work Order" is asked again** (review round 3, 7D5-R3-002): it said only that no second
shift was charged, and the new question is the whole pattern, which cannot be read from it - the new `NONE` ("states no
shifts") or `ONE_SHIFT` would each claim more than was recorded. So its shift pattern is left not recorded, reported
`SHIFTS` missing, and the upgrade logs how many periods it re-asks. **The old answer is kept** (review round 4,
7D5-R4-001): `legacy_night_shift_not_in_work_order`, a boolean false on every other row, marks the period; the response
returns it, the screen shows it beside the shift question ("Recorded before 10 October 2026: the night shift was not in
the Work Order..."), no request can set or change it, a save leaves it, and copying terms to another line does not carry
it (it is that period's history, not a term). Downgrade restores the night shift as `NONE` from it while the pattern is
still unanswered. Refusing such rows instead was weighed and not chosen: every period saved since Part 2 on a shift, day
or month line holds a night-shift answer, so a refusal would stop the upgrade on every database with billing terms.
Nothing was charged under the old answer and nothing is under the new.

**It refuses to run**, naming the period and what to correct, as `0037` did, while any charged night shift on a
monthly line holds hours with no working days, or hours that do not divide into an exact hour figure (two decimals)
by its working days, or would make two shifts longer than 24 hours. Shift 1's hours are filled in only where the
division is exact; otherwise they are left blank and reported missing - the contracted hours themselves are kept
unchanged, so nothing is lost.

Downgrade converts back what Part 2 can hold - NONE (no shifts stated, so no night shift charged), or two shifts charged
per shift - and loses one or three stated shifts,
"the same rate for every shift", the shift hours of shift 1, "per shift or per day" and every crew-upkeep term. Stated
in the migration rather than discovered.

The night-shift CHECKs of `0038` are dropped and the two that also covered other columns
(`ck_wol_term_p2_positive_values`, `ck_wol_term_p2_basis_chosen_first`) are recreated without the night columns:
PostgreSQL would otherwise drop them whole with the column, silently losing their mobilisation and fuel rules.

### API

No new route, permission or event. Part 1's `POST` and `PUT` accept the new fields, `GET` returns them, and the five
`night_shift_*` fields are gone from request and response - a request still sending one is refused as an unknown
field. Each period's response gains the read-only `legacy_night_shift_not_in_work_order` (above). `missing_items` gains
`SHIFTS` (in `NIGHT_SHIFT`'s place) and `CREW_UPKEEP`. Events keep their payload;
`changed_fields` names the new columns, never a value. Recorded in `work-order-contract.md`, "Slice 7D Part 5".

The resource requirement's `line.night_shift_charged` becomes `line.shifts_per_day` (1, 2 or 3; null when not
recorded or hourly), recorded in `resource-requirement-api-contract.md` (A14).

### Screen

On the Work Order page's billing terms, in the 7D.1 chapters and cards, styled through `globals.css`:

- **Shifts**, in "Working time" after the off days (moved from "Extra charges", where the night shift sat, because
  one rate for every shift is no extra charge): shifts a day, each shift's hours, the rate choice, and each later
  shift's rate (and working days on a monthly line).
- **Overtime** shows "On these shifts, overtime is counted: per shift / for the whole day" wherever overtime is charged on
  two or three shifts.
- **Crew food, accommodation and travel**, in "Extra charges" after Crew, once the crew is stated: a row per item,
  operators then helpers, each a choice with, when "at a cost", its cost, its basis and how it is recovered;
  **Same as for operators** copies the operators' answers to the helpers.
- The read-only view shows the same.

## Not in scope

- Any calculation: deductions, separately billed costs, shift billing, overtime.
- Paying anyone: "nothing is ever paid to the worker"; crew pay stays PBL's HR terms (the 8B standing rule).
- Different overtime or breakdown rules per shift (Part 2 decision 10 stands); different shifts on different
  weekdays.
- Locking at mobilisation; applying amendments (`D-07`).
- The handoff: `crm_work_order_line`, `WorkOrderResponse`, `WorkOrderLineResponse`, `WORK_ORDER_LINE_SELECT_COLUMNS`
  and the frozen contract file are untouched.

## Test plan

```text
backend/tests/test_slice_7d_part_5_upkeep_and_shifts.py
  every new rule refused through the API, with its message; every legal shape recorded and read back; each
  completeness item appearing and clearing; NONE an answer, null missing; the roles at 0; equipment only;
  "Same as..." is a screen helper (frontend test); events carry no value; copying terms carries the new columns;
  each CHECK by a direct insert naming its constraint, and legal shapes accepted directly; the handoff writes none
backend/tests/test_slice_7d_part_2_billing_terms.py   night-shift tests moved to the shift pattern
backend/tests/test_wrr001_resource_requirements.py    shifts_per_day replaces night_shift_charged
Migration (scripted, scratch database): night shift NONE asked again and kept as the marker, charged on SHIFT, DAY and
  MONTH carried; each refusal; downgrade (the marker back to NONE, one shift to NONE) and upgrade again
frontend: which shift and upkeep fields show and are sent, the copy to helpers, the new missing items' groups
```

## Allowed files

```text
backend/alembic/versions/20260908_0052_billing_terms_crew_upkeep_and_shifts.py     new
backend/app/modules/work_orders/contract.py, schemas.py, repository.py, services/billing_terms.py
backend/app/modules/resource_requirements/schemas.py, service.py                    A14
backend/tests/...                                                                    as above, plus fixtures touched
backend/tooling/smoke_data/scenarios.py (and builders if needed)                     screen-check data
frontend/src/pages/work-orders/WorkOrderBillingTermsSection.tsx, workOrderBillingTermsState.ts (+ .test.ts)
frontend/src/pages/resource-requirements/ResourceRequirementDetailPage.tsx, resourceRequirementState.ts (+ tests)
frontend/src/styles/globals.css                                                      a class for the upkeep table
docs: this file, the acceptance checklist, work-order-contract.md, resource-requirement-api-contract.md,
      FUTURE_SLICES.md, DEFERRED_REQUIREMENTS.md, MCF_ADOPTION_RECORD.md, NEXT_STEPS.md, a continuity note
```

## Independent review

### Round 1 (the independent reviewer, 10 October 2026): CORRECTION_REQUIRED, three material findings

Packet `3287e2d2...a676`, commit `ad21eef`. All three were about an assumption deciding money; all three are corrected.

- **7D5-R1-001 - "per shift or per day" was not asked on a monthly line counted over the whole month.** The owner's
  answer 5 was not limited, so that was an assumption too far. It is now asked wherever overtime is charged on two or
  three shifts: service, CHECK `ck_wol_term_overtime_counted_per`, the screen, completeness, the contract, the tests and
  the smoke data (whose monthly line now records it on both periods). A12 is rewritten.
- **7D5-R1-002 - the percentage's referent.** The owner described Part 2's option as "a % of the day rate"; the screen
  said "% of the Work Order rate". The code was right and unchanged - `PERCENT_OF_NORMAL` is a percentage of
  `normal_rate_amount`, the rate the first (day) shift is charged at, exactly as Part 2 stored it, so migrated
  percentages keep their meaning - but the words did not show it. The screen now says "% of the first shift's rate (the
  Work Order rate)", the contract says what the percentage is of, and A15 records the reading for the owner.
- **7D5-R1-003 - travel was assumed per person.** Every cost now records its basis, so none is assumed: travel to and
  from the job per person per trip or per trip whatever the number of people; daily travel per person per day or per
  day whatever the number; food and accommodation per person per day or per month (the codes say "per person", as the
  owner did). Four columns more (thirty-two), a per-item domain in the CHECK and the service, the basis asked on screen
  for every cost; migration `0052` amended in place (never merged or deployed). A2 is rewritten.

### Round 2 (the independent reviewer, 10 October 2026): CORRECTION_REQUIRED, three material findings

Packet `89360231...6a4f`, merged head `a357c8f` (main with CS-05a merged in; `0052` re-pointed to `0051`). Round 1's
three corrections were not questioned.

- **7D5-R2-001 - the percentage's referent still rested on an assumption.** Not a new assumption: owner decision 7 of
  14 September 2026 agreed "% of normal" for the night/second shift on shift, day and month lines, and the owner's
  answer 4 extends that option. A15 now cites that decision, says plainly that it bears on money, and stays on the
  owner's screen-check list because the 9 October wording ("the day rate") differs; the packet carries the decision's
  text. No code change: the stored meaning is Part 2's, unchanged.
- **7D5-R2-002 - "not in the Work Order" was read as one shift.** Corrected as recommended: `NONE` now states no
  shifts, and a new `ONE_SHIFT` records one stated shift with its hours (missing until given). One shift has no rate
  choice and no "per shift or per day". The resource requirement reports no shift count for `NONE`. Mirrored in the
  service, the CHECKs (`ck_wol_term_shift_codes`, `_shift_values`; migration `0052` amended in place), completeness, the
  screen, the read-only view and the tests.
- **7D5-R2-003 - records out of step.** The acceptance checklist, continuity note, backlog, deferred list and test
  docstring now say A1 to A15, describe the cost bases as recorded (per person, or per trip or per day whatever the
  number of people), and name A15 as the one assumption bearing on money.

### Round 3 (the independent reviewer, 10 October 2026): CORRECTION_REQUIRED, four material findings

Packet `d737e95e...8f48`, commit `9055070`.

- **7D5-R3-001 - A15 still needs the owner.** Agreed that only the owner can settle it; it is the money-bearing point
  the brief says to stop on rather than decide, and the brief's way of stopping is an assumption listed for the owner's
  screen check. Nothing is calculated until 8D, so the package records the percentage as the Work Order states it and
  **8D may not use a later shift's percentage until the owner has confirmed A15** - written into `FUTURE_SLICES.md`
  (8D) and `DEFERRED_REQUIREMENTS.md`. No code change.
- **7D5-R3-002 - the migration turned a night shift "not in the Work Order" into "states no shifts".** Corrected: such
  a period's shift pattern is now left not recorded and asked again (above); the upgrade logs the count; the migration
  check now expects that.
- **7D5-R3-003 - the requirement page hid a count of one.** Corrected: `shiftsPerDayText` (a pure rule, tested) shows
  "1 shift a day" or "N shifts a day", and nothing when no count is stated.
- **7D5-R3-004 - four records still described the old shapes.** Corrected: `FUTURE_SLICES.md`, the migration's
  docstring and comments, this document's rule summary and the acceptance checklist's test data.

### Round 4 (the independent reviewer, 10 October 2026): CORRECTION_REQUIRED, one blocking and one material finding

Packet `c69ace6e...3095`, commit `a18a839`. The reviewer recorded A15 as "appropriately gated from later calculation
pending confirmation".

- **7D5-R4-001 (blocking) - round 3's re-ask discarded the old answer.** Corrected by preserving it: the migration
  keeps a Part 2 night shift "not in the Work Order" as `legacy_night_shift_not_in_work_order` on its period (above),
  read back and shown beside the shift question, never written by a request; downgrade restores `NONE` from it. The
  migration check proves the marker is set on exactly that row, survives down and up, and restores `NONE`; a backend
  test proves it reads back, survives a save that answers the shifts, and cannot be sent.
- **7D5-R4-002 - records still described the round-2 mapping.** Corrected: A7, the "nothing is lost" sentence (now true
  again), the Part 1 test fixture's comment, the resource-requirement schema's docstring, and the continuity note's
  frontend counts.

### Round 5 (the independent reviewer, 10 October 2026): CORRECTION_REQUIRED, three material findings

Packet `94a70a0f...9094`, commit `1b1b49f`. Round 5 reached the package's five-round cap (owner, relayed 9 October
2026); the owner then asked for a sixth round (9 October 2026), which reviews these corrections. The merge stays the
owner's.

- **7D5-R5-001 - A9, A10 and A12's whole-month part also bear on money.** Corrected: each is marked so in the table
  above, in `FUTURE_SLICES.md` (8D: no calculation with any of A9, A10, A12 or A15 until the owner confirms it), in
  `DEFERRED_REQUIREMENTS.md`, the acceptance checklist and the continuity note; the screen's choices now read in the
  owner's words, "The same rate for every shift" and "A rate set for each later shift (shift 1 at the Work Order rate)",
  and the helper text no longer says how contracted hours apply to several shifts.
- **7D5-R5-002 - no test that copying leaves the marker behind.** Corrected:
  `test_copying_terms_does_not_carry_the_legacy_marker`.
- **7D5-R5-003 - records.** Corrected: the review summary's column count (thirty-two), and the continuity note now
  separates the earlier runs from those on the final head.
