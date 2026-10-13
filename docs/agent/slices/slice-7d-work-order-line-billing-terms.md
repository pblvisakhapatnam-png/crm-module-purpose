# Slice 7D - Work Order Line Billing Terms

## Status

**Part 1: AGREED, 14 September 2026; integrated through PR #61 (`eed77ea`), without an ACCEPTED
review by owner decision** (see "Integration decision"). The owner agreed all seven questions as
recommended.

**Part 2: AGREED, IMPLEMENTED and ACCEPTED, 15 September 2026.** Independent review accepted it at round
2, after round 1's three material findings were corrected, and the owner's screen check passed. See
"Part 2" at the end of this document.

Track 2 (Hiring), second package. Foundation Slice Mode.

```text
Branch                 hiring/slice-7d-work-order-line-billing-terms
Worktree               <a separate worktree>
Baseline commit        3ee414d (origin/main)
Alembic parent         20260908_0036 (Slice 7C line operational detail)
Migration slot         20260908_0037, assigned by the owner to the Hiring lane
Frozen contract hash   accepted-offer-to-work-order-handoff-contract.md
                       sha256 70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a
Review                 one independent review (the slice carries a migration and a new permission)
Review cap             three rounds; a fourth needs the owner's explicit yes
```

## Why this slice exists

Slice 7C gave each Work Order line its site, billing identity, billing basis and contracted hours.
A billing slice still could not bill the line, because nothing records **what the customer agreed
to pay**: the rate, whether overtime is paid and how it is counted, what happens to breakdown and
idle hours, how a part month is charged, and so on. `WBT-001` (APPROVED) lists that term set, says
the Work Order owns it with effective versions, and says **only terms that are explicitly recorded
may be calculated**.

Sources, all directional under ADR-013 unless noted:

```text
WBT-001 (APPROVED, binding)     minimum term set; versions; missing terms never guessed; INR
FRS 2.4 Billing Basis & OT      four bases; month OT modes; contracted-hours gate; different rates for
                                normal, OT, breakdown, 2nd shift, holidays; OT as % of normal
FRS 7.4 Billing & Financial     cumulative vs daily overtime; breakdown hours x breakdown rate;
                                same-day OT offsetting "if enabled in the Work Order"
FRS 7.1 / Compliance            idle hours caused by the customer are billable as working hours;
                                mobilisation reversal after minimum contract months; demobilisation
                                charged only if the contract ends before a set time
Annexure-7 T&C (Hiring)         mobilisation charge, demobilisation waiver after N months, 10 h/day
                                excluding Sundays and holidays, breakdown deducted pro rata, OT per
                                hour, diesel supplied free at N litres/hour with excess as debit note
Annexure-10 Log Sheet           the six worked billing examples this design is tested against
```

## Owner decisions from Slice 7C that bind this slice (not re-asked)

- Billing terms are entered **when the customer's Work Order is entered**.
- Missing details **block at Work Order release (7B)**, not earlier.
- Site, billing basis, contracted hours and customer line reference **lock at mobilisation**;
  billing GSTIN and address lock at e-invoice. Neither event exists yet.
- A **Closed** Work Order refuses changes.
- Only explicitly recorded terms may be calculated; missing terms are never guessed (`WBT-001`).
- Amounts are **INR**.
- 7D comes **before `WRR-001`**.

## Owner decisions, 14 September 2026

Put in plain language, per `AGENTS.md`. **The owner agreed every recommendation below as written.**

| # | Question | Recommendation (agreed) |
| --- | --- | --- |
| 1 | **How much to build at once.** Recording every billing term in one package is large. Should it be split into two? | **Split.** Part 1: the periods, the rate, working days and holidays, overtime, breakdown, idle time, minimum guarantee and part-month charging - everything the six Annexure-10 examples need. Part 2: night/second shift, mobilisation and demobilisation charges, and fuel. Part 2 adds fields to what Part 1 builds and needs its own migration slot (`20260908_0038`) when it starts. One package is possible but is likely to need more than three review rounds |
| 2 | **Terms that change on a date.** Can a line's terms change part-way through the contract - for example a lower monthly rate after the first six months? | **Yes.** Terms are recorded in periods. The first period starts with the contract; each later period has its own start date and replaces the previous one from that date |
| 3 | **Work Order rate different from our quote.** The rate on the customer's Work Order may differ from the rate in our accepted offer. Allowed? | **Allowed.** The screen shows the quoted rate beside the Work Order rate so the difference is visible. No approval step in this package - approval rules need `APR-001`, which is later |
| 4 | **Terms the Work Order does not mention.** If the customer's Work Order says nothing about, say, overtime or breakdown, what should be recorded? | **The user chooses "Not in the Work Order" for that term.** A term left blank shows as missing and will block release. Nothing that is not written in the Work Order is ever charged or deducted |
| 5 | **Who may enter and change billing terms?** | **Sales User, Sales Manager, Operations and Admin** - the same people who enter the rest of the line's details in 7C, since the terms come from the same Work Order. Finance and Management see them read-only. It gets its own permission, so the list can be changed later without affecting site and billing details |
| 6 | **When the terms lock.** Billing basis and contracted hours already lock at mobilisation. Should all the other billing terms lock then too, with later changes made only through a Work Order Amendment that starts a new period? | **Yes.** Nothing is enforced in this package because mobilisation does not exist yet; it is recorded for the mobilisation slice |
| 7 | **The choices offered for each term.** Are the choices in the table below the forms you see in customer Work Orders? | **Start with these.** Add another choice when a real Work Order needs it, rather than guessing now |

### The choices offered (question 7)

"Not in the Work Order" is always a choice and means not charged or not deducted.

| Term | Choices | Applies to |
| --- | --- | --- |
| Overtime | Rate per hour, or a percentage of the normal hourly rate | Shift, Day, Month |
| Overtime hours counted (monthly) | Hours the machine was **available** at the customer's request, or hours it **actually worked** by the hour meter | Month |
| Overtime counted over (monthly) | The **whole month**, after contracted hours are completed (shortfall is made up first), or **day by day** | Month |
| Breakdown | **Reduce the billed hours** pro rata, or a **separate deduction** at a breakdown rate (per hour or % of normal) | Shift, Day, Month |
| Breakdown offset | Same-day overtime may offset breakdown hours: yes / no | Shift, Day, Month, when breakdown is deducted |
| Idle time caused by the customer | Paid as **working hours**, paid at a **standby rate** (per hour or % of normal), or not paid | all |
| Weekly off days | Which days of the week are off (none is allowed, for a 7-day week) | Shift, Day, Month |
| Work on an off day or holiday | Charged at the **overtime rate**, a **holiday rate** (per hour or % of normal), or the **normal rate** | Shift, Day, Month |
| Minimum guarantee | At least N billing units per month (for example 200 hours, or 25 days) | Hour, Shift, Day |
| Part month (monthly rate) | Divided by the **calendar days** in that month, the **contracted working days** (for example 26), or **30 days** | Month |
| *Part 2:* Night / second shift | Rate per shift or hour, or % of normal; contracted hours for that shift | Shift, Day, Month |
| *Part 2:* Mobilisation | Charge amount; credited back if the machine stays beyond N months | all |
| *Part 2:* Demobilisation | Charge amount; not charged if the machine stays beyond N months | all |
| *Part 2:* Fuel | Supplied by PBL and included, supplied by PBL and charged, or supplied by the customer at an agreed N litres per working hour (and per travel hour), with excess recovered as a debit note | all |

Hour-based lines have no overtime, breakdown, off-day or part-month terms: `WBT-001` settles that
hourly billing uses actual working hours only.

## Design (engineering)

Written for Part 1, with decisions 1-7 as agreed. Part 2 adds its rows from the table above as
columns on the same table, in the same pattern.

### Where 7C's billing basis and contracted hours go

**They move into the billing terms, and leave the 7C table.**

