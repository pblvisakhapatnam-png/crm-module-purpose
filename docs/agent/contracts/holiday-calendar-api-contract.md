# Holiday Calendar API Contract - PBL's holiday calendar, year by year (HOL-1)

Implementation contract for HOL-1 (2 October 2026). The design and the owner's answers are
`docs/agent/slices/hol-1-holiday-calendar.md`; the decision it builds is `docs/agent/DEFERRED_REQUIREMENTS.md`, "PBL's
default holiday calendar" (owner, 2 October 2026). This file states what the routes accept, return and refuse, and
what other modules read. A Work Order's own changes to the calendar, and the holidays that apply to its lines, are the
Work Order's: `work-order-contract.md`, "HOL-1".

```text
backend/app/modules/holiday_calendar/
  contract.py      the codes: kinds, "applies to", the year range, events, record type
  rules.py         pure (no database, no clock): a year's refusals; the dates a save adds, removes and changes; the
                   holidays for a state
  repository.py    its own three tables only
  service.py       reading and saving a year; what other modules read (calendar_between, state_for_address,
                   last_year_started); the port the Alerts read (registered when loaded)
  schemas.py, routes.py
```

The module is the **Holiday Calendar** row of `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`. It reads ELG-1's list of states and
union territories through Eligibility's public `list_jurisdictions` and `jurisdiction_for_state_text`, and keeps no
copy; Eligibility never imports it - the Alerts ask it through `eligibility/ports.py`'s `CalendarYearSource`. Work Orders
reads it through the service; it never reads Work Orders.

## Permissions

| Code | Roles | Guards |
| --- | --- | --- |
| `HOLIDAY_CALENDAR_READ` (new) | all six | the states, the years, a year |
| `HOLIDAY_CALENDAR_MANAGE` (new) | `ADMIN` | saving a year, and marking it complete or not |

Admin keeps the calendar until a position is mapped under `ORA-001`; that is a grant, with no code change. Every route
is pinned in `backend/tests/fixtures/post_baseline_tightened_routes.py` (`POST_BASELINE_NEW_ROUTES`).

## Conventions

- A **year** is any year from 2000 to 2100. It is **not started** until first saved, **started** once saved, and
  **complete** once Admin marks it so (design 1.2, point 1). Dates are `YYYY-MM-DD`; "today" is Asia/Kolkata.
- **Kinds**: `NATIONAL` | `FESTIVAL`, the words of the states' National and Festival Holidays Acts. The kind does not
  decide where a holiday applies: a state may count its own day among its national holidays (Maharashtra's 1 May).
- **Where it applies**: `ALL_INDIA`, naming no state, or `STATES`, naming one or more states or union territories by
  their ISO 3166-2:IN code (`IN-GJ`); never `IN`, the central government's own sites.
- A date is a holiday **at most once for each state**: one all-India holiday on a date and then no state's own; a state
  named once on a date. The same date may be a holiday for different states under different names.
- Codes are accepted in any case and stored in capitals. Unknown fields are refused (`422`). Errors are
  `{"detail": "..."}` in plain words, each naming the date it is about: a holiday's kind, name or "applies to" left
  out, null, blank, too long or not known is refused in those words, not by the request validator (HOL-1's review,
  HOL1-R3-001 and HOL1-R4-002). Only a holiday with no date - nothing to name - is refused as the request stands.

## Routes

```text
GET  /api/holiday-calendar/states                   HOLIDAY_CALENDAR_READ    200
GET  /api/holiday-calendar/years                    HOLIDAY_CALENDAR_READ    200
GET  /api/holiday-calendar/years/{calendar_year}    HOLIDAY_CALENDAR_READ    200, 422 (outside 2000 to 2100)
PUT  /api/holiday-calendar/years/{calendar_year}    HOLIDAY_CALENDAR_MANAGE  200, 409, 422
```

### `GET .../states`

The 36 states and union territories, in ELG-1's order: `state_code`, `state_label`, `state_kind_code`
(`STATE` | `UNION_TERRITORY`).

### `GET .../years`

```text
today                India's date
years[]              every year started, and the current and next year even when not started - only years from
                     2000 to 2100, so in 2100 no next year is offered - earliest first:
  calendar_year
  year_public_id, year_version                     null when not started
  is_complete
  complete_marked_by_display_name, complete_marked_at
  holiday_count                                    0 when not started
  updated_by_display_name, updated_at
```

### `GET .../years/{calendar_year}`

The year's summary as above, with `today` and `holidays[]`, earliest first (then all of India before states, then by
name):

