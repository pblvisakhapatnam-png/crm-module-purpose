import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadWorkOrderAmendmentsManifest } from "./fixtures/manifest";

const manifest = loadWorkOrderAmendmentsManifest();
const record = manifest.records["amendment_read_only_view"];
const amendment = record?.amendments?.[0];

test.skip(
  !record || !amendment,
  "work-order-amendment-regression-bundle manifest is missing the 'amendment_read_only_view' record."
);

test.describe("Work Order Amendment visibility for a read-only role (Slice 6O.2)", () => {
  test("shows amendment data without any mutation controls", async ({ page }) => {
    await login(page, "readonly1");

    const workOrder = record.work_orders[0];
    await page.goto(`/work-orders/${workOrder.public_id}`);
    await expect(page.getByText(/Amendment #1 - Administrative/)).toBeVisible();
    await expect(page.getByRole("link", { name: "Record Work Order Amendment" })).not.toBeVisible();

    await page.getByRole("link", { name: "Open" }).click();
    await expect(page).toHaveURL(/\/amendments\//);

    await expect(page.getByText("Received", { exact: true }).first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Start Review" })).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Reject" })).not.toBeVisible();
    await expect(page.getByRole("button", { name: "Cancel" })).not.toBeVisible();
    await expect(page.getByRole("button", { name: /^Record (Add|Change|Cancel) Line$/ })).not.toBeVisible();
    await expect(
      page.getByText("Your role can view amendment lines but cannot add or remove them.")
    ).toBeVisible();
  });
});
