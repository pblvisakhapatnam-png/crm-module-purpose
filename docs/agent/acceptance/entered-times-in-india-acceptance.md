# Entered times acceptance - a date and time typed in India's time comes back as typed

Slice record: `docs/agent/slices/entered-times-in-india.md`. Contracts: `commercial-offer-contract.md`, `lead-contract.md`
and `interaction-contract.md`, each "Entered times" / "Times carry their zone" (11 October 2026); ADR-028 "Timestamps".
No migration.

## Automated checks

Run on branch `fix/entered-time-zone` in a port-free Compose stack (`pbl-tz`) whose backend runs with
`PASSWORD_HASH_ITERATIONS=10000`, as CI's does. The full backend regression and Playwright run in CI
(`Required validation`).

| Check | What it covers |
| --- | --- |
| `backend/tests/test_entered_time_zone.py` | Every date-and-time input of every route uses `ZonedDateTime` with both its checks, and there are exactly the thirteen listed (a route walk through bodies, queries, nested models); `written_with_zone` passes ISO text with its zone and a datetime from code, and refuses text without a zone, a date, a number, digits, empty text, null and bytes; `in_utc` converts an offset and refuses no zone; a number or digits sent for a market rate's time, a Lead activity's, a conversation's or a conversation filter is refused (nothing recorded); on one offer: the details form's submitted at, a line's market rate (`Z` and `+05:30`), submission evidence and the credit review each refuse a time with no zone (nothing recorded) and return 10:30 typed in India as `05:00` UTC, which reads 10:30 in India; mark-submitted copies it; `offer_date` and `valid_until` unchanged; a customer response at 00:30 in India on 12 October is returned as `2026-10-11T19:00:00` and dates the outcome 12 October; a Lead activity's two times; a conversation's two times, its update and its list filters |
| The fifteen test files that sent these times with no zone (`test_commercial_offers_api.py`, `test_commercial_offer_related_offers_api.py`, `test_cs04_handoff_once_per_line.py`, `test_cs05a_offer_stale_save.py`, `test_cs05c_submitted_offer_lock.py`, `test_leads_api.py`, `test_operating_currency.py`, `test_slice_7c_work_order_line_detail.py`, `test_slice_7d_part_3_contract_period.py`, `test_slice_7d_work_order_line_billing_terms.py`, `test_slice_9b_pilot_hardening.py`, `test_slice_9f_commercial_offer_versions.py`, `test_work_order_amendments_api.py`, `test_work_orders_api.py`, `test_wrr001_resource_requirements.py`) | 79 lines now send the same time with `Z` (UTC, as the API read them before); only the time sent changed, never an expected result |
| The other files that reach these routes, and the guards that read route or service source | `test_interactions_api.py` (already sent zones), `test_slice_4g_*`, `test_slice_9d_*`, `test_smoke_data_harness.py`, `test_cs11_*`, `test_authorization_route_migration_guard.py`, the `test_business_authority_*` guards, `test_postgresql_dialect_regression.py`, `test_tb1_605_*`, `test_tb1_400_*`, `test_tb1_102b_*` |
| Result of the 32 files above together | `1061 passed, 1 skipped` in 13 min 52 s before review; `1074 passed, 1 skipped` in 11 min 4 s after the round 2 corrections (thirteen new cases). The skip is CS-04's note check, which reads `docs/` (not mounted in the container; CI runs it) |
| `frontend/src/components/enteredDateTime.test.ts` | 10:30 typed becomes `05:00:00.000Z`, whatever the browser's zone; what comes back shows 10:30 am, where the old way showed 4:00 pm; India's day kept across midnight; an empty or malformed box sends nothing; a saved time goes back into a box in India's time and saves as the same moment; a box starts at now in India; counted per source file, no file has fewer calls to `enteredIndiaTimeToUtc` than date-and-time boxes (eight boxes in four files today; which call takes which box is left to the screen check and Playwright), and no file keeps one of the old send helpers |
| `frontend/src/components/dateTimeDisplay.test.ts` | Unchanged and passing: `formatDateTime` reads no zone as UTC |
| Frontend | `npm run typecheck`, `npm test`, `npm run build` |
| UAT sheets | `python scripts/render_uat_sheet_pdfs.py --check docs/uat`; `python -m unittest scripts.tests.test_uat_tester_sheets` |
| Frozen handoff contract | SHA-256 `0f16ff22...cd39080` before and after |

Undo proofs (each change put back on a copy, the test run, the change restored and its checksum compared): a schema
field back to `datetime` fails the route walk and that field's refusal; `outcome_date` back to `.date()` fails the
customer-response test; the offer page's old send helper fails `enteredDateTime.test.ts`; and (round 1) a second
date-and-time box added to `LineMarketRates.tsx` without a second conversion fails the per-file count; and (round 2)
`ZonedDateTime` without its first check (`written_with_zone`) fails the route walk and the offer, Lead and conversation
tests, which then accept a number.

## Manual check (about 10 minutes)

**Who**: `sales1` (Sales User); `ops1` for a market rate if you prefer. **Where**: a local stack or a test site
carrying this package. **Data**: any Draft offer with one active line, and any Lead.

Positive path:

