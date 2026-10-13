# ELG-2 Certificate reminders and escalation - design

Status: **Design proposed 30 September 2026; revised and agreed 1 October 2026.** The owner's answers (section 1.0):
Q20 deferred, the points of section 1.3 accepted, Q19 reworked on the owner's point that a missing certificate's date
can be known, and its follow-up Q19a **as recommended - "go ahead and build it"**. Built on that agreement.

Hiring lane (Track 2). Worktree `<a separate worktree>`, branch `hiring/elg-2-certificate-reminders`, based on
`main` at `82acebd`. Migration slot `20260908_0046`, parent `20260908_0045` - the single Alembic head on `main`. No
branch on `origin` holds a `0046` revision (checked 30 September 2026). Foundation Slice Mode: the shape is built
properly, the screens minimally. The frozen Slice 6D.1 handoff contract's SHA-256 is
`70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a` before this package.

**What is already agreed.** ELG-1 designed the reminders in its section 19. The owner answered its questions Q14 to
Q18 "All as recommended" on 27 September 2026: build them as ELG-2, after 8A's core and before the Hiring user test.
This design builds that. It fills in what section 19 left open, and it asked two new questions (section 1.2). One
follow-up is open (section 1.1).

In plain words:

- **Three kinds of reminder** - and a fourth, as recommended in Q19a.
  1. **A certificate running out** on any machine or piece of kit - what Certificates due lists today, now as
     reminders.
  2. **A certificate running out before the job starts** - on a machine allocated to a job, or a piece of kit going
     with it.
  3. **A certificate running out during the job.**
  4. **A certificate not yet recorded** (Q19a): papers not entered since a machine was added to the Equipment
     Master, or since a rule began to require them.
- **Every reminder has a date and a reason.** For a certificate running out, the date is the day it runs out. For one
  not yet recorded, it is the day it became needed: the day the machine was added, or the day the rule took effect.
- **Each is repeated on a schedule.** The standard schedule reminds 60 and 30 days before the certificate runs out,
  weekly from 15 days before, daily from 7 days before, and every day after it has run out, until someone deals with
  it.
- **Each reaches more people as the day comes nearer.** The Fleet Admin (Admin today) from the first reminder;
  Operations from 15 days before, or at once when the machine is on a job; Management from 7 days before. Nobody
  drops off.
- **On screen only, for now.** The menu shows **Alerts** with a count. The Alerts page lists the reminders that have
  reached you. Email, SMS and messaging come when they are integrated.
- **"Mark as seen"** quiets a reminder for you until its next reminder day. It never stops the reminders, and it
  never stops them reaching more people. Only dealing with the certificate does:
  - a renewal is recorded with its copy;
  - or a "not applicable" mark is recorded, where the rule allows one;
  - or the machine is freed or replaced on the job, or the piece taken off the trip;
  - or the machine is retired.
- **Admin changes the schedules and the paths** on a **Reminder settings** page. Each change is kept as a new
  version, with who made it and when.

**Reuse, not a second structure** (CODING_STANDARDS.md section 1, DRY first):

- **What raises a reminder** is ELG-1's own judgement, unchanged:
  - the first reminder uses the results Certificates due uses;
  - the other two use the check each allocation already shows as "today's answer" (8A core, section 6.4).
- **The allocations** are 8A's. Eligibility reads them through a port that Resource Assignments registers, as
  Resource Requirements reads coverage today. Eligibility never imports Resource Assignments.
- **Events** go through `record_business_event`, with codes, ids and dates only.
- **The screens** reuse the tested loaders of ELG-1 and 8A (`createQueryController`, `createLatestOnly`).

**What is new** is only what nothing holds today:

- the settings - each reminder's schedule and path, versioned;
- the "seen" marks.

The reminders themselves are **worked out each time they are read**, as Certificates due is. No job runner is
needed, and nothing is sent.

### Carried over from 8A core

8A core's pull request, PR #80, merged as `82acebd` on 30 September 2026 (16:24 UTC). All seven checks succeeded on
its head `0e22166`:

- Backend regression;
- Empty-database migrations;
- Frontend build and tests;
- Contract fixture validation;
- Secret and dependency checks;
- Compose build, health and E2E;
- `Required validation`.

This is recorded in `docs/continuity/NEXT_STEPS.md` with this design, and goes into ELG-2's continuity note when it
is built.

---

## 1. Questions for the owner

### 1.0 Answered by the owner (1 October 2026)

| # | Answer |
| --- | --- |
| Q20 | **"ok. Put note as a deferred design requiring PBL confirmation before taking up."** No note with "seen" in ELG-2. Recorded in `DEFERRED_REQUIREMENTS.md`, "Certificate reminders: what ELG-2 leaves out", as needing PBL's confirmation before it is taken up |
| Section 1.2 | **"Rest fine."** Each point there stands |
| Q19 | Not answered; the owner asked for the logic: "Q19 - 2 options: New certificate for an existing machine and Certificate(s) for a new machine added to the Equipment Master. For the former, why this certificate is added now and start date may be from a date prior to date of adding. For the latter, also, same should work with Machine added to master as the reason why this certificate is added. If machine has been newly added but certificate is missing, I think it already shows that a certificate is missing, will it not? I am unclear why it should be treated as already run out. Please explain your logic." |

**The logic of the first Q19, and why it changes.** The reminders count days to a date: the day a cover ends. The
first Q19 assumed that a missing certificate has no such date, so there were only two choices: show it to everyone
at once, or to the Fleet Admin alone. It chose "everyone at once" because a missing certificate stops a machine
exactly as a run-out one does: both block allocation. "Treated as run out" was only about when, and to whom, the
reminder is shown. The screen still says "missing", as Certificates due already does.

The owner's point is right: the date **can** be known, from the reason the certificate is needed now. A machine added
to the Equipment Master needs its papers from the day it was added. An existing machine needs a newly required
certificate from the day the rule requiring it takes effect - which may be before the day the rule was entered. So
every missing certificate now has a date and a reason (section 5.2), and the reminders follow it like any other.

That leaves one choice, Q19a below: who sees papers not yet entered for a machine just added, and from when.

| # | Answer |
| --- | --- |
| Q19a | **"Q19a as recommended, go ahead and build it"** (1 October 2026): a fourth reminder, "A certificate not yet recorded", with its own schedule and path |

### 1.1 The follow-up, as put (answered as recommended)

#### Q19a. Papers not yet entered: who sees them, and from when

Every reminder's path counts days **before** its date: Operations from 15 days before, Management from 7 days before.
A missing certificate's date is the day it became needed. For a machine just added, that day is today. So on one path,
Operations and Management would see a new machine's missing papers on the day it is added, before the Fleet Admin has
had time to enter them.

**Recommendation:** a fourth reminder, **"A certificate not yet recorded"**, with its own schedule and path, which
Admin changes like the others:

- It covers papers not entered, or entered without their copy, since the machine was added or the rule began.
- Standard schedule: every day, from the day it became needed.
- Standard path: the Fleet Admin from that day; Operations from 7 days after it; Management from 14 days after it -
  each only if the papers are still not entered.
- A certificate that lapses later stays "A certificate running out", on its own path: one that runs out, a "not
  applicable" mark that ends, or a renewal recorded without its copy. So nobody who was reminded before drops off.

**The alternative:** one path for all. Everyone on it sees a new machine's missing papers on the day it is added.

### 1.2 The questions as first put, 30 September 2026 (record)

#### Q19. A certificate that has never been recorded

Sometimes a certificate is not recorded at all, or it is recorded without its copy. For example, a machine has just
come in from Plum's report, and its papers are not entered yet. The platform cannot tell since when the certificate
has been missing. So it cannot count the days to decide who should be reminded.

**Recommendation:** treat it like a certificate that has already run out.

- It is shown every day, to everyone on the path at once: Fleet Admin, Operations and Management.
- This continues until it is recorded with its copy.
- This is the cautious reading. Before go-live, the spreadsheet upload (ELG-1, section 18) will enter the fleet's
  papers. After that, anything still missing is a real gap.

One effect for the Hiring user test: if the testers see PBL's real fleet, its papers must be entered first.
Otherwise every machine will fill the Alerts page.

**The alternative:** while the machine is not on a job, only the Fleet Admin sees it. Operations and Management see
it once the machine is on a job. A machine missing a certificate cannot be put on a job anyway, because every
rule loaded today blocks.

#### Q20. A short note with "seen"

When someone marks a reminder as seen, should they be able to add a short note for the others it has reached? For
example: "Renewal applied for at the RTO, expected on 10 October."

**Recommendation:** not now. The Alerts page shows who has seen each reminder, and when. A note can be added after
the user test, if the testers ask for it.

If you want it now, the note would be optional, one line, and shown to everyone the reminder has reached.

### 1.3 Decided in this design - accepted ("Rest fine", 1 October 2026)

- **Alerts** is in the menu for everyone, just below Dashboard. Its count is the reminders that have reached you and
  that you have not yet marked as seen.
- **"Mark all shown as seen"** marks every reminder on the page at once. Without it, the daily reminders of the last
  week would need one click each, every day.
