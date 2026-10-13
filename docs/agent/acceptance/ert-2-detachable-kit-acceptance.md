# ERT-2 Acceptance - Detachable kit

Design and implementation record: `docs/agent/slices/ert-2-detachable-kit.md` (section 18). API:
`docs/agent/contracts/equipment-reference-api-contract.md`, "ERT-2: detachable kit". Continuity:
`docs/continuity/ERT_2_DETACHABLE_KIT.md`.

## Preconditions

- The stack at migration head `20260908_0043` (`docker compose exec backend alembic current`). `alembic/`
  is baked into the backend image: after switching to this branch, `docker compose up -d --build
  --force-recreate backend`, and rebuild the frontend (`docker compose up -d --build frontend`).
- Test users: `admin1` (Admin - the Fleet Admin until that role exists; holds
  `EQUIPMENT_REFERENCE_MANAGE`), `readonly1` (Management Read Only) for the permission check. Password as
  documented for the prototype seed users.
- Seed the screen-check data on a database with no equipment machine and no waiting report preview:
  `docker compose exec backend python -m tooling.smoke_data seed --scenario equipment-plum-import --json`,
  and save the manifest. Its `equipment_kit` block names the kit crane model, its two cranes and the three
  kit models.
- Clean up afterwards: `docker compose exec backend python -m tooling.smoke_data cleanup --run-id <run id>`.
  Beyond ERT-1's records it removes every piece of kit of the run's kit models - including pieces added on
  screen - and the models' fits, and refuses, deleting nothing, when a kit model it did not make is recorded
  as fitting one of its crane models.

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| Kit through the routes: structure version 3, kit models and their fits, adding, sharing, details, retiring, the depth setting, the database's own guards, permissions and events | `docker compose exec backend pytest tests/test_ert2_detachable_kit.py -q` | 41 passed |
| ERT-1's tests with structure version 3 | `docker compose exec backend pytest tests/test_ert1_equipment_import_api.py tests/test_ert1_plum_report.py -q` | all pass |
| The harness: the scenario with kit, kit added on screen cleaned up, the refusal for an outside kit model | `docker compose exec backend pytest tests/test_ert1_smoke_data.py -q` | 14 passed |
| WRR-001's tests with structure version 3 | `docker compose exec backend pytest tests/test_wrr001_equipment_reference.py tests/test_wrr001_resource_requirements.py -q` | all pass |
| Route guard and permission catalogue (the two new routes pinned to `EQUIPMENT_REFERENCE_MANAGE`) | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py tests/test_authorization_post_baseline_catalogue.py -q` | all pass |
| Full backend regression, run alone | `docker compose exec backend pytest -q` | 0 failed; see Results |
| Migration: empty database to head, `downgrade -1`, head again | a scratch database inside the running Postgres | reaches `20260908_0043`; see Results |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence (prefix `MSYS_NO_PATHCONV=1` in Git Bash) | clean; 352 tests (330 before); no route added |
| Full E2E suite | `pwsh -NoProfile -File scripts/run-e2e.ps1` | see Results; `equipment-kit.spec.ts` adds two tests. **Run it with `pwsh`, not `powershell`** |
| Committed-credential and fixture checks | `python scripts/check_tracked_secrets.py`, `python scripts/validate_contract_fixtures.py` | clean |

## Test data

- Every test uses invented models and pieces carrying a run-unique token. Nothing is read from Plum's real
  report or from the website's equipment list, which only informed the design's sizes (design, section 2).
- The screen-check scenario `equipment-plum-import` adds, beside ERT-1's records: a second crane model,
  ACME CC 100 <token> (a Crane, crawler, 100 t), with two cranes of it in both reports (`TEST-<token>-KC1`,
  `-KC2`), and kit held for that model - two pieces of "CC 100 insert 6 m <token>" (a boom insert, maker's
  part number `PN-INS-<token>`), a counted set of four "CC 100 block 3.7 t <token>" (counterweight), and a
  hook block model "CC 100 hook block 100 t <token>" with no piece held yet.

## Manual happy path

Sign in as `admin1`. Start at **Equipment** in the sidebar (`/equipment`).

1. **Machines**: type the token and open `TEST-<token>-KC1`. A **Kit for ACME CC 100 <token>** section says
   the kit is shared by the 2 active cranes of the model, and lists the insert "2 held", the counterweight
   "4 held, counted" and the hook block "None held yet".
2. **Add kit**: choose the hook block model, "How many alike" 2, **Add kit**. Beside the button: "Added to
   the kit for this model: 2 records of ...". The hook block row now reads "2 held".
3. Open `-KC2`: the same kit list, hook blocks included - the kit is the model's, not one crane's.
4. In the kit list, open the insert model's link: **Machines** shows "Showing the pieces of one kit model."
   and its two pieces, with "Back to TEST-<token>-KC1" at the top. **Show everything** clears the filter;
   **Show** "Machines, parts and kit" lists machines and pieces together.
5. Open one insert: it reads "Equipment - kit", "Held for" names ACME CC 100 <token>, and it shows no Plum
   facts and no Correct a Plum value. **Enter details**: a serial number and a year - saved beside the
   button.
6. **Retire this piece**: Why "Scrapped", **Retire**. Beside the button: "Retired. Its history is kept."; the
   page reads "Retired on <today>: scrapped." Back on `-KC1`, the insert reads "1 held".
7. Open the counterweight set (from `-KC1`'s kit list, then its piece): "Pieces in the set" 4. **Retire
   pieces**, "How many of the 4 pieces" 1, Why "Lost", **Retire**. Beside the button: "1 piece retired from
   the set; 3 left in it. Its history is kept." The set now reads 3, and stays active.
8. **Models**: **Record a model**, class Hook block. Saving without ticking a crane model is refused beside
   the button - kit must name the crane models it fits. Tick ACME CC 100 <token>, give a rated capacity and
   weight, and save: the list shows it with "(kit)", and its Kit column reads "Fits ACME CC 100 <token>".
9. **Models**, the mapping choices for a Plum model name offer no kit model.

## Negative checks on screen

- On `-KC1`, **Add kit** with "How many alike" 0 or 51: refused beside the button ("Give how many, from 1
  to 50.").
- **Enter details** with a year of manufacture after this year: refused beside the button.
- Open the manlift `-ML1`: no kit section - only kinds of machine the structure gives kit to (cranes) have
  one.
- **Models**, **Change** on ACME CC 100 <token>: the Kind box is disabled, and beside it "2 records use this
  model, so its kind cannot change. Record a new model instead." The same on a kit model with pieces held.
- With `-KC1` open in two tabs: in one, **Enter details** and save; in the other, **Add kit** - refused
  beside the button: someone else changed this machine; reload.
- On a counted set, **Enter details** offers no serial number, and lowering the number of pieces is refused
  beside the button: a set shrinks only by retiring the pieces that left.
- On a fitted part (`-CR1C` after ERT-1's step 7, or any Plum part), there is no Retire action: Plum's
  report retires Plum's machines.

## Manual permission check

Sign in as `readonly1`. `-KC1` shows the same kit list with no **Add kit**; a kit piece's page shows its
details and "Held for" with no Enter details and no Retire; **Models** offers no Record a model.

## Not visible on screen, checked by the automated tests

- A model's class cannot change while machines or pieces use it, or while kit fits it; and a model Plum names
  are mapped to does not become a kind of kit (review round 3).
- The harness's cleanup takes a piece as the run's by the kit model it was added as, not the one it carries
  now: the run's piece moved to another model goes with the run; someone else's piece moved onto a run's
  model makes cleanup refuse (review round 3).
- Kit is never fitted to a machine; a Plum report never brings kit in or maps a name to a kit model; a
  confirmed report neither changes nor retires kit.
- The database itself refuses a Plum record of a kind of kit and a platform record that is not kit, a
  counted set with its own number, a one-by-one piece with a quantity above one, a machine with no number, a
  retired piece without its reason, and any change to the request that made a record (review rounds 2 and
  4). The service refuses a fitted link that would nest deeper than the depth setting (3); the migration's
  own check refuses part fits or open links that loop or nest deeper, and records whose origin disagrees with
  their kind.
- Adding kit twice with the same request key adds it once and answers with the same pieces, and the same
  key for another kit model is refused - judged by the model the request first asked for, even after a
  piece's model changed (review round 2); retiring an already retired piece changes nothing; a stale version
  is refused.
  **Reconciled 8 October 2026 (TB-1 TB1-102 part b):** the key with any other request - another count, number or year
  as well as another kit model - is refused; only the very same request is answered with the first pieces.
  `test_ert2_detachable_kit.py` carries the new checks; `docs/continuity/TB1_102B_REPLAY_RULE.md` records them.
- Kit is added only on the premise its page showed: refused when the machine or the kit model changed since,
  or when the kit model does not fit the machine's model (review round 1).
- The migration's own check refuses open fitted links deeper than the setting, and a loop of them even with
  no top (review round 1).
- Between two answers of one version of a machine, the page shows the one asked for later, so an older kit
  list never replaces a newer one (review round 1; frontend tests).
- Every write is refused to every role but Admin; every read is open to the six read roles.
- Event payloads carry no serial number or note text beyond the retirement note as the event's reason.

## Deferred, deliberately

See `docs/agent/DEFERRED_REQUIREMENTS.md`, "Detachable kit: what ERT-2 left out", "Fixed Assets: what the
Equipment Reference keeps for it", "Trailer beds and prime movers" and "Statutory requirements found with
ERT-2".

## Not independently reviewed

Four review rounds ran (design section 18); none ended `ACCEPTED`. The owner directed no fifth round, so round
4's five corrections were checked only by their own tests (each fails when its correction is undone), the
full regression and E2E, not by the reviewer:

- the retirement CHECK's NOT NULL reason (ERT2-R4-001);
- the trigger's refusal of a Plum record of a kind of kit, and the structure check's origin clause
  (ERT2-R4-002);
- an open model form taking the reloaded model, and `kindProblem` (ERT2-R4-003);
- the structure and models loaded by the machine loader (ERT2-R4-004);
- a retired piece's details form (ERT2-R4-005).

## Results

Recorded with the tree each was measured on, in the continuity note.

**The owner's screen check, 27 September 2026:** every step passed apart from five notes ("Rest all ok"), each
resolved the same day - the Models form brought into view, a way back from the filtered Machines list, the
Kind box's alignment (one stylesheet rule for every form), "Machines, parts and kit" in Show, and the year of
manufacture capped at the current year. Design section 18, "The owner's screen check".

## Update, 4 October 2026: a counted set may not shrink below its trips (TB-1 finding TB1-307)

Automated: `test_a_counted_set_cannot_shrink_below_what_its_trips_list_from_today` - a set of four with three listed
on a trip: retiring two is refused (`422`, naming 3 and the allocation; quantity, version and status unchanged),
retiring one is allowed (three left). It fails without the change (the retirement is accepted). And
`test_retiring_kit_takes_the_allocation_lock_before_the_equipment_lock` - a retirement waiting for Resource
Assignments' lock holds nothing of the Equipment Reference's; it fails on a lock timeout with the locks taken the
other way round.

Screen check. Test user `admin1` (Fleet Admin) and `ops1` (Operations). Test data: the smoke-data scenario
`equipment-allocation` (`allocation_target`: a Work Order needing two 250 t crawlers, nothing allocated, with a
counted counterweight set held for their model).

1. As `ops1`, allocate a 250 t crawler and list 3 counterweight blocks on its first trip.
2. As `admin1`, open the counterweight set's machine page and retire 2 of its pieces (if it holds 4): refused beside
   the button - "Trips list 3 of this set at once from today (AL-...), so it cannot go down to 2 ..."; the quantity is
   unchanged.
3. Retire 1: it saves; the set holds 3.
4. Negative path: as `ops1` (not Admin), the retire action is refused as before (permission unchanged).
