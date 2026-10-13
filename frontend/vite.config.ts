/// <reference types="vitest/config" />

import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

/**
 * Proxy target for the FastAPI backend.
 *
 * This value is read by the Vite server in Node, never by browser code. It is deliberately not a
 * `VITE_*` variable, because those are inlined into the client bundle and would leak an internal
 * hostname into the browser. Pages fetch relative `/api/...` URLs only.
 *
 * Default `http://localhost:8000` suits a host-run server; Compose supplies
 * `http://backend:8000` when the frontend runs inside its container.
 */
const backendInternalUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";

/** Shared by the dev server and `vite preview`, so both reach the backend the same way. */
const apiProxy = {
  "/api": {
    target: backendInternalUrl,
    changeOrigin: true,
  },
};

/**
 * Host headers the server answers to. Vite rejects anything else as DNS-rebinding protection.
 *
 * `localhost` covers a browser using the published port. `frontend` covers callers inside the
 * Compose network, which reach the service by its Compose service name - the Playwright container
 * uses `http://frontend:3000`. Further deployment hostnames are added through `ALLOWED_HOSTS`
 * (comma-separated) rather than by disabling the check.
 */
const allowedHosts = [
  "localhost",
  "frontend",
  ...(process.env.ALLOWED_HOSTS ?? "")
    .split(",")
    .map((host) => host.trim())
    .filter(Boolean),
];

export default defineConfig({
  plugins: [react()],
  // `host` is set for container use. Port 3000 is the application's published port in every
  // environment (Compose, Playwright, the demo runbook), so both the dev server and the preview
  // server that serves the production build bind to it.
  //
  // `strictPort` makes a clash fail loudly. Without it Vite would quietly bind the next free port
  // while Compose still maps host 3000 to container 3000, so the service would look healthy and
  // refuse every request.
  server: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    allowedHosts,
    proxy: apiProxy,
  },
  preview: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    allowedHosts,
    proxy: apiProxy,
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts", "src/**/*.test.tsx"],
  },
});
