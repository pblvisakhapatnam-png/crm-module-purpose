import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

// 8A core: Operations allocates the run's invented 250 t crawler cranes to a requirement for two crawler cranes of
// at least 200 t. The core bundle's allocation_target is a Work Order no other spec touches; its site is in
// Maharashtra and not a central-government site. Of the cranes, two can be allocated, one only with a warning
// (its examination runs out during the job) and one cannot (nothing recorded). Cleanup finds the allocations by
// the run's requirement.

type AllocationDemo = {
  requirement_public_id: string;
  requirement_reference: string;
  machine_numbers: { ok_1: string; ok_2: string; warns: string; bare: string };
  kit: { hook: string; counterweight: string; inserts: string[]; sling: string };
};

const manifest = loadManifest();
const demo = (manifest.records["allocation_target"] as unknown as { allocation_demo?: AllocationDemo } | undefined)?.allocation_demo;

test.describe("Allocating machines", () => {
  test("Operations allocates with a warning, lists kit, replaces the machine and frees it", async ({ page }) => {
    test.skip(!demo, "core-regression-bundle manifest has no 'allocation_demo' in 'allocation_target'.");
    const { machine_numbers: machines, kit } = demo!;
    await login(page, "ops1");

    await page.goto(`/resource-requirements/${demo!.requirement_public_id}`);
    await expect(page.getByText("Machines - 0 of 2 units covered")).toBeVisible();
    await page.getByRole("link", { name: "Allocate a machine to unit 1" }).click();
    await expect(page).toHaveURL(/\/resource-assignments\/new\?/);

    // The crane with nothing recorded is shown, and cannot be chosen.
    await expect(page.getByRole("radio", { name: new RegExp(machines.bare) })).toBeDisabled();
    await page.getByRole("radio", { name: new RegExp(machines.warns) }).check();
    const allocate = page.getByRole("button", { name: "Allocate, with these warnings" });
    await allocate.click();
    await expect(page.getByText('Tick "I have seen these warnings" first.')).toBeVisible();
    await page.getByLabel(/I have seen these warnings/).check();
    await allocate.click();

    await expect(page).toHaveURL(/\/resource-assignments\/[0-9a-f-]{36}/);
    await expect(page.getByText("Held for this Work Order")).toBeVisible();
    const firstUrl = page.url();

    // Kit goes to site with it: the hook block, and two of the four counterweight blocks.
    await page.getByRole("button", { name: "Add pieces to Trip (Own Load) 1" }).click();
    await page.getByLabel(`Take ${kit.hook}`).check();
    await page.getByLabel(`How many of ${kit.counterweight}`).fill("2");
    await page.getByRole("button", { name: "List these pieces" }).click();
    await expect(page.getByText("Listed.")).toBeVisible();

    // A crane goes in several loads: the first Trip (Own Load) says which part of it it carries.
    await page.getByLabel("What this load carries").first().fill("Base and carbody");
    await page.getByRole("button", { name: "Save", exact: true }).first().click();
    await expect(page.getByText("Saved.")).toBeVisible();
    await expect(page.getByRole("cell", { name: new RegExp(kit.hook) })).toBeVisible();

    // A breakdown: another crane replaces it, and both stay on the history.
    await page.getByRole("link", { name: "Replace the machine" }).click();
    await expect(page).toHaveURL(/replacing=/);
    await page.getByRole("radio", { name: new RegExp(machines.ok_1) }).check();
    await page.getByLabel("Why it is being replaced").selectOption("BREAKDOWN");
    await page.getByRole("button", { name: "Replace the machine" }).click();
    await expect(page).toHaveURL(/\/resource-assignments\/[0-9a-f-]{36}/);
    await expect(page).not.toHaveURL(firstUrl);
    await expect(page.getByText("Held for this Work Order")).toBeVisible();
    await expect(page.getByRole("link", { name: /^AL-\d{6,}:/ })).toBeVisible();

    // Freed before it goes: the requirement needs machines again.
    await page.getByLabel("Why it is being freed").selectOption("NOT_NEEDED");
    await page.getByRole("button", { name: "Free the machine" }).click();
    await page.getByRole("button", { name: "Yes, free it" }).click();
    await expect(page.getByText("Freed. The allocation stays on the history.")).toBeVisible();
    await expect(page.getByText("Freed", { exact: true }).first()).toBeVisible();

    await page.goto(`/resource-requirements/${demo!.requirement_public_id}`);
    await expect(page.getByText("Replaced", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Machines - 0 of 2 units covered")).toBeVisible();
  });

  test("a read-only role sees the requirement's machines but no way to allocate", async ({ page }) => {
    test.skip(!demo, "core-regression-bundle manifest has no 'allocation_demo' in 'allocation_target'.");
    await login(page, "readonly1");
    await page.goto(`/resource-requirements/${demo!.requirement_public_id}`);
    await expect(page.getByText(/Machines - \d of 2 units covered/)).toBeVisible();
    await expect(page.getByRole("link", { name: /Allocate a machine/ })).toHaveCount(0);
  });
});
