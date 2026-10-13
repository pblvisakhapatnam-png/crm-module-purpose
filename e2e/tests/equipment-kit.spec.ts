import { test, expect, type Page } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

// ERT-2: detachable kit, held for the crane models it fits. The core bundle's equipment_reference_target has
// a second invented crane model with two cranes, and kit held for it: two boom inserts, a counted set of four
// counterweight blocks, and a hook block model with nothing held yet. This spec adds hook blocks from one
// crane's page, sees them on the other crane's, and retires one insert. Cleanup finds what it adds by its
// model, which the run made.

type EquipmentKit = {
  crane_model_label: string;
  crane_machine_numbers: string[];
  insert_model_label: string;
  counterweight_model_label: string;
  hook_model_label: string;
};

const manifest = loadManifest();
const kit = (manifest.records["equipment_reference_target"] as unknown as { equipment_kit?: EquipmentKit } | undefined)?.equipment_kit;

async function openMachine(page: Page, machineNumber: string): Promise<void> {
  await page.goto("/equipment");
  await page.getByLabel("Machine number or reference").fill(machineNumber);
  const link = page.getByRole("link", { name: /^EQ-\d{6,}$/ });
  await expect(link).toHaveCount(1);
  await link.click();
  await expect(page.getByRole("heading", { level: 2 })).toContainText(machineNumber);
}

function kitRow(page: Page, modelLabel: string) {
  return page.getByRole("row").filter({ has: page.getByRole("link", { name: modelLabel, exact: true }) });
}

test.describe("Detachable kit", () => {
  test("Admin adds kit to a crane model, sees it on both its cranes, and retires a piece", async ({ page }) => {
    test.skip(!kit, "core-regression-bundle manifest has no 'equipment_kit' in 'equipment_reference_target'.");
    await login(page, "admin1");

    await openMachine(page, kit!.crane_machine_numbers[0]);
    await expect(page.getByText(`Kit for ${kit!.crane_model_label}`)).toBeVisible();
    await expect(page.getByText("shared by 2 active cranes of it", { exact: false })).toBeVisible();
    await expect(kitRow(page, kit!.insert_model_label)).toContainText("2 held");
    await expect(kitRow(page, kit!.counterweight_model_label)).toContainText("4 held, counted");
    await expect(kitRow(page, kit!.hook_model_label)).toContainText("None held yet");

    // Two hook blocks alike, from this crane's page: they are the model's, not this crane's.
    await page.getByRole("button", { name: "Add kit", exact: true }).click();
    await page.getByRole("combobox", { name: /^Kit model/ }).selectOption({ label: `${kit!.hook_model_label} (hook block)` });
    await page.getByLabel("How many alike").fill("2");
    await page.getByRole("button", { name: "Add kit", exact: true }).click();
    await expect(page.getByText(`Added to the kit for this model: 2 records of ${kit!.hook_model_label}.`)).toBeVisible();
    await expect(kitRow(page, kit!.hook_model_label)).toContainText("2 held");

    // The other crane of the model holds the same kit.
    await openMachine(page, kit!.crane_machine_numbers[1]);
    await expect(kitRow(page, kit!.hook_model_label)).toContainText("2 held");

    // One insert is scrapped: retired with the reason, and kept.
    await kitRow(page, kit!.insert_model_label).getByRole("link", { name: kit!.insert_model_label, exact: true }).click();
    await expect(page).toHaveURL(/\/equipment\?kit_model=[0-9a-f-]{36}/);
    await expect(page.getByText("Showing the pieces of one kit model.")).toBeVisible();
    const pieces = page.getByRole("link", { name: /^EQ-\d{6,}$/ });
    await expect(pieces).toHaveCount(2);
    await pieces.first().click();
    await expect(page.getByText("Equipment - kit")).toBeVisible();
    await expect(page.getByText(kit!.crane_model_label, { exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Retire this piece" }).click();
    await page.getByRole("combobox", { name: /^Why/ }).selectOption("SCRAPPED");
    await page.getByRole("button", { name: "Retire", exact: true }).click();
    await expect(page.getByText("Retired. Its history is kept.")).toBeVisible();
    await expect(page.getByText(/^Retired on \d{4}-\d{2}-\d{2}: scrapped\.$/)).toBeVisible();
  });

  test("a read-only role sees the kit and is offered no kit action", async ({ page }) => {
    test.skip(!kit, "core-regression-bundle manifest has no 'equipment_kit' in 'equipment_reference_target'.");
    await login(page, "readonly1");
    await openMachine(page, kit!.crane_machine_numbers[0]);
    await expect(kitRow(page, kit!.counterweight_model_label)).toContainText("4 held, counted");
    await expect(page.getByRole("button", { name: "Add kit" })).toHaveCount(0);
    await kitRow(page, kit!.counterweight_model_label).getByRole("link", { name: kit!.counterweight_model_label, exact: true }).click();
    await page.getByRole("link", { name: /^EQ-\d{6,}$/ }).first().click();
    await expect(page.getByText("Equipment - kit")).toBeVisible();
    await expect(page.getByText("Pieces in the set")).toBeVisible();
    await expect(page.getByRole("button", { name: /^Retire/ })).toHaveCount(0);
  });
});
