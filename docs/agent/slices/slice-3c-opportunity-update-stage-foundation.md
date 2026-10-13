# Slice 3C - Opportunity Update / Stage Foundation

## Goal

Add a narrow, production-style foundation for updating Opportunity fields and moving Opportunity stage/status before Lead conversion and commercial-offer work begins.

## Scope

```text
- Add PUT /api/opportunities/{public_id}.
- Allow Sales/Admin roles to update foundation fields already present in crm_opportunity.
- Allow early Opportunity stage/status movement using existing workflow_status seed values.
- Record OpportunityUpdated business events.
- Record OpportunityStageChanged when status changes.
- Add a role-aware edit/stage form on the Opportunity profile page.
- Keep read-only roles able to view Opportunities without update actions.
- Update contracts, acceptance and continuity docs.
```

Editable foundation fields:

```text
opportunity_name
opportunity_source
source_reference
customer_requirement_summary
estimated_value
expected_close_date
opportunity_status_code
owner_user_public_id        backend contract only; not exposed in current UI
```

Allowed Slice 3C status movement:

```text
NEW
NEEDS_REVIEW
QUALIFIED
QUOTE_PENDING
ON_HOLD
LOST
```

`WON` and `CLOSED` are deliberately deferred.

## Out of scope

```text
- New database migration.
- Lead conversion to Account / Qualified Prospect.
- Lead conversion to Opportunity.
- Account linkage workflow.
- Quote / Commercial Offer creation.
- Approval workflow.
- Credit checks or exposure tracking.
- Work Order handoff.
- Duplicate matching.
- Assignment queues, tasks or reminders.
```

## Backend contract

```text
PUT /api/opportunities/{public_id}
```

Request body supports partial updates using the foundation fields above.

Successful response:

```text
{
  "opportunity": { ...OpportunityResponse },
  "events": [ ...business event summaries... ]
}
```

Update roles:

```text
ADMIN
SALES_USER
SALES_MANAGER
```

Read roles remain unchanged:

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

Sales/Admin users see an `Edit Opportunity / Stage` action. Read-only users do not.

The edit form must stay narrow and must not introduce quote, approval, credit or Work Order actions.

## Business event rule

Any successful update creates:

```text
OpportunityUpdated
```

A status change additionally creates:

```text
OpportunityStageChanged
```

Business event payloads must not store passwords, tokens or secrets.

## Minimum acceptance gate

```text
1. No migration is added.
2. Backend pytest passes.
3. Frontend production build passes.
4. Frontend test script passes.
5. Manual happy path: Sales user updates an Opportunity field and changes status to QUALIFIED or QUOTE_PENDING.
6. Manual permission check: Finance user can view but cannot update an Opportunity.
7. Manual validation check: blank Opportunity name or deferred WON status is rejected.
8. Docs and NEXT_STEPS are updated.
```
