# TE-2A Acceptance - React and Vite Web Migration

## Status

Part 1 implemented and accepted on branch `technical-enablement/te-2a-react-vite-migration`.

Part 2 is **implemented, corrected, accepted after independent review and integrated on `main`.**
The complete TE-2A package is commit `5c87e079eba4650a2da1f9e992d8c4a428c940df`, built on the
reviewed Part 1 commit `59af44e44b2169992d5858bd8504e6b010bb5852`.

The independent review of the uncommitted Part 2 diff on 13 August 2026 confirmed the migration
evidence and raised three findings; correction pass `TE-2A.2-C1` addressed all three. The
independent review then verified and accepted the corrected package. At that review point, integration awaited the
PBL-directed Git action. The package was subsequently committed and integrated; explicit
confirmation that PostgreSQL is the frozen production database is now the current gate.

## Part 1 checkpoint

```text
[x] One TE-2A branch is used; main remains unchanged.
[x] Vite/React Router dependencies and lockfile are intentional and reviewed.
[x] Parallel Vite entry point, application shell and explicit route table exist.
[x] Every current public frontend route has a matching static/dynamic route definition.
[x] Vite /api proxy uses BACKEND_INTERNAL_URL; browser requests remain relative /api.
[x] Any next/navigation compatibility shim is Vite-only, minimal and marked for Part 2 deletion.
[x] A real frontend test command protects route matching.
[x] npm run typecheck:vite passes.
[x] npm run test passes.
[x] npm run build:vite passes.
[x] Existing npm run build (Next) still passes.
[x] Vite manual smoke: login, dashboard and one dynamic detail/deep-link reload pass.
[x] No backend, API, schema, business behavior, Docker/Compose default or E2E scenario changed.
[x] Implementation handoff provides commit hash, exact commands/results, self-review and clean status.
[x] The independent review examines the actual diff and records approve/correct/reject.
```

Part 1 must not be merged to `main`.

### Independent Part 1 review

The independent review examined commit `59af44e44b2169992d5858bd8504e6b010bb5852` and approved
it for continuation to Part 2. The Part 1 commit does not need to be rewritten. Part 2 must apply
the Strict Mode correction recorded below before cutover.

Independent checks on 12 August 2026:

```text
git diff main...HEAD --check       pass
npm run typecheck:vite             pass, no diagnostics
npm test                           pass, 1 file / 54 tests
npm run build:vite                 pass, 70 modules
npm run build                      pass, unchanged Next route inventory
Vite /login browser render         pass, shell and form present, no console warnings/errors
Vite dynamic deep-link + reload    pass, Work Order route and shell render after reload
Vite /api/health proxy             pass, HTTP 200 from the backend
Vite bundle internal-host scan     pass, no backend:8000, localhost:8000,
                                    BACKEND_INTERNAL_URL or next/dist string
```

One non-blocking parity issue must be corrected in Part 2. `src/main.tsx` omits
`React.StrictMode` on the stated basis that the current Next development runtime runs effects
once. The installed Next 15.1.12 source defines App Router Strict Mode as enabled by default when
`reactStrictMode` is unset (`__NEXT_STRICT_MODE_APP` in
`next/dist/build/webpack/plugins/define-env-plugin.js`). Part 2 must wrap `RouterProvider` in
`React.StrictMode` and remove the inaccurate single-pass comment. This affects development
diagnostics, not the Part 1 production build or current default Next runtime, so it does not
require a separate Part 1 correction commit.

The Vite build's single 668.67 kB JavaScript chunk remains a non-blocking optimization note. Do
not widen Part 2 into route-level performance work unless the cutover itself requires it.

### Part 1 dependencies added

```text
react-router-dom      7.18.2   dependency
vite                  7.3.6    devDependency
@vitejs/plugin-react  5.2.0    devDependency
vitest                4.1.10   devDependency
@types/node           22.20.1  devDependency (raised from 22.10.5)
```

