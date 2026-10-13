# Slice 7D Part 4 - the remaining billing terms

## Status

**IMPLEMENTED, ACCEPTED BY INDEPENDENT REVIEW AT ROUND 4, AND PASSED THE OWNER'S SCREEN CHECK, 24 September
2026.** Committed as `357bced` - exactly the accepted tree - with these records in the commit after it.
Records pass 23 September 2026; follow-up questions answered 24 September 2026 (decisions 27 to
31, below); built the same day - see "Part 4 as built". The owner answered questions 21 to 26 on 17 and 18
September 2026. Those answers were given in conversation and never written into the repository until
now; they are recorded below and they are the authority (ADR-013, level 1). The original questions and
the recommendations of the time stay where they were asked - `slice-7d-part-3-contract-period.md`,
"Part 4" - marked where an answer supersedes them.

Four further questions, and a proposal for where a standing rule belongs, were put to the owner after
the records pass and answered on 24 September 2026: see "Owner decisions, 24 September 2026".

```text
Branch                hiring/slice-7d-part-4-billing-terms
Worktree              <a separate worktree>
Baseline              bdc6053 (origin/main, PR #67 merged)
Alembic parent        20260908_0039 (Part 3)
Migration slot        20260908_0040 - CONFIRMED by the owner, 24 September 2026
Frozen contract hash  70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a, unchanged
Review                the independent reviewer, external; three-round cap, a fourth needs the owner's yes
```

Part 1 and Part 2 (`slice-7d-work-order-line-billing-terms.md`) and Part 3
(`slice-7d-part-3-contract-period.md`) are merged. TE-6 split the Work Orders service before this
package, so Part 4's term checks go beside Part 1's and Part 2's in `services/billing_terms.py`
(`CODING_STANDARDS.md`, "When a service outgrows one file").

## The owner's answers, 17-18 September 2026

| # | Topic | Answer | Against the recommendation of the time |
| --- | --- | --- | --- |
| 21 | Billing frequency (FRS 2.8.1) | **Leaves Part 4.** The invoice cycle belongs to the **equipment**, not to the Work Order or the line: one line can carry several machines, and so several cycles. It is recorded against equipment assignment (8A) and used by invoicing (8G) | Supersedes "on the Work Order, not the line" |
| 22 | Extra kilometres (FRS 2.5.6) | **As recommended.** Offer both an allowance **per day** and one **per month**, with a **rate per extra kilometre** | Agrees |
| 23 | Crew (FRS 2.5.6) | Operators and helpers are counted in **numbers per unit of work**, and the unit is the **line's own billing basis**: a day-basis line carrying 2 operators and 2 helpers, or 3 and 3. "Crew unit" was a wrong framing and that question is **withdrawn**. The only thing that may still be open is how crew beyond the count is charged | Supersedes "per shift"; the charge for extra crew is question (b) below |
| 24 | Weekly-off and holiday rates (FRS 2.4.5) | **Do not split them.** All holidays are treated the same: the Work Order either states a holiday rate or says it equals the overtime rate, and the existing single choice for off-day work (Part 1) already records both. **No migration for this** | The recommendation to separate them is **withdrawn** |
| 25 | Which days are holidays | **Holiday dates come into Part 4.** There are three kinds: **weekly off** (already recorded, as a line's weekly off days), **national holidays**, and **festival holidays the customer specifies**. National and festival dates are stated in the Work Order, so they are entered with it - not taken from a company calendar. They are kept as a **list: date, kind, optional description**, for log sheets and billing | Supersedes "not in this package"; where the list sits is question (a) below |
| 26 | A monthly line short of its contracted hours | A monthly shortfall is **deducted pro rata, with no minimum**, and there is **no new term**. What is wrong today is only the message: a monthly line refuses a minimum guarantee because "the monthly rate already covers the contracted month", which contradicts that rule. **Fix the wording**, and record the pro-rata rule for billing (8D) | Supersedes the explicit three-way choice |

**How question 22 is read.** "Offer both" is taken to mean both allowances are on offer as choices, and
each period records the one its Work Order states - per day **or** per month - with the rate per extra
kilometre. If a Work Order can state a daily and a monthly allowance at the same time, this reading is
wrong and the owner will say so.

**Answer 25, superseded in part on 2 October 2026.** The owner decided that PBL sets up a default
holiday calendar every year, with a facility in the system to do so; every Work Order inherits it,
and its own terms vary it - adding a holiday, or taking a calendar holiday off. "Not taken from a
company calendar" no longer holds. What Part 4 built is unchanged until the calendar is built; then
its list becomes the Work Order's variations (additions as today, and removals), and "names no
holidays" becomes "follows PBL's calendar unchanged". See `docs/agent/DEFERRED_REQUIREMENTS.md`,
"PBL's default holiday calendar".

**Built by HOL-1, 2 October 2026** (`hol-1-holiday-calendar.md`; `work-order-contract.md`, "HOL-1"): the answer codes
became `CALENDAR_UNCHANGED` and `CALENDAR_CHANGED`, each listed date became a change - a holiday added, as here, or a
calendar holiday made a working day at the normal or the overtime rate (the owner's answer to HOL-1's Q4) - and every
rule this part built for the list carries over. The rest of this record describes Part 4 as it was built.

## Standing rules, 17-18 September 2026

These are not Part 4 terms. They govern later slices and are recorded here because they arrived with
the answers.

**1. An operator's pay never derives from the customer's billed overtime.** PBL sets its operators'
hours. An operator contracted for 10 hours works 10 hours on a Work Order that specifies 8: the
customer is charged 2 hours of overtime, and the operator gets no overtime pay. Crew attendance and pay
take their hours from PBL's own HR terms, through the HR reference of ADR-032 - never from the Work
Order. The crew numbers Part 4 records are what the **customer** is charged for, not what anyone is
paid. Recorded against 8B in `FUTURE_SLICES.md`, and in `DEFERRED_REQUIREMENTS.md` beside the crew and
billing-term items.

**2. Contracts with customers, vendors and employees are independent of each other.** Where one depends
on another, it is created while **viewing** the other, and nothing is inherited automatically. Part 3's
"Apply these terms to other lines" is the pattern: it copies once, at the user's hand, and the copies
then stand on their own. Where it will bite:

- a vendor's hire terms for a hired machine (Market Hire, `MHA-001`) are written while looking at the
  customer's Work Order line, never derived from its rates, and never changed by a later change to them;
- an operator's hours and pay come from PBL's HR terms (rule 1), whatever the customer's Work Order says;
- a customer's Work Order amendment does not reach into a vendor's contract or an employee's terms.

Where rule 2 should live was question (e) below. The owner chose not to make it an ADR (decision 31):
it is recorded in `DEFERRED_REQUIREMENTS.md`, "Contracts are independent of each other".

## What Part 4 builds, once the questions are answered

- **Extra kilometres**, per period: not in the Work Order, or a number of kilometres included per day,
  or per month, with the rate per extra kilometre.
- **Crew**, per period: not part of the Work Order (equipment only), or the number of operators and
  helpers per billing unit of the line, and how crew beyond that number is charged (question (b)).
- **Holiday dates**: a list of date, kind (national or festival) and optional description, entered from
  the Work Order (questions (a) and (c)). Each date is checked against the contract with
  `contract_period_rules.py`, as Part 3 checks a period's start and a line's own dates: a date outside
  the contract, or in a gap before an extension, is refused naming both dates. Once a holiday is listed,
  the contract dates cannot move to exclude it, as they already cannot for a period start or a line date.
- **The monthly message** (answer 26). A monthly line still records no minimum guarantee; the refusal
  now says why correctly: a month short of the contracted hours is charged pro rata, with no minimum.
- **Completeness.** Two new items per period, `EXTRA_KILOMETRES` and `CREW`, reported until answered -
  "not in the Work Order" is an answer, blank is not. Every period saved before Part 4 therefore reports
  both, which is correct: they were never recorded. The holiday list reports its own missing item.

Nothing Part 1, 2 or 3 recorded changes, and the frozen handoff stays untouched.

## What leaves Part 4, and where it goes

| Item | Where it goes |
| --- | --- |
| Billing frequency | The equipment: recorded with equipment assignment (8A), used by invoicing (8G) |
| Separate weekly-off and holiday rates | Nowhere - withdrawn. Part 1's off-day choice already records both |
| A monthly shortfall choice | No term. Billing (8D) deducts a monthly shortfall pro rata, with no minimum |

## What Part 4 does not do

- No calculation. Extra-kilometre and extra-crew charges, the pro-rata monthly shortfall and billing a
  holiday all belong to billing (8D).
- No company holiday calendar. Holidays are the ones the Work Order states. (HOL-1 built the calendar, 2 October 2026.)
- No crew assignment, attendance or pay: those are 8B's, from PBL's HR terms (rule 1).
- No approval of any term.

## Owner decisions, 24 September 2026

The questions below were put to the owner after the records pass, and answered the same session:

| # | Decision |
| --- | --- |
| 27 (a) | **The holiday list sits on the Work Order**, one list for every line. Marking a holiday "only these lines" can be added later, without changing anything already entered, if a Work Order ever needs different festivals for different sites |
| 28 (b) | **Extra crew is charged at a rate for each extra operator and a rate for each extra helper, per billing unit of the line**, or is not in the Work Order. The operator and helper numbers are whole numbers; one may be zero ("2 operators, no helpers"), not both, because a Work Order with no crew at all is recorded as **equipment only** |
| 29 (c) | **An explicit answer beside the holiday list:** "The Work Order names no holidays" or "The Work Order names these holidays". Blank is not answered and is reported missing; "names these holidays" with no dates entered is still missing; "names no holidays" cannot be chosen while dates are listed |
| 30 (d) | **Migration slot `20260908_0040` confirmed**, parent `20260908_0039` |
| 31 (e) | **No ADR.** Standing rule 2 is recorded in `DEFERRED_REQUIREMENTS.md`, "Contracts are independent of each other", not as ADR-037 |

The table below is the questions as they were put, with the recommendations of the time, kept as a
record.

## Questions for the owner

Asked 24 September 2026; answered as recorded above.

| # | Question | Recommendation |
| --- | --- | --- |
| (a) | **Where the holiday list sits.** On the Work Order, or on each line? Sites in different states can have different festival holidays | **On the Work Order, one list for every line.** A customer usually states its holidays once. If a Work Order ever gives different festivals for different sites, each holiday can later be marked "only these lines" without losing or changing anything already entered - so starting with one list closes nothing off |
| (b) | **How crew beyond the count is charged**, if still open. And may a count be zero - "2 operators, no helpers"? | Per period: **not in the Work Order**, or **a rate for each extra operator and a rate for each extra helper, per billing unit of the line** - the same unit the counts use. Counts are whole numbers; zero is allowed for one of the two (no helpers), not for both, because a Work Order with no crew at all is recorded as "equipment only" |
| (c) | **"No holidays" against "not entered yet".** An empty list cannot tell them apart, and a recorded "none" must never look the same as a missing answer | **One answer beside the list:** "The Work Order names no holidays" or "The Work Order names these holidays". Blank means not answered, and the list is reported as missing. "Names these holidays" with no dates entered yet is still missing. "Names no holidays" cannot be chosen while dates are listed |
| (d) | **Migration slot.** | `20260908_0040`, after Part 3's `20260908_0039`. No other lane holds a migration open |
| (e) | **Where standing rule 2 lives.** An ADR, or `DEFERRED_REQUIREMENTS.md`? | **An ADR (ADR-037).** It is a rule about ownership between modules - customer billing, Market Hire and HR - of the kind ADR-017 and ADR-030 record, and it will govern slices not yet written. `DEFERRED_REQUIREMENTS.md` lists work still to build, and a principle filed there reads as a to-do and gets struck through with it. The ADR is written only if the owner agrees |

## Part 4 as built

Built 24 September 2026 against decisions 27 to 30, on the outline below, which held. The authoritative
description of routes, fields, refusals and events is the "Slice 7D Part 4" section of
`docs/agent/contracts/work-order-contract.md`; this section records the choices made while building and
why.

### The shape

```text
Migration 20260908_0040   nine columns and nine CHECKs on crm_work_order_line_billing_term;
                          crm_work_order_holiday_list (the answer, one row per Work Order);
                          crm_work_order_holiday (the dates, each belonging to the list row);
                          WORK_ORDER_LINE_BILLING_TERMS_WRITE's description reworded
services/billing_terms.py _part_4_term_values, _check_part_4_terms, _part_4_missing_items, after Part 1's
                          and Part 2's; the two new choices join _BASIS_DEPENDENT_TERMS, as Part 2's did
services/holidays.py      the holiday list's own concern module, importing only services/common.py
services/common.py        WorkOrderHolidayListConflictError, beside the module's other exceptions
services/contract_period.py  refuses a contract change that would exclude a listed holiday, reading the
                          dates straight from the repository so neither concern imports the other
Routes                    GET and PUT /api/work-orders/{public_id}/holidays
Frontend                  Extra kilometres and Crew cards in the "Extra charges" chapter; a Holidays
                          section under the Contract period, in "The Work Order" group
```

### Choices made while building, and why

- **Two holiday tables, not one.** The answer ("names no holidays" / "names these") and the dates are
  different facts. With the answer on a row of its own, "no row" means not answered - so a recorded
  "none" is a real row, exactly what decision 29 asks for - and a date row's foreign key to the list row
  means no date can exist without an answer beside it. That "names no holidays" holds no dates is a rule
  across the two tables that a CHECK cannot see; the service owns it, as Part 3's service owns a line
  date being inside the contract.
- **The list is replaced as a whole.** One PUT carries the answer and every date, guarded by one version,
  the Part 3 contract-period pattern. Each date row is recreated on every changing save, so a date's
  public id is not stable across saves; nothing refers to it, and the event records what changed by date.
- **Its own conflict error.** `WorkOrderHolidayListConflictError` rather than borrowing the contract
  period's: the error names what moved. It is the third name added to `service.py` after the split.
- **The billing-terms permission, reworded.** As planned; its description had not named Part 2's terms or
  Part 3's copying either, so the rewording corrects all three at once.
- **Holiday dates are checked both ways.** A date outside the contract or in a gap is refused as it is
  entered, and the contract cannot then move to exclude it - by an edit or by removing an extension - the
  rule Part 3 already applies to a billing period's start and a line's own dates. Gaps need no check on
  the contract side: a gap only ever follows the end an extension continues from, so any day in it was
  already after the contract's end and could not have been listed.
- **"Not answered yet" is offered only until an answer is saved.** The server has no way to take an
  answer back, so offering it afterwards would only invite a save the form then refuses.
- **Crew numbers are whole numbers sent as numbers, and the form checks them first.** A number that is
  not a whole number of 0 or more, or is beyond what the database can record, is refused on the screen
  naming the field in the line's own unit - "Helpers per day must be a whole number, 0 or more." The
  server refuses it too, but its refusal of a malformed number reaches the screen only as a generic
  message (review round 1, finding F-02). The number field is also capped at that largest value. Since
  round 2 (finding F-06) the same check covers the four Part 4 amounts, to the server's own limits.
- **The holiday list is read in one statement.** The answer and its dates come from one snapshot, so a
  read never returns a list that never existed (review round 2, finding F-05).
- **The monthly message.** Changed in the one place it is raised; a monthly line shows no
  minimum-guarantee field, so the new wording is reachable only through the API and is covered by a test.

### Independent review, round 1 (24 September 2026)

`CORRECTION_REQUIRED`, four material findings, packet `1fcfa119...`, tree `93a506b7`. All corrected:

- **F-01 - the crew CHECK could overflow.** "Not both zero" was written as the two numbers added together,
  which overflows an integer at the largest value the API accepts, turning a valid save into a server
  error. Found independently by the controller's own self-review the same day. Rewritten without
  arithmetic - at least one number not recorded yet or above zero - with tests at the largest value, one
  beyond it, and a direct insert of the largest value on both sides. **Migration `20260908_0040` is
  amended in place**: it has never been merged or deployed.
- **F-02 - a malformed crew number got only a generic message.** The form now checks the numbers before
  sending and names the field; see "Choices made while building".
- **F-03 - the holiday list's version CHECK had no test.** Added, naming the constraint; the test plan's
  wording about which keys are tested was narrowed to what is actually tested.
- **F-04 - `DEFERRED_REQUIREMENTS.md` still said the terms were not built.** Corrected, naming what
  remains open (calculation, 8D; assignment, 8B).

### Independent review, round 2 (24 September 2026)

`CORRECTION_REQUIRED`, two material findings, packet `36acd94e...`, tree `a76bacc2`. The round-1
corrections were not questioned. Both corrected:

- **F-05 - a read could mix two versions of the holiday list.** The answer and the dates were read in two
  statements, so a save committing between them could return version 1's "names no holidays" beside
  version 2's dates - a list that never existed. They are now read in one statement, which PostgreSQL
  answers from one snapshot. A test forces a save to commit straight after the read's first statement, in
  both directions (none to listed, listed to none), and asserts the read is version 1 whole while the save
  still lands. **Mutation proof:** with the two-statement read put back, both cases fail; the file was
  then restored byte-for-byte.
- **F-06 - the four new amounts could still reach the server malformed.** Round 1's form check covered the
  crew numbers only; kilometres included, the rate per extra kilometre and the two extra-crew rates could
  be sent as 0, negative, with three decimal places or too large, and the server's refusal reaches the
  screen only as "Check the values entered". The form check now covers every Part 4 number that would be
  sent, matching the server's own limits exactly - probed on the running backend: leading and trailing
  zeros ignored, 7 digits before the point for kilometres, 16 for rates, 2 after. A number that would not
  be sent is not checked, and a blank one is left to be reported missing.

Both findings have older relatives outside this package, recorded rather than fixed here:
`DEFERRED_REQUIREMENTS.md`, "Read consistency and number messages on the Work Order page".

### Independent review, round 3 (24 September 2026)

`CORRECTION_REQUIRED`, one material finding, packet `9dd3dc10...`, tree `30b245e3`. The round-2
corrections were not questioned otherwise, and the reviewer recorded no other material uncertainty.
Corrected:

- **F-07 - exponent forms slipped past the amount check.** A browser number field accepts `1e-3` or
  `1e7`, which the server reads as the plain number and refuses, and round 2's check let any exponent form
  through. The form now writes an exponent form out before counting its digits (`decimalDigits`), so
  plain and exponent forms meet the same limits. Every case in the tests is the server's own answer,
  probed on the running backend (`1e3`, `9.99e6`, `1e-2` accepted; `1e-3`, `1.5e-2`, `1e7` refused for
  kilometres; `1e16` refused for a rate). **Mutation proof:** with round 3's behaviour put back, both new
  exponent tests fail; the file was then restored byte-for-byte.

A fourth round is beyond the owner's three-round cap and needs the owner's explicit yes.

### Independent review, round 4 (24 September 2026)

Authorised by the owner beyond the cap. **`ACCEPTED`, no findings**, packet `2a013402...`, reviewed tree
`15d5ac5df35a65f23c25f9063ddfbbc0528163dd`, committed unchanged as `357bced`. Four rounds found 4, 2, 1 and
0 material findings; each correction held in the round after it, and each carries a test shown to fail
with the correction removed.

### The owner's screen check, 24 September 2026

**PASS**, on the seeded `work-order-billing-terms-part-4` scenario (`WO-002658`), against steps 1 to 17 of
the acceptance checklist.

### Test data

`.\scripts\smoke-data.ps1 seed -Scenario work-order-billing-terms-part-4` builds the screen-check Work
Order described in the acceptance checklist. The Part 3 scenario's two term sets gained the Part 4 answers
("not in the Work Order", "equipment only") so its lines still read "Terms complete".

### Test plan, as implemented

```text
backend/tests/test_slice_7d_part_4_billing_terms.py   63 (58 at round 1)
  every rule the API refuses (codes, values without their choice, both crew numbers zero, not positive,
  not whole, unknown field, before the basis, non-finite); what is recorded on every basis, one crew
  number zero; what is reported missing, the order of the two new items; the monthly message; events
  carry no value; copying terms carries Part 4; every CHECK by a direct insert naming its constraint, and
  every legal shape accepted directly
backend/tests/test_slice_7d_part_4_holidays.py        54 (50 at round 1, 52 at round 2)
  not answered, names none, names these with none, listed in date order, descriptions, case; what is
  refused; each date against the contract (before, after, first and last day, in a gap, no contract
  recorded); the contract cannot then move to exclude a holiday, by an edit or by removing an extension;
  versions, identical save, a read never mixing two versions, event payload with no wording; roles,
  signed out, Closed, not found; the handoff writes none; by a direct insert naming the constraint,
  every CHECK (the answer, the version,
  the kind), one list per Work Order, one date per list, and a date's foreign key to its list
backend/tests/test_te6_work_orders_service_surface.py  6 (3 new): names added after the split
backend/tests/test_smoke_data_harness.py               +1: the scenario, and cleanup of holidays added later
frontend workOrderHolidaysState.test.ts                15
frontend workOrderBillingTermsState.test.ts            +16 (Part 4 payload rules, the number and amount checks, exponent forms, labels, tags)
frontend workOrderPageState.test.ts                    +3 (the holiday list in the page-load generation)
```

## Engineering outline (written before the build; it held)

- **Migration `20260908_0040`** (if confirmed): nullable columns on `crm_work_order_line_billing_term`
  for extra kilometres and crew; the holiday list in its own table(s), outside `crm_work_order` and
  `crm_work_order_line` so the handoff neither writes nor returns it. Every number finite and greater
  than zero, except the crew counts in (b). Every rule a CHECK written NULL-safe (`CASE` or
  `IS NOT DISTINCT FROM`), each tested by inserting rows.
- **`services/billing_terms.py`**: `_part_4_term_values`, `_check_part_4_terms` and
  `_part_4_missing_items`, after Part 1's and Part 2's, which fixes the order of refusals and of
  `changed_fields`. Copying terms between lines copies the new columns with the rest, column by column.
- **The holiday list** gets its own concern module importing only `services/common.py`, re-exported from
  `service.py`. The TE-6 surface test gets a separate pinned set for names added after the split;
  `PUBLIC_NAMES_BEFORE_THE_SPLIT` is not edited.
- **Permission**: the holiday list is written under `WORK_ORDER_LINE_BILLING_TERMS_WRITE`. Holidays
  decide which days take the holiday rate, so who may change a rate should decide them too - the
  reasoning Part 3 gave for copying terms. No new permission.
- **Events** carry dates, codes and counts, never an amount and never the description text. New routes
  go in `POST_BASELINE_NEW_ROUTES`, and that fixture is read by eye after any merge.
- **Smoke data**: cleanup covers the new table(s) under the TE-3/TE-4 provenance rule, and a new scenario
  seeds a Work Order for the owner's screen check.
- **Frontend**: two new cards, Extra kilometres and Crew, in the existing "Extra charges" chapter - the
  7D.1 layout stays as built - and the holiday list. Every screen rule is a pure function with tests,
  because the frontend still has no component-test capability. Date inputs are capped with
  `DATE_INPUT_MAX`.
