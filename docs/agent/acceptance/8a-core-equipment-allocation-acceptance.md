# 8A core Acceptance - Own machines allocated to the resource requirements

Design and implementation record: `docs/agent/slices/8a-core-equipment-allocation.md` (section 17). API:
`docs/agent/contracts/resource-assignment-api-contract.md`. Continuity:
`docs/continuity/SLICE_8A_CORE_EQUIPMENT_ALLOCATION.md`.

## Preconditions

- The stack at migration head `20260908_0045` (`docker compose exec backend alembic current`). `alembic/` is
  baked into the backend image: after switching to this branch, `docker compose up -d --build
  --force-recreate backend`, and rebuild the frontend (`docker compose up -d --build --no-deps frontend`).
- Test users: `ops1` (Operations - allocates, and sets the billing cycle), `readonly1` (Management Read Only)
  for the permission check, `sales1` (Sales User) for the billing-cycle split. Password as documented for the
  prototype seed users.
- Seed the screen-check data on a database with no equipment machine and no waiting report preview:
  `docker compose exec backend python -m tooling.smoke_data seed --scenario equipment-allocation --json`, and
  save the manifest. Its `allocation_target.allocation_demo` block names the Work Order, the requirement, the
  four cranes and the kit below.
- Clean up afterwards: `docker compose exec backend python -m tooling.smoke_data cleanup --run-id <run id>`. It
  removes the run's allocations - those made on screen included - with their trips, kit lines and stored
  decisions, and refuses, deleting nothing, when an allocation of a requirement the run did not make holds or
  held one of the run's machines or pieces of kit (a freed allocation keeps them on its Work Order's history).

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| The pure rules: busy days, a unit's coverage, the status, candidate order, counted sets | `docker compose exec backend pytest tests/test_8a_allocation_rules.py -q` | all pass |
| Through the routes and at the database: finding, allocating, every refusal, replacing, freeing, dates, checking again, the billing cycle, trips and kit, coverage and status, cancelling, the port, the constraints, permissions, events | `docker compose exec backend pytest tests/test_8a_equipment_allocation.py -q` | all pass |
| The harness: allocations made later are the run's and go with it; the refusal when another Work Order holds or held a run's crane; the harness registering the port without the API | `docker compose exec backend pytest tests/test_8a_smoke_data.py -q` | 3 passed |
| Requirements, line details, the earlier harness sets | `docker compose exec backend pytest tests/test_wrr001_resource_requirements.py tests/test_slice_7c_work_order_line_detail.py tests/test_smoke_data_harness.py tests/test_elg1_smoke_data.py tests/test_ert1_smoke_data.py -q` | all pass |
| Route guard and permission catalogue (the 14 routes pinned) | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py tests/test_authorization_post_baseline_catalogue.py tests/test_authorization_compatibility_matrix.py -q` | all pass |
| Full backend regression, run alone | `docker compose exec backend pytest -q` | 0 failed; see Results |
| Migration: empty database to head, `downgrade -1`, head again | a scratch database inside the running Postgres | reaches `20260908_0045`; see Results |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence (prefix `MSYS_NO_PATHCONV=1` in Git Bash) | clean; see Results |
| Full E2E suite | `pwsh -NoProfile -File scripts/run-e2e.ps1` | see Results; `equipment-allocation.spec.ts` adds two tests. **Run it with `pwsh`, not `powershell`** |
| Committed-credential and fixture checks | `python scripts/check_tracked_secrets.py`, `python scripts/validate_contract_fixtures.py` | clean |

## Test data

- Every machine, model and number is invented and carries a run-unique token.
- The scenario `equipment-allocation` seeds ERT-1's, ERT-2's and ELG-1's records (`equipment-plum-import`) and:
  - four crawler cranes of an invented **ACME CC 250 <token>** (250 t), **`TEST-<token>-CW1`** to **`-CW4`**, their
    road papers marked not applicable (a crawler crane that cannot travel on a road):
    - `-CW1` and `-CW2`: thorough examination (30 and 45 days ago) and load test - **can be allocated**;
    - `-CW3`: thorough examination 350 days ago - it runs out during the job, **with a warning**;
    - `-CW4`: nothing recorded - **cannot be allocated**;
  - kit held for the CC 250: a **hook block** with its examinations, a counted set of **four counterweight
    blocks**, **two boom inserts**, and a **sling** never examined (it cannot go);
  - a Work Order (`allocation_target`) with one line whose site is **Jetty 2, Invented Port, Mumbai,
    Maharashtra**, "not a central-government site", a contract from yesterday for a year, and a requirement for
    **2 crawler cranes of at least 200 t** from 5 days ahead to 60 days ahead. Nothing is allocated.
- ERT-2's CC 100 crawlers (100 t) are left out as below the requirement; the all-terrain cranes are another type.

## Manual happy path

Sign in as `ops1`. Start at the requirement: **Resource planning** in the sidebar, then the requirement named in
the manifest (or `/resource-requirements/<requirement_public_id>`). The owner ran these steps on 29 September 2026
(runs `te1-d38e094b` and, for the re-check, `te1-a32c89e5`); what they found is in the design's section 17.

1. The requirement reads **Open**, and its **Machines** section "Machines - 0 of 2 units covered", with unit 1
   and unit 2 each "No machine yet." and **Allocate a machine to unit 1** / **unit 2**.
2. **Allocate a machine to unit 1.** The page names the requirement and unit; "Where and when" shows the site in
   Maharashtra, "not a central-government site", and the requirement's days. Above the machines table, "Not
   offered, of this class: ..." counts the crane whose model is not mapped and the CC 100 cranes, below what is
   asked. The table: `-CW1` and `-CW2` "Can be allocated", `-CW3` "Can be allocated, with a warning" (its
   thorough examination runs out during the job), `-CW4` "Cannot be allocated", its choice disabled.
   - A machine's link opens its page with **Back to allocating** at the top. Further down that page, "Kit for ACME
     CC 250 <token>" lists the kit held for its model, before any allocation.
3. Choose `-CW3`, a billing cycle **Monthly**, and **Allocate, with these warnings**: beside the button, "Tick "I
   have seen these warnings" first." Tick it and allocate again. The allocation page opens: **Held for this Work
   Order**, the stored answer and today's answer, the billing cycle "Monthly (set by ...)".
4. **Trips (Own Load) to site** (owner, 29 September 2026: a crane may go in several loads, each a Trip (Own
   Load) saying what it carries). Each message below appears beside its own button, and the page stays where it is.
   - **Add pieces to Trip (Own Load) 1**: the two inserts and the hook block "Free", the counterweight set "4 of 4"
     with a box for up to three digits and "nos." beside it, the sling "Cannot be allocated", its box disabled.
     Tick the hook block, enter **2** counterweight blocks, **List these pieces**: "Listed.", and both lines on
     Trip (Own Load) 1.
   - In Trip (Own Load) 1's **What this load carries** (the empty box hints "e.g. Base & carbody"), enter "Base and
     carbody", **Save**: "Saved.". Saving the same words again: "Nothing changed, so nothing was recorded."
   - Below the trips, **Another Trip (Own Load) goes on** already shows the allocation's first day. Enter "Boom
     butt", **Add a Trip (Own Load)**: "Trip (Own Load) added.", and Trip (Own Load) 2 on the first day.
   - **Add pieces to Trip (Own Load) 2**: the hook block now "Taken" (on trip 1), the counterweight "2 of 4". Tick
     both inserts, **List these pieces**: "Listed.", and both inserts on Trip (Own Load) 2.
5. Back on the requirement: **Partly allocated**, "Machines - 1 of 2 units covered". Unit 1, covered on every
   day, offers no **Allocate a machine** link; unit 2 does.
6. On the allocation, **Replace the machine**. The finder's days default to the allocation's own. Set "Replaces
   from" about two weeks in, **Find machines for these days**, choose `-CW1`, "Why it is being replaced"
   **Breakdown**, **Replace the machine**. The new allocation opens, held, "Replaces AL-...". The old one reads
   **Replaced**, its days ending the day before, "Replaced by ...", its trips and kit kept on its history.
7. On the new allocation, **Change the dates**:
   - move the start two days later, **Save the dates**: "Dates changed, and checked again." The requirement shows
     "0 of 2 units covered", and unit 1's link is back - the two days between are uncovered;
   - a start on the replaced allocation's last day is refused: "Unit 1 of RR-... already has a machine (AL-...)
     from ... to .... Choose other dates, or replace that machine.";
   - an end after the requirement's is refused: "This allocation ends on ..., after RR-... ends on ...".
8. **Allocate a machine to unit 2.** `-CW1` and `-CW3` show where they are held - `-CW3` for the replaced
   allocation's days, which it keeps - their choices disabled; `-CW4` cannot be chosen. Change the **To** date
   without finding again: choosing is disabled, "These machines are for the dates found before...". **Find
   machines for these days**, choose `-CW2`, **Allocate**.
9. On `-CW1`'s allocation, choose **Not needed**, **Free the machine**, **Yes, free it**: "Freed. The allocation
   stays on the history." Freed before its first day, it reads "Never went (ended before it started)".
10. **Allocations** in the sidebar: **Starting in the next 15 days** lists the held ones with today's answer; "All,
    with the history" adds the replaced and freed ones. The Work Order's "Machines allocated" and `-CW3`'s machine
    page ("Allocations", below its certificates) list the same.

## Negative checks on screen

- Step 2: `-CW4`'s choice cannot be picked; a request for it through the API is refused naming the load test and
  examination "missing".
- Step 3: without the tick the allocation is refused beside the button; nothing is stored.
- Step 4: a day before the allocation's first, or after its last, in **Another Trip (Own Load) goes on**: the
  button is disabled, with "A Trip (Own Load) goes on a day of the allocation: ..." beside it.
- Step 9: **Other (say what)** with the note empty: **Free the machine** is refused beside the button, "Say what the
  other reason is, in the note.", before any confirmation.
- The Work Order line's details: set **Central-government site?** to **Not answered** and save. The requirement's
  own page shows "Say on line 1's details whether its site is a central-government site ..." in place of the
  **Allocate a machine** links; an allocation reads "The site cannot be judged"; its **Check again** (under
  **Eligibility**) is refused beside the button; its kit picker shows the same message with every box disabled.
  Set the answer back to **No**: **Check again** then stores a fresh answer.

## Manual permission check

- Sign in as `readonly1` and open the requirement: the Machines section lists the allocations but offers no
  **Allocate a machine** link; an allocation's page has no **Check again**, **Replace**, **Free**, dates, trip or
  kit buttons, and each Trip (Own Load) reads "Carries: ..." without a box to change it.
- Sign in as `sales1`: the allocation pages show; **Save the billing cycle** is offered, the allocation actions
  are not.
- With an allocation open, **Sign out** from the menu: the page asks to sign in and shows no allocation. Sign in as
  `readonly1` and open it again: no action buttons.

## Not visible on screen, checked by the automated tests

- The database's own checks: one machine, one unit and one single kit piece never held twice on a common day (the
  exclusion constraints, each shown refusing on its own); end fields exactly when replaced or freed; reasons
  fitting the status; `OTHER` with a note; a counted quantity only on a counted set.
- Once an allocation's first day has come (owner, 1 October 2026): freeing it with no last day is refused unless the
  reason is **Recorded by mistake**, which still frees it with no days; replacing it from its first day is refused,
  from a later day allowed; the replacement finder starts on the day after its first day at the earliest; changing
  its dates may move its last day but not its first (4 October 2026). The seeded allocations all start in the
  future, so this cannot be reached on screen with the test data; the screens' own refusals (beside **Free the
  machine**, on the replace page, and beside **Save the dates**) are covered by `allocationState.test.ts`.
- Two saves of one machine at once: one wins, the other is told the machine was just taken.
- A request key used twice has one effect; reused for anything else, `409`.
- Cancelling a requirement frees its held machines in the same transaction; the requirement's version and who
  last changed it do not move when only its status does.
- Event payloads carry ids, codes, dates and counts - no registration, note or reason text.
- The harness cleanup removes allocations made on screen and refuses when someone else's requirement holds a
  run's machine.

## Known limitations

- A replaced or freed allocation's kit lines read "Listed": their days ended with the allocation's, which its
  Days row shows.
- A Trip (Own Load) can be neither moved nor removed: an allocation's dates cannot be changed to leave one outside
  them (Free and Replace still end an allocation early). Deferred: `DEFERRED_REQUIREMENTS.md`, 8A, "Trips (Own
  Load)".
- What a load carries is the planner's own words: the crane's parts are not yet records, and a model's standard
  loads are not yet held (both deferred, as above).
- An action's message stays beside its button after the next action (owner: deferred; `UI_UX_CARRY_FORWARD.md`,
  "Allocations").

## Deferred, deliberately

Design section 12: hired machines and vendors, firm allocation at release (7B; the owner leans to line by line),
dispatch and arrival checks, gate passes, general tools, kit coming back (8E), crew (8B), reminders (ELG-2),
events on lapse and a recheck job, approving "needs approval", a time limit on holds.

## Results

Every check is recorded, with the tree it ran on, in the continuity note; a result holds for the tree it names, not
for a later one (independent review, 8A-FB2-005).

**Before the full review:**

- full backend regression 2673 passed, 0 failed, on `10ad1bb`;
- full E2E 30 passed, 9 skipped, 0 failed, on `1dcd995`, on its third run: the first found a real defect (a
  description typed while the page was read again was lost, corrected in `1dcd995`), the second met the laptop
  stalling for about 45 seconds (0.6 GB of memory free);
- frontend typecheck clean, 414 tests passed, build clean, on `1dcd995`;
- the owner's screen check, and the re-check of its findings, passed (29 September 2026, on `072596f` and
  `4fb3c27`).

**The full review's first corrections (`aae2174`):** frontend 418 passed; the 8A, requirement and route-guard suites
318 passed; the migration on an empty database, head, `downgrade -1` and head again; the browser check of the screen
corrections. The full backend regression on `aae2174` was run while the second round reviewed it.

**The full review's second corrections (`f221d3f`):** full backend regression 2682 passed, 0 failed; full E2E 30
passed, 9 skipped, 0 failed (its second run; the first met a stall under load, see the continuity note); frontend
420 passed on the tree it committed.

**The focused round 3's corrections (`d0f5b27`):** the migration check (head, `downgrade -1`, head again), frontend
420 passed, the guard's proof case by case, and the 8A, requirement and route-guard suites, as the continuity note
records for that commit. The package is accepted only when the review is. The full backend regression on `aae2174`, the first corrections' tree: 2677
passed, 0 failed.

**Review.** Nine rounds of independent review, every finding corrected; round 10 was not run (owner, 29 September
2026). The owner then asked for a full review of 8A core, with documentation and UAT corrections, before ELG-2 (30
September 2026), and for its follow-up round. Design section 17 records both rounds' findings and corrections.
