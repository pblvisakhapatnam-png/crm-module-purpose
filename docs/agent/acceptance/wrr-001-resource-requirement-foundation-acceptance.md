# WRR-001 Acceptance - Resource Requirements and the Equipment Reference

Written so a later tester can perform regression/UAT without this session's chat history. Design,
owner answers and the implementation record: `docs/agent/slices/wrr-001-resource-requirement-foundation.md`.
Routes as built: `docs/agent/contracts/resource-requirement-api-contract.md`. The equipment structure's
ownership: ADR-037.

## Preconditions

Stack running. This package adds migration `20260908_0041`; `alembic/` is baked into the backend image,
so after merging rebuild before testing:

```powershell
docker compose up -d --build --force-recreate backend
docker compose exec backend alembic current
```

Expected: `20260908_0041 (head)`. Rebuild the frontend image too (`docker compose up -d --build
frontend`): its source is not bind-mounted.

Frozen contract check, before and after:

```bash
sha256sum docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md
```

Expected: `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a`.

**Reconciled 9 October 2026 (TB-1 TB1-102 part b):** that was its hash until CS-04 part 1 (8 October 2026) appended
the owner-approved dated amendment at its end; its SHA-256 is now `0f16ff221e897f6199c352204a0ecced6f9a67f0c6695ad97c08c9dc2cd39080`, the current value
recorded in `docs/continuity/NEXT_STEPS.md`. A check run today expects that hash, unchanged before and after.

## Automated checks

Each count below is what the command reports on the current candidate (round 4's tree with its three
corrections); the full backend regression and the E2E suite are recorded under **Results**, with the tree
each ran on, once they finish.

