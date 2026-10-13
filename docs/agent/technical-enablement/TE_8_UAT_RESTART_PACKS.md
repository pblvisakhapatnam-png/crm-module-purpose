# TE-8 - The user-test restart: both packs rebuilt, the sites' reset

## Status

Built from 9 October 2026 on `uat/restart-packs-oct-2026` (worktree `pbl-crm-hiring-uatr`), from `main` at `f0eb393`.
Merged only on the owner's word: the owner reviews the packs before sending them. Up to three independent review rounds. The
reset itself is the owner's, on the VPS: there is no server access from the development machine.

Parts of three sheets waited for packages built at the same time, marked where they stood (`<!-- WAITS: ... -->`):
CS-05a (a stale save refused), Slice 7D Part 5 (the crew's food, accommodation and travel; the shift pattern) and the
submitted-offer lock (a submitted offer changed only by a revision; one live Base Offer; clear double-click messages).
The packs describe only what is on `main`; each waiting step is finished once its package merges.

- **CS-05a** merged on 9 October 2026 (PR #116): CRM Tester 2's step 9 now checks it, with its own messages - two
  tabs on the offer and on a line, the second save refused beside its button. The CRM guide tells testers not to edit
  a customer, Lead, enquiry, amendment or conversation in two tabs at once: those wait for CS-05b.
- **Slice 7D Part 5** merged on 10 October 2026 (PR #118). A line's terms are now complete only with its shifts and,
  where the order states a crew, the crew's food, accommodation and travel answered, so all three of the Hiring Sales
  tester's terms tables answer them: line 1 in its own step (10), which first checks that only those two are missing;
  lines 2 and the day line in their tables. A dry run on the routes (sales1, a development stack at `20260908_0052`)
  gave line 1 missing exactly `SHIFTS` and `CREW_UPKEEP`, then complete; lines 2 and 3 complete. The User Guide and the
  Accounts sheet describe the new cards.
- **The submitted-offer lock (CS-05c)** merged on 10 October 2026 (PR #119). CRM Tester 1's step 19 checks a sent offer's
  forms give way to its note, step 22 changes a rate inside the revised offer, step 23 sees the note return once it is
  re-sent; Tester 2's step 10 saves a new offer from two tabs on a spare enquiry (the second refused, naming the first)
  and double-clicks a T&C clause (attached once). Tester 3's basis-rate check says what to expect once Tester 1 has sent
  the offer; the CRM guide says a sent offer is settled. No step waits any more.
- **Slice 9F (offer versions)** merged on 11 October 2026 (PR #120, `cfa11d7`, migration `20260908_0054`) and replaced
  the lock's revised offer: a sent version is frozen, and a change is a new version, copied. The branch merged `main`
  and the CRM pack now describes it. Tester 1's step 19 reads the new note and the code `CO-... v1`; step 21 records
  the customer's request, then **Make a new version** (*Reason* `Rate correction`); step 22 changes line 3's rate on
  v2 while v1 keeps the old one; step 23 generates v2's quotation (`CO-... v2/V1`), has it approved, records v2's own
  submission evidence and **Record as Submitted / Commercially Committed**, after which v1 reads "Replaced by v2";
  steps 24 and 26 record the yes and hand over on v2. Tester 2's step 2 approves v2's quotation, Tester 3's step 7 opens
  v2 to make the Work Order, and the CRM guide's offer section, status table and route describe versions. The wording
  was checked against the code on `main` - the page's own messages and labels - and the steps were run on a development
  stack at `20260908_0054`, through the API as `sales1`, `manager1` and `ops1`, from smoke-data's `revision-requested`
  (a sent offer with the customer's request recorded): 28 of 28 checks matched the sheets. v2 was made as a Draft with
  the same code; its rate changed while v1 kept its own and refused a change; its quotation read `CO-... v2/V1`, which
  Sales could not approve and the manager did; v1's evidence was not copied; v2 was recorded as sent without a warning,
  so the copied credit review counts; v1 then read replaced by v2 and refused a reply; the yes on v2 made it ready for
  its Work Order, which Operations made, and a second was refused. The seeded offer had no market rates, so their copy
  rests on 9F's own test (`test_slice_9f_commercial_offer_versions.py`, the selected basis copied). Both runs were
  cleaned up by the harness, versions and Work Order included. The step numbers are unchanged; two step titles changed and
  the CRM Feedback Log was rebuilt.
- **The commit to deploy** is `main` once this package merges - it carries the Hiring site's loading step - so the
  reset steps find it with `git log --grep='Merge pull request #117 '` rather than naming it.
- *Changed 11 October 2026 (Slice 4G, PR #121):* the sites now get market rates per offer line too, and the CRM sheets
  were rewritten for it, so the reset steps find `Merge pull request #121 ` instead. #121 merges after #117, so it
  carries everything above.

## Why

In the first round a single tester did every test, randomly mixing the data he was given with his own. The owner
decided on 9 October 2026:

| Question | Answer |
| --- | --- |
| What is kept | Nothing. Both sites are cleared completely; fresh data for testers to enter; fresh walk-throughs; no "what changed" notes |
| Testers | 3 or 4 a site, as in the first pilot: one job and one set of data each, named so they cannot collide (`T1-`, `T2-`); plus a fixed route when one person does everything |
| Their own data | A separate last part, only after the sheets, every name `OWN-` |
| What is pre-loaded | CRM: nothing but the sign-ins. Hiring: only the fleet (invented machines with their certificates) and the holiday calendar |
| Sign-ins | The same accounts and passwords on both sites, re-created after the wipe from the server's root-only password file, never printed |
| Results | Each tester records Pass or Fail per step in the Feedback Log |

## What changed

**A pre-load scenario, `hiring-uat-fleet`** (`backend/tooling/smoke_data/hiring_uat.py`): `hiring-uat-seeded`'s fleet -
the same machines, papers and kit, from the same invented Plum report - and PBL's holiday calendar for this year and
the next, marked complete: the fixed national holidays, Gujarat Day and Maharashtra Day for their states, and Holi and
Diwali for 2026 and 2027. No customer, offer, Work Order, requirement or allocation. It refuses, writing nothing, where
a machine or a waiting Plum preview is held (the empty-fleet guard, now tested for it too) or where either calendar
year is already started; cleanup removes the years by provenance with the run's machines.
`backend/tests/test_hiring_uat_fleet_smoke_data.py` pins what the sheets rely on: each machine's answer for the sites
the sheets use, the reminder stages on day 0, that nothing else is seeded, and that cleanup leaves every table as it
found it (`hiring-uat-seeded`'s whole-table digest).

**The CRM pack (`docs/uat/`)**, rewritten for an empty site: the Tester Guide (now a PDF made from its Markdown, like
every sheet), one sheet per tester - Sales Executive, Sales Manager, Operations, Accounts - the one-person route, the
own-data part, the Feedback Log, the README and the runbook. Removed: the seeded-data review, the numbered copies of the
data sheet and their master (`docs/uat-source/`), the Operations and Finance sheets they replace, the hand-built guide
page, and `scripts/render_uat_tester_sheets.py` with its test.

**The Hiring pack (`docs/uat-hiring/`)**, rewritten for a site with only the fleet and the calendar: the User Guide
(holiday calendar, the Work Order's holidays, the Create Work Order form, current labels; the starting data), the
Tester Guide, one sheet per tester - Sales, Fleet Admin, Operations, Accounts - the one-person route, the own-data part,
the Feedback Log, the README and the runbook. The Sales tester now makes the customer, offer and two Work Orders that
the others work on.

**The Feedback Logs** are built by `scripts/build_uat_feedback_logs.py` from the sheets' step headings: a tab per
tester (Step, Result - Pass, Fail, Could not try, Not done - Findings row, Notes), one for own data, Findings and a
Summary. `scripts/tests/test_uat_tester_sheets.py` (standard library; CI step "Check the user-test packs' tester
sheets", replacing TE-5's) checks every PAN and GST number against the Account service's own patterns and the tester's
digit, that no two testers share a GST number, that a sheet names only records another sheet makes, that every link
leads somewhere, and that each log lists its sheets' steps exactly.

**The reset steps**, `docs/deployment/UAT_RESET_2026-10_STEPS.md`: one command at a time, each with what it should
print - a safety backup of both sites, clearing each site's two volumes, deploying the agreed commit, the sign-ins
re-created from the CRM site's password file through a pipe, the Hiring pre-load, the handover backups, and the health
checks. `CRM_UAT_VPS_RUNBOOK.md` points to it.

## Choices made, and the owner's answers (10 October 2026)

The owner agreed the logins and keeping one site login per site. The GST point is not a decision: it is the known,
deferred limitation `DEFERRED_REQUIREMENTS.md` records under Slice 7C (a GSTIN's state is fixed when it is added,
until SurePass or the audited manual route ADR-015 permits), and the sheets treat it as such.


- **Logins.** The CRM site's six accounts on both sites, with their passwords, and one new: `uat-fleet-01`, an Admin
  login for the Hiring site's Fleet Admin, created on both sites for "the same accounts". The six `hire-...` accounts
  of the first Hiring round are not re-created. Tester slots: CRM 1 Sales Executive (`uat-sales-01`), 2 Sales Manager
  (`uat-manager-01`), 3 Operations (`uat-operations-01`), 4 Accounts (`uat-finance-01`); Hiring 1 Sales, 2 Fleet Admin
  (`uat-fleet-01`), 3 Operations, 4 Accounts. `uat-sales-02` is a spare. No Management (read only) login on either
  site; Management's reminder path is therefore not seen by a tester.
- **The site logins** (the browser box) stay one per site; only the application sign-ins are shared.
- **A GST number entered by Sales cannot be marked Verified afterwards**: no route changes a GSTIN once added. The
  Accounts sheet asks the tester to find this out and say how it should work, rather than promising a step the system
  does not have.
- **The pictures** in the Hiring User Guide stay those of the first round's practice data (`hiring-uat-seeded`), whose
  names differ from the testers'; the guide says so. They are retaken once, after the waiting packages merge.
- **The CRM guide's hand-built page and its published copy** are retired: one source, the Markdown, and its PDF.

## Verification

On a port-free worktree stack (PostgreSQL 17, Alembic head `20260908_0050`):

- `tests/test_hiring_uat_fleet_smoke_data.py`, `tests/test_ert1_smoke_data.py` and `tests/test_hiring_uat_smoke_data.py`,
  whole: 21 passed, 1 skipped (the docs-mounted report check). With the scenario's complete mark and its calendar
  guard taken out, the two new seeding tests failed - and the broken refusal leaked a run, which is why the refusal
  test cleans up whatever a broken refusal seeds.
- The reset's account steps, rehearsed on the same stack: accounts created into a scratch password file, the database
  wiped, the same accounts created again from the file through `pw <user> | ... create --password-stdin` - nothing
  printed, the re-created account signed in (200) - into the second site's file too; a missing username refused with
  "No password on standard input", creating nothing. The seed's output and its refusal on a second run are as the steps
  quote them. The health check's query printed `8|0|0|27|2026:true,2027:true` there - six demo users and two test
  accounts on a development database; a site has the seven accounts and the seed's two switched-off authors, so 9.
- `python -m unittest scripts.tests.test_uat_tester_sheets`: 6 passed.
- No local full regression or Playwright (CI runs both).

## Independent review

the independent reviewer, one bounded packet a round, up to three rounds (the owner's cap).

**Round 1** (commit `9f1e394`, packet SHA-256 `1fa320d7...`): `CORRECTION_REQUIRED`, eight material findings, all
accepted and corrected.

- **TE8-R1-001** - the calendar refusal came after `run_scenario` had resolved, and on a site created, the actor.
  The guard now runs in `run_scenario` before the actor; the refusal test fails if the actor is resolved first.
- **TE8-R1-002** - cleanup leaves the switched-off authors a run writes as (`sales1`, `admin1`), and the test's
  snapshot leaves out the accounts. The claim is narrowed: they are every site scenario's authors, hold none of the
  run's data and cannot sign in; the docstrings and this record say so.
- **TE8-R1-003** - seeding is not one transaction, so a failure part-way leaves data with no manifest. The reset steps
  now say how to clear the Hiring site and load again after any failure other than the two refusals.
- **TE8-R1-004** - the calendar test compared the stored rows with the function that seeded them. It now writes the
  expected holidays out itself.
- **TE8-R1-005** - two waiting steps were partly executable. Each is split: the part `main` has, and a waiting step
  recorded wholly "Not done". Later steps, routes, runbooks and logs renumbered.
- **TE8-R1-006** - Operations' machine lists missed the two machines Plum's second report adds; they are listed.
- **TE8-R1-007** - the two packs shared PAN and GST numbers, and the Fleet Admin's model had no prefix. The Hiring
  pack has its own block (`ZZZZH`, own data `ZZZZQ`), the model is `T2-XC 60 T`, and the sheet test checks numbers
  across both packs and every record-naming value's prefix.
- **TE8-R1-008** - the CRM guide said Accounts verifies GST numbers; it can only choose that when adding one.

**Round 2** (commit `0990f5b`, packet SHA-256 `0a7c326c...`, with CS-05a and Slice 7D Part 5 written in):
`CORRECTION_REQUIRED`, six material findings, all accepted and corrected. Round 1's corrections were not questioned.

- **TE8-R2-001** - a site still open to testers could write between the backup's database dump and its documents
  archive. The reset steps now stop each site's page server first, and have the owner check the restore check's counts
  equal the live ones.
- **TE8-R2-002** - CRM Tester 2 recorded quotation version 2 as sent after step 9 had made version 3; it records `V3`.
- **TE8-R2-003** - Tester 4's opening and the README still said Accounts verifies GST numbers; corrected as in round 1.
- **TE8-R2-004** - a Work Order holiday's name began `T1 ` rather than `T1-`, and the sheet test did not look at that
  field; both corrected.
- **TE8-R2-005** - the Hiring Sales sheet counted from "today" while the others count from the load date. Every Hiring
  sheet now counts from the load date, which the owner writes down and gives the testers.
- **TE8-R2-006** - the one-person routes left the own-data block to "any one login", some of which cannot do every
  step. They name `uat-manager-01` (CRM) and `uat-fleet-01` (Hiring).

**Round 3** (commit `4d04123`, packet SHA-256 `78e4fdf4...`, the whole package with CS-05c written in), the last of the
owner's three: `CORRECTION_REQUIRED`, six material findings, all accepted and corrected. Rounds 1 and 2's corrections
were not questioned. No fourth round without the owner.

- **TE8-R3-001** - the restore check compares counts, not which documents. The reset steps now compare the exact list
  of stored-document keys the database names with the files in each backup's archive (`diff`, expecting
  "documents match"), for the safety and the handover backups. Rehearsed on the worktree stack: 72 keys, all with their
  files; the 79 files left there by earlier test runs, which no record names, were listed as `>` lines.
- **TE8-R3-002** - a failure in step 1 left both sites closed while the failure section said nothing had changed. It now
  says so, and gives the commands to reopen them.
- **TE8-R3-003** - the handover backups were taken with the sites open and not checked. The sites now stay closed from
  the deployment until both handover backups pass the restore check and the documents check; step 6 opens them.
- **TE8-R3-004** - the empty-fleet refusal was tested against a few tables only. A new test refuses with a waiting
  preview and then a held machine, fails if the scenario reaches the actor or the calendar guard, and counts users,
  roles, calendar rows, events and equipment. Undo check: with the empty-fleet guard taken out, it fails.
- **TE8-R3-005** - Tester 1's contact names had no prefix; they are `T1-...`, and the sheet test counts "Contact name".
- **TE8-R3-006** - restoring a step-1 backup would bring back the old passwords while the password file kept the new
  ones. Step 1 now copies each site's password file, and the rollback puts it back.

