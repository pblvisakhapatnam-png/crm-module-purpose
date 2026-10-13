import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

const manifest = loadManifest();
const record = manifest.records["existing_traceability"];

test.skip(!record, "core-regression-bundle manifest is missing the 'existing_traceability' record.");
test.skip(!record?.work_orders?.length, "'existing_traceability' record has no pre-created Work Order.");

test.describe("Existing Work Order traceability on an already-handed-off offer", () => {
  test("Commercial Offer shows the linked Work Order without a misleading fully-handed-off statement", async ({
    page,
  }) => {
    const workOrder = record.work_orders[0];
    // Logged in as admin1 (ADMIN is in EVENT_VIEW_ROLES) so the provenance section's
    // underlying WorkOrderCreated business event detail is asserted, not just the
    // always-visible creation timestamp/creator that every role sees.
    await login(page, "admin1");

    await page.goto(`/commercial-offers/${record.commercial_offer.public_id}`);
    await page.getByRole("tab", { name: "Submission" }).click();

    await expect(page.getByText("Before you create the Work Order").first()).toBeVisible();
    await expect(
      page.getByText(`${record.work_orders.length} Work Order(s) already exist for this Commercial Offer`)
    ).toBeVisible();
    await expect(page.getByText(workOrder.work_order_code).first()).toBeVisible();

    // Since CS-04 part 1 (8 October 2026) an offer line's quantity goes onto Work Orders once, whole or in
    // parts. This offer's one Work Order holds every line in full, so the panel says so and offers no further
    // Work Order; an offer with something left would offer "Create another Work Order".
    await expect(page.getByText("Every line of this offer is already on a Work Order in full.").first()).toBeVisible();
    await expect(page.getByRole("link", { name: "Create another Work Order" })).toHaveCount(0);
    // The note under the existing Work Orders states the rule and points to no link the page does not show (review
    // round 8: it once said a second Work Order was "not offered here" beside a link offering one).
    await expect(page.getByText("it takes only what is not on a Work Order yet").first()).toBeVisible();
    await expect(page.getByText("not offered here")).toHaveCount(0);

    await page.getByRole("link", { name: "Open Work Order", exact: true }).first().click();
    await expect(page).toHaveURL(new RegExp(`/work-orders/${workOrder.public_id}`));

    await expect(page.getByText("Awaiting release to Ops", { exact: true }).first()).toBeVisible();

    const traceabilityRow = page.getByRole("row", { name: new RegExp(record.commercial_offer.line_public_id) });
    await expect(traceabilityRow).toBeVisible();

    // Admin/Management Read Only roles see the underlying business event in the provenance section.
    await expect(page.getByText("How this Work Order was created").first()).toBeVisible();
    await expect(page.getByText("WorkOrderCreated").first()).toBeVisible();
  });
});
