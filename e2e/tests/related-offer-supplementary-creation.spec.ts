import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadRelatedOffersManifest } from "./fixtures/manifest";

const manifest = loadRelatedOffersManifest();
const record = manifest.records["supplementary_offer_create_target"];

test.skip(
  !record,
  "related-offer-regression-bundle manifest is missing the 'supplementary_offer_create_target' record."
);

test.describe("Create Supplementary Offer from an Accepted Base Offer (Slice 6O.1)", () => {
  test("creates a separate DRAFT offer series linked to the Base Offer, not a revision of it", async ({ page }) => {
    await login(page, "sales1");

    await page.goto(`/commercial-offers/${record.commercial_offer.public_id}`);
    await expect(page.getByText(record.commercial_offer.offer_code).first()).toBeVisible();
    await expect(page.getByText("Base Offer", { exact: true }).first()).toBeVisible();

    await page.getByRole("tab", { name: "Traceability" }).click();
    await expect(page.getByRole("heading", { name: "Related Commercial Offers", exact: true })).toBeVisible();
    await expect(
      page.getByText("No Supplementary Offer or Change Quotation has been created from this Commercial Offer yet.")
    ).toBeVisible();

    await page.getByRole("link", { name: "Create Supplementary Offer" }).click();
    await expect(page).toHaveURL(/\/related-offers\/new\?purpose=SUPPLEMENTARY/);
    await expect(page.getByRole("heading", { name: "Create Supplementary Offer" })).toBeVisible();
    await expect(page.getByText(record.commercial_offer.offer_code).first()).toBeVisible();

    await page.getByLabel(/Request \/ change summary/).fill("Customer requested one additional crane for the same site.");
    await page.getByLabel("Customer request reference").fill("CUST-REQ-E2E-001");

    // TB-1 finding TB1-801: a refusal keeps the page and says what to correct. An amount written the Indian way is
    // refused before sending, naming the field.
    const createButton = page.getByRole("button", { name: "Create Supplementary Offer" });
    await page.getByLabel(/Offer value/).fill("1,00,000");
    await createButton.click();
    await expect(page.getByText("Offer value must be a number.")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Create Supplementary Offer" })).toBeVisible();

    // The server's own list of field errors (FastAPI's answer to a refused field) is shown as a sentence; before the
    // fix React replaced the whole page with its error screen.
    await page.getByLabel(/Offer value/).fill("100000");
    await page.route(
      "**/api/commercial-offers/*/related-offers",
      (route) =>
        route.request().method() === "POST"
          ? route.fulfill({
              status: 422,
              json: { detail: [{ type: "decimal_parsing", loc: ["body", "offer_value"], msg: "Input should be a valid decimal" }] },
            })
          : route.fallback()
    );
    await createButton.click();
    await expect(page.getByText("Check the values entered: one of them is not accepted.")).toBeVisible();
    await expect(page.getByText("Unexpected Application Error!")).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Create Supplementary Offer" })).toBeVisible();
    await page.unrouteAll();

    await createButton.click();
    await expect(page.getByRole("heading", { name: "Supplementary Offer created" })).toBeVisible();

    const openLink = page.getByRole("link", { name: /^Open CO-/ });
    await expect(openLink).toBeVisible();
    await openLink.click();

    await expect(page).toHaveURL(/\/commercial-offers\//);
    await expect(page.getByText("Supplementary Offer", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Draft", { exact: true }).first()).toBeVisible();

    await page.getByRole("tab", { name: "Traceability" }).click();
    await expect(page.getByText(record.commercial_offer.offer_code).first()).toBeVisible();
    await expect(page.getByText("Customer requested one additional crane for the same site.")).toBeVisible();

    // Base Offer remains unchanged: reopen it and confirm it is still Base/Accepted and now lists the new related offer.
    await page.getByRole("link", { name: record.commercial_offer.offer_code }).first().click();
    await expect(page).toHaveURL(new RegExp(`/commercial-offers/${record.commercial_offer.public_id}`));
    await expect(page.getByText("Accepted", { exact: true }).first()).toBeVisible();
    await page.getByRole("tab", { name: "Traceability" }).click();
    await expect(page.getByText(/Supplementary Offer/).first()).toBeVisible();
  });
});
