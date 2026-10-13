# Slice 6E.2 - Frontend Next.js Security Patch Upgrade

## Purpose

Upgrade the frontend Next.js dependency from the vulnerable `15.1.3` baseline to the safest available patch within the compatible `15.1.x` line.

This is a narrow platform/security dependency patch. It does not intentionally change application behavior.

## Scope

In scope:

- Inspect frontend dependency files.
- Upgrade `next` from `15.1.3` to a patched `15.1.x` target.
- Update the frontend lock file consistently.
- Run frontend build, frontend test script and a Next.js version check.
- Record the security patch decision for future agents.

Out of scope:

- No backend code changes.
- No database model or migration changes.
- No API route changes.
- No business behavior changes.
- No T&C feature changes.
- No frozen Slice 6D.1 Accepted Offer -> Work Order handoff contract changes.
- No broad dependency upgrade outside the narrow Next.js patch target.

## Dependency change

The original frontend dependency was:

```text
next@15.1.3
```

The initial target was `15.1.9` because the advisory noted that as a fixed version for the `15.1.x` line. During install, npm still emitted a Next.js security warning for `15.1.9`, and `npm view next versions --json` showed later `15.1.x` releases were available.

The final selected version is:

```text
next@15.1.12
```

This keeps the upgrade inside the `15.1.x` patch line while moving beyond `15.1.9`.

## Lock file

The frontend did not have a committed `package-lock.json` before this slice. Running npm install created `frontend/package-lock.json`, which now records the resolved `next@15.1.12` dependency tree.

## Verification

Commands run:

```powershell
docker compose run --rm frontend npm install next@15.1.12 --save-exact
docker compose run --rm frontend npm ls next
docker compose run --rm frontend npm audit --omit=dev
docker compose run --rm frontend npm run build
docker compose run --rm frontend npm test
```

Result:

- `npm ls next` resolves `next@15.1.12`.
- `npm run build` passes with Next.js 15.1.12.
- Build output includes `/`, `/terms-and-conditions` and `/commercial-offers`.
- `npm test` passes; the current frontend test script reports that automated frontend tests are not configured.

## Residual audit note

The direct npm install warning seen for `next@15.1.3` and `next@15.1.9` did not appear when installing `next@15.1.12`.

However, `npm audit --omit=dev` still reports Next.js and `postcss` advisories and recommends `next@15.5.20`, which is outside this slice's requested same-line `15.1.x` patch scope. A broader Next.js minor upgrade should be handled as a separate compatibility slice if the project owner decides to pursue full npm audit cleanup.

## Backend impact

Backend and Alembic tests were not required because no backend, API, database, migration or runtime configuration files were changed.