React 19.0.0, react-dom 19.0.0 and TypeScript 5.7.2 are unchanged. `@types/node` was raised
because Vite 7 declares an optional peer of `^20.19.0 || >=22.12.0` and the previous 22.10.5 pin
failed `npm install` resolution. Vite 7 rather than Vite 8 is deliberate: it keeps the proven
Rollup build pipeline during a migration whose acceptance standard is functional equivalence,
rather than adopting a new default bundler at the same time. Exact versions are pinned; no
`latest` ranges are committed.

### Part 1 commands and results

Run inside the frontend container (`docker compose exec -T frontend sh -c 'cd /app && ...'`),
consistent with the repository's container runtime convention.

```text
npm install --no-audit --no-fund   added 88 packages, changed 4 packages
npm run typecheck:vite             pass, no diagnostics
npm test                           pass, 1 file / 54 tests
npm run build:vite                 pass, 70 modules, dist 668.70 kB (gzip 162.11 kB)
npm run build                      pass, same 24 app routes as before, no pages-router route
git diff --check                   clean
```

Route-test strength was verified by mutation rather than assumed. Temporarily pointing
`accounts.detail` at the Lead detail page failed 1 test; renaming `:workOrderId` to `:woId`
failed 2; deleting the `events` route failed 4. The table was restored and re-run green.

Two independent checks confirm the compatibility shim, not the real Next package, is what the
Vite runtime uses: `tsc --traceResolution` resolves every `next/navigation` specifier to
`/app/src/compat/next-navigation.ts`, and the built bundle contains zero `next/dist` references.
The built bundle also contains no `localhost:8000`, `backend:8000` or `BACKEND_INTERNAL_URL`
string, confirming the proxy target stays server-side.

### Part 1 manual Vite smoke

Vite dev server on port 4173 in a throwaway container
(`docker compose run --rm -d -p 4173:4173 -e BACKEND_INTERNAL_URL=http://backend:8000 ...`), with
the default Next runtime left untouched on port 3000. Data came from the TE-1 harness scenario
`accepted-offer-with-work-order` (run `te1-551a6622`), cleaned up afterwards.

```text
/login                                                    renders shell + form; admin1 sign-in
                                                          succeeds through the relative /api proxy
/                                                         Demo Dashboard renders with role-aware
                                                          create actions
/work-orders/<seeded id>                                  full profile, handoff provenance,
                                                          WorkOrderCreated event (ADMIN) and line
                                                          traceability all load
reload of that dynamic URL (F5)                           identical render, no console errors
/commercial-offers/<id>/related-offers/new                deepest nested route resolves its
                                                          parameter and loads locked base-offer
                                                          context
/not-a-real-page                                          application not-found page
curl /api/health through :4173                            200, proxied to the backend
```

After the smoke run the seeded records were removed (`cleanup --run-id te1-551a6622`), the
throwaway container was deleted, the `.next` volume was cleared of the production build, and the
default Next frontend was restarted and confirmed serving `/login` and `/api/health` on port 3000.

### Part 1 deviations and notes for the independent reviewer

- `src/components/NotFoundPage.tsx` is deliberately **not** under `src/pages/`. The first Next
  build after adding it published a real `/NotFoundPage` Pages Router URL, because Next treats
  `src/pages/` as its Pages Router directory. Part 2 may move it once Next is removed.
- A catch-all `*` route was added. Next served a built-in 404 for unknown URLs; a Vite SPA serves
  `index.html` for every path, so without it an unknown URL renders an empty shell.
- Part 1 intentionally omitted `React.StrictMode`, but the independent review found that this does not match the
  current Next App Router development behavior. The mandatory Part 2 correction is recorded in
  the independent review above and in the Part 2 implementation package.
- `build:vite` reports a single 668 kB chunk above Rollup's 500 kB advisory threshold. This is the
  existing application bundled without route-level code splitting; it is a Part 2/performance
  consideration, not a Part 1 defect.
- The Part 1 commit deliberately excludes `docs/agent/technical-enablement/TE_2A_*.md` and the
  other in-flight planning edits present in the working tree, which are outside the Part 1
  allowed-files boundary.

## Part 2 completion

