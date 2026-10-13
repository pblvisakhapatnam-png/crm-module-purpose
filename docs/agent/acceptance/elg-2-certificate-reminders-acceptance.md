# ELG-2 Acceptance - Certificate reminders and escalation

Design and implementation record: `docs/agent/slices/elg-2-certificate-reminders.md` (section 16). API:
`docs/agent/contracts/eligibility-api-contract.md`, "Reminders and escalation". Continuity:
`docs/continuity/ELG_2_CERTIFICATE_REMINDERS.md`.

## Preconditions

- The stack at migration head `20260908_0046` (`docker compose exec backend alembic current`). `alembic/` is
  baked into the backend image: after switching to this branch, `docker compose up -d --build
  --force-recreate backend`, and rebuild the frontend (`docker compose up -d --build --no-deps frontend`).
- Test users (password as documented for the prototype seed users):
  - `admin1` (Admin - the Fleet Admin until that role exists; holds `ELIGIBILITY_RULE_MANAGE`);
  - `ops1` (Operations User);
  - `readonly1` (Management / Read Only).
- Seed the screen-check data on a database with no equipment machine and no waiting report preview:
  `docker compose exec backend python -m tooling.smoke_data seed --scenario equipment-allocation --json`, and save the
  manifest. Its `equipment_reference_target.equipment_reminders` and `reminder_target.reminder_demo` blocks name the
  machines and the allocation below. Every machine number is `TEST-<token>-...`.
