# Entered times - a date and time typed in India's time comes back as typed

Status: built on branch `fix/entered-time-zone` (from `main` at `7650685`, after Slice 4G), 11 October 2026. No
migration. No change to any business rule.

## Why

Found in the Slice 4G screen check on 11 October 2026: a market rate's "Collected at" typed as 10:30 showed as
4:00 pm. The owner asked for it to be fixed separately (it predates 4G: the whole-offer rate form did the same).

**Cause, confirmed.** A date-and-time box (`components/DateInput.tsx` with `withTime`, a browser `datetime-local`
box) holds the time typed, in India's time, with no zone: `2026-10-11T10:30`. The offer page sent it as it was
(`formatCollectedDateTimeInput` only added `:00`; Slice 4G's line rates sent it unchanged). The backend took a time
with no zone as it came and wrote it into a `timestamp without time zone` column, which holds UTC (ADR-028; every
session is set to UTC). The API sends such a column's time back with no zone, and the page reads a time with no zone
as UTC (`components/dateTimeDisplay.ts`, `formatDateTime`, TB-1 TB1-604) and shows it in India's time: 10:30 + 5:30 =
16:00.

The Lead activity form and the conversation log did not shift for a tester in India: they converted the typed time
with the browser's own zone (`new Date(value).toISOString()`), which is right only while the browser is in India.

## Where a person types a date and time

Every `DateInput withTime` in `frontend/src`, and every API input that takes a date and time. The route walk in
`backend/tests/test_entered_time_zone.py` finds exactly these thirteen inputs and no other. The Account and
Opportunity pages take a typed time only through the shared conversation log, which is mounted on the Lead, Account and
Opportunity pages; its mounting on the Commercial Offer and Work Order pages is deferred since Slice 9D, though the API
already accepts a conversation linked to either. The Accounts, Opportunities and Work Orders modules' own routes and
every Hiring module (allocations, eligibility, certificates, the holiday calendar) take dates, never a date and time,
and the times they record (decided, seen, saved) are the server's own.

| Screen box | Page | API input | Column |
| --- | --- | --- | --- |
| Submitted at (offer details form) | Commercial Offer | `PUT /api/commercial-offers/{id}` `submitted_at` | `crm_commercial_offer.submitted_at` (no zone) |
| Collected at (a line's market rate) | Commercial Offer, Slice 4G | `POST .../pricing-evidence` `collected_at` | `crm_commercial_offer_pricing_evidence.collected_at` (no zone) |
| Submitted at (submission evidence) | Commercial Offer | `POST .../submission-evidence` `submitted_at` | `commercial_offer_submission_evidence.submitted_at` (no zone) |
| Reviewed at (credit review) | Commercial Offer | `POST .../credit-review` `reviewed_at` | `commercial_offer_credit_review.reviewed_at` (no zone) |
| Response received at (customer response) | Commercial Offer | `POST .../customer-responses` `response_received_at` | `commercial_offer_customer_response.response_received_at` (no zone) |
| Activity at, Next follow-up at | Lead | `POST /api/leads/{id}/activities` `activity_at`, `next_follow_up_at` | `crm_lead_activity` (no zone) |
| When it happened | Conversations (`InteractionLog.tsx`), on the Lead, Account and Opportunity pages | `POST /api/interactions` `occurred_at` | `interaction.occurred_at` (with zone) |
| - (no box) | - | `POST /api/interactions` and `PUT /api/interactions/{id}` `next_follow_up_at`; `GET /api/interactions` `occurred_from`, `occurred_to` | `interaction` (with zone) |
| - (route refuses every request since 9F) | - | `POST .../revisions` `opened_at` | `commercial_offer_revision.opened_at` (no zone) |

## Where those times are shown or compared

- **Shown:** the offer page (details, submission evidence, credit reviews, customer responses and the summary line,
  line market rates), the Lead page's activities, the conversation log - all through a
  `formatDateTime` that reads a time with no zone as UTC and shows India's time. No report, no quotation document and
  no Hiring page shows one: reports read dates and the server's own times; a quotation shows only when it was
  generated (`quote_documents._format_business_datetime`, already India's time).
- **Compared or ordered:** the latest credit review (readiness) and the latest customer response (lifecycle guidance,
  the Work Order handoff's "the latest response must be the acceptance", CS-04) are taken by the time, newest first;
  submission evidence and revisions are listed by time; conversations are filtered by `occurred_from`/`occurred_to`.
  Mark-submitted copies the latest submission evidence's time onto the offer. All compare UTC with UTC once every
  stored time is UTC.
- **A date taken from one:** a customer response that accepts or rejects the offer sets the offer's `outcome_date`
  from the time received. It took `.date()` of the time as sent - India's date only because the time arrived in
  India's time. It now takes India's date of the moment (`business_time.india_date`), so a response received at
  00:30 on 12 October in India is dated 12 October, not 11.
- **Events:** the events of a credit review, submission evidence, a Lead activity and a conversation carry the time as
  stored; a customer response's event carries the time as received, now in UTC with `+00:00` where it used to carry
  the India time typed.
- **Smoke data:** the harness passes times with a zone (`datetime.now(timezone.utc)`), unchanged.
- **The UAT packs:** the CRM sheets have testers type "today, 15:00" (a conversation, Tester 1), "today, 10:00 /
  11:30 / 12:15" (market rates, Tester 3) and "now" (customer responses, Testers 1 and 2; the Hiring Sales sheet).
  Tester 3's market-rate step and Tester 1's conversation step now also check that the time shows as typed.
- **Dates that business rules compare** - `valid_until`, `offer_date`, `outcome_date`, Work Order and Hiring dates -
  are dates, not times, and nothing here changes them.

## The rule (engineering decision, ADR-023)

No business meaning changes: a time a person types is the time they mean, in India; it is shown back the same. Three
parts, recorded in ADR-028 "Timestamps" and the API conventions:

1. **The page sends a typed time as a UTC moment with its zone.** `components/enteredDateTime.ts`,
   `enteredIndiaTimeToUtc`: `2026-10-11T10:30` becomes `2026-10-11T05:00:00.000Z`, whatever the browser's own zone
   (India keeps no daylight saving; its offset is always +05:30). A form that starts from a saved time puts it back in
   the box in India's time (`apiDateTimeToIndiaInput`); a box that starts at now starts at now in India
   (`nowAsIndiaInput`). Every page with a date-and-time box uses them. `enteredDateTime.test.ts` counts, per source
   file, the date-and-time boxes and the calls to `enteredIndiaTimeToUtc`, and fails when a file has fewer calls than
   boxes or keeps one of the old send helpers; it cannot tell which call takes which box (the screen check and
   Playwright do).
2. **The API refuses a date and time without a zone, and holds one with a zone as UTC.** `app/shared/zoned_datetime.py`,
   `ZonedDateTime`, on all thirteen inputs: `422` with "Give the date and time with its time zone, for example
   2026-10-12T05:00:00Z or 2026-10-12T10:30:00+05:30." Any offset is accepted and converted. Two checks
   (review round 2): the value as sent must be ISO text with its zone, or a datetime made in code
   (`written_with_zone`) - Pydantic alone would read a number, or digits as text, as seconds since 1970 and hand back a
   UTC time that the second check could not tell from one sent with `Z`; then the moment must carry a zone (`in_utc`).
   `test_entered_time_zone.py` walks every route and fails on a date-and-time input that lacks either check, or on one
   more or one fewer than the thirteen.
3. **Storage, and the form of the times the API sends back, are unchanged.** UTC in the columns; the CRM tables' times
   are sent back with no zone and read as UTC (TB1-401; CS-16 converts those columns to `timestamp with time zone`).

**Refused rather than converted.** A time with no zone can be read two ways, and the defect was exactly a silent
reading the wrong way. Reading it as India's time would make the API read a time with no zone one way coming in and the
other way going out; reading it as UTC is what stored the shifted times. A caller that sends one now learns at once.
The platform's own precedent is the same: the authority configuration refuses an `effective_from` with no zone
(`configuration_service.py`), and HR reference times must carry one. Nothing that calls the API today depends on
sending a time with no zone: the pages now send a zone, the smoke-data harness passes one, and the backend tests that
sent none now send `Z`.

**The API contracts change, deliberately.** Business meaning does not change, but the request contract of the thirteen
inputs does: a time with no zone, accepted until now (and read as UTC), is refused. That is a breaking tightening for a
caller that sent one, recorded in each contract's "Entered times" / "Times carry their zone" section and in ADR-028's
refinement. INT-001's change-control rule (`interactions/contract.py`: the major part for a breaking change) makes its
version `2.0`, which its create, update and delete responses now carry as `contract_version`; the Commercial Offer
and Lead contracts carry no version number. Two things change in responses, and only these: that `contract_version`,
and a customer response's event (`CommercialOfferCustomerResponseRecorded`, stored and returned in the `POST`
response), whose `response_received_at` is now always UTC with `+00:00`. Field names and types are unchanged
everywhere, the records' times keep their form, and an earlier conversation's stored command fingerprint is unchanged
(a time with no zone was fingerprinted as UTC), so a replayed request still matches.

## Rows already stored

- **The five offer times typed on screen before this change** (offer details' submitted at, market rates' collected at,
  submission evidence, credit reviews, customer responses) hold India's time in a UTC column and keep showing 5 hours
  30 minutes late. Mark-submitted copied the same shifted time onto the offer. A response's `outcome_date` is right:
  it was taken from India's time.
- **Everything else is right:** Lead activities and conversations typed in India were converted by the browser; the
  smoke data, the tests and every time the server sets are UTC.
- **No migration.** A screen-typed row cannot be told from a correctly stored one in the same column: the UAT practice
  data and any API caller stored true UTC there, and subtracting 5 hours 30 minutes from every row would break those.
- **The test sites** are reset for the October restart (`docs/deployment/UAT_RESET_2026-10_STEPS.md`): step 2 clears
  both databases, and step 3 now deploys this package's merge, so no shifted row reaches the testers. If the reset runs
  before this merges, the offer times testers type until the next deploy stay 5 hours 30 minutes late after it. Step
  1's safety backup holds the pilot's earlier rows as they were: restored, their typed offer times read late, as now.
- **A local database** keeps its rows. Where an offer has a typed time from before and one from after, ordering by time
  (the latest credit review or customer response) can misplace two within 5 hours 30 minutes of each other; reload the
  smoke data or record again.

## Out of scope

- Sending the CRM tables' times back with a zone: CS-16, with the column conversion (TB1-401).
- The display copies: nine files keep their own `backendDateTimeToDate` and `formatDateTime`, in three variants that
  read a time with no zone as UTC and show India's time like the shared one - `InteractionLog.tsx`,
  `CommercialOfferDetailPage.tsx`, `CommercialOffersPage.tsx`, `LeadDetailPage.tsx`, `OpportunitiesPage.tsx`,
  `OpportunityDetailPage.tsx`, `WorkOrderAmendmentDetailPage.tsx`, `WorkOrderDetailPage.tsx`, `WorkOrdersPage.tsx`.
  Moving them to `dateTimeDisplay.ts`, with a stronger guard, is TB-1 register note N-06 (updated with this list): a
  frontend tidy-up of its own, not part of this fix, which changes the sending side.
- A data repair for rows typed before the change (see above).

## Contracts and records changed

- `docs/agent/contracts/commercial-offer-contract.md`, `lead-contract.md`, `interaction-contract.md` (INT-001: a dated
  section and version `2.0`, set in `backend/app/modules/interactions/contract.py`), and INT-001's row in
  `docs/agent/architecture/CONTRACT_REGISTRY.md` (its version only; its maturity is unchanged).
- `docs/agent/ARCHITECTURE_DECISIONS.md`, ADR-028 "Timestamps": a dated refinement.
- `docs/agent/architecture/API_EVENT_AND_INTEGRATION_CONVENTIONS.md`, "Synchronous interfaces".
- `docs/agent/CODING_STANDARDS.md` (sections 3 and 7) and `AGENTS.md` ("Date/time display rule").
- `docs/agent/tb-1/TB_1_DEFERRED_IMPROVEMENT_REGISTER.md`, note N-06: dated, with the display copies listed.
- `docs/uat/PBL_CRM_UAT_TESTER_1_SALES.md` and `PBL_CRM_UAT_TESTER_3_OPERATIONS.md` with their PDFs;
  `docs/deployment/UAT_RESET_2026-10_STEPS.md`, "The commit to deploy".
- Acceptance: `docs/agent/acceptance/entered-times-in-india-acceptance.md`. Continuity:
  `docs/continuity/ENTERED_TIMES_IN_INDIA.md`, `docs/continuity/NEXT_STEPS.md`.

## Authority and required reading

- AGENTS.md, "Date/time display rule"; ADR-023, ADR-028 ("Timestamps"); ADR-013
- TB-1 findings TB1-401 (the CRM tables' times without a zone) and TB1-604 (pages reading them as local)
- `docs/agent/contracts/commercial-offer-contract.md` (4D, 6I, 6I.2, 6J, 6L, CS-05a, CS-05c, 9F and 4G sections),
  `lead-contract.md` (Slice 2D), `interaction-contract.md` (MCF-001 conformance, change control)
- `docs/agent/architecture/API_EVENT_AND_INTEGRATION_CONVENTIONS.md`, `CONTRACT_REGISTRY.md` (INT-001 is `APPROVED`)
- `docs/agent/CODING_STANDARDS.md` sections 1, 3 and 7; `docs/agent/TESTING_STRATEGY.md` section 4
- `docs/agent/slices/slice-4g-market-rates-per-offer-line.md` (where it was found)
- `docs/deployment/UAT_RESET_2026-10_STEPS.md`
- The frozen handoff contract: not touched; SHA-256 `0f16ff22...cd39080` before and after
