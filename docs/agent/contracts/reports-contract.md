# Reports Contract (read model)

## Status

Written 8 October 2026 (TB-1 finding TB1-107, corrective package CS-07) for routes Slice 9A built on 7 September 2026
(`docs/agent/slices/slice-9a-reporting-dashboard-foundation.md`) and TB1-600 changed on 4 October 2026 (a total per
currency). It records what the code does at `main` `5e19123`; it changes nothing. Like the other module contracts
outside the registry's production foundation set, it is a current implementation contract
(`docs/agent/architecture/CONTRACT_REGISTRY.md`, "Existing contract position").

Reconciled 10 October 2026 for Slice 9F: open-offer reads now understand immutable Commercial Offer versions. The
route and response shapes are unchanged; only which version rows count is refined as recorded below.

## What it is

`backend/app/modules/reports/` is a **read model** (ADR-017): four reports for the dashboard, computed on each request
from tables other modules own. It owns no table, writes nothing, adds no migration and records no business event -
reading is not a business action (`test_reports_create_no_business_events`). It decides nothing. Lead,
Opportunity and Work Order statuses are counted as stored, whatever they are. Which offers are "open" is the
Commercial Offer contract's own list, imported. **Two offer statuses are restated as literals, not imported**:
`ACCEPTED` (`COMMERCIAL_OFFER_ACCEPTED_STATUS`, `reports/contract.py`) and `SUBMITTED` (awaiting the customer's
response, `COMMERCIAL_OFFER_AWAITING_RESPONSE_STATUS`, `reports/repository.py`). Should the Commercial Offer module
rename either, or change what it means, Reports does not follow on its own (see "When a source changes");
`reports/contract.py`'s docstring says the same.

**Freshness.** Each report is read live from the owners' tables when it is asked for; nothing is cached or copied, so
there is no refresh to run and no lag. Every response carries `generated_at`, in UTC (the screen shows India's time).

## Routes

| Route | Permission (who holds it) | Response |
| --- | --- | --- |
| `GET /api/reports/pipeline` | `OPPORTUNITY_READ` | `PipelineReport` |
| `GET /api/reports/open-offers` | `COMMERCIAL_OFFER_READ` | `OpenOffersReport` |
| `GET /api/reports/accepted-offers` | `COMMERCIAL_OFFER_READ` | `AcceptedOffersReport` |
| `GET /api/reports/work-order-handoff?limit=N` | `WORK_ORDER_READ` | `WorkOrderHandoffReport`; `limit` 1 to 100, default 20 (the dashboard asks for 10); outside that range, `422` |

The reports reuse the modules' read permissions rather than codes of their own (a new code would have needed a
migration). Each of the three is held by the same six roles - Admin, Sales User, Sales Manager, Finance User,
Operations User, Management Read Only - so every signed-in role reads every report. The pipeline report counts Leads
under `OPPORTUNITY_READ`; that is right only while `LEAD_READ` and `OPPORTUNITY_READ` have the same holders, which
`test_lead_and_opportunity_read_have_identical_role_sets` checks. No credentials: `401`. A route's permission is
pinned by `test_report_routes_request_the_expected_permission_codes`.

Errors use FastAPI's `{"detail": ...}`, as every route does today (`CODING_STANDARDS.md`, section 8; MCF-001's
envelope is CS-06).

## Response shapes

