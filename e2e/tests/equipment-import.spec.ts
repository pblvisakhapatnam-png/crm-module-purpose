import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

// ERT-1: Admin brings Plum's machines in. The core bundle's equipment_reference_target has invented models,
// an invented report already confirmed, and a second invented report (in the manifest) that this spec
// uploads: its carrier's model name is not mapped yet, and a new manlift's capacity reads "230 KG <token>".
// Cleanup finds the upload by the report's fingerprint, and everything it brought in by that import.

type EquipmentDemo = {
  token: string;
  crane_machine_number: string;
  carrier_machine_number: string;
  new_manlift_machine_number: string;
  chassis_model_name: string;
  carrier_model_label: string;
  odd_capacity_value: string;
  second_report_file_name: string;
  second_report_csv: string;
};

const manifest = loadManifest();
const demo = (manifest.records["equipment_reference_target"] as unknown as { equipment_demo?: EquipmentDemo } | undefined)?.equipment_demo;

test.describe("Plum's machines into the Equipment Reference", () => {
  test("Admin uploads a report, maps a model, reads a value, pairs a crane, confirms, and sees the machine", async ({ page }) => {
    test.skip(!demo, "core-regression-bundle manifest has no 'equipment_reference_target' record.");
    await login(page, "admin1");

    await page.goto("/equipment/plum-report");
    await page.getByLabel("Report file (CSV, up to 5 MB)").setInputFiles({
      name: demo!.second_report_file_name,
      mimeType: "text/csv",
      buffer: Buffer.from(demo!.second_report_csv, "utf-8"),
    });
    await page.getByRole("button", { name: "Upload and preview" }).click();
    await expect(page).toHaveURL(/\/equipment\/plum-report\/[0-9a-f-]{36}/);
    await expect(page.getByText("Model names to map")).toBeVisible();

    // Map the carrier's Plum name to the carrier model.
    const modelChoice = page.getByRole("combobox", { name: `Model for ${demo!.chassis_model_name}` });
    await modelChoice.selectOption({ label: `${demo!.carrier_model_label} (Crane carrier)` });
    await modelChoice.locator("xpath=ancestor::div[contains(@class, 'page-actions')]").getByRole("button", { name: "Map", exact: true }).click();
    await expect(page.getByText("Mapped. Refresh the preview to see its effect.")).toBeVisible();
    // The same prompt at the top of the page, where the eye goes after mapping (screen check, step 4).
    await expect(page.getByRole("button", { name: "Refresh the preview", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "Confirm", exact: true })).toBeDisabled();

    // Read the new manlift's capacity as 230 kilograms, wherever it appears.
    await page.getByRole("button", { name: `Read "${demo!.odd_capacity_value}" as...` }).click();
    await page.getByLabel("Number", { exact: true }).fill("230");
    // A dropdown by its role: a <select> inside its <label> adds its options' text to the label's own.
    await page.getByRole("combobox", { name: "Unit", exact: true }).selectOption("KILOGRAM");
    await page.getByLabel("Reason", { exact: true }).fill("Plum wrote the unit into the figure.");
    await page.getByRole("button", { name: "Record reading" }).click();
    await expect(page.getByText("Recorded for this value wherever it appears.", { exact: false })).toBeVisible();

    await page.getByRole("button", { name: "Refresh", exact: true }).click();
    await expect(page.getByText("Preview refreshed with everything as it stands now.")).toBeVisible();

    // The carrier is now a part, proposed to its crane; confirm the pair, then the report.
    await expect(page.getByRole("combobox", { name: `Machine for ${demo!.carrier_machine_number}` })).toHaveValue(demo!.crane_machine_number);
    await page.getByLabel(`Confirm pair for ${demo!.carrier_machine_number}`).check();
    await page.getByRole("button", { name: "Confirm", exact: true }).click();
    await expect(page.getByText("Report confirmed. The machines are updated.")).toBeVisible();

    await page.goto("/equipment");
    await page.getByLabel("Machine number or reference").fill(demo!.crane_machine_number);
    const craneLink = page.getByRole("link", { name: /^EQ-\d{6,}$/ });
    await expect(craneLink).toHaveCount(1);
    await craneLink.click();
    await expect(page).toHaveURL(/\/equipment\/machines\/[0-9a-f-]{36}/);
    await expect(page.getByRole("heading", { level: 2 })).toContainText(demo!.crane_machine_number);
    await expect(page.getByRole("link", { name: new RegExp(`${demo!.carrier_machine_number}$`) })).toBeVisible();
    await expect(page.getByText(`ACME AC 100 ${demo!.token}`).first()).toBeVisible();
  });

  test("a read-only role sees machines and is offered no upload", async ({ page }) => {
    test.skip(!demo, "core-regression-bundle manifest has no 'equipment_reference_target' record.");
    await login(page, "readonly1");
    await page.goto("/equipment");
    await page.getByLabel("Machine number or reference").fill(demo!.token);
    await expect(page.getByRole("cell", { name: demo!.crane_machine_number, exact: true })).toBeVisible();
    // Engine and chassis numbers are Admin's only, for now (owner, 25 September 2026).
    await page.getByRole("link", { name: /^EQ-\d{6,}$/ }).first().click();
    await expect(page).toHaveURL(/\/equipment\/machines\/[0-9a-f-]{36}/);
    await expect(page.getByText("Shown to Admin only", { exact: true })).toHaveCount(2);
    await page.goto("/equipment/plum-report");
    await expect(page.getByText("Only Admin uploads and confirms Plum's report.")).toBeVisible();
    await expect(page.getByRole("button", { name: "Upload and preview" })).toHaveCount(0);
  });
});
