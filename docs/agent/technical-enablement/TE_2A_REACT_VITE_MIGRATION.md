# TE-2A - React and Vite Web Migration

## Status

**Implemented, corrected, accepted after independent review and integrated on `main` as commit `5c87e07`.** One
controlled technical-enablement lane, executed as two sequential implementation sessions on the same branch
`technical-enablement/te-2a-react-vite-migration`. Part 1 (commit `59af44e`) added the parallel
Vite application and was independently reviewed and accepted. Part 2 performed the runtime cutover,
removed Next.js and passed the full regression gate. The independent review of the uncommitted Part 2 diff on
13 August 2026 and raised three findings, corrected by pass `TE-2A.2-C1`.

TE-2A is integrated. The current gate is explicit confirmation that PostgreSQL is the frozen
production database; TE-2B follows only after that confirmation. See
"Final evidence" below and
`docs/agent/acceptance/te-2a-react-vite-migration-acceptance.md`.

## Objective

Replace the Next.js App Router/runtime with a client-rendered React 19 application using Vite and
React Router while preserving the existing routes, UI, authentication behavior, relative `/api`
calls, business workflows and Playwright regression coverage.

TE-2A changes the web framework only. FastAPI remains the sole authoritative backend. This work
does not add business behavior, alter API contracts, change the database or redesign screens.

## Why two sessions

The frontend contains 24 route pages, one App Router layout and approximately 16,000 lines. Only eight pages import
`next/navigation`, but Docker, Compose, API proxying, build commands, Playwright warm-up and active
agent guidance also depend on Next.js.

Splitting the work gives the independent reviewer a reviewable checkpoint before runtime cutover:

```text
Part 1: complete parallel Vite application builds/tests; Next remains default runtime
  -> independent review of the commit verifies Vite route/build evidence
Part 2: move/cut over runtime, Docker, Compose and E2E; remove Next; full regression
  -> independent review accepts TE-2A
```

Both parts use one branch and one implementation owner. They are not parallel slices and must not
be developed in separate worktrees.

## Current inventory

```text
frontend/app/                         24 page.tsx routes plus layout/globals.css
frontend/components/                  SessionActions shared shell component
frontend/package.json                 Next 15.1.12; React 19; no real frontend test runner
frontend/next.config.ts               /api -> http://backend:8000 rewrite
frontend/Dockerfile                   next dev on port 3000
docker-compose.yml                    .next named volume
e2e/playwright.config.ts              next dev cold-compile global setup and comments
e2e/tests/global-setup.ts             Next route warm-up only
.env.example                          stale NEXT_PUBLIC_API_BASE_URL
init-skeleton.ps1                     generates an obsolete Next frontend skeleton
```

Direct Next runtime imports are limited to:

- `frontend/app/layout.tsx`: `Metadata`;
- eight dynamic detail/create pages: `useParams` from `next/navigation`.

Browser code already uses relative `/api` URLs. Existing ordinary anchors, query strings,
`window.location` actions and origin-aware return links must preserve their behavior during this
framework migration.

## Target frontend shape

Final naming may vary slightly where the implementation agent identifies a simpler equivalent, but the completed
application should have one obvious Vite entry point and explicit route table:

```text
frontend/index.html
frontend/vite.config.ts
frontend/src/main.tsx
frontend/src/router.tsx
frontend/src/layout/AppShell.tsx
frontend/src/pages/...
frontend/src/components/...
frontend/src/styles/globals.css
```

Required final routes:

```text
/
/login
/accounts
/accounts/new
/accounts/:accountId
/leads
/leads/new
/leads/:leadId
/opportunities
/opportunities/new
/opportunities/:opportunityId
/commercial-offers
/commercial-offers/new
/commercial-offers/:commercialOfferId
/commercial-offers/:commercialOfferId/related-offers/new
/terms-and-conditions
/work-orders
/work-orders/new
/work-orders/:workOrderId
/work-orders/:workOrderId/amendments/new
/work-orders/:workOrderId/amendments/:amendmentId
/documents
/workflow-statuses
/events
```

React Router supplies dynamic parameters. Query strings and current browser-history behavior stay
compatible. Direct requests/reloads of deep links must serve the SPA, not return a server 404.

## Part 1 - Parallel Vite application