`WBT-001` puts the billing UOM and the normal-hours definition inside the versioned term set, and
they are exactly what a mid-contract amendment changes (for example 10 hours a day becoming 12).
Kept on 7C's single, unversioned row they could not have a start date, so a new period's overtime
rate would be read against hours that had silently changed for the months already worked. Keeping
them in both places would mean two answers to one question.

Consequences, stated rather than hidden:

- Migration `20260908_0037` copies every 7C row's `billing_uom_code` and
  `contracted_hours_per_billing_unit` into a first period for that line, then drops both columns and
  the three CHECK constraints that govern them (`ck_wol_detail_billing_uom`, `ck_wol_detail_hours_positive`,
  `ck_wol_detail_hours_not_hourly`) from `crm_work_order_line_detail`. The same rules are recreated
  on the new table. Downgrade restores the columns from the **first** period only; later periods
  cannot fit a single row and are lost on downgrade. That is acceptable for a downgrade and is
  written into the migration docstring.
- One 0036 state cannot be carried: contracted hours with **no** billing basis. The 7C service never
  wrote it, but 0036's CHECK allowed it (a NULL CHECK passes). Period 1 may hold no term before a basis,
  so rather than drop those hours silently the upgrade **refuses to run** while such a row exists, and
  its message says what to correct (review round 1). It refuses the same way for contracted hours stored
  as `NaN`, which 0036's `> 0` CHECK accepted (review round 4).
- The 7C `PUT .../detail` stops accepting the two fields, and `GET .../line-details` stops returning
  them and stops listing `BILLING_BASIS` and `CONTRACTED_HOURS` as missing. Those move to the billing
  terms response. This changes a merged 7C route, so `work-order-contract.md`'s 7C section is updated
  and the 7C tests that pin its shape are updated to match - moved, not weakened: every 7C rule about
  basis and hours reappears as a 7D test.
- The pilot at the CRM pilot site runs `c2a34fb`, which predates 7C, so no pilot data is
  affected.
- 7C's meaning of contracted hours is kept exactly: **per billing unit**, so 8 for a shift, 12 for a
  day, **260 for a month**. Monthly lines add contracted working days per month (26), and the screen
  shows the derived hours per day (10). The Annexure-10 month example needs all three.

### Records

```text
crm_work_order_line_billing_term          one row per period of one Work Order line

id                                         integer identity PK
work_order_line_billing_term_public_id     UUID string, unique
work_order_line_id                         FK -> crm_work_order_line.id
period_number                              1, 2, 3 ...  UNIQUE (work_order_line_id, period_number)
effective_from                             date; NULL for period 1 (starts with the contract),
                                           required for every later period
term_revision                              integer >= 1; the conflict check, like 7C's detail_version
currency_code                              'INR' only

billing_uom_code                           HOUR | SHIFT | DAY | MONTH                     (from 7C)
contracted_hours_per_billing_unit          numeric(9,2) > 0; NULL for HOUR                (from 7C)
contracted_working_days_per_month          numeric(5,2) > 0; MONTH only
normal_rate_amount                         numeric(18,2) > 0, per billing unit

weekly_off_day_codes                       varchar(3)[] subset of MON..SUN; NULL = not recorded,
                                           empty = 7-day week; never all seven days; not HOUR
off_day_work_treatment_code                NONE | OVERTIME_RATE | HOLIDAY_RATE | NORMAL_RATE; not HOUR;
                                           OVERTIME_RATE never with overtime NONE
holiday_rate_method_code / _amount / _percent

overtime_rate_method_code                  NONE | RATE_PER_HOUR | PERCENT_OF_NORMAL; not HOUR
overtime_rate_amount / overtime_rate_percent
month_overtime_hours_basis_code            AVAILABLE_HOURS | ENGINE_HOURS; MONTH only
month_overtime_counting_code               WHOLE_MONTH | DAY_BY_DAY; MONTH only

breakdown_treatment_code                   NONE | REDUCE_BILLED_HOURS | DEDUCT_AT_BREAKDOWN_RATE; not HOUR
breakdown_rate_method_code / _amount / _percent
breakdown_offset_by_same_day_overtime      boolean not null default false

customer_idle_treatment_code               NONE | AS_WORKING_HOURS | STANDBY_RATE; not before a basis
standby_rate_method_code / _amount / _percent

minimum_guarantee_code                     NONE | UNITS_PER_MONTH; not MONTH
minimum_billing_units_per_month            numeric(9,2) > 0

part_month_basis_code                      CALENDAR_DAYS | CONTRACTED_WORKING_DAYS | THIRTY_DAYS; MONTH only

term_notes                                 unicode text; never read by any calculation
created_by / created_at / updated_by / updated_at
```

Every term column is nullable: **NULL means "not recorded yet"** and shows as missing; `NONE` means
"Not in the Work Order" and is complete. That distinction is the whole of question 4.

Each of the four `*_rate_method_code` groups follows one rule: `RATE_PER_HOUR` needs the amount and
no percent; `PERCENT_OF_NORMAL` needs the percent and no amount; otherwise both are empty.
`breakdown_offset_by_same_day_overtime` defaults to false because the source makes offsetting an
option that exists only "if enabled in the Work Order" - absence is the source's own meaning, not a
guess.

**Database constraints**, so a direct INSERT cannot store a term a billing engine would misread:
the code domains; positive amounts, percents, hours and days; `currency_code = 'INR'`; the rate
method/amount/percent rule for each group; the period-1-has-no-date rule; `period_number >= 1`,
`term_revision >= 1`; no term before a basis (idle time included); never all seven days off; off-day
work at the overtime rate never with overtime "not in the Work Order"; and the basis applicability
rules (every "not HOUR" column NULL on an HOUR period, every "MONTH only" column NULL otherwise,
minimum guarantee NULL on MONTH). Each comparison is written to be TRUE or FALSE when the other column
is empty, because a CHECK that evaluates to NULL passes. The service
enforces the same rules with readable messages, plus what a CHECK cannot see: effective dates
strictly increasing across a line's periods.

**Why typed columns rather than one JSON document.** A billing engine will read these terms; typed
columns let the database refuse a nonsensical combination and keep every term queryable. The table
is wide but uniform, and Part 2 adds columns in the same pattern.

**Why a separate table, again.** The frozen handoff writes `crm_work_order_line` and the frozen
contract describes its output. As in 7C, nothing here touches that table, the handoff insert, the
handoff response or the 6O.2 amendment snapshot.

### Normal rate versus the quoted rate

`crm_work_order_line.rate_amount` stays exactly as the handoff copied it: the rate in our accepted
offer, kept for history as `WBT-001` requires. `normal_rate_amount` is the rate on the customer's
Work Order. The screen pre-fills the Work Order rate field from the quoted rate when a billing basis
is first chosen on a period with no rate entered - not when the empty period is created, because no
term may be stored before a basis - and shows both (question 3). The pre-filled value is only a
starting value in the form, marked "Filled in from the quoted rate", which the user checks and saves;
neither is derived from the other after that. A later period copies the latest period's saved rate.

### Completeness, advisory and computed on read

Per period, `missing_items` draws from:

```text
BILLING_BASIS              no basis
CONTRACTED_HOURS           SHIFT, DAY or MONTH without contracted hours
CONTRACTED_WORKING_DAYS    MONTH without working days per month
NORMAL_RATE                no Work Order rate
WEEKLY_OFF_DAYS            SHIFT, DAY or MONTH with off days not recorded
OFF_DAY_WORK               SHIFT, DAY or MONTH with no off-day treatment; or a holiday rate without
                           its method; or the overtime rate while overtime is not recorded
OVERTIME                   SHIFT, DAY or MONTH with no overtime choice
MONTH_OVERTIME_METHOD      MONTH, overtime charged, hours basis or counting not chosen
BREAKDOWN                  SHIFT, DAY or MONTH with no breakdown choice
IDLE_TIME                  no idle-time choice
MINIMUM_GUARANTEE          HOUR, SHIFT or DAY with no minimum-guarantee choice
PART_MONTH                 MONTH with no part-month choice
```

