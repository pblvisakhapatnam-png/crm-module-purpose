import { Locator, Page, expect, test } from "@playwright/test";

import { login } from "../tests/fixtures/auth";

// TE-7: the user guide's pictures (see playwright.guide.config.ts); TE-8 adds the holiday calendar (9, 10). Each is the part of the page the guide talks
// about, captured as the role the guide describes, from the practice data's fixed codes and machine numbers.

const OUT = "guide/out";

function card(page: Page, title: string): Locator {
  return page.locator("section.section-card", { has: page.locator("h4.section-card-title", { hasText: title }) }).first();
}

// A part of the page, cut from a full-page picture. Playwright's own element picture lost the foot of a card about a
// viewport tall (a grey band over its last row), so every card is cut this way.
async function shoot(page: Page, target: Locator, file: string): Promise<void> {
  await page.evaluate(() => window.scrollTo(0, 0));
  const box = await target.boundingBox();
  if (!box) throw new Error(`${file}: nothing to photograph`);
  await page.screenshot({ path: `${OUT}/${file}`, fullPage: true, clip: box });
}

async function openFromList(page: Page, listPath: string, code: string): Promise<void> {
  await page.goto(listPath);
  await page.getByRole("link", { name: code, exact: true }).first().click();
  await expect(page.getByText(code).first()).toBeVisible();
}

