# Slice 7D Part 5 Acceptance - the shift pattern, and the crew's food, accommodation and travel

Written so a later tester can perform regression/UAT without this session's chat history. Design, the owner's answers
of 9 October 2026 and the assumptions taken where they left a point open:
`docs/agent/slices/slice-7d-part-5-crew-upkeep-and-shifts.md`.

## Preconditions

This slice adds migration `20260908_0052`; `alembic/` is baked into the backend image, so after merging rebuild
before testing:

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend alembic current
```

Expected: the single head (`20260908_0052`). Rebuild the frontend image too (`docker compose up -d --build --no-deps
frontend`): its source is not bind-mounted.

Frozen contract check, before and after: `sha256sum docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md`
gives `0f16ff221e897f6199c352204a0ecced6f9a67f0c6695ad97c08c9dc2cd39080`.

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| Part 5 rules through the routes and the database | `docker compose exec backend pytest tests/test_slice_7d_part_5_upkeep_and_shifts.py -q` | all pass |
| Slice 7D Parts 1, 2 and 4 (term sets now answer the shift pattern) | `docker compose exec backend pytest tests/test_slice_7d_work_order_line_billing_terms.py tests/test_slice_7d_part_2_billing_terms.py tests/test_slice_7d_part_4_billing_terms.py -q` | all pass |
| Resource requirements read the shifts a day | `docker compose exec backend pytest tests/test_wrr001_resource_requirements.py -q` | all pass |
| Harness scenario and cleanup | `docker compose exec backend pytest tests/test_smoke_data_harness.py -q` | all pass |
| Full backend regression and E2E | CI, `Required validation` | success |
| Migration from empty, with a night shift to convert, refusals, down and up | the scripted check in the continuity note | as recorded there |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence | clean |

## Test data

```powershell
.\scripts\smoke-data.ps1 seed -Scenario work-order-contract-period
```

It builds a Work Order with three lines (the Slice 7D Part 3 scenario, extended for Part 5):

- **line 1**, by the month, with two billing-terms periods:
  - **from contract start**: two shifts - 10 hours, then 8 hours - each at its own rate: shift 2 at 90% of the first
    shift's rate (the Work Order rate), 26 working days a month; overtime counted over the whole month and **per
    shift**; one operator and one helper. Their food and accommodation are provided by the customer, except the
    **helper's accommodation, INR 3,000 per person per month, billed to PBL separately**; the **operator's trip to and
    from the job, INR 2,500 per person per trip, deducted from PBL's invoice**; daily travel is not in the Work Order;
  - **from 1 July 2027**: three 8-hour shifts at one rate, 624 contracted hours a month, overtime counted day by day
    and **for the whole day**;
- **line 2**, by the shift, shifts and crew both "not in the Work Order" (equipment only);
- **line 3**, no terms.

The output names the Work Order. Open it as **Sales User** (`sales1`) and go to **Billing terms**.

## The owner's screen check

Each step says where it is. "Save" means the period's own **Save terms** button; its message appears just beside it.

1. **Line 1, first period** ("From contract start"), chapter **Working time**: a **Shifts** card sits between the off
   days and **Overtime**. It shows *Two shifts*, *Shift 1 hours* 10, *Shift 2 hours* 8, *A rate set for each later
   shift (shift 1 at the Work Order rate)*, *Shift 2 is charged at* % of the first shift's rate (the Work Order
   rate), 90, and 26 working days. In **Overtime**, *On these shifts, overtime is counted*: Per shift. Tag: **Answered**. There is no
   **Night shift** card anywhere.
2. Same period, chapter **Extra charges**: after **Crew** (1 operator, 1 helper) comes **Crew food, accommodation and
   travel**: four items - Food, Accommodation, Travel to and from the job, Daily travel to site - each with
   **Operators** and **Helpers** side by side. Check the answers in the test data above, including *The cost is* per
   person per month and *The customer recovers it* Billed to PBL separately for the helpers' accommodation, and *The
   cost is* per person per trip for the operator's travel. Open *The cost is* on a travel item: it offers per person per
   trip, or per trip whatever the number of people. Tag: **Answered**.
3. **Line 1, second period** ("From 1 July 2027"): *Three shifts*, three 8-hour boxes, *The same rate for every
   shift*. In **Overtime**, *Overtime counted* Day by day, then **On these shifts, overtime is counted**:
   For the whole day.
4. *Negative, the day's 24 hours*: in that period change *Shift 1 hours* to **10** and **Save**. Expected beside the
   button: "The shifts add up to 26 hours, more than the 24 hours in a day." Nothing is saved (reload: still 8).
5. Put *Shift 1 hours* back to 8. Change *Overtime counted* to **Over the whole month, after contracted hours**: the
   *On these shifts* choice stays (it is asked however the month counts overtime). **Save**: "Terms saved."; the
   period stays complete.
6. **Line 2** (by the shift): set *Crew* to **The Work Order states the operators and helpers**, *Operators per shift*
   **2**, *Helpers per shift* **0**, *Crew beyond these numbers* Not in the Work Order. A **Crew food, accommodation and
   travel** card appears with an **Operators** column only. **Save**. Expected: the line's summary reads "Terms missing:
   crew food, accommodation and travel" and the card's tag **Still needed**.
7. In that card set the operators' *Food* **Provided by the customer**; *Accommodation* **Provided by the customer at a
   cost**, leave the cost empty; travel both **Not in the Work Order**. **Save**: saved, and still **Still needed**
   (the cost is missing). Enter **150**, *per person per day*, *Deducted from PBL's invoice*; **Save**: **Answered**,
   line complete.
8. Change *Helpers per shift* to **1**: the **Helpers** column appears, empty. Press **Same as for operators**: the
   helpers' answers become the operators'. Change the helpers' food to **Not in the Work Order**; **Save**: complete.
9. *Negative, an amount*: set a helper cost to **0** and **Save**. Expected beside the button: "Accommodation for
   helpers must be greater than 0." (or the item you changed). Nothing is saved.
10. **Line 2**: *Shifts a day* **Two shifts**: the hours boxes and *The shifts are charged* appear, and **Overtime**
   asks *On these shifts, overtime is counted*. **Save** with them empty: saved, line summary "Terms missing: overtime,
   shifts". Fill 12 and 8, **The same rate for every shift**, **Per shift**; **Save**: complete.
11. **Line 3**: **Start billing terms**, choose **Hour**: no Shifts card; choose **Day**: the Shifts card appears. Choose
   *Shifts a day* **One shift**: one hours box, no rate choice and no overtime counting question; with **Not in the Work
   Order**, no hours box at all.
12. *Read-only*: sign in as **Finance** (`finance1`), open the same Work Order. The same cards show as text; the
   helpers' accommodation on line 1 reads "INR 3000.00 per person per month; billed to PBL separately by the customer".
   No Save button.
13. *Copying*: back as `sales1`, on line 1 **Apply these terms to other lines**, tick line 3 and apply, confirming
   the replacement (step 11 started its terms). Line 3 now shows line 1's shifts and crew upkeep in both periods.

## Assumptions to confirm (from the slice document, A1 to A15)

For each, say "agreed" or what a real Work Order says instead.

- Travel is two separate items: the trip to and from the job and daily travel to site. Every cost says what it is for:
  food and accommodation per person per day or per month; travel per person per trip or per trip, daily travel per
  person per day or per day, whatever the number of people.
- "Deducted from PBL's invoice" or "billed separately" is recorded for each item and for operators and helpers
  separately. **Same as for operators** saves typing when they are the same.
- An **equipment only** line is asked nothing about crew upkeep; a Work Order stating **0 helpers** is asked nothing
  for helpers.
- A Work Order saying PBL arranges the crew's food or travel itself is recorded as **Not in the Work Order**.
- **Not in the Work Order** for shifts means the Work Order states no shifts; **One shift** records one stated shift and
  its hours ("one shift of 10 hours").
- **The same rate for every shift** and **A rate set for each later shift** record the Work Order's words. How billing
  counts them is assumption A9, which bears on money and waits for your confirmation. The reading so far: the same rate
  covers every shift in the line's billing unit (a monthly rate covers all the month's shifts; a rate per shift applies
  to each shift), and a rate for each later shift keeps the night shift's choices: per shift, per hour or a % of the
  first shift's rate (the Work Order rate - what the night shift's "% of the normal rate" meant, and what you called
  "the day rate"), with its own working days on a monthly line.
- The contracted hours are entered as the Work Order states them and are not checked against the shift hours. Which
  shifts they cover is assumption A10, which bears on money: the reading so far is the hours the Work Order rate buys -
  every shift with the same rate for every shift, the first shift alone with a rate for each later shift.
- The shifts of one day add up to no more than 24 hours.
- **Per shift or for the whole day** is asked whenever overtime is charged on two or three shifts (A12). How that
  answer applies when overtime is counted over the whole month bears on money and waits for your confirmation.
- An hourly line has no shift pattern.
- The resource requirement page says "2 shifts a day" where it said "night shift charged", and nothing when the Work Order states no shifts.
- **Four bear on money and must be confirmed before billing is built: A9, A10, A12 (its whole-month part) and A15.**
  The one most likely to differ (A15): a later shift's percentage is of the Work Order rate the first (day) shift is
  charged at - what you agreed for the night shift on 14 September ("% of normal") and called "the day rate" in your
  answer. Say if any Work Order means a rate per day instead.

## Results

Not yet run. Record the outcome here: Pass / Pass with minor issues / Fail - functional / Fail - usability / Blocked,
with any defect beside its step number.

## Known manual gaps

- The frontend has no component-test capability, so the cards' layout and wiring are covered by this screen check;
  the rules behind them by `workOrderBillingTermsState.test.ts`.
- Nothing is calculated: no deduction, separate bill, shift billing or overtime is worked out (8D).
- A Part 2 night shift "not in the Work Order", kept by the migration and shown beside the shift question ("Recorded
  before 10 October 2026..."), arises only from the upgrade, so the seeded data cannot show it; the migration check and
  `test_a_kept_legacy_night_shift_answer_is_read_and_never_changed_by_a_save` cover it. On a site upgraded with Part 2
  data, open any such period to see it.
