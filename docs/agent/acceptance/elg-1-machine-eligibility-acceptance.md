# ELG-1 Acceptance - Machine eligibility

Design and implementation record: `docs/agent/slices/elg-1-machine-eligibility.md` (section 20). API:
`docs/agent/contracts/eligibility-api-contract.md`. Continuity: `docs/continuity/ELG_1_MACHINE_ELIGIBILITY.md`.

## Preconditions

- The stack at migration head `20260908_0044` (`docker compose exec backend alembic current`). `alembic/` is
  baked into the backend image: after switching to this branch, `docker compose up -d --build
  --force-recreate backend`, and rebuild the frontend (`docker compose up -d --build --no-deps frontend`).
- Test users: `admin1` (Admin - the Fleet Admin until that role exists; holds `EQUIPMENT_REFERENCE_MANAGE`,
  `EQUIPMENT_IDENTITY_READ` and `ELIGIBILITY_RULE_MANAGE`), `readonly1` (Management Read Only) for the
  permission check. Password as documented for the prototype seed users.
- Seed the screen-check data on a database with no equipment machine and no waiting report preview:
  `docker compose exec backend python -m tooling.smoke_data seed --scenario equipment-plum-import --json`, and
  save the manifest. Its `equipment_eligibility` block names the machines below.
- Have a small PDF at hand to attach as a certificate's copy (any PDF; it is a test copy).
- Clean up afterwards: `docker compose exec backend python -m tooling.smoke_data cleanup --run-id <run id>`. It
  removes the run's certificates, marks and copies with their stored files - those recorded on screen
  included - and refuses, deleting nothing, when a stored decision about a machine the run did not bring in
  used one of its machines. A rule added on screen is the platform's and stays: end it (step 8).

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| The decision, pure: rule choice, cover, renewals, withdrawals, marks, transport, permits, outcomes, bands | `docker compose exec backend pytest tests/test_elg1_evaluation.py -q` | 61 passed |
| Through the routes and at the database: reference lists, the seeded rules, certificates, copies, marks, the check, `record_decision`, Certificates due, rules, permissions, numbers withheld, events | `docker compose exec backend pytest tests/test_elg1_machine_eligibility_api.py -q` | 59 passed |
| The harness: the seeded certificates and their cleanup, the refusal | `docker compose exec backend pytest tests/test_elg1_smoke_data.py tests/test_ert1_smoke_data.py -q` | 17 passed |
| Documents: the pinned type list and the attach rules | `docker compose exec backend pytest tests/test_document_upload_rights.py -q` | all pass |
| Route guard and permission catalogue (the 12 routes pinned) | `docker compose exec backend pytest tests/test_authorization_route_migration_guard.py tests/test_authorization_post_baseline_catalogue.py tests/test_authorization_compatibility_matrix.py -q` | all pass |
| Full backend regression, run alone | `docker compose exec backend pytest -q` | 0 failed; see Results |
| Migration: empty database to head, `downgrade -1`, head again | a scratch database inside the running Postgres | reaches `20260908_0044`; see Results |
| Frontend typecheck, tests, build | the `AGENTS.md` sequence (prefix `MSYS_NO_PATHCONV=1` in Git Bash) | clean; 378 tests (352 before), measured on the round-6 corrections; two routes added |
| Full E2E suite | `pwsh -NoProfile -File scripts/run-e2e.ps1` | see Results; `equipment-certificates.spec.ts` adds four tests. **Run it with `pwsh`, not `powershell`** |
| Committed-credential and fixture checks | `python scripts/check_tracked_secrets.py`, `python scripts/validate_contract_fixtures.py` | clean |

## Test data