```text
holiday_public_id, holiday_date, holiday_kind_code, holiday_kind_label, holiday_name, applies_to_code,
states[] {state_code, state_label}                 empty for all of India; in ELG-1's order
```

A year not started reads as `year_version` null, `is_complete` false, `holidays` empty.

### `PUT .../years/{calendar_year}`

Whole replacement of the year's holidays and its complete mark, guarded by the version last read.

```text
expected_version     null before the year is first saved; otherwise the version last read
is_complete          required: whether the year's calendar is complete
holidays[]           up to 1000
  holiday_date       inside the year
  holiday_kind_code  NATIONAL | FESTIVAL
  holiday_name       required, not blank, up to 255
  applies_to_code    ALL_INDIA | STATES
  state_codes[]      none with ALL_INDIA; one or more with STATES
```

Answer: `{"year": <the year as GET returns it>, "event": <the event, or null>}`.

- **First save** starts the year at version 1. **A change** moves the version by one. **The same again** - the same
  holidays in any order and the same mark - changes nothing, records no event, keeps the version.
- **The complete mark** records who marked it and when; kept while it stays marked, cleared when taken off.
- **Refused `409`**: a version that is not the current one, or null once the year is started - someone saved it after
  the caller read it. Nothing is written.
- **Refused `422`**, nothing written: a date outside the year; a kind other than the two; a name blank or too long; an
  "applies to" other than the two; all of India with states named; "these states" with none; a state not known, or
  `IN`; a state named twice on one holiday; two all-India holidays on one date; an all-India holiday and a state's own
  on one date; a state's holiday twice on one date; a year outside 2000 to 2100; no signed-in user.
- Any year may be changed at any time (Q3): every Work Order uses the calendar as it is now. The page warns before a
  save that touches a day already passed; the server does not refuse it.

All saves are serialized by the module's write lock (`pg_advisory_xact_lock`), and the year and its holidays are read in
one statement, so a read never mixes two versions.

## Events

```text
HOLIDAY_CALENDAR_YEAR_RECORDED | HOLIDAY_CALENDAR_YEAR_CHANGED
record_type = holiday_calendar_year, record_public_id = the year's public id, source_module = holiday_calendar
payload: calendar_year, year_version, is_complete, was_complete, holiday_count,
         added_dates[], removed_dates[], changed_dates[]      (a change of kind, name or states)
```

Dates, codes and counts only: a holiday's name never appears in a payload.

## What other modules read (no route)

- `calendar_between(db, first_day, last_day) -> CalendarReading`: every year the span touches - started, complete, its
  version - and every holiday on those days, from one statement. Work Orders reads the holidays that apply from it.
- `state_for_address(db, text) -> SiteState | None`: the state an address's free-text state names, as 8A matches a
  site's (`jurisdiction_for_state_text`).
- `last_year_started(db) -> int | None`.
- For the Alerts, through `eligibility/ports.py`: `CalendarYearSource.years_not_complete(db, years)` (a read, no lock)
  and `hold(db)` (the write lock alone, taken by marking reminders seen).

## The reminder for a year not set up (Q2)

On ELG-2's Alerts, a fifth kind: `HOLIDAY_CALENDAR_NOT_SET_UP`, "PBL's holiday calendar not set up" - see
`eligibility-api-contract.md`, "Reminders and escalation", and design section 5.4. It is raised for this year and next
until each is marked complete, dated 1 January of the year, and ends only with the mark. Only a year the calendar keeps
(2000 to 2100) is reminded: from November 2100 no reminder is raised for 2101, which could never be marked complete.

## Data (migration `20260908_0047_holiday_calendar`)

- **`holiday_calendar_year`**: public id; `calendar_year` (unique, 2000 to 2100); `year_version` (1 or more);
  `complete_marked_by`, `complete_marked_at` (both or neither); created and updated, by and at.
- **`holiday_calendar_holiday`**: public id; the year (a key on `(year_id, calendar_year)`, with a CHECK that the date
  falls in it); the date; the kind; the name (not blank); `applies_to_code`. A partial unique index allows one all-India
  holiday on a date.
- **`holiday_calendar_holiday_state`**: the holiday (a key on `(holiday_id, holiday_date)`) and a state (a key to
  `eligibility_jurisdiction`, never `IN`); unique on `(holiday_date, jurisdiction_code)`, so a state has one holiday on a
  date.
- That "these states" names at least one, and that an all-India holiday and a state's own are not on one date, are rules
  across rows the service owns under its lock.
- Nothing is loaded: every year's dates, the national ones included, are PBL's to enter (design 1.2, point 14).
