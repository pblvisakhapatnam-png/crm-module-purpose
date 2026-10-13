# Slice 0D - Business Events Foundation

## Goal

Activate the reusable business event foundation before Account/business_party implementation begins.

## Scope

Includes:

- business event schemas;
- business event repository/service helpers;
- protected recent-events API;
- login success event recording;
- login failure event recording without storing passwords;
- frontend Events page for smoke testing;
- backend tests for event recording and role restriction.

## Out of scope

- full audit log engine;
- approval workflow events;
- Account/business_party events;
- document events;
- event export;
- event filtering beyond recent-events limit.

## Backend routes

```text
GET /api/events/recent?limit=25
```

Access:

```text
Admin
Management / Read Only
```

## Event names introduced

```text
UserLoginSucceeded
UserLoginFailed
```

## Business rules

- Login success should create a business event.
- Login failure should create a business event.
- Passwords, tokens and secrets must not be stored in business event payloads.
- Sales User should not be able to view recent events.
- Admin and Management / Read Only may view recent events.

## Completion criteria

Slice 0D is complete when:

- backend starts;
- `/api/health` works;
- `/api/platform/db-health` works;
- user can login through frontend;
- `/events` page can load recent events as Admin;
- Sales User is denied access to recent events;
- backend tests pass;
- Slice 0A, 0B and 0C smoke checks still work.