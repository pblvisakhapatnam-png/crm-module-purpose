import { test, expect, type Page } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

// ELG-1: machine eligibility. The core bundle's equipment_reference_target has a wheeled crane with its
// carrier fitted: road papers on the carrier and the thorough examination on the crane, each with a copy, but
// no load test - so the crane cannot be allocated until one is recorded. Its crawler cranes are not motor
// vehicles on public roads, very likely: the second has its road papers marked not applicable; the first is left
// for this spec. Cleanup finds what the spec records by the run's assets it is on.

type Eligibility = {
  crane_machine_number: string;
  carrier_machine_number: string;
  open_crawler_machine_number: string;
  marked_crawler_machine_number: string;
};

const manifest = loadManifest();
const seeded = (manifest.records["equipment_reference_target"] as unknown as { equipment_eligibility?: Eligibility } | undefined)?.equipment_eligibility;
const TODAY = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());

function daysFromToday(days: number): string {
  const [year, month, day] = TODAY.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10);
}

async function uploadCopy(page: Page, fileName: string) {
  const form = certificates(page).getByRole("form", { name: "Add a file" });
  await form.getByLabel("File", { exact: true }).setInputFiles({
    name: fileName,
    mimeType: "application/pdf",
    buffer: Buffer.from("%PDF-1.4\n% invented certificate copy\n%%EOF\n", "utf-8"),
  });
  await form.getByRole("button", { name: "Upload", exact: true }).click();
  await expect(form.getByText(`File added: ${fileName}.`)).toBeVisible();
}

async function showMachine(page: Page, machineNumber: string): Promise<void> {
  await page.goto("/equipment");
  await page.getByLabel("Machine number or reference").fill(machineNumber);
  const link = page.getByRole("link", { name: /^EQ-\d{6,}$/ });
  await expect(link).toHaveCount(1);
  await link.click();
  await expect(page.getByRole("heading", { level: 2 })).toContainText(machineNumber);
}

function certificates(page: Page) {
  return page.locator("section.section-card").filter({ has: page.getByRole("heading", { name: "Certificates", exact: true }) });
}

function certificateRow(page: Page, kindLabel: string) {
  return certificates(page).getByRole("row").filter({ has: page.getByRole("cell", { name: new RegExp(`^${kindLabel}`) }) });
}