```text
[x] Part 2 was prepared from the accepted Part 1 commit.
[x] Default dev/build/test commands use Vite/Vitest and succeed.
[x] All current routes and query/return navigation behavior are preserved.
[x] Direct deep links and browser reloads resolve through SPA fallback.
[x] Dynamic parameters use React Router directly; temporary compatibility shim is gone.
[x] Pages/components/styles live in the final non-Next source structure.
[x] next, next.config.ts, next-env.d.ts, .next references and use-client directives are removed
    from active frontend/runtime/tooling records.
[x] Browser API requests remain relative /api; no localhost or Docker hostname is bundled into
    browser code.
[x] Dockerfile builds the Vite application and Compose starts it on port 3000.
[x] Compose no longer declares frontend-next/.next volume.
[x] Playwright no longer performs Next cold-compile warm-up; retries remain zero.
[x] init-skeleton.ps1 and active frontend/agent/tooling guidance generate/describe Vite.
[x] No backend/API/database/business-event behavior changed.
[x] docker compose exec backend pytest passes.
[x] frontend production build and frontend tests pass.
[x] .\scripts\run-e2e.ps1 passes with cleanup.
[x] Vendor-demo tooling and the vendor-review repository were not accessed; vendor review remains
    deferred until PBL explicitly authorizes it.
[x] Docker clean-start, backend health and frontend login route pass.
[x] Manual admin happy path passes from login through linked Offer/Work Order views.
[x] Manual read-only/permission path passes.
[x] Final diff contains no generated dist, node_modules, .next, E2E artifacts or manifests.
[x] Slice, acceptance, NEXT_STEPS and TE-2A continuity completion records are current.
[x] An uncommitted structured implementation handoff is provided; the independent review examines/tests the
    complete diff before any commit or push.
    Handoff provided. The first independent review (13 August 2026) raised three findings, corrected by
    TE-2A.2-C1. Final review accepted the corrected package after an independent generated-skeleton
    image build and cleanup check, script parsing, scope review and diff hygiene checks.
```

## TE-2A.2-C1 correction pass

The independent review examined the uncommitted Part 2 diff on 13 August 2026 and independently confirmed
`git diff --check`, Alembic head `20260713_0029` unchanged, 218 backend tests, frontend typecheck,
54 Vitest tests, the 69-module production build, a clean frontend image build, `/login`, a direct
Work Order deep link, `/api/health`, a `Host: frontend` request, the built-bundle forbidden-string
scan, and Playwright at 12 passed / 9 vendor-demo skipped with all three seeded runs cleaned up.

It also raised three findings. All three are corrected below; the application migration itself is
unchanged.

### Finding 1 - generated skeleton could not build (blocking)

`init-skeleton.ps1` emitted a frontend `Dockerfile` containing
`COPY package.json package-lock.json ./` and `RUN npm ci`, but the generator writes no
`package-lock.json`. The independent review confirmed against an isolated temporary root:
`PackageJson=true, PackageLock=false, DockerCopiesLock=true, DockerRunsNpmCi=true`. A fresh
skeleton therefore failed before dependency installation.

Corrected: the emitted Dockerfile now uses `COPY package*.json ./` and a shell conditional -
`npm ci` when `package-lock.json` exists, otherwise `npm install`. The generated `package.json`
already pins exact versions, so the no-lockfile path still installs the reviewed versions. The
repository's own `frontend/Dockerfile` is deliberately unchanged and remains lockfile-backed with
`npm ci`. The repository lockfile was not embedded into the generator.

Verified by generating into a unique temporary root under the system temp directory (path checked
to resolve under it before use) and building the generated frontend image both ways:

```text
generator run against <a temporary folder>
  PackageJson       True
  PackageLock       False        (no lockfile, as a fresh skeleton has)
  DockerCopiesGlob  True         (COPY package*.json ./)
  DockerHasBareCi   False        (no unconditional npm ci)
doubled-quote scan over every generated frontend file    no matches
docker build (no lockfile -> npm install branch)         success, dist 275.77 kB
npm install --package-lock-only, then
docker build --no-cache (lockfile -> npm ci branch)      success, dist 275.77 kB
PowerShell AST parse of init-skeleton.ps1                no syntax errors
```

