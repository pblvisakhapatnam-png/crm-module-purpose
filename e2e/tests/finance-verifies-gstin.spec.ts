import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

// TB-1 finding TB1-800: the Add GSTIN form was shown to Finance - the only role that may record a GSTIN as Verified -
// but its button checked the Account-create roles and refused them. These tests add a GSTIN to the Account the
// document-upload target already seeds; the harness's cleanup removes the GSTINs on the run's Accounts.
const manifest = loadManifest();
const record = manifest.records["document_upload_target"];

test.skip(!record, "core-regression-bundle manifest is missing the 'document_upload_target' record.");

/** A well-formed GSTIN no other run holds: its letters and digits come from the run's id. */
function gstinForRun(runId: string): string {
  let hash = 7;
  for (const char of runId) hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  const letters = Array.from({ length: 5 }, (_, i) => String.fromCharCode(65 + ((hash >>> (i * 5)) % 26))).join("");
  const digits = String(hash % 10000).padStart(4, "0");
  return `27${letters}${digits}F1Z${hash % 10}`;
}

test.describe("GSTINs on the Account page, by role", () => {
  test("Finance adds a GSTIN as Verified", async ({ page }) => {
    const gstin = gstinForRun(manifest.run_id);
    await login(page, "finance1");
    await page.goto(`/accounts/${record.account.public_id}`);
    await expect(page.getByText(record.account.account_name).first()).toBeVisible();

    await page.getByLabel(/^GSTIN \*$/).fill(gstin);
    await page.getByLabel("GSTIN verification state").selectOption({ label: "Verified" });
    await page.getByRole("button", { name: "Add GSTIN", exact: true }).click();

    // The confirmation sits beside the button; the refusal "You do not have permission to add GSTIN details." is gone.
    await expect(page.getByText("GSTIN added.")).toBeVisible();
    await expect(page.getByText("You do not have permission to add GSTIN details.")).toHaveCount(0);
    const row = page.getByRole("row", { name: new RegExp(gstin) });
    await expect(row).toBeVisible();
    await expect(row.getByRole("cell", { name: "Verified", exact: true })).toBeVisible();
  });

  test("Sales may add a GSTIN but is offered no final state", async ({ page }) => {
    await login(page, "sales1");
    await page.goto(`/accounts/${record.account.public_id}`);
    await expect(page.getByText(record.account.account_name).first()).toBeVisible();

    const states = page.getByLabel("GSTIN verification state");
    await expect(states).toBeVisible();
    await expect(states.locator("option", { hasText: /^Verified$/ })).toHaveCount(0);
    await expect(states.locator("option", { hasText: /^Rejected \/ Incorrect$/ })).toHaveCount(0);
  });
});
