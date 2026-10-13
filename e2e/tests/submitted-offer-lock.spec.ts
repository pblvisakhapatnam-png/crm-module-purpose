import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

const manifest = loadManifest();
const record = manifest.records["submitted_lock_target"];

test.skip(!record, "core-regression-bundle manifest is missing the 'submitted_lock_target' record.");

// Slice 9F: a sent version never changes. Sales copies it to a new Draft, edits and sends that row, and v1 becomes
// read-only Replaced history.

test.describe("Immutable Commercial Offer versions (Slice 9F)", () => {
  test("makes, edits and sends v2 while v1 stays replaced history", async ({ page }) => {
    await login(page, "sales1");
    await page.goto(`/commercial-offers/${record.commercial_offer.public_id}`);
    await expect(page.getByText(`${record.commercial_offer.offer_code} v1`).first()).toBeVisible();

    await page.getByRole("tab", { name: "Lines & Pricing" }).click();
    await expect(page.getByText("can no longer change on this version").first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Add Commercial Offer line" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Edit line" })).toHaveCount(0);

    await page.getByRole("tab", { name: "Submission" }).click();
    const makeVersionForm = page.locator("form").filter({ has: page.getByRole("button", { name: "Make a new version" }) });
    await makeVersionForm.getByLabel("Reason").selectOption("RATE_CORRECTION");
    await makeVersionForm.getByLabel("Note (optional)").fill("Customer requested a corrected day rate.");
    await makeVersionForm.getByRole("button", { name: "Make a new version" }).click();
    await expect(makeVersionForm.getByText("made as an editable Draft")).toBeVisible();
    await makeVersionForm.getByRole("link", { name: "Open the new version" }).click();
    await expect(page).toHaveURL(/\/commercial-offers\/[0-9a-f-]+$/);
    await expect(page.getByText(`${record.commercial_offer.offer_code} v2`).first()).toBeVisible();

    await page.getByRole("button", { name: "Edit Commercial Offer / Status" }).click();
    await page.getByLabel("Offer title").fill("Corrected crane hire offer");
    await page.getByRole("button", { name: "Save Commercial Offer" }).click();
    await expect(page.getByText("Commercial Offer updated successfully.")).toBeVisible();
    await page.getByRole("button", { name: "Cancel" }).click();

    await page.getByRole("tab", { name: "Lines & Pricing" }).click();
    await page.getByRole("button", { name: "Edit line" }).first().click();
    const lineForm = page.locator("form").filter({ has: page.getByRole("button", { name: "Save line" }) });
    await lineForm.getByLabel("Rate amount").fill("31000");
    await lineForm.getByRole("button", { name: "Save line" }).click();
    await expect(page.getByText("Commercial Offer line updated.")).toBeVisible();
    await expect(page.getByText("INR 31,000", { exact: true })).toBeVisible();

    await page.getByRole("tab", { name: "Submission" }).click();
    const evidenceForm = page.locator("form").filter({ has: page.getByRole("button", { name: "Record submission evidence" }) });
    await evidenceForm.getByLabel("Submitted date/time").fill("2026-10-10T15:00");
    await evidenceForm.getByLabel("Submission reference").fill("E2E-SLICE-9F-V2");
    await evidenceForm.getByLabel("Submitted version / revision").fill("v2");
    await evidenceForm.getByRole("button", { name: "Record submission evidence" }).click();
    await expect(page.getByText("Submission evidence recorded.")).toBeVisible();
    await page.getByRole("button", { name: "Record as Submitted / Commercially Committed" }).click();
    await expect(page.getByText("Commercial Offer recorded as submitted. It is now commercially committed.")).toBeVisible();
    await expect(page.getByText("Replaced by v2").first()).toBeVisible();

    await page.getByRole("button", { name: "Edit Commercial Offer / Status" }).click();
    await expect(page.getByLabel("Offer title")).toBeDisabled();
    await expect(page.getByLabel("Offer value")).toBeDisabled();
    await page.getByLabel("Offer status").selectOption("WITHDRAWN");
    await page.getByLabel("Outcome date").fill("2026-10-10");
    await page.getByLabel("Outcome remarks").fill("Customer asked PBL to withdraw this submitted version.");
    await page.getByRole("button", { name: "Save Commercial Offer" }).click();
    await expect(page.getByText("Commercial Offer updated successfully.")).toBeVisible();
    await expect(page.getByLabel("Offer status")).toHaveValue("WITHDRAWN");
    await expect(page.getByLabel("Offer title")).toBeDisabled();
    await expect(page.getByLabel("Outcome date")).toBeEditable();
    await expect(page.getByLabel("Outcome remarks")).toBeEditable();
    await expect(page.getByRole("button", { name: "Save Commercial Offer" })).toBeEnabled();

    await page.getByRole("link", { name: `${record.commercial_offer.offer_code} v1` }).click();
    await expect(page.getByText("Replaced by v2. This version remains read-only history.")).toBeVisible();
  });
});
