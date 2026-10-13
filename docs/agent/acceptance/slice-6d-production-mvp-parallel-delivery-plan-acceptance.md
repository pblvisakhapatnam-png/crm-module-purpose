# Slice 6D Acceptance - Production MVP Scope and Parallel Delivery Plan

## Automated checks

Run from repository root:

```powershell
git diff --check
```

Backend and frontend tests are not required if this slice remains documentation-only.

If any application code changes, run the relevant tests and record why code changed.

## Documentation review checklist

Starting files:

```text
docs/planning/PRODUCTION_MVP_SCOPE_AND_PARALLEL_DELIVERY_PLAN.md
docs/planning/CRM_HIRING_PARALLEL_WORKSTREAM_SPLIT.md
docs/planning/MVP_DEFERRED_SCOPE_DECISIONS.md
docs/planning/CRM_TO_HIRING_HANDOFF_FREEZE_CHECKLIST.md
```

Positive path:

```text
1. Confirm production-grade MVP is defined as secure, auditable, tested, deployable, usable and limited in scope.
2. Confirm CRM MVP scope includes Lead, Account, Opportunity, Commercial Offer, Commercial Offer lines, pricing evidence, lifecycle, handoff, events, roles and reports.
3. Confirm Hiring MVP scope includes Work Order header/lines, handoff consumption, Customer Master checkpoint, equipment assignment, crew eligibility, log sheet, limited billing, invoice-support handoff, events, roles and reports.
4. Confirm the freeze checklist covers Work Order header/line payloads, Account/Customer identity, PAN/GSTN/site/billing terms, Commercial Offer references, line identity, credit reference, document links, status/events and authorization.
5. Confirm deferred scope includes AI ingestion, external integrations, advanced rate benchmarking, analytics, sales commission, complex approval configurator, full credit engine, full revisions, full T&C automation, SharePoint automation, GPS/fuel/maintenance integrations, complex hired-equipment vendor workflows and profitability analytics.
6. Confirm the parallel delivery model separates CRM, Hiring, Platform/NFR and UAT/documentation workstreams.
7. Confirm the recommendation says 1-2 months is feasible only as a tightly scoped production MVP, not full ERP scope.
```

Out-of-scope check:

```text
Confirm no backend, frontend, Docker, database, migration, test or contract files changed.
```

Expected result:

```text
The planning pack can be used by PBL and the vendor to decide whether a 1-2 month production MVP timeline is acceptable and what must be deferred.
```

## Acceptance status

```text
Pending human documentation review.
```
