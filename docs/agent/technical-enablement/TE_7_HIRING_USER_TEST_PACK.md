# TE-7 - The Hiring User Test Pack

## Status

Built 2 October 2026 on `hiring/uat-pack` (worktree `pbl-crm-hiring-huat`), after ELG-2 merged (PR #83, `af0f75c`).
No migration, API, permission or business-rule change. Merged only on the owner's word, after `Required validation`.
The server steps - setting up the second site, accounts, loading the data - are the owner's: there is no server access
from the development machine.

## What it is for

The owner's brief (2 October 2026), for the Hiring user test, "one thing done differently from last time":

1. **A user guide first**, with seeded data, making the whole flow up to equipment allocation and alerting clear.
2. **Buttons some roles see and others do not**, highlighted for both, with where each appears.
3. **The regulatory rules illustrated with examples** - why a state is asked (Gujarat and Maharashtra differ), why a
   central-government site is declared.
4. **Test data covering scenarios beyond the obvious.**
5. **The menu items and their sequence**, with the buttons on each.
6. **Not too long or verbose.**

And, as for the CRM pilot: a tester guide, a sheet per role, a feedback log.

## Owner decisions, 2 October 2026

| Question | Answer |
| --- | --- |
| Machines in the practice data | Invented, not from Plum's real report |
| Where the test runs | **A separate site with its own logins**: a separate Hiring test site. The owner added the DNS record |
| Logins | `hire-fleet-01` (Admin), `hire-ops-01` and `hire-ops-02` (Operations), `hire-sales-01` (Sales), `hire-finance-01` (Accounts), `hire-md-01` (Management) |
| Screenshots in the guide | Yes |
| Four stale or missing screen texts found while writing the guide | Fixed in this package |
| Holidays when a Work Order names none | PBL sets a default calendar yearly; every Work Order inherits it and varies it. Recorded in `docs/agent/DEFERRED_REQUIREMENTS.md`, "PBL's default holiday calendar"; nothing built changes |
| The guide | Reviewed by the owner before the sheets were written |

## What changed

**The hosted sites (`deploy/uat/`).** The same files now run two sites. `bin/site.sh` names the site from the folder
the script is in (`/home/projects/<site>/bin`, or a release's `deploy/uat/bin` under it), and every container, image,
volume, network, router, backup and log tag carries that name; the compose file takes `UAT_SITE` and `UAT_HOST` from
`bin/compose.sh`. Nothing in the environment can change the site: `CRM_UAT_STACK_DIR` (which named the folder when
there was one site, for the tests) or `UAT_SITE` naming another site is refused, so a script of one site cannot be
pointed at the other, a restore included (independent review, round 1); the tests run copies of the scripts from
site-shaped folders instead. The CRM pilot's compose file renders exactly as before. `cron/crm-uat-hiring` runs the Hiring site's
backup and health check 30 and 5 minutes after the pilot's. `scripts/tests/test_uat_deploy_scripts.py` runs every
script test for both sites, and checks that every name is the site's own.

**The screens.** Four texts that still said allocation was "not built yet" (Work Orders list, a Work Order's access
line and "later steps", Resource Planning, Dashboard); a machine's *Events* card that showed "No events" to a role not
allowed to see events now says so; Alerts in the Equipment pages' own menu, and that menu on the Alerts page; and the
"central government site" box on a machine's *Check for a site*, which listed "a port" and no metro, now says what
the Work Order line says.

**The practice data**: scenario `hiring-uat-seeded` (`backend/tooling/smoke_data/hiring_uat.py`), with five new
builders (kit on a trip, replace, free, a further trip, and dating a machine's arrival). What it holds, record by
record and machine by machine, is in `docs/uat-hiring/PBL_HIRING_UAT_RUNBOOK.md`. It seeds only on an empty fleet,
like the other equipment scenarios.

**The pack, `docs/uat-hiring/`**: the user guide (with its pictures, taken by `e2e/guide/`, a capture run on purpose
and not part of the regression suite), the tester guide, Sheet 1, four Sheet 2s, Sheet 3, the feedback log and form,
the second Plum report the Fleet Admin uploads, the README (who gets what) and the runbook. Every sheet has its PDF;
`scripts/render_uat_sheet_pdfs.py` renders them, now with pictures and per folder. The second site's setup is in
`docs/deployment/CRM_UAT_VPS_RUNBOOK.md`, "The second site".

## Choices made, and deviations

- **Machines dated as added 8 and 15 days ago.** "A certificate not yet recorded" escalates by how long a machine has
  been in the fleet, so a fleet loaded today would show only the first stage on the first day. The harness moves two
  machines' `created_at` back with one `UPDATE` (`date_equipment_assets_added`) - the one place the seed writes a row
  directly rather than through a service. Adding an "added on" input to the service for test data would put a field
  in production that no real user should have.
- **No state or central-government rule seeded.** None is law PBL has adopted (ELG-1). The Fleet Admin's sheet adds a
  Gujarat rule that starts four months ahead, checks a crane in Gujarat against Maharashtra, and ends it - so nothing
  anyone else sees changes.
- **The sites say what they are.** The metro works answer "Yes" to "Central-government site?" (the screen's own hint
  names a metro), and the other sites' names say "not a major port", "private", so a tester applying the guide's rule
  reaches the practice data's answer.
- **A model name mapped takes effect at the next confirmed report.** The Fleet Admin's sheet therefore maps the
  unknown name inside the second report's preview, before confirming, and the sheets say so.
- **Pictures cut from a full-page capture.** Playwright's element screenshot lost the foot of a card about a viewport
  tall; `e2e/guide/hiring-guide.capture.ts` crops a full-page picture instead.
- **The second report's file is pinned to LF** (`.gitattributes`): cleanup finds the upload by the report's SHA-256.
- **The guide is a PDF**, not also an HTML page and a published web page as the CRM guide was: it carries pictures, and
  one form is one thing to keep in step.

## Verification

On a worktree stack (PostgreSQL 17, Alembic head `20260908_0046`, no migration in the package):

- **Backend:** full regression 2804 passed, 0 failed (57 min, alone, on an empty database). After the review
  corrections, `test_hiring_uat_smoke_data.py`, the empty-fleet refusal test (now over three scenarios) and the
  harness tests were rerun and pass. The practice data's test proves each answer, kit choice, reminder stage and site
  answer the sheets rely on, and that cleanup leaves every table - business events included - exactly as before.
- **Frontend:** typecheck clean, 462 tests, build clean.
- **Playwright:** 33 passed, 9 skipped, 0 failed, retries 0 - the same counts as before the package.
- **Deploy scripts:** every script test runs for both sites, in a Linux container (the git-based two on Windows);
  the CRM pilot's compose file rendered identically before and after.
- **Contract fixtures and tracked secrets** clean. **Frozen handoff contract** hash unchanged:
  `70debad711eea67f5e8f0ff3a945c7431235ddfd97b34330beb390215cb0b86a`.
- **The sheets, tried:** on a fresh stack seeded with the scenario alone, through the services - Operations 1's
  allocation with a warning and its replacement; the copy attached to UAT-AC100-07's renewal; Sales' offer accepted,
  WO-000004 made, its requirement allocated UAT-CC250-04 with a warning, cleared by a new examination and **Check
  again**; the second report's preview before and after mapping; the future Gujarat rule's effect.

**Independent review (the independent reviewer).** Round 1: one blocking finding - a test-only setting let a script of one site act
on the other - and two material: the owner's untracked `Send to team` folder, swept into the reviewed tree, held an
older PDF (left out of the package, the owner told); and cleanup's test did not count business events (it now does;
the eight events it found at first were the test's own sign-ins). Round 2: four material findings - the dating of
two machines ran as two UPDATEs (now one); the Fleet Admin's and Operations' sheets gave different results in
different orders (the Fleet Admin now waits where it matters, and Operations has the other outcome too); the Sales
sheet promised a mapped name was enough (a confirmed report is needed); and the guide ran together how a
certificate's and a job's reminders end. Each corrected. Round 3: one blocking finding - an inherited
`COMPOSE_PROJECT_NAME` outranks the compose file's own name, so it could have pointed a Hiring-site restore at the CRM
pilot's containers (true of the pilot's scripts before this package too) - and one material: the Alerts page's own
subtitle said every reminder lasts until the certificate is dealt with. `compose.sh` now names the project itself and
`site.sh` refuses a `COMPOSE_PROJECT_NAME` of another site (three new tests, each failing without the change); the
subtitle says what the guide says, and the guide's Alerts picture was retaken. Three rounds is the owner's limit; the
owner agreed a fourth. Round 4: two material findings - the Alerts subtitle still left out that a renewal counts only
with its copy, and the "not applicable" and retired cases (it now names all four); and the cleanup test compared only
row counts. It now compares every in-scope table's whole contents (a digest of every row's every value) and the
document store's files with their digests, around an unrelated Account and stored file that cleanup must leave as
they are. A scratch cleanup that reported the copies' files deleted while keeping them made only the document store
differ, so the test catches it; cleanup's own after-check already refuses when a deletion visibly fails. The owner
chose to open the pull request after round 4's corrections, without a fifth round (2 October 2026).

**CI on the pull request** found two steps of "Secret and dependency checks" not run locally: ShellCheck, which could
not follow the scripts' shared `site.sh` (now `deploy/uat/.shellcheckrc`), and the hosted compose template's
validation, which needs the site's name `compose.sh` supplies (the workflow now validates it for both sites). Both
pass locally as CI runs them.
