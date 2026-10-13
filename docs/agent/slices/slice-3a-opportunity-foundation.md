# Slice 3A - Opportunity Foundation

## Goal

Create Opportunity as its own CRM foundation object so that the project can later implement Lead conversion, Opportunity stage updates, quote/commercial offer creation and downstream handoffs without mixing those concerns into Lead.

## Scope

```text
- Add crm_opportunity table.
- Seed Opportunity workflow statuses.
- Add Opportunity backend create/list/get API routes.
- Add OpportunityCreated business event.
- Add minimal frontend list/create/read-only profile pages.
- Add backend API tests for happy path, permissions, validation and not-found behavior.
- Update contract, acceptance and continuity docs.
```

## Out of scope

```text
- Lead conversion to Account / Qualified Prospect.
- Lead conversion to Opportunity.
- Opportunity update or stage movement.
- Quote / Commercial Offer creation.
- Approval workflow.
- Credit checks or exposure tracking.
- Work Order handoff.
- Duplicate matching.
- Assignment queues, tasks or reminders.
```

## Backend contract

Routes:

```text
POST /api/opportunities
GET  /api/opportunities
GET  /api/opportunities/{public_id}
```

Create roles:

```text
ADMIN
SALES_USER
SALES_MANAGER
```

Read roles:

```text
ADMIN
SALES_USER
SALES_MANAGER
FINANCE_USER
OPERATIONS_USER
MANAGEMENT_READ_ONLY
```

Business event:

```text
OpportunityCreated
source_module = opportunities
record_type = opportunity
```

## Frontend contract

Routes:

```text
/opportunities
/opportunities/new
/opportunities/[opportunityId]
```

UI must make it clear that Slice 3A is a foundation slice and does not perform conversion, quote creation, approvals, credit checks or Work Order handoff.

## Data model notes

`crm_opportunity` includes nullable internal link columns for future handoff compatibility:

```text
business_party_id
source_lead_id
```

Slice 3A manual creation leaves these fields empty. A later conversion slice may populate them deliberately.

## Minimum acceptance gate

```text
1. Alembic head/current visible and upgrade applies cleanly.
2. Backend pytest passes.
3. Frontend build passes.
4. Frontend test script passes.
5. Manual happy path: Sales user creates Opportunity, sees it in list, opens profile.
6. Manual permission check: Finance user can view/list but cannot create.
7. Obvious validation check: missing name or invalid status/source/value is blocked.
8. Docs and NEXT_STEPS updated.
```