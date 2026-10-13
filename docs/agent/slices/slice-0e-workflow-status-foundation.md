# Slice 0E - Workflow Status Foundation

## Goal

Activate reusable workflow status reference data before Account/business_party implementation begins.

## Scope

Includes:

- seed Account/business_party workflow statuses;
- protected workflow status API;
- protected workflow module API;
- frontend Workflow Statuses smoke page;
- backend tests for authentication and status lookup;
- documentation updates.

## Out of scope

- Account/business_party table;
- Account status transitions;
- approval workflow rules;
- workflow history;
- status change business events;
- UI controls to edit workflow statuses.

## Backend routes

```text
GET /api/workflow/statuses?module=business_party&active_only=true
GET /api/workflow/modules?active_only=true
```

Access:

```text
Any authenticated user
```

Reason:

Workflow status values are reference data required by many screens. Editing them will be restricted later, but reading them should be allowed to users who can use the application.

## Seeded module

```text
business_party
```

This is the internal backend/domain module. The user-facing label will be Account.

## Seeded Account statuses

```text
DRAFT
LEAD_LINKED
QUALIFIED_PROSPECT
ACTIVE_PROSPECT
DORMANT
ON_HOLD
BLOCKED
CUSTOMER_ACTIVATION_PENDING
CUSTOMER_ACTIVE
BLACKLISTED
```

## Completion criteria

Slice 0E is complete when:

- backend starts;
- `/api/health` works;
- `/api/platform/db-health` works;
- user can login through frontend;
- `/workflow-statuses` can load Account statuses;
- `/api/workflow/statuses` rejects unauthenticated access;
- Sales User can read status reference data;
- backend tests pass;
- Slice 0A-0D smoke checks still work.