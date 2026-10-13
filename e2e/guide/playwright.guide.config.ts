import { defineConfig, devices } from "@playwright/test";

// TE-7: captures the screenshots in docs/uat-hiring/PBL_HIRING_USER_GUIDE.md from the Hiring user test's practice
// data (`hiring-uat-seeded`). Not part of the regression suite - its own folder and config, run only on purpose:
//
//   docker compose --profile e2e run --rm e2e bash -c "npm install --no-audit --no-fund && npx playwright test -c guide/playwright.guide.config.ts"
//
// on a fresh stack seeded with that scenario and nothing else, so the codes match the guide's. It accepts offer
// CO-000004 (once; a rerun finds it accepted) to show where "Create Work Order" appears, so reseed before the data is
// used for anything else. The pictures land in guide/out/; copy them to docs/uat-hiring/images/.
export default defineConfig({
  testDir: ".",
  testMatch: "*.capture.ts",
  timeout: 5 * 60_000,
  expect: { timeout: 15_000 },
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  outputDir: "out/test-results",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://frontend:3000",
    viewport: { width: 1360, height: 900 },
    deviceScaleFactor: 1,
    actionTimeout: 30_000,
    navigationTimeout: 45_000,
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1360, height: 900 } } }],
});