Part 1 adds a complete Vite application and proves it compiles while leaving the current Next
scripts, Docker/Compose runtime and existing `frontend/app/` pages operational.

Expected approach:

- add Vite, the React plugin, React Router and a small real Vitest route test;
- add `dev:vite`, `build:vite` and `typecheck:vite` scripts without replacing the existing
  default `dev`/`build` scripts yet;
- create `index.html`, Vite configuration, entry point, shell and explicit route definitions;
- reuse existing page modules during this intermediate checkpoint instead of duplicating 16,000
  lines;
- use a clearly temporary Vite-only compatibility alias for the eight `next/navigation`
  `useParams` imports if needed, backed by React Router;
- configure the Vite development proxy to use `BACKEND_INTERNAL_URL`, defaulting to
  `http://localhost:8000` for host use; browser code continues to call relative `/api`;
- add route-table tests that prove static and dynamic URL examples match the expected page;
- prove both the Vite build and unchanged Next build pass.

Part 1 must not:

- switch Docker/Compose/default scripts to Vite;
- delete or move Next files;
- rewrite all page UI or replace working anchors merely for style;
- change backend, API, schema, business behavior or Playwright scenarios;
- update active instructions as though cutover is complete; or
- merge to `main` independently.

## Independent review checkpoint after Part 1

The independent review examines the actual commit and independently checks:

- the route table covers every current route exactly once;
- Vite uses React Router rather than an invented router;
- the compatibility layer is narrow, temporary and does not leak into business code;
- relative `/api` proxying works without exposing an internal host to browser code;
- no current Next runtime behavior was broken;
- route tests can fail when a route mapping is removed or wrong; and
- Part 2 scope is adjusted for any discoveries before the next implementation package is issued.

## Part 2 - Cutover, cleanup and regression

Part 2 is issued only after Part 1 is accepted. Part 2:

- moves pages/components/styles into the final Vite source structure with history-preserving
  moves where practical;
- replaces the eight Next parameter imports directly with React Router and removes the temporary
  compatibility alias;
- removes obsolete `"use client"` directives;
- switches default package scripts and TypeScript configuration to Vite;
- removes Next dependency/config/type/build artifacts;
- updates Dockerfile and Compose, removes the `.next` volume and supplies
  `BACKEND_INTERNAL_URL=http://backend:8000` to the Vite development runtime;
- updates/removes the Next cold-compile Playwright global setup and comments without weakening
  scenario coverage or adding retries;
- updates `.env.example`, `init-skeleton.ps1`, frontend README and active agent/tooling guidance;
- runs the full frontend build/test, backend regression, Playwright regression, Docker clean-start
  and manual role/permission checks; and
- records completion in acceptance, continuity and next-step documents.

Vendor-demo preflight is explicitly **not** a TE-2A required check. Vendor-demo tooling
(`scripts/vendor-demo.ps1`), vendor-demo data and both vendor-review repositories remain untouched
by this package, and vendor review is deferred until PBL explicitly authorizes it. The ordinary
regression run may still collect the vendor-demo spec, but all nine of its tests skip because no
vendor manifest is supplied.

Historical continuity records remain historical. Do not rewrite old slice notes merely because
they accurately said Next.js was used at that time.

## Final shape delivered

```text
frontend/index.html                       document shell, title, description
frontend/vite.config.ts                   build, /api proxy, allowed hosts, Vitest
frontend/tsconfig.json                    single Vite/React TypeScript configuration
frontend/src/main.tsx                     entry point; StrictMode + RouterProvider
frontend/src/router.tsx                   route objects nested under the shell
frontend/src/routes.tsx                   route table, 24 routes + catch-all
frontend/src/routes.test.ts               route-table regression tests (54)
frontend/src/layout/AppShell.tsx          sidebar, navigation, <Outlet />
frontend/src/components/SessionActions.tsx
frontend/src/pages/**                     24 page modules + NotFoundPage
frontend/src/styles/globals.css
```

Removed: `frontend/app/**`, `frontend/components/**`, `frontend/next.config.ts`,
`frontend/next-env.d.ts`, `frontend/tsconfig.vite.json`, `frontend/src/compat/next-navigation.ts`,
the `next` dependency, the `frontend-next` and `frontend-node-modules` Compose volumes, and
`e2e/tests/global-setup.ts`.

## Final evidence

