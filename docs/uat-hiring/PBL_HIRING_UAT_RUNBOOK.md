# PBL Hiring User Test - Runbook

For whoever runs the Hiring user test, **not for testers**: what the site starts with, the handovers to watch, and
resetting. The site itself - deploying, accounts, backups - is run from PBL's own hosting runbook, which is not part
of this copy.

The data is invented for the same reasons as the CRM test's ([`docs/uat/PBL_CRM_UAT_RUNBOOK.md`](../uat/PBL_CRM_UAT_RUNBOOK.md)):
no real customer, machine, registration, chassis, engine, PAN, insurance or certificate number (owner's test-data rule,
25 September 2026), and it can be removed completely.

## What the site starts with

Scenario `hiring-uat-fleet` (owner's decision, 9 October 2026: only the fleet and the holiday calendar), loaded once on
the empty database. Every date counts from the day it was loaded ("day 0").

**The fleet** - the first round's invented machines, unchanged, from one invented Plum report, confirmed:

| Machine | Shows |
| --- | --- |
| UAT-CC250-01, 03 | 250 t crawlers: road papers "not applicable", examinations in date - can be allocated |
| UAT-CC250-02, 04 | Examination runs out about 15 and 13 days after day 0 - a warning for a job running past it |
| UAT-CC250-05 | A registration saying transport wins over its "not applicable" marks: fitness and permit missing - cannot |
| UAT-CC250-06 | Nothing recorded, added 15 days before day 0: "not yet recorded" has reached Admin, Operations and Management |
| UAT-AC100-01 (+ carrier 01C) | Non-transport; road papers on its fitted carrier - can be allocated anywhere |
| UAT-AC100-02 | Transport, permit for Maharashtra only - cannot in Gujarat |
| UAT-AC100-03 | Transport, all-India permit - can be allocated anywhere |
| UAT-AC100-04 | Transport, no fitness, no permit - cannot |
| UAT-AC100-05 | Insurance recorded without its copy - cannot |
| UAT-AC100-06 | First-year PUC marked not applicable until day 25 - a warning for a job past it |
| UAT-AC100-07 | Insurance ends day 20; the renewal from day 21 has no copy - a warning |
| UAT-AC100-08 | Nothing recorded, added 8 days before: reached Admin and Operations |
| UAT-AC100-09 | Nothing recorded, added on day 0: Admin only. Tester 2 records its papers |
| UAT-CC80-01 | Papers running out on days 20, 10 and 5, load test run out: every reminder stage at once |
| UAT-CC80-02 | Insurance runs out on day 6 |
| UAT-XC60-01 | Plum model name not mapped: no type until Tester 2 maps it and confirms the second report |

Tester data: names `T1-` (Sales) and `T2-` (Fleet Admin); PAN and GST numbers `ZZZZH1...` - the CRM pack uses
`ZZZZM...`, so the two packs never share a number; own data `OWN-`, numbers `ZZZZQ1...`.

Kit, held for the 250 t crawlers: two hook blocks (EQ-000020, and EQ-000021 examined 7 months ago - fine), a set of 12
counterweights (EQ-000022), two boom inserts (EQ-000023, 24), two 20 t slings (EQ-000025, and EQ-000026 examined 7
months ago - cannot go); and an 8 t sling for the 80 t crawlers (EQ-000027).

**PBL's holiday calendar** for this year and next, both marked complete: Republic Day, Independence Day and Gandhi
Jayanti for all of India; Holi, Diwali and Christmas as festival holidays; Gujarat Day (Gujarat) and Maharashtra Day
(Maharashtra) on 1 May. It is a practice calendar, not PBL's own.

**No state or central-government rule is loaded**: none is law PBL has adopted (ELG-1). Tester 2 adds a test rule four
months ahead and ends it.

Tester 2 uploads `PBL_HIRING_UAT_PLUM_REPORT_2.csv`: the same machines and UAT-AC100-10 (with its carrier), UAT-CC250-07
(capacity written "250 T").

## The handovers to watch

| From | To | What | Sheet steps |
| --- | --- | --- | --- |
| Tester 1 | Tester 3 | The first Work Order, its sites, contract and terms | T1 5 to 12, T3 3 to 7 |
| Tester 1 | Tester 3 | The second Work Order, at a central-government site | T1 13, T3 9 to 11 |
| Tester 3 | Tester 2 | UAT-CC250-02 allocated with a warning; its new examination; **Check again** | T3 4 and 8, T2 9 |
| Tester 3 | Tester 2 | The kit finished; then two more boom inserts | T3 6, T2 14 |
| Tester 1 | Tester 2 | The first Work Order's contract; then a Gujarat holiday added to next year's calendar | T1 8, T2 15 |
| Tester 1, 3 | Tester 4 | Terms, holidays and machines to read | T4 4 to 11 |

## Resetting

**Usually: restore the handover backup** - the one taken right after loading (PBL's hosting runbook, not part of this copy).
It puts back the fleet, the calendar and the accounts as handed over, and testers keep
their passwords. But **the dates do not move back**: the machines' papers were dated from day 0, so after a restore
they are as many days older as have passed. For a fresh day 0, repeat PBL's reset steps (not part of this copy) for
the Hiring site alone.

On a machine of your own: the scenario seeds only into a database with no machine, no waiting Plum report preview and
neither calendar year started, and `python -m tooling.smoke_data cleanup --run-id <id>` removes everything it made.
Prefer a rebuild (`docker compose down -v`) where nothing else lives in the database.

The first round's scenario, `hiring-uat-seeded` - four customers with Work Orders, allocations and every reminder
stage - still exists; the user guide's pictures are taken on it.

## The user guide's pictures

Retaken with `e2e/guide/` (its config file says how), on a fresh stack seeded with `hiring-uat-seeded`. They show
screens, so retake them when a screen in them changes; then copy them to `images/` and regenerate the guide's PDF. The
names in them (`UAT-H ...`) are the first round's; the testers' own are `T1-...`. The guide says so.
