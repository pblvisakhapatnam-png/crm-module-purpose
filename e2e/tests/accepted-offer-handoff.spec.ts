import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

const manifest = loadManifest();
const record = manifest.records["handoff_target"];

test.skip(!record, "core-regression-bundle manifest is missing the 'handoff_target' record.");

test.describe("Accepted Commercial Offer -> Work Order shell handoff", () => {
  test("creates the Work Order shell and shows correct traceability", async ({ page }) => {
    await login(page, "sales1");

    await page.goto(`/commercial-offers/${record.commercial_offer.public_id}`);
    await expect(page.getByText(record.commercial_offer.offer_code).first()).toBeVisible();
    await expect(page.getByText("Accepted", { exact: true }).first()).toBeVisible();

    await expect(page.getByText(record.opportunity.public_id).first()).toBeVisible();
    await expect(page.getByText(record.account.public_id).first()).toBeVisible();

    await page.getByRole("tab", { name: "Submission" }).click();
    await expect(page.getByText("Before you create the Work Order").first()).toBeVisible();
    await expect(
      page.getByText("No Work Order has been created yet from this Commercial Offer.").first()
    ).toBeVisible();

    await page.getByRole("link", { name: "Create Work Order", exact: true }).first().click();
    await expect(page).toHaveURL(/\/work-orders\/new/);
    await expect(page.getByText(record.commercial_offer.offer_code).first()).toBeVisible();
    await expect(
      page.getByText("No Work Order has been created yet from this Commercial Offer.").first()
    ).toBeVisible();

    // Since CS-04 part 1 the customer's Work Order reference is required: one customer order makes one Work Order.
    await page.getByLabel(/Customer WO reference/).fill(`E2E-LOI-${Date.now()}`);
    await page.getByRole("button", { name: "Create Work Order", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Work Order created" })).toBeVisible();

    // TB-1 CS-04 part 1 (review round 2): after creating, the page reads the offer again - what each line has left
    // comes from the server - so the line now shows as on a Work Order in full and Create is no longer offered.
    await expect(page.getByText(/Already on a Work Order in full: WO-/).first()).toBeVisible();
    await expect(page.getByText("Every line of this offer is already on a Work Order in full.").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Create Work Order", exact: true })).toBeDisabled();

    const openLink = page.getByRole("link", { name: /^Open WO-/ });
    await expect(openLink).toBeVisible();
    const workOrderHref = await openLink.getAttribute("href");
    expect(workOrderHref).toBeTruthy();

    await openLink.click();
    await expect(page).toHaveURL(/\/work-orders\//);

    await expect(page.getByText("Awaiting release to Ops", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(record.commercial_offer.offer_code).first()).toBeVisible();
    await expect(page.getByText(record.opportunity.public_id).first()).toBeVisible();
    await expect(page.getByText(record.account.public_id).first()).toBeVisible();

    // Line traceability: the Work Order line must carry the source Commercial Offer line identity.
    const traceabilityRow = page.getByRole("row", { name: new RegExp(record.commercial_offer.line_public_id) });
    await expect(traceabilityRow).toBeVisible();

    const returnLink = page.getByRole("link", { name: "Back to Commercial Offer" });
    await expect(returnLink).toBeVisible();
    await returnLink.click();
    await expect(page).toHaveURL(new RegExp(`/commercial-offers/${record.commercial_offer.public_id}`));
  });
});
