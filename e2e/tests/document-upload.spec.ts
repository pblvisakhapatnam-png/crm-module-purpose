import fs from "node:fs";
import { test, expect } from "@playwright/test";
import type { Page } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

const manifest = loadManifest();
const record = manifest.records["document_upload_target"];

test.skip(!record, "core-regression-bundle manifest is missing the 'document_upload_target' record.");

// Named after the seeded run, so a file left behind by any other run can never satisfy an assertion.
const accountFileName = `account-file-${manifest.run_id}.txt`;
const offerFileName = `offer-file-${manifest.run_id}.txt`;
const accountFileText = `Account file for run ${manifest.run_id}.\n`;
const offerFileText = `Offer file for run ${manifest.run_id}.\n`;

function escapeForRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function fileRow(page: Page, fileName: string) {
  return page.getByRole("row", { name: new RegExp(escapeForRegExp(fileName)) });
}

async function uploadTextFile(page: Page, fileName: string, text: string, documentTypeLabel: string) {
  const form = page.getByRole("form", { name: "Add a file" });
  await expect(form).toBeVisible();
  await form.getByLabel("File", { exact: true }).setInputFiles({
    name: fileName,
    mimeType: "text/plain",
    buffer: Buffer.from(text, "utf-8"),
  });
  await form.getByLabel("Document type", { exact: true }).selectOption({ label: documentTypeLabel });
  await form.getByRole("button", { name: "Upload", exact: true }).click();
  // The confirmation sits beside the Upload button, not at the top of the page.
  await expect(form.getByText(`File added: ${fileName}.`)).toBeVisible();
}

test.describe("Files on the Account and Commercial Offer pages", () => {
  // The View only test reads the files the first two tests add, so they run in order and a failure
  // stops the rest rather than producing a misleading second failure.
  test.describe.configure({ mode: "serial" });

  test("Sales adds a file to an Account, sees it listed and downloads it", async ({ page }) => {
    await login(page, "sales1");
    await page.goto(`/accounts/${record.account.public_id}`);

    await uploadTextFile(page, accountFileName, accountFileText, "KYC");

    const row = fileRow(page, accountFileName);
    await expect(row).toBeVisible();
    await expect(row.getByText("KYC", { exact: true })).toBeVisible();
    // The file's own reference shows under its name, as the older Account list showed it.
    await expect(row.getByText(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/)).toBeVisible();

    const downloadPromise = page.waitForEvent("download");
    await row.getByRole("button", { name: "Download" }).click();
    const download = await downloadPromise;

    expect(download.suggestedFilename()).toBe(accountFileName);
    // The bytes that come back are the bytes that went in.
    const downloadedPath = await download.path();
    expect(fs.readFileSync(downloadedPath, "utf-8")).toBe(accountFileText);
  });

  test("Sales adds a file to a Commercial Offer on its Overview tab and sees it listed", async ({ page }) => {
    await login(page, "sales1");
    await page.goto(`/commercial-offers/${record.commercial_offer.public_id}`);
    await expect(page.getByText(record.commercial_offer.offer_code).first()).toBeVisible();
    await expect(page.getByRole("tab", { name: "Overview" })).toHaveAttribute("aria-selected", "true");

    await uploadTextFile(page, offerFileName, offerFileText, "Commercial");

    const row = fileRow(page, offerFileName);
    await expect(row).toBeVisible();
    await expect(row.getByText("Commercial", { exact: true })).toBeVisible();
  });

  test("View only sees the files on both pages but is offered no way to add one", async ({ page }) => {
    await login(page, "readonly1");

    await page.goto(`/accounts/${record.account.public_id}`);
    // Waiting for the file first means the panel has rendered, so the absence checks below cannot
    // pass merely because the page had not finished loading.
    await expect(fileRow(page, accountFileName)).toBeVisible();
    await expect(page.getByText("Your role can view these files but cannot add new ones.")).toBeVisible();
    await expect(page.getByRole("form", { name: "Add a file" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Upload", exact: true })).toHaveCount(0);
    await expect(page.getByText("Record a link to a file stored elsewhere")).toHaveCount(0);

    await page.goto(`/commercial-offers/${record.commercial_offer.public_id}`);
    await expect(fileRow(page, offerFileName)).toBeVisible();
    await expect(page.getByText("Your role can view these files but cannot add new ones.")).toBeVisible();
    await expect(page.getByRole("form", { name: "Add a file" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Upload", exact: true })).toHaveCount(0);
  });

  // The two record types allow different roles (owner decision, 11 September 2026): an Account is
  // Admin, Sales, Sales Manager and Accounts; an offer is Admin, Sales, Sales Manager and
  // Operations. Finance and Operations are exactly where the two sets diverge, so testing them on
  // both pages pins that the form follows the server's rule for each type - not one shared rule.
  // Both roles can read both records, so the panel and its files load on each page; only the
  // upload form differs. sales1 (both) and readonly1 (neither) are covered by the tests above.
  const DIVERGING_UPLOAD_ROLES = [
    { user: "finance1", onAccount: true, onOffer: false },
    { user: "ops1", onAccount: false, onOffer: true },
  ];

  for (const role of DIVERGING_UPLOAD_ROLES) {
    test(`${role.user} is offered the upload form only where the server allows it`, async ({ page }) => {
      await login(page, role.user);

      await page.goto(`/accounts/${record.account.public_id}`);
      // Wait for the file first, so an absence check below cannot pass merely because the panel
      // had not finished loading.
      await expect(fileRow(page, accountFileName)).toBeVisible();
      await expect(page.getByRole("form", { name: "Add a file" })).toHaveCount(role.onAccount ? 1 : 0);

      await page.goto(`/commercial-offers/${record.commercial_offer.public_id}`);
      await expect(fileRow(page, offerFileName)).toBeVisible();
      await expect(page.getByRole("form", { name: "Add a file" })).toHaveCount(role.onOffer ? 1 : 0);
    });
  }
});