- Every machine, model and number is invented and carries a run-unique token.
- The scenario `equipment-plum-import` (and the core bundle's seventh record set) adds, beside ERT-1's and
  ERT-2's records:
  - **`TEST-<token>-WC1`**, an all-terrain crane (ACME AC 250 <token>), with its carrier **`-WC1C`** fitted when
    the first report is confirmed. On the carrier: registration (non-transport, to 12 years from 3 years
    ago), insurance (to 334 days ahead), pollution certificate (to 150 days ahead) and a one-time road tax; on
    the crane: a thorough examination 60 days old. Each with a copy. **No load test**, so it cannot be
    allocated yet.
  - **`-KC2`**, the second crawler crane of ERT-2's CC 100: registration, insurance, pollution certificate and
    road tax marked not applicable ("Crawler crane: not equipped to travel on public roads ...").
  - **`-KC1`**, the first crawler crane: nothing recorded - for step 4.
  - A **sling** held for the CC 100 cranes (LIFTCO Sling 10 t <token>), examined and load tested 150 days ago:
    slings are examined every 6 months, so its examination runs out in about a month.
- `-CR1` (ERT-1's all-terrain crane; its carrier comes only with the second report) and `-CR2` (whose model is
  not mapped) have nothing recorded.

## Manual happy path

Sign in as `admin1`. Start at **Equipment** in the sidebar (`/equipment`).

1. **Certificates due** (in the Equipment links): the counts by band at the top. Type the token in "Machine
   number or reference": `-KC1`, `-CR1` and `-CR2` show every paper missing - fitness and permit too, since
   no registration says they are non-transport; `-WC1` shows only "Load test - missing"; `-KC2` only its two
   examinations; the sling "Within 60 days", its thorough examination.
2. Open `-WC1` (from Machines or the list). **Certificates**: the registration, insurance, pollution
   certificate and road tax each read "valid until ..." (the road tax "valid, with no end date") with "On its
   fitted part EQ-..." and "Attached"; the thorough examination is valid; the load test reads "missing".
   **Check for a site**: Gujarat, the dates as offered, **Check**: "Cannot be allocated", with the load test
   "missing - Stops it".
3. **Record a certificate**: Load test, a number, "Issued by" a competent person, issued on and valid from
   today, "Valid until" empty; **Record certificate**. Beside the button: "Certificate recorded. Attach its
   copy below: it counts only with its copy." The load test reads "copy missing". In **Copies of the load
   test**, choose the PDF and **Upload**: "File added: ...". The load test reads "valid until <five years
   less a day>", "Attached". **Check** again: "Can be allocated".
4. Open `-KC1`. **Mark not applicable**: Registration, a reason; **Mark not applicable**. Beside the button:
   "Marked not applicable."; the registration reads "not applicable: <reason>", and fitness and permit are
   gone - a crane that is not a motor vehicle needs neither. Back on `-WC1`, **Mark not applicable** offers
   only the pollution certificate: the law is clear for a wheeled crane. Choose it with no end date: the form
   asks for one "no later than" a day 12 months ahead.
5. Open `-CR1`. **Record a certificate**: Registration as a **Transport vehicle** (valid from a year ago to
   ten years ahead), then **Fitness** valid from a year ago until a week ago; attach a copy to each. **Check**
   for Gujarat: "Cannot be allocated" - fitness "ran out on ...", the permit "missing", as for any transport
   vehicle.
6. Open `-WC1C` (the carrier). Its page says its certificates count for the machine it is fitted to. **Record
   a certificate**: Insurance from today until ten days ahead, with its copy. Back on `-WC1`: the insurance
   reads "runs out in 10 days"; **Check**: "Can be allocated, with a warning" - "runs out on ..., during the
   period - renew it".
7. On `-WC1`, **Withdraw** that insurance with a reason: beside the form, "Withdrawn. The one before it, if
   any, is in force again."; the insurance reads "valid until" next August again, and step 6's check answer is
   gone - it was about the records before the change. **Check** again: "Can be allocated". **Earlier** lists
   the withdrawn one.
8. **Certificate rules**: "Where" Gujarat shows none; **Add a rule**: Thorough examination, Crane, every type,
   Gujarat, applies always, from today, renew every 1 month, PBL's own rule, a lapse stops the machine,
   "Never", a source; **Add rule**: "Rule added." On `-WC1`, **Check** for Gujarat: "Cannot be allocated" -
   the thorough examination "ran out", "Gujarat's rule"; for Maharashtra: "Can be allocated". Back on
   Certificate rules, **End this rule** with today's date and a reason: "Rule ended."

## Negative checks on screen

- Step 3: **Record certificate** stays disabled until the number, issuer and dates are given; an insurance
  with no "valid until", or one that runs out before it starts, is named beside the button.
- Step 4: marking `-WC1`'s registration is not offered at all; the pollution certificate's end later than
  the date named is refused beside the button.
- Step 8: a statutory rule that only warns, an examination rule with no interval, or a rule with no source,
  is named beside **Add rule**; a second rule for Gujarat from the same day is refused: "Another rule for the
  same certificate, kind of machine and place is in effect ... End it first".

## Manual permission check

Sign in as `readonly1` and open `-WC1`: the certificates show with "number shown to Admin only" and "Attached",
and no **Record a certificate**, **Mark not applicable**, **Withdraw** or **Copies** button. **Check for a site**
works. Certificates due and Certificate rules show; there is no **Add a rule** and no **End this rule**.

## Not visible on screen, checked by the automated tests

- The database's own checks: an end before the start, a missing end, "valid in" and "registered as" exactly
  where the kind needs them, a withdrawal with its reason, one mark in force per asset and kind, a mark's
  reason, overlapping rules (the exclusion constraint), a statutory rule that only warns, an interval on a
  kind that states its own end, an examination without one.
- A request key used twice has one effect; reused with any field different, it is refused; a key of only spaces
  is refused and nothing is written.
- Each asset's certificates are their own sequence: a newer record on the crane does not hide a valid one on its
  carrier. A transport registration on any asset of the unit, or one taking effect before the job starts, calls
  for fitness and a permit. Whether a registration's "not applicable" mark exempts from them is read by the
  registration rule the check uses - the site's state's - and a registration rule "only for transport vehicles"
  is refused, as is a rule for the central government's sites for anything but an examination. A registration in
  force wins over a "not applicable" mark on the registration: the mark counts only once the registration has run
  out or been withdrawn (the owner's decision, 28 September 2026).
- A mark may run as long as the most generous rule allowing one lets it - a state's longer limit included -
  and counts at a site only where that site's own rule allows it.
- A renewal takes over on its own start date, also one starting before the current certificate ends: without
  its copy, or ending sooner, it shortens the cover the check and Certificates due see.
- `record_decision` holds the module's write lock until the caller's transaction ends.
- A central-government site takes the examinations from `IN`'s rules and road papers from the state's.
- A retired piece of kit is blocked; nothing is recorded on it; a fitted part is not checked on its own.
- Only an uploaded Certificate counts as a copy: a file of another type, or a link to a file kept elsewhere, is
  refused, and an archived copy does not count. A withdrawn or unknown certificate refuses a copy; copies are read
  and downloaded only by Admin.
- `record_decision` stores the decision and its results and records `ELIGIBILITY_EVALUATED`; the screen's
  check keeps nothing. Event payloads carry no number, issuer, source or reason, and a certificate's and a mark's
  events carry fixed reasons. A mark's reasons, like a certificate's number and withdrawal reason, are shown only
  to Admin; others read "reason shown to Admin only".
- The harness cleanup removes certificates, marks, copies and stored files recorded on screen, and refuses
  when another machine's decision used a run's machine.

## Deferred, deliberately

Design section 13: reminders and escalation (ELG-2, after 8A's core); emails and messages (`NTF-001`); the
recheck job; blocking an active allocation whose certificate lapses (8A); the site's state and central
flag on a Work Order line (8A); the test after erection; approving a gap that is not the law (`APR-001`);
customers' own requirements; the spreadsheet upload (its own package, design section 18); the people half
(8B).

## Results

Recorded with the tree each was measured on, in the continuity note.

**The owner's screen check, 27 September 2026** (seeded run `te1-9c90fa66`, branch at `21121ff`): every step as
expected - "All others OK" - except that the certificates table's Copy and Change columns split their words and
buttons ("Attac hed", "Withd raw"), so the row's buttons stood at different heights. Corrected: those cells keep
their words whole on one line (`.cell-actions` in `globals.css`), and at 1440 px every row's two buttons stand
level. Two points raised are outside this package: the sign-in page and the sidebar mix "Sign in" and "Log
out" (the shared sign-in screens), and a copy can be downloaded but not viewed (`DEFERRED_REQUIREMENTS.md`,
"A document cannot be viewed without downloading it").