async function checkGujarat(page: Page) {
  const section = page.locator("section.section-card").filter({ has: page.getByRole("heading", { name: "Check for a site", exact: true }) });
  await section.getByRole("combobox", { name: /^The site's state/ }).selectOption({ label: "Gujarat" });
  await section.getByRole("button", { name: "Check", exact: true }).click();
  return section;
}

test.describe("Machine certificates", () => {
  test("Admin records the missing load test with its copy, and the crane may then be allocated", async ({ page }) => {
    test.skip(!seeded, "core-regression-bundle manifest has no 'equipment_eligibility' in 'equipment_reference_target'.");
    await login(page, "admin1");
    await showMachine(page, seeded!.crane_machine_number);

    // Its road papers are its carrier's, and count for it.
    await expect(certificateRow(page, "Registration")).toContainText(`On its fitted part`);
    await expect(certificateRow(page, "Load test")).toContainText("missing");
    let check = await checkGujarat(page);
    await expect(check.getByText("Cannot be allocated", { exact: true })).toBeVisible();

    await certificates(page).getByRole("button", { name: "Record a certificate" }).click();
    await certificates(page).getByRole("combobox", { name: /^Certificate/ }).selectOption({ label: "Load test" });
    await certificates(page).getByLabel("Number, as printed").fill(`LT-E2E-${manifest.run_id}`);
    await certificates(page).getByLabel("Issued by").fill("Invented Competent Person (E2E)");
    await certificates(page).getByLabel(/^Issued on/).fill(TODAY);
    await certificates(page).getByLabel("Valid from").fill(TODAY);
    await certificates(page).getByRole("button", { name: "Record certificate" }).click();
    await expect(certificates(page).getByText("Certificate recorded. Attach its copy below: it counts only with its copy.")).toBeVisible();
    // Recorded, but it counts only once its copy is attached (Q5).
    await expect(certificateRow(page, "Load test")).toContainText("copy missing");

    await uploadCopy(page, "load-test.pdf");
    await expect(certificateRow(page, "Load test")).toContainText("Attached");

    check = await checkGujarat(page);
    await expect(check.getByText("Can be allocated", { exact: true })).toBeVisible();

    // Withdrawing what the answer relied on takes the answer away before any new check (review round 4).
    await certificateRow(page, "Load test").getByRole("button", { name: "Withdraw", exact: true }).click();
    const withdrawForm = certificates(page).locator("div.form-grid").filter({ has: page.getByLabel(/^Why withdraw/) });
    await withdrawForm.getByLabel(/^Why withdraw/).fill("Recorded against the wrong machine (E2E).");
    await withdrawForm.getByRole("button", { name: "Withdraw", exact: true }).click();
    await expect(certificates(page).getByText("Withdrawn. The one before it, if any, is in force again.")).toBeVisible();
    await expect(certificateRow(page, "Load test")).toContainText("missing");
    await expect(check.getByText("Can be allocated", { exact: true })).toHaveCount(0);
    await expect(check.getByRole("table")).toHaveCount(0);
    check = await checkGujarat(page);
    await expect(check.getByText("Cannot be allocated", { exact: true })).toBeVisible();

    // A renewal recorded ahead of time, its copy attached after coming back to the page (review round 3).
    await certificates(page).getByRole("button", { name: "Record a certificate" }).click();
    await certificates(page).getByRole("combobox", { name: /^Certificate/ }).selectOption({ label: "Insurance" });
    await certificates(page).getByLabel("Number, as printed").fill(`INS-E2E-${manifest.run_id}`);
    await certificates(page).getByLabel("Issued by").fill("Invented Insurer (E2E)");
    await certificates(page).getByLabel(/^Issued on/).fill(TODAY);
    await certificates(page).getByLabel("Valid from").fill(daysFromToday(400));
    await certificates(page).getByLabel(/^Valid until/).fill(daysFromToday(764));
    await certificates(page).getByRole("button", { name: "Record certificate" }).click();
    await expect(certificates(page).getByText("Certificate recorded. Attach its copy below: it counts only with its copy.")).toBeVisible();
    await page.reload();
    const renewal = certificates(page).getByRole("listitem").filter({ hasText: `INS-E2E-${manifest.run_id}` });
    await expect(renewal).toContainText("takes over on");
    await expect(renewal).toContainText("copy missing");
    await renewal.getByRole("button", { name: "Attach its copy" }).click();
    await uploadCopy(page, "insurance-renewal.pdf");
    await expect(renewal).toContainText("copy attached");
  });

  test("a session change on the same page withholds the numbers and the buttons again", async ({ page }) => {
    test.skip(!seeded, "core-regression-bundle manifest has no 'equipment_eligibility' in 'equipment_reference_target'.");
    await login(page, "admin1");
    await showMachine(page, seeded!.crane_machine_number);
    await expect(certificateRow(page, "Registration")).toContainText("No. RC-TEST-");
    await expect(certificates(page).getByRole("button", { name: "Record a certificate" })).toBeVisible();

    // Another user signs in without leaving the page (review round 3): nothing loaded under Admin stays.
    const response = await page.request.post("/api/auth/login", { data: { username: "readonly1", password: "password" } });
    expect(response.ok()).toBeTruthy();
    const { access_token: token } = (await response.json()) as { access_token: string };
    await page.evaluate((value) => {
      window.localStorage.setItem("pbl_auth_token", value);
      window.dispatchEvent(new Event("pbl-session-changed"));
    }, token);
    await expect(certificateRow(page, "Registration")).toContainText("number shown to Admin only");
    await expect(certificateRow(page, "Registration")).not.toContainText("No. RC-TEST-");
    await expect(certificates(page).getByRole("button")).toHaveCount(0);
  });

  test("Admin marks a crawler crane's road papers not applicable, which a wheeled crane is not offered", async ({ page }) => {
    test.skip(!seeded, "core-regression-bundle manifest has no 'equipment_eligibility' in 'equipment_reference_target'.");
    await login(page, "admin1");
    await showMachine(page, seeded!.open_crawler_machine_number);

    await certificates(page).getByRole("button", { name: "Mark not applicable" }).click();
    const kinds = certificates(page).getByRole("combobox", { name: /^Certificate that does not apply/ });
    await kinds.selectOption({ label: "Registration" });
    await certificates(page).getByLabel("Why it does not apply").fill("Crawler crane: not equipped to travel on public roads.");
    await certificates(page).getByRole("button", { name: "Mark not applicable", exact: true }).click();
    await expect(certificates(page).getByText("Marked not applicable.")).toBeVisible();
    await expect(certificateRow(page, "Registration")).toContainText("not applicable: Crawler crane");

    // The law is clear for a wheeled crane: only the first-year pollution certificate may be marked.
    await showMachine(page, seeded!.crane_machine_number);
    await certificates(page).getByRole("button", { name: "Mark not applicable" }).click();
    const offered = await certificates(page).getByRole("combobox", { name: /^Certificate that does not apply/ }).locator("option").allTextContents();
    expect(offered).toEqual(["Choose a certificate", "Pollution certificate (PUC)"]);
  });

  test("a read-only role sees certificates without their numbers, copies or buttons", async ({ page }) => {
    test.skip(!seeded, "core-regression-bundle manifest has no 'equipment_eligibility' in 'equipment_reference_target'.");
    await login(page, "readonly1");
    await showMachine(page, seeded!.crane_machine_number);
    await expect(certificateRow(page, "Registration")).toContainText("number shown to Admin only");
    await expect(certificateRow(page, "Registration")).toContainText("Attached");
    await expect(certificates(page).getByRole("button")).toHaveCount(0);
    const check = await checkGujarat(page);
    await expect(check.getByRole("table")).toContainText("Registration");

    await page.goto("/equipment/certificates");
    await page.getByLabel("Machine number or reference").fill(seeded!.marked_crawler_machine_number);
    // The list reloads for the search: wait until it shows only the marked crawler's two examinations.
    const due = page.getByRole("row").filter({ hasText: seeded!.marked_crawler_machine_number });
    await expect(due).toHaveCount(2);
    await expect(due.filter({ hasText: "Thorough examination" })).toContainText("missing");
    await expect(due.filter({ hasText: "Load test" })).toContainText("missing");
    // Its road papers are marked not applicable, with no end: nothing is due for them.
    await expect(due.filter({ hasText: "Registration" })).toHaveCount(0);
  });
});
