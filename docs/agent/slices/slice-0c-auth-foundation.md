# Slice 0C - Authentication Foundation

## Goal

Add simple seeded-user authentication and role-check foundations before implementing CRM business modules.

## Scope

Includes:

- password hashing helper;
- minimal JWT creation and verification;
- seed users for each initial role;
- `/api/auth/login`;
- `/api/auth/me`;
- `/api/auth/roles` restricted to Admin;
- role dependency helper;
- frontend login smoke page;
- frontend protected endpoint smoke check from Accounts placeholder;
- backend tests for success and failure paths.

## Out of scope

- production identity provider integration;
- password reset;
- user management UI;
- refresh tokens;
- audit logging of login events;
- Account/business_party implementation.

## Seed users

```text
admin1 / password       Admin
sales1 / password       Sales User
manager1 / password     Sales Manager
finance1 / password     Finance User
ops1 / password         Operations User
readonly1 / password    Management / Read Only
```

These are development seed users only.

## Backend routes

```text
POST /api/auth/login
GET  /api/auth/me
GET  /api/auth/roles
```

## Completion criteria

Slice 0C is complete when:

- backend starts and applies the 0C seed migration;
- login succeeds for `admin1 / password`;
- bad password returns 401;
- `/api/auth/me` requires a bearer token;
- `/api/auth/roles` requires Admin;
- frontend login page can sign in;
- frontend Accounts placeholder can call `/api/auth/me`;
- backend tests pass;
- Slice 0A and 0B smoke URLs still work.