# Slice 7D Part 3 and Part 4 - the contract period, and the remaining billing terms

## Status

**Part 3: IMPLEMENTED, 17 September 2026**, against the decisions agreed the same day (questions 13
to 20d, three of which carry a change of the owner's own). **Part 4: PROPOSED**, questions 21 to 26
still open and deliberately not built. Part 1 and Part 2 are merged; their design and owner decisions
1 to 12 are in `slice-7d-work-order-line-billing-terms.md` and are not re-asked here.

**Superseded for Part 4, 23 September 2026:** the owner answered questions 21 to 26 on 17 and 18
September. Part 4 now has its own document, `slice-7d-part-4-remaining-billing-terms.md`, which records
the answers and is the authority for Part 4. The questions and recommendations below are kept as asked;
the "Part 4" section marks which recommendations the answers replaced. Part 3 merged as `944af54`.

The owner confirmed migration slot `20260908_0039` (parent `20260908_0038`) on 17 September 2026,
and answered one question the agreed design had not covered - see "Putting a wrong end date right"
below.

**Owner's screen check, 22 September 2026:** six findings, and four decisions that change how an
extension is corrected and when the end date may be edited. The 17 September correction rule is
superseded. See "The owner's screen check, 22 September 2026" below; the fixes went to a fourth
review round, which the owner granted, and returned `ACCEPTED` with no findings. **The owner then
clarified the extension dates the same day** - an extension's own start date, and days no contract
runs on - which changed the package again; see "The owner's clarification of extension dates".

```text
Branch                hiring/slice-7d-part-3-contract-period, then Part 4
Baseline              e855862 (origin/main, PR #63 merged)
Alembic parent        20260908_0038 (Part 2)
Migration slot        20260908_0039 for Part 3 - CONFIRMED by the owner, 17 September 2026
                      20260908_0040 for Part 4 - still to be confirmed when Part 4 is scoped
Frozen contract hash  70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a, unchanged
Review                one independent review each; three-round cap
```

## Why this exists

The owner asked (15 September 2026) whether anything built or planned falls short of FRS 2.3 to 2.8.
The check found six items with no home; the record is in `docs/agent/DEFERRED_REQUIREMENTS.md`, "FRS
2.3 to 2.8 gap check". The owner's direction: **anything that has to be tested now so it can be used
later - contract validity, start and end dates - is done now**, as Part 3 if a separate package suits.

Sources, all directional under ADR-013 unless noted:

```text
WBT-001 (APPROVED, binding)  minimum term set; versions; missing terms never guessed; INR
FRS 2.3.7 / 2.3.8 / 2.3.9    no transaction beyond the contract end date unless extended; notice
                             before expiry; structured extension and renewal under approval
FRS 2.5.1                    daily log sheets run from the contract start date to completion or expiry
FRS 2.7.2 / 2.7.4            mobilisation credited back, and demobilisation charged, by how long the
                             equipment stayed against a minimum period
FRS 2.3.2                    line terms, with defaults inherited from the Work Order header
FRS 2.8.1 / 2.5.6 / 2.4.5    billing frequency; extra kilometres and extra crew; separate rates for
                             weekly-off and holiday work
WRR-001 (APPROVED)           a Resource Requirement carries a required start and end or scheduling window
```

## Sequencing

Part 3 comes before `WRR-001`, which needs the scheduling window these dates give it. Part 4 follows
Part 3. Both touch the same billing-terms screen as Slice 7D.1 (the layout package, awaiting merge),
so code starts once that is merged. **`D-04` and `D-06` block neither part.**

## Part 3 - the contract period

### Owner decisions, 17 September 2026

**The owner agreed every recommendation. Three carry a change of their own, marked below**, and two
answers correct how question 20 was written rather than what it does.

| # | Question | Decision (agreed) |
| --- | --- | --- |
| 13 | **Where the contract period is recorded.** | **Both, with the Work Order leading.** The Work Order holds the contract start and end dates. A line may carry its own start and end inside that period when the Work Order says so - a second machine arriving later, or leaving earlier. A line left blank follows the Work Order. When equipment actually arrives and leaves is a different thing, and comes later from mobilisation and log sheets |
| 14 | **A Work Order with no end date.** | **"Until the work is complete" is a recorded answer**, exactly as "Not in the Work Order" is for a term, and different from leaving the end date blank, which stays missing. **Owner's addition: the screen tells the user that the Work Order cannot be closed until a firm end date is recorded.** The wording goes in now; refusing closure belongs to the closure slice, and is recorded there (8E) |
| 15 | **Extensions.** | **Each extension is its own record**: the new end date, the customer's reference, the date it was received, and who recorded it. Previous end dates stay as history and are never overwritten, so what the contract said at any time is always recoverable. A renewal on changed rates is an extension plus a new billing-terms period from that date |
| 16 | **Approval of an extension.** | **No approval is asked for yet, and the screen says so in those terms: "Approval step not yet added".** The owner's point: "no approval step" leaves the reader unsure whether approval is needed at all, while this says plainly that the system does not ask for one yet. Approval rules need `APR-001`; recorded for Slice 8F |
| 17 | **What the dates change today.** | **Record, show and check within the Work Order only.** The page shows the contract state - not started, active, ends in N days, ended - and a period stops saying "From contract start" and shows the date itself. **Owner's addition: every refusal says why**, naming the dates: "This period starts on 1 May 2027, after the contract ends on 31 March 2027", and "The contract cannot end on 1 February 2027, because this line has terms starting 1 March 2027". The rule behind them is built and tested now, for log sheets, release and billing to use later |
| 18 | **Who may record and change the dates.** | **The same four roles as the rest of the line's details** - Sales User, Sales Manager, Operations, Admin - under a permission of their own, so extensions can later be narrowed to managers without touching code |
| 19 | **When the dates lock.** | **The contract start locks at mobilisation**, like the other terms (decision 6). After that the end date changes only through an extension record, never by editing in place. Nothing is enforced in this package, because mobilisation does not exist yet; it is recorded for the mobilisation slice |
| 20 | **Entering the same terms on several lines (FRS 2.3.2).** | **"Apply these terms to other lines"**, offered on a line whose terms are saved. **The source is whichever line you are standing on** - line 1, line 3, any of them - so it chooses its source as freely as copying line by line would have, and settles a ten-line Work Order in one action instead of nine. The owner weighed pushing against pulling and chose this, because the tick boxes make the lines that will change explicit before anything happens. It is a copy taken once, not terms inherited from a Work Order header: inheritance couples lines invisibly, and a later change to the header would silently change lines whose periods may already have been billed. A deliberate departure from the wording of 2.3.2, recorded as one |

### Question 20: how it actually works

The owner asked why the list is of *other* lines, and how ticking behaves. The answer to the first is
that **the list is the lines being given the terms, not the lines they could come from** - the source
is the line already open, so it is not in its own list. The mechanics:

| # | Question | Decision (agreed) |
| --- | --- | --- |
| 20a | **Which lines does it offer?** | **Every other line on the Work Order**, each with a tick box. Lines with no terms yet are **ticked to begin with**, because they are what this is for; lines that already have terms are listed and **left unticked**. Each line shows its own billing basis and rate, so a line that plainly differs is easy to leave alone |
| 20b | **What ticking does.** | **Ticking only chooses. Nothing is written until the button is pressed**, and the button says how many lines it will change. Unticking before pressing simply leaves that line alone - **it never removes terms from a line**. **Owner's addition: where a ticked line already has terms, pressing the button asks for confirmation and names those lines**, because that is the only case where something recorded is replaced. When it finishes, the result is reported line by line |
| 20c | **One period or all of them?** | **Every period the source line has.** The owner's reason: a change in rate should apply to every item whose rate changed, so a rate that changes on a date carries across with the rest |
| 20d | **Mobilisation and demobilisation.** | **Copied**, and each receiving line can then be edited where its own charge differs |

Each line that receives the terms records its own business event, so the audit trail reads as one
change per line rather than a single bulk action. A line that cannot be written - locked, or changed
by someone else meanwhile - is named in the result without stopping the others.

### What Part 3 does not do

No expiry alerts (Slice 8F, and they need `NTF-001` and a notice period you set). No approval
workflow. No refusing of closure, log sheets or billing, none of which exist yet; the closure rule
from decision 14 is recorded against 8E. No change to the frozen handoff, and no change to what
Part 1 and Part 2 record.

## Part 3 as built

Recorded 17 September 2026. What follows is what the code does, beside the decisions above.

### Putting a wrong end date right (owner, 17 September 2026)

**Superseded on 22 September 2026.** A mistaken extension is now removed, not answered with another,
and an extension must move the end later. The text below is kept as the record of what was built and
reviewed in rounds 1 to 3; see "The owner's screen check, 22 September 2026".

The agreed design did not say what happens when an end date is typed wrongly - 2037 for 2027. Asked,
the owner chose: **record another extension with the right date**. Any end date other than the one
currently recorded is accepted, earlier or later, and both entries stay visible in the history, with
who recorded each and when. Nothing is overwritten.

The alternative considered and rejected was to accept only a later date, on the reading that an
extension extends. That would have left a typed 2037 permanently uncorrectable, because every later
entry would have had to be after 2037. A separate cancel action was also declined as widening the
package beyond what was agreed.

### The shape

Two new tables and two new columns (Alembic `20260908_0039`), none of them on `crm_work_order` or
`crm_work_order_line`, so the frozen handoff is untouched by construction as it was in 7C and 7D:

```text
crm_work_order_contract_period      one row per Work Order: the start date, how the end is answered,
                                    the end date, notes, and a version for concurrency
crm_work_order_contract_extension   one row per extension: what the end was before, the new end, the
                                    customer's reference, when it was received, and who recorded it
crm_work_order_line_detail          + line_start_date, line_end_date (7C's table: a line's own facts)
```

`contract_end_basis_code` is the point of decision 14. Null means not answered yet and is reported
missing; `FIXED_DATE` carries a date; `UNTIL_WORK_COMPLETE` carries none and is a recorded answer,
exactly as `NONE` is for a billing term. A CHECK constraint ties the two together, so a row cannot
claim a firm end date while reporting itself open-ended, or the reverse, even from a direct write.

`needs_firm_end_date` is returned separately from `missing_items`, because those are different
statements: the answer is recorded, and the Work Order still cannot be closed. The screen says so in
the owner's own terms; refusing the closure belongs to 8E.

### The rule, and why it has four answers rather than two

`backend/app/modules/work_orders/contract_period_rules.py` is pure - no database, no clock, no I/O -
so log sheets, release and billing can reuse it and so every case could be stated directly in tests.
`classify_date_against_contract` answers `WITHIN`, `BEFORE_START`, `AFTER_END` or `NOT_DETERMINED`.

The fourth matters more than it looks. With no contract start recorded, whether a date falls inside
the contract is **not knowable**, and answering `WITHIN` would be a guess - the same mistake WBT-001
forbids for a missing term. A later caller that read "we do not know" as "yes" would bill or release
a day against a contract nobody had recorded. `CONTRACT_DATE_OUTSIDE_OUTCOMES` is the set a caller
should test for a refusal; `NOT_DETERMINED` is not in it.

Both bounds are inclusive: work on the contract's first and last day is work under the contract.

### What is refused, and how each refusal reads

Every message names the dates, as decision 17 asks. The owner's two examples are implemented
verbatim, with the line named so the user knows which one to look at:

```text
This period starts on 1 May 2027, after the contract ends on 31 March 2027.
The contract cannot end on 1 February 2027, because line 2 has terms starting 1 March 2027.
```

The rules, in both directions:

- a billing-terms period start must sit inside the contract - on adding a period and on changing one;
- a line's own start and end must sit inside it, and its end may not precede its own start;
- the contract's own dates may not move to exclude a period start or a line date already recorded;
- an extension's new end date is checked the same way, and may not fall before the contract start.

Added after the owner's screen check (22 September 2026):

- once an extension exists, a save of the contract dates may not change the end - only the start and
  the notes;
- an extension must move a fixed end date later;
- an extension order may not be dated before the contract starts, and the start may not move past an
  extension order already recorded;
- removing an extension is checked like any other move of the end, so it cannot restore an end that
  would now exclude a billing period, a line's own date, or the contract's own start.

Added after the owner's clarification (22 September 2026):

- an extension must start after the end it follows - normally the day after - and not after its own
  end; a later start is refused until the user confirms it, and no start is taken where there is no
  fixed end to follow;
- a billing period may not start, and a line's own dates may not fall, on a day in a gap before an
  extension;
- the contract start may not move past the end an extension continued from.

**The start side is a deliberate completion of the stated rule.** Decision 17 names only the end
case. The start case is the same rule read the other way and is genuinely reachable, because dates
are often entered before the contract is: record a period from 1 June, then record the contract as
starting 1 July, and the period now begins before the contract does. Refusing that, with the matching
message, costs nothing and closes the gap; it is recorded here rather than left as an unannounced
addition.

### What is deliberately NOT refused

**A copied period may fall outside the receiving line's own dates.** Line 2 running 1 January to
31 March can receive a period starting 1 June, because copying does not check a period against the
receiving line's dates - only against the contract. Enforcing it would block the very case decision
20d describes, where a line takes the terms and is then edited, and no decision asks for it. It is
recorded here as a known gap rather than added quietly. If it becomes a real problem, the rule to add
is the same `classify_date_against_contract` call with the line's own bounds.

### Copying terms between lines

`POST .../lines/{line}/billing-terms/apply-to-lines`. The source is the line in the path, so it is
never in its own list. Every period is copied, mobilisation and demobilisation with them, column by
column from rows that already passed every term rule - nothing is re-derived, so nothing can drift
from the source. Receiving lines start at revision 1 and stay editable.

The confirmation of decision 20b is enforced **per line**. Each target carries `replace_confirmed`
and **every period the screen saw of it**, in the same shape the source sends. Under the lock, a
target whose live periods differ in any way from those observed is refused by name, and a populated
target without its own confirmation is refused by name. Two earlier designs were not enough: a single
request-wide flag could authorize replacing a line the confirmation never mentioned (round 1, F-02),
and a period count plus the latest revision could not see a change to an earlier period (round 2,
F-07).

Each receiving line is written inside its own savepoint and records its own `WorkOrderLineBillingTermsCopied`
event, so the trail reads as one change per line and a line that cannot be written is named in the
result without stopping the others. **With the Work Order locked for the whole operation, nothing can
change a line underneath the call, so that per-line path is a guard rather than a common outcome.**
It is proved by a test that makes one line's write fail deliberately, not by pretending a natural
failure exists - the point being that the failed line rolls back alone, writes no event, and the other
lines keep their copies.

### Permissions

Two new codes, both holding the same four roles today:

```text
WORK_ORDER_CONTRACT_PERIOD_WRITE      the contract dates, and a line's own dates
WORK_ORDER_CONTRACT_EXTENSION_WRITE   recording an extension
```

*Corrected 7 October 2026 (TB-1 TB1-904):* the first line above is wrong about a line's own dates, as
correction F-04 below already found. `WORK_ORDER_CONTRACT_PERIOD_WRITE` governs the contract dates only;
a line's own dates are saved through the 7C line-detail route, so `WORK_ORDER_LINE_DETAIL_WRITE` governs
them.

Two rather than one because decision 18 asks for them "under a permission of their own, so extensions
can later be narrowed to managers without touching code". Narrowing a single shared permission would
also narrow who may set the original dates, which is not that. Copying terms between lines asks for
the existing `WORK_ORDER_LINE_BILLING_TERMS_WRITE`: it writes billing terms, and who may change a
line's rates should be one answer, not two.

All five new routes are pinned in `POST_BASELINE_NEW_ROUTES`; the frozen PF-1A-E1 baseline inventory
is untouched. The fifth, removing an extension, was added after the owner's screen check and asks for
`WORK_ORDER_CONTRACT_EXTENSION_WRITE`: who may extend a contract is who may withdraw an extension
recorded in error.

### Locking

Recorded, not enforced, exactly as decision 19 says. A Closed Work Order refuses every Part 3 write
today, as it does for 7C's detail and 7D's terms. The mobilisation lock - the contract start fixed,
the end moving only through an extension - waits for mobilisation to exist, and is recorded in
`docs/agent/DEFERRED_REQUIREMENTS.md` beside the other 7C and 7D locks.

**Half of decision 19 now applies earlier.** Since the owner's screen check, the end date moves only
through extensions from the first extension onward, not from mobilisation. The start still locks only
at mobilisation.

### Small things worth knowing

- **An extension before any contract dates** is accepted and records no previous end. Truthful rather
  than tidy: the customer did send an end date, and refusing would only force the same date to be
  typed somewhere else first.
- **A line's dates are never reported missing.** Blank means the line follows the Work Order, which
  is the normal case, so there is nothing to be missing.
- **`list_work_order_line_detail_rows` now builds its SELECT from `WORK_ORDER_LINE_DETAIL_COLUMNS`**
  rather than listing columns by hand. Adding the two date columns exposed that a hand-written list
  silently returns null for a new column; building it from the tuple makes that impossible to repeat.
- **A line's own dates keep their value when a caller omits them.** Every other field on that route
  is a whole replacement. These two are not, because they were added to a route that already had
  callers - the smoke-data harness's `set_work_order_line_detail` among them - and whole replacement
  would have let an ordinary edit erase dates nobody touched (round 1, finding F-03). An explicit
  null still clears a date.
- **An identical save is not an edit** - no version bump and no event - as everywhere else in this
  module.

### Independent review, round 1

the independent reviewer, one bounded packet, 17 September 2026. `CORRECTION_REQUIRED`, six material findings,
all accepted and corrected. They are recorded here because three of them changed an interface, and
one of the corrections then exposed a seventh problem the review had not found.

| # | What was wrong | What it is now |
| --- | --- | --- |
| F-01 | The copy checked the source's period *count* and its *latest* revision. A change to an earlier period leaves both identical, so a period the user never reviewed could be copied. | Every source period's id and revision is carried and compared, in order, under the Work Order lock. |
| F-02 | One request-wide `replace_existing_terms` flag. The screen names line 2 in its confirmation; line 3 gains terms before the request takes the lock; the flag replaces both. | Each target carries its own `replace_confirmed` and the state the screen saw of it. A line whose terms changed since is refused **by name**, which is also what stops an unconfirmed replacement. |
| F-03 | Line dates had **no screen at all** - the acceptance checklist described controls that did not exist - and a caller written against the earlier line-detail shape silently cleared them, the smoke-data harness among them. | Controls and a read-only row added. An omitted date field now keeps its value; an explicit null still clears it. These two fields alone depart from the route's whole-replacement shape, and say why at the point of departure. |
| F-04 | `WORK_ORDER_CONTRACT_PERIOD_WRITE` was described as governing a line's own dates, but the line-detail route asks for `WORK_ORDER_LINE_DETAIL_WRITE`, so narrowing the grant would not have narrowed what the description promised. | The description is corrected rather than the enforcement: a line's dates live on its 7C detail row and are saved through the 7C route, so they are that route's permission to govern, like every other field on it. |
| F-05 | The extension table did not constrain its *previous* basis and date to the shapes the service writes. | A CHECK matching the period's own. |
| F-06 | The period-ordering refusals were generic - "A later period must start after the previous period starts" - against decision 17's "every refusal says why, naming the dates". | Each names the entered date and the blocking one. Period 1's refusal names the contract start when it is recorded. |

**The seventh, which the review did not find and the correction's own test did.** Both
`is_answered` constraints were first written as a chain of `OR`s. A `CHECK` rejects a row only when
its expression is `FALSE`, and `NULL = 'FIXED_DATE'` is `NULL` - so the constraint **admitted** the
one shape it existed to refuse: an end date recorded with no basis beside it. Both the contract and
the review packet asserted it as a guarantee, on the strength of reading the constraint against the
service's intent; that reasoning never reaches SQL's three-valued logic. Both are now `CASE`
expressions, which return a definite boolean for a NULL basis, and both tables are tested for all
three contradictory shapes.

The lesson worth keeping: **a CHECK constraint that compares a nullable column to a literal must be
written so the NULL case is explicit** - `CASE`, or `IS NOT DISTINCT FROM` - and it must be tested
by insertion, not by reading.

### Independent review, round 2

`CORRECTION_REQUIRED`, four findings - three material, one advisory - all accepted and corrected.

| # | What was wrong | What it is now |
| --- | --- | --- |
| F-07 | **The same defect as F-01, on the other side of the same function.** Targets were still verified by period *count* plus the *latest* revision - the very pair removed from the source in round 1 for being unable to see a change to an earlier period. A concurrent edit to an earlier period of a populated target would have been silently deleted by the replacement. | Each target carries every period it was seen with, identical in shape to `source_periods`, compared in order under the lock. |
| F-06 | Not fully closed by round 1: the `0001-01-01` guard still refused generically. | It names the date, like the other three. (The test written for it claimed to walk all four ordering refusals and walked three; round 3 caught that as F-10.) |
| F-08 | The screen threw away the backend's 409 detail - "Line 3's billing terms changed..." - and showed a generic sentence instead, so with several chosen lines the user could not tell which one refused. It also contradicted acceptance step 25a. | The 409 detail is shown; `readErrorDetail` still falls back to a safe generic message when there is none. |
| F-09 (advisory) | The `copy_work_order_line_billing_terms` docstring still described `replace_existing_terms`, an API that no longer exists. | Rewritten to describe the per-target confirmation and the period-by-period comparison. |

**What F-07 says about the round-1 correction.** The fix for F-01 and the introduction of F-07 were
the same edit: the source's insufficient check was removed and an equally insufficient one written
for the targets a few lines below. Correcting a weak check in one place is not the same as
correcting the reasoning behind it - the second use of the same pattern has to be looked for
deliberately, because it will not announce itself.

**One part of F-08's suggested correction is not done.** It asks for a frontend test asserting the
named line reaches the displayed feedback. The frontend has no component-test capability - a
separately tracked gap in `docs/agent/DEFERRED_REQUIREMENTS.md` - so that assertion cannot be
written here. The change itself is one line, visible in the diff, and acceptance step 25a checks it
on screen.

### Independent review, round 3

`ACCEPTED`, 18 September 2026, with one advisory finding. The accepted tree,
`66be42f610a26350286c39bf3ef7b7f5ee7065e5`, is committed exactly as the package's first commit, so
the commit reproduces what was reviewed.

**F-10 (advisory) - a test claimed more than it exercised.** Round 2's
`test_every_period_ordering_refusal_names_the_dates` was said, here and in the review packet, to walk
all four ordering refusals. It walked three: the on-or-after-the-next-period branch needs a *middle*
period, and the test never built one. Its "previous period" case also used the same date on both
sides, so it could not show that both dates are named rather than one date that happened to be both.
The production code was right; the claim about its coverage was not.

Corrected in the second commit, at the owner's direction and exactly as the reviewer prescribed: the
test builds three periods and moves the middle one past the third, and every case now uses an entered
date distinct from the one it clashes with. The text it asserts for the next-period case appears in
exactly one place in the service, so the test cannot pass by any other route. That commit is not
re-reviewed; it adds one test case and corrects this record.

**Across the three rounds:** ten findings - six, then four, then one advisory - every one of them
real, and every one fixed. Plus the seventh problem of round 1, which no round found and the
correction's own test did. Two of the ten are worth remembering for how they arose rather than what
they were: **F-07 repeated F-01 inside the very edit that fixed it**, and **F-10 was a test written to
prove F-06 closed that claimed a coverage it did not have.** Both are the same failure - asserting a
thing is done because the reasoning for it has been done - and the only defence against either is to
check the claim itself, not the reasoning.

### The owner's screen check, 22 September 2026

The owner worked through the acceptance checklist on a seeded Work Order after round 3 was accepted
and PR #64 was open. Six findings.

| # | What the owner saw | What it was |
| --- | --- | --- |
| 1 | A date field accepted a year of five or six digits. | Chrome lets a date input's year run on unless the input has a maximum. None of the Work Order page's date inputs had one. |
| 2 | "Received on" did not say received what. | Wording. |
| 3 | After recording extensions, the contract end date on the form had changed back, and the history no longer explained the current end. | **A real defect.** The form still offered the end date after extensions existed, and a save there silently replaced the end the extensions had set. The business events showed it happening twice. **The checklist's step 16, as it was numbered until 22 September, instructed exactly that edit** - "restore the dates to 1 January 2027 and 30 September 2028, and save" - so the checklist walked the tester into it. |
| 4 | With the end editable in two places, it was unclear which one was meant to be used. | The same defect, seen from the screen. |
| 5 | Step 25a asked for the named line, but a save in two tabs worked correctly and named nothing. | The step was worded for the copy panel and read as if it were about saving a period. It is now reworded. |
| 6 | The page does not say who is signed in. | True of the whole application, not this slice. Recorded, and offered to the owner as a separate small change. |

**The owner's decisions, 22 September 2026:**

| # | Question | Decision |
| --- | --- | --- |
| S1 | Once an extension exists, can the end date still be edited on the form? | **No, only through extensions.** The form shows it read-only; the server refuses a save that changes it. The start date and the notes stay editable. |
| S2 | How is an extension recorded in error put right? | **Remove the latest.** Only the most recent extension can be removed; the end goes back to what it was before it; the removal is kept in the audit log. With every extension removed, the end date is editable again. This replaces the 17 September rule, so an extension must now move the end later. |
| S3 | When may an extension order be dated? | Owner's words: "Extensions usually come before the contract date is over, not after. So any date but not before the contract start date, obviously, and if more than 15 days before today's date, a warning." Refused only before the contract start; a warning, never a refusal, when more than 15 days before today (India time). |
| S4 | A fourth review round for these fixes? | **Yes**, granted by the owner. |

Finding 1 was fixed on the Work Order page's eight date inputs (`max="9999-12-31"`); the same gap on
other pages is recorded in `docs/agent/DEFERRED_REQUIREMENTS.md` rather than widened into this
package. Finding 2: the field reads **Extension order received on**, the column **Order received on**.

**One rule added for consistency, not asked for.** S3 refuses an order dated before the contract
start. Moving the start later past an order already recorded is the same rule read from the other
side, exactly as the start side of decision 17 was, and is refused with the matching message
("because extension 1's order was received on 1 March 2027"). Otherwise an order refused at entry
could be produced afterwards by moving the start.

**Why S1 and S2 go together.** Before S2, recording another extension was the only way to correct a
mistyped one, and that needed any end date to be accepted - which in turn made the form's end field
redundant only in principle. With removal available, an extension can be required to extend, and the
form can stop offering the end date once one exists, so the end has exactly one way to move.

**What removal does, exactly.** `DELETE /api/work-orders/{public_id}/contract-extensions/{extension_public_id}`,
under the Work Order lock like every other Part 3 write:

- only the most recent extension; any other is refused, naming the one that is most recent - which
  is also what protects a screen that is out of date;
- the end basis and date go back to the ones the extension recorded as previous, so "until the work
  is complete" and "not recorded" come back as well as dates;
- the restored end is checked against billing periods, lines' own dates and the contract's start,
  and a refusal begins "This extension cannot be removed.";
- the row is deleted and `WorkOrderContractExtensionRemoved` records the extension's number, the end
  it set and the end restored, without the customer's reference;
- an extension already removed, or not on this Work Order, is not found.

The event, not the row, is what keeps the fact that an extension existed. The history table therefore
shows the extensions in force, and the audit log shows every one ever recorded.

### Round 4

`ACCEPTED`, no findings at any severity, packet `3d5347e1ae8c2cc1b25b3c537dcc92ca649b86249f389b48d39d7db7c4198c2f`,
tree `d83bf2686c4ab6309fa0a05dc7e9e528f571dca9`. That tree was never committed: the owner's
clarification below changed the package before it was.

### The owner's clarification of extension dates, 22 September 2026

Asked whether an order dated in the future should be refused, the owner explained that the question
was framed wrongly - the order date is not the thing to test against today:

> An extension is issued during the currency of a WO, usually. If a verbal commitment has been
> received but the actual order arrives a few days after the WO last date, it may be entered on the
> day it arrives, which can be after the contract ends but generally the extension start date is a day
> after the WO close date. If the extension start date is a date after the WO close date, then it needs
> confirmation, else it can be recorded. Extension can be issued any time after the WO starts so an
> extension date cannot obviously be before the WO start date.

That names something the system did not record: **the date an extension starts**. Asked four
follow-up questions, the owner chose:

| # | Question | Decision |
| --- | --- | --- |
| S5 | Does an extension record its own start date? | **Yes, the day after by default.** The screen fills in the day after the current end. A later start is recorded only after the user confirms it. A start on or before the current end is refused: that is not an extension. |
| S6 | What about the days between the old end and a later start? | **Outside the contract.** No contract runs on them; later, no log sheet or bill may fall on them. |
| S7 | An order that arrives after the contract has ended? | **Recorded normally.** Any order date from the contract start onward, as S3 already said. |
| S8 | Keep the warning for an order dated more than 15 days before today? | **Keep it**, as a warning only. |

And on the missing signed-in user (screen-check finding 6): "a small change, ok to keep it separate if
that aids tracking but if not, and if it is indeed small, it can be rolled into the current work". It
was small - the sidebar asks `/api/auth/me` whenever the session changes and shows the name and role -
so it is rolled in.

**What was built.**

- `extension_start_date` on each extension, nullable exactly when there was no fixed end to follow;
  a new CHECK, `ck_wo_contract_extension_start_follows_previous_end`, requires it after a fixed end,
  after that end, and not after the extension's own new end. **Migration `20260908_0039` is amended in
  place** rather than given a new revision: it has never been merged or deployed, so no database
  anywhere depends on its earlier shape, and taking `0040` would have used the slot tentatively
  reserved for Part 4.
- The request takes `extension_start_date` (omitted means the day after) and `gap_confirmed_from`. A
  later start without it is refused naming the days it would leave outside; the screen asks first,
  naming them, and sends the gap's first day only when the user agrees. **It is a date, not a yes,
  deliberately.** A yes was the first version, and it had the weakness review found twice in the copy
  action (F-02, F-07): if another user moved the end after the page was read, a yes given for one gap
  would record a different one. The date binds the agreement to the gap shown; a mismatch is `409`.
- The pure rules gain `ContractGap`, `gap_before_extension` and a fifth outcome, `IN_GAP`, which is in
  `CONTRACT_DATE_OUTSIDE_OUTCOMES`. It is answered whether or not the start is recorded, because a gap
  is made only of recorded dates. A billing-period start or a line date in a gap is refused: "This
  period starts on 5 April 2027, when no contract runs: the contract ended on 31 March 2027, and
  extension 1 starts on 15 April 2027." A line may span a gap; only its own dates may not fall in one.
- `contract_state` gains `BETWEEN_EXTENSIONS` - "Not running: extension 1 starts in 3 days, on ..." -
  so a day in a gap is never shown as "Active".
- The period response lists `gaps[]`; the screen shows each under the extension history and names the
  start in the history only when it is not the day after.

**Why copying terms needs no gap check.** A gap only ever lies after the end it follows, and no billing
period can start after the current end, so no existing period can be in a gap and a copy never carries
one there. The same reasoning is why recording an extension checks no recorded date against the new
gap.

**One hole found while working it through, and closed.** Once an order may arrive after the contract
ends (S7), its received date is no longer a guard on the contract start. The start could then be moved
past the end an extension continued from - a contract that "starts" after the end it was extended from.
This was reachable before the clarification too, with a late order. It is now refused at the start:
"The contract cannot start on 15 April 2027, because extension 1 continues from an end date of 31 March
2027." Removal's own check against a later start stays as a backstop, and its test now sets that state
directly in the database, as data written before this rule could hold it.

### Round 5

`CORRECTION_REQUIRED`, one material finding, packet
`b874db6b9fea12f080c33c52c5dd3dd1e4736688a624dbdc2d29270d6c81b1e3`, tree
`8f1b623d8034c290a0523ee77183636c0c574e8c`. Authorized by the owner beyond the cap. Nothing in the
extension-date change drew a finding.

**F-01 - the sidebar could show the previous user's name after a change of session.** When the token
changed, the name fetched for the old token stayed on screen until the new lookup answered, and forever
if it never did - wrong precisely during the account switch the feature was added to make safe.
Corrected as prescribed: the name is kept with the token it was fetched for, and `userForToken` shows it
only while that token is the one in use, so a new session reads plain "Signed in" until its own answer
arrives. Five tests cover it, including A to B with B's lookup pending and with it failing. Checked on
screen with the lookup made to hang: after switching user, the sidebar read "Signed in", not the old
name.

### Round 6

`ACCEPTED`, no findings at any severity, packet
`b36bd820fcdbe7c5cf415e46449579f05c5b335a01011790cf86b0f66dd19c27`, tree
`36f2ab4eba75f574001f35a75a98a38e99fbac5b` - committed exactly, so the commit reproduces what was
reviewed. Authorized by the owner beyond the cap, as rounds 4 and 5 were. The reviewer's only remark
was that a component test would confirm the React wiring independently, which needs the frontend
component-test capability tracked separately.

**Across six rounds: 6 material, 4, 1 advisory, 0, 1 material, 0.** Two of those rounds judged changes
the owner asked for after their own screen check, and one judged a clarification that arrived after a
round had already accepted the package - which is why the round-4 tree was never committed.

### The owner's second screen check, 23 September 2026

**PASS.** The whole checklist, on the seeded scenario. Three things recorded rather than corrected:
the placement of "Remove this period" (`UI_UX_CARRY_FORWARD.md`), Backspace not walking back through a
date field, and the date caps still missing on other pages (both in `DEFERRED_REQUIREMENTS.md`, beside
each other because both want one shared date-input component).

Two lessons about the checklist itself, both fixed in it:

- **Step 17i sent the tester to another section without saying so.** After two steps in the extension
  form, "In Billing terms, on line 1..." read as if it were still about extensions. A checklist step
  that changes section has to say it is changing section.
- **The check produced a state the checklist did not anticipate**, and the code handled it: a
  billing-terms period recorded beyond the contract end made removing the extension impossible, with
  a message naming the line and its date. Correct, and worth knowing before someone reports it as a
  fault.

### Test plan, as implemented

```text
backend/tests/test_slice_7d_part_3_contract_rules.py     47 tests, no database
  (35 before the owner's clarification; +12 for gaps: where one starts and ends, both edges exact,
  knowable without a start, the message, and a day in a gap reading as not running)
  every position against a fully and partly recorded contract; NOT_DETERMINED is not a refusal;
  both bounds inclusive; the wording of every message; each contract state and its "in N days",
  "today", "tomorrow"; an end recorded without a start cannot claim the contract is running

backend/tests/test_slice_7d_part_3_contract_period.py    128 tests, through the routes
  (68 at round 1, 82 after rounds 1 and 2, 107 after the owner's screen check, 128 after the owner's
  clarification: the start date and its default, on or before the end, a later start refused until
  confirmed and then recorded with its gap, a confirmation given for other days refused as out of
  date, a confirmation ignored when there is no gap, after its own end, none where no fixed end, a period and a
  line date in a gap, a line spanning one, today in a gap, removal taking its gap, a late order, the
  start past the end an extension followed, and the new CHECK by insertion)
  recording and changing the dates, versions, conflicts and the identical save; the three states;
  "until the work is complete" as an answer against a blank end; every basis/date combination
  refused; extensions, their history, an extension must move the end later, and an extension against
  an open-ended or unrecorded contract; the end date locked once an extension exists, with the start
  and notes still editable; removing the latest extension - back to the previous end, open-ended or
  unrecorded, only the latest, not found once removed, kept in the audit log without the customer's
  reference, refused when the old end would exclude a period or fall before a later start, the four
  roles that may and the two that may not, a Closed Work Order; an order dated before the contract
  start refused, any other date accepted, and the start unable to move past an order already recorded;
  the period and contract rules in both directions; a line's own
  dates; copying - every period, mobilisation, editability afterwards, one event per line, the
  confirmation, a line left out, the source as a target, duplicates, an unknown line, a source with
  no terms, stale terms, and one line failing without stopping the others; the four writing roles
  and the two that cannot; a Closed Work Order; and that no Part 3 field reaches the frozen handoff

frontend/src/pages/work-orders/workOrderContractPeriodState.test.ts   41 tests
  (35 before the clarification; +6: the default start, the day after across a leap day, a gap and its
  confirmation, how a gap is listed, the start named in the history only when it is not the day after)
frontend/src/components/sessionUser.test.ts                           9 tests
  who is signed in: the name and roles, several roles, no name rather than a wrong one; and (round 5,
  F-01) a name shown only for the token it was fetched for - A to B while B's lookup is pending, B's
  lookup failing, B answered, and signed out
  what the screen decides for itself: the form, the end-basis interaction, the payload, how an
  extension reads, period 1's label once the contract start is known, which lines the copy offers
  and which start ticked, the button's count, the confirmation's wording, and the result line by line;
  since the screen check, when the end locks, which extension may be removed, what the end goes back
  to, the removal's confirmation, and the 15-day warning - its boundary, a month and year end, an
  incomplete date, and "today" taken in India rather than in the browser's zone

backend/tests/test_smoke_data_harness.py   + 1
  cleanup removes a Work Order's contract period and extensions before the Work Order itself
```

## Part 4 - the remaining billing terms

**Answered 17 and 18 September 2026; recorded 23 September 2026 in
`slice-7d-part-4-remaining-billing-terms.md`, which is now the authority for Part 4.** The table below is
the questions as they were asked, with the recommendations of the time, kept as a record (ADR-013). What
the answers did to each recommendation:

```text
21  superseded   billing frequency belongs to the equipment (8A, 8G), not the Work Order; leaves Part 4
22  agreed       per day or per month, with a rate per extra kilometre
23  superseded   crew counted in numbers per billing unit of the line, not per shift; "crew unit" withdrawn;
                 how extra crew is charged is still to be asked
24  withdrawn    weekly-off and holiday rates are NOT split; Part 1's single choice records both
25  superseded   holiday dates come INTO Part 4, as a list entered from the Work Order
26  superseded   no new choice: a monthly shortfall is deducted pro rata with no minimum; only the
                 refusal's wording is fixed
```

### Questions for the owner

| # | Question | Recommendation |
| --- | --- | --- |
| 21 | **Billing frequency (FRS 2.8.1).** Invoices are raised weekly or monthly per the contract. Where is that recorded, and what choices? | **On the Work Order, not the line** - one invoice cycle for the whole Work Order - with **Weekly** and **Monthly (calendar month)** to start with. Add another choice when a real Work Order needs one, as decision 7 established. Tell me if lines on one Work Order are ever billed on different cycles |
| 22 | **Extra kilometres (FRS 2.5.6).** | Per period, like the other terms: **not in the Work Order**, or **N kilometres included per day** with a rate per extra kilometre, or **N included per month** with that rate. Which of per day or per month do your Work Orders actually state? |
| 23 | **Extra crew (FRS 2.5.6).** | Per period: the **contracted number of operators and helpers per shift**, and the **rate for each extra operator and each extra helper**. Assigning the actual people comes with crew assignment (8B). Is the extra charged per shift, or per day? |
| 24 | **Weekly-off work and holiday work (FRS 2.4.5).** Today they share one choice and one rate. | **Separate them**, each with its own choice and rate, because a contract can price Sunday work and a public holiday differently. The migration copies today's single answer into both, so nothing already recorded is lost or guessed |
| 25 | **Which days are holidays.** A holiday rate needs to know what counts as a holiday. | **Not in this package.** The list of dates belongs with log sheets (8C), where the day being billed is known. The question for you: does the customer's Work Order name its holidays, or does PBL apply its own list for the state the site is in? |
| 26 | **A monthly line that falls short of the contracted hours.** FRS 2.4.4.2.1 bills such a month pro rata. Today a monthly line cannot record a minimum, and the screen says the monthly rate already covers the month. | **Make it an explicit choice**, since a term is never guessed: hours short of the contracted hours are **billed pro rata**, **billed in full**, or **billed to a minimum of N hours**. Blank stays missing. This replaces the current refusal and its wording |

### What Part 4 does not do

No calculation, as before: what these terms feed - extra-kilometre and extra-crew charges, the
monthly shortfall, holiday and weekly-off rates - belongs to the billing slices (8D). No holiday
calendar. No approval of any term.

*Superseded in part by answer 25:* Part 4 now takes the holiday dates the Work Order states, as a list.
It still has no company holiday calendar.

## Engineering shape (outline, to be settled after the answers)

- Part 3 adds its own table for the contract period rather than columns on `crm_work_order`, so the
  frozen handoff output is untouched, exactly as 7C and 7D did. Extensions are a second table, one
  row per extension, so history is kept by construction rather than by care.
- Line-level dates sit with the line's operational detail (7C), which is where a line's own facts
  already live.
- Part 4 adds columns to `crm_work_order_line_billing_term`, following Part 2's pattern: nullable
  columns, a CHECK for every rule, and the same missing-items reporting.
- Every rule that decides what the screen shows is a pure function with its own tests, because the
  frontend still has no component-test capability.