- **Who has seen a reminder**, and when, is shown to everyone the reminder has reached. Management can then see that
  the Fleet Admin has seen it.
- **Management may mark reminders as seen**, although its role only reads. Marking changes nothing in the records. It
  changes only that person's own list.
- **Everyone may read the Reminder settings.** Only Admin may change them (Q18).
- **The count in the menu is refreshed at most every five minutes,** and at once after you mark something as seen.
  The Alerts page itself is always up to date.

### 1.4 Already settled, not asked again

| Point | Settled by |
| --- | --- |
| Three reminders, built together after 8A's core and before the Hiring user test | Q14 |
| The standard schedule: 60 and 30 days before, weekly from 15, daily from 7, and every day after it has run out; the same for all three reminders to start with, changeable for each | Q15 |
| The standard path: Fleet Admin from the first reminder; Operations from 15 days before, and at once for a machine on a job; Management from 7 days before. Nobody drops off. Sales is not on it | Q16 ("Please say who else" - answered "as recommended") |
| The path names roles now, and `ORA-001` authorities once positions are live | Q16; ELG-1 section 19.3 |
| Seeing a reminder never stops the reminders or the escalation; only dealing with the certificate does | Q17 |
| Admin changes schedules and paths under `ELIGIBILITY_RULE_MANAGE`; a change applies when saved, and records who made it and when | Q18 |
| On screen now; other channels are configured once integrated | Owner, 27 September 2026 (ELG-1 Q4; "applies to Q9-13 also") |
| Admin acts as Fleet Admin until that role exists | ERT-1 design, comment 1 |
| A lapsed statutory certificate always blocks; a reminder never relaxes a block or a deadline | `ELA-001`; `NTF-001`, "Delivery failure" |
| Migration slot `20260908_0046` | The owner's working terms for this package, 30 September 2026 |

### 1.5 At the owner's screen check (1 October 2026)

All eleven steps pass ("Everything passes, including 3 and 11"). The owner raised three points:

| Point | The owner's decision |
| --- | --- |
| Step 3 listed fitness and a permit as "not yet recorded" for a machine with nothing recorded. "If a registration is not recorded, the assumption should be that it is a non-transport crane and if there is a registration then it is a transport crane and as soon as registration is entered, these two certificates get activated for that crane." | **Adopted, in this package, with one review round** ("1 now with one review round"). With no registration recorded, a machine is not a transport vehicle; fitness and a permit are needed once a registration saying transport is entered. This replaces ELG-1's cautious reading (ELG-1 design, section 6, step 2): the registration is itself required, and a missing one is reminded and blocks on its own, so the cautious reading only added two duplicate reminders per machine. A transport registration that has run out still says what the machine is, so fitness and a permit go on being reminded while it is renewed - unless the registration is then marked "not applicable" (refinement 12) |
| Why Management (Read Only) has "Mark as seen" | **Kept** ("3 keep"). ELG-1 Q17: anyone a reminder reaches may mark it seen. It is the person's own note - it changes no business record and never stops reminders or escalation - quieting the reminder for them and showing the others, "Seen by <name>", that the escalation was read |
| Step 11: from Alerts, the allocation's page went back to Allocations | **Corrected**: every page a reminder links to offers "Back to Alerts", to the list as it was (refinement 13) |

**The owner's re-check, 2 October 2026: "all pass"** - CW4's six papers with no fitness or permit, on Alerts and
Certificates due; Back to Alerts keeping the search; a reminder marked seen staying in place until Refresh. The owner
asked that a filter's share be shown - "something like 6/45 and when marked as seen and refreshed, 5/44" - now, if a
small change, else with the UAT team's changes. Small, and done now (refinement 14).

---

## 2. What the sources say

Each source is read against the later decisions that refine it (ADR-013).

- **`FUTURE_SLICES.md`, "ELG-2"** records the agreed scope: the three reminders, configurable schedules and paths,
  "seen" never stopping escalation, Admin's settings screen, the Alerts page and count, and two new records. It
  says: "worked out when read, so no job runner is needed for the screen".
- **ELG-1, section 19** is the draft this design completes. Section 13 lists where this design refines it.
- **`ELA-001`** (APPROVED), "Continuous validity monitoring":
  - eligibility is not a one-time check;
  - alerts go at 60, 30 and 15 days before expiry, "plus the operational owner where assignment is affected";
  - a statutory lapse has no override;
  - a recheck job, and the events `EligibilityExpiring`, `EligibilityLapsed` and `EligibilityRestored`, need the
    job runner.

  The 60/30/15 days are PBL's policy, not law (ELG-1, section 2, C). The standard schedule keeps them.
- **`NTF-001`** (APPROVED, not built):
  - "The originating business module owns why a notification is required, its business record, audience rule and
    due time." So the reminders, their schedules and their paths are Eligibility's.
  - Notifications owns channel delivery. Until it exists, the screen is the only channel (section 13, row 8).
  - Never the same notification twice "for the same type, source version, recipient and scheduled occurrence". Each
    reminder here has an occurrence date for that reason.
  - A failed notification "does not silently change or relax the underlying deadline, statutory block". Here the
    reminders only inform. The block is ELG-1's decision, read afresh by 8A.
- **`ORA-001`** (APPROVED, not live): positions and business authorities come from the Employee Master. Roles are a
  "transitional access grouping". So a path names roles as **data** in its settings, never in the code, and names
  authorities once positions are live.
- **8A core** (`8a-core-equipment-allocation.md`, sections 6.4, 6.10 and 17; `resource-assignment-api-contract.md`):
  - every held allocation shows "today's answer", worked out for its site and days, and a compliance state of
    `CLEAR`, `WARNING`, `BLOCKED` or `SITE_UNKNOWN`;
  - each piece of kit on a Trip (Own Load) is judged on its own, over the trip's day to the allocation's end;
  - a blocked allocation stays held until it is renewed, replaced or freed, and is never freed automatically;
  - its Q2 answer says warnings "stay on the allocation until they are dealt with, and ELG-2 will remind people about
    them".
- **`RPA-001`** (APPROVED): an assignment whose compliance lapses needs an explicit release or replacement. The
  reminders point Operations to it.
- **`MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`**: the Notifications row says the originating module owns the audience
  trigger and the business meaning; the Background Jobs row says job execution is not business state.

---

## 3. Authority and required reading

Per PBL's internal working instructions, "Reading discipline". Each was read in full unless a section is named.

- **The agreed design:** `docs/agent/slices/elg-1-machine-eligibility.md` - sections 1.1, 1.3 (Q14 to Q18), 1.4, 6,
  7, 13, 14, 19 and 20.
- **8A core:** `docs/agent/slices/8a-core-equipment-allocation.md` - sections 1, 6, 12 and 17.
- **Contracts:**
  - `eligibility-api-contract.md`, in full;
  - `eligibility-assignment-contract.md` (`ELA-001`), in full;
  - `resource-assignment-api-contract.md`, in full;
  - `notification-delivery-contract.md` (`NTF-001`), in full;
  - `organization-authority-authorization-contract.md` (`ORA-001`), in full.
- **Registry and architecture:**
  - `CONTRACT_REGISTRY.md`: the `ELA-001`, `RPA-001` and `NTF-001` rows;
  - `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`: the Compliance / Eligibility, Notifications and Background Jobs rows.
- **Backlog:**
  - `FUTURE_SLICES.md`: "ELG-2", "Hiring user test", "8B";
  - `DEFERRED_REQUIREMENTS.md`: the 8A and "Statutory requirements found with ERT-2" entries naming ELG-2.
- **Decisions:**
  - ADR-013 (source guidance is directional);
  - ADR-017 (module-owned data; the port);
  - ADR-019 (the job queue, not built);
  - ADR-023 (settled points are applied, not asked again).
- **Continuity:** `docs/continuity/NEXT_STEPS.md`, the updates of 27 to 30 September 2026.
- **Code:**
  - `eligibility/`: `contract.py`, `service.py` (the check, `record_decision`, Certificates due), `evaluation.py`
    (`evaluate`, `baseline_results`, `due_band`);
  - `resource_assignments/views.py` (`build_assignments`, `today_answer`, `site_facts`);
  - `resource_requirements/ports.py`, the port pattern reused;
  - `authorization/contract.py` (the six roles);
  - `frontend/src/layout/AppShell.tsx` and `pages/equipment/certificatesState.ts`;
  - the seed users' roles (`20260629_0002_auth_seed_users.py`).

---

## 4. What it builds

1. **The reminders** - three, and a fourth as recommended in Q19a - worked out when read, from ELG-1's judgement
   and 8A's allocations (section 5.1), each with its date and reason (section 5.2).
2. **Schedules**: when a reminder repeats, set for each kind of reminder (section 5.3).
3. **Paths**: whom a reminder reaches, and from when, set for each kind of reminder (section 5.4).
4. **"Seen" marks**, per person and per reminder day (section 5.5).
5. **Reminder settings**: Admin changes a schedule or a path as a new version (section 5.6). The standard ones of
   Q15 and Q16 come with the package.