```text
docker compose exec backend alembic current/heads   20260713_0029 (head), unchanged
docker compose exec backend pytest                  218 passed
npm run typecheck                                   pass, no diagnostics
npm test                                            pass, 1 file / 54 tests
npm run build                                       pass, 69 modules, 668.67 kB
docker compose build --no-cache frontend            pass
docker compose up -d db backend frontend            all healthy
/login, deep link, /api/health through :3000        200, 200 (SPA fallback), 200
built bundle scan                                   no backend:8000, localhost:8000,
                                                    BACKEND_INTERNAL_URL or next/dist
.\scripts\run-e2e.ps1                               12 passed, 9 skipped (@demo-preflight,
                                                    no vendor manifest), cleanup clean, 52.2s
git diff --check                                    clean
```

Two defects were found and fixed during Part 2 validation, both in the new Vite/Docker
configuration rather than in CRM business behavior:

- `vite preview` rejected the `Host: frontend` header the Playwright container uses, failing all
  12 business specs. Fixed with an explicit `allowedHosts` allowlist (`localhost`, `frontend`,
  plus anything in `ALLOWED_HOSTS`) rather than by disabling the DNS-rebinding check.
- The original Compose source bind mount would have shadowed the image-built `dist/` and
  `node_modules`. It was removed, and `frontend/README.md` documents the explicit-mount dev-server
  and check commands that replace it.

## Strict Mode

Part 1 omitted `React.StrictMode` on an inaccurate rationale. The independent review established that Next 15.1.12
enables App Router Strict Mode by default when `reactStrictMode` is unset, so omitting it would
have relaxed development diagnostics rather than preserved them. Part 2 wraps `RouterProvider` in
`StrictMode` and removed the incorrect comment.

The application was then exercised in Vite development mode with Strict Mode active. Read effects
double-invoke, which is the intended development-only diagnostic and matches the previous runtime;
those requests are idempotent GETs and are absent from production builds. `POST /api/auth/login`
fired exactly once. A code-level scan confirms no page issues a `POST`, `PUT`, `DELETE` or `PATCH`
from inside a `useEffect` - every mutation is in an event handler, which Strict Mode does not
double-invoke - so no duplicate business action or duplicate record is possible through this
mechanism. No effect was suppressed and no business rule was weakened.

## Known limitations carried forward

- The build emits a single 668.67 kB JavaScript chunk, above Rollup's 500 kB advisory. Route-level
  code splitting was explicitly out of TE-2A scope and remains available as a later performance
  slice.
- `docs/agent/contracts/platform-foundation.md` still describes the prototype platform, including
  Next.js. It is a contract file and outside TE-2A's allowed-files boundary; reconciling it is part
  of the TE-2C gate ("obsolete Next.js and SQL Server assumptions are removed or explicitly
  documented").
- Compose serves the built application with `vite preview`. That is adequate for local development,
  the demo runbook and the Playwright suite, but final hosting-provider selection and static-server
  hardening remain out of scope.
- Playwright timeouts were left at their TE-1 values rather than tightened; the suite now completes
  in about 52 seconds with `retries: 0`.

## Authorization, events and data

No authorization rule changes. The browser token key remains `pbl_auth_token`; backend
authorization remains authoritative. No business event, API or database change is expected.

## Final stop conditions

Stop and report instead of guessing if:

- a current route cannot be represented without changing its public URL or workflow;
- Vite proxy/deep-link behavior would require an API or deployment-contract change;
- an existing Playwright failure indicates a pre-existing business regression rather than a
  migration issue;
- package installation requires an incompatible React downgrade or an unapproved application
  state/data-fetching library; or
- unrelated user changes appear in owned files.

## Completion boundary

TE-2A is complete only after Part 2 and the acceptance checklist pass **and** the independent review accepts the
diff. Part 1 alone is neither a release nor an approved intermediate state for `main`.

Both parts are implemented, the `TE-2A.2-C1` corrections are applied, and the independent review accepted the
corrected package after independent verification. Commit `5c87e07` is integrated on `main`. The
current gate is explicit confirmation that PostgreSQL is the frozen production database; TE-2B
follows only after that confirmation.

TE-2A is a technology migration, not a production-readiness claim. Vendor review remains deferred
until PBL explicitly authorizes it, and no vendor-demo data, vendor branch or vendor-review
repository was touched by this package.