- Have a small PDF at hand, as a certificate's copy.
- Clean up afterwards: `docker compose exec backend python -m tooling.smoke_data cleanup --run-id <run id>`. It removes
  the run's machines, certificates, allocations and every "seen" mark on them - those made on screen included. A
  reminder setting saved on screen is the platform's and stays: a version is never edited or deleted.

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| The pure rules: reminder days, the flag at once, the path, each date and reason, which reminder an outcome raises, the refusals of a setting | `docker compose exec backend pytest tests/test_elg2_reminder_rules.py -q` | 83 passed |
| Through the routes and at the database: the four reminders, who sees what, seen, the list, settings, the database's refusals, fail closed | `docker compose exec backend pytest tests/test_elg2_certificate_reminders_api.py -q` | 27 passed |
| The harness: the seeded reminders and the cleanup of "seen" marks | `docker compose exec backend pytest tests/test_elg2_smoke_data.py -q` | 1 passed |
| ELG-1, 8A and the harness counts ELG-2's seed changes | `docker compose exec backend pytest tests/test_elg1_evaluation.py tests/test_elg1_machine_eligibility_api.py tests/test_elg1_smoke_data.py tests/test_ert1_smoke_data.py tests/test_8a_allocation_rules.py tests/test_8a_equipment_allocation.py tests/test_8a_smoke_data.py -q` | all pass |
| Route guard and permission catalogue (the five routes pinned) | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py tests/test_authorization_post_baseline_catalogue.py tests/test_authorization_baseline_equivalence.py -q` | all pass |
| Full backend regression, run alone | `docker compose exec backend pytest -q` | 0 failed; see Results |
| Migration: empty database to head, `downgrade -1`, head again | a scratch database inside the running Postgres | see Results |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence (prefix `MSYS_NO_PATHCONV=1` in Git Bash) | clean; 460 tests (420 before); two routes added |
| Full E2E suite | `pwsh -NoProfile -File scripts/run-e2e.ps1` | see Results; `equipment-alerts.spec.ts` adds three tests. **Run it with `pwsh`, not `powershell`** |
| Committed-credential and fixture checks | `python scripts/check_tracked_secrets.py`, `python scripts/validate_contract_fixtures.py` | clean |
| The frozen Slice 6D.1 handoff contract | `sha256sum docs/agent/contracts/accepted-offer-to-work-order-handoff-contract.md` | `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a` |

## Test data

Beside ERT-1's, ERT-2's, ELG-1's and 8A's records, the scenario `equipment-allocation` (and the core bundle) adds:

- **`TEST-<token>-RM1`**, an 80 t crawler crane (ACME CC 80 <token>): registration and road tax marked not
  applicable; insurance running out in **20 days**, pollution certificate (PUC) in **10**, thorough examination in
  **5**; a load test that **ran out 2 days ago**.
- **`TEST-<token>-RM2`**, another 80 t crawler: registration, PUC and road tax marked not applicable; insurance running
  out in **6 days**; both examinations in order.
- A **sling** held for the CC 80 cranes (LIFTCO Sling 8 t <token>), its thorough examination running out in **25
  days**.
- **`reminder_target`**: a Work Order whose line's site is Jetty 4, Invented Port, Dahej, **Gujarat** (not a
  central-government site), with a requirement for one crawler crane of at least 50 t from **12 days ahead** for about
  seven weeks. **RM2 is held on it** (allocation `AL-...`, in the manifest), with the sling on its first Trip (Own
  Load): its insurance runs out **before the job starts**, the sling's examination **during** it.
- **`TEST-<token>-CW4`** (8A's) has nothing recorded: its papers are **not yet recorded**, since today.

The standard settings come with the migration: "A certificate running out" and the two allocation reminders remind
60 and 30 days before, weekly from 15, daily from 7, and every day after; "A certificate not yet recorded" every day.
Admin is reached from the first reminder; Operations from 15 days before (at once on a job; 7 days after for papers not
yet recorded); Management from 7 days before (14 days after for papers not yet recorded).

## Manual happy path (the owner's screen check, about twenty minutes)

1. Sign in as `admin1`. The menu shows **Alerts** just below Dashboard, with a red count. Open it.
2. In "Machine, piece, Work Order or allocation", type `RM1`'s number: four reminders - "Load test ran out on ...",
   "Thorough examination runs out on ..." (5 days), "Pollution certificate (PUC) runs out on ..." (10 days),
   "Insurance runs out on ..." (20 days). Each says "Reminded once, on <today>" and whom it has reached.
3. Type `CW4`'s number: its six papers - registration, insurance, PUC, road tax, thorough examination, load test -
   each "missing since <today> - added to the Equipment Master then", **A certificate not yet recorded**, reached:
   Admin only. No fitness or permit: with no registration recorded it is not a transport vehicle (the owner, 1 October
   2026; design section 1.5).
4. Back on `RM1`: above the list, "4 of the N reminders you have not seen". **Mark as seen** on the load test.
   "Marked as seen." shows beside the button, the row says "Seen by you" where it is, the count in the menu drops by
   one, and the line above reads "3 of the N-1". **Refresh**: the row leaves the list; the line stays "3 of the N-1".
   Untick "Only those I have not seen": the load test is there, "Seen by you".
5. Sign out; sign in as `ops1`. Alerts, `RM1`: the PUC, the examination and the load test - **not** the insurance
   (20 days: Operations is reached from 15). `CW4`: nothing (Operations from 7 days after).
6. Search the allocation's `AL-` reference: "Insurance runs out on ..., before the job at Jetty 4, Invented Port, Dahej,
   Gujarat starts on ...", and the sling's "Thorough examination runs out on ..., during the job ...", both reaching
   Operations at once, each linked to the Work Order and the allocation.
7. Sign out; sign in as `readonly1`. `RM1`: the examination and the load test only; the load test says "Seen by
   <Admin's name> (...)". The `AL-` reference: the insurance only (6 days); not the sling (25 days).
8. Sign in as `admin1`. **Equipment > Reminder settings**: four sections, each "Version 1, loaded with the package",
   with its reminder days in words. In **A certificate running out**, change step 2 (Operations User) to **25 days
   before the date**; **Save**: "Saved as version 2. It applies from now."; the version line names you.
9. Remove the last band (the one "after the date (0: on the day)") and **Save**: refused beside Save - "The last band
   must start on the day the certificate runs out, or after it ...". **Undo changes**.
10. Sign in as `ops1`. Alerts, `RM1`: the insurance is now there (step 8). **Reminder settings**: it only reads - no
    Save.
11. As `ops1`, open the allocation (its link on the Alerts page) and **Free the machine** (reason "Not needed"),
    **Yes, free it**. **Back to Alerts**: the list as it was, the `AL-` reference still in the search, now showing
    nothing.

## Negative and permission paths (automated; spot-check by hand if wished)

- Sales, Sales Manager and Finance see no reminder with the standard paths (`test_elg2_certificate_reminders_api.py`).
- Only Admin saves a setting (`403` for the other five roles); a stale version is `409`; each refusal is in words.
- Marking a reminder that has not reached you is `404`; one that has moved on is `409`; several at once is all or none.
- Without `RESOURCE_ASSIGNMENT_READ`, the allocation reminders are not shown.
- The database refuses a band or step out of range, a channel other than the screen, a role that does not exist, and
  a "seen" mark whose key names another reminder.

## Known limitations and deferred checks

- On screen only: no email or SMS (`NTF-001`). A reminder records no event, and nothing is scheduled (ADR-019).
- Paths name roles; positions and regions wait for `ORA-001`.
- A note with "seen" is a deferred design needing PBL's confirmation (Q20).
- The count in the menu may lag up to five minutes, except after marking seen or signing in again.
- See `DEFERRED_REQUIREMENTS.md`, "Certificate reminders: what ELG-2 leaves out".

## Results

Each result names the tree it ran on.

- Pure rules 70 passed; API 21 passed; harness 1 passed; the authorization, ELG-1, 8A and harness suites 377 passed
  (on the build commit `31a80c7` before its smoke-data changes; the smoke-data tests rerun on `63c16db`: 21 passed).
- Migration on a scratch database: empty to `20260908_0046`; `downgrade -1` to `20260908_0045` with the four tables
  gone; head again with the four standard settings (on `63c16db`).
- Frontend: typecheck clean, 440 tests passed, build clean (on `31a80c7`; no frontend change since).
- E2E: 33 passed, 9 skipped, 0 failed (`equipment-alerts.spec.ts` 3 of them), exit 0, cleanup removed the run's one
  "seen" mark (on `63c16db`).
- Time: the dummified Plum report of 24 September brings in 290 machines with nothing recorded - 836 reminders. The
  count takes 0.06 s, a page of 100 0.07 s, Certificates due 0.03 s (a scratch database, on `63c16db`). Beyond the
  report's 681 rows: 700 invented crawler cranes with nothing recorded give 5,600 reminders; the count takes 0.33 s, a
  page 0.33 s, Certificates due 0.21 s (a scratch database, on the round-1 corrections).
- After independent review round 1 (design section 16): pure rules 75 passed, API 26 passed, harness 1 passed; frontend
  typecheck clean, 444 tests passed, build clean; each new test shown to fail without its correction.
- After round 2: pure rules 78 passed, API 26 passed, harness 1 passed; frontend typecheck clean, 445 tests passed,
  build clean; each new or changed test shown to fail without its correction; the migration re-applied with the stored
  date (downgrade, upgrade).
- After round 3: pure rules 81 passed, API 27 passed, harness 1 passed, ELG-1's evaluation 61 passed; frontend
  typecheck clean, 449 tests passed, build clean; each new test shown to fail without its correction.
- Full backend regression, started on `7baa219` (round 2's corrections): 2788 passed, 0 failed, in 63 minutes. Round
  3's backend edits were made while it ran, after collection; it is not counted as the final tree's run.
- After round 4: pure rules 82 passed, API 27 passed, harness 1 passed; frontend typecheck clean, 453 tests passed,
  build clean; each new or changed test shown to fail without its correction.
- After round 5: frontend typecheck clean, 453 tests passed, build clean; the changed test shown to fail without its
  correction. Round 5 changed no backend file.
- Full backend regression on the final backend (`84d5adf`; no backend file changed after it), run alone: 2793 passed,
  0 failed, in 50 minutes.
- Full E2E on the final tree, with `pwsh`: first 32 passed, 9 skipped, 1 failed - "Marked as seen." beside the button
  went with its row as the list was read again at once (design section 16, refinement 11). Corrected: the marked
  reminder stays where it is, "Seen by you", until the list is next read (`alertsMarkedSeen`, tested; frontend 454
  tests, typecheck and build clean). Run again: 33 passed, 9 skipped, 0 failed, exit 0; cleanup removed the run's one
  "seen" mark, none left.
- **The owner's screen check, 1 October 2026: all eleven steps pass** ("Everything passes, including 3 and 11"), on the
  worktree stack at `84cf123`, run `te1-ac2b9f1c`; the server log shows the seen mark (`200`), the setting's version 2
  (`201`) and the allocation freed (`200`). Raised at the check:
  - Step 11: from Alerts, an allocation's page went back to Allocations, not to Alerts. Corrected: every page a reminder
    links to - the machine, the Work Order, the allocation - offers "Back to Alerts", to the list as it was (its
    filters in the address; `alertsPageHref`, `alertFiltersFromSearch`, tested; the E2E spec follows the link back).
  - Step 3: fitness and a permit listed as missing for a machine with no registration recorded - ELG-1's cautious
    reading. **The owner's decision: no registration recorded is not a transport vehicle**, in this package, with one
    review round (design section 1.5, refinement 12). Built: `evaluation.is_transport` and the shared
    `registrations_in_force`; six ELG-1 tests rewritten to it (the four on a registration's mark now on a transport
    registration that has run out, the one case a mark still decides), one ELG-1 route test and one ELG-2 test.
  - "Mark as seen" for Management (Read Only). **The owner's decision: kept** (ELG-1 Q17; design section 1.5).
- After the owner's decisions (the change of rule, Back to Alerts) and review round 6 (design section 16): full backend
  regression on `866ceb3` - no backend file changed after it - run alone: **2794 passed, 0 failed**, in 74 minutes.
  Backend restarted on the final code, then the full E2E with `pwsh` on `829f23e`: **33 passed, 9 skipped, 0 failed**,
  exit 0, the spec following "Back to Alerts"; cleanup removed the run's "seen" mark, none left. Frontend 458 tests,
  typecheck and build clean.
- **The owner's short re-check, 2 October 2026: "all pass"** (run `te1-2dd7daf0` on `b6b04ae`; the server log shows the
  seen mark, `200`). Asked at it, and done now: above the list, a filter's share of all the reminders (refinement 14;
  `shownOfText`, tested; the E2E spec checks "3 of the N", then "2 of the N-1" after marking one seen, and after
  Refresh). Frontend 460 tests, typecheck and build clean. Full E2E with `pwsh`: 33 passed, 9 skipped, 0 failed, exit 0;
  cleanup removed the run's "seen" mark.
- `main` merged in (`e2a60ab`: the 8A keep-held-days fix, PRs #81 and #82), per the owner's merge order; the conflicts
  as `main`'s note foresaw. On the combined tree: ELG-2's, ELG-1's evaluation and 8A's suites 319 passed, 0 failed;
  frontend typecheck clean, 462 tests, build clean; backend restarted, full E2E 33 passed, 9 skipped, 0 failed. The
  full backend regression on the combined tree is the pull request's `Backend regression` check.

## TB-1 correction, 5 October 2026 - Sign out leaves no token in the tab (TB1-802)

- [x] `alertsState.test.ts`: the kept count holds a fingerprint, never the token or any part of it; a copy in the
  earlier form, with the token, is never read back. `sessionAlertCount.test.ts`: the copy is removed, quietly when the
  browser refuses its storage, and Sign out and the shared session clearing both remove it. All five tests fail without
  the change.
- Screen check (browser developer tools). Test user `ops1` (Operations), starting URL `/`: once the menu shows the
  Alerts count, Application > Session storage > `pbl_alert_count` holds `session` (a short code), `unseen` and `at` - no
  token. Sign out: the `pbl_alert_count` entry is gone. Sign in again: the count appears as before.