6. **Alerts**: a count in the menu, and a page listing what has reached you (section 6).

---

## 5. The rules, step by step

"Today" is the day in Asia/Kolkata, as everywhere in Eligibility.

### 5.1 What raises a reminder

| Reminder (code) | Raised for | Ends when |
| --- | --- | --- |
| **A certificate running out** (`CERTIFICATE_RUNNING_OUT`) | every active machine and piece of kit, for every certificate the baseline rules require of it today, whose cover has run out or ends within the schedule's reach; every "not applicable" mark ending that soon, or ended or withdrawn with nothing recorded since; and a renewal recorded without its copy. A crane's papers on its carrier count, as on Certificates due | a certificate with its copy covers past the schedule's reach; or a mark applies; or the asset is retired |
| **A certificate not yet recorded** (`NOT_YET_RECORDED`, Q19a) | every active machine and piece of kit, for every certificate the baseline rules require of it today, that has not been recorded with its copy since it became needed - since the machine was added to the Equipment Master, or the rule requiring it took effect (section 5.2) | it is recorded with its copy; or a mark is recorded, where the rule allows one; or the asset is retired |
| **Runs out before the job starts** (`BEFORE_JOB_STARTS`) | a machine held on an allocation that has not started, or a piece of kit listed on one of its Trips (Own Load), whose cover ends before the first day - the allocation's, or for a piece its trip's day - judged for the allocation's site and days, exactly as the allocation's "today's answer" is. A certificate already run out, missing or without its copy counts too | the cover reaches the first day; or the allocation is freed or replaced, or the piece removed; or the first day comes - then a cover still short is a reminder of the next kind |
| **Runs out during the job** (`DURING_JOB`) | the same machines and pieces, whose cover ends on or after the first day and before the last day, or at any time when the allocation has no last day; and, once the job has started, a certificate that has run out, is missing or has no copy | the cover reaches the last day; or the allocation is freed or replaced, or the piece removed; or the last day passes |

- **The first two together are what Certificates due lists**, split by why the certificate is short: papers never
  entered since they became needed, or a cover that has ended or is ending.
- **Which allocations.** Held allocations whose last day has not passed, and the pieces listed on their trips. A
  replaced or freed allocation raises nothing: its stored decision stands as the record (8A, section 6.4).
- **Engineering: from the check's outcomes.** Each allocation reminder comes from one result of the check:

  | Outcome | Reminder |
  | --- | --- |
  | `RUNS_OUT_BEFORE_START` | before the job starts |
  | `RUNS_OUT_IN_PERIOD` | during the job |
  | `RUN_OUT`, `MISSING`, `COPY_MISSING` | before the job starts if the first day (a piece's: its trip's day) is after today; otherwise during the job |
  | `RUNS_OUT_SOON`, `VALID`, `NOT_APPLICABLE` | none: the job is over before the cover ends, and the first reminder covers the machine |
  | `RETIRED` | none: 8A's allocation shows it, blocked |

  A "not applicable" mark ending before or during the job gives the same outcomes as a cover, as the check already
  does (ELG-1 refinement, round 3).
- **One certificate can raise several reminders.** For example: one on the renewal list, and one for each job it
  affects. Each shows what it is about.
- **An allocation whose site cannot be judged** - 8A's `SITE_UNKNOWN` - raises no allocation reminder. 8A's own page
  already says what to put right. The first reminder still covers the machine, by the baseline rules.

### 5.2 A reminder's date

Every reminder is about one date, with its reason (the owner, 1 October 2026). The schedule counts from that date,
and the screen shows both.

| What is found | Its date | The reason shown, for example |
| --- | --- | --- |
| A cover running out, or run out | the day the cover ends | "Insurance runs out on 30 November 2026" |
| A "not applicable" mark ending, or ended with nothing recorded since | the mark's last day | "Not applicable until 30 November 2026; needed after that" |
| A mark withdrawn, with nothing recorded since | the day it was withdrawn | "Needed since the 'not applicable' mark was withdrawn on 2 October 2026" |

A mark ended or withdrawn dates the certificate only if it stood for this requirement: the rule in force on its last
day allowed marks, and the mark kept within that rule's limit on how long - as the check counts a mark. A mark under
the baseline never covered a job in a state whose rule allows none (independent review, round 3).
| A certificate recorded without its copy - in force, or a renewal recorded ahead | the day the cover before it ends, as for a certificate running out (with none before it, the day before it takes over): a renewal without its copy changes the reason, not the date, so it stays the same reminder; and where the one before it was also without its copy, the day the last one with its copy stopped covering - further certificates without their copies leave the date as it was (independent review, rounds 1, 2 and 4) | "Insurance: covered until 30 September 2026; the certificate taking over after it has no copy attached" |
| Never recorded, on a machine added to the Equipment Master | the day the machine was added | "Missing since 3 October 2026 - machine added to the Equipment Master" |
| Never recorded, because a rule requires it | the day the rule took effect - which may be before the day the rule was entered | "Missing since 1 November 2026 - required by a rule from that day" |
| Never recorded: fitness or a permit, because the registration says transport | the day that registration took effect | "Missing since 5 October 2026 - registered as a transport vehicle" |

- **Several reasons at once.** The latest date wins: it is the reason the certificate is needed now. For example, a
  certificate recorded without its copy on a machine just added: its "valid from" is usually earlier than the day
  the machine was added, so the reason is the machine being added.
- **Which reminder.** The last three rows - papers never entered since they became needed - are **"A certificate
  not yet recorded"** (Q19a). The others are **"A certificate running out"**. When reasons of both fall on the same
  day, "A certificate running out" wins: it is the cautious one, as its path reaches more people sooner.
- **A mark that ends keeps its reminder.** Before its end, a mark ending is reminded with the mark's last day as its
  date. After it, the same date and the same reminder carry on. So nobody it has reached drops off.
- **Allocation reminders** take their dates the same way. Which of the two they are follows section 5.1.
- **When the reminder began.** A reminder cannot have been raised before the thing it is about existed:
  - the first reminder begins on the day the machine or piece was brought into the platform;
  - an allocation reminder begins on the day the allocation, or the kit line, was recorded.

  Reminder days before that are not counted.

### 5.3 The schedule, and the reminder days

A schedule is a list of **bands**. Each band says: "from N days before the date, every M days". A negative N means
after the date. Each band runs until the next band starts. The last band runs on for as long as the reminder lasts.

The standard schedule (Q15):

| From | Every | Reminder days it gives |
| --- | --- | --- |
| 60 days before | 30 days | 60 and 30 days before |
| 15 days before | 7 days | 15 and 8 days before |
| 7 days before | 1 day | 7, 6, 5, 4, 3, 2 and 1 day before |
| the day itself (0) | 1 day | the day it runs out, and every day after |

"A certificate not yet recorded" has its own standard schedule (Q19a): every day, from the day it became needed. Its
date is never ahead of today, so reminders before the date do not arise.

**The reminder's days** are those days, from the day the reminder began.

- **Flagged at once.** If the reminder began inside the schedule's reach - a machine allocated 20 days before its
  insurance runs out, say - the day it began is also a reminder day. This is the "flag" the owner asked for when a
  machine is allocated (ELG-1, Q15). It adds to the warning 8A already shows when allocating.
- **The current reminder day** is the latest reminder day up to today. A reminder is **shown** from its first
  reminder day, until it ends (section 5.1).

**Example.** A crane's insurance runs out on 30 November:

- Its first reminder comes on 1 October (60 days before), then on 31 October, 15 November and 22 November, then
  every day from 23 November, on 30 November itself, and every day after, until a renewal is recorded with its copy.
- The crane is allocated on 10 November to a job from 1 to 31 December. The reminder "runs out before the job
  starts" begins on 10 November - a reminder day, flagged at once - and then follows the same days from 15
  November.

### 5.4 The path: whom a reminder reaches, and from when

A path is an ordered list of **steps**. Each step adds one audience. Nobody drops off.

```text
role       one of the platform's roles: Admin (the Fleet Admin, until that role exists), Operations, Management,
           Sales User, Sales Manager, Finance. Later, an ORA-001 authority, once positions are live.
from       the first reminder; or N days before the date (a negative N means after it)
channels   Screen, for now; email, SMS or a messaging channel once integrated (NTF-001)
```

- A step **has reached** its audience from the later of the reminder's first shown day and "N days before the
  date".
- A person sees a reminder when **any** of their roles is on a step that has reached them.

The standard paths (Q16; the fourth column as recommended in Q19a):

| Step | A certificate running out | Before the job starts / During the job | A certificate not yet recorded |
| --- | --- | --- | --- |
| 1 | Admin (the Fleet Admin), from the first reminder | Admin (the Fleet Admin), from the first reminder | Admin (the Fleet Admin), from the first reminder - the day it became needed |
| 2 | Operations, from 15 days before | Operations, from the first reminder - the allocation, when it was allocated inside the schedule | Operations, from 7 days after |
| 3 | Management, from 7 days before | Management, from 7 days before | Management, from 14 days after |