A line's terms are complete when it has at least one period and every period is complete; a line
with no period reports `NO_TERMS`. Nothing is blocked; release (7B) will refuse an incomplete line.
7B then checks two things per line - 7C's site and billing identity, and these terms.

### Save semantics

All writes lock the Work Order row (`lock_work_order_row`), refuse a Closed Work Order, and check
the line belongs to the Work Order in the path.

```text
POST   add a period
       body: expected_period_count (periods the caller saw), expected_latest_term_revision (the latest
             period's revision the caller saw; null when there is none), effective_from, all terms
       count or latest revision differs     -> 409, nothing written (review round 2: the count alone
                                               does not change when the latest period is edited)
       first period with a date, or a later period without one  -> 422
       later period on the first calendar date (0001-01-01)     -> 422 (the period before it could
                                                                    have no end date)
       date not after the previous period's date                -> 422
       -> insert at the next period_number, revision 1, event WorkOrderLineBillingTermsPeriodAdded

PUT    replace one period (whole replacement)
       body: expected_term_revision, effective_from, all terms
       revision differs                      -> 409
       period 2+ date not strictly between its neighbours       -> 422
       nothing would change                  -> 200 with current state, no event, no revision bump
       changed                               -> revision + 1, event WorkOrderLineBillingTermsPeriodUpdated

DELETE remove the latest period, only when the line has more than one
       query: expected_term_revision
       not the latest, or the only period   -> 422
       revision differs                      -> 409
       -> event WorkOrderLineBillingTermsPeriodRemoved
```

Period 1 cannot be deleted; it is corrected in place. The screen sends one write at a time per line
- start, add, save and remove share one guard and every action on the line is disabled while one is in
flight - because each response carries the whole line and two concurrent writes could answer out of
order (review round 2). Every response is read and built inside the
transaction, under the lock, before commit - 7C review round 1 found the post-commit read defect and
this does not repeat it. Any period may be edited while the Work Order is not Closed; locking periods
that have been billed belongs to the mobilisation and billing slices (question 6).

### Routes

```text
GET    /api/work-orders/{public_id}/billing-terms
       require_permission(WORK_ORDER_READ)
       one entry per Work Order line, in line order

POST   /api/work-orders/{public_id}/lines/{line_public_id}/billing-terms
       require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE)

PUT    /api/work-orders/{public_id}/lines/{line_public_id}/billing-terms/{term_public_id}
       require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE)

DELETE /api/work-orders/{public_id}/lines/{line_public_id}/billing-terms/{term_public_id}
       require_permission(WORK_ORDER_LINE_BILLING_TERMS_WRITE)
```

All four are new and go in `POST_BASELINE_NEW_ROUTES`, never in the frozen PF-1A-E1 inventory.
That fixture fails silently on a bad merge; it is read by eye after any merge that touches it.

Response entry:

```text
work_order_line_public_id, line_number, source_offer_line_public_id
quoted_uom, quoted_rate_amount                    the handoff copy, read-only
current_period_number                             latest period whose start is on or before today
                                                  (India time), else 1; null with no periods
periods[]:  term_public_id, period_number, effective_from, effective_to (derived: next period's
            start minus one day, or null), term_revision, every term column,
            derived_hours_per_working_day (MONTH), is_complete, missing_items[],
            updated_by, updated_by_display_name, updated_at
terms_complete, line_missing_items[]              NO_TERMS, or the union across periods
```

Write responses return the line's entry as `line_billing_terms` alongside `event` (null on a no-op).

### Permission

```text
WORK_ORDER_LINE_BILLING_TERMS_WRITE   ADMIN, SALES_USER, SALES_MANAGER, OPERATIONS_USER   (question 5)
  "Record or change a Work Order line's billing terms: rate, overtime, breakdown, idle time and periods."
```

Added to `POST_BASELINE_ROLE_PERMISSION_MATRIX` and seeded in `20260908_0037`, following the 0035
and 0036 seed pattern. `WORK_ORDER_LINE_DETAIL_WRITE`'s description is updated to drop "and billing
basis" - in the contract module and in the migration's seed row, so the description no longer
promises something the permission no longer governs. The frozen 31 / 110 / 76 baseline is unchanged.

### Events

```text
WorkOrderLineBillingTermsPeriodAdded
WorkOrderLineBillingTermsPeriodUpdated
WorkOrderLineBillingTermsPeriodRemoved
source_module = work_orders, record_type = work_order, record_public_id = Work Order public id
payload: work_order_line_public_id, term_public_id, period_number, effective_from, term_revision,
         billing_uom_code, changed_fields[]
```

**No amounts, rates or percentages in any payload**: they are commercial data, and `CODING_STANDARDS.md`
keeps sensitive commercial values out of logs; `changed_fields` says which terms changed without
saying to what.

### Frontend

On the existing Work Order detail page only; `frontend/src/routes.tsx` is not touched.

- A "Billing terms" section, one collapsible card per line following the 7C.1 pattern: the summary
  shows basis, current Work Order rate and a "Terms complete" or "Missing: ..." badge; an incomplete
  line starts open.
- A line with no terms yet shows **Start billing terms**, which creates an empty period 1 for the user
  to fill in.
- Inside a card, the periods in order ("From contract start", "From 1 March 2027"), each a form in
  short labelled groups: basis and hours; rate (quoted rate shown beside it); working days and off
  days; overtime; breakdown; idle time; minimum guarantee or part month. Fields that do not apply to
  the chosen basis are hidden, not merely disabled, so an hourly line shows a short form.
- "Add a later period" asks for a start date and copies the latest period's terms as the new period's
  values, saved at once; the user then edits them. "Remove this period" appears on the latest period
  when there is more than one.
- Weekly off days are a tick box, "The Work Order states the weekly off days", with a day tick box
  for each day beneath it: unticked is not recorded; ticked with no day chosen is a 7-day week.
