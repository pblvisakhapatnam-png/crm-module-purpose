"""Server-side account administration for the hosted CRM pilot (TE-5).

Creates, disables, re-enables and re-passwords application users, replaces their roles, locks the
six demo users that sign in with the password `password`, and reports any active account that still
accepts that password. Development and CI get those six from its `seed-demo-users` command, which
refuses outside a development APP_ENV; until TB-1 TB1-203 (7 October 2026) Alembic revision
20260629_0002 created them on every database, so a database built before then may still hold them.

Since TB-1 TB1-204 part a (7 October 2026) a password it sets must meet the rules in
`app.modules.identity.password_rules`; a reset, disabling and retiring end every earlier sign-in, as
`end-sign-ins` does without changing the password; and `unlock` lifts the stop that repeated wrong
passwords put on a username.

Run inside the backend container, which already holds the database settings:

    python -m tooling.user_admin --help

Passwords are generated here, hashed with the application's own `hash_password`, and written only
to a credentials file the operator names, with mode 0600. They are never printed, logged or put in
a business event.

Tooling only. Never imported by `app.main` and not reachable through any API route.
"""
