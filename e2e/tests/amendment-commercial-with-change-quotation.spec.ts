import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadWorkOrderAmendmentsManifest } from "./fixtures/manifest";

const manifest = loadWorkOrderAmendmentsManifest();
const record = manifest.records["commercial_amendment_create_target"];
const changeQuotation = record?.related_offers?.[0];

test.skip(
  !record || !changeQuotation,
  "work-order-amendment-regression-bundle manifest is missing the 'commercial_amendment_create_target' record or its accepted Change Quotation."
);

test.describe("Record a Commercial Work Order Amendment against an accepted Change Quotation (Slice 6O.2)", () => {
  test("creates, lines, reviews and validates the amendment without mutating the Work Order or the Change Quotation", async ({ page }) => {
    await login(page, "sales1");

    await page.goto(`/commercial-offers/${changeQuotation.public_id}`);
    await expect(page.getByText(changeQuotation.offer_code).first()).toBeVisible();
    await expect(page.getByText("Change Quotation", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Accepted", { exact: true }).first()).toBeVisible();

    await page.getByRole("tab", { name: "Traceability" }).click();
    await expect(page.getByRole("heading", { name: "Work Order Amendment", exact: true })).toBeVisible();
    await expect(page.getByText("No Work Order Amendment is linked to this Commercial Offer yet.")).toBeVisible();

    await page.getByRole("link", { name: "Record Work Order Amendment" }).click();
    await expect(page).toHaveURL(/\/amendments\/new\?relatedOfferId=/);
    await expect(page.getByRole("heading", { name: "Record Work Order Amendment" })).toBeVisible();

    await page.getByLabel(/Received date/).fill("2026-07-13");
    await page.getByLabel(/Amendment reason/).fill("Customer requested a revised day rate per the accepted Change Quotation.");
    await page.getByLabel(/Commercial change summary/).fill("Revise the day rate for the crane hire line.");

    await page.getByRole("button", { name: "Record amendment" }).click();
    await expect(page.getByRole("heading", { name: "Amendment recorded" })).toBeVisible();
    await page.getByRole("link", { name: /^Open Amendment #/ }).click();

    await expect(page).toHaveURL(/\/amendments\//);
    await expect(page.getByText("Commercial", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(changeQuotation.offer_code).first()).toBeVisible();

    // Add one proposed line (ADD_LINE, no source) and confirm original/proposed are distinct columns.
    await page.getByLabel(/Proposed description \/ scope/).fill("Provide one additional 80T crane with operator.");

    // TB-1 finding TB1-801: a refusal keeps the page and says what to correct. A quantity of 0 is refused before
    // sending, naming the field; the server's own list of field errors is shown as a sentence, not React's error screen.
    const addLineButton = page.getByRole("button", { name: "Record Add Line" });
    await page.getByLabel("Proposed quantity").fill("0");
    await addLineButton.click();
    await expect(page.getByText("Proposed quantity must be greater than 0.")).toBeVisible();
    await page.getByLabel("Proposed quantity").fill("1");
    await page.route(
      "**/api/work-orders/*/amendments/*/lines",
      (route) =>
        route.request().method() === "POST"
          ? route.fulfill({
              status: 422,
              json: { detail: [{ type: "greater_than", loc: ["body", "proposed_quantity"], msg: "Input should be greater than 0" }] },
            })
          : route.fallback()
    );
    await addLineButton.click();
    await expect(page.getByText("Check the values entered: one of them is not accepted.")).toBeVisible();
    await expect(page.getByText("Unexpected Application Error!")).toHaveCount(0);
    await page.unrouteAll();

    await addLineButton.click();
    await expect(page.getByText("Amendment line proposal recorded.")).toBeVisible();
    await expect(page.getByText("Not applicable (new line)")).toBeVisible();
    await expect(page.getByText("Provide one additional 80T crane with operator.")).toBeVisible();

    await page.getByRole("button", { name: "Start Review" }).click();
    await expect(page.getByText("Amendment status updated to Under Review.")).toBeVisible();
    await expect(page.getByText("Under Review", { exact: true }).first()).toBeVisible();

    const validateButton = page.getByRole("button", { name: "Validate" });
    await expect(validateButton).toBeEnabled();
    await validateButton.click();
    await expect(page.getByText("Amendment status updated to Validated.")).toBeVisible();
    await expect(page.getByText("Validated", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/has not been applied to the Work Order/i)).toBeVisible();

    // The Work Order itself remains unchanged: same status and the same number of lines
    // as originally handed off (the traceability table shows each line's source Commercial
    // Offer line identity, not the Work Order line's own id, so line count is the
    // meaningful UI-level immutability signal here).
    const workOrder = record.work_orders[0];
    await page.getByRole("link", { name: workOrder.work_order_code }).first().click();
    await expect(page).toHaveURL(new RegExp(`/work-orders/${workOrder.public_id}`));
    await expect(page.getByText("Awaiting release to Ops", { exact: true }).first()).toBeVisible();
    await expect(page.locator(".data-table-wrap table tbody tr")).toHaveCount(workOrder.line_public_ids.length);

    // The Change Quotation itself remains Accepted and unchanged.
    await page.goto(`/commercial-offers/${changeQuotation.public_id}`);
    await expect(page.getByText("Accepted", { exact: true }).first()).toBeVisible();
  });
});
