# HOL-1 Acceptance - PBL's holiday calendar, and each Work Order's changes to it

Design and implementation record: `docs/agent/slices/hol-1-holiday-calendar.md` (section 16). APIs:
`docs/agent/contracts/holiday-calendar-api-contract.md`, and the "HOL-1" section of `work-order-contract.md`; the
calendar reminder is in `eligibility-api-contract.md`, "Reminders and escalation". Continuity:
`docs/continuity/HOL_1_HOLIDAY_CALENDAR.md`.

## Preconditions

- The stack at migration head `20260908_0047` (`docker compose exec backend alembic current`). `alembic/` is baked into
  the backend image: after switching to this branch, `docker compose up -d --build --force-recreate backend`, and
  rebuild the frontend (`docker compose up -d --build --no-deps frontend`).
- **A test site only, never PBL's own**: the steps start the 2026 and 2027 calendars, which are shared by every Work
  Order on that database.
- Test users (password as documented for the prototype seed users): `admin1` (Admin - keeps the calendar),
  `ops1` (Operations - reads the calendar, writes a Work Order's holidays), `readonly1` (Management / Read Only).
- Seed the screen-check Work Order: `docker compose exec backend python -m tooling.smoke_data seed --scenario
  holiday-calendar --json`, and keep the manifest. Its `holiday_target.work_order` URL is the Work Order below: a
  contract from 1 December 2026 to 30 November 2027; line 1's site in Gujarat and line 2's in Maharashtra, both by the
  day with an overtime rate; line 3 with no site, by the hour; holidays not answered. No calendar year is started.
- Clean up afterwards: `docker compose exec backend python -m tooling.smoke_data cleanup --run-id <run id>` removes the
  Work Order and its holiday changes. The 2026 and 2027 calendars entered on screen are the test site's, not the run's:
  they stay until removed by hand.

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| The pure rules: a year's refusals, what a save changes, the holidays for a state, the window, the holidays that apply, the notes, the overtime rate | `docker compose exec backend pytest tests/test_hol1_holiday_rules.py -q` | 49 passed |
| The calendar through its routes and at the database: years, saving, versions, the complete mark, every refusal, roles, the write lock, every constraint | `docker compose exec backend pytest tests/test_hol1_holiday_calendar_api.py -q` | 42 passed (38 at the build; four added at review round 1) |
| The holidays that apply: each state's lines, a line with no site or an unknown state, working days and holidays added, the notes, the overtime rate, the window, read roles | `docker compose exec backend pytest tests/test_hol1_resulting_holidays_api.py -q` | 16 passed |
| The calendar reminder on the Alerts: schedule, who it reaches, search, seen, a reminder settled meanwhile, the setting, fail closed, when it begins, the "seen" table's checks | `docker compose exec backend pytest tests/test_hol1_calendar_reminder.py -q` | 17 passed (one added at review round 1) |
| Slice 7D Part 4's holiday tests, carried over to the new shape, none weakened, plus the working days | `docker compose exec backend pytest tests/test_slice_7d_part_4_holidays.py -q` | 81 passed (54 before) |
| ELG-2, which gains the fifth kind | `docker compose exec backend pytest tests/test_elg2_reminder_rules.py tests/test_elg2_certificate_reminders_api.py tests/test_elg2_smoke_data.py -q` | 111 passed |
| The harness: the new scenario, the core bundle's tenth record set and its cleanup by provenance | `docker compose exec backend pytest tests/test_smoke_data_harness.py tests/test_hiring_uat_smoke_data.py -q` | all pass |
| Route guard, permission catalogue, the Work Orders service surface | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py tests/test_authorization_post_baseline_catalogue.py tests/test_authorization_compatibility_matrix.py tests/test_authorization_baseline_equivalence.py tests/test_te6_work_orders_service_surface.py -q` | all pass |
| Full backend regression, run alone | `docker compose exec backend pytest -q` | 0 failed; see Results |
| Migration: empty database to head, `downgrade -1`, head again | a scratch database inside the running Postgres | see Results |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence (prefix `MSYS_NO_PATHCONV=1` in Git Bash) | clean; 501 tests (462 before; one added at review round 2, one at round 4, three after the screen check); one route added |
| Full E2E suite | `pwsh -NoProfile -File scripts/run-e2e.ps1` | 35 passed, 9 skipped, 0 failed; `holiday-calendar.spec.ts` adds two tests. **Run it with `pwsh`** |
| Committed-credential and fixture checks | `python scripts/check_tracked_secrets.py`, `python scripts/validate_contract_fixtures.py` | clean |
| The frozen Slice 6D.1 handoff contract | `sha256sum docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` | `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a` |

## Screen check (about twenty minutes)

Sign in as `admin1`. "Today" below is the day of the check, in 2026.

1. **Alerts** (menu). Click **PBL's holiday calendar not set up**. One reminder: *Holiday Calendar 2026* - "PBL's holiday
   calendar for 2026 is not marked complete, and 2026 began on 1 January 2026", reminded since the day the package was
   installed; reached Admin and Management from that day. (2027's appears from 2 November 2026.)
2. Open the seeded **Work Order**. In **Holidays: PBL's calendar and this Work Order's changes**: "Holidays: not answered
   yet". Under **Holidays that apply**: "1 December 2026 to 30 November 2027"; the note "PBL's holiday calendar for 2026
   and 2027 is not complete yet ..."; three groups - **Line 1 - Gujarat**, **Line 2 - Maharashtra**, **Line 3 - no site
   recorded** (with what to put right) - and no days in any.
3. **Holiday Calendar** (menu). The picker shows 2026 and 2027, each "Not set up". Click **2027**. Add, then **Save**:
   - 26 January 2027, *Republic Day*, National holiday, All of India;
   - 22 March 2027, *Holi*, Festival holiday, All of India;
   - 1 May 2027, *Gujarat Day*, Festival holiday, These states: Gujarat;
   - 1 May 2027, *Maharashtra Day*, National holiday, These states: Maharashtra;
   - 14 April 2027, *Tamil New Year*, Festival holiday, These states: Tamil Nadu.

   Expected: "Saved as version 1. Every Work Order uses it from now."; 2027 reads "Being entered (version 1)".
4. **Refused, nothing saved**: add a second all-India holiday on 26 January 2027 and Save - "Two holidays on 26 January
   2027 apply to all of India. Keep one."; remove it. Add *Uttarayan*, 1 May 2027, for Gujarat and Save - "1 May 2027 is
   a holiday for Gujarat twice. Keep one."; remove it (or **Undo changes**).
5. Back on the **Work Order**, **Holidays that apply**: Line 1 - Gujarat lists 26 January, 22 March and 1 May (Gujarat
   Day); Line 2 - Maharashtra the same with 1 May as Maharashtra Day; Line 3 only 26 January and 22 March. None lists 14
   April. Each says "Holiday: as each line's off-day term says".
6. Choose **The Work Order changes PBL's calendar as listed**. The table **PBL's calendar holidays inside the contract**
   lists 26 January (Lines 1, 2 and 3), 22 March (Lines 1, 2 and 3) and 1 May (Gujarat Day (Gujarat); Maharashtra Day
   (Maharashtra) - Lines 1 and 2). Set 22 March to **Working day, overtime rate** with the note *Customer's plant runs*;
   set 1 May to **Working day, normal rate**. Under **Holidays this Work Order adds**, **Add a holiday**: 29 August 2027,
   Festival holiday, *Site foundation day*. **Save holidays**: "Holidays saved."; the badge reads "Changes PBL's
   calendar: 1 holiday added, 2 working days".
7. **Holidays that apply** is read again: 22 March reads "Working day, every hour at the line's overtime rate" with the
   note, and in Line 3's group "... Line 3 records no overtime rate for this day." (line 3 is by the hour); 1 May reads
   "Working day, normal rate" for lines 1 and 2 - Maharashtra Day too, as the Work Order's changes are one list for
   every line; 29 August appears for every line, "added by this Work Order".
8. Under **Working days on dates not in PBL's calendar yet**, **Add a working day**: 15 August 2027, Working day,
   normal rate. **Save holidays**. Beside "Holidays saved." - a moment after it, once the holidays that apply are read
   again - and under **Holidays that apply**: "15 August 2027: Not a holiday in PBL's calendar for any site of this Work
   Order: making it a working day does nothing."
9. In **Contract period**, try to move the end to 1 August 2027 and save. Refused: "The contract cannot end on 1 August
   2027, because a working day is listed on 15 August 2027." Nothing changes.
10. **Holiday Calendar**, 2027: tick **This year's calendar is complete**, **Save**: "Complete (version 2)". Back on the
    Work Order, the note names 2026 only. Open **2026**: add 15 August 2026, *Independence Day*, National, All of India.
    Before saving, the page warns "This changes a day already passed: 15 August 2026. ...". Tick complete and **Save**.
    The red count beside **Alerts** in the menu goes at once. **Alerts**: the 2026 reminder is gone.
11. Sign out; sign in as `ops1`. **Holiday Calendar**: the years read, with no **Save**, **Add a holiday** or complete
    tick. On the Work Order, the holidays can still be changed and saved (Operations writes billing terms).
12. Sign in as `readonly1`. **Holiday Calendar** and the Work Order's holidays only read: no **Save holidays**.

## Results

Recorded on the worktree's own stack (PostgreSQL 17), 2 October 2026.

```text
full backend regression, run alone, at 2aebac6 (8236082 changes   2951 passed, 1 skipped, 0 failed (53 min)
  no backend file)
migration on an empty scratch database                            upgrade to 20260908_0047 (head); downgrade -1 to
                                                                  20260908_0046; upgrade to 20260908_0047; one head
review round 1 corrections: the five new tests on the code as it  4 failed, each for the reason found (the next save's
  was                                                             year in the answer; 2101 offered and reminded); the
                                                                  field-name test passed - the code was right there
the same with the corrections, and the affected suites            316 passed (calendar API 42, reminder 17, rules 49,
                                                                  resulting 16, Part 4 81, ELG-2 111)
full E2E suite at 0288bb4 (round 1 corrected)                     35 passed, 9 skipped, 0 failed; cleanup clean
review round 2 corrections: the earlier key CHECK put back in a   all three stored - the real key, one ending "|", one
  rolled-back transaction, three keys for one year's mark         ending "||suffix"
the same suites with the corrections (reminder, ELG-2, calendar   170 passed
  API)
migration on an empty scratch database, with the "seen" table's   0046 -> head -> downgrade -1 -> head: after the
  CHECKs compared                                                 downgrade the CHECKs are 0046's exactly; after the
                                                                  second upgrade, the first upgrade's exactly
frontend: typecheck, tests, build (round 2 corrected)             clean; 497 passed; built
review round 3 correction: the words asserted for a name, a       2 failed with the request validator's list, no date;
  description and a note too long, on the schemas as they were    with the correction, the words naming the date
calendar API, Part 4, rules, resulting, reminder, TE-6 surface    211 passed
  (round 3 corrected)
full backend regression at 90d9df3 (round 3 corrected)            26 failed, 2930 passed, 1 skipped - every failure the
                                                                  worktree database's own leftovers, not the code: 11
                                                                  machines (and one eligibility rule) created at 14:54
                                                                  UTC by the run on a4b0930, stopped at 2% when round 3
                                                                  required a change, so its tests' cleanup never ran.
                                                                  The equipment scenarios refuse to seed where machines
                                                                  are held, as designed. Re-run on a fresh database
review round 4 correction: the words asserted for a field left    3 failed with the request validator's "Field
  out, on the schemas as they were                                required" list; with the correction, the words
calendar API, Part 4, rules, resulting, reminder, TE-6 surface    211 passed
  (round 4 corrected)
frontend: typecheck, tests (round 4's reducer test added)         clean; 498 passed. The new test fails, with the
                                                                  page's other generation tests, when the reducer's
                                                                  generation guard is removed for the check
independent review round 5 on 039d308                                      ACCEPTED, no findings
final full backend regression at 039d308, run alone, on a fresh   2956 passed, 1 skipped, 0 failed (54 min)
  worktree database
final full E2E suite at 039d308, retries 0                        35 passed, 9 skipped, 0 failed; cleanup clean
frontend build                                                    built at round 2's correction; no frontend source
                                                                  file changed after it (rounds 3 and 4 changed a test)
```

After 039d308 only documents changed.

**The owner's screen check, 3 October 2026**, on the worktree stack: steps 1 to 7 and 11 to 12 passed. Step 8: only
"Holidays saved." showed beside the button - the note was under "Holidays that apply" alone. Step 9: the contract's
start was moved, not its end, and the refusal ("The contract cannot start on 1 August 2027, because a working day is
listed on 22 March 2027.") was right for that. Step 10: the menu's Alerts count still showed 1, after a reload too,
while the Alerts page listed none. Steps 8 and 10 corrected (design section 16, "After the owner's screen check"); the
steps above now say where the note shows and that the count goes at once.

```text
frontend after the screen-check corrections: typecheck, tests,     clean; 501 passed (three added); built
  build
browser, on the worktree stack                                    2026's complete mark taken off: the menu count 1 at
                                                                  once; put back: gone at once. A save with the 15
                                                                  August 2027 working day: the note beside "Holidays
                                                                  saved."
full E2E suite at 209d0ad, retries 0                              35 passed, 9 skipped, 0 failed; cleanup clean
```

**The owner re-checked steps 8 and 10 on the corrected build, 3 October 2026: "8 and 10 pass now".** With steps 1 to 7
and 11 to 12 passed before, and step 9 right for what was entered, the screen check is complete. The owner chose to
open the pull request without a sixth review round for the screen-check corrections.

## Known gaps, deliberately left (design section 11; `DEFERRED_REQUIREMENTS.md`, "What HOL-1 leaves")

- Nothing is calculated or locked: log sheets (8C) and billing (8D) will read the holidays that apply.
- A working day at the overtime rate on a line with no overtime rate is shown, not refused.
- The Hiring user test pack still describes Slice 7D Part 4's holiday list; it is updated after the test (Q1).
- The calendar reminder is on screen only; email and SMS wait for `NTF-001`.
