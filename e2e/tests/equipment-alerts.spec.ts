import { test, expect, type Page } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

// ELG-2: certificate reminders and escalation. The core bundle's reminder_target holds the run's second 80 t
// crawler on a job in Gujarat from 12 days ahead - its insurance runs out in 6 days, before the job starts - with a
// sling whose examination runs out in 25 days, during it. The run's first 80 t crawler has papers running out in
// 20, 10 and 5 days, and a load test that ran out 2 days ago. On the standard paths, Operations is reached from 15
// days before (at once on a job), Management from 7 days before. This spec never saves a reminder setting: a saved
// version is never edited or deleted, by design, so it would stay in the shared database.

type ReminderDemo = {
  assignment_reference: string;
  machine_numbers: { running_out: string; on_job: string };
  sling_reference: string;
};

const manifest = loadManifest();
const demo = (manifest.records["reminder_target"] as unknown as { reminder_demo?: ReminderDemo } | undefined)?.reminder_demo;

function search(page: Page) {
  return page.getByLabel("Machine, piece, Work Order, allocation or year");
}

function reminderRow(page: Page, text: string | RegExp) {
  return page.getByRole("row").filter({ hasText: text });
}

async function menuCount(page: Page): Promise<number> {
  const count = page.locator(".app-nav-link", { hasText: "Alerts" }).locator(".app-nav-count");
  if ((await count.count()) === 0) return 0;
  return Number(await count.innerText());
}

test.describe("Certificate reminders", () => {
  test("Operations sees what has reached Operations, and marking one seen lowers the count", async ({ page }) => {
    test.skip(!demo, "core-regression-bundle manifest has no 'reminder_demo' in 'reminder_target'.");
    await login(page, "ops1");
    await page.goto("/alerts");
    await search(page).fill(demo!.machine_numbers.running_out);

    // 10 days, 5 days and run out have reached Operations; 20 days has not.
    await expect(reminderRow(page, "Pollution certificate (PUC) runs out on")).toHaveCount(1);
    await expect(reminderRow(page, "Thorough examination runs out on")).toHaveCount(1);
    await expect(reminderRow(page, "Load test ran out on")).toHaveCount(1);
    await expect(reminderRow(page, "Insurance runs out on")).toHaveCount(0);
    // The search's share of all those not seen (the owner, 2 October 2026).
    const shownOf = page.getByText(/ reminders? you have not seen$/);
    await expect(shownOf).toHaveText(/^3 of the \d+ reminders you have not seen$/);

    await expect.poll(() => menuCount(page)).toBeGreaterThan(0);
    const before = await menuCount(page);
    const puc = reminderRow(page, "Pollution certificate (PUC) runs out on");
    await puc.getByRole("button", { name: "Mark as seen" }).click();
    // It stays where it is, "Seen by you", with the message beside it; the menu's count drops by one.
    await expect(puc.getByText("Marked as seen.")).toBeVisible();
    await expect(puc.getByText("Seen by you")).toBeVisible();
    await expect.poll(() => menuCount(page)).toBe(before - 1);
    await expect(shownOf).toHaveText(new RegExp(`^2 of the ${before - 1} reminders you have not seen$`));
    // Only those not seen are listed: read again, it leaves the list; the share stays.
    await page.getByRole("button", { name: "Refresh" }).click();
    await expect(reminderRow(page, "Pollution certificate (PUC) runs out on")).toHaveCount(0);
    await expect(shownOf).toHaveText(new RegExp(`^2 of the ${before - 1} reminders you have not seen$`));
    await page.getByLabel(/Only those I have/).uncheck();
    await expect(reminderRow(page, "Pollution certificate (PUC) runs out on").getByText("Seen by you")).toBeVisible();

    // The allocation reminders reach Operations at once: the machine's insurance before the job, the sling's
    // examination during it.
    await search(page).fill(demo!.assignment_reference);
    await expect(reminderRow(page, /Insurance runs out on .*, before the job at Jetty 4, Invented Port, Dahej, Gujarat starts on/)).toHaveCount(1);
    await expect(reminderRow(page, demo!.sling_reference).filter({ hasText: /Thorough examination runs out on .*, during the job/ })).toHaveCount(1);

    // The allocation opens with the way back to this list, as it was (the owner's screen check).
    await reminderRow(page, demo!.sling_reference).getByRole("link", { name: demo!.assignment_reference }).click();
    await page.getByRole("link", { name: "Back to Alerts" }).click();
    await expect(search(page)).toHaveValue(demo!.assignment_reference);
    await expect(reminderRow(page, demo!.sling_reference)).toHaveCount(1);
  });

  test("Management sees what has come within 7 days, and who has seen it", async ({ page }) => {
    test.skip(!demo, "core-regression-bundle manifest has no 'reminder_demo' in 'reminder_target'.");
    await login(page, "readonly1");
    await page.goto("/alerts");
    await page.getByLabel(/Only those I have/).uncheck();
    await search(page).fill(demo!.machine_numbers.running_out);
    await expect(reminderRow(page, "Thorough examination runs out on")).toHaveCount(1);
    await expect(reminderRow(page, "Load test ran out on")).toHaveCount(1);
    await expect(reminderRow(page, "Pollution certificate (PUC) runs out on")).toHaveCount(0);

    await search(page).fill(demo!.assignment_reference);
    await expect(reminderRow(page, /Insurance runs out on .*, before the job/)).toHaveCount(1);
    await expect(reminderRow(page, demo!.sling_reference)).toHaveCount(0);
  });

  test("the reminder settings only read for Operations", async ({ page }) => {
    await login(page, "ops1");
    await page.goto("/equipment/alert-settings");
    await expect(page.getByRole("heading", { name: "A certificate running out" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "A certificate not yet recorded" })).toBeVisible();
    await expect(page.getByText("Reminders 60, 30, 15, 8, 7, 6, 5, 4, 3, 2 and 1 day before; on the day, and every day after that.").first()).toBeVisible();
    await expect(page.getByRole("button", { name: "Save" })).toHaveCount(0);
  });
});
