import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

// WRR-001: Operations records what a Work Order line needs on site. The core bundle's
// resource_requirement_target is a Work Order no other spec touches; read_only_view is the read-only
// role's own Work Order, which this spec only reads.

const manifest = loadManifest();
const record = manifest.records["resource_requirement_target"];
const readOnly = manifest.records["read_only_view"];

test.describe("Resource requirements on a Work Order line", () => {
  test("Operations adds a requirement, sees it on the Work Order and the planning list, and cancels it", async ({ page }) => {
    test.skip(!record?.work_orders?.length, "core-regression-bundle manifest has no 'resource_requirement_target' Work Order.");
    const workOrder = record.work_orders[0];
    await login(page, "ops1");

    await page.goto(`/work-orders/${workOrder.public_id}`);
    await expect(page.getByText("What each line needs on site")).toBeVisible();
    await page.getByRole("link", { name: "Add a requirement" }).first().click();
    await expect(page).toHaveURL(/\/resource-requirements\/new\?/);

    // The seeded line's category is "Crane", so the class is suggested.
    const machineKind = page.getByLabel("Kind of machine");
    await expect(machineKind).toHaveValue("CRANE");
    await page.getByLabel("Number of machines").fill("2");
    await page.getByRole("combobox", { name: "Type", exact: true }).selectOption("CRAWLER");
    await page.getByLabel("Rated capacity (t), at least").fill("220");
    await page.getByLabel("Needed from").fill("2027-01-10");
    await page.getByRole("spinbutton", { name: "Operators", exact: true }).fill("1");
    await page.getByRole("spinbutton", { name: "Helpers", exact: true }).fill("1");
    await page.getByRole("button", { name: "Save requirement" }).click();

    await expect(page).toHaveURL(/\/resource-requirements\/[0-9a-f-]{36}/);
    const title = page.getByRole("heading", { level: 2 });
    await expect(title).toContainText("2 x Crawler crane, rated capacity at least 220 t");
    const reference = ((await title.textContent()) ?? "").match(/RR-\d{6,}/)?.[0];
    expect(reference, "the requirement's reference is in the page title").toBeTruthy();

    await page.goto(`/work-orders/${workOrder.public_id}`);
    await expect(page.getByRole("link", { name: reference!, exact: true })).toBeVisible();

    await page.goto("/resource-requirements");
    await page.getByRole("link", { name: reference!, exact: true }).click();
    await expect(page).toHaveURL(/\/resource-requirements\/[0-9a-f-]{36}/);

    await page.getByLabel("Why it is being cancelled").fill("Customer will use its own crane");
    await page.getByRole("button", { name: "Cancel this requirement" }).click();
    await page.getByRole("button", { name: "Yes, cancel it" }).click();
    await expect(page.getByText("Requirement cancelled.")).toBeVisible();
    await expect(page.getByText("Cancelled", { exact: true }).first()).toBeVisible();
    // Final: nothing left to change or cancel.
    await expect(page.getByRole("button", { name: "Change the requirement" })).toHaveCount(0);
  });

  test("a read-only role sees what each line needs but is offered no way to add a requirement", async ({ page }) => {
    test.skip(!readOnly?.work_orders?.length, "core-regression-bundle manifest has no 'read_only_view' Work Order.");
    await login(page, "readonly1");
    await page.goto(`/work-orders/${readOnly.work_orders[0].public_id}`);
    await expect(page.getByText("What each line needs on site")).toBeVisible();
    await expect(page.getByText("No requirement recorded for this line.").first()).toBeVisible();
    // Substring match on purpose: for an absence check, the broader match is the stronger assertion.
    await expect(page.getByRole("link", { name: "Add a requirement" })).toHaveCount(0);
  });
});