- "Show terms for all lines" and "Hide terms for all lines" appear when there is more than one line
  (worded differently from the 7C section's "Expand all lines" so the two cannot be mistaken).
- Save and Add show their success or error message directly beneath their button. Start and Remove
  change the list itself - the Start button disappears once period 1 exists, and a removed period's form
  disappears with it - so their result is shown in one message line below the line's periods, where
  those buttons were (review round 1). A Remove error, which leaves the period in place, shows beneath
  the Remove button. A `409` reads "Someone else changed these terms. Reload to see their version."
- The 7C "Site and billing details" card loses its billing basis and hours fields; the Lines table's
  "Site and billing" cell reads the basis from the current period.
- **No new visible link or button text containing "Open"** on this page: Playwright matches link
  names by case-insensitive substring and 7C's first CI run failed on exactly that. The page's existing
  "Open" links are not renamed: existing specs click them by that name (corrected in review round 1,
  which read an earlier wording as applying to every link on the page).

## The Annexure-10 examples, and what each needs recorded

No calculation is built. Instead, each worked example must be recordable as a complete term set that
states every input its calculation reads, and a test records each one.

| Annexure-10 example | Terms recorded |
| --- | --- |
| Hour-wise (265 h worked, 265 billed) | HOUR, rate; idle time and minimum guarantee chosen |
| Shift-wise (8 h shift, OT above 8, breakdown below 8) | SHIFT, 8 h, rate; overtime rate; breakdown treatment; off days and off-day work; idle; minimum guarantee |
| Day-wise (12 h day) | DAY, 12 h, the rest as shift-wise |
| Month, cumulative, OT normal hours (260 + 14 OT) | MONTH, 260 h, 26 days, off day SUN, rate; overtime rate; AVAILABLE_HOURS; WHOLE_MONTH; breakdown REDUCE_BILLED_HOURS; off-day work OVERTIME_RATE; part month |
| Month, cumulative, OT engine hours (260 + 10 OT) | as above with ENGINE_HOURS |
| Month, non-cumulative (260 + 18 OT + 4 breakdown lines) | as above with AVAILABLE_HOURS, DAY_BY_DAY, breakdown DEDUCT_AT_BREAKDOWN_RATE with a breakdown rate |

The example does not state a part-month rule because it is a full month; the test records
CALENDAR_DAYS, the method FRS 2.4 describes for monthly rates. (The full-text extract shows "Month hours 4" in the
engine-hours block, an extraction slip for 260; the source `.docx` controls and nothing here
depends on it.)

## In scope (Part 1)

- `crm_work_order_line_billing_term`, migration `20260908_0037`, moving 7C's basis and hours into it.
- The Part 1 term set above, periods with effective dates, revision conflict checks, advisory
  completeness computed on read.
- Four routes, one permission, three events.
- A "Billing terms" section on the Work Order page; 7C's card and Lines cell adjusted.
- Smoke-data harness: a billing-terms builder, cleanup deletes billing terms before Work Order lines,
  and the 7C line-detail builder loses its two fields.

## Explicitly not in scope

- Any change to what `POST /api/work-orders/from-commercial-offer` accepts or returns,
  `WorkOrderResponse`, `WorkOrderLineResponse`, `WORK_ORDER_LINE_SELECT_COLUMNS` or
  `crm_work_order_line`.
- Part 2 terms: night/second shift, mobilisation, demobilisation, fuel (question 1).
- Any calculation, billing result, log sheet or Billing Worksheet.
- Locking periods at mobilisation or once billed; the e-invoice lock (question 6).
- Applying a Work Order Amendment to create a period (`D-07`, parked); approval of a Work Order rate
  that differs from the quote (`APR-001`).
- Contract valid-from and valid-to dates (header, 7B). Period 1 therefore has no date of its own.
- From `WBT-001`'s minimum term set, deliberately deferred and recorded here as a deviation:
  **taxable-value adjustment terms** and **approved exception/variation references** (both belong
  with billing and approvals), and precision and rounding settings (a Finance setting before billing
  goes live).
- Invoice presentation: the single-line average-rate bill, and showing off-day hours as normal-day
  overtime for a customer whose ERP requires it (Annexure-10 notes 1 and 4).
- Different working times on different weekdays; extra kilometre and extra crew charges.
- Hourly-line holiday premiums and shift/day engine-hours overtime: not in the source; add when a
  real Work Order needs them.
- A new Playwright spec.

## The work_orders boundary, and how it is proven

Same four proofs as 7C:

1. The frozen contract file hash before (above) and after must match.
2. The existing handoff shape-pin test in `test_slice_7c_work_order_line_detail.py` is unchanged and
   passes.
3. A test asserts the handoff inserts no `crm_work_order_line_billing_term` row.
4. The diff shows no change to `create_work_order_from_commercial_offer`, `WorkOrderResponse`,
   `WorkOrderLineResponse` or `WORK_ORDER_LINE_SELECT_COLUMNS`.

## Test plan - each written to fail against code that lacks the rule

`backend/tests/test_slice_7d_work_order_line_billing_terms.py`:

```text
Periods
  first period: POST with no date creates period 1 at revision 1 and records PeriodAdded
  first period with a date -> 422; later period without a date -> 422
  later period dated on or before the previous period's date -> 422
  PUT moving period 2's date past period 3's -> 422
  stale expected_period_count on POST -> 409, nothing written
  changing PUT bumps revision and records PeriodUpdated with changed_fields
  identical PUT -> 200, no event, revision unchanged
  stale expected_term_revision on PUT and on DELETE -> 409
  DELETE of period 1 when alone -> 422; DELETE of a period that is not the latest -> 422
  effective_to and current_period_number derived correctly around today's date
  the returned entry is the revision its event records; a failure building it leaves nothing written
  a concurrent save cannot change the revision another save reports (two paused sessions)

Terms
  HOUR period refuses overtime, breakdown, off-day, contracted hours and part-month terms -> 422 each
  idle time before a basis -> 422; off-day work at the overtime rate with overtime NONE -> 422
  MONTH-only terms refused on SHIFT; minimum guarantee refused on MONTH
  each rate group: amount with PERCENT_OF_NORMAL, percent with RATE_PER_HOUR, neither when needed -> 422
  non-INR currency, zero or negative amounts, percents, hours, days -> 422
  unknown code in any domain -> 422

Completeness
  a line with no periods reports NO_TERMS
  an empty SHIFT period lists exactly its items; an empty HOUR period lists only its own
  NONE counts as recorded; NULL does not
  off-day work at the overtime rate while overtime is unrecorded lists OFF_DAY_WORK and OVERTIME
  MONTH with overtime charged but no hours basis lists MONTH_OVERTIME_METHOD
  empty weekly_off_day_codes (7-day week) is complete; NULL is missing
  each of the six Annexure-10 term sets records and reports complete

Moving 7C's fields
  7C PUT no longer accepts billing_uom_code or contracted_hours_per_billing_unit (422, extra field)
  7C line-details no longer returns them nor lists BILLING_BASIS / CONTRACTED_HOURS
  the 7C shape test pins the new, smaller entry

Permissions
  SALES_USER, SALES_MANAGER, OPERATIONS_USER, ADMIN may POST, PUT, DELETE
  FINANCE_USER and MANAGEMENT_READ_ONLY get 403 on writes and 200 on GET
  unauthenticated gets 401 on all four

Boundary and events
  handoff inserts no billing-term row; handoff key sets unchanged
  no event payload contains an amount, rate or percent
  CLOSED Work Order refuses POST, PUT, DELETE

Database
  a direct INSERT breaking each kind of rule is refused, including every rule whose other side can be
  NULL (a CHECK that evaluates to NULL passes in PostgreSQL)
  UNIQUE (work_order_line_id, period_number) rejects a duplicate period
```

Also: the route-permission guard recognises all four routes; a smoke-data cleanup test removes a
Work Order whose line has billing terms; frontend pure-rule tests for which fields a basis shows, what
the form sends when a field is hidden, the period labels and the completeness badge (the frontend
still has no component-test capability).

The migration itself - upgrade from 0036 carrying real 7C rows into period 1, `downgrade -1`
restoring them from period 1 only, and upgrade again - is not a pytest test: this repository has no
migration test harness, and 7C checked its migration the same way. It is a scripted check in a
scratch database inside the running Postgres, recorded in the continuity note.

## Allowed files

```text
backend/alembic/versions/20260908_0037_work_order_line_billing_terms.py         new
backend/app/modules/work_orders/contract.py, schemas.py, repository.py,
    service.py, routes.py                                                       additive, plus removing
                                                                                7C's two fields
backend/app/modules/authorization/contract.py                                   one permission, one description
backend/tests/fixtures/post_baseline_tightened_routes.py                        four new routes
backend/tests/test_slice_7d_work_order_line_billing_terms.py                    new
backend/tests/test_slice_7c_work_order_line_detail.py                           basis/hours tests moved out
backend/tests/test_commercial_offers_api.py                                     shared cleanup helper: terms first
backend/tooling/smoke_data/builders.py, cleanup.py, tests/test_smoke_data_harness.py  new table and builder
frontend/src/pages/work-orders/WorkOrderDetailPage.tsx                          wiring only
frontend/src/pages/work-orders/WorkOrderBillingTermsSection.tsx                 new component
frontend/src/pages/work-orders/workOrderBillingTermsState.ts and .test.ts        pure rules and tests
frontend/src/pages/work-orders/WorkOrderLineDetailsSection.tsx                  remove basis and hours
docs/agent/contracts/work-order-contract.md                                     a 7D section; 7C section updated
docs/agent/slices/slice-7d-work-order-line-billing-terms.md                     this file
docs/agent/acceptance/slice-7d-work-order-line-billing-terms-acceptance.md      new
docs/continuity/SLICE_7D_WORK_ORDER_LINE_BILLING_TERMS.md                       new
docs/continuity/NEXT_STEPS.md, docs/agent/DEFERRED_REQUIREMENTS.md,
    docs/agent/FUTURE_SLICES.md                                                 status and deferred items
```

`main.py` and `routes.tsx` are not touched. Stop and report if: the migration parent is no longer
`20260908_0036`; any handoff key-set assertion would need changing; a rule cannot be expressed
without altering `crm_work_order_line`; or the frozen contract hash differs.

## Verification gate before proposing the candidate

```text
1. Frozen contract hash equal to the baseline above.
2. Empty-database migration: upgrade to head, constraint assertions, a 7C row seeded at 0036 and
   carried into period 1, downgrade -1 restoring it, upgrade again.
3. Backend image rebuilt (alembic/ is baked in), alembic current = 20260908_0037.
4. Rule-removal check on the conflict check, the date ordering and one basis rule; backend container
   recreated afterwards, not just the file restored.
5. Full backend regression, run alone.
6. Frontend typecheck, test and build; frontend image rebuilt before any screen check.
7. Full E2E suite against the worktree stack.
8. python scripts/check_tracked_secrets.py, python scripts/validate_contract_fixtures.py,
   git diff --check, git ls-files --eol on new files.
9. A seeded Work Order with a monthly and an hourly line for the owner's screen check
   (sign-in cannot be done from these sessions).
```

## Review record

External bounded independent review (read-only, no tools, one hashed packet),
under the three-round cap.

### Round 1 - CORRECTION_REQUIRED (packet sha256 efff9faf...fc5953, candidate tree 7be070f)

Six material findings and one advisory. Each was checked against the code, held, and was corrected in
the same round:

1. **Migration could lose hours.** A 0036 row with contracted hours but no basis was legal in the
   database (its CHECK evaluated to NULL) and was not copied, then its column was dropped. Upgrade now
   refuses to run while such a row exists, with a message naming the correction. The migration check
   seeds that row and confirms the refusal leaves the database at 0036 with no partial table.
2. **Off-day work at the overtime rate with overtime "not in the Work Order"** was accepted and
   reported complete, though it cannot be priced. Now refused by the service and by
   `ck_wol_term_off_day_overtime_needs_overtime`; while overtime is still unrecorded, off-day work is
   reported missing. API, completeness and direct-insert tests added.
3. **Idle time before a basis** was accepted, and the form sent it while hidden. Idle time joined the
   basis-first rule in the service, the CHECK and the form; tests added, including a frontend rule that
   nothing is sent once the basis is set back to not chosen.
4. **All seven days off** was refused by the service but allowed by the CHECK. The CHECK now refuses an
   array containing every day; direct-insert test added.
5. **"Open" link text.** This document said no link on the page may start with "Open"; the page already
   had such links, which existing specs click by name. The wording was wrong, not the page: it now
   covers text this package adds.
6. **Feedback placement.** Start's confirmation rendered under the Add button, and a successful Remove
   showed nothing because its form unmounted. Both now report in one message line below the line's
   periods, where those buttons were.
7. **Advisory: boundary tests.** Zero contracted hours (API and database), zero working days, zero
   percent, zero minimum units and a part-month term on an hourly line are now tested individually.

Three of the new direct-insert tests were first run, by accident, against a database still holding
the round-1 constraints (Alembic does not rerun an applied revision): all three failed there and pass
after `0037` was re-applied - direct evidence that they catch the gap they were written for.

### Round 2 - CORRECTION_REQUIRED (packet sha256 dadadca7...cceb1, candidate tree 899ff77)

Four material findings, each checked against the code, held, and corrected in the same round:

1. **A later period starting 0001-01-01** was accepted, and deriving the previous period's end date then
   overflowed into an unhandled `500`. `_check_period_start` now refuses the first calendar date with a
   `422`; test added, and 0001-01-02 is still accepted.
2. **Adding a period from stale terms.** The period-count check did not move when the latest period
   was edited, so a period copied from what the caller saw could be built from terms since changed.
   `POST` now carries `expected_latest_term_revision`, checked under the Work Order lock; tests for a
   stale revision (409, nothing inserted, no event) and a revision given before any period exists.
3. **Out-of-order responses on the screen.** Separate forms on one line could write at once and an older
   whole-line response could overwrite a newer one. All writes for a line now go through one guard
   (`createLineWriteGuard`, with a synchronous flag against a double click) and every action on the line
   is disabled while one runs; pure-rule test added.
4. **The quoted-rate pre-fill** this document promised was not implemented. The form now pre-fills the
   rate from the quoted rate when a basis is first chosen on a period with no rate (`formAfterBasisChange`),
   never overwriting a typed rate or a period that already had a basis; tests added. This section's
   wording was corrected to say when the pre-fill happens, since an empty period 1 cannot store a rate.

Rule-removal check for the two new server rules: removing the latest-revision comparison failed 2
tests, removing the first-calendar-date refusal failed 1; restored, `service.py` identical, 3 pass.

### Round 3 - CORRECTION_REQUIRED (packet sha256 d5028fd5...951bc1, candidate tree 561d380)

Two material findings and one advisory, each checked against the code, held, and corrected. The reviewer
recorded that the backend - frozen handoff, migration and downgrade, constraints, authorization, period
locking and conflicts, completeness and event values - was otherwise supported by the packet.

1. **The read-only view hid a recorded monthly overtime choice.** Both rows were gated on the hours
   basis alone, so a period with only the counting choice showed neither. The rows are now shown
   whenever overtime is charged on a monthly line, each with "-" for a gap (`showsMonthOvertimeRows`);
   pure-rule tests cover each one-sided combination.
2. **A failed refresh kept stale forms editable.** The Work Order page kept the earlier entries and
   their "loaded for" marker when a reload failed. Line details and billing terms now share one loaded
   list state (`LoadedList`): a load marks nothing loaded until it succeeds, and a failure drops the
   entries, so no form is editable from a load known to have failed. The same fix was applied to the
   7C line-details load on the same page, which had the identical pattern. Pure-rule tests cover a
   success followed by a failed refresh.
3. **Advisory: a test that could fail by chance.** The event-payload test searched the whole payload,
   including random public ids, for digit strings. It now checks the field types and searches only
   the fields that could carry a value.

This was the third round, so the three-round cap is reached. A fourth round needs the project owner's
explicit yes.

### Round 4 - CORRECTION_REQUIRED (packet sha256 c4a69b14...ffffc2, candidate tree 2f135ae)

Authorised by the project owner beyond the three-round cap. Three material findings, each checked
against the code, held, and corrected:

1. **NaN passed every "positive" CHECK.** PostgreSQL `numeric` can hold `NaN`, which compares greater
   than every number, so `col > 0` accepted it; a 0036 row with NaN hours would also have been copied
   into period 1. Every numeric CHECK now also requires a finite value, and the upgrade refuses to run
   while a 7C row holds NaN hours. Direct-insert tests for NaN; the migration check seeds a NaN row and
   confirms the refusal.
2. **A failed Work Order reload could still leave stale terms current.** The round-3 fix lived inside the
   line-detail and billing-term loaders, and a failed `/lines` request returns before they run. Every
   Work Order load now supersedes any load or save in flight and clears lines, line details and billing
   terms before anything is fetched; a line whose terms have not loaded says so rather than "no terms".
3. **A multi-dimensional off-days array** passed containment (which ignores shape) and would break the
   read. The CHECK now requires a one-dimensional array; the empty array for a 7-day week still passes,
   with a test proving it.

Proof for the database fixes: with `ck_wol_term_positive_values` and `ck_wol_term_off_days` put back in
their round-3 forms, exactly the four new direct-insert cases failed; restored, all 32 insert tests pass.

### Round 5 - CORRECTION_REQUIRED (packet sha256 2de9a5fa...7c2c06, candidate tree 8a2979f)

Authorised by the project owner, as round 4 was. The reviewer reported no further material defect in
the backend (migration, authorization, completeness, events, the handoff boundary, ordinary writes).
Two material findings:

1. **Corrected.** `ck_wol_term_first_period_has_no_date` did not refuse a later period dated
   0001-01-01, which the service refuses; a directly written row would make the line unreadable through
   the API (deriving the previous period's end date overflows). The CHECK now requires a later period to
   start after that date. The new direct-insert case failed against the round-4 form of the CHECK and
   passes against the fix; a second test proves 0001-01-02 is still accepted and the line still reads.
2. **Not corrected in Part 1; carried to Part 2 by owner decision (14 September 2026).** the Work Order detail page has no single load generation. The main Work Order and lines requests have
no generation check (since Slice 5A), and a finished save restarts the line-detail or billing-terms load
gate unconditionally (the Slice 7C pattern, copied by 7D). Navigating to another Work Order while one is
still loading, or pressing Refresh while a save is in flight, can therefore let an older response show
under the newer Work Order, or leave the billing terms read-only until the next reload. The server's
revision checks mean no stale screen can save a wrong value. Correction: one page-load generation (or
AbortController) covering the Work Order, lines, line-detail and billing-term loads and every save
callback; results apply only while their generation and Work Order are current, and a save started
before a newer load never invalidates it. Test it with component or integration tests for out-of-order
navigation and refresh during an in-flight save - the frontend has no component-test capability yet.

## Integration decision

The project owner decided on 14 September 2026 to commit Part 1 **without an ACCEPTED review**: five
rounds were run (the fourth and fifth authorised beyond the cap), every finding but round 5's second
was corrected, and that finding is carried to Part 2, whose slice document will list it first. This
follows the 7C precedent of an owner-accepted change without a further review round. The owner also
expects a full test before the Hiring work goes to UAT - perhaps at 7E - to iron out remaining wrinkles;
that is recorded in `docs/agent/DEFERRED_REQUIREMENTS.md` so it is not lost.

**Owner screen check, 14 September 2026.** Everything worked except one message: an error under "Add a
later period" ("A later period needs the date it starts from.") stayed on screen after later successful
saves, until a page refresh. Corrected after review: starting any write on a line now clears every other
control's message on that line (`feedbackIsStale`), so a message always belongs to the latest action;
pure-rule tests added. This change was not independently reviewed; the owner asked for it at the screen
check. The owner also confirmed period 1 stays as designed - once started it is corrected in place and
never removed, so "Start billing terms" does not return after the first save.

**Evidence correction.** The migration check's pass counts shown to the reviewer in rounds 1, 4 and 5
(23, 28, 28) were each one too high: the controller miscounted the output listings. The real counts were
22, 27 and 27, every listed check passed, and no check failed at any point. Corrected in the continuity
note on 14 September 2026, before commit.

---

# Part 2

## Status

**AGREED, IMPLEMENTED and ACCEPTED, 15 September 2026.** The owner agreed questions 8-12 as recommended
and confirmed migration slot `20260908_0038`. Independent review accepted the work at round 2, the owner's
screen check passed, and it was committed on the owner's instruction: first the accepted tree unchanged,
then this record.

```text
Branch                 hiring/slice-7d-part-2-billing-terms
Worktree               <a separate worktree>
Baseline commit        eed77ea (origin/main, PR #61 merged)
Alembic parent         20260908_0037 (Part 1)
Migration slot         20260908_0038, confirmed by the owner
Frozen contract hash   sha256 70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a (checked
                       at the baseline and after the work: unchanged)
Review                 one independent review; three-round cap, a fourth needs the owner's explicit yes
```

### Independent review, round 1 (15 September 2026): CORRECTION_REQUIRED, three material findings

All three were real, and are corrected. None was in the Part 2 rules themselves; two were places where
the recorded rule and the built rule had drifted apart, and one was a test that could not fail.

- **The month counts carried an invented maximum.** The request schema capped both month counts at 600
  while the contract and the database asked only for a whole number of at least one, so a documented-valid
  601 was refused by the API and accepted by a direct write. The owner never agreed a 50-year maximum, so
  the cap is removed rather than written into the contract. The one bound left is the integer column's own
  range, which is stated in the contract and in the schema: it exists so a nonsense number is refused as a
  readable `422` instead of failing at the database as a `500`.
- **The contract described a night-shift state the code cannot reach.** It listed "charged without its
  rate value" as a reported-missing case, but a chosen rate method carries its value in the same save -
  exactly as Part 1's overtime, holiday, breakdown and standby rates do, and the CHECK agrees. The code is
  right and consistent with Part 1; the contract wording was wrong and is corrected. What may genuinely be
  left for a later save is the night-shift hours, and on a monthly line its working days.
- **A direct-write test could not fail.** The case proving a later period cannot carry mobilisation used
  period 2 with no date, which Part 1's own CHECK already refuses, so it would have passed with Part 2's
  first-period-only CHECK removed. It now uses a real date, and a second test names
  `ck_wol_term_first_period_only_terms` in the refusal, so the rule cannot be dropped unnoticed.

One advisory finding was also correct and is fixed: the page's own subtitle still called the full billing
terms future work, which this slice implements. It now says the billing terms are held here and that the
billing which works them out is what comes later.

### Independent review, round 2 (15 September 2026): ACCEPTED

All four round-1 findings resolved, no new finding, nothing the reviewer could not judge. The round was a
correction review: the packet carried the exact tree-to-tree diff from the tree round 1 reviewed
(`a80b1510`) to the corrected one, with the corrected contract section and the re-gathered evidence,
rather than the whole candidate again - 46 KB against round 1's 300 KB, with nothing left out, because a
tree-to-tree diff cannot omit a change. The reviewer agreed that F2 was rightly fixed in the document
rather than the code.

Accepted tree `bc017b3a37c76538029b729594a7e04e1ad3b65e`, committed unchanged as the first Part 2 commit.

### Owner screen check (15 September 2026): PASSED

On the worktree stack against `WO-002674` - a monthly line whose first period held Part 1's terms only,
and an hourly line with no terms. Every step P2-1 to P2-11 passed, including Part 1's deferred
stale-message re-check (steps 11c and 11d).

Part 2 has two pieces of work, in this order:

1. **The Work Order page shows only its latest load** - carried from Part 1's review round 5.
2. **The Part 2 terms** - night / second shift, mobilisation, demobilisation and fuel.

Everything Part 1 settled (decisions 1-7, the owner's screen-check decisions, the design above) stands
and is not re-asked.

## Item 1 - the Work Order page shows only its latest load

### What goes wrong today, in plain language

The Work Order page loads its information in several steps: the Work Order, its lines, the site and
billing details, the billing terms, and some smaller lists. Two things can go wrong:

- **Going to another Work Order while one is still loading.** The first Work Order's answers can
  arrive late and appear under the second Work Order.
- **Pressing Refresh while a save is still running.** When the save finishes it can stop the refreshed
  billing terms (or site details) from ever becoming editable, until the page is reloaded.

Nothing wrong can be saved - the server's revision checks refuse a stale save - but the screen can
show the wrong Work Order's details or get stuck read-only.

### Design (engineering)

**One page-load generation replaces the two per-list gates.** Every load of the page - on opening a
Work Order, on navigating to another, on Refresh - takes a new generation number. Every result the page
receives carries the generation it was started in:

```text
Work Order request, lines request                      the load's generation
line details, billing terms                            the load's generation
related offers, amendments, handoff events, loading    the load's generation (same defect, same fix;
flag, page message and error                           Part 1's review did not name them, but they
                                                       share the pattern)
a save on a line (site details or billing terms)       the generation current when the save STARTED
```

A result is applied only while its generation is still the current one. **Applying a save never
starts a new generation** - that is the Part 1 defect: `onSaved` / `onApplied` called the list gate's
`begin()`, which invalidated a newer load that was already running.

Why one generation is enough, with no per-list gate: within one generation each list is loaded once,
and a line's form becomes editable only when that load has succeeded (`LoadedList.loadedFor`). So a
save in the same generation can never overlap its own list's load, and a save from an older generation
is discarded. The existing guards stay: one write at a time per line (`createLineWriteGuard`), messages
belonging to the latest write (`feedbackIsStale`), and a failed load leaving nothing editable
(`LoadedList`).

**Where the logic lives.** The decisions are a pure reducer, `workOrderPageState.ts`, holding the
page's loaded state (Work Order, lines, line details, billing terms, related offers, amendments, handoff
events, loading, message, error). Every action carries a generation; an action from a generation that
is not current returns the state unchanged. The page component only starts requests and dispatches
their results, so the ordering rules can be tested without a browser.

**What a discarded save means for the user.** If Refresh is pressed while a save is running, the save
still happens on the server, but its answer is not shown; the page shows what the refreshed load
returned. If that load read the terms before the save finished, the next save on that line is refused
as a conflict. The conflict message today says "Someone else changed these terms", which would be wrong
here - the user changed them. Part 2 rewords all three conflict messages (billing terms add and save,
site and billing details) to: **"These terms have changed since the page loaded. Reload to see the
latest version."** (and "details" for the site section).

### What can and cannot be tested

The frontend still has no component-test capability (`DEFERRED_REQUIREMENTS.md`).

```text
Tested by pure-rule tests (vitest), replaying out-of-order sequences through the reducer:
  - navigate A -> B, A's Work Order / lines / line details / terms / related offers arrive after B's:
    B's state is unchanged
  - navigate A -> B, A's answers arrive before B's: B's answers replace them when they arrive
  - Refresh while a save is in flight, save answers after the refresh started: discarded, and the
    refreshed load still becomes editable when it succeeds
  - a save in the current generation after its list loaded: applied, generation unchanged, still editable
  - a failed Work Order or lines request clears lines, line details and terms and leaves nothing editable
  - a stale failure (older generation) does not clear the newer load's state or error

Not tested automatically, and said so:
  - that the component passes the right generation into each request and save (the wiring). Covered
    only by reading the diff, the existing Playwright specs (which exercise ordinary loads and saves) and
    the owner's screen check.
  - real network timing. There is no way to hold a request open in the current test tooling.
```

## Item 2 - the Part 2 terms

### Questions for the owner

Put in plain language, per `AGENTS.md`. Each has a recommendation. Nothing in the "Choices offered"
table above is re-asked; these are points that table did not settle.

| # | Question | Recommendation |
| --- | --- | --- |
| 8 | **Once for the line, or in each dated period?** A line's terms are recorded in periods, so a new period can change them from a date. Mobilisation and demobilisation happen once - the machine arrives once and leaves once. Should they be recorded **once for the line**, while night shift and fuel follow the periods like the rate does? | **Yes.** Mobilisation and demobilisation are recorded once for the line (shown in the first period, marked "for the whole line"), and a later period does not copy or change them. Night shift and fuel belong to each period, because a Work Order amendment can change a night rate or the fuel average from a date. If an amendment ever changes mobilisation or demobilisation, that is handled when amendments are applied to Work Orders (parked as `D-07`) |
| 9 | **The "N months" for mobilisation credit and demobilisation waiver.** The Work Order says, for example, "demobilisation not charged if the machine works beyond 12 months". Is N always a whole number of months? | **Yes, whole months.** Only the number is recorded now. How the months are counted (from which date, and whether a part month counts) is decided by the billing slice, which will check it against real Work Orders |
| 10 | **What is separate for the night shift?** Annexure-10 gives the night shift its own hours per day, days per month and a possibly different rate. | **The night shift has its own rate, its own contracted hours, and on a monthly line its own working days per month. Everything else follows the line's day-shift terms:** overtime, breakdown, idle time, off days and holiday work. If a Work Order sets different overtime or breakdown rules for nights, add that choice when it is seen (decision 7) |
| 11 | **Fuel supplied by PBL and charged: how is the charge stated?** The choices table says "charged" but not how, and only a recorded method may be calculated. | **Two choices: "at an agreed rate per litre"** (the rate is recorded) **or "at actual cost"** (nothing more is recorded; billing uses the fuel bills). Add another form when a real Work Order needs it |
| 12 | **Fuel supplied by the customer: how is excess use measured?** Per month, per log sheet, or left to billing? | **Left to log sheets and billing.** The Work Order terms record only the agreed litres per working hour and, where the Work Order gives it, litres per travel hour. The FRS already describes the check (expected litres from working hours against actual use, day by day) and a deduction the billing team reviews before posting; that belongs with log sheets |

Also for the owner: **confirm migration slot `20260908_0038`** (parent `20260908_0037`) for the Hiring
lane.

### Design (engineering)

Written to recommendations 8-12. If the owner decides differently, this section changes before code.

**Records.** New columns on `crm_work_order_line_billing_term`, in the Part 1 pattern: every term column
nullable, NULL = not recorded (missing), `NONE` = "Not in the Work Order" (complete).

```text
Night / second shift (per period; SHIFT, DAY, MONTH only - NULL on HOUR)
night_shift_rate_method_code            NONE | RATE_PER_SHIFT | RATE_PER_HOUR | PERCENT_OF_NORMAL
night_shift_rate_amount                 numeric(18,2) > 0, finite; RATE_PER_SHIFT or RATE_PER_HOUR only
night_shift_rate_percent                numeric(7,2)  > 0, finite; PERCENT_OF_NORMAL only
night_shift_contracted_hours            numeric(9,2)  > 0, finite; required when the night shift is
                                        charged, NULL otherwise; counted per the line's billing unit,
                                        exactly like contracted_hours_per_billing_unit
night_shift_working_days_per_month      numeric(5,2)  > 0, finite; MONTH and charged only

Mobilisation and demobilisation (period 1 only - NULL on every later period; all bases)
mobilisation_charge_code                NONE | CHARGED | CHARGED_CREDITED_AFTER_MONTHS
mobilisation_charge_amount              numeric(18,2) > 0, finite; required when charged
mobilisation_credit_after_months        integer >= 1; CHARGED_CREDITED_AFTER_MONTHS only
demobilisation_charge_code              NONE | CHARGED | CHARGED_WAIVED_AFTER_MONTHS
demobilisation_charge_amount            numeric(18,2) > 0, finite; required when charged
demobilisation_waived_after_months      integer >= 1; CHARGED_WAIVED_AFTER_MONTHS only

Fuel (per period; all bases)
fuel_treatment_code                     NONE | PBL_SUPPLIED_INCLUDED | PBL_SUPPLIED_CHARGED | CUSTOMER_SUPPLIED
fuel_charge_method_code                 AGREED_RATE_PER_LITRE | ACTUAL_COST; PBL_SUPPLIED_CHARGED only
fuel_rate_per_litre_amount              numeric(18,2) > 0, finite; AGREED_RATE_PER_LITRE only
fuel_litres_per_working_hour            numeric(9,2)  > 0, finite; CUSTOMER_SUPPLIED only
fuel_travel_allowance_code              NONE | LITRES_PER_TRAVEL_HOUR; CUSTOMER_SUPPLIED only
fuel_litres_per_travel_hour             numeric(9,2)  > 0, finite; LITRES_PER_TRAVEL_HOUR only
```

"Credited after N months" and "waived after N months" are codes rather than a nullable number beside
`CHARGED`, so that "charged, no credit-back" is a recorded answer and a forgotten month count is
missing - the decision-4 distinction applied inside a term.

Why mobilisation lives on period 1 rather than in its own table: period 1 always exists once terms are
started and is never removed (owner, Part 1 screen check), so it is a stable one-row-per-line home. It
reuses Part 1's routes, revision check and lock with no new route or permission. The cost, stated:
saving mobilisation bumps period 1's revision, so a later period's add made from a stale view of period 1
gets the usual 409 when period 1 is the latest.

**Database constraints**, each written NULL-safe and finite as in Part 1: code domains; positive finite
values; integer months >= 1; the rate method/amount/percent rule for the night shift (with
`RATE_PER_SHIFT` needing the amount); night-shift hours present exactly when the night shift is charged;
night-shift days only on MONTH and only when charged; night-shift columns NULL on HOUR; mobilisation and
demobilisation columns NULL on every period after the first; amount present exactly when charged; months
present exactly for the credited / waived codes; each fuel sub-column present exactly when its parent
choice asks for it; no term before a basis (as Part 1). The service mirrors every rule with a readable
`422`, and every service rule has its CHECK.

**Completeness**, added to `missing_items`:

```text
NIGHT_SHIFT              SHIFT, DAY or MONTH with no night-shift choice; or charged without its rate
                         value, hours, or (MONTH) working days
MOBILISATION             period 1 with no mobilisation choice, or charged without amount / months
DEMOBILISATION           period 1 with no demobilisation choice, or charged without amount / months
FUEL                     no fuel choice; or a sub-choice or its value missing
```

**Routes, permission, events.** No new route or permission: Part 1's `POST` and `PUT` accept the new
fields and `GET` returns them. `POST` of a later period refuses mobilisation or demobilisation values
(`422`). Events keep Part 1's payload shape; `changed_fields` names the new columns and no amount,
rate, percent, litres or months value is ever in a payload.

**Frontend.** In each period form, three new short groups after "Idle time": **Night shift** (hidden on
an hourly line), **Fuel**, and - in period 1 only - **Mobilisation and demobilisation (for the whole
line)**. Hidden fields are never sent (`termsPayloadFromForm` gains the period number). "Add a later
period" copies night shift and fuel, never mobilisation. The page's "Not built yet" list drops the
night-shift, mobilisation, demobilisation and fuel line. No new text containing "Open".

**Migration `20260908_0038`.** Adds the columns and constraints; existing Part 1 rows get NULL for every
new term, so existing lines report the new items as missing - correct, since those terms were never
recorded. Downgrade drops the columns and constraints; Part 2 values are lost on downgrade, written into
the docstring.

### Explicitly not in scope (Part 2)

- Any calculation: mobilisation invoices, credit notes, demobilisation billing, fuel variance, debit
  notes, night-shift pay.
- Creating mobilisation or demobilisation Transportation orders; fuel sensors; diesel card balances.
- How the credit-back and waiver months are counted (question 9) and how fuel excess is measured
  (question 12).
- Separate overtime or breakdown rules for the night shift (question 10); different working times on
  different weekdays; extra kilometre and crew charges; food and accommodation.
- Locking at mobilisation; applying amendments (`D-07`); the frontend component-test capability.
- Any change to the handoff, `crm_work_order_line`, `WorkOrderResponse`, `WorkOrderLineResponse` or
  `WORK_ORDER_LINE_SELECT_COLUMNS`; the frozen contract file must hash the same after.

### Test plan (outline; written in full with the code)

```text
Backend (test_slice_7d_part_2_billing_terms.py)
  each new domain, positive/finite value, integer month and method-value rule: API 422 and direct INSERT
  non-finite numbers refused: through the API the schema refuses NaN and Infinity alike (422). Written
    directly, NaN is stored by the column and refused by the CHECK - which is the case the CHECK exists
    for - while Infinity never reaches the CHECK, because a numeric with a declared precision cannot hold
    it and PostgreSQL refuses it as out of range. Both are tested, and which refusal fires is recorded
    rather than assumed; the CHECKs still exclude Infinity, so the rule holds if a later column is ever
    declared without a precision
  night-shift columns refused on HOUR; night-shift days refused on SHIFT/DAY and when not charged
  mobilisation/demobilisation on period 2 refused by API and CHECK; add-period refuses them
  completeness: each new item appears and clears; NONE is complete, NULL is missing
  a full Part 1 + Part 2 term set records complete for a monthly and an hourly line
  no event payload carries a new value; handoff key sets unchanged; handoff inserts no term row
  rule-removal proof for two CHECKs and one service rule, recorded
Migration: upgrade 0037 -> 0038 carrying Part 1 rows (new terms NULL, rows readable), downgrade -1, upgrade
Frontend (vitest): the page reducer sequences above; night shift hidden on HOUR; mobilisation only in
  period 1 and never copied; each fuel sub-field sent only when its parent asks
```

### Screen check at the end (owner)

- Part 2's own checks, written into the acceptance checklist with the code.
- Part 1's stale-message fix, deferred to this check: acceptance steps 11c and 11d.
- A seeded Work Order with a monthly and an hourly line for both.

# Follow-up after merge (7D.1), 15 September 2026: the billing terms form's layout

From the owner's look at the merged form: every group of terms flowed top to bottom in identical thin
grey boxes, one field per row, so one group could not be told from the next. **Layout only.** No migration,
route, permission, event, contract or payload change, so self-review plus CI rather than an independent
review, as agreed with the owner - the same basis as 7C.1. The direction was agreed from a mockup before
any code, because it is a matter of taste and the implementation session cannot sign in to see the page.

1. **Three chapters, in the order a Work Order reads.** *The rate* (basis and rate), *Working time* (off
   days, overtime, breakdown, idle time and minimums) and *Extra charges* (night shift, fuel, mobilisation
   and demobilisation), coloured with the tones the rest of the application already uses: blue, teal and
   amber. A chapter with nothing to show for the chosen basis is left out.
2. **Each group is a card** with its title, one line on what it covers, and a tag: **Answered**, or
   **Still needed** while any item that group answers is in the period's missing items. The two helper
   texts that explained a whole group (night shift follows the day shift's terms; mobilisation is recorded
   once) became those groups' descriptions.
3. **Fields sit side by side** in columns of equal width, so a rate's method and its value, or the two
   monthly overtime choices, share a row. Mobilisation and demobilisation, and idle time and the minimum or
   part-month choice, each keep their own rows inside their card.
4. **Save terms has its own bar** with the notes and its message beside the button; **Add a later
   period** sits apart in a dashed box, so it does not read as part of the form. Finance's read-only view
   uses the same chapters and cards.
5. **Each period opens and closes**, added after the owner found that a line with several start dates
   stacked every full form, one after another. A closed period shows its start date, basis and rate, its
   Complete or missing tag, and **In force now** on the period that applies today when the line has more
   than one. Until the user opens, closes or edits a period, the **latest** is open - a change goes into
   it, and a new period copies it - and an earlier period is open only while it has gaps. Editing a
   period counts as choosing to keep it open, so saving an earlier period to complete does not close it
   under the user. The line card's own summary now uses the same summary helper.

What was kept exact, and how it was checked: every field binding, label and option list is the same as
before (compared mechanically - the only textual difference is two labels reading a local variable holding
the same value), and each group appears under the same basis and period conditions as before.

**The rules are pure and tested** (`workOrderBillingTermsState.ts`, 9 new tests): whether a period starts
open (`periodOpen`) and how it is summarised (`periodSummary`), which chapter a group
belongs to, which groups a basis and period show, which missing items each group answers - every item the
backend can report belongs to exactly one group, so a new item cannot go unflagged - and when a tag shows.
**No tag is shown while the form's billing basis differs from the saved one**: the missing items describe
the period as last saved, so after switching basis on screen the cards belong to a basis that report never
assessed, and "Answered" over empty fields would be untrue. Both rules were broken on purpose and exactly
their tests failed, then the file was restored by hash; the same was done for the rule that the latest
period starts open.

What cannot be tested: the layout itself. The frontend still has no component-test capability, so how the
cards look is the owner's screen check.
