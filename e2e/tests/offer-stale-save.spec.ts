import { test, expect, Page } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

const manifest = loadManifest();
const record = manifest.records["stale_save_target"];

test.skip(!record, "core-regression-bundle manifest is missing the 'stale_save_target' record.");

// CS-05a (TB-1 finding TB1-303): two tabs open on one offer. What the first saves stands; the second, opened before
// that save, is refused beside the Save button it pressed and writes nothing - for the offer's details and for a line.

const OFFER_REFUSAL = "Someone else changed this Commercial Offer after you opened it";
const LINE_REFUSAL = "Someone else changed this Commercial Offer line after you opened it";

function offerForm(tab: Page) {
  return tab.locator("form").filter({ has: tab.getByRole("button", { name: "Save Commercial Offer" }) });
}

function lineForm(tab: Page) {
  return tab.locator("form").filter({ has: tab.getByRole("button", { name: "Save line" }) });
}

async function openOffer(tab: Page, offerUrl: string): Promise<void> {
  await tab.goto(offerUrl);
  await expect(tab.getByText(record.commercial_offer.offer_code).first()).toBeVisible();
}

async function openLineEdit(tab: Page): Promise<void> {
  await tab.getByRole("tab", { name: "Lines & Pricing" }).click();
  await tab.getByRole("button", { name: "Edit line" }).click();
  await expect(lineForm(tab)).toBeVisible();
}

test.describe("A stale form cannot overwrite an offer (CS-05a)", () => {
  test("the second tab's save of the offer and of its line is refused beside its own Save button", async ({ page }) => {
    await login(page, "sales1");
    const offerUrl = `/commercial-offers/${record.commercial_offer.public_id}`;
    const second = await page.context().newPage();

    // The offer's details: both tabs open the edit form before either saves.
    await openOffer(page, offerUrl);
    await openOffer(second, offerUrl);
    for (const tab of [page, second]) {
      await tab.getByRole("button", { name: "Edit Commercial Offer / Status" }).click();
    }
    await offerForm(page).getByLabel("Remarks / requirement notes").fill("Saved first, from tab one");
    await offerForm(page).getByRole("button", { name: "Save Commercial Offer" }).click();
    await expect(offerForm(page).getByText("Commercial Offer updated successfully.")).toBeVisible();

    await offerForm(second).getByLabel("Remarks / requirement notes").fill("Saved second, from tab two");
    await offerForm(second).getByRole("button", { name: "Save Commercial Offer" }).click();
    await expect(offerForm(second).getByText(OFFER_REFUSAL)).toBeVisible();

    await openOffer(second, offerUrl);
    await second.getByRole("button", { name: "Edit Commercial Offer / Status" }).click();
    await expect(offerForm(second).getByLabel("Remarks / requirement notes")).toHaveValue("Saved first, from tab one");

    // A line: both tabs open its edit form before either saves.
    await openOffer(page, offerUrl);
    await openOffer(second, offerUrl);
    await openLineEdit(page);
    await openLineEdit(second);
    await lineForm(page).getByLabel("Rate amount").fill("30000");
    await lineForm(page).getByRole("button", { name: "Save line" }).click();
    await expect(page.getByText("Commercial Offer line updated.")).toBeVisible();
    await expect(page.getByText("INR 30,000", { exact: true })).toBeVisible();

    await lineForm(second).getByLabel("Quantity").fill("4");
    await lineForm(second).getByRole("button", { name: "Save line" }).click();
    await expect(lineForm(second).getByText(LINE_REFUSAL)).toBeVisible();

    await openOffer(second, offerUrl);
    await openLineEdit(second);
    await expect(lineForm(second).getByLabel("Rate amount")).toHaveValue("30000.00");
    await expect(lineForm(second).getByLabel("Quantity")).toHaveValue("10.00");

    await second.close();
  });
});
