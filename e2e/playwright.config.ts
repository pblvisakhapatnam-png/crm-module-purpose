import { defineConfig, devices } from "@playwright/test";

// Inside the `e2e` Compose service this resolves the frontend over the Docker
// Compose network. Override with E2E_BASE_URL for a host-run exception if ever needed.
const baseURL = process.env.E2E_BASE_URL ?? "http://frontend:3000";

export default defineConfig({
  testDir: "./tests",
  globalTimeout: 10 * 60_000,
  // The frontend now serves a pre-built Vite bundle (see frontend/Dockerfile), so there is no
  // per-route cold-compile cost and no warm-up step. Timeouts stay generous because several
  // specs drive multi-step business flows against a real database, not because of flakiness --
  // retries stay at 0.
  timeout: 60_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  outputDir: "test-results",
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    actionTimeout: 30_000,
    navigationTimeout: 45_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