test("the Hiring user guide's screenshots", async ({ page }) => {
  // 0. The flow at a glance, drawn here so it stays in step with the guide's table.
  const steps = [
    ["1", "Offer accepted, Work Order made", "Commercial Offers", "Sales"],
    ["2", "Site, billing, central-government site?", "Work Orders", "Sales · Operations"],
    ["3", "Billing terms, contract, holidays", "Work Orders", "Sales · Operations"],
    ["3a", "PBL's holiday calendar", "Holiday Calendar", "Fleet Admin (Admin)"],
    ["4", "What each line needs", "Work Order › Resources needed", "Operations"],
    ["5", "The fleet: Plum report, models, kit", "Equipment", "Fleet Admin"],
    ["6", "Each machine's certificates", "Equipment › a machine", "Fleet Admin"],
    ["7", "Allocate a machine (checked)", "Resource Planning", "Operations"],
    ["8", "Trips, kit, replace, free", "Allocations", "Operations"],
    ["9", "Reminders and escalation", "Alerts", "Everyone reached"],
  ];
  await page.setContent(`<!doctype html><html><head><style>
    body { margin: 0; font: 15px/1.35 "Segoe UI", Arial, sans-serif; color: #1f2933; background: #fff; }
    .flow { display: grid; grid-template-columns: repeat(3, 300px); gap: 14px 36px; padding: 22px; width: fit-content; }
    .step { border: 2px solid #2563eb; border-radius: 10px; padding: 10px 12px; background: #eff6ff; position: relative; }
    .step.fleet { border-color: #0f766e; background: #ecfdf5; }
    .step.alert { border-color: #b45309; background: #fffbeb; }
    .n { font-weight: 700; color: #2563eb; } .fleet .n { color: #0f766e; } .alert .n { color: #b45309; }
    .what { font-weight: 600; } .menu { color: #475569; font-size: 13px; } .who { font-size: 13px; margin-top: 4px; }
    </style></head><body><div class="flow" id="flow">${steps
      .map(([n, what, menu, who]) => {
        const kind = n === "3a" || n === "5" || n === "6" ? "fleet" : n === "9" ? "alert" : "";
        return `<div class="step ${kind}"><div><span class="n">${n}</span> <span class="what">${what}</span></div><div class="menu">Menu: ${menu}</div><div class="who">Who: ${who}</div></div>`;
      })
      .join("")}</div></body></html>`);
  await page.locator("#flow").screenshot({ path: `${OUT}/00-flow.png` });

  // PBL's holiday calendar for this year and next, complete, as the restart's pre-load (`hiring-uat-fleet`) holds them;
  // `hiring-uat-seeded` has none. Started once: a rerun finds the years there.
  await login(page, "admin1");
  await page.goto("/");
  const adminToken = await page.evaluate(() => window.localStorage.getItem("pbl_auth_token"));
  const thisYear = new Date().getFullYear();
  const practice = (year: number) => [
    [`${year}-01-26`, "NATIONAL", "Republic Day", []],
    [`${year}-05-01`, "FESTIVAL", "Gujarat Day", ["IN-GJ"]],
    [`${year}-05-01`, "NATIONAL", "Maharashtra Day", ["IN-MH"]],
    [`${year}-08-15`, "NATIONAL", "Independence Day", []],
    [`${year}-10-02`, "NATIONAL", "Gandhi Jayanti", []],
    [`${year}-12-25`, "FESTIVAL", "Christmas", []],
  ];
  for (const year of [thisYear, thisYear + 1]) {
    const current = await page.request.get(`/api/holiday-calendar/years/${year}`, { headers: { Authorization: `Bearer ${adminToken}` } });
    expect(current.ok(), await current.text()).toBeTruthy();
    if ((await current.json()).year_version !== null) continue;
    const saved = await page.request.put(`/api/holiday-calendar/years/${year}`, {
      headers: { Authorization: `Bearer ${adminToken}`, "Content-Type": "application/json" },
      data: {
        expected_version: null,
        is_complete: true,
        holidays: practice(year).map(([holiday_date, holiday_kind_code, holiday_name, state_codes]) => ({
          holiday_date, holiday_kind_code, holiday_name,
          applies_to_code: (state_codes as string[]).length ? "STATES" : "ALL_INDIA",
          state_codes,
        })),
      },
    });
    expect(saved.ok(), await saved.text()).toBeTruthy();
  }

  // 1. The menu, as Operations, with the Alerts count.
  await login(page, "ops1");
  await page.goto("/");
  await expect(page.locator(".app-nav-link", { hasText: "Alerts" }).locator(".app-nav-count")).toBeVisible();
  await shoot(page, page.locator("aside.app-sidebar"), "01-menu.png");

  // 2. Create Work Order, top right of an accepted offer: accept CO-000004 as Sales, through the API the page uses.
  await login(page, "sales1");
  await openFromList(page, "/commercial-offers", "CO-000004");
  const header = page.locator("header.page-header").first();
  await expect(header.getByRole("button", { name: "Refresh" })).toBeEnabled();
  if (!(await header.getByText("Accepted", { exact: true }).isVisible())) {
    const offerId = page.url().split("/").pop()!.split("?")[0];
    const token = await page.evaluate(() => window.localStorage.getItem("pbl_auth_token"));
    const accepted = await page.request.post(`/api/commercial-offers/${offerId}/customer-responses`, {
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      data: { response_outcome: "ACCEPTED_AWARDED", response_received_at: "2026-10-01T11:00:00", response_channel: "EMAIL" },
    });
    expect(accepted.ok(), await accepted.text()).toBeTruthy();
    await page.reload();
  }
  await expect(header.getByRole("link", { name: "Create Work Order" })).toBeVisible();
  await expect(header.getByRole("button", { name: "Refresh" })).toBeEnabled();
  await shoot(page, header, "02-create-work-order.png");

  // 3. Site and billing details on Operations tester 1's Work Order, as Sales (who may change them): every line
  // folded but the central-government refinery line.
  await openFromList(page, "/work-orders", "WO-000001");
  const sites = card(page, "Site and billing details");
  await expect(sites.getByText("Loading the saved details...")).toHaveCount(0);
  await sites.getByRole("button", { name: "Collapse all lines" }).click();
  await sites.locator("details > summary", { hasText: "Line 3 -" }).click();
  await expect(sites.getByRole("button", { name: "Save details" })).toHaveCount(1);
  await shoot(page, sites, "03-site-and-billing.png");

  // 4. Billing terms on the Sales and Accounts Work Order: line 1 open with its two periods folded to their bands.
  await openFromList(page, "/work-orders", "WO-000003");
  const terms = card(page, "Billing terms");
  await expect(terms.getByText("Loading the billing terms...")).toHaveCount(0);
  await terms.getByRole("button", { name: "Hide terms for all lines" }).click();
  await terms.locator("details > summary", { hasText: "Line 1 -" }).click();
  const openBands = terms.locator("details.terms-period[open] > summary.terms-period-band").filter({ visible: true });
  await expect(async () => {
    if ((await openBands.count()) > 0) await openBands.first().click();
    await expect(openBands).toHaveCount(0, { timeout: 1_000 });
  }).toPass();
  await expect(terms.locator("details.terms-period").filter({ visible: true })).toHaveCount(2);
  await shoot(page, terms, "04-billing-terms.png");

  // 5. A machine's certificates, as the Fleet Admin: the transport crane whose permit covers Maharashtra only.
  await login(page, "admin1");
  await page.goto("/equipment");
  await page.getByLabel("Machine number or reference, or a piece's own number").fill("UAT-AC100-02");
  await page.getByRole("row", { name: /UAT-AC100-02/ }).getByRole("link").first().click();
  await expect(page.getByText("UAT-AC100-02").first()).toBeVisible();
  const certificates = page.locator("section.section-card", { has: page.locator("h4.section-card-title", { hasText: /^Certificates$/ }) });
  await expect(certificates.getByRole("cell", { name: /^Permit/ })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await shoot(page, certificates, "05-machine-certificates.png");

  // 6. Allocating to the central-government refinery line in Gujarat, as Operations: every answer side by side.
  await login(page, "ops1");
  await openFromList(page, "/resource-requirements", "RR-000003");
  await page.getByRole("link", { name: /Allocate a machine to unit 1/ }).click();
  await page.getByRole("button", { name: "Find machines for these days" }).click();
  const machines = page.locator("section.section-card", { has: page.locator("h4.section-card-title", { hasText: /^Machines for/ }) }).first();
  await expect(machines.getByText("UAT-AC100-02")).toBeVisible();
  await shoot(page, machines, "06-allocate.png");

  // 7. The allocation with kit on two trips.
  await openFromList(page, "/resource-assignments", "AL-000001");
  const trips = card(page, "Trips (Own Load) to site");
  await expect(trips.getByRole("button", { name: "Add a Trip (Own Load)" })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await shoot(page, trips, "07-allocation.png");

  // 8. Alerts, as Operations.
  await page.goto("/alerts");
  await expect(page.getByText(/reminders? you have not seen/)).toBeVisible();
  await page.screenshot({ path: `${OUT}/08-alerts.png` });

  // 9. PBL's holiday calendar, next year, as the Fleet Admin (Admin): the editor.
  await login(page, "admin1");
  await page.goto("/holiday-calendar");
  await page.getByRole("button", { name: new RegExp(`^${thisYear + 1}: Complete`) }).click();
  const calendar = card(page, `${thisYear + 1}`);
  await expect(calendar.getByRole("button", { name: "Add a holiday" })).toBeVisible();
  await shoot(page, calendar, "09-holiday-calendar.png");

  // 10. A Work Order's holidays and the holidays that apply, as Sales, on the Sales and Accounts Work Order.
  await login(page, "sales1");
  await openFromList(page, "/work-orders", "WO-000003");
  const holidays = card(page, "Holidays: PBL's calendar and this Work Order's changes");
  await expect(holidays.getByRole("button", { name: "Save holidays" })).toBeVisible();
  await page.waitForLoadState("networkidle");
  await shoot(page, holidays, "10-holidays.png");
});
