# Slice 9A - CRM Operational Reporting and Dashboard Foundation

## Status

Implemented, 7 September 2026. Foundation Slice Mode. No migration.

This is the slice listed as `9A - Reporting and Dashboard Foundation` in
`docs/agent/FUTURE_SLICES.md`, brought forward ahead of the 7x/8x Hiring slices because it
is the highest visible-delta work available that is independent of both the Platform
Foundation authority lane and the Alembic migration head.

## Objective

Replace the dead demo dashboard - 180 lines that made zero API calls - with live operational
figures, and add the four minimum reports a sales manager needs: pipeline, open offers,
accepted offers and Work Order handoff.

## Why this slice does not contend with other lanes

- **No migration.** Every report is an aggregate read over tables owned by existing modules.
  This slice moves the Alembic head not at all, so it never contends for it. PF-1A-E3 merged
  while this slice was in progress and took the head to `20260906_0032`; Slice 9A needed no
  rebase and no change as a result, which is the property the design was chosen for.
- **No new permission codes.** New `REPORT_*` codes would have required a migration to seed
  `authz_permission` / `authz_role_permission`. See "Authorization" below.
- **No writes.** No business rule, lifecycle transition, contract or frozen boundary changes.

## Backend

New module `backend/app/modules/reports/` (contract, schemas, repository, service, routes).
It owns no tables and writes nothing.

```text
GET /api/reports/pipeline               OPPORTUNITY_READ
GET /api/reports/open-offers            COMMERCIAL_OFFER_READ
GET /api/reports/accepted-offers        COMMERCIAL_OFFER_READ
GET /api/reports/work-order-handoff     WORK_ORDER_READ   (?limit=1..100, default 20)
```

### Report content

| Report | Content |
| --- | --- |
| Pipeline | Lead counts by status; Opportunity counts and value by status |
| Open offers | Non-terminal, non-accepted offers by status and value; ageing buckets; awaiting-response count; expiry counts (expiring within 30 days, already expired, no validity date recorded) |
| Accepted offers | Accepted count and value, split by `offer_purpose`, and split by whether a Work Order shell already exists versus awaiting handoff |
| Work Order handoff | Shells by status; total source-offer value; recent handoffs with source Commercial Offer identity |

### Derived, not restated

Every status grouping is imported from the owning module's contract rather than re-declared.
"Open" is derived from `COMMERCIAL_OFFER_GENERIC_UPDATE_CANNOT_LEAVE_STATUSES`
(`ACCEPTED`, `WITHDRAWN`, `REJECTED`, `CLOSED`), so if the Commercial Offer module changes its
lifecycle, this module follows automatically instead of drifting. Ageing buckets and the
expiry horizon are contract constants, and the ageing SQL is generated from them.

### Authorization

The reports reuse existing per-module read permissions rather than introducing new codes.
All five business read permissions (`ACCOUNT_READ`, `LEAD_READ`, `OPPORTUNITY_READ`,
`COMMERCIAL_OFFER_READ`, `WORK_ORDER_READ`) map to the identical six-role set, so **no access
is widened or narrowed by this slice**.

The pipeline report spans Leads and Opportunities but requests only `OPPORTUNITY_READ`. That
is safe exactly while those two permissions carry the same role set, so
`test_lead_and_opportunity_read_have_identical_role_sets` asserts that equality directly. If a
future change narrows either one, the test fails loudly rather than silently leaking Lead
counts to a role that may no longer read Leads - at which point the pipeline report must be
split or given its own permission code and migration.

### Currency

Amounts are summed without conversion. That is correct only because ADR-023 fixes every
current operating amount to INR and defers multi-currency. The constraint is recorded at the
top of `repository.py`; if multi-currency is introduced, every `SUM` must be revisited.

Superseded on 4 October 2026: the reports now total each currency separately. See "TB-1 fix TB1-600" below.

## Frontend

- New `frontend/src/components/OperationalReports.tsx`: fetches all four reports in parallel,
  with loading, no-session, error-with-retry and empty states.
- `DashboardPage.tsx` renders it above the existing navigation grid. **The existing role-aware
  create shortcuts and demo guidance are preserved unchanged.**
