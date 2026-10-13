import { test, expect, type Page } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

// HOL-1: PBL's holiday calendar, and a Work Order's changes to it. The core bundle's holiday_calendar_target starts a
// year of the calendar far ahead - one of the harness's own years, 2095 to 2099, never one anyone keeps - holding
// Republic Day and Holi for all of India and 1 May as Gujarat Day (Gujarat) and Maharashtra Day (Maharashtra), with a
// Work Order over that whole year: line 1's site in Gujarat and line 2's in Maharashtra, both by the day with an
// overtime rate, line 3 with no site, by the hour. The year is the run's, and its cleanup removes it whatever this
// spec saves to it. docs/agent/slices/hol-1-holiday-calendar.md, section 14.

type HolidayDemo = { work_order_public_id: string; calendar_year: number };

const manifest = loadManifest();
const demo = (manifest.records["holiday_calendar_target"] as unknown as { holiday_demo?: HolidayDemo } | undefined)?.holiday_demo;

function holidaysSection(page: Page) {
  return page.locator(".section-card").filter({ hasText: "Holidays: PBL's calendar and this Work Order's changes" });
}

function applyingRow(page: Page, group: string, date: string) {
  return holidaysSection(page).locator("h4", { hasText: group }).locator("xpath=following-sibling::div[1]").getByRole("row").filter({ hasText: date });
}

test.describe("PBL's holiday calendar", () => {
  test("Operations reads the calendar and cannot change it", async ({ page }) => {
    test.skip(!demo, "core-regression-bundle manifest has no 'holiday_demo' in 'holiday_calendar_target'.");
    const year = demo!.calendar_year;
    await login(page, "ops1");
    await page.goto(`/holiday-calendar?year=${year}`);
    await expect(page.getByRole("button", { name: `${year}: Being entered (version 1)` })).toBeVisible();
    for (const name of ["Republic Day", "Holi", "Gujarat Day", "Maharashtra Day"]) {
      // The name's own cell: "Holi" is also inside "Festival holiday".
      await expect(page.getByRole("cell", { name, exact: true })).toHaveCount(1);
    }
    // A national holiday for one state only: Maharashtra's 1 May.
    await expect(page.getByRole("row").filter({ hasText: "Maharashtra Day" })).toContainText("National holiday");
    await expect(page.getByRole("row").filter({ hasText: "Maharashtra Day" })).toContainText("Maharashtra");
    await expect(page.getByRole("button", { name: "Save" })).toHaveCount(0);
    await expect(page.getByRole("button", { name: "Add a holiday" })).toHaveCount(0);
  });

  test("Admin adds a holiday, and a Work Order works one calendar holiday at the overtime rate", async ({ page }) => {
    test.skip(!demo, "core-regression-bundle manifest has no 'holiday_demo' in 'holiday_calendar_target'.");
    const year = demo!.calendar_year;
    await login(page, "admin1");

    // Admin adds Diwali for all of India, and saves the year as version 2.
    await page.goto(`/holiday-calendar?year=${year}`);
    await page.getByRole("button", { name: "Add a holiday" }).click();
    const added = page.getByRole("row").last();
    await added.getByLabel("Date").fill(`${year}-11-01`);
    await added.getByLabel("Holiday").fill("Diwali");
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.getByText("Saved as version 2. Every Work Order uses it from now.")).toBeVisible();
    await expect(page.getByRole("button", { name: `${year}: Being entered (version 2)` })).toBeVisible();

    // The Work Order: before any change, its lines get the calendar for their own state.
    await page.goto(`/work-orders/${demo!.work_order_public_id}`);
    const section = holidaysSection(page);
    await expect(section.getByText("Holidays: not answered yet")).toBeVisible();
    await expect(applyingRow(page, "Line 1 - Gujarat", `1 May ${year}`)).toContainText("Gujarat Day");
    await expect(applyingRow(page, "Line 2 - Maharashtra", `1 May ${year}`)).toContainText("Maharashtra Day");
    await expect(applyingRow(page, "Line 3 - no site recorded", `1 November ${year}`)).toContainText("Diwali");
    await expect(section.getByText(`PBL's holiday calendar for ${year} is not complete yet`)).toBeVisible();

    // It changes the calendar: Holi is worked, every hour at the overtime rate.
    await section.getByLabel("This Work Order and PBL's calendar").selectOption("CALENDAR_CHANGED");
    await section.getByLabel(`This Work Order on 22 March ${year}`).selectOption("OVERTIME_RATE");
    await section.getByLabel(`Note for 22 March ${year}`).fill("Plant runs");
    await section.getByRole("button", { name: "Save holidays" }).click();
    await expect(section.getByText("Holidays saved.")).toBeVisible();
    await expect(section.getByText("Changes PBL's calendar: 1 working day")).toBeVisible();

    // The holidays that apply are read again: a working day for every line; line 3, by the hour, records no
    // overtime rate for it.
    await expect(applyingRow(page, "Line 1 - Gujarat", `22 March ${year}`)).toContainText("Working day, every hour at the line's overtime rate");
    await expect(applyingRow(page, "Line 1 - Gujarat", `22 March ${year}`)).toContainText("Plant runs");
    await expect(applyingRow(page, "Line 3 - no site recorded", `22 March ${year}`)).toContainText("Line 3 records no overtime rate for this day.");
    await expect(applyingRow(page, "Line 2 - Maharashtra", `26 January ${year}`)).toContainText("Holiday: as each line's off-day term says");
  });
});