All on screen. A certificate missing on a machine that is on a job is an allocation reminder, so Operations sees it
from the first reminder whatever its reason.

**A reminder that becomes another kind** - "runs out before the job starts" becoming "runs out during the job" as the
job starts (section 5.1) - follows the new kind's path from then. The standard paths of the two are the same, so nobody
drops off; where Admin sets them differently, each kind's own path applies, as Admin set it.

### 5.5 Seen

- **Per person, per reminder, per reminder day** (Q17). Marking a reminder as seen quiets it for you until its next
  reminder day. On that day it is unseen again.
- **It changes nothing else.** The reminders go on, the path goes on reaching more people, and the certificate's
  state is what it was.
- **Only the current reminder day** may be marked, and only by someone the reminder has reached. Marking it twice
  changes nothing the second time.
- **Several at once.** "Mark all shown as seen" marks every reminder on the page. It is all or none: if any has moved
  on since the page was read - a new day, or a renewal recorded - nothing is marked, and the page reads the list
  again.
- **Who has seen it**, with when, is shown to everyone the reminder has reached, for its current reminder day.

### 5.6 Settings

There is one setting for each kind of reminder. It holds a schedule and a path. Admin changes a setting under
`ELIGIBILITY_RULE_MANAGE` (Q18).

- **A change is saved as a new version.** Nothing is edited. The version records who saved it and when.
- **It applies at once** to every reminder, including the reminder days counted so far and whom each reminder has
  reached, since reminders are worked out when read (Q18: "each change applies from the moment it is saved"). "Nobody
  drops off" (section 5.4) is about one path as the days pass; a path Admin changes - a role taken off, a step moved
  later, a schedule starting later - applies as changed.
- **Saving the same as the current version** records nothing.
- **A version saved by someone else** since the page was opened is refused (`409`), and the page reads the setting
  again.

**A setting is refused** (`422`, with the reason beside **Save**) when:

- the schedule has no band, or more than ten;
- a band starts more than 365 days before or after the date, or repeats less often than every day or more than
  every 365 days;
- two bands start on the same day;
- no band covers the date itself and after (the last band must start on the date or after it). An overdue
  certificate is never left without reminders: "until someone deals with it" (Q15);
- the path has no step, or more than ten;
- a role is unknown, inactive, or on two steps;
- the first step does not start at the first reminder, so the first reminder would reach nobody;
- a step starts before the schedule's first band;
- a step has no channel, or a channel other than Screen.

The steps' order in the list is the order they are shown; each step's own "from" decides when it reaches its
audience.

### 5.7 Worked out when read

Nothing is stored about a reminder except its "seen" marks. Each read of the Alerts page, or of the count, works
them out afresh:

1. It reads the current settings, one for each kind of reminder.
2. It reads the evidence **once** for every asset, as Certificates due does: every active asset with its fitted
   parts, and every certificate, mark and rule.
3. It reads the held allocations and their listed kit through the port (section 9).
4. It judges each allocation and piece for its site and days, against that one reading of the evidence.
5. It reads the "seen" marks of the reminders' current reminder days.

**The cost** grows with the fleet. The build measures a read at the size of Plum's report (681 machines) with kit,
and records it. If that is too slow for the menu count, it comes back to the owner (section 12).

---

## 6. Screens

Messages sit beside the button that caused them. Styling uses `globals.css` classes only. A page with no session
says `SIGN_IN_FIRST`, a refused one `SIGN_IN_AGAIN`. Loading goes through the tested pure controllers of ELG-1 and 8A,
in which only the latest answer is shown and a session change resets the page.

1. **The menu** gains **Alerts**, just below Dashboard, for everyone. Beside it, the count of reminders that have
   reached you and that you have not seen. When the menu is hidden, the **Menu** button carries the count.
   - The count is read when a page loads, at most every five minutes. It is kept in the browser's session storage,
     with who it is for.
   - It is read at once after you mark something as seen, and when you sign in as someone else.
2. **Alerts** (`/alerts`).
   - **Filters:** the kind of reminder; "only those I have not seen" (on at first); a search by machine number,
     reference, piece number, Work Order or allocation.
   - **Order:** most urgent first - by date, the earliest first, so what has run out or has long been missing comes
     before what is still to run out.
   - **Each reminder shows:**
     - the machine or piece (linked), the certificate, and "on its carrier EQ-000124" where it is recorded there;
     - what it means, with its date and reason (section 5.2). For example: "Insurance runs out on 5 October 2026,
       before the job at Dahej, Gujarat starts on 20 October (Work Order WO-000012, allocation AL-000031)", or "Load
       test missing since 3 October 2026 - machine added to the Equipment Master";
     - "Reminded 4 times since 5 August";
     - who it has reached, with from when: "Admin from 5 August; Operations from 20 September";
     - who has seen it, and when;
     - **Mark as seen**, or "Seen by you today".
   - **Mark all shown as seen**, beside the list.
   - A line at the top: "Reminders are shown here only. Email and SMS will come when they are connected." With
     links to Certificates due and Reminder settings.
   - With nothing for you: "No reminder has reached you." The page names the roles the current paths reach.
3. **Reminder settings** (`/equipment/alert-settings`), linked from the Equipment pages' header beside Certificates
   due and Certificate rules, and from Alerts.
   - **One section for each kind of reminder.**
     - Its schedule: one row per band - "From [60] days [before] the date, every [30] days" - with **Add a band** and
       **Remove**.
     - A preview in words: "Reminders on 60, 30, 15, 8, 7, 6, 5, 4, 3, 2 and 1 day before, on the day, and every day
       after."
     - Its path: one row per step - the role, "from the first reminder" or "from [N] days [before] the date", and the
       channels. Screen is ticked; email and SMS are shown as "not yet available".
     - **Save**, with its message beside it.
     - Its versions: "Version 2, saved by <name> on 1 October 2026 at 14:05"; "Version 1, loaded with the package".
   - For everyone but Admin, the page only reads.

**A screen check fits in twenty minutes**, on a seeded crane whose papers run out in 20, 10 and 5 days, one already
run out, a crane added today with its insurance not yet entered, and a held allocation with a machine and a sling:

1. As `admin1`, open **Alerts**: all the seeded reminders are there, with the count in the menu. The new crane's
   reads "Insurance missing since <today> - machine added to the Equipment Master".
2. Mark one as seen: it says "Seen by you" where it is, with "Marked as seen." beside it, and the count drops by one;
   read again (Refresh), it leaves the list. Show all: it is there, "Seen by you" (refinement 11).
3. As `ops1`: the 10-day, 5-day and run-out ones, and the allocation's. Not the 20-day one, and not the new crane's
   (Operations from 7 days after).
4. As `readonly1` (Management): the 5-day and run-out ones, and the machine's insurance on the allocation (6 days).
   Not the sling (25 days), and not the new crane's. Admin's "seen" is shown on the one Admin marked.
5. As `admin1`, record the renewal of the 5-day certificate, with its copy: its reminders are gone.
6. On **Reminder settings**, move Operations to "from 25 days before" for "A certificate running out", and save:
   version 2, with your name. As `ops1`, the 20-day reminder is now there.
7. Try to save a schedule whose last band ends before the date: refused, with the reason beside **Save**.
8. As `ops1`, the settings only read.
9. Free the allocation: its reminders are gone.

---

## 7. Permissions

No new permission.

| Permission | Granted to | Allows |
| --- | --- | --- |
| `EQUIPMENT_REFERENCE_READ` (exists) | the six roles | reading the Alerts that have reached you, and the count; marking them as seen; reading the Reminder settings |
| `RESOURCE_ASSIGNMENT_READ` (exists) | the six roles | also needed to be shown the two allocation reminders, which name Work Orders and allocations |
| `ELIGIBILITY_RULE_MANAGE` (exists) | Admin | saving a new version of a setting (Q18) |

**Marking as seen is under a read permission** on purpose. It writes only the person's own mark. It changes no
business record, so it is not a write to what the permission guards. The service allows it only on a reminder that
has reached the person (section 5.5).

Alerts never carry a certificate's number, issuer or reason, or a mark's reason. So `EQUIPMENT_IDENTITY_READ` does not
come into it.

---

## 8. Routes

Under `/api/eligibility`, each pinned in `POST_BASELINE_NEW_ROUTES`. The contract's new section states exactly what
they accept, return and refuse.

```text
GET  /alerts?reminder_kind_code&unseen_only&search&limit&offset                       READ         200
GET  /alerts/count                                                                   READ         200
POST /alerts/seen            {items: [{reminder_key, reminder_on}]}   1 to 200        READ         200
GET  /alert-settings                                                                 READ         200
POST /alert-settings/{reminder_kind_code}  {expected_version, bands[], steps[]}       RULE_MANAGE  201
```

