# Slice 9A Acceptance - CRM Operational Reporting and Dashboard Foundation

Written so a later tester can perform regression/UAT without this session's chat history.

## Preconditions

Stack running (`docker compose up -d`), Alembic at `20260906_0032 (head)` - the PF-1A-E3 head.
This slice adds no migration and does not move the head.

If `alembic current` reports an older revision than `alembic heads`, rebuild the backend image:
`alembic/` is baked into the image rather than bind-mounted, so a merged migration is invisible
until `docker compose up -d --build --force-recreate backend` runs. Seed demo data first so the figures are non-zero:

```powershell
docker compose exec backend python -m tooling.smoke_data seed --scenario core-regression-bundle
```

Record the `run_id` printed; clean up afterwards with
`docker compose exec backend python -m tooling.smoke_data cleanup --run-id <run_id>`.

## Automated checks

| Check | Command | Expected |
| --- | --- | --- |
| Focused suite | `docker compose exec backend pytest tests/test_reports_api.py -q` | 42 passed |
| Full backend regression | `docker compose exec backend pytest -q` | 1025 passed, 0 failed |
| Alembic unchanged by this slice | `docker compose exec backend alembic current` | `20260906_0032 (head)` |
| Frontend typecheck | see `AGENTS.md` frontend sequence | clean |
| Frontend tests | see `AGENTS.md` frontend sequence | 54 passed |
| Frontend build | see `AGENTS.md` frontend sequence | clean |

## Manual positive path

Test user: `sales1` / `password` (SALES_USER). Starting URL: `http://localhost:3000/`.

1. Log in and open the dashboard.
2. Confirm an **Operational summary** card appears above the existing navigation cards.
3. Confirm four KPI tiles render: Open opportunities, Open offers, Awaiting handoff, Work
   Order shells - each with a count and an INR amount.
4. Confirm amounts use Indian digit grouping (for example `₹10,00,000`, not `₹1,000,000`).
5. Confirm the "Live figures as at ..." timestamp is in Asia/Kolkata local time, not UTC.
6. Confirm four sections render: Pipeline, Open Commercial Offers, Accepted Commercial Offers,
   Work Order handoff.
7. In Work Order handoff, confirm each row shows both the Work Order code and its **source
   Commercial Offer code**, and that both link through to their detail pages.
8. Click **Refresh** and confirm the timestamp updates.
9. Confirm the pre-existing navigation cards (Lead, Account, Opportunity, Commercial Offer,
   T&C, Work Order shell, Traceability guard) are still present and unchanged, and that the
   role-aware create shortcuts still appear for this role.

## Reconciliation check (the point of the slice)

Cross-check the dashboard against the API for the same session:

```powershell
curl -s -H "Authorization: Bearer <token>" http://localhost:8000/api/reports/accepted-offers
```

`with_work_order_shell + awaiting_handoff` must equal `accepted_total`, and both must match
what the Accepted Commercial Offers table shows. Against `core-regression-bundle` the expected
figures are 3 accepted, 2 with a shell, 1 awaiting handoff.

## Manual permission path

1. Log in as `readonly1` / `password` (MANAGEMENT_READ_ONLY).
2. Confirm the Operational summary renders in full - read-only roles are intended to see every
   report.
3. Confirm the role-aware create shortcuts are hidden, as before this slice.
4. Repeat for `finance1` and `ops1`; all four reports must load for every seeded role.

## Manual negative paths

1. Log out (or clear `pbl_auth_token`) and reload the dashboard. Expect the message "Login to
   see live pipeline, offer and handoff figures." - not a crash or an error banner.
2. Stop the backend (`docker compose stop backend`), reload the dashboard while logged in.
   Expect a readable error message and a working **Try again** button. Restart the backend and
   confirm Try again recovers.
3. Request an out-of-range limit:
   `GET /api/reports/work-order-handoff?limit=0` and `?limit=101` must both return `422`.
4. Request any report without an `Authorization` header; expect `401`.

## Empty-state check

Against a database with no CRM records (or after cleanup), confirm each section shows its
empty-state text rather than a broken table: "No Opportunities recorded yet.", "No Leads
recorded yet.", "No open Commercial Offers.", "No accepted Commercial Offers yet.", "No Work
Order shells yet."

## Explicitly not covered by this slice

- Potential/Firm exposure reporting - `CEX-001` is approved but unimplemented; there is no
  exposure data to report and no placeholder was invented.
- Export to CSV/print.
- Date-range filters, owner/segment breakdowns, charts, drill-through report pages.
- Any write path, business event, lifecycle change, migration or permission change.

## Deferred manual checks

- Performance against production-scale data. The aggregates are unindexed `GROUP BY` scans over
  the full tables, which is appropriate at prototype volume but should be re-measured before
  production use, and may then need supporting indexes (which would require a migration).
- Playwright coverage. The TE-1 suite does not yet assert dashboard figures; adding a spec
  should follow the existing manifest-driven pattern rather than a new seeding mechanism.

## TB-1 fix TB1-600 (4 October 2026): a total per currency

Test user: `sales1` / `password` (SALES_USER). Starting URL: `http://localhost:3000/`.

1. Open the dashboard. Where every offer is in INR, the Operational summary looks as before: one rupee amount per
   tile and row, and "All amounts in INR." under the title.
2. Open a Draft Commercial Offer, edit it, choose `USD - US dollar` in Currency and save. Back on the dashboard, the
   Open offers tile shows two amounts, the rupee total and a dollar total (for example "₹1,25,000 · $5,000"); the
   offer's value has left the rupee total. The line under the title reads "Each currency is totalled separately;
   nothing is converted."
3. Edit the offer back to `INR - Indian rupee`. The dollar total disappears.

Negative path: the Currency box offers only INR, USD, GBP and EUR; there is nothing to type. A request sent with
another code (for example `AUD`) is refused with `Currency must be one of INR, USD, GBP, EUR.` - covered by
`backend/tests/test_operating_currency.py`.
