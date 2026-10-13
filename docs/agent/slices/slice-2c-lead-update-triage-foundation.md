# Slice 2C - Lead Details Update Foundation

## Objective

Add controlled early Lead update and review without implementing qualification, conversion or Opportunity creation.

## Included

```text
PUT /api/leads/{public_id}
Lead details status seed rows
Editable Lead Details section on /leads/[leadId]
Role-aware update form
LeadUpdated business event
LeadStatusChanged business event when status changes
LeadAssigned business event when assignment field changes
Backend tests
Lead contract and continuity updates
```

## Excluded

```text
Qualified Prospect / Account creation
Opportunity creation
Lead conversion workflow
Approval workflow
Duplicate matching
Automated assignment rules
Lead scoring
External intelligence checks
Task/activity management
```

## Permission rule

```text
ADMIN / SALES_USER / SALES_MANAGER:
- update early Lead details fields

FINANCE_USER / OPERATIONS_USER / MANAGEMENT_READ_ONLY:
- view Leads only
```

## Notes

`assigned_to_user_public_id` remains a simple public-ID field for now. Formal user lookup, queues, territory assignment and reassignment approval are future slices.