The temporary skeleton directory was removed afterwards, only after re-confirming its resolved
path was still under the system temporary directory.

Observation for the independent reviewer, not changed here: `init-skeleton.ps1` still hard-codes
`$Root = "<your checkout>"`, so it cannot be pointed at another directory without editing
it. This verification therefore ran a patched copy inside the temporary root and left the live
script untouched. Parameterizing `$Root` was outside this correction's allowed scope.

### Finding 2 - default E2E could test a stale frontend image (blocking)

`scripts/run-e2e.ps1` ran only `docker compose up -d db backend frontend`, which reuses an
existing image. Since TE-2A removed the frontend source bind mount, the suite could seed current
data, exercise an older frontend bundle and still report success - weakening the regression
evidence for all future frontend work.

Corrected: the default path now runs `docker compose build frontend` before `docker compose up -d`,
and the synopsis, `.PARAMETER` help and run-time messages state why. `-SkipServiceStart` keeps its
meaning - it skips both the build and the start - and now emits an explicit warning that the caller
owns the running services and image and may not be testing current source. Seeding, the three
manifests, cleanup, exit-code handling, scenarios, assertions and `retries: 0` are untouched.

`frontend/README.md` no longer implies `docker compose up -d frontend` builds; it states that the
command starts an available image, keeps `--build` as the instruction after a source change, and
notes that `run-e2e.ps1` builds on its default path for the same reason.

### Finding 3 - review and completion state recorded too early

The package marked TE-2A complete, advanced the current gate to production-database confirmation
and ticked the Part 2 independent-review item before the diff had been reviewed - and that review then
found two blocking issues, so those statements were not true.

At the correction handoff, PBL's internal working instructions, `PLAN.md`, `AGENT_HANDOFF.md`, `FUTURE_SLICES.md`, this
file, `INDEPENDENT_IMPLEMENTATION_REVIEW_WORKFLOW.md`, `TE_2A_REACT_VITE_MIGRATION.md`,
`NEXT_STEPS.md` and the
continuity completion note described Part 2 as awaiting final independent-review acceptance, kept that acceptance as
the current gate and left the reviewer checkbox unchecked. The final review above recorded the
subsequent acceptance and, at that review stage, advanced the gate to the PBL-directed Git action.

`TE_2A_REACT_VITE_MIGRATION.md` also still listed a demo preflight among the Part 2 required
checks, contrary to the approved Part 2 prompt and PBL's instruction to defer all vendor work.
That requirement is removed and replaced with the record that vendor-demo tooling and both
vendor-review repositories remain untouched and vendor review is deferred until PBL explicitly
authorizes it.

### TE-2A.2-C1 checks

```text
git diff --check                                     clean (exit 0)
PowerShell AST parse of init-skeleton.ps1            no syntax errors
isolated temporary-root skeleton generation          success, no doubled quotes
docker build of generated skeleton frontend          success, both no-lockfile and lockfile paths
.\scripts\run-e2e.ps1 (default path)                 frontend image built first;
                                                     12 passed, 9 skipped, all three runs cleaned up
Independent generated no-lockfile image build     success; temporary root removed
Final independent review                          accepted; no blocking findings
```

The hard-coded `$Root` in `init-skeleton.ps1` is a recorded, non-blocking portability limitation of
the pre-existing bootstrap tool; the generated output itself was verified using an isolated patched
copy. Parameterize it before treating the script as a general-purpose multi-root generator. The
longer corrected E2E runtime is expected because the default path now builds the current frontend
image; no retry or timeout was added.

### Part 2 source structure

24 page modules moved with `git mv` (all recorded as 100%-similarity renames), plus
`SessionActions`, `globals.css` and `NotFoundPage`:

