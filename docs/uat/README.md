# The CRM test pack - what to hand out, and to whom

Everything a CRM tester needs, for the test site **the CRM test site**, rebuilt for the restart of
12 October 2026 (owner's decisions, 9 October 2026): the site starts empty but for the sign-ins; each tester has one
job and one set of data; their own data comes last, every name starting `OWN-`; and each step is marked Pass or Fail
in the Feedback Log.

This folder is shared with the testers, so everything in it is something a tester may be given, except this README
and `PBL_CRM_UAT_RUNBOOK.md`, which are for whoever runs the test.

| Document | Who gets it | What it is for |
| --- | --- | --- |
| `PBL_CRM_TESTER_GUIDE.md` | Everyone, first | What the CRM does, how the test runs, the rules, what is deliberately not built, how to report |
| `PBL_CRM_UAT_TESTER_1_SALES.md` | Tester 1 | Sales Executive: two Leads, a customer, an offer, quotation, a new version of it, the customer's yes |
| `PBL_CRM_UAT_TESTER_2_SALES_MANAGER.md` | Tester 2 | Sales Manager: approving Tester 1's quotations; an offer in euros; an order awarded in two parts |
| `PBL_CRM_UAT_TESTER_3_OPERATIONS.md` | Tester 3 | Operations: market rates on the Sales testers' offer lines, with a vendor quote; Tester 1's Work Order; what Operations may not do |
| `PBL_CRM_UAT_TESTER_4_ACCOUNTS.md` | Tester 4 | Accounts: verifying and rejecting a PAN; adding GST numbers already checked; finding that a GST number Sales entered cannot be changed; documents; what Accounts may not do |
| `PBL_CRM_UAT_ONE_PERSON_ROUTE.md` | Only someone doing all four | Which login, in which order, with which data |
| `PBL_CRM_UAT_YOUR_OWN_DATA.md` | Everyone, last | Their own work, every name `OWN-`, and trying to break the system |
| `PBL_CRM_UAT_FEEDBACK_LOG.xlsx` | Everyone, one copy each | A tab of steps for each tester (Pass or Fail), one for their own data, and Findings, one row per problem |
| `PBL_CRM_UAT_FEEDBACK_FORM.md` | As an alternative | The Findings questions in words |

PBL hands its testers a PDF of each sheet, made from the Markdown here by `scripts/render_uat_sheet_pdfs.py`. The PDFs
are not part of this copy.

## Testers and logins

The same usernames and passwords work on both test sites. A tester keeps the password they already have; the reset
re-creates their account with it (PBL's own reset steps, not part of this copy).

| Tester | Job | Login | Their data |
| --- | --- | --- | --- |
| 1 | Sales Executive | `uat-sales-01` | names `T1-`, PAN and GST numbers `ZZZZM1...` |
| 2 | Sales Manager | `uat-manager-01` | names `T2-`, numbers `ZZZZM2...` |
| 3 | Operations | `uat-operations-01` | vendors `T3-`; Work Orders for Tester 1 |
| 4 | Accounts | `uat-finance-01` | numbers `ZZZZM4...` |
| - | Project owner | `uat-owner-01` | reviewing, and the only login that sees the business event history |

`uat-sales-02` is a spare Sales login, and `uat-fleet-01` (Admin) is the Hiring site's Fleet Admin: neither has a CRM
sheet. Own data uses `OWN-T<n>-` names and `ZZZZP<n>...` numbers.

**With three testers**, leave Tester 4 out at first, and let whoever finishes first do Tester 4's sheet with the
`uat-finance-01` login. **With one**, hand over the one-person route with all four sheets.

## Three things that will otherwise go wrong

**The sheets hand work to each other.** Tester 1 needs Tester 3's market rates and Tester 2's approval; Tester 3 makes
Tester 1's Work Order; Tester 4 checks the customers Testers 1 and 2 type in. Each sheet says what to do while waiting.
These handovers are worth watching - they are the real work.

**Sheet data and own data must never mix.** That is what spoiled the first round. Every sheet name starts with the
tester's number; every own-data name starts `OWN-`; nothing else should appear.

**A GST number exists only once in the system.** Each tester's numbers carry their own digit, so they never clash. A
tester who borrows another's numbers is refused - correctly.

## If you change a sheet

Edit the Markdown, then regenerate its PDF and the Feedback Log, whose step tabs are built from the sheets:

```bash
python scripts/render_uat_sheet_pdfs.py docs/uat          # the PDFs
python scripts/build_uat_feedback_logs.py                 # both packs' Feedback Logs
python scripts/render_uat_sheet_pdfs.py --check           # exit 1 if a PDF is older than its Markdown
python -m unittest scripts.tests.test_uat_tester_sheets   # numbers, links and the log's steps
```

A step is a heading `### <n>. <title>` in a sheet; the log lists them in order, so a renumbered sheet needs a new log.
