# PBL CRM test - Runbook

For whoever runs the CRM test, **not for testers**: how the site starts, the handovers to watch, collecting results,
and resetting. The site itself - deploying, accounts, backups - is run from PBL's own hosting runbook, which is not
part of this copy.

## How the site starts

**Empty, but for the sign-ins** (owner's decision, 9 October 2026). No practice customers, enquiries or offers are
loaded: in the first round one tester did every test and mixed the data he was given with his own, so this round every
record is typed in by a tester from their own sheet, or as their own data under an `OWN-` name.

The seeded practice scenario of the first round, `uat-pilot-seeded`, still exists in the smoke-data harness, for a
machine of your own; it is not loaded on the site.

## Why the data is invented

Two policy items are still open: nothing purges records when a retention period ends, and nothing records **who
downloaded** a document (`docs/agent/DEFERRED_REQUIREMENTS.md`, both required before production). Neither blocks the
test, because it runs on invented data (owner's decision, 8 September 2026). That depends on two things staying true:
the data really is invented - no real customer, enquiry, rate, PAN or GSTIN - and it really can be removed, which on
the test site is done by clearing the database (below).

## The handovers to watch

| From | To | What | Sheet steps |
| --- | --- | --- | --- |
| Tester 1 | Tester 3 | Market rates on lines 1 and 3 of Tester 1's offer | T1 13, T3 2 |
| Tester 1 | Tester 2 | Approving the quotation of offer v1, then of v2 | T1 17 and 23, T2 1 and 2 |
| Tester 1 | Tester 4 | Checking the customer's PAN and GST numbers | T1 10, T4 2 to 5 |
| Tester 2 | Tester 3 | Market rates in euros on line 1 | T2 6, T3 3 |
| Tester 2 | Tester 4 | Checking (and rejecting) the PAN | T2 4, T4 6 |
| Tester 1 | Tester 3 | The accepted offer becomes a Work Order | T1 24 to 26, T3 7 to 9 |

Tester 4 also adds numbers to Tester 1's converted customer (T4 7 to 9) - the only time a tester changes another's
customer, on purpose.

## Collecting results

Each tester fills in their own copy of `PBL_CRM_UAT_FEEDBACK_LOG.xlsx`: their tab of steps (Pass, Fail, Could not
try, Not done) and Findings. Collect the copies at the end of each day: a Fail with no Findings row, or a Findings row
with no login or time, is worth asking about while the tester still remembers.

## Resetting

**Usually: restore the handover backup** - the one taken right after the reset (PBL's hosting runbook, not part of this copy). It
puts the site back as handed over: empty, with the sign-ins and the testers' passwords.

**For a fresh start from nothing**, repeat PBL's reset steps (not part of this copy) for the CRM site alone.

On a machine of your own, clear the database with `docker compose down -v && docker compose up -d`. On a shared
development machine that destroys its database too: give the test stack its own `COMPOSE_PROJECT_NAME` first.

## Known, already on the list

These need not be reported (the Tester Guide says so): markup over the basis rate is not modelled; the quotation is a
web page printed to PDF; there is no credit limit check, GST calculation or sending from the system; a GST number cannot
be changed once added; every job sees every record.