- Four KPI tiles (open opportunities, open offers, awaiting handoff, Work Order shells), then
  the four report sections.
- Amounts use `en-IN` INR formatting; timestamps display in Asia/Kolkata per the project
  date/time rule.
- Work Order and source Commercial Offer entries link through to their detail pages,
  preserving the Slice 6D.1 handoff traceability the report exists to show.
- No new route. Adding one would have required a `routes.tsx` change and its regression tests;
  the dashboard is the screen users already open.

## Out of scope (deliberate)

- **Potential/Firm exposure views**, which `FUTURE_SLICES.md` lists under 9A. `CEX-001` is
  approved but not implemented, and there is no exposure data to report. Deferred until the
  exposure engine exists; this slice does not invent a placeholder calculation.
- **Export-ready output** (CSV/print), also listed under 9A. Deferred.
- Date-range filtering, drill-through report pages, owner/segment breakdowns, charts.
- Any write, business event, lifecycle change, migration or permission change.

## Verification

```text
docker compose exec backend pytest tests/test_reports_api.py -q     42 passed
docker compose exec backend pytest -q                             1025 passed (983 baseline + 42)
frontend npm run typecheck                                         clean
frontend npm test                                                   54 passed
frontend npm run build                                              clean
```

Manual browser check performed against seeded `core-regression-bundle` data. Every figure on
the dashboard reconciled exactly with the API responses and the seeded scenario: 4
Opportunities at INR 10,00,000; 0 open offers; 3 accepted at INR 7,50,000 with 2 holding a
Work Order shell and 1 awaiting handoff; 2 shells at INR 5,00,000 source value.

## Defect found and fixed during this slice

The first test run left residue: 4 Accounts, 4 Opportunities and 4 DRAFT offers survived,
which then showed up as wrong dashboard figures. Cause was not the cleanup logic but its
placement - a `KeyError` raised during fixture setup fired *before* the `try:` block, so the
`finally` teardown never ran. The fixture now registers each created id as soon as it exists
and performs all setup inside the `try`, so a partial setup failure still cleans up what it
created. Re-verified: 42 passed, zero residue.

## TB-1 fix TB1-600 (4 October 2026): a total per currency

The "Currency" note above held only while every amount was INR, and nothing enforced that: an offer could be saved in
any three letters and its value was added into the rupee totals. With the owner's decision of 4 October 2026 (INR by
default, USD, GBP or EUR when chosen; the Commercial Offer contract's TB1-600 section), each report totals every
currency separately and never converts or adds across currencies.

The reports have no contract file (TB-1 records that gap as TB1-107), so this record is the reference for the
response change:

```text
every report                   currency_code removed: a report no longer has one currency
StatusCount, LabelledCount     total_value -> totals: [{currency_code, amount}], still omitted where the record
                               carries no amount
PipelineReport                 opportunity_total_value -> opportunity_totals
OpenOffersReport               open_offer_total_value -> open_offer_totals
AcceptedOfferPurposeRow        total_value -> totals
AcceptedOffersReport           accepted_total_value -> accepted_totals
                               awaiting_handoff_value -> awaiting_handoff_totals
WorkOrderHandoffReport         source_offer_total_value -> source_offer_totals
HandoffRow                     + source_offer_currency_code
```

Every `totals` list starts with INR, which is always there, at zero if need be. Another currency is listed only when a
record in that group is in it - the owner's instruction was that the dashboard shows only INR unless other currencies
are actually used - so a dashboard where everything is in INR looks as it did. Opportunities carry no currency; their
value is INR. The SQL groups each `SUM` by the offer's currency, and `reports/service.py` builds the lists
(`_currency_totals`).

On screen, an amount with more than one currency shows each total, joined by " · " (for example
"₹12,34,000 · $5,000"). The line under the title says "All amounts in INR." when nothing is in another currency, and
"Each currency is totalled separately; nothing is converted." otherwise. `test_reports_api.py` now reconciles every
breakdown currency by currency, and moves an offer from INR to USD to prove its value leaves the INR total and forms a
USD total of its own.
