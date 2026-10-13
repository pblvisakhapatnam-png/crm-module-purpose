# The Hiring user test pack - what to hand out, and to whom

Everything a Hiring tester needs, for the test site **the Hiring test site**, rebuilt for the
restart of 12 October 2026 (owner's decisions, 9 October 2026): the site starts with only the invented fleet and PBL's
holiday calendar; each tester has one job and one set of data; their own data comes last, every name starting `OWN-`;
and each step is marked Pass or Fail in the Feedback Log.

This folder is shared with the testers, so everything in it is something a tester may be given, except this README
and `PBL_HIRING_UAT_RUNBOOK.md`, which are for whoever runs the test.

| Document | Who gets it | What it is for |
| --- | --- | --- |
| `PBL_HIRING_USER_GUIDE.md` | Everyone, first | **The system:** the flow from an accepted offer to a machine allocated and its reminders; which menu, which button, who may press it; why each rule is what it is |
| `PBL_HIRING_TESTER_GUIDE.md` | Everyone, first | **The test:** signing in, who does what, the rules, how to report |
| `PBL_HIRING_UAT_TESTER_1_SALES.md` | Tester 1 | The customer, the accepted offer, two Work Orders with their sites, terms and holidays |
| `PBL_HIRING_UAT_TESTER_2_FLEET_ADMIN.md` | Tester 2 | Plum's second report, machines' papers, a test state rule, kit, the holiday calendar |
| `PBL_HIRING_UAT_TESTER_3_OPERATIONS.md` | Tester 3 | Requirements, allocations with their answers, kit on trips, a replacement |
| `PBL_HIRING_UAT_TESTER_4_ACCOUNTS.md` | Tester 4 | Reading the terms, contract, holidays and machines as the person who will bill |
| `PBL_HIRING_UAT_ONE_PERSON_ROUTE.md` | Only someone doing all four | Which login, in which order, with which data |
| `PBL_HIRING_UAT_YOUR_OWN_DATA.md` | Everyone, last | Their own work, every name `OWN-`, and trying to break the system |
| `PBL_HIRING_UAT_FEEDBACK_LOG.xlsx` | Everyone, one copy each | A tab of steps for each tester (Pass or Fail), one for their own data, and Findings |
| `PBL_HIRING_UAT_FEEDBACK_FORM.md` | As an alternative | The Findings questions in words |
| `PBL_HIRING_UAT_PLUM_REPORT_2.csv` | Tester 2 only | The invented Plum report their sheet uploads |

PBL hands its testers a PDF of each sheet, made from the Markdown here by `scripts/render_uat_sheet_pdfs.py`. The PDFs
are not part of this copy.

## Testers and logins

The same usernames and passwords work on both test sites (PBL's own reset steps, not part of this copy, set them).

| Tester | Job | Login | Role |
| --- | --- | --- | --- |
| 1 | Sales | `uat-sales-01` | Sales User |
| 2 | Fleet Admin | `uat-fleet-01` | Admin |
| 3 | Operations | `uat-operations-01` | Operations User |
| 4 | Accounts | `uat-finance-01` | Finance User |
| - | Project owner | `uat-owner-01` | Admin: reviewing, and the business event history |

"Fleet Admin" is an Admin login until a Fleet Admin role exists, so it can also do everything else: its sheet says what
is its job and what is not. `uat-manager-01` and `uat-sales-02` also sign in here, with no Hiring sheet.

**With three testers**, leave Tester 4 out at first, and let whoever finishes first do Tester 4's sheet with the
`uat-finance-01` login. **With one**, hand over the one-person route with all four sheets.

## Three things that will otherwise go wrong

**Everything starts with Tester 1.** Operations and Accounts have no Work Order until Sales has made one: their sheets
begin with a part that needs nobody. Watch the first hour - if Tester 1 is slow, the others wait.

**The sheets hand work to each other.** Tester 3 waits for Tester 1's Work Orders; Tester 2's new examination clears a
warning Tester 3 saw, and Tester 2's kit and calendar steps wait for Testers 3 and 1. Each sheet says what to do if the
other is not ready. These handovers are worth watching.

**Dates move.** Every date in the machines' papers counts from day 0, the day they were loaded. Load them the day
before the test starts, or that morning; the reminders move on as the days pass - that is the system working. **Tell
every tester the load date: it is the "day 0" every Hiring sheet counts from.**

## If you change a sheet

Edit the Markdown, then regenerate its PDF and the Feedback Log, whose step tabs are built from the sheets:

```bash
python scripts/render_uat_sheet_pdfs.py docs/uat-hiring   # the PDFs
python scripts/build_uat_feedback_logs.py                 # both packs' Feedback Logs
python -m unittest scripts.tests.test_uat_tester_sheets   # numbers, links and the log's steps
```

The user guide's screenshots come from `e2e/guide/` (see `e2e/guide/playwright.guide.config.ts` for how to retake
them); the second Plum report is generated from the practice data's own code, and a test fails if the file here
differs from it.
