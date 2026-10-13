# ERT-1 Acceptance - Plum's machines into the Equipment Reference

Design and implementation record: `docs/agent/slices/ert-1-plum-machines-into-the-equipment-reference.md`
(section 20). API: `docs/agent/contracts/equipment-reference-api-contract.md`. Continuity:
`docs/continuity/ERT_1_PLUM_MACHINES_INTO_THE_EQUIPMENT_REFERENCE.md`.

## Preconditions

- The stack at migration head `20260908_0042` (`docker compose exec backend alembic current`). `alembic/`
  is baked into the backend image: after switching to this branch, `docker compose up -d --build
  --force-recreate backend`.
- Test users: `admin1` (Admin - the Fleet Admin until that role exists; holds
  `EQUIPMENT_REFERENCE_MANAGE` and `EQUIPMENT_IDENTITY_READ`), `readonly1` (Management Read Only) for the
  permission check. Password as
  documented for the prototype seed users.
- Seed the screen-check data: `docker compose exec backend python -m tooling.smoke_data seed --scenario
  equipment-plum-import --json`, and save the manifest. Its `equipment_demo.second_report_csv` is the
  second invented report; write it to a file to upload (the screen-check hand-over names the file).
- Clean up afterwards: `docker compose exec backend python -m tooling.smoke_data cleanup --run-id <run id>`.
  It removes the run's models, both imports (the second found by its fingerprint), every machine they
  brought in, the reading recorded on the second report and the mappings to the run's models - and
  nothing else.

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| The import, models, machines, corrections, pairs, permissions and events through the routes | `docker compose exec backend pytest tests/test_ert1_equipment_import_api.py -q` | 66 passed |
| The transformer itself, including the dummified report of 24 September against counts taken independently | `docker compose exec backend pytest tests/test_ert1_plum_report.py -q` | 36 passed |
| The harness: scenario, the screen flow on its second report, cleanup by provenance, refusal, idempotence | `docker compose exec backend pytest tests/test_ert1_smoke_data.py -q` | 11 passed |
| WRR-001's tests with structure version 2 | `docker compose exec backend pytest tests/test_wrr001_equipment_reference.py tests/test_wrr001_resource_requirements.py -q` | all pass |
| Route guard and permission catalogue (the two new permissions and 23 new routes pinned) | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py tests/test_authorization_post_baseline_catalogue.py -q` | all pass |
| Harness regression | `docker compose exec backend pytest tests/test_smoke_data_harness.py -q` | all pass |
| Full backend regression, run alone | `docker compose exec backend pytest -q` | 0 failed; see Results |
| Migration: empty database to head, `downgrade -1`, head again | a scratch database inside the running Postgres | reaches `20260908_0042`; see Results |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence (prefix `MSYS_NO_PATHCONV=1` in Git Bash) | clean; 330 tests (294 before); `equipmentState.test.ts` added; five routes added to the route table and its tests |
| Full E2E suite | `pwsh -NoProfile -File scripts/run-e2e.ps1` | see Results; `equipment-import.spec.ts` adds two tests. **Run it with `pwsh`, not `powershell`** |
| Committed-credential and fixture checks | `python scripts/check_tracked_secrets.py`, `python scripts/validate_contract_fixtures.py` | clean |

## Test data

- Every behaviour test uses invented reports in the shape of Plum's: a title line, then the 32 columns in
  Plum's order. Machine numbers, model names and odd values carry a run-unique token.
- One realistic test reads `backend/tests/fixtures/plum_vehicle_report_dummified_2026-09-24.csv`, a copy of
  Plum's report of 24 September 2026 made under the owner's rule of 25 September 2026: registration, bed,
  engine and chassis numbers replaced by stable dummies (`TEST-REG-0001`, ...; placeholders such as `0`,
  `NA`, `NIL` kept), PAN, insurance, invoice, purchase, posting-account and GPS values replaced by
  `DUMMY`; categories, makes, models, capacities, years, owner and status kept. The original file stays in
  `<a PBL folder outside the repository>` and is never committed. Its expected counts - 290 machines to bring in, 328 inactive and
  never seen, 62 in classes no business line uses, 1 without a machine number, 60 model names to map -
  were counted from the file with PowerShell, independently of the code.
- The screen-check scenario `equipment-plum-import`: three models (ACME AC 100 <token>, a Crane
  all-terrain rated 100 t; the same name as a Crane carrier; LIFTCO LX 18 <token>, a scissor Aerial Work
  Platform, 18 m working height, 230 kg platform capacity), one confirmed report with three machines
  (`TEST-<token>-CR1` crane, `-ML1` manlift, `-CR2` a crane whose model name is not mapped), and a second
  report adding `-CR1C` (the crane's carrier, its name not mapped yet) and `-ML2` (a manlift whose capacity
  reads `230 KG <token>`).

## Manual happy path

Sign in as `admin1`. Start at **Equipment** in the sidebar (`/equipment`).

1. **Machines** lists `TEST-<token>-CR1`, `-ML1` and `-CR2` (type the token in "Machine number or
   reference"). CR1 reads "Crane, all-terrain - ACME AC 100 <token>", Rated capacity 100 t; CR2 shows "Model
   name not mapped to a model yet"; all three say serial number or year of manufacture to enter.
2. **Models** lists the three models, with the Plum names mapped to the crane and the manlift.
3. **Plum report**: choose the second report file, leave the date as today, **Upload and preview**. The
   preview says what confirming would do: new 2, unchanged 3 (or changed, if a machine was edited).
4. **Model names to map** shows `<token> ACME AC 100 CHASSIS` (1 machine) and `<token> MYSTERY CRANE`.
   Choose "ACME AC 100 <token> (Crane carrier)" for the first and **Map**: "Mapped. Refresh the preview to
   see its effect." Confirm is now disabled, with the reason beside it.
5. In **Rows needing attention**, `-ML2` is flagged "Plum's figure is not a number: platform capacity".
   **Read "230 KG <token>" as...**: A number and its unit, 230, kilogram, a reason; **Record reading**.
6. **Refresh**: "Preview refreshed ..." `-ML2` is no longer flagged, and beside it reads: Capacity figure
   (for the check): "230 KG <token>" read as 230 kg. `-CR1C` is now a Crane carrier (part).
7. **Crane halves to pair** proposes `-CR1` for `-CR1C`. Tick **Confirm pair for ...**, then **Confirm**:
   "Report confirmed. The machines are updated."
8. Open `-CR1` from Machines: **Fitted parts** lists `-CR1C` fitted today. Open `-CR1C`: "Fitted to" names
   `-CR1`.
9. On `-CR1`: **Enter details** (a serial number, a year) - saved beside the button; the machine no longer
   appears under "Details to complete". **Correct a Plum value**: Engine number, a new value, a reason -
   the engine number changes at once, marked "Corrected: Plum has ...". **Plum report** page: the
   correction and the reading of step 5 are under **Corrections to send to Plum**.
10. Upload the same second report again: refused - "This report was already imported on <today>."

## Manual permission check

Sign in as `readonly1`. **Equipment** lists the same machines; a machine's page offers no Enter details,
Correct or Pair, and its engine and chassis numbers read "Shown to Admin only" (owner, 25 September 2026) - as do
the values of a correction to either, whose reason reads "The reason is shown to Admin only."; **Models** offers no Record a model or Map; **Plum report** says "Only Admin uploads and
confirms Plum's report." with no upload, and still shows the corrections to send to Plum.

## Not visible on screen, checked by the automated tests

- Nothing changes until confirmation; a preview made before another report was confirmed, or before a
  mapping, rule, correction, own value or pair changed, is refused ("Refresh it"); a second confirmation
  does nothing twice; a stale version is refused.
- Inactive machines never seen are not brought in; a known machine Plum marks inactive is retired and comes
  back when active again; a machine missing from a report is flagged, never retired; a new number carrying
  a missing machine's chassis number is flagged as possibly renumbered.
- A correction closes itself when a confirmed report carries the corrected value, and is flagged when Plum
  changes to a third value; the machine number cannot be corrected; details entered on the platform
  survive every import.
- A model's rating reaches its machines; a model's class cannot change while machines use it; a retired
  model cannot be newly mapped.
- Independent review, round 1: a model's new rating or type, and a machine's own value, re-read the machine
  at once (the "differs from the rating" flag clears or appears in the same save); a part changed since it
  was shown, or retired, is not fitted or removed; a confirmation moves the version of every machine it
  changes and of no other; the same file as any confirmed report - not only the latest - is refused; the
  preview names every correction and reading a row was read with, and shows that row even with no flag;
  cleanup refuses when a fitted-part link joins the run's records to anyone else's.
- Independent review, round 2: the reason of an engine or chassis number correction or reading is withheld
  from everyone but Admin; a correction that changes a machine's class or kind removes a part that no longer
  fits and flags the parts left unfitted at once; the preview page never shows one import's answer under
  another's address, and neither page lets an earlier version replace a later one; cleanup refuses when
  another name is mapped to a run's model or another import was compared with a run's.
- Independent review, round 3: a report that ends a fit shows it in the preview before confirming, and
  confirming closes exactly that; a link is never closed before the day it was fitted; only the awaited
  action's or save's answer shows a message or unlocks a form, and only on its own page; a mapping's
  event is the mapping's own.
- Independent review, round 4: the equipment scenarios - and so the E2E suite - seed only on a database
  with no machines and no waiting preview; a set-aside row closes or flags no correction; a part is never
  fitted before it was last removed; an old action's answer changes nothing on the preview page; a model's
  form closes when someone else saves a newer version.
- Every write is refused to every role but Admin; every read is open to the six read roles.
- Event payloads carry no machine, engine or chassis number, Plum value or reason text; the import keeps no
  PAN or insurance column, and neither does its preview.

## Deferred, deliberately

See `docs/agent/DEFERRED_REQUIREMENTS.md`, "Plum's machines: what ERT-1 left out".

## Results

Recorded with the tree each was measured on, in the continuity note.

**The owner's screen check, 26 September 2026: Pass with minor issues.** Steps 1 to 10 of the happy path
and the read-only check passed on scenario run `te1-87b0b26e`. Three screen notes, each resolved in the
next commit (layout and wording only):

- Step 3: "Show every row" starts at line 3 - the column is the line in the file (lines 1 and 2 are the
  report's title and headings). The column now reads "Line in file", with that note above the table.
- Step 4: Refresh was hard to find - the owner clicked Reload at the top first. A **Refresh the preview**
  prompt now appears at the top of the page once a name is mapped or a reading recorded. Deferred: after a
  refresh, highlighting the rows it changed (`UI_UX_CARRY_FORWARD.md`, "Equipment").
- Step 9: Save details and Cancel sat out of line with the boxes. A form's buttons in a `.form-grid` now
  stand level with the boxes, with any message beneath them, by one stylesheet rule - and the Equipment
  pages now style through `globals.css` rather than inline (owner, the same day).