- **`GET /alerts`** answers with:
  - `today`;
  - the counts, as a whole and for each kind of reminder, before the filters;
  - `total`, `limit` (1 to 500, default 100) and `offset`;
  - `items[]`, one per reminder that has reached the caller. Each item has:
    - `reminder_key` (its identity: the kind of reminder, what it is about, the asset, the certificate kind and the
      date);
    - `reminder_kind_code`;
    - the asset, and the asset the certificate is recorded on;
    - the certificate kind, the outcome, the date and its reason code (section 5.2), and the mark where one is
      concerned;
    - for an allocation reminder: the allocation (public id, reference), the Work Order (public id, code), the line,
      the unit, the site, the days, and for kit the trip and the kit line;
    - `began_on`, `first_reminder_on`, `reminder_on` (the current reminder day), and `reminders_so_far`;
    - `reached[]`: each step that has reached its audience - the role, and from when;
    - `seen_by_me`, and `seen_by[]` - name and time - for the current reminder day.
- **`GET /alerts/count`**: `{unseen, total}` for the caller.
- **`POST /alerts/seen`** is refused:
  - `404` when a reminder is not one that has reached the caller today;
  - `409` when its current reminder day is no longer the one sent ("This reminder has moved on. Read the list
    again."). Nothing is then marked.

  A reminder already marked changes nothing. The answer says how many were marked.
- **`GET /alert-settings`**: for each kind of reminder, its current version - bands, steps, who saved it and when -
  and the earlier versions, newest first.
- **`POST /alert-settings/{reminder_kind_code}`**: `201` with the new version and its event; `200` with
  `unchanged: true` and no event when it equals the current one. `404` for an unknown kind. `409` when
  `expected_version` is not the current one. `422` for each refusal of section 5.6. Unknown fields are refused
  (`422`).

Errors are `{"detail": "..."}` in plain words, as everywhere in Eligibility.

---

## 9. Events

The record type is `eligibility_alert_setting`, the source module `eligibility`.

| Event | Payload |
| --- | --- |
| `ELIGIBILITY_ALERT_SETTING_CHANGED` | the kind of reminder; the version before and after; the new version's bands (from, every) and steps (role, from, channels) as codes and numbers |

- **Marking as seen records no business event** (ELG-1, section 19.6). The mark is itself the record of who saw
  what, and when.
- **A reminder records no event.** Reading must not write, and nothing schedules a reminder yet. `EligibilityExpiring`,
  `EligibilityLapsed` and `EligibilityRestored` wait for the job runner (section 11).

---

## 10. Data, module and migration

**Module** `backend/app/modules/eligibility/` gains:

```text
reminders.py   pure, with no database and no clock, as evaluation.py is:
               - the reminder days a schedule gives (60, 30, 15, 8, 7 ... 1, 0, -1 ...);
               - the current reminder day, and how many so far, from the day a reminder began;
               - the steps that have reached their audience, and from when;
               - a short certificate's date and reason (section 5.2);
               - which reminder an outcome raises (section 5.1);
               - the refusals of section 5.6
ports.py       AllocationSource: what Eligibility asks of Resource Assignments (below)
alerts.py      the Alerts list and count, marking as seen, the settings - the routes' service functions
contract.py    the reminder kinds, step starts, channels, limits, the event
repository.py, schemas.py, routes.py    additions
service.py     one public read shared with Certificates due: the baseline results of every active asset, out
               to a given reach. Certificates due returns exactly what it returns today (a test pins it).
               And one public read judging many units, each for its own site and days, against one reading of
               the evidence
```

**Two facts the dates need** (section 5.2), which the evidence ELG-1 loads does not yet carry: the day each asset was
added (its record's creation, in Asia/Kolkata - one more field on `AssetFacts`, the Equipment Reference's existing
read for Eligibility; its tables do not change),
and the day a "not applicable" mark was withdrawn (`withdrawn_at`, already on the mark). The decision itself does not
change: neither fact is read by `evaluate` or `baseline_results`.

`service.py` stays one file. `alerts.py` uses only its public functions. The split into `services/` waits until
`service.py` outgrows one file (CODING_STANDARDS.md).

**The port.** `ports.py` holds `AllocationSource`. Resource Assignments registers an implementation when it is
loaded, as it registers `AssignmentPort` with Resource Requirements. `app.main` always loads it. The smoke-data
harness loads it too (8A refinement 10). With none registered, reading the Alerts fails with a server error. It never
shows no allocation reminders merely because Resource Assignments was not loaded (fail closed).

```text
held_for_reminders(db, today) -> list of:
  requested_for_type       resource_assignment | resource_assignment_kit (as for record_decision)
  requested_for_public_id  the allocation's or the kit line's public id
  assignment public id and reference; Work Order public id and code; line number; unit; trip number (kit)
  asset_public_id          the machine, or the piece
  period_from, period_to   the allocation's first day and last day (empty: runs on); for kit, its line's days
  began_on                 the day the allocation or kit line was recorded, in Asia/Kolkata
  site                     state code, central-government answer, label - or its problem, as 8A's SiteFacts
```

It lists held allocations whose last day has not passed, and the listed kit lines of each with days left. It reads
only Resource Assignments' own tables and the site as 8A already reads it. It writes nothing and takes no lock.

**Migration `20260908_0046_certificate_reminders`**, parent `20260908_0045`. As migrations `0033` to `0045`, its
rows are spelled out, not imported, so the revision stays a frozen snapshot.

- **`eligibility_alert_setting`**: one version of one reminder kind's setting, never edited.
  - Columns: public id, reminder kind (CHECK: the four), version number (unique with the kind), saved by (a key to
    the user; empty for the versions loaded by the migration), saved at.
- **`eligibility_alert_band`**: the setting, band number, "from N days before" (-365 to 365), "every M days" (1 to
  365).
  - Unique: the band number, and the "from", within a setting.
- **`eligibility_alert_step`**: the setting, step number, role (a key to `role.role_code`), start (`FIRST_REMINDER`
  or `DAYS_BEFORE`), "from N days before" (given exactly with `DAYS_BEFORE`, -365 to 365), channels (not empty;
  `SCREEN` only, for now).
  - Unique: the step number, and the role, within a setting.
- **`eligibility_alert_acknowledgement`**: one person's "seen" of one reminder on one reminder day.
  - Columns: the reminder key, the reminder kind, the asset (a key to `equipment_asset.asset_public_id`), what it
    is about (`asset`, `resource_assignment` or `resource_assignment_kit`, and its public id - no key, as a stored
    decision's "requested for" has none), the certificate kind (a key), the reminder day, who (a key to the user)
    and when.
  - Unique: the reminder key, the reminder day and who.
- **The standard settings**: version 1 of each kind, with the schedule of Q15 and the paths of Q16, and for "A
  certificate not yet recorded" those recommended in Q19a.

The order across rows - bands in order, the last on or after the date, the first step from the first reminder - is
checked by the service, under the module's write lock, as rules are. Each row's own values are checked by the
database too. The downgrade drops the four tables. No other table changes.

**Smoke data.** The `equipment-allocation` scenario, and the core bundle's record set used by Playwright, gain their
own machines, so the allocation spec's machines are untouched:

- a crane whose certificates run out in 20, 10 and 5 days, and one run out 2 days ago;
- a crane added on the day of the run, with its insurance not yet entered;
- a held allocation starting in 12 days, whose machine's insurance runs out in 6 days - before the job starts - with
  a sling listed whose examination runs out in 25 days, during the job.

Cleanup removes the "seen" marks of the run's assets, allocations and kit lines, whoever made them, before the
assets. The harness never changes a setting.

---

## 11. Not in ELG-2

| Left out | Where it goes |
| --- | --- |
| Email, SMS and messaging | the notification service (`NTF-001`) with a provider; each step is then given its channels |
| A job raising reminders; the events `EligibilityExpiring`, `EligibilityRecheckScheduled`, `EligibilityLapsed`, `EligibilityRestored`; a recheck job | the job runner (ADR-019); `ELA-001` |
| Reaching people by position, region or site ("the Operations head for the site's region") | `ORA-001`, once positions are live |
| The people half: crew licences and operators' certificates | 8B, reusing these reminders with their own kinds |
| A note with "seen" | Q20: a deferred design, **needing PBL's confirmation before it is taken up** (owner, 1 October 2026; `DEFERRED_REQUIREMENTS.md`, "Certificate reminders: what ELG-2 leaves out") |
| Reminding ahead of a rule that starts on a later day, for a machine not on a job | later, if wanted. A machine on a job is reminded already: its check takes the rule in effect when the job starts, and the date counts from the rule's start |
| Snoozing a reminder, or giving it to one person to deal with | later, if the testers ask |
| The platform's other reminders: contract expiry at 30 days, offer review, credit profile review (`NTF-001`'s list) | their own modules. The Alerts page can gather them, and its count then adds them up |
| An allocation whose site cannot be judged | 8A shows it (`SITE_UNKNOWN`) and says what to put right |
| A retired machine still held on a job | 8A shows it, blocked |
| Reminders on the Dashboard | later |
| Stopping the reminders of a closed Work Order | when closing a Work Order is built; nothing closes one yet |

Resource Requirements, Work Orders, the Equipment Reference's tables, 8A's tables, ELG-1's tables, and the frozen
Slice 6D.1 handoff contract do not change.

---

## 12. What would stop implementation and come back to the owner

- An answer to Q19a other than as recommended. One path for all removes the fourth reminder (sections 5.1, 5.2 and
  5.4) but not the shape.
- A need for email or SMS before the notification service exists. That needs a provider, an external dependency.
- Working the reminders out when read proving too slow for the menu at the real fleet's size. Reminders would then
  have to be stored by a daily job (ADR-019), which is a different design.
- A need to reach people by position or region before `ORA-001` is live.

---

## 13. Differences from earlier records (recorded per ADR-013)

| # | Earlier record | ELG-2 | Why |
| --- | --- | --- | --- |
| 1 | ELG-1 19.1: the first reminder "is worked out from Certificates due" | The same baseline results, out to the schedule's reach rather than Certificates due's fixed 60 days | The schedule is configurable (Q15): a first reminder at 90 days would otherwise never come before 60. Certificates due is unchanged |
| 2 | ELG-1 19.1: a missing certificate's date is "today" | Its date is the day it became needed, with the reason: the machine added, the rule taking effect, the registration saying transport, a mark ending or withdrawn, a renewal without its copy taking over (section 5.2). Papers never entered since they became needed are their own reminder, "A certificate not yet recorded" (Q19a) | The owner, 1 October 2026: the date can be known from why the certificate is needed now. A date of "today" would begin again every day. The first proposal - no date, shown to everyone at once - is replaced (section 1.0) |
| 3 | ELG-1 19.2: raised "on the day the machine is allocated" | On the day the allocation, or the kit line, was recorded. The first reminder begins the day the asset was brought in. Reminder days before a reminder began are not counted | A reminder cannot have been raised before what it is about existed. A change of dates does not flag again: the reminder appears on its schedule |
| 4 | ELG-1 19.1: the allocation reminders cover a cover "ending" before the start or during the job | Also a certificate run out, missing or without its copy on an allocated machine: before the start if the job has not started, otherwise during it | Every blocking lapse on a job reaches Operations: `RPA-001` asks for an explicit release or replacement |
| 5 | ELG-1 19.4: "Acknowledge" | The screens say **Mark as seen**; the table keeps its agreed name, `eligibility_alert_acknowledgement` | Plain words (AGENTS.md, "PBL review and approval language") |
| 6 | ELG-1 19.4: the count is "the reminders due today ... not acknowledged" | The reminders that have reached you whose current reminder day you have not marked, whichever day it was | A reminder raised on a day you did not open the platform stays until you see it |
| 7 | Q15: "daily after it has run out, until someone deals with it" | Every schedule must have a band from the date onwards | An overdue certificate is never left without reminders |
| 8 | `NTF-001`: Notifications owns channel delivery | The Alerts page is Eligibility's own list of what is due and for whom, like Certificates due. "Seen" marks are not delivery records | Notifications does not exist. When it is built, it can take over the screen channel; the reminders, schedules and paths stay Eligibility's, as the originating module's |
| 9 | `ELA-001`: alerts go "to the employee and HR manager, plus the operational owner where assignment is affected" | For machines: the Fleet Admin, Operations and Management, by role | The employee and the HR manager are the people half (8B). Roles now, authorities later (Q16) |
| 10 | `ELA-001`: `EligibilityExpiring` and `EligibilityRecheckScheduled` | Not recorded | Nothing schedules a reminder, and a read must not write. They need the job runner |
| 11 | ELG-1 19.6: "Reading and acknowledging: anyone the reminder has reached, with `EQUIPMENT_REFERENCE_READ`" | The allocation reminders also need `RESOURCE_ASSIGNMENT_READ` | They name Work Orders and allocations, which that permission guards. Today both are granted to the same six roles |
| 12 | ELG-1 19.6: `eligibility_alert_setting` "holding its bands and its steps" | A version row, with its bands and steps in rows of their own | So the database checks each value |
| 13 | ELG-1 19.1 and `FUTURE_SLICES.md`: three reminders | Four, the fourth "A certificate not yet recorded" (Q19a, as recommended) | So papers not yet entered for a machine just added reach the Fleet Admin first, while a lapse still reaches everyone on its path |

---

## 14. Tests and checks

- **The pure rules** (`reminders.py`):
  - the standard schedule gives 60, 30, 15, 8, 7 to 1, 0 and every day after; other schedules, including a weekly
    last band and one starting after the date;
  - the current reminder day and the count so far: before the first, on it, between two, long after;
  - a reminder beginning inside the schedule: its first day is a reminder day, and earlier days are not counted;
  - the steps reached: from the first reminder, from N days before, from N days after;
  - each date and reason of section 5.2; the latest winning; "running out" winning a tie; a rule taking effect
    before the day it was entered; a renewal's copy missing on an existing machine ("running out") and on a machine
    just added ("not yet recorded");
  - a mark ending keeping the same reminder before and after its end, so nobody drops off;
  - each outcome's reminder (section 5.1), before and after the first day;
  - every refusal of section 5.6.
- **The Alerts, by the service and the route:**
  - each of the four reminders raised, and each ending: a renewal with its copy; a renewal without its copy
    (still raised); a mark; retiring; freeing; replacing; removing a piece; the job ending;
  - a machine added today with papers not entered: Admin only, then Operations after 7 days and Management after 14;
  - a carrier's papers raising the crane's reminder;
  - a kit line judged over its own days;
  - a site that cannot be judged raising no allocation reminder;
  - the port not registered failing closed;
  - what each role sees with the standard paths - Admin, Operations, Management - and Sales and Finance seeing
    nothing;
  - the allocation reminders withheld from a role without `RESOURCE_ASSIGNMENT_READ` (granted in the test only);
  - the filters, the search, the order, the counts, paging;
  - no certificate number, issuer or reason in any answer;
  - Certificates due returning exactly what it returns today.
- **Seen:** marking; twice with one effect; a reminder that has not reached the caller (`404`); one that has moved on
  (`409`, nothing marked); several at once, all or none; the next reminder day unseen again; who has seen it; no
  business event.
- **Settings:** saving a version; the event and its payload; the same again changing nothing; a stale version
  (`409`); each refusal (`422`), by the service and, where it is a row's own value, by the database; refused without
  `ELIGIBILITY_RULE_MANAGE`; a new version applying at once; the standard versions loaded.
- **Migration:** from the empty database to the single head; downgrade, then upgrade again.
- **Time:** a read of the Alerts at the size of Plum's report (681 machines) with kit, measured and recorded.
- **Frontend:** pure state for the Alerts (the list, marking as seen, the count's five minutes and its reset) and the
  settings (the form's rules, as the server's, and the preview in words), each tested with answers late and out of
  order; the route-table tests for the two URLs; typecheck, tests, build.
- **Smoke data and cleanup:** the seeded reminders; cleanup removing the "seen" marks with the run, and refusing,
  deleting nothing, where it already refuses.
- **E2E** (`equipment-alerts.spec.ts`, with `pwsh`): Operations sees what reached Operations and not the rest,
  marks one as seen and sees the count drop; Management sees less; the settings only read for Operations.
  **Playwright never saves a setting.** A setting is never edited or deleted by design, so a saved version would
  stay in the shared database. The backend tests and the owner's screen check cover saving.
- **Full gate:** the full backend regression, one suite at a time; the frontend gate; the full E2E suite; the
  migration from empty and back; `check_tracked_secrets.py` and `validate_contract_fixtures.py`; the frozen handoff
  contract's hash before and after; independent review, up to three rounds; the owner's screen check, with the steps
  in the chat.

---

## 15. Shared files this package touches

- `backend/app/modules/eligibility/`: the new files and additions of section 10.
- `backend/app/modules/resource_assignments/views.py` and `service.py`: the port's read, and its registration.
- `backend/tests/fixtures/post_baseline_tightened_routes.py`: the five routes. Read it by eye after any merge.
- `frontend/src/routes.tsx` and its tests: two URLs.
- `frontend/src/layout/AppShell.tsx`: Alerts and its count.
- `frontend/src/pages/alerts/` (new), `frontend/src/pages/equipment/` (the settings page, and the header link),
  `frontend/src/styles/globals.css` (the count).
- `backend/tooling/smoke_data/`, `e2e/`, and `scripts/run-e2e.ps1` if a new sign-in is needed there.

`backend/app/main.py` and `authorization/contract.py` do not change: the routes join Eligibility's router, and no
permission is new.

**Documents updated when it is built:**

- `eligibility-api-contract.md` (a section on the reminders) and `resource-assignment-api-contract.md` (the port);
- `CONTRACT_REGISTRY.md` (the `ELA-001` note: the reminders are built on screen; maturity stays the reviewer's);
- the Compliance / Eligibility row of `MODULE_BOUNDARY_OWNERSHIP_MATRIX.md`;
- this design's implementation record, and an acceptance record;
- `FUTURE_SLICES.md`, `DEFERRED_REQUIREMENTS.md`, `NEXT_STEPS.md`, and a continuity note.

---

## 16. Implementation record (1 October 2026)

Built on `hiring/elg-2-certificate-reminders` in worktree `<a separate worktree>`, from the design commits and
`main` at `82acebd`, on the owner's answers of 1 October 2026 (section 1.0). Migration `20260908_0046`, parent
`20260908_0045`. Sections 4 to 10 are built; section 11 lists what is not.

### What exists now

```text
backend/alembic/versions/20260908_0046_certificate_reminders.py
        eligibility_alert_setting, eligibility_alert_band, eligibility_alert_step, eligibility_alert_acknowledgement;
        version 1 of each of the four kinds (Q15, Q16, Q19a)
backend/app/modules/eligibility/
        reminders.py (pure), alerts.py, ports.py (new); contract.py, schemas.py, repository.py, routes.py (five
        routes); service.py: the fleet read once (read_fleet, baseline_of, judge_in_fleet, member_assets, added_on,
        asset_summary, kind_label), which Certificates due now uses; evaluation.py: a mark's withdrawal day
backend/app/modules/equipment_reference/service.py, repository.py   AssetFacts.added_on
backend/app/modules/resource_assignments/views.py, service.py, repository.py
        held_for_reminders, registered as eligibility.ports.AllocationSource
backend/tests/fixtures/post_baseline_tightened_routes.py    the five routes
backend/tests/test_elg2_reminder_rules.py, test_elg2_certificate_reminders_api.py, test_elg2_smoke_data.py;
        eligibility_test_support.py removes the new rows; the harness tests count ELG-2's seeds
backend/tooling/smoke_data/   two 80 t crawlers and a sling (equipment_reminders), the record set reminder_target
                              (a held allocation with the sling on its trip), builders allocate_machine and
                              list_kit_on_trip; cleanup removes every "seen" mark on the run's assets, allocations and
                              kit lines
frontend/src/pages/alerts/AlertsPage.tsx, alertsState.ts (tested)          /alerts
frontend/src/pages/equipment/AlertSettingsPage.tsx, alertSettingsState.ts (tested)   /equipment/alert-settings
frontend/src/layout/AppShell.tsx (Alerts and its count), routes.tsx and its tests, EquipmentParts.tsx (the link),
        styles/globals.css (the count)
e2e/tests/equipment-alerts.spec.ts
docs: eligibility-api-contract.md ("Reminders and escalation"), resource-assignment-api-contract.md ("For
        Eligibility's reminders"), equipment-reference-api-contract.md (added_on), CONTRACT_REGISTRY.md (ELA-001
        note), MODULE_BOUNDARY_OWNERSHIP_MATRIX.md, FUTURE_SLICES.md, DEFERRED_REQUIREMENTS.md, TESTING_STRATEGY.md,
        NEXT_STEPS.md, the acceptance record and the continuity note
```

### Refinements made while building (recorded per ADR-013)

None changes an answer of the owner's.

| # | Design said | Built | Why |
| --- | --- | --- | --- |
| 1 | A missing certificate needed because "the rule requiring it took effect" is dated by that day | By the day the requirement began: the rule's start, or, where it took over from a rule of the same scope ending the day before, that rule's - walking back | A rule replaced by its successor - an interval changed - does not make every machine's paper newly needed. Without this, Operations and Management would drop off for 7 and 14 days: "nobody drops off" (section 5.4) |
| 2 | A mark "withdrawn" dates the reminder by the day it was withdrawn | By its last day if it ended before it was withdrawn | It stopped standing then |
| 3 | - | The day a mark was withdrawn joins the evidence the reminders read (`Mark.withdrawn_on`); the decision never reads it | The date needs it; ELG-1's answers are unchanged |
| 4 | Certificates due and the reminders "read the evidence once" | One public read, `service.read_fleet`, which Certificates due also uses; the allocations are judged against it by `judge_in_fleet`, the check `evaluate_asset` runs without reading again | DRY: one reading, one judgement. Certificates due returns what it returned (its ELG-1 tests pass unchanged) |
| 5 | A "seen" mark's key | The database also checks that the key begins with its kind, subject type and subject | A mark can never be stored against another reminder |
| 6 | Settings saved "the same as the current version" record nothing | `200` with `unchanged: true`; a new version is `201` | As the design's routes; bands given in any order are compared in order |
| 7 | The list "stays" while read again | Only while the same query is read again (`createShownQuery`, tested); another filter, page or session clears it at once | ELG-1's review round 2 and 8A's screen check together |
| 8 | Smoke data: "their own machines" | Two crawlers of an 80 t model, below the 200 t the allocation requirement asks for, so the allocation test never meets them; `reminder_target` in Gujarat | The allocation spec's candidates and coverage stay as they were |
| 9 | The count "read at most every five minutes" | Kept in the browser's session storage with the session's token; a count read for one session is never shown for another | As the sidebar's signed-in name (ELG-1 review round 5's rule) |
| 10 | A mark ended or withdrawn dates a certificate needed again | Only a mark that stood for the requirement: the rule in force on its last day - the result's rule or one it took over from - allowed it, within its limit on how long (`evaluation.allows_mark`, which the check's `counted_mark` now uses too). Where a later rule stopped a mark standing before it ended, the date falls back to the requirement's start or the machine added - earlier, the cautious side | Independent review, ELG2-R3-002: a mark that never covered the requirement is not why it is needed now |
| 11 | Marked as seen, a reminder "leaves the list" at once | It stays where it is, "Seen by you", with "Marked as seen." beside it, and the count in the menu drops; it leaves a list of those not seen when the list is next read - Refresh, a filter, another page. A refusal (the reminder moved on) says to read the list again, beside its button, and the list waits for the person | The full E2E run on the final tree failed once: the message beside the button went with its row as the list was read again at once, too soon to be seen. Kept in place, the confirmation stays beside the button that asked (the project's rule) and the rows below do not jump (the owner's 8A screen check) |
| 12 | ELG-1's cautious reading: with no registration in force, fitness and a permit are needed unless the registration is marked not applicable | A unit is a transport vehicle when a registration recorded on one of its assets says so: one standing today or on the job's rule day decides; with none standing, a transport registration that has run out still does, unless the registration is marked not applicable (the mark judged as before); with none recorded, or the last one non-transport, it is not (`evaluation.is_transport`, sharing `registrations_in_force` with the reminders' `transport_since`). Certificates due, the allocation check and the reminders all follow | The owner's decision at the screen check (section 1.5). The run-out case is this package's reading of it: otherwise a transport vehicle's fitness and permit reminders would vanish the day its registration ran out - people dropping off as the days pass (section 5.4) |
| 13 | - | The machine, Work Order and allocation links on Alerts carry "Back to Alerts", with the list's filters in the address, which Alerts reads when it opens (`alertsPageHref`, `alertFiltersFromSearch`) | The owner's screen check, step 11 |
| 14 | - | Above the list, how many it holds of all those it is drawn from: "6 of the 45 reminders you have not seen", or "... that have reached you" with all shown; a reminder marked seen here counts as seen at once (`shownOfText`) | The owner's re-check, 2 October 2026: "the number of certificates applicable to that filter should be shown ... something like 6/45 and when marked as seen and refreshed, 5/44" - done in this package as a small change |

### Tests and checks

Recorded in the acceptance record, each with the tree it ran on.

### Independent review

the independent reviewer, bounded packets. The owner's cap was three rounds; the owner agreed a fourth and a fifth
(1 October 2026), and a sixth for the change of rule made at the screen check. Any further round needs the owner's
agreement.

**Round 1** (packet `bf4ed7f2...`, tree `4db72ab`, commit `089c597`): `CORRECTION_REQUIRED`, six material findings,
none blocking. All six corrected, each test shown to fail without its correction:

| Finding | What was wrong | Corrected |
| --- | --- | --- |
| ELG2-R1-001 | A renewal recorded ahead without its copy cuts the cover short the day before it takes over; the reminder said the certificate in force "runs out" on that day, not that the renewal's copy is missing | `reminders.uncopied_takeover`: when the cover ends the day before a renewal of the same sequence (the one recorded last) takes over and that renewal has no copy, the reminder is `COPY_MISSING`, dated by its start - the same date and reminder before and after the takeover. Tests: pure (before and after, a copied renewal, one after a gap, one taking over early), and through the routes on a piece of kit and on a kit line of an allocation |
| ELG2-R1-002 | Marking seen was not serialized with the writes that change reminders: one committing meanwhile could leave a mark on a reminder that no longer reaches the person | `mark_seen` takes Resource Assignments' lock (the port's new `hold`) and then this module's - the locks every certificate, mark, rule, setting and allocation write takes, in the order 8A's writes take them - before working the reminders out. A site change or a retirement in the same instant is not serialized; such a mark is never shown (contract). Tests: a setting saved meanwhile is waited for and nothing is marked (`404`); marking waits for Resource Assignments' lock |
| ELG2-R1-003 | The menu's count was not latest-only: an older request answering later could replace a newer count, or be kept for its session | `createCountLoader` (`alertsState.ts`): every load takes a ticket; only the latest answer is shown or kept. Tests: answers out of order for one session, and across a session change |
| ELG2-R1-004 | The database checked only a "seen" mark's key prefix, with `LIKE`, whose `_` is a wildcard | The CHECK compares every part exactly (`split_part`): kind, subject type, subject, asset, certificate kind, an ISO date, and nothing more. A test varies each part |
| ELG2-R1-005 | A certificate dated 1 January of year 1 made the Alerts fail with a date overflow | Date arithmetic in `reminders.py` holds at the first and last day a date can be; `requirement_began` stops at the first. Tests: pure, and through the routes with certificates dated in year 1 and to 31 December 9999 |
| ELG2-R1-006 | `FUTURE_SLICES.md` still said "Three reminders" under the note that four were built | The bullet lists all four, saying which came when |

**Round 2** (packet `7e0fdec4...`, tree `8a3ded1`, commit `2672f23`): `CORRECTION_REQUIRED`, six material findings,
none blocking. Four corrected, each test shown to fail without its correction; one corrected in part and in part
settled by the agreed design; one settled by the agreed design:

| Finding | What was wrong | Done |
| --- | --- | --- |
| ELG2-R2-001 | Saving a setting can make a reminder disappear, or take a role off a reminder it had reached | **Settled by the design, no change.** Q18 - "each change applies from the moment it is saved" - and section 5.6: a new version applies at once to every reminder, including whom it has reached. "Nobody drops off" is about one path as the days pass (section 5.4), not a path Admin changes. Section 5.6 now says so in those words. The round-2 instruction had listed "a setting saved" as a drop-off case: the controller's wording, corrected for round 3 |
| ELG2-R2-002 | People reached could drop off when a renewal without its copy was recorded (round 1 dated it by its start, a day later) or when a job started | **Corrected for the renewal**: a certificate short for a missing copy - a renewal recorded ahead, or one in force - is dated by the day the cover before it ends, as one running out is (with none before it, the day before it takes over; `covered_until_before`). Recording the renewal, and its taking over, change the reason, not the date - the same reminder, the same people, the same "seen" marks. Tests: the date before and after, Management staying reached, a renewal after a gap, through the routes before and after the takeover. **The job starting is the design**: section 5.1 makes a cover still short when the job starts a reminder of the next kind, and section 5.4 now says it follows that kind's path - the standard paths of the two are the same |
| ELG2-R2-003 | A transport registration taking effect by a job's rule day made fitness or a permit needed for the job, but the reminder was dated as if not | `transport_since` reads the registrations in force today and, for a job, on its rule day (the later of today and its first day), as the check does. Test: pure |
| ELG2-R2-004 | Other writes changing a reminder were not serialized with marking seen: an asset retired, a part fitted, a site changed | Marking also takes the Equipment Reference's lock (`hold_equipment_writes`), between Resource Assignments' and this module's - no write takes two of them the other way round. A certificate's copy was already serialized: its attach check takes this module's lock (ELG-1). A Work Order line's site change is not: a mark made in that instant still records, truly, that the person saw that reminder that day (contract). Test: marking waits for the Equipment Reference's lock |
| ELG2-R2-005 | An answer to "Mark as seen" or Save could be applied after a session change, under another person's controls | Both pages note the session an action starts in (`createSessionGuard`, tested) and apply its answer only while that session is current; a session change resets the page's busy state |
| ELG2-R2-006 | A "seen" mark's date part was checked only as digits, so an impossible date passed | The mark stores the reminder's date (`reminder_date_on`), and its key's date part must equal it written as `YYYY-MM-DD`. Tests: an impossible date, 0000-00-00, and a real date other than the one stored |

**Round 3** (packet `b385fbd0...`, tree `a140467`, commit `7baa219`), the last within the cap:
`CORRECTION_REQUIRED`, two material findings and two advisory, none blocking. All four corrected; each new test shown
to fail without its correction:

| Finding | What was wrong | Done |
| --- | --- | --- |
| ELG2-R3-001 (material) | The session was checked before the answer's body was read, not after, so an answer read after a session change could still be applied | `actInSession` (`alertsState.ts`): the whole answer, body or refusal, is read first (`readActionAnswer`), and the session checked only then, immediately before anything is applied - feedback, the "seen" signal, the list read again, or a session ended. Both pages use it. Tests with a body still on its way when the session changes: a success, a refusal (a session ended included) and a network failure are each dropped whole |
| ELG2-R3-002 (material) | A "not applicable" mark that ended dated a certificate needed again even where it never stood for that requirement: a baseline mark at a site whose state's rule allows none, or a mark longer than the rule allows | `mark_stopped` counts only a mark the rule in force on its last day let stand, as the check counts one (refinement 10). Tests: a baseline mark against a state's rule allowing none, a mark longer than the rule's limit, a mark judged by the rule in force when it stopped |
| ELG2-R3-003 (advisory) | The module's description, `uncopied_takeover`'s and a test's name still said a renewal without its copy is reminded from its start | Reworded: it changes the reason, not the date |
| ELG2-R3-004 (advisory) | The round-2 transport correction was tested only on the pure rule, not through the allocation reminders that must pass the job's rule day | A route test: a registration saying transport, taking effect the day before a job starts, dates fitness and a permit for the job by that day - and the machine itself needs neither yet |

**Round 4** (packet `c63981f5...`, tree `4939d56`, commit `f4a579b`), agreed by the owner beyond the three planned:
`CORRECTION_REQUIRED`, two material findings, none blocking. Both corrected; each new test shown to fail without its
correction:

| Finding | What was wrong | Done |
| --- | --- | --- |
| ELG2-R4-001 | A second certificate without its copy, taking over from one also without its copy, moved the reminder's date forward though no cover had been restored: a new reminder, its "seen" marks and reach starting afresh | `covered_until_before` walks back through certificates without their copies, one after another, to where the last one with its copy stopped covering (or the day before the first of them). Tests: two in a row and a same-day replacement, all the same date; none with its copy before them; a certificate with its copy between them restoring the cover; through the routes, marked seen and then two more without their copies - the same reminder, still seen |
| ELG2-R4-002 | Reminder settings kept the previous session's settings and unsaved edits on screen while the new session's read was on its way | The page reads through the shared `createQueryController` (only the latest read's answer is shown) and `settingsPageAfter` (`alertSettingsState.ts`): a read starting clears the settings and every unsaved form at once, except the same session's read after a save refused as stale, which keeps them under the message. Tests: an admin's read still on its way when another person signs in - the page cleared at once, the admin's late answer kept out, the new answer shown; signed out, nothing shown and not left loading |

**Round 5** (packet `e0387e55...`, tree `4eb0caa`, commit `84d5adf`), agreed by the owner: `CORRECTION_REQUIRED`, two
material findings, none blocking; it found both round-4 corrections right and complete. Both corrected:

| Finding | What was wrong | Done |
| --- | --- | --- |
| ELG2-R5-001 | A job's fitness or permit reminder caused by a transport registration taking effect later said the certificate was "missing since" a day still to come | Said as "needed from" that day while it is ahead, as a rule taking effect later already was (`reasonText`). Test: a registration taking effect on 14 October, read on 1 October |
| ELG2-R5-002 | The continuity note and this section still said the review was to come, capped at three rounds | Both say what was done: five rounds, the fourth and fifth on the owner's agreement; a further round needs it too |

**Round 6** (packet `29af097c...`, tree `77c070d`, commit `4bbd659`), agreed by the owner for the change of rule at the
screen check (section 1.5): `CORRECTION_REQUIRED`, one material finding, none blocking. **No finding on the change of
rule** - no registration recorded is not a transport vehicle - which the instruction asked it to judge first and
hardest. Corrected:

| Finding | What was wrong | Done |
| --- | --- | --- |
| ELG2-R6-001 | A reminder could be marked seen while the list was being read again (Refresh); a read formed before the mark but answering after it would put the reminder back as not seen, beside "Marked as seen." | A row's **Mark as seen** is not offered while the list is read, as "Mark all shown as seen" already was not; and a mark is shown through the read's own controller (`showMarkedSeen`, `controller.answered`), which drops any read still on its way. Test: a read formed before the mark, answering after it, cannot bring the reminder back unseen - shown to fail when the mark only changes the list in hand |

A further round needs the owner's agreement.

## TB-1 correction, 5 October 2026 - the count's copy no longer keeps the token (TB1-802)

Decision 9 above kept the menu's count "in the browser's session storage with the session's token". TB-1's Pass 8 found
that Sign out did not remove that copy, so a working sign-in token stayed in the browser tab after signing out, usable
until it expired. TB-1's final independent review judged it a section 12 emergency; the owner chose a fix package. The
copy now keeps a fingerprint of the token instead (`tokenFingerprint`, `alertsState.ts`), so it still tells one
session's count from another's; a copy in the earlier form is never read back; and Sign out (`useSession.ts`) and the
shared session clearing (`pageSession.ts`) remove it (`components/sessionAlertCount.ts`). Tests: `alertsState.test.ts`
(the kept copy holds no part of the token; the earlier form is refused), `sessionAlertCount.test.ts`. No backend change,
no change to when the count is read. See `docs/continuity/TB1_802_SIGN_OUT_CLEARS_ALERT_CACHE.md`.
