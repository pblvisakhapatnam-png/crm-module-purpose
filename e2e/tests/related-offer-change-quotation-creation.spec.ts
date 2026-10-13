import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadRelatedOffersManifest } from "./fixtures/manifest";

const manifest = loadRelatedOffersManifest();
const record = manifest.records["change_quotation_create_target"];

test.skip(
  !record,
  "related-offer-regression-bundle manifest is missing the 'change_quotation_create_target' record."
);
test.skip(!record?.work_orders?.length, "'change_quotation_create_target' record has no pre-created Work Order.");

test.describe("Create Change Quotation from a Work Order (Slice 6O.1)", () => {
  test("creates a separate DRAFT offer series linked to the Work Order and Base Offer without amending the Work Order", async ({
    page,
  }) => {
    const workOrder = record.work_orders[0];
    await login(page, "sales1");

    await page.goto(`/work-orders/${workOrder.public_id}`);
    await expect(page.getByText(workOrder.work_order_code).first()).toBeVisible();
    await expect(page.getByRole("heading", { name: "Related Commercial Offers", exact: true })).toBeVisible();
    await expect(
      page.getByText("No Supplementary Offer or Change Quotation is linked to this Work Order yet.")
    ).toBeVisible();

    await page.getByRole("link", { name: "Create Change Quotation" }).click();
    await expect(page).toHaveURL(/\/related-offers\/new\?purpose=CHANGE_QUOTATION/);
    await expect(page.getByRole("heading", { name: "Create Change Quotation" })).toBeVisible();
    await expect(page.getByText(record.commercial_offer.offer_code).first()).toBeVisible();

    // The single linked Work Order is auto-selected because change_quotation_create_target has exactly one.
    await expect(page.getByLabel(/Linked Work Order/)).toHaveValue(workOrder.public_id);

    await page.getByLabel(/Request \/ change summary/).fill("Customer requested a revised price before an amendment.");

    await page.getByRole("button", { name: "Create Change Quotation" }).click();
    await expect(page.getByRole("heading", { name: "Change Quotation created" })).toBeVisible();

    const openLink = page.getByRole("link", { name: /^Open CO-/ });
    await expect(openLink).toBeVisible();
    await openLink.click();

    await expect(page).toHaveURL(/\/commercial-offers\//);
    await expect(page.getByText("Change Quotation", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Draft", { exact: true }).first()).toBeVisible();

    await page.getByRole("tab", { name: "Traceability" }).click();
    await expect(page.getByText(workOrder.work_order_code).first()).toBeVisible();

    // Return to the Work Order and confirm it now shows the Change Quotation, and the Work
    // Order shell itself is still the unreleased handoff shell (not amended/released/posted).
    // (The page's own explanatory copy legitimately contains the substring "this Work Order
    // has been amended" as part of a negation -- "does not mean ... has been amended" -- so a
    // naive text-absence check on that phrase would false-positive on the correct disclaimer;
    // asserting the "Awaiting release to Ops" status badge is what "not amended" concretely means here.)
    await page.goto(`/work-orders/${workOrder.public_id}`);
    await expect(page.getByText(/Change Quotation/).first()).toBeVisible();
    await expect(page.getByText("Awaiting release to Ops", { exact: true }).first()).toBeVisible();
  });
});
