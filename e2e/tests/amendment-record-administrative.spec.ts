import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadWorkOrderAmendmentsManifest } from "./fixtures/manifest";

const manifest = loadWorkOrderAmendmentsManifest();
const record = manifest.records["administrative_amendment_create_target"];

test.skip(
  !record,
  "work-order-amendment-regression-bundle manifest is missing the 'administrative_amendment_create_target' record."
);

test.describe("Record an Administrative Work Order Amendment (Slice 6O.2)", () => {
  test("records intake, leaves the Work Order unchanged and shows it in the Amendments section", async ({ page }) => {
    await login(page, "sales1");

    const workOrder = record.work_orders[0];
    await page.goto(`/work-orders/${workOrder.public_id}`);
    await expect(page.getByText("Awaiting release to Ops", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("No Work Order Amendment has been recorded yet.")).toBeVisible();

    await page.getByRole("link", { name: "Record Work Order Amendment" }).click();
    await expect(page).toHaveURL(/\/amendments\/new/);
    await expect(page.getByRole("heading", { name: "Record Work Order Amendment" })).toBeVisible();
    await expect(page.getByText(workOrder.work_order_code).first()).toBeVisible();

    await page.getByLabel(/Received date/).fill("2026-07-13");
    await page.getByLabel(/Amendment reason/).fill("Customer requested a mobilisation date change via E2E test.");

    await page.getByRole("button", { name: "Record amendment" }).click();
    await expect(page.getByRole("heading", { name: "Amendment recorded" })).toBeVisible();

    const openLink = page.getByRole("link", { name: /^Open Amendment #/ });
    await expect(openLink).toBeVisible();
    await openLink.click();

    await expect(page).toHaveURL(/\/amendments\//);
    await expect(page.getByText("Received", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Administrative", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/does not change the Work Order/i)).toBeVisible();

    const backLink = page.getByRole("link", { name: "Back to Work Order" });
    await expect(backLink).toBeVisible();
    await backLink.click();

    await expect(page).toHaveURL(new RegExp(`/work-orders/${workOrder.public_id}`));
    await expect(page.getByText("Awaiting release to Ops", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/Amendment #1 - Administrative/)).toBeVisible();
  });
});
