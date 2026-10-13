# Slice 2B - Lead Detail / Profile Shell

## Intent

Create the first read-only Lead profile page and make Lead list rows navigable.

## Implemented

```text
/leads/[leadId] frontend route
Lead list company link to Lead detail page
Read-only Lead summary/profile shell
Contact snapshot section
Requirement summary section
Lead action placeholders
Audit snapshot section
Back to Leads link
Loading, unauthorized, forbidden and not-found messaging
Lead contract update
```

## Backend impact

No backend route, schema or migration change is required in this slice.

Slice 2B uses the existing route from Slice 2A:

```text
GET /api/leads/{public_id}
```

## Role treatment

```text
ADMIN / SALES_USER / SALES_MANAGER:
- can view Lead profile
- see future Sales/Admin action placeholders

FINANCE_USER / OPERATIONS_USER / MANAGEMENT_READ_ONLY:
- can view Lead profile
- see view-only placeholder messaging
```

Backend read permission remains authoritative.

## Explicit exclusions

```text
Lead edit
Lead qualification
Lead conversion
Opportunity creation
Lead assignment workflow
Duplicate matching
Lead tasks/activities
Lead event creation on view
```

## Carry-forward rule

Lead detail page should remain a shell until qualification/conversion contracts are explicitly introduced. Future agents should add new Lead actions as local, role-aware sections with action-specific success/error messages placed beside the triggering action.