1. Open the offer, **Lines & Pricing**, **Add a rate for line 1**: any amount and basis, *Collected at* today 10:30.
   **Save rate**. The rate reads "Collected by ... on <today>, 10:30 am" - not 4:00 pm.
2. **Details**: set *Submitted at* to today 09:15 and save. It shows 09:15 am. Open the form again: the box shows
   09:15, and saving with no other change says nothing changed.
3. **Submission**: record submission evidence at today 11:00, then a credit review at today 11:05. Both show the time
   typed. **Record as Submitted**: the offer's *Submitted at* shows 11:00 am.
4. **Customer response**: *Response received at* today 00:30 (half past midnight), outcome *Accepted / awarded*. It
   shows 12:30 am today, and the offer's outcome date is today.
5. On the Lead: record an activity at today 16:45 with a next follow-up tomorrow 10:00; record a conversation at today
   15:00. Each shows the time typed.

Negative path (API, as a tool or a test would send it): `POST /api/commercial-offers/{id}/pricing-evidence` with
`"collected_at": "2026-10-12T10:30:00"` (no zone) answers `422` with "Give the date and time with its time zone, ..."
and records nothing. The same with `"2026-10-12T10:30:00+05:30"` records the rate, returned as `2026-10-12T05:00:00`.

Permission path: unchanged - the routes' permissions are not touched (`test_authorization_route_migration_guard.py`).

**Exploratory check done, 11 October 2026 (23:20 IST)**, on the lane stack (`pbl-tz`, page server on `localhost:3100`)
in the in-app browser as `sales1`, browser zone Asia/Kolkata. The pane was hidden, so fields were filled with form
inputs and forms submitted in the page (no pointer clicks). A line's market rate typed at 10:30 read "Collected by ... on
11 Oct 2026, 10:30 am", stored `2026-10-11T05:00:00`; the offer details form's *Submitted at* typed at 09:15 was stored
`2026-10-11T03:45:00`, shown "11 Oct 2026, 09:15 am", came back into the reopened form as 09:15, and saving it unchanged
said "Nothing has been changed, so there is nothing to save."; on the Lead, the conversation log's *When it happened*
started at now in India, and a conversation typed at 15:00 was listed at "11 Oct 2026, 03:00 pm". Not done by hand: steps
3 and 4 above (submission evidence, the credit review, the customer response) and step 5's Lead activity form - held by
the backend tests and the per-file source count.

## Deferred and known gaps

- Offer times typed on screen before this change stay 5 hours 30 minutes late; there is no migration (the slice record
  says why). The test sites are cleared by the October reset.
- What the API sends back keeps no zone for the CRM tables (TB1-401, CS-16).
- Nine files keep their own copy of the display helper, behaving like `dateTimeDisplay.ts`: TB-1 register note N-06,
  updated with the list, holds moving them.
- No component test renders a page (`DEFERRED_REQUIREMENTS.md`, "Frontend component-test capability"): the page wiring
  is held by the source scan in `enteredDateTime.test.ts`, the screen check above and Playwright's existing flows.

## Independent review

the independent reviewer (one bounded packet per round; up to three rounds, merge only on the owner's word).

- **Round 1** (packet `82540908...2ecc`, commit `efcd8ef0`): `CORRECTION_REQUIRED`, two material and two advisory
  findings, all corrected in the next candidate - none deferred:
  - ETZ-R1-001 (material): the records placed the conversation log on the offer and Work Order pages; it is mounted on
    the Lead, Account and Opportunity pages (offer and Work Order mounting deferred since 9D). Slice record and
    continuity note corrected.
  - ETZ-R1-002 (material): the records said no API contract changed. Refusing a time with no zone is a deliberate,
    breaking tightening of thirteen inputs' request contract: now said in ADR-028's refinement, the three contracts and
    the slice record; INT-001 is version `2.0` under its own change-control rule.
  - ETZ-R1-003 (advisory): the source scan passed a file with a second, unconverted box. It now counts boxes and calls
    per file; the records say what it can and cannot see.
  - ETZ-R1-004 (advisory): `zoned_datetime.py` named a test file that does not exist, and the new test's header dated
    the screen check 12 October. Both corrected.
- **Round 2** (packet `2790202c...cfba7`, commit `849c1fe0`): `CORRECTION_REQUIRED`, two material findings, both
  corrected:
  - ETZ-R2-001 (material, code): a number, or digits as text, slipped past the zone check - Pydantic reads it as
    seconds since 1970 and hands back a UTC time before the check runs. `ZonedDateTime` now checks the value as sent
    first (`written_with_zone`: ISO text with its zone, or a datetime made in code); tests send a number to a body
    field in each of the three modules and digits as text to the market rate and to both conversation filters, and the
    route walk requires both checks.
  - ETZ-R2-002 (material, records): "responses are unchanged" was too broad - INT-001's responses now carry
    `contract_version` `2.0`, and a customer response's event gives its time in UTC with `+00:00` - and ADR-028's
    "Unchanged by this decision" read as covering the refinement. The contracts, slice record, continuity note and
    NEXT_STEPS now say exactly what changes in responses, and ADR-028's section names the refinement as its one
    exception.
