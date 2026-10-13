# Slice 2A Acceptance - Lead Foundation

## Automated checks

```text
alembic heads shows 20260704_0011
alembic upgrade head succeeds
backend pytest passes
frontend build passes
frontend test script passes
```

## Manual foundation checks

```text
Login as sales1 or admin1.
Open /leads.
Open /leads/new.
Create one manual Lead with company name and requirement summary.
Confirm the Lead appears in the list.
Confirm dashboard/sidebar Lead links work.
Login as finance1, ops1 or readonly1.
Confirm Leads are visible but Lead create form is unavailable.
```

## Deferred checks for later agents

```text
Detailed duplicate detection
Lead qualification statuses
Conversion to Account / Opportunity
External ingestion and tender capture
Lead assignment rules
Lead scoring
```