| Check | Command | Expected |
| --- | --- | --- |
| Resource Requirements through the routes and the database, with the concurrent-create and database backstop tests | `docker compose exec backend pytest tests/test_wrr001_resource_requirements.py -q` | 85 passed |
| The Equipment Reference: version 1 against the design, its constraints, the class suggestion, no write route | `docker compose exec backend pytest tests/test_wrr001_equipment_reference.py -q` | 37 passed |
| TE-6 service surface (the new Work Order read pinned with the names added after the split) | `docker compose exec backend pytest tests/test_te6_work_orders_service_surface.py -q` | all pass |
| Route guard (pins all seven new routes) and the permission catalogue | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py tests/test_authorization_post_baseline_catalogue.py -q` | all pass |
| Harness scenario and cleanup | `docker compose exec backend pytest tests/test_smoke_data_harness.py -q` | 79 passed |
| Full backend regression, run alone | `docker compose exec backend pytest -q` | 0 failed; see Results for the count on each tree |
| Migration: empty database to head, then `downgrade -1`, then head | a scratch database inside the running Postgres, as recorded in the continuity note | reaches `20260908_0041`; ten tables, three permissions and fourteen grants appear and disappear with the revision; version 1 loads 1 version, 12 classes, 9 class business lines, 23 types, 17 capabilities, 20 class capabilities and 32 aliases |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence (prefix `MSYS_NO_PATHCONV=1` in Git Bash) | clean; 294 tests (222 before this package); `resourceRequirementState.test.ts`, `resourceRequirementDetailState.test.ts` and `resourceRequirementRequests.test.ts` added; three routes added to the route table and its tests |
| Full E2E suite | `pwsh -NoProfile -File scripts/run-e2e.ps1` | 19 passed, 9 skipped, 0 failed (17 passed before; two added by `resource-requirement.spec.ts`); cleanup succeeded. **Run it with `pwsh`, not `powershell`** |
| Committed-credential and fixture checks | `python scripts/check_tracked_secrets.py`, `python scripts/validate_contract_fixtures.py` | clean |

## Test data

Seed the scenario written for this screen check:

```powershell
.\scripts\smoke-data.ps1 seed -Scenario work-order-resource-requirements
```

It builds a Work Order with three lines and a contract from **1 October 2026 to 30 September 2027**:

- **line 1** - a crane line (category "Crane") with a site, *Berth 4, Fishing Harbour, Kakinada*, shift
  billing terms stating **1 operator and 1 helper**, and an **urgent** requirement for **1 crawler crane,
  rated capacity at least 250 t**, from 15 October 2026;
- **line 2** - a manlift line (category "Manlifts") with **no site**, and a requirement for **2
  articulating-boom aerial work platforms, working height at least 26 m**, from 1 November 2026, 1
  operator;
- **line 3** - a forklift line (category "Forklift") with no requirement, left for the tester.

The output prints the Work Order's URL. Clean up afterwards with `.\scripts\smoke-data.ps1 cleanup -RunId
<run id>`; cleanup removes every requirement on the Work Order's lines, including ones added by hand.

## Manual happy path

User `ops1` (Operations). Open the seeded Work Order.

1. In the **Jump to** row there is **Resources needed**. The section **What each line needs on site**
   lists every line. Line 1 shows its reference (RR-...) and "1 x Crawler crane, rated capacity at least
   250 t. From 15 October 2026, until the line ends." with **Open** and **Urgent**. Line 2 shows "2 x
   Articulating boom aerial work platform, working height at least 26 m" and, in brown, "The line has no
   site recorded yet." Line 3 reads "No requirement recorded for this line." Each line has **Add a
   requirement**.
2. Click **Add a requirement** on line 3. Expected: the page **Add a requirement**, a card naming the
   Work Order and line 3 with its scope; **Kind of machine** already set to **Forklift** with "Suggested
   from the line's category, "Forklift"."; **Number of machines** 1; **Needed from** 1 October 2026 (the
   contract start); **Operators** and **Helpers** empty, and beneath them "The Work Order's terms: Not
   recorded yet."
3. Open **Kind of machine**. Expected: only **Crane, Aerial Work Platform, Forklift, Excavator** - no
   prime mover, trailer, generator or light vehicle. Choose **Crane**: **Type** offers Crawler,
   All-terrain, Truck-mounted telescopic, Rough-terrain, Pick-and-carry, Knuckle-boom loader, Mobile
   tower and Derrick, and the capabilities are **Rated capacity (t), at least** (marked as the main
   capability), **Main boom length (m), at least** and **Maximum tip height (m), at least**. Choose
   **Forklift** again.
4. Leave **Operators** empty and click **Save requirement**. Expected, beneath the button: "Enter the
   operators." Nothing is saved.
5. Enter **Operators 1**, **Helpers 0**, **Rated capacity 5**, **Needed from 15 September 2026**, and
   save. Expected, beneath the button: **"This requirement starts on 15 September 2026, before the
   contract starts on 1 October 2026."**
6. Change **Needed from** to **1 December 2026** and save. Expected: the requirement's own page opens,
   titled "RR-... - 1 x Forklift, rated capacity at least 5 t", **Open**; **Needs attention** says "The
   line has no site recorded yet"; **The Work Order line, as it stands now** shows the contract "1
   October 2026 to 30 September 2027".
7. Click **Change the requirement**, set **Number of machines** to 2 and **Priority** to Urgent, and
   **Save changes**. Expected: "Changes saved." beneath the button; the title reads "2 x Forklift ...";
   an **Urgent** badge.
8. Click **Change the requirement** and **Save changes** without changing anything. Expected: "Nothing
   changed, so nothing was saved."
9. In **Cancel this requirement**, click **Cancel this requirement** with no reason. Expected: "Give the
   reason the requirement is being cancelled." Type a reason, click **Cancel this requirement**, then
   **Yes, cancel it**. Expected: "Requirement cancelled."; the badge reads **Cancelled**; a **Cancelled**
   row shows who, when and the reason; there is no longer a way to change or cancel it.
10. In the sidebar, **Resource Planning**. Expected: **Resources needed**, showing Open requirements with
    the urgent crane first and the manlift after it; the cancelled forklift is not listed. Set **Status**
    to Cancelled: it is. Set **Status** back to Open and **Kind of machine** to Aerial Work Platform: only
    the manlift.
11. Open the crane requirement from the list. Expected: **Crew in the Work Order** "1 operator, 1 helper
    per shift"; **Billing basis** Shift; **Site** "Berth 4, Fishing Harbour, Kakinada, Andhra Pradesh";
    no **Needs attention** box.
12. **Change the requirement**: **Operators** 2, and save. Expected: **Needs attention** now says "The
    crew differs from the Work Order's". Put it back to 1: the warning goes.
13. Open the Work Order (the link in **The Work Order line, as it stands now**). In **Contract period**
    change **Contract starts on** to **1 November 2026** and save. Expected: saved - a requirement never
    blocks a contract change. Back on the crane requirement (from 15 October 2026), **Needs attention**
    says "The dates no longer fit the contract or the line's own dates". Put the start back to 1 October
    2026: the warning goes.

## Manual permission check

14. Sign in as `readonly1` (or `sales1` or `finance1`) and open the same Work Order. Expected: **Resources
    needed** lists the requirements, with no **Add a requirement** anywhere. Open one: no change or cancel
    controls, and "Your role can view this requirement. Operations and Admin can change or cancel it."
    **Resource Planning** lists them too.

## Not visible on screen, checked by the automated tests

- Every refusal the API makes that the form already prevents: a class Hiring does not deploy, a type of
  another class, a capability that does not describe the class or given twice, a unit sent with a
  value, zero, negative, NaN or oversized values, two items, unknown fields, a line on another Work
  Order, a date in a gap between extensions, dates outside the line's own dates, a Closed Work Order.
- A repeated create with the same request key returning the first requirement; the same key for another
  line refused; a stale version refused for change and cancel.
  **Reconciled 8 October 2026 (TB-1 TB1-102 part b):** only the very same request returns the first requirement, with
  `replayed: true`; the key with any other request - on the same line too - is refused (`409`).
  `test_wrr001_resource_requirements.py` carries the new checks; `docs/continuity/TB1_102B_REPLAY_RULE.md`
  records them.
- A retired type refused for a new choice but kept on a requirement saved with it.
- Event payloads carrying no specification, notes, cancellation reason or amount.
- Every database constraint and the capability trigger, by writing rows directly; version 1 of the
  structure against the design, row by row.
- Two creates with one request key submitted at the same moment: one requirement, one event.
- Answers that arrive late, out of order or not at all (review rounds 2 to 4): only the answer to the
  request awaited is shown, on the planning list and the requirement page; the list empties while a new
  filter's request is pending; Save stays disabled until the facts for the date on the form are in, and a
  retry clears an earlier refusal; a typed crew number is never overwritten, and the other still follows
  the date. These are tested as pure rules (`resourceRequirementRequests.test.ts`,
  `resourceRequirementState.test.ts`), because the frontend has no component tests yet.

## Deferred, deliberately

See `docs/agent/DEFERRED_REQUIREMENTS.md`, "Resource requirements and the Equipment Reference": the Plum
transformer and the Model and Machine records (next package), a maintenance screen for the structure,
combinations of machines (Transportation's), structured licence checks (Eligibility), availability,
reservation, assignment and fulfilment (8A), and whether release (7B) needs a requirement per machine
line.

## Results

Measured, with the tree each ran on:

- **First candidate** (24 September 2026, before review): full backend regression 2247 passed, 0 failed;
  E2E 19 passed, 9 skipped, 0 failed, cleanup succeeded; migration from empty as above; an exploratory
  browser run of steps 1 to 11, signed in as `admin1`, matched every expected result.
- **Round-1 tree `703312aa`**: full backend regression 2251 passed, 0 failed. Its E2E run was stopped when
  every request reached the backend about ten seconds late while Chromium ran - the laptop short of memory,
  not the code; its cleanup ran.
- **Round-3 tree `b321698a`**: focused suites (the requirement, Equipment Reference, service-surface, route-guard and permission-catalogue tests) 237 passed, 0 failed; frontend typecheck clean, 276 tests, build clean. Full backend regression 2262 passed, 0 failed (34 min); the backend is unchanged since, so this is also the current candidate's backend result. The E2E run after it stopped at the health gate, before seeding anything: the host had 706 MB of 12 GB free and the health endpoint answered in 2 s or not at all. E2E is run on the current candidate instead.

- **Round-4 tree `17b9499f`** (round 3's three frontend corrections): frontend typecheck clean, 288 tests,
  build clean. The backend is unchanged from round 3's tree.
- **Current candidate** (round 4's three frontend corrections): frontend typecheck clean, 294 tests, build
  clean; six mutations of the new rules, all caught by the new tests. The backend is unchanged from round
  3's tree. E2E not yet run to completion: on 24 September the first two tests failed while starting
  Chromium (`browserType.launch: Timeout 180000ms exceeded`), before any test step, with the host at about
  1 GB of 12 GB free; the run was stopped and its cleanup of all three seeded runs completed.

- **Final tree** (the accepted tree plus the screen check's layout correction, 25 September): frontend
  typecheck clean, 294 tests, build clean; **E2E 19 passed, 9 skipped, 0 failed**, both
  `resource-requirement.spec.ts` tests among the passes, cleanup of all three seeded runs succeeded. The
  frontend image was rebuilt from this tree by the run itself.
- **Exploratory browser check on the current candidate** (24 September, freshly seeded
  `work-order-resource-requirements`, as `readonly1`): the Work Order lists both seeded requirements with
  no **Add a requirement**; on **Resource Planning** the table emptied the moment **Kind of machine** was
  changed and then showed only the manlift; **Status** Cancelled showed "No requirements match."; the crane
  requirement shows "Your role can view this requirement", no change or cancel controls, crew "1 operator,
  1 helper per shift" and billing basis Shift. The Operations steps are the owner's screen check.

Independent review: rounds 1 to 4 CORRECTION_REQUIRED, every finding corrected; round 5 (tree `1d85ad9a`,
on the owner's yes, scoped to round 4's corrections) **ACCEPTED** with no findings (slice document, section
22).

**The owner's screen check, 25 September 2026** (seeded run `te1-8b69a926`, Work Order WO-003375, as
`ops1` and then `readonly1`): **Pass with minor issues.** Steps 1 to 14 passed, with two remarks:

- Steps 2 and 3: the **Type** box sat lower than **Kind of machine** beside it, and the offset shifted as
  hints appeared and disappeared with the choices made. The rows stretched every field to the tallest
  one's height, which pushed a field without a hint down. Corrected in `ResourceRequirementFormFields.tsx`:
  the fields sit at the top of their row, and the key capability's hint is now beneath its box like every
  other hint. Layout only; no behaviour changed. The owner looked again at steps 2 and 3 the same day: aligned.
- Step 6: the requirement's title and status badge should stay visible when the page scrolls. Deferred
  to the UI pass, at the owner's word (`UI_UX_CARRY_FORWARD.md`).