```text
frontend/app/page.tsx                                  -> frontend/src/pages/DashboardPage.tsx
frontend/app/login/page.tsx                            -> frontend/src/pages/LoginPage.tsx
frontend/app/documents/page.tsx                        -> frontend/src/pages/DocumentsPage.tsx
frontend/app/events/page.tsx                           -> frontend/src/pages/EventsPage.tsx
frontend/app/workflow-statuses/page.tsx                -> frontend/src/pages/WorkflowStatusesPage.tsx
frontend/app/terms-and-conditions/page.tsx             -> frontend/src/pages/TermsAndConditionsPage.tsx
frontend/app/accounts/**                               -> frontend/src/pages/accounts/{Accounts,NewAccount,AccountDetail}Page.tsx
frontend/app/leads/**                                  -> frontend/src/pages/leads/{Leads,NewLead,LeadDetail}Page.tsx
frontend/app/opportunities/**                          -> frontend/src/pages/opportunities/{Opportunities,NewOpportunity,OpportunityDetail}Page.tsx
frontend/app/commercial-offers/**                      -> frontend/src/pages/commercial-offers/{CommercialOffers,NewCommercialOffer,CommercialOfferDetail,NewRelatedOffer}Page.tsx
frontend/app/work-orders/**                            -> frontend/src/pages/work-orders/{WorkOrders,NewWorkOrder,WorkOrderDetail,NewWorkOrderAmendment,WorkOrderAmendmentDetail}Page.tsx
frontend/components/layout/SessionActions.tsx          -> frontend/src/components/SessionActions.tsx
frontend/app/globals.css                               -> frontend/src/styles/globals.css
frontend/src/components/NotFoundPage.tsx               -> frontend/src/pages/NotFoundPage.tsx
```

Deleted: `frontend/app/layout.tsx` (superseded by `index.html` + `src/layout/AppShell.tsx`),
`frontend/next.config.ts`, `frontend/next-env.d.ts`, `frontend/tsconfig.vite.json`,
`frontend/src/compat/next-navigation.ts`, `e2e/tests/global-setup.ts`, and the leftover empty
`frontend/app/**` / `frontend/components/**` skeleton directories.

25 `"use client"` directives (and the UTF-8 BOMs that preceded 10 of them) were removed. Eight
`import { useParams } from "next/navigation"` became `from "react-router-dom"`.

### Part 2 dependency changes

```text
next  15.1.12  removed from dependencies; package-lock.json regenerated
```

Nothing was added. React 19.0.0, react-dom 19.0.0, react-router-dom 7.18.2, TypeScript 5.7.2,
Vite 7.3.6, Vitest 4.1.10, `@vitejs/plugin-react` 5.2.0 and the `@types/*` pins are unchanged from
Part 1. No React downgrade and no new application state, data-fetching, UI or CSS library.

### Part 2 script and configuration changes

```text
dev        next dev -H 0.0.0.0 -p 3000  ->  vite
build      next build                   ->  vite build
preview    (new)                        ->  vite preview
test       vitest run                       unchanged
typecheck  (was typecheck:vite)         ->  tsc -p tsconfig.json --noEmit
start      next start                   ->  removed
```

`dev:vite`, `build:vite`, `preview:vite` and `typecheck:vite` are gone. `tsconfig.vite.json` was
folded into `tsconfig.json` (`jsx: react-jsx`, `target: ES2020`, no Next plugin, no
`next/navigation` path mapping, scoped to `src/**` and `vite.config.ts`).

### Part 2 commands and results

Frontend commands run in a container over the working tree, since the `frontend` service has no
bind mount:
`docker compose run --rm --no-deps -v ${PWD}/frontend:/app -v /app/node_modules frontend <cmd>`.

```text
git diff --check                                    clean (exit 0)
docker compose exec backend alembic current         20260713_0029 (head)
docker compose exec backend alembic heads           20260713_0029 (head)
docker compose exec backend pytest                  218 passed in 446.62s
npm run typecheck                                   pass, no diagnostics
npm test                                            pass, 1 file / 54 tests
npm run build                                       pass, 69 modules, dist 668.67 kB
                                                    (gzip 162.06 kB), css 8.19 kB
docker compose build --no-cache frontend            pass (npm ci + vite build inside the image)
docker compose up -d db backend frontend            all three up
.\scripts\run-e2e.ps1                               12 passed, 9 skipped, 52.2s; three seeded
                                                    runs cleaned up with zero residue
```

Route-test coverage is unchanged from Part 1: all 24 URLs, page-module identity, static-over-
dynamic precedence, nested routes, query-string independence and the unknown-route fallback, 54
tests total.