Defined in `backend/app/modules/reports/schemas.py`. Amounts are decimals. **Amounts in different currencies are never
converted or added together** (owner's decision, 4 October 2026, TB1-600): a total is a list of `CurrencyTotal`
(`currency_code`, `amount`), INR first and always present, another currency only where a record in the group is in
it. Opportunities have no currency field: their estimated value is INR.

- `PipelineReport`: `lead_total`, `leads_by_status` (status, count); `opportunity_total`, `opportunity_totals`,
  `opportunities_by_status` (status, count, totals of estimated value).
- `OpenOffersReport`: commercially live offers that are neither accepted, final nor superseded. A Draft/Ready later
  version is excluded while its submitted predecessor remains counted; `REVISED` and `ABANDONED` are excluded.
  `open_offer_total`, `open_offer_totals`,
  `offers_by_status` (status, count, totals of offer value); `ageing` - four buckets by days since the offer's date,
  or its creation date when it has none (0-7, 8-30, 31-90, over 90), each with count and totals;
  `awaiting_customer_response` (status `SUBMITTED`); `expiry_horizon_days` (30); `expiring_within_horizon`,
  `already_expired` and `no_expiry_recorded`, by `valid_until` against today's date.
- `AcceptedOffersReport`: accepted offers, `accepted_total`, `accepted_totals`; `with_work_order_shell` and
  `awaiting_handoff` (an accepted offer with at least one Work Order, or none), `awaiting_handoff_totals`; and the same
  split per `offer_purpose` (`by_purpose`).
- `WorkOrderHandoffReport`: `work_order_total`, `work_orders_by_status`; `source_offer_totals`; `recent_limit` and
  `recent` - the latest Work Orders, newest first, each with its public id, code, status, customer reference and
  received date, created time, and its source offer's public id, code, value and currency, and the Account's public
  id.

## Sources

| Report | Reads (owner) | Columns it depends on | Statuses it relies on |
| --- | --- | --- | --- |
| Pipeline | `crm_lead` (Leads); `crm_opportunity` (Opportunities) | `lead_status_code`; `opportunity_status_code`, `estimated_value` | - |
| Open offers | `crm_commercial_offer` (Commercial Offers) | `offer_status_code`, `previous_version_offer_id`, `currency_code`, `offer_value`, `offer_date`, `created_at`, `valid_until` | "Open" = not one of `COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES` (`ACCEPTED`, `WITHDRAWN`, `REJECTED`, `CLOSED`, `REVISED`, `ABANDONED`), imported; a later-version `DRAFT`/`READY_FOR_REVIEW` is excluded while in preparation; `SUBMITTED` for "awaiting the customer's response", **restated** |
| Accepted offers | `crm_commercial_offer` (Commercial Offers); `crm_work_order` (Work Orders) | the offer's `id` (the join key), status, `offer_purpose`, `currency_code`, `offer_value`; the Work Order's `commercial_offer_id` | `ACCEPTED`, **restated** |
| Work Order handoff | `crm_work_order` (Work Orders); `crm_commercial_offer` (Commercial Offers); `business_party` (Accounts) | the Work Order's `id` (the listing's tie-break order), `work_order_status_code`, `work_order_public_id`, `work_order_code`, `customer_wo_reference`, `received_date`, `created_at`, `commercial_offer_id`, `business_party_id`; the offer's `id` (the join key), `offer_public_id`, `offer_code`, `offer_value`, `currency_code`; the Account's `id` (the join key), `business_party_public_id` | - |

These reads are R7 of `docs/agent/architecture/BOUNDARY_EXCEPTION_REGISTER.md`: nine `SELECT` statements in
`reports/repository.py` (two with a subquery), holding thirteen reads of other modules' tables - `crm_lead` 1,
`crm_opportunity` 1, `crm_commercial_offer` 6, `crm_work_order` 4, `business_party` 1; no lock, no write.

## When a source changes

A package that renames, retypes or re-means a column above, or changes a status listed above, updates this contract
and `reports/repository.py` in the same change; `backend/tests/test_reports_api.py` reconciles each report's counts
and totals against the records it creates, so a broken read fails there. The two restated statuses are the ones to
watch: a change to `ACCEPTED` or `SUBMITTED` in the Commercial Offer module is made in `reports/contract.py` and
`reports/repository.py` too (or the literals are replaced by imports from the owner's contract). A new status needs
nothing here unless it changes what "open", "accepted" or "awaiting response" means.

## Recorded limits

- **A source offer's whole value is counted once per Work Order.** `source_offer_totals` sums, over Work Orders, the
  value of each one's source offer, so an offer with two Work Orders - a partial award - counts twice. What a Work
  Order carries of its offer's value is CS-04's subject (HOF-2); this total follows it when that is settled.
- `ageing` and `expiry` count calendar days by the database's `CURRENT_DATE`, which the session's UTC sets - so between
  midnight and 05:30 in India the day is still the previous one.
- No paging, filters, Account scope or export: the dashboard's foundation, as Slice 9A built it.
