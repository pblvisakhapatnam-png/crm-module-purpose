import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadWorkOrderAmendmentsManifest } from "./fixtures/manifest";

const manifest = loadWorkOrderAmendmentsManifest();
const record = manifest.records["blocked_validation_target"];
const amendment = record?.amendments?.[0];

test.skip(
  !record || !amendment,
  "work-order-amendment-regression-bundle manifest is missing the 'blocked_validation_target' record or its amendment."
);

test.describe("Commercial Work Order Amendment blocked from validation without an accepted basis (Slice 6O.2)", () => {
  test("shows the backend blocking reason and disables Validate", async ({ page }) => {
    await login(page, "sales1");

    const workOrder = record.work_orders[0];
    await page.goto(`/work-orders/${workOrder.public_id}/amendments/${amendment.public_id}`);

    await expect(page.getByText("Under Review", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Commercial", { exact: true }).first()).toBeVisible();
    await expect(
      page.getByText(/must be Accepted through its own lifecycle before this amendment can be validated/i)
    ).toBeVisible();

    const validateButton = page.getByRole("button", { name: "Validate" });
    await expect(validateButton).toBeVisible();
    await expect(validateButton).toBeDisabled();

    // The amendment is still editable/under review, not terminal: Reject/Cancel remain
    // available and no terminal read-only wording is shown.
    await expect(page.getByRole("button", { name: "Reject" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Cancel" })).toBeVisible();
    await expect(page.getByText(/is read-only\. It has not been applied/i)).not.toBeVisible();
  });
});