Runtime verification against the rebuilt image:

```text
GET http://localhost:3000/login                                200, 525 bytes
GET http://localhost:3000/work-orders/<unknown-uuid>           200, 525 bytes (SPA fallback,
                                                               not a server 404)
GET http://localhost:3000/api/health                           200 {"status":"ok",...}
built bundle grep: backend:8000 / localhost:8000 /             0 / 0 / 0 / 0
  BACKEND_INTERNAL_URL / next/dist
grep -rn "next/navigation" frontend/src                        0
```

### Part 2 defects found and fixed

1. **`vite preview` rejected the Playwright container's Host header.** Vite 7 answers only hosts
   listed in `preview.allowedHosts`; the E2E container reaches the frontend as
   `http://frontend:3000`, so all 12 business specs failed with
   `Blocked request. This host ("frontend") is not allowed.` Fixed with an explicit allowlist
   (`localhost`, `frontend`, plus a comma-separated `ALLOWED_HOSTS` variable) rather than by
   disabling the DNS-rebinding protection. Re-run: 12 passed.
2. **Compose bind mount would have shadowed the image build.** `./frontend:/app` would replace the
   image-built `dist/` and `node_modules` with host copies. The mount and both `frontend-next` /
   `frontend-node-modules` volumes were removed; `frontend/README.md` and `AGENTS.md` document the
   explicit-mount commands that replace them for checks and for a hot-reloading dev server.

### Part 2 code review

`/code-review` (high effort) was run against the complete uncommitted diff after the first green
run. It produced six findings. Five were fixed and the affected checks rerun; one is outside this
package's allowed-files boundary and is reported for the independent reviewer rather than fixed.

```text
1  init-skeleton.ps1      The new frontend blocks used "" inside PowerShell expandable
   FIXED                  here-strings (@"..."@), where "" is not an escape and emits two literal
                          quotes. The generated index.html would have contained
                          <div id=""root""></div> (empty id, app never mounts) and vite.config.ts
                          would have started with an invalid /// <reference types=""vitest/config"" />.
                          Verified directly against the PowerShell parser. All frontend blocks were
                          converted to literal here-strings (@'...'@), which also removes the
                          $-interpolation hazard the pre-existing blocks escape by hand.
2  e2e/tests/fixtures/    loadVendorDemoManifest's comment still pointed at tests/global-setup.ts,
   manifest.ts            which this package deletes. Reworded to describe the guard that actually
   FIXED                  exists in demo-preflight.spec.ts.
3  frontend/              server/preview had no strictPort, so a port-3000 clash would silently
   vite.config.ts         bind another port while Compose still maps 3000, leaving a "healthy"
   FIXED                  container refusing every request and an unexplained run-e2e timeout.
                          strictPort: true added to both, and to the skeleton's generated config.
4  docs/demo/02_VENDOR_   Still states "Frontend: Next.js". docs/demo/ is outside this package's
   IMPLEMENTATION_        allowed files and vendor material is deferred, so this is reported, not
   HANDOFF_NOTES.md       changed. Schedule it with the other vendor-facing updates.
   REPORTED
5  init-skeleton.ps1      Generated "test": "vitest run" exits 1 on a fresh skeleton because it
   FIXED                  writes no test file. Changed to vitest run --passWithNoTests.
6  AGENTS.md,             Documented docker commands passed -v ${PWD}/frontend:/app unquoted, which
   frontend/README.md     breaks on any repository path containing a space. Quoted.
   FIXED
```

Checks rerun after the fixes: `npm run typecheck` (pass), `npm test` (54 tests), `docker compose
build frontend` (pass), `docker compose up -d frontend` (preview bound to 3000), `.\scripts\run-e2e.ps1`
(12 passed, 9 skipped, 50.2s, three runs cleaned up). `init-skeleton.ps1` was additionally parsed
with the PowerShell AST parser and reports no syntax errors.

### Part 2 Strict Mode evidence

`src/main.tsx` renders `<StrictMode><RouterProvider /></StrictMode>` and the inaccurate
single-pass comment is gone.

