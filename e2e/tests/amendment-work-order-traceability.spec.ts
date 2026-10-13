import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadWorkOrderAmendmentsManifest } from "./fixtures/manifest";

const manifest = loadWorkOrderAmendmentsManifest();
const record = manifest.records["commercial_amendment_with_basis"];
const amendment = record?.amendments?.[0];
const changeQuotation = record?.related_offers?.[0];

test.skip(
  !record || !amendment || !changeQuotation,
  "work-order-amendment-regression-bundle manifest is missing the 'commercial_amendment_with_basis' record."
);

test.describe("Work Order Amendment traceability (Slice 6O.2)", () => {
  test("appears on the Work Order and links back to Work Order, Base Offer and commercial basis", async ({ page }) => {
    await login(page, "sales1");

    const workOrder = record.work_orders[0];
    await page.goto(`/work-orders/${workOrder.public_id}`);
    await expect(page.getByText(/Amendment #1 - Commercial/)).toBeVisible();
    await expect(page.getByText("Validated", { exact: true }).first()).toBeVisible();

    const amendmentArticle = page.locator("article", { hasText: "Amendment #1 - Commercial" });
    await amendmentArticle.getByRole("link", { name: "Open" }).click();
    await expect(page).toHaveURL(/\/amendments\//);

    // Source context: Work Order, Base Commercial Offer, Opportunity, Account links.
    await expect(page.getByRole("link", { name: workOrder.work_order_code }).first()).toBeVisible();
    await expect(page.getByRole("link", { name: record.commercial_offer.offer_code }).first()).toBeVisible();
    // The linked Opportunity and Account now show by name, not as a raw UUID, so the link to the
    // exact record is asserted by its destination rather than by its text.
    await expect(page.locator(`a[href^="/opportunities/${record.opportunity.public_id}"]`).first()).toBeVisible();
    await expect(page.locator(`a[href^="/accounts/${record.account.public_id}"]`).first()).toBeVisible();

    // Commercial basis: the accepted Change Quotation.
    await expect(page.getByText(changeQuotation.offer_code).first()).toBeVisible();
    await expect(page.getByText("Change Quotation", { exact: true }).first()).toBeVisible();

    await page.getByRole("link", { name: changeQuotation.offer_code }).first().click();
    await expect(page).toHaveURL(new RegExp(`/commercial-offers/${changeQuotation.public_id}`));
    await expect(page.getByText("Accepted", { exact: true }).first()).toBeVisible();

    await page.goto(`/work-orders/${workOrder.public_id}/amendments/${amendment.public_id}`);
    await page.getByRole("link", { name: "Back to Work Order" }).click();
    await expect(page).toHaveURL(new RegExp(`/work-orders/${workOrder.public_id}`));

    // No wording anywhere on the Work Order claims the amendment has been applied.
    await expect(page.getByText(/applied to the Work Order/i)).not.toBeVisible();
  });
});
