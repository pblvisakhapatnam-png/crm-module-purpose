# Slice 6E.2 Acceptance - Frontend Next.js Security Patch Upgrade

## Acceptance scope

Confirm that the frontend Next.js dependency is upgraded from `15.1.3` to a patched `15.1.x` release without changing application behavior.

## Files expected to change

- `frontend/package.json`
- `frontend/package-lock.json`
- `docs/agent/slices/slice-6e2-frontend-nextjs-security-patch-upgrade.md`
- `docs/agent/acceptance/slice-6e2-frontend-nextjs-security-patch-upgrade-acceptance.md`
- `docs/continuity/SLICE_6E2_FRONTEND_NEXTJS_SECURITY_PATCH_UPGRADE.md`
- `docs/agent/AGENT_HANDOFF.md`
- `docs/agent/FUTURE_SLICES.md`
- `docs/continuity/NEXT_STEPS.md`

## Version acceptance

Expected result:

- `frontend/package.json` pins `next` to `15.1.12`.
- `frontend/package-lock.json` resolves `node_modules/next` to `15.1.12`.
- `docker compose run --rm frontend npm ls next` reports `next@15.1.12`.

Observed result:

- Passed. `npm ls next` reports `next@15.1.12`.

## Build acceptance

Command:

```powershell
docker compose run --rm frontend npm run build
```

Expected result:

- Frontend production build passes.
- Existing routes still build, including `/`, `/terms-and-conditions` and `/commercial-offers`.

Observed result:

- Passed. Next.js 15.1.12 build completed successfully and listed the expected routes.

## Test acceptance

Command:

```powershell
docker compose run --rm frontend npm test
```

Expected result:

- The existing frontend test command completes successfully.

Observed result:

- Passed. The current script prints `Frontend automated tests not configured in Slice 0A`.

## Security warning acceptance

Expected result:

- The direct npm install warning for the older vulnerable Next.js package should not remain for the selected patched `15.1.x` target.

Observed result:

- Passed for the install warning. Installing `next@15.1.12` did not emit the direct Next.js deprecation/security warning seen with `15.1.3` and `15.1.9`.
- Residual note: `npm audit --omit=dev` still reports Next.js and `postcss` advisories and recommends `next@15.5.20`, outside this slice's same-line `15.1.x` patch scope.

## Regression boundary

Confirmed:

- No backend code changed.
- No API routes changed.
- No database models or migrations changed.
- No business behavior changed intentionally.
- No T&C behavior changed intentionally.
- No Slice 6D.1 handoff contract changed.

## Deferred checks

- A future platform/security slice should decide whether to move from `15.1.x` to a later Next.js minor release such as the audit-recommended `15.5.x` line.
- Browser-level manual smoke testing can be repeated after the frontend service is restarted from the new dependency tree.
