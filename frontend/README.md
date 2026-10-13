# Frontend

React 19 + Vite + React Router client for the PBL CRM + Equipment Hiring prototype
(see `docs/agent/ARCHITECTURE_DECISIONS.md`, ADR-016).

FastAPI remains the sole authoritative backend. This application renders in the browser, calls
relative `/api/...` URLs only and enforces no business rules of its own.

## Source layout

```text
index.html                 document shell, title and description
vite.config.ts             build, /api proxy, allowed hosts, Vitest configuration
src/main.tsx               entry point; renders the router inside React.StrictMode
src/router.tsx             React Router route objects built from the route table
src/routes.tsx             the route table - one entry per public URL
src/routes.test.ts         route-table regression tests
src/layout/AppShell.tsx    sidebar, navigation and the page <Outlet />
src/components/            shared components
src/pages/                 one module per page
src/styles/globals.css     application stylesheet
```

## Commands

Run inside a container, consistent with the repository's runtime convention (no host Node.js
required). The explicit source mount matters: the `frontend` service has no bind mount, so without
it these commands would check the source baked into the last image rather than the working tree.
The anonymous `/app/node_modules` mount keeps the image's installed dependencies.

```powershell
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run typecheck
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm test
docker compose run --rm --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run build
```

| Command | What it does |
| --- | --- |
| `npm run dev` | Vite development server on port 3000 with hot reload |
| `npm run build` | Production build into `dist/` |
| `npm run preview` | Serves the built `dist/` on port 3000 (what the container runs) |
| `npm test` | Vitest run, including the route-table regression tests |
| `npm run typecheck` | `tsc --noEmit` over the application and its configuration |

## Docker Compose runtime

The image runs `npm ci`, then `npm run build`, and serves the built application with
`vite preview` on port 3000. There is deliberately **no** source bind mount: it would shadow the
image-built `dist/` and `node_modules` with host copies.

Because of that, the running container serves whatever bundle its image was built from.
`docker compose up -d frontend` starts an **available** image and does not rebuild it when one
already exists, so on its own it can keep serving stale frontend source. Always pass `--build`
after changing frontend code:

```powershell
docker compose up -d --build frontend
```

For the same reason `scripts/run-e2e.ps1` builds the frontend image on its default path, so the
Playwright suite never tests a stale bundle.

`vite preview` supplies the SPA fallback, so a direct request or browser reload of a deep link
such as `/work-orders/<id>` returns `index.html` instead of a server 404, and it proxies `/api`
to `BACKEND_INTERNAL_URL` (`http://backend:8000` under Compose). That variable is read server-side
only and is never inlined into browser code.

## Hot-reloading development server

For a hot-reloading server against host sources, mount the source explicitly and keep the image's
own `node_modules`:

```powershell
docker compose run --rm --service-ports --no-deps -v "${PWD}/frontend:/app" -v /app/node_modules frontend npm run dev
```

Stop the Compose `frontend` service first: both bind port 3000, and `strictPort` makes the second
one fail rather than silently move to another port.

## Allowed hosts

`vite.config.ts` allows `localhost` (browser access through the published port) and `frontend`
(callers inside the Compose network, such as the Playwright container). Add further deployment
hostnames through the `ALLOWED_HOSTS` environment variable as a comma-separated list rather than
disabling the check, which exists to prevent DNS rebinding.

## URL

```text
http://localhost:3000
```
