# Slice 3B - Opportunity Detail / Profile Shell

## Goal

Stabilize the Opportunity detail page as a clear read-only profile shell so users can understand the Opportunity, its current workflow position, its Account/Lead context, and its downstream boundaries before the project adds update/stage movement and Lead conversion.

## Scope

```text
- Replace the minimal Slice 3A Opportunity detail view with a structured profile shell.
- Use the existing GET /api/opportunities/{public_id} API response.
- Show profile snapshot, workflow position, Account context, source/enquiry context, requirement, commercial readiness, next workflow boundaries, and audit traceability.
- Keep the page role-aware for event-page navigation without bypassing backend event permissions.
- Keep the Opportunity detail page read-only.
- Update contract, acceptance and continuity docs.
```

## Out of scope

```text
- New database migration.
- New backend route.
- Opportunity update or stage movement.
- Lead conversion to Account / Qualified Prospect.
- Lead conversion to Opportunity.
- Quote / Commercial Offer creation.
- Approval workflow.
- Credit checks or exposure tracking.
- Work Order handoff.
- Duplicate matching.
- Assignment queues, tasks or reminders.
```

## Backend contract

No backend API change is required in Slice 3B.

The page uses the existing route:

```text
GET /api/opportunities/{public_id}
```

Read roles remain enforced by the backend route:

```text
ADMIN
SALES_USER
SALES_MANAGER
FINANCE_USER
OPERATIONS_USER
MANAGEMENT_READ_ONLY
```

## Frontend contract

Route:

```text
/opportunities/[opportunityId]
```

Required read-only sections:

```text
Profile snapshot
Workflow position
Account context
Source / enquiry context
Customer requirement
Commercial readiness
Next workflow boundaries
Audit and traceability
```

The page must make it clear that Lead conversion, stage updates, quote/commercial offer, approvals, credit checks and Work Order handoff are deferred.

## Business event rule

Slice 3B is read-only and does not create a new business event.

The profile may link to the Events page only for roles that already have access to Events. Backend Events authorization remains authoritative.

## Minimum acceptance gate

```text
1. No migration is added.
2. Backend route contract remains unchanged.
3. Backend pytest passes as regression check if run.
4. Frontend production build passes.
5. Frontend test script passes.
6. Manual happy path: Sales user opens an existing Opportunity profile and sees the structured shell.
7. Manual permission check: Finance user can view the profile but sees read-only messaging and no create/update action.
8. Admin/Management event navigation is role-aware and does not bypass backend event permissions.
9. Docs and NEXT_STEPS are updated.
```
