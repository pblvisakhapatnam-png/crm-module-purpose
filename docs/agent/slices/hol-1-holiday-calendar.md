# HOL-1 PBL's holiday calendar - design

Status: **Design proposed and agreed 2 October 2026** (section 1.0): Q1, Q2, Q3 and Q5 as recommended; Q4 answered
by the owner with a change - each calendar holiday a Work Order makes a working day is charged at the normal or the
overtime rate, as the Work Order says - which this text now carries. Read again the same day before it went to the
owner; one point corrected then (1.2, point 2: a national holiday may apply to named states only). Built on that
agreement.

Hiring lane (Track 2). Worktree `<a separate worktree>`, branch `hiring/hol-1-holiday-calendar`, based on
`main` at `e1f7409` (PR #84, TE-7, merged). Proposed migration slot `20260908_0047`, parent `20260908_0046` - the
single Alembic head on `main`; no branch on `origin` holds a `0047` revision (checked 2 October 2026). Foundation
Slice Mode: the shape is built properly, the screens minimally. The frozen Slice 6D.1 handoff contract's SHA-256 is
`70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a` before this package.

Working terms (the owner, 2 October 2026, "same working terms as before"): own worktree and branch from `main`,
never a commit to `main`; the frozen handoff contract's hash checked before and after; independent review, up to three
rounds; the pull request merged only on the owner's word, after `Required validation` succeeds.

**What is already decided.** The owner decided on 2 October 2026 that PBL sets up a default holiday calendar every
year, and the system must provide the facility. Every Work Order inherits it, and its own terms change it for that
Work Order: a holiday added, or a calendar holiday taken off because the Work Order works through it.
`DEFERRED_REQUIREMENTS.md`, "PBL's default holiday calendar", records the decision and what it changes in Slice 7D
Part 4. It left two points for this package: a year whose calendar is not set up yet, and a change to a year already
in use. This design builds the decision and answers those two points (Q2 and Q3).

In plain words:

- **A Holiday Calendar page**, kept by Admin, read by everyone. One calendar for each year, January to December.
  Each holiday has its date, its kind (national or festival), its name, and where it applies: all of India, or the
  states named.
- **A year is "set up" when Admin marks it complete.** Until then, the dates entered so far still count, and the
  platform keeps reminding (Q2).
- **On the Work Order, the holiday answer changes meaning.** "The Work Order names no holidays" becomes "The Work
  Order follows PBL's calendar unchanged". "Names these holidays" becomes "The Work Order changes PBL's calendar as
  listed", and the list holds two kinds of change (Q4):
  - **a holiday added** - date, kind, description - as today;
  - **a calendar holiday made a working day**, charged **at the normal rate** or **at the overtime rate**, with an
    optional note. The Work Order page lists PBL's calendar holidays inside the contract, each with the choice
    "Holiday", "Working day, normal rate" or "Working day, overtime rate", so Sales picks rather than types.
- **The Work Order page shows the holidays that apply**, for the contract period, for each group of lines in the same
  state: PBL's calendar for that state, with each day the Work Order makes a working day shown as such, plus the days
  added. Each day says where it came from.
- **The calendar charges nothing.** Work on a holiday is charged as each line's "Work on an off day or holiday" term
  says (answer 24, confirmed by the owner on 2 October 2026). A calendar holiday the Work Order makes a working day is
  charged as the Work Order says: at the normal rate, or every hour of that day at the line's own overtime rate.
- **Nothing is calculated or locked yet.** Log sheets (8C) and billing (8D) will read the holidays that apply through
  the same rule the page uses.

**Reuse, not a second structure** (CODING_STANDARDS.md section 1):

- **The states** are ELG-1's list of the 36 states and union territories (`eligibility_jurisdiction`), the platform's
  only list of them. A line's state is read from its site address exactly as 8A's allocation reads it
  (`jurisdiction_for_state_text`).
- **The Work Order's list** stays Part 4's two tables, answer and dates, extended rather than replaced. Every rule
  Part 4 built - each date inside the contract, the contract unable to move to leave one outside, one version, the
  list replaced as a whole - carries over unchanged.
- **The "inside the contract" check** is Part 3's `contract_period_rules.py`.
- **The reminder** (Q2, as recommended) uses ELG-2's Alerts, schedules, paths and "seen" marks.

---

## 1. Questions for the owner

### 1.0 Answered by the owner (2 October 2026)

| # | Answer |
| --- | --- |
| Q4 | Asked again in plainer words, with an example. The owner: **"I don't know how often they come up, probably reasonably often but ALL festivals are never not working days. So, a) they will need to be set as per WO and b) even if some festivals are marked as working days, it is possible that they will be charged at overtime rates. So, we need flexibility here."** Read as: no Work Order works through every festival, so a single "national holidays only" choice does not fit; which festivals are worked is set on each Work Order; and a festival worked may be charged at the normal rate or at the overtime rate. The reading, and the change it brings, were put back to the owner as three points - (1) the reading; (2) "overtime rate" means every hour worked that day at the line's overtime rate, not only the hours beyond the normal day; (3) a festival that stays a holiday is still charged by the line's single off-day term (answer 24) - and the owner answered **"1, 2 and 3 all yes"** |
| Q4, the change | **A choice per calendar holiday on the Work Order**: "Holiday" (the default), "Working day, normal rate" or "Working day, overtime rate", with an optional note; "Add a holiday" stays for a day not in the calendar; a day in a year not set up can still be typed in; a line with no overtime rate on such a day is noted. Put to the owner with the three points above and accepted with them. It replaces the first draft's "worked through, with why" (section 13, row 3) |
| Q1, Q2, Q3, Q5 | **"The remaining Qs are fine"**: each as recommended - the calendar stays out of the Hiring user test, whose pack this package does not change (Q1); a reminder on the Alerts page for a year not set up (Q2); a year may be changed at any time, every change kept, with a warning for a day already passed (Q3); migration slot `20260908_0047` (Q5) |
| Section 1.2 | Put to the owner with "say if any is wrong"; none was raised |

### 1.1 The questions as put (2 October 2026; answered in 1.0)

#### Q1. The Hiring user test: with the calendar, or after it?

The user test pack (TE-7) is ready. Its guide says the yearly calendar is not built yet. The Accounts sheet asks the
testers which days they would bill as holidays.

**Recommendation: build the calendar now, but keep it out of the user test.**

- The test site runs the version the testers' sheets describe (TE-7). It is not moved to this version during the
  test.
- This package does not change the test pack (`docs/uat-hiring/`).
- After the test, the guide is updated, together with whatever the testers say about holidays. Their answers may
  change this design, at little cost.

**The alternative:** the calendar joins the test. This package then also updates the guide, the Sales and Accounts
sheets and the practice data (a practice calendar), and the test waits until this package is merged.

#### Q2. A year whose calendar is not set up yet

A Work Order often runs into the next year. If PBL's calendar for that year is not set up, the platform cannot
know that year's holidays. Only the Work Order's own added holidays would count.

**Recommendation: a reminder on the Alerts page, like the certificate reminders.**

- **What it says:** "PBL's holiday calendar for 2027 is not set up."
- **When:** on the certificate reminders' standard days, counted to 1 January of that year: 60 and 30 days before,
  weekly from 15 days before, daily from 7 days before, and every day after 1 January, until it is set up.
- **Who:** Admin from the first reminder. Management from 1 January, when the year has started without a calendar.
- **It ends** only when Admin marks that year's calendar complete. "Mark as seen" quiets it until its next reminder
  day, as for certificates.
- **Admin may change** its days and who it reaches on **Reminder settings**, as for the other reminders.
- **The Work Order page** also says it, under "Holidays that apply": "PBL's calendar for 2027 is not set up yet.
  Only this Work Order's own changes count for 2027."
- **It holds nothing.** No Work Order is refused anything because a year is not set up.

What this costs: the Alerts page so far knows only certificates. This makes it gather a reminder from another part of
the platform for the first time, as ELG-2 expected it would. It adds about a quarter to this package.

**The alternative, smaller:** no reminder on Alerts. A notice on the Dashboard for Admin and Management, from 60
days before the year, and on the Holiday Calendar and Work Order pages. No count in the menu, and no "seen".

#### Q3. Changing a year already in use

PBL may need to change a year's calendar after it has started. For example, a state declares a holiday for an
election day.

**Recommendation: Admin may change any year at any time, and every change is kept.**

- Each change gives the year a new version, with who made it, when, and which dates changed.
- Work Orders always use the calendar as it is now.
- When a change touches a day that has already passed, the page says so beside **Save**.
- Today nothing is billed, so nothing needs correcting. When log sheets exist (8C), a change to a day already on an
  approved log sheet is put right by a corrected log sheet, never by rewriting it (`LBE-001`). 8C designs that.

**The alternative:** a year cannot be changed after 1 January. A late holiday would then have to be added on every
Work Order it affects.

#### Q4. A Work Order that keeps only some of PBL's holidays

Some Work Orders may say, for example, "only the national holidays". With this design, that is entered as one
"worked through" change for each festival holiday of PBL's calendar - about eight to ten a year.

**Recommendation: one change per date, for now.** It is explicit, and it shows exactly which days are worked. If
the testers or real Work Orders often say "only national holidays", a single choice can be added later without
changing anything already entered.

**The alternative, now:** a third answer, "The Work Order keeps only PBL's national holidays", plus any changes
listed. It would follow the calendar automatically when Admin changes the festival holidays.

How often do your Work Orders say this?

**Answered (1.0):** neither as put. Which festivals are worked is set on each Work Order, and a festival worked
may be charged at the normal or the overtime rate - a choice per calendar holiday.

#### Q5. Migration slot

**Recommendation:** `20260908_0047`, after ELG-2's `20260908_0046`. No other branch holds `0047`.

### 1.2 Decided in this design (put to the owner; none raised)

1. **"Complete" is a mark Admin records**, as "names no holidays" is a recorded answer (decision 29): dates entered
   are not enough to say a year is finished. Admin may take the mark off again.
2. **The two kinds, national and festival, are the words of the states' holiday laws** (their National and Festival
   Holidays Acts), and **the kind does not decide where a holiday applies.** Republic Day, Independence Day and Gandhi
   Jayanti are national holidays for all of India, but a state may count its own day among its national holidays:
   Maharashtra's Shops and Establishments Act, 2017 lists four - 26 January, **1 May**, 15 August and 2 October. So a
   national holiday may be entered for named states only, and Admin records each day as PBL's list calls it. The kind
   only describes the day. Every holiday is charged alike (answer 24). (Corrected 2 October 2026, on a second reading:
   the first draft refused a national holiday for named states, which would have refused Maharashtra's 1 May.)
3. **One date, different states.** The same date may be in the calendar more than once for different states - 14
   April is Tamil New Year in Tamil Nadu, Vishu in Kerala and Baisakhi in Punjab - but never twice for one state.
4. **The calendar year runs from 1 January to 31 December.**
5. **Each calendar holiday has a name** ("Diwali"). On a Work Order, an added holiday's description stays optional,
   as in Part 4.
6. **A working day on a date not in PBL's calendar is accepted, with a note.** "Not a holiday in PBL's calendar for
   any site of this Work Order: this change does nothing." So it can be typed in before that year's calendar is set
   up, and a wrong date shows up at once. Likewise an added holiday that the calendar already has for every site: "Already in
   PBL's calendar for every site of this Work Order."
7. **Every change must fall inside the contract**, as every listed holiday must today. The contract cannot then move
   to leave one outside. This now covers the working days as well as the days added.
8. **A line's state comes from its site address on the Account**, as allocation already reads it. A line with no
   site, or with a state the platform does not recognise, shows the all-India holidays and the Work Order's changes,
   with a note naming the line and what to put right. It blocks nothing; 7C already reports a missing site.
9. **"Holidays that apply" covers the contract period**, with the extensions and without any gap before an
   extension. With no contract start recorded, it says to record the contract period first. With the end "until the
   work is complete", it runs to the end of the last year started in the calendar, and says so. A line's own dates do
   not narrow it; log sheets will do that per line.
10. **The answer is still needed before release (7B)**, as now. "Changes PBL's calendar as listed" with no change
    entered is still missing, as "names these holidays" with no date is today.
11. **Practice data already entered carries over:** "names no holidays" becomes "follows PBL's calendar unchanged",
    and each listed date becomes a holiday added. A list that was meant as the Work Order's only holidays now also
    takes the calendar's. No real Work Order exists yet.
12. **The menu** gains **Holiday Calendar**, after Work Orders. Its page shows the current year, the next year, and
    any year already started; Admin can start another.
13. **Crew pay is not decided here.** The calendar says which days are holidays for a Work Order. Crew attendance and
    pay take their holidays from PBL's HR terms (the standing rule against 8B); whether those use this calendar is
    8B's decision.
14. **No holidays are loaded for you.** Every year's dates, the national ones included, are PBL's to enter.

Added with the answer to Q4 (2 October 2026):

15. **"Overtime rate" is each line's own.** A working day at the overtime rate is charged, every hour of it, at the
    overtime rate the line's billing terms record for the period that day falls in. Where a line has none on that
    day - overtime "not in the Work Order", not recorded yet, no terms, or an hourly line, which has no overtime - the
    Work Order page says so beside the day, naming the line. It blocks nothing: the list is one for every line, and
    the terms may be entered later; billing (8D) will refuse to guess the rate.
16. **A working day's note is optional,** as an added holiday's description is. With a choice beside every calendar
    holiday, a required note on each would slow entry for no gain; the customer's clause can be noted where it helps.

### 1.3 Already settled, not asked again

| Point | Settled by |
| --- | --- |
| A default calendar every year; the system provides the facility | The owner, 2 October 2026 (`DEFERRED_REQUIREMENTS.md`) |
| Every Work Order inherits it, and its own terms vary it: a holiday added, or a calendar holiday removed with why; a holiday moved is one of each | The same, as corrected by the owner the same day. Refined by Q4 (1.0): a calendar holiday is not removed but made a working day, at the normal or the overtime rate, with an optional note |
| Dates already listed carry over as additions; "names no holidays" becomes "follows PBL's calendar unchanged" and is still required before release | The same |
| The variations stay one list for every line; each line applies them to its own site's state | The same; decision 27 |
| The calendar decides which days are holidays, never what they are charged; the off-day choice covers every holiday | The same; answer 24, confirmed by the owner on 2 October 2026 (Q4, point 3); `WBT-001`. A calendar holiday the Work Order makes a working day is charged as the Work Order says (Q4) |
| Each date with its kind, a description and where it applies (all of India or named states); kept by Admin until a position is mapped under `ORA-001` | The same ("the facility, as recommended") |
| Approved log sheets are corrected by versioning, never rewritten | The same; `LBE-001` |
| Who may change a Work Order's holidays: the billing-terms permission | Slice 7D Part 4, engineering outline |
| Every holiday the Work Order lists is inside the contract, and the contract cannot move to exclude it | Slice 7D Part 4 |
| The calendar is built before or with log sheets (8C) | `FUTURE_SLICES.md`, 8C |

---

## 2. What the sources say

Each source is read against the later decisions that refine it (ADR-013).

- **The FRS** (`docs/reference/erp-source-extracts/CRM_HIRING_RELEVANT_REQUIREMENTS_EXTRACT.md`) says different rates
  may apply on holidays and that a customer's ERP may make holiday hours billed as normal-day overtime. It says nothing
  about where the holiday dates come from. A real Work Order in the functional specification excludes "Sundays and
  holidays" without listing them - the case the owner's decision answers.
- **`DEFERRED_REQUIREMENTS.md`, "PBL's default holiday calendar"** is the decision this package builds, with what it
  supersedes (answer 25's "not taken from a company calendar"), what it changes in Part 4, the facility as
  recommended, and the two points left to this package.
- **Slice 7D Part 4** (`slice-7d-part-4-remaining-billing-terms.md`): answers 24 and 25, decisions 27 and 29, the
  reconciliation note under answer 25, and "Part 4 as built".
- **`work-order-contract.md`, "The holidays a Work Order names"**: the routes, fields, refusals and events this
  package changes.
- **`FUTURE_SLICES.md`**: 8C ("PBL's default holiday calendar ... built before or with this slice"; log sheets mark a
  day as a holiday) and 8D (the off-day choice applies "to every holiday of PBL's default calendar as the Work Order
  varies it").
- **`WBT-001`**: missing terms are not guessed. The calendar sets dates, not charges, so it guesses no term.
- **`LBE-001`**: billing records the exact term versions used; corrections are versioned. So each calendar year has a
  version, which log sheets and billing can record later.
- **ELG-2** (`elg-2-certificate-reminders.md`): the Alerts, schedules, paths and "seen" marks; section 11 expected
  other modules' reminders to join the Alerts page.
- **`NTF-001`**: the originating module owns why a reminder is needed and its business record; delivery belongs to
  Notifications, which is not built. The screen stays the only channel.
- **`MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`**: no row owns a holiday calendar today. This package adds one (section 10).

---

## 3. Authority and required reading

Per PBL's internal working instructions, "Reading discipline". Each was read in full unless a section is named.

- **The decision:** `DEFERRED_REQUIREMENTS.md`, "PBL's default holiday calendar", and the entries it sits among under
  "Work Order lines" (the 7C locks, including whether the holiday list locks at mobilisation; the contract period;
  read consistency; billing terms deferred by 7D).
- **Slice 7D Part 4:** `slice-7d-part-4-remaining-billing-terms.md`, in full, with its answer 25 reconciliation.
- **Contracts:**
  - `work-order-contract.md`, the Slice 7D Part 3 and Part 4 sections;
  - `accepted-offer-to-work-order-handoff-contract.md` (frozen; hash only);
  - `work-order-billing-terms-contract.md` (`WBT-001`) and `log-sheet-billing-contract.md` (`LBE-001`), in full;
  - `eligibility-api-contract.md`, "Reminders and escalation" and the jurisdictions;
  - `notification-delivery-contract.md` (`NTF-001`).
- **Backlog:** `FUTURE_SLICES.md` - 7B, 7D Part 4, 8B, 8C, 8D; "Hiring user test".
- **Registry and architecture:** `CONTRACT_REGISTRY.md`; `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`.
- **Designs reused:** `elg-2-certificate-reminders.md`, sections 1 to 15; `elg-1-machine-eligibility.md`, the
  jurisdictions; `8a-core-equipment-allocation.md`, section 6.1 (the site).
- **The user test:** `docs/agent/technical-enablement/TE_7_HIRING_USER_TEST_PACK.md`; `docs/uat-hiring/`, where
  holidays are mentioned.
- **Decisions:** ADR-013 (source guidance is directional); ADR-017 (module-owned data); ADR-023 (settled points are
  applied, not asked again); ADR-037 (canonical platform structures).
- **Continuity:** `docs/continuity/NEXT_STEPS.md`, the updates of 30 September to 2 October 2026.
- **Code:**
  - `work_orders/services/holidays.py`, `services/contract_period.py` (the reverse check),
    `contract_period_rules.py`, `contract.py`, the holiday reads and writes in `repository.py`, the holiday schemas;
  - migration `20260908_0040` (the two holiday tables);
  - `eligibility/service.py` (`list_jurisdictions`, `jurisdiction_for_state_text`), `alerts.py`, `reminders.py`,
    `ports.py`, `contract.py`; migration `20260908_0046`;
  - `resource_assignments/views.py` (`site_facts`);
  - `authorization/contract.py` (the post-baseline matrix);
  - `frontend/src/pages/work-orders/WorkOrderHolidaysSection.tsx`, `workOrderHolidaysState.ts`,
    `workOrderPageState.ts`; `frontend/src/layout/AppShell.tsx`; `frontend/src/pages/alerts/`;
  - `backend/tooling/smoke_data/` (the holiday builder, the Part 4 scenario, `hiring_uat.py`, cleanup).

---

## 4. What it builds

1. **PBL's holiday calendar** - one per year, versioned, with a "complete" mark - in a new module of its own
   (section 5.1).
2. **The Holiday Calendar page**: Admin enters and changes a year; everyone reads (section 6).
3. **The Work Order's changes to the calendar**: Part 4's list, now of holidays added and calendar holidays made
   working days at the normal or the overtime rate, with the new answer wording (section 5.2).
4. **"Holidays that apply"** on the Work Order: a read of the resulting holidays for each state's lines, over the
   contract period, from one pure rule that log sheets and billing will call (section 5.3).
5. **The reminder for a year not set up**, on Alerts (Q2), and a notice on the Work Order (section 5.4).

---

## 5. The rules, step by step

"Today" is the day in Asia/Kolkata.

### 5.1 The calendar

- **A year** is any year from 2000 to 2100. It is **not started** until Admin first saves it, **started** once saved,
  and **complete** once Admin marks it so.
- **A holiday in the calendar** has:
  - its date, inside the year;
  - its kind: national or festival;
  - its name, up to 255 characters;
  - where it applies: **all of India**, or **these states** - one or more of the 36 states and union territories.
- **Refused** (each refusal names the date):
  - a date outside the year;
  - "these states" with no state, or an unknown state;
  - a holiday with no name;
  - a date that applies twice to one state: two all-India holidays on one date, an all-India holiday and a state one
    on one date, or the same state named twice on one date (1.2, point 3).
- **Saving a year** replaces its holidays as a whole and gives it a new version, as a Work Order's holiday list is
  saved. Saving exactly what is there changes nothing and records nothing. A year saved by someone else since the page
  was opened is refused; the page reads it again.
- **Marking complete** is part of the same save, and so is taking the mark off.
- **A Work Order never blocks a change to the calendar.** A Work Order that made a day a working day which Admin then
  takes out of the calendar shows the note of 1.2, point 6.

### 5.2 The Work Order's changes to the calendar

- **The answer**, beside the list (decision 29, reworded):
  - **"The Work Order follows PBL's calendar unchanged"** (was "names no holidays");
  - **"The Work Order changes PBL's calendar as listed"** (was "names these holidays").
  - No answer recorded is missing. "Changes ... as listed" with no change entered is missing. "Follows ... unchanged"
    cannot be chosen while changes are listed.
- **A change** is one of (Q4):
  - **a holiday added**: date, kind (national or festival), optional description - exactly as today;
  - **a working day**: a calendar holiday the Work Order works, charged **at the normal rate** or **at the overtime
    rate** - every hour of that day at the line's own overtime rate (1.2, point 15) - with an optional note, up to
    255 characters (1.2, point 16).
- **Refused**, as today, each naming the date: a date listed twice (a date is either added or a working day, never
  both); a working day with no rate chosen, or a rate on an added holiday; a kind on a working day; a date outside the
  contract or in a gap before an extension; any write on a Closed Work Order.
- **The contract cannot move to leave a change outside it** - added or a working day - by an edit of the dates or by
  removing an extension (1.2, point 7).
- **One list for every line** (decision 27). Each line applies it to the calendar for its own state.

### 5.3 The holidays that apply

For a line whose site is in state S, over the contract period:

```text
every calendar holiday applying to all of India or to S        a holiday, unless
  the Work Order makes that date a working day                   then a working day, at the rate it says
plus each date the Work Order adds                               a holiday
on days inside the contract (not before its start, not after its end, not in a gap before an extension)
```

- **Each day shown says what it is and where it came from**: "Holiday - PBL's calendar", "Holiday - added by this Work
  Order", "Working day, normal rate" or "Working day, overtime rate" (with its note). A calendar holiday made a working
  day stays in the list, so a reader sees it was a calendar holiday; log sheets (8C) count it as a working day, and
  billing (8D) charges it at the rate it says.
- **Lines are grouped by state.** "Lines 1 and 3 - Gujarat"; "Line 2 - Maharashtra"; "Line 4 - site not recorded:
  all-India holidays only".
- **Notes**, beside the list:
  - each year in the period whose calendar is not complete (Q2);
  - each change that does nothing for any line (1.2, point 6);
  - each line whose state is unknown, and what to put right (1.2, point 8);
  - each working day at the overtime rate on a line with no overtime rate that day, naming the line (1.2, point 15).
- **One rule, written once.** The rule above is a pure function in the Work Orders module, with no database or clock,
  tested exhaustively, as `contract_period_rules.py` is. Log sheets (8C) will call it to mark a day as a holiday or a
  working day; billing (8D) will charge a holiday by the line's off-day choice and a working day at the rate it says.

### 5.4 A year not set up (Q2, as recommended)

- **The reminder** "PBL's holiday calendar for <year> is not set up" is raised for every year that is not complete:
  - the next year, from the schedule's first reminder before 1 January;
  - the current year, from the day the package is installed if it is not complete then - on the day of installation,
    2026 has no calendar, so Admin is reminded at once to enter at least October to December.
- **Its date** is 1 January of that year. Its schedule and path are those of section 1.1, Q2, held on **Reminder
  settings** as a fifth kind of reminder, which Admin may change as for the other four.
- **It ends** when Admin marks the year complete. A mark taken off raises it again.
- **"Seen"** works as for certificates: per person, per reminder day.
- **On the Work Order**, the note of section 5.3.

### 5.5 What happens on the day it is installed

- No calendar exists. Every Work Order's "Holidays that apply" shows only its own added holidays and working days,
  with the note that the year's calendar is not set up.
- Practice data's answers and dates carry over (1.2, point 11).
- Admin enters 2026 and 2027, and marks each complete.

---

## 6. Screens

Messages sit beside the button that caused them. Styling uses `globals.css` classes only. A page with no session says
`SIGN_IN_FIRST`, a refused one `SIGN_IN_AGAIN`. Loading goes through the tested pure controllers
(`createQueryController`, `createLatestOnly`), in which only the latest answer is shown and a session change resets
the page.

1. **The menu** gains **Holiday Calendar**, after Work Orders, for everyone.
2. **Holiday Calendar** (`/holiday-calendar`).
   - **A year picker**: the current year, the next year, and every year already started, each with its state - "Not
     set up", "Being entered (version 2)", "Complete". Admin may start another year.
   - **The year's holidays**, earliest first: date, kind, name, where it applies ("All of India", or the states named).
   - **For Admin:** **Add a holiday**, **Remove** on each row, a choice of states for each row, the tick "This year's
     calendar is complete", and **Save**, with its message beside it. The page warns before saving when a change
     touches a day already passed (Q3).
   - **Who saved it, and when**: "Version 3, saved by <name> on 2 October 2026 at 14:05".
   - For everyone else, the page only reads.
3. **The Work Order page, "Holidays"** (now titled "Holidays: PBL's calendar and this Work Order's changes").
   - **The answer**: "The Work Order follows PBL's calendar unchanged" or "The Work Order changes PBL's calendar as
     listed".
   - **PBL's calendar holidays inside the contract**, for the states of the Work Order's lines, one row per date
     with the holiday's name for each state, and beside it the choice **Holiday** (the default), **Working day,
     normal rate** or **Working day, overtime rate**, with an optional note. The choice is open only with "changes
     PBL's calendar as listed".
   - **Added holidays**: **Add a holiday** (date, kind, description), as today.
   - **A working day on a date not in the calendar yet**: **Add a working day** (date, rate, note), for a year not
     set up (1.2, point 6).
   - **Save holidays**, with its message beside it. Only the rows that differ from the calendar are saved.
   - **Holidays that apply** (section 5.3), read only, grouped by state, with its notes and a link to the Holiday
     Calendar.
4. **Alerts** (Q2): the calendar reminder in the same list, with "Mark as seen"; its own filter; counted in the menu.
   **Reminder settings** gains its section.

**A screen check fits in twenty minutes**, on a seeded Work Order with a contract from 1 December 2026 to 30 November
2027, line 1 at a site in Gujarat, line 2 in Maharashtra, line 3 with no site, and no calendar yet:

1. As `admin1`, open **Alerts**: "PBL's holiday calendar for 2026 is not set up" is there. The Work Order's "Holidays
   that apply" shows only its own holidays, with the note for 2026 and 2027.
2. On **Holiday Calendar**, start 2027: Republic Day (national, all of India); Holi (festival, all of India); Gujarat
   Day on 1 May (festival, Gujarat); Tamil New Year and Baisakhi on 14 April (Tamil Nadu; Punjab). Save: version 1.
3. Add Maharashtra Day on 1 May as a national holiday for Maharashtra only: accepted. Try a second all-India holiday on
   26 January: refused, naming the date. Try Gujarat Day again on 1 May for Gujarat: refused, naming the date and
   Gujarat.
4. On the Work Order: line 1's group shows 26 January, Holi and 1 May as Gujarat Day; line 2's the same three, with
   1 May as Maharashtra Day; line 3's the all-India two, with its note. None shows 14 April.
5. Choose "changes PBL's calendar as listed"; set Holi to "Working day, overtime rate", note "customer's plant runs";
   set Gujarat Day to "Working day, normal rate"; add a site festival; save. Holi and Gujarat Day show as working
   days at their rates; the festival shows as added. Line 3 (hourly) shows the note that it has no overtime rate on
   Holi.
6. Add a working day on 15 August 2027 (not in the calendar): saved, with "this change does nothing".
7. Try to move the contract start past the site festival: refused, naming both dates.
8. As `admin1`, mark 2027 complete: the note for 2027 goes. Enter 2026 and mark it complete: the Alerts reminder goes.
9. As `ops1`: Holiday Calendar only reads; the Work Order's changes can still be saved (the billing-terms permission).
10. As `readonly1`: everything reads; no Save.

---

## 7. Permissions

| Permission | Granted to | Allows |
| --- | --- | --- |
| `HOLIDAY_CALENDAR_READ` (new) | the six roles | reading the calendar, its years and the states |
| `HOLIDAY_CALENDAR_MANAGE` (new) | Admin | saving a year, and marking it complete or not |
| `WORK_ORDER_READ` (exists) | the six roles | reading a Work Order's changes and the holidays that apply |
| `WORK_ORDER_LINE_BILLING_TERMS_WRITE` (exists) | Admin, Sales User, Sales Manager, Operations | saving a Work Order's changes, as today |
| `EQUIPMENT_REFERENCE_READ`, `ELIGIBILITY_RULE_MANAGE` (exist) | as now | the Alerts and Reminder settings, as for the other reminders |

Both new permissions join `POST_BASELINE_ROLE_PERMISSION_MATRIX`, as every permission since Slice 9D has. A position
mapped under `ORA-001` later is given `HOLIDAY_CALENDAR_MANAGE` by a grant, with no code change.

---

## 8. Routes

Each new route pinned in `POST_BASELINE_NEW_ROUTES`. The new `holiday-calendar-api-contract.md` and the Work Order
contract's new section state exactly what they accept, return and refuse.

```text
GET  /api/holiday-calendar/states                          HOLIDAY_CALENDAR_READ    200
GET  /api/holiday-calendar/years                           HOLIDAY_CALENDAR_READ    200
GET  /api/holiday-calendar/years/{calendar_year}           HOLIDAY_CALENDAR_READ    200, 422
PUT  /api/holiday-calendar/years/{calendar_year}           HOLIDAY_CALENDAR_MANAGE  200, 409, 422

GET  /api/work-orders/{public_id}/holidays                 WORK_ORDER_READ                       (changed)
PUT  /api/work-orders/{public_id}/holidays                 WORK_ORDER_LINE_BILLING_TERMS_WRITE   (changed)
GET  /api/work-orders/{public_id}/holidays/resulting       WORK_ORDER_READ                       200, 404 (new)
```

- **`GET .../years`**: each year started - year, version, complete, how many holidays, who saved it and when - and the
  current and next year even when not started, if within 2000 to 2100 (HOL1-R1-002).
- **`GET .../years/{year}`**: the year with its holidays, each with its states; `year_version` null when not started.
- **`PUT .../years/{year}`**: `{expected_version, is_complete, holidays[{holiday_date, holiday_kind_code,
  holiday_name, applies_to_code: ALL_INDIA | STATES, state_codes[]}]}`. Whole replacement; `event` null when nothing
  changed; `409` on a stale version; `422` for each refusal of section 5.1; unknown fields refused. (Corrected at review
  round 1, HOL1-R1-003: this line first read `complete` and `description`, while the built route and
  `holiday-calendar-api-contract.md` take `is_complete` and `holiday_name`, the names a calendar holiday is shown with.)
- **`PUT /api/work-orders/{id}/holidays`**: `{expected_list_version, holidays_answer_code: CALENDAR_UNCHANGED |
  CALENDAR_CHANGED, changes[{change_code: HOLIDAY_ADDED | WORKING_DAY, holiday_date, holiday_kind_code
  (HOLIDAY_ADDED only), working_day_rate_code: NORMAL_RATE | OVERTIME_RATE (WORKING_DAY only), description
  (optional for both: an added holiday's description, a working day's note)}]}`. Everything else as Part 4.
- **`GET .../holidays/resulting`**: the period used; the calendar holidays inside it for the states of the Work
  Order's lines, by date, with each state's name for the day (what the form offers a choice beside); and for each
  state group its lines, its state (or the problem), and its days - date, kind, name or description, `day_code`
  (`HOLIDAY` | `WORKING_DAY`), `source_code` (`CALENDAR` | `WORK_ORDER`), a working day's rate and note; the years not
  complete; the changes that do nothing; the lines with no overtime rate on an overtime working day. It reads; it
  never writes.

Errors are `{"detail": "..."}` in plain words.

---

## 9. Events

| Event | Record type, module | Payload |
| --- | --- | --- |
| `HOLIDAY_CALENDAR_YEAR_RECORDED` / `HOLIDAY_CALENDAR_YEAR_CHANGED` | `holiday_calendar_year`, `holiday_calendar` | the year; the version; complete; the holiday count; the dates added, removed and changed (a change of kind, name or states) |
| `WorkOrderHolidaysRecorded` / `WorkOrderHolidaysUpdated` (names kept) | as Part 4 | the version; the answer; the counts of holidays added and of working days; the dates entered, taken off and changed (a change of kind, rate, description, or between added and working day) |

Dates, codes and counts only. A name, description or note is free text and never appears in a payload. Marking a
reminder as seen records no event (ELG-2).

---

## 10. Data, module and migration

### The module

`backend/app/modules/holiday_calendar/` (new):

```text
contract.py    kinds, "applies to" codes, the year range, events, record type, labels
rules.py       pure, no database or clock: a year's refusals (section 5.1); the dates added, removed and changed
               between two versions; which holidays apply to a state
repository.py  its three tables only
schemas.py, routes.py
service.py     reading and saving a year (the year row locked for the write); and the public reads other modules use:
               holidays_between(first_day, last_day), years_status(years), state_for_address(text)
```

- **The states** are read through Eligibility's public `list_jurisdictions` and `jurisdiction_for_state_text`, which
  8A already uses. The calendar keeps no copy. If a shared list of places is ever built, both move to it.
- **Work Orders reads the calendar** through the service's public reads. The calendar never reads Work Orders.
- **The reminder** reaches Alerts through a port, as Resource Assignments' allocations do: Eligibility's `ports.py`
  gains `CalendarYearSource`, which the calendar registers when it is loaded. `app.main` always loads it, and so does
  the smoke-data harness. With none registered, reading the Alerts fails with a server error rather than showing no
  calendar reminder (fail closed, as ELG-2).
- **`MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`** gains a row: "Holiday Calendar (platform reference) - owns PBL's default
  holiday calendar per year, its versions and its complete mark; does not own a Work Order's changes to it, what a
  holiday is charged, or employees' holidays for pay; depends on Eligibility's states."

### Work Orders

- `services/holidays.py`: the new answer codes, the two kinds of change, the notes; otherwise unchanged.
- `holiday_rules.py` (new, pure): the rule of section 5.3.
- `services/resulting_holidays.py` (new): the read of section 5.3 - the lines and their sites, the contract period and
  its gaps, the list, and the calendar through its public read. It imports `services/common.py` and the calendar's
  service only.
- `contract_period.py`'s reverse check already reads every date in the list, so a working day is covered as a day
  added is. Only its message changes: it names what the date is - "a holiday is listed on" for a day added, "a
  working day is listed on" for a calendar holiday made a working day.

### Migration `20260908_0047_holiday_calendar` (Q5), parent `20260908_0046`

Rows spelled out, not imported, so the revision stays a frozen snapshot (the `0033` to `0046` convention).

- **`holiday_calendar_year`**: public id; `calendar_year` (unique, 2000 to 2100); `year_version` (1 or more);
  `complete_marked_at` and `complete_marked_by` (both or neither); created and updated, by and at.
- **`holiday_calendar_date`**: public id; the year (a composite key carrying `calendar_year`, with a CHECK that the
  date falls in it); the date; the kind (`NATIONAL` | `FESTIVAL`); the name (not blank); `applies_to_code`
  (`ALL_INDIA` | `STATES`). The kind and where it applies are independent (1.2, point 2).
- **`holiday_calendar_date_state`**: the holiday and a state (a key to `eligibility_jurisdiction`), unique together.
- Rules across rows - "these states" names at least one; one date at most once per state; a state not the
  all-India entry `IN` - are the service's, under the year's row lock, as Part 4's service owns "names no holidays
  holds no dates".
- **`crm_work_order_holiday_list`**: `NONE` becomes `CALENDAR_UNCHANGED` and `LISTED` becomes `CALENDAR_CHANGED`, and
  the CHECK follows.
- **`crm_work_order_holiday`**: `change_code` (`HOLIDAY_ADDED` | `WORKING_DAY`; existing rows `HOLIDAY_ADDED`);
  `working_day_rate_code` (`NORMAL_RATE` | `OVERTIME_RATE`, only and always with `WORKING_DAY`); `holiday_kind_code`
  only and always with `HOLIDAY_ADDED`; `description` optional for both. The unique date per list stays.
- **The two permissions**, with their grants.
- **Alerts (Q2)**: a fifth reminder kind, `HOLIDAY_CALENDAR_NOT_SET_UP`, in the setting and "seen" CHECKs; the "seen"
  table takes a new subject, `holiday_calendar_year`, for which the asset and certificate kind are empty (a CHECK by
  subject); its key CHECK compares the whole key, exactly six parts (HOL1-R2-002); version 1 of its setting, with the
  schedule and path of Q2.
- **Downgrade**: drops the three tables and the permissions; deletes the working days, the new kind's settings and
  "seen" marks; puts the codes and columns back. It loses the working days, which did not exist before.

### Smoke data

- The Part 4 builder takes the new shape; the Part 4 and Hiring user-test scenarios keep their meaning (answers and
  dates carry over as section 5.5 says).
- A new scenario, `holiday-calendar`, seeds the screen-check Work Order of section 6 with no calendar.
- **The harness never saves a calendar year of a real year.** The calendar is shared by everyone; a seeded year
  could overwrite PBL's. Tests and E2E use years far ahead (2090s), created by their run and removed by its cleanup
  under the TE-4 provenance rule, and only if still at the version the run left.

---

## 11. Not in HOL-1

| Left out | Where it goes |
| --- | --- |
| Working out a charge for a holiday | Billing (8D), from the off-day choice |
| Marking a log-sheet day as a holiday; correcting approved log sheets after a calendar change | Log sheets (8C), through the rule of section 5.3; `LBE-001` |
| Locking the Work Order's changes at mobilisation | Still open (`DEFERRED_REQUIREMENTS.md`): decided when mobilisation is built |
| Changes for some lines only ("only these lines") | Later, if a Work Order needs it (decision 27); nothing entered changes |
| "Keeps only national holidays" as one choice | Not wanted: no Work Order works through every festival (Q4) |
| A charge for a holiday that stays a holiday other than the line's off-day term | Not wanted: answer 24, confirmed (Q4, point 3) |
| Different working hours on different weekdays (FRS 2.4.7) | Still open, with 8C |
| Employees' holidays for attendance and pay | 8B, from PBL's HR terms |
| Copying last year's calendar; loading holidays automatically | Later, if Admin asks |
| Email and SMS for the reminder | `NTF-001`, with a provider |
| Updating the user test pack | After the test (Q1) |

Accounts, Commercial Offers, Resource Requirements, Resource Assignments, the Equipment Reference's tables, ELG-1's
tables, and the frozen Slice 6D.1 handoff contract do not change.

---

## 12. What would stop implementation and come back to the owner

- An answer to Q2 other than as recommended: the smaller alternative removes the Alerts work (sections 5.4, 6 item 4,
  the port and the migration's Alerts part) but not the shape.
- Q1 answered "in the test": the test pack, the practice data and a practice calendar join this package.
- Real Work Orders needing changes for some lines only, or a third kind of holiday.
- The state list needing to move out of Eligibility before this can be built on it.

---

## 13. Differences from earlier records (recorded per ADR-013)

| # | Earlier record | HOL-1 | Why |
| --- | --- | --- | --- |
| 1 | Part 4, answer 25: dates "not taken from a company calendar"; "What Part 4 does not do": "No company holiday calendar" | A calendar per year; the Work Order states only how it differs | The owner, 2 October 2026 (already recorded beside answer 25) |
| 2 | Part 4, decision 29: "names no holidays" / "names these holidays"; codes `NONE` / `LISTED`; field `holidays[]` | "follows PBL's calendar unchanged" / "changes PBL's calendar as listed"; codes `CALENDAR_UNCHANGED` / `CALENDAR_CHANGED`; field `changes[]` | The owner's rewording. The old code `NONE` reads as "no holidays", the very misreading the owner found; 8C and 8D will read these codes |
| 3 | `DEFERRED_REQUIREMENTS.md`: "a calendar holiday removed (the date, and why)" | "Made a working day", at the normal or the overtime rate, with an optional note; accepted even when the date is not (yet) in the calendar, with a note | The owner's answer to Q4: a festival worked may be charged at the overtime rate, so the change carries its rate. A Work Order is often entered before next year's calendar exists; the note also shows a wrong date at once |
| 4 | Part 4 events: `holiday_count`, `added_dates`, `removed_dates`, `changed_dates` | Counts of each kind of change; the dates entered, taken off and changed | "Added" now names a kind of change; the payload must not mix the two meanings. Event names unchanged |
| 7 | 2 October 2026 decision: "The calendar decides which days are holidays, never what they are charged" | Still true of the calendar. A Work Order's own change may now say how a calendar holiday it works is charged: the normal or the overtime rate | The owner's answer to Q4. A Work Order term, recorded explicitly, so nothing is guessed (`WBT-001`); a day that stays a holiday is still charged by the off-day term (answer 24) |
| 5 | ELG-2, section 13 row 8: the Alerts page is Eligibility's own list | It also gathers the calendar's reminder, through a port (Q2) | ELG-2 section 11 expected other modules' reminders to join it |
| 6 | `FUTURE_SLICES.md`, 8C: built "before or with" log sheets | Built before | The owner, 2 October 2026 ("after TE-7") |

---

## 14. Tests and checks

- **The pure rules** (`holiday_calendar/rules.py`, `work_orders/holiday_rules.py`):
  - every refusal of section 5.1; one date for different states accepted; the version diff;
  - which holidays apply to a state; all-India and state holidays together;
  - the resulting days: calendar holidays, those made working days at each rate, and those added; a working day not
    in the calendar; a day added already in it; before the start, after the end, in a gap, on the first and last day;
    no start; no end; "until the work is complete"; a year not complete; a line with no state; a line with no
    overtime rate on an overtime working day (none recorded, "not in the Work Order", no terms, an hourly line, a
    later period).
- **The calendar, by the service and the route:** saving a new year; a change; the same again (no event, no version);
  a stale version (`409`); each refusal (`422`); marking and unmarking complete; the event and its payload, with no
  name in it; every database CHECK by a direct insert naming its constraint; refused without
  `HOLIDAY_CALENDAR_MANAGE`; read by each role; the year row lock serialising two saves.
- **The Work Order:** each answer and each kind of change, each rate; every Part 4 rule still holding (the 54 Part 4
  holiday tests carried over to the new shape, none weakened); a working day blocking a contract move, by an edit and
  by removing an extension; the notes; the resulting read for lines in two states, one with no site, one with a state
  not recognised; Closed; not found; the handoff writing and returning nothing of it; existing answers and dates
  carried over by the migration.
- **Alerts (Q2):** the reminder raised for the next year from its first reminder day, and for the current year; ended
  by the complete mark and raised again when it is taken off; who it reaches; "seen"; the port not registered failing
  closed; the four certificate reminders unchanged (ELG-2's tests pass untouched).
- **Migration:** from the empty database to the single head; downgrade, then upgrade again; the codes carried over.
- **Frontend:** pure state for the calendar page (the form's rules, as the server's; the warning for a past day; the
  year picker) and for the Work Order's changes and the resulting view, each tested with answers late and out of
  order; the page-load generation including the resulting read; the route-table tests; typecheck, tests, build.
- **Smoke data and cleanup:** the new scenario; the carried-over scenarios; cleanup removing only the run's own years.
- **E2E** (`holiday-calendar.spec.ts`): Operations reads the calendar but has no Save; on a seeded Work Order and a
  seeded far-ahead year, a working day and a day added change "Holidays that apply". Playwright saves no real
  year.
- **Full gate:** the full backend regression, one suite at a time; the frontend gate; the full E2E suite; the
  migration from empty and back; `check_tracked_secrets.py` and `validate_contract_fixtures.py`; the frozen handoff
  contract's hash before and after; independent review, up to three rounds; the owner's screen check, with the steps in
  the chat.

---

## 15. Shared files this package touches

- `backend/app/main.py`: the calendar's router (and its port registration).
- `backend/app/modules/authorization/contract.py`: the two permissions.
- `backend/tests/fixtures/post_baseline_tightened_routes.py`: the five new routes. Read it by eye after any merge.
- `frontend/src/routes.tsx` and its tests; `frontend/src/layout/AppShell.tsx` (the menu).
- `backend/app/modules/eligibility/` (`ports.py`, `alerts.py`, `contract.py`, `schemas.py`, `repository.py`) and
  `frontend/src/pages/alerts/`, `frontend/src/pages/equipment/` (Reminder settings) - Q2 only.
- `backend/app/modules/work_orders/` and `frontend/src/pages/work-orders/` (the holidays section and page state).
- `backend/tooling/smoke_data/`, `e2e/`.

**Documents updated when it is built:**

- `holiday-calendar-api-contract.md` (new); `work-order-contract.md` (a HOL-1 section); `eligibility-api-contract.md`
  (the fifth reminder, Q2);
- `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md` (the new row); the module table in PBL's internal working instructions;
- `DEFERRED_REQUIREMENTS.md` ("PBL's default holiday calendar": built, and what remains), `FUTURE_SLICES.md` (8C,
  8D), a pointer beside answer 25 in the Part 4 record;
- this design's implementation record, an acceptance record, a continuity note and `NEXT_STEPS.md`.

---

## 16. Implementation record (2 October 2026)

Built on the agreement of section 1.0, on `hiring/hol-1-holiday-calendar` from `main` at `e1f7409`; migration
`20260908_0047`, parent `20260908_0046`. The frozen handoff contract's SHA-256 is unchanged
(`70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a`).

### What exists now

```text
backend/app/modules/holiday_calendar/      contract, rules (pure), repository, schemas, service, routes; registers the
                                           Alerts' CalendarYearSource when loaded
backend/app/modules/work_orders/
  holiday_rules.py                         the holidays that apply, pure: the window, the days, the notes, the overtime rate
  services/holidays.py                     the answer and the two kinds of change (HOLIDAY_ADDED, WORKING_DAY)
  services/resulting_holidays.py           GET .../holidays/resulting; imports services/common.py and the calendar only
  services/common.py                       gains _account_reference_maps and _usable_address (refinement 2)
  services/contract_period.py              its reverse check names a working day as such
backend/app/modules/eligibility/           ports.CalendarYearSource; the fifth reminder kind in contract, alerts, schemas
backend/alembic/versions/20260908_0047_holiday_calendar.py
frontend/src/pages/holiday-calendar/       the Holiday Calendar page and its tested pure state
frontend/src/pages/work-orders/            the Holidays section rewritten (choices beside each calendar holiday, typed
                                           working days, holidays added, Holidays that apply) and its tested state
frontend/src/pages/alerts/                 the fifth kind; a calendar row links to its year
backend/tooling/smoke_data/                scenario holiday-calendar; core bundle record set holiday_calendar_target;
                                           cleanup of the run's calendar years by provenance
e2e/tests/holiday-calendar.spec.ts
```

Routes added: `GET /api/holiday-calendar/states`, `GET /api/holiday-calendar/years`, `GET` and `PUT
/api/holiday-calendar/years/{calendar_year}`, `GET /api/work-orders/{public_id}/holidays/resulting` - all five pinned.
The Work Order's `GET`/`PUT .../holidays` change shape (`work-order-contract.md`, "HOL-1"). Permissions added:
`HOLIDAY_CALENDAR_READ` (the six roles) and `HOLIDAY_CALENDAR_MANAGE` (Admin).

### Refinements made while building (recorded per ADR-013)

1. **The holidays that apply are read again when what they come from changes on the page** - the contract's dates and
   extensions, a line's site detail, a line's billing terms, the Work Order's own changes - by a key of their versions
   (`resultingRefreshKey`), with a Refresh button besides. The read itself is the separate route of section 8.
2. **Two address helpers moved to `services/common.py`.** `_account_reference_maps` and `_usable_address` were
   `line_detail.py`'s alone; the holidays that apply read each line's site exactly as the line's detail does, and a
   concern module imports only `common` (`CODING_STANDARDS.md`, "When a service outgrows one file"). Moved verbatim; no
   public name changed; nothing patched them.
3. **A calendar reminder begins on the day the package came** - its setting's first version, loaded by the migration -
   as section 5.4 says. The first build counted it from two years before the year, so on the day of installation the
   Alerts read "Reminded 286 times since 2 November 2025": found in the builder's own browser check, corrected, and
   tested (`test_a_year_running_when_the_reminder_came_is_reminded_from_that_day_not_before`).
4. **One free-text column per change.** An added holiday's description and a working day's note are both
   `description`, never in an event.
5. **Event payload names.** `holidays_added_count`, `working_days_count`, `entered_dates`, `taken_off_dates`,
   `changed_dates` - section 9's "counts of holidays added and of working days; the dates entered, taken off and
   changed".
6. **Years for tests and the harness.** Backend tests use 2090 to 2094 and clear them before and after; the harness
   starts the latest free year from 2099 down to 2095, and refuses, writing nothing, when none is free. The harness's
   cleanup removes a run's year by provenance, whoever changed it later - as a run's Work Orders are.
7. **The Reminder settings' "last band" message** names the date generally - a certificate's last day, or 1 January for
   a calendar year - in the server and the page alike; ELG-2's tests' phrase "never left without reminders" is kept.
8. **The Alerts' search box** is labelled "Machine, piece, Work Order, allocation or year", and finds a calendar reminder
   by its year; the ELG-2 Playwright spec follows the label.
9. **The rewritten Holidays section uses the shared stylesheet** (`globals.css`) - its inline styles went with the
   rewrite - and the calendar page adds one class, `.state-picker`.

### Tests and checks

At the build (2 October 2026), on the worktree stack:

```text
tests/test_hol1_holiday_rules.py           49 passed
tests/test_hol1_holiday_calendar_api.py    38 passed (42 after review round 1)
tests/test_hol1_resulting_holidays_api.py  16 passed
tests/test_hol1_calendar_reminder.py       16 passed (17 after review round 1)
tests/test_slice_7d_part_4_holidays.py     81 passed (54 before; every Part 4 case carried over, none weakened)
ELG-2's three files                        111 passed (three lists of kinds gain the fifth)
harness (smoke data, hiring UAT, ELG-2)    all pass, with three new or extended cases
authorization and TE-6 surface             129 passed
frontend                                   typecheck clean; 496 tests (462 before; 497 after review round 2, 498 after round 4, 501 after the screen check)
E2E                                        35 passed, 9 skipped, 0 failed (two new); cleanup clean
```

The full regression, the migration from empty and back, and the frontend build are recorded in the acceptance record's
Results.

### Independent review

the independent reviewer, one bounded packet a round, up to three rounds.

**Round 1** (tree `9919240f`, packet SHA-256 `98749c3c...`): `CORRECTION_REQUIRED`, three material findings, all
accepted and corrected.

- **HOL1-R1-001 - a save's answer could show the next save's year.** `save_year` read the year it returns after its
  commit, and an identical save after its rollback - both of which let the write lock go - so a second save committing
  in that instant was shown as the first one's version, beside the first one's event. Nothing was written wrongly; the
  answer was. Corrected: the answer is read inside the transaction, before the commit or rollback, as the Work Order
  holidays save already did. Two new tests run a second save from the session's own `after_commit` and
  `after_rollback` hooks - the instant the lock is let go - and check the first answer is its own; both fail on the
  code as it was. By analogy, ELG-2's reminder-settings save has the same shape: recorded in DEFERRED_REQUIREMENTS,
  not changed here (another module's code).
- **HOL1-R1-002 - in 2100 the next year is 2101, which the calendar cannot keep.** The year list offered it and the
  Alerts reminded about it from 2 November 2100, a reminder nothing could ever end. Corrected: the year list adds the
  current and next year only within 2000 to 2100, and the calendar's answer to "which years are not complete" never
  names a year outside them (the port's description says so). Two clock-controlled tests: the year list in 2100, and
  the Alerts on 15 December 2100.
- **HOL1-R1-003 - section 8 named the save's fields `complete` and `description`;** the route and the API contract
  take `is_complete` and `holiday_name`. Section 8 corrected. A test pins the request's field names to the contract's
  and shows the old names are refused (`422`), never half understood. The suggested contract-fixture check is not
  used: the PAF-1 fixture validator covers the foundation contracts, not module API contracts, and the backend's test
  container holds no `docs/`.

The packet's residual note - the regression still running, the migration round trip and the frozen file not in it -
is answered in round 2's packet: the regression result, the migration check's output, and the frozen file whole.

**Round 2** (commit `0288bb4`, packet SHA-256 `eced93f0...`): `CORRECTION_REQUIRED`, two material findings, both
accepted and corrected. Round 1's corrections were not questioned.

- **HOL1-R2-001 - from 2101 the page could not be used.** The years route leaves out a year the calendar cannot keep,
  but the page, asked for no year, still read India's current year - 2101 - and the server refused it, so the whole
  page failed, with no picker to reach 2100. The same before 2000. Corrected: the page reads the current year, or
  outside 2000 to 2100 the nearest year the calendar keeps (`yearToShow` in `holidayCalendarState.ts`), which the
  picker already offers beside the years started. A test covers 2026, 2100, 2101 and 1999.
- **HOL1-R2-002 - the "seen" key CHECK let a malformed key through.** It compared the key part by part and required the
  seventh part empty; PostgreSQL's `split_part` returns an empty part both when there is none and when it is empty, so
  a key ending `|`, or `||` and more, passed - and, being a different text, could sit beside the real key under the
  unique index, never read. The same check was ELG-2's (0046); HOL-1 rewrote it and kept the gap. Shown on the worktree
  database: with the earlier check put back in a rolled-back transaction, three keys for one mark - the real one, one
  ending `|`, one ending `||suffix` - were all stored. Corrected: the CHECK compares the whole key with its six parts
  joined by `|`. Direct-insert tests refuse the trailing `|`, `||suffix` and a leading `|`, for a year's mark and for a
  certificate's. The downgrade puts back 0046's check word for word: a downgrade restores the revision below it, and
  the scratch-database round trip shows the checks after it identical to a database built to 0046.

**Round 3** (commit `a4b0930`, packet SHA-256 `8db56c60...`), the last of the three agreed: `CORRECTION_REQUIRED`, one
material finding, accepted and corrected. Rounds 1 and 2's corrections were not questioned.

- **HOL1-R3-001 - a name, description or note too long was refused without its date.** The request schemas carried a
  255-character limit, which FastAPI applies before the service runs, so the calendar's own dated message ("The name of
  the holiday on 26 January 2027 is longer than 255 characters.") was never reached and the answer was the request
  validator's list - against the contracts' "each naming the date". The same for a Work Order change's description or
  note, a limit Part 4 had too, and for a code too long to be one known. The screens stop these boxes at 255
  characters, so it showed only through the API. Corrected: the request schemas carry no lengths for these; the
  calendar's rules and the Work Order holidays service refuse in words naming the date
  (`WORK_ORDER_HOLIDAY_DESCRIPTION_MAX_LENGTH` in the Work Order contract module). The tests now assert the words, not
  only `422`; on the code as it was, both failed with the validator's list.

**Round 4**, run on the owner's word (2 October 2026: "yes, send round 4") after round 3 required a change, on commit
`90d9df3` (packet SHA-256 `4581ca14...`): `CORRECTION_REQUIRED`, two findings called material. Round 3's correction was
not questioned.

- **HOL1-R4-001 - not a defect; the packet left out the guard.** The review read that a holidays save answering after
  the user had opened another Work Order would be shown, and could be saved, under the second one, because the
  reducer's `holidays-applied` case does not compare generations. It need not: `workOrderPageReducer` drops every
  action but `load-started` whose generation is not the current one, before its `switch` - the lines just above the
  excerpt the packet carried. The page dispatches the save's answer with the generation the save began in, and opening
  another Work Order starts a new one. An existing test already showed a late save ignored after a new load; a test now
  names the case the review described - Work Order A's save answering after B's load began, and after B's holidays
  loaded - and asserts B's state unchanged. With the guard removed for a check, it fails, with the page's other
  generation tests.
- **HOL1-R4-002 - a required field left out was still refused without its date.** Round 3 took the lengths out of the
  request schemas, but a holiday's name, kind or "applies to", a change's code, or the Work Order's answer left out
  (or null) was still refused by the request validator before the service could say which date. Corrected: only the
  date is required in a holiday or a change; the rest reach the calendar's rules and the Work Order holidays service,
  which refuse them in words naming the date (the answer, which has no date, in its own words). A holiday with no date
  has no date to name and is refused as the request stands. Tests assert the exact words for each field left out and
  null.

**Round 5**, run on the owner's word (2 October 2026: "yes, send round 5 when ready"), on commit `039d308` (packet
SHA-256 `03669d47...`), its packet carrying the whole Work Order page reducer and where the page starts a load:
**`ACCEPTED`**, no findings. Its residual note: the final full regression was running when the packet was built, and the
final Playwright run and the owner's screen check were still to come - recorded in the acceptance record's Results.

### After the owner's screen check (3 October 2026)

The owner passed every step but three, and two of the three found what the reviews had not: how the screens behave
just after a save.

- **Step 8 - the note on a working day that does nothing was shown only under "Holidays that apply"**, further down
  the page, while beside **Save holidays** the page said only "Holidays saved." The rule that an action's feedback sits
  by its button applies. Corrected: once the holidays that apply have been worked out from the version the save made,
  their notes on the Work Order's changes are shown beside "Holidays saved." too (`notesForSavedVersion` in
  `workOrderHolidaysState.ts`; one `ChangeNotes` piece draws them in both places). The acceptance step now says where.
- **Step 9 - not a defect.** The contract's start was moved to 1 August 2027 rather than its end; the refusal named
  the earliest change that would fall outside, the working day on 22 March 2027 - right for what was entered.
- **Step 10 - the menu's Alerts count still showed 1 after the last calendar reminder had ended**, and after a page
  reload, while the Alerts page listed none. The count is kept for up to five minutes (ELG-2's design) and read again
  at once only after reminders are marked seen; marking a year complete ends its reminder without that. Corrected: the
  calendar page tells the menu to read its count again after a save, and the Alerts page does so whenever it reads its
  list, so the two never disagree there (`announceAlertsChanged` in `alertsState.ts`, raising the event the menu already
  listened to). A certificate renewal recorded on another page still waits up to five minutes, as ELG-2 designed, unless
  the Alerts page is opened.

Both checked in the browser on the worktree stack: unticking 2026's complete mark raised the count to 1 at once and
ticking it again cleared it at once; a save with a working day on 15 August 2027 showed the note beside "Holidays
saved." Frontend only; tests for both.