Verified in Vite development mode (throwaway container on port 5173 against seeded TE-1 data,
`accepted-offer-with-work-order`, run `te1-0399f5e7`, cleaned up afterwards):

```text
POST /api/auth/login                    fired exactly once - no duplicate business action
Commercial Offer detail load            each read GET fired twice (Strict Mode double-invoked
                                        effects; idempotent, development-only, matches the
                                        previous Next App Router default)
console errors                          none, on /login, the dashboard and the offer detail page
code-level scan                         no POST/PUT/DELETE/PATCH is issued from inside any
                                        useEffect in frontend/src/pages; every mutation lives in
                                        an event handler, which Strict Mode does not double-invoke
```

No effect was suppressed, no duplicate-request guard was added and no business rule was weakened.

### Part 2 manual checks

Admin path (`admin1` / `password`, seeded run `te1-0399f5e7`):

```text
/login direct load and sign-in                        pass, "Login successful.", role Admin
/ dashboard                                            pass, full demo dashboard, no console errors
/commercial-offers/<seeded id>                         pass, Accepted Base Offer, all five tabs
Traceability tab -> Open Work Order shell              pass, origin-aware returnTo/returnLabel
                                                       query string preserved on the link
/work-orders/<seeded id>                               pass, handoff shell badge, provenance,
                                                       WorkOrderCreated event (ADMIN), line
                                                       traceability
reload (F5) of that deep link with query string        pass, same WO-003785, query string intact,
                                                       no console errors
```

Read-only path (`readonly1` / `password`) on the same Commercial Offer:

```text
role reported                     MANAGEMENT_READ_ONLY
record data                       visible (offer code, status, all tabs)
"Edit Commercial Offer / Status"  not offered
page wording                      "read-only Commercial Offer profile for your current role."
```

Backend authorization is unchanged and remains authoritative; the frontend hiding above is the
usability aid it has always been.

### Part 2 deviations and notes for the independent reviewer

- `AccountDetailPage` previously declared `useParams<{ accountId?: string | string[] }>()` and
  branched on `Array.isArray`. React Router's `useParams` constrains its type parameter to
  `Record<string, string | undefined>`, so the `string[]` member is not expressible. The generic is
  now `{ accountId: string }` and the dead array branch is gone: the route table declares no splat
  segment, so that branch could never execute. This is the only page-body change in Part 2 beyond
  directive/import removal.
- `NotFoundPage` moved from `src/components/` to `src/pages/`. Part 1 kept it out of `src/pages/`
  only because Next treated that directory as its Pages Router; with Next gone the constraint is
  too.
- `frontend/.dockerignore` is new. Without it, `COPY . .` would copy host `node_modules` and `dist`
  over the image's own `npm ci` result.
- `vite.config.ts` binds both the dev server and preview to port 3000, the port every environment
  (Compose, Playwright, the demo runbook) already publishes.
- `frontend/lib/` and `frontend/tests/` remain as empty, untracked skeleton directories from
  `init-skeleton.ps1`. They predate TE-2A, are not Next-specific and were left alone.
- The obsolete `frontend-next` and `frontend-node-modules` Docker volumes were deleted from the
  local Docker engine so the clean-start evidence is genuine.
- `docs/agent/contracts/platform-foundation.md` still describes a Next.js frontend. It is a
  contract file and outside this package's allowed-files boundary; reconciling it belongs to the
  TE-2C gate.

## Explicitly out of scope

- UI redesign or component refactoring unrelated to framework removal.
- New business workflow, API, backend, database, permission or event behavior.
- React Native work.
- Production database migration (`TE-2B`).
- GitHub Actions implementation (`TE-2CI`).
- Production hosting/provider selection or final static-server hardening beyond the Vite Docker
  runtime needed for current Compose and tests.

## Human acceptance

Test users and data come from the existing TE-1 smoke-data/Playwright scenarios.

```text
Admin: admin1 / password
Read-only: readonly1 / password
Start: http://localhost:3000/login
```

Check the same screens and actions before and after migration. TE-2A is accepted only for
functional equivalence; a visual or workflow change requires a separately recorded slice.
