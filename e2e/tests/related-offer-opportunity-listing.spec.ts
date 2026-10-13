import { Page, test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadRelatedOffersManifest } from "./fixtures/manifest";

const manifest = loadRelatedOffersManifest();
const record = manifest.records["multi_series_target"];

test.skip(!record, "related-offer-regression-bundle manifest is missing the 'multi_series_target' record.");
test.skip((record?.related_offers?.length ?? 0) < 2, "'multi_series_target' record needs both a Supplementary Offer and a Change Quotation.");

// A related offer's default title embeds its Base Offer's code (e.g. "CO-003871 Change
// Quotation"), and the table's "Base Offer" column also repeats that code -- so any text- or
// accessible-name-based row match (substring or anchored) ends up ambiguous across the Base
// row and its related rows for this specific table. This is the documented escape hatch case
// (UI_UX_CARRY_FORWARD / Slice 6O.1 task instructions): a stable semantic selector is not
// available here, so the row carries a data-testid keyed by the offer's own public_id.
function offerRow(page: Page, offerPublicId: string) {
  return page.getByTestId(`commercial-offer-row-${offerPublicId}`);
}

test.describe("Opportunity shows multiple Commercial Offer series (Slice 6O.1)", () => {
  test("Base Offer, Supplementary Offer and Change Quotation each appear as independent series", async ({ page }) => {
    const supplementary = record.related_offers!.find((offer) => offer.offer_purpose === "SUPPLEMENTARY");
    const changeQuotation = record.related_offers!.find((offer) => offer.offer_purpose === "CHANGE_QUOTATION");
    expect(supplementary).toBeTruthy();
    expect(changeQuotation).toBeTruthy();

    await login(page, "sales1");
    await page.goto(`/opportunities/${record.opportunity.public_id}`);

    await expect(page.getByRole("heading", { name: "Commercial Offers" })).toBeVisible();

    const baseRow = offerRow(page, record.commercial_offer.public_id);
    await expect(baseRow).toBeVisible();
    await expect(baseRow.getByText("Base Offer", { exact: true })).toBeVisible();

    const supplementaryRow = offerRow(page, supplementary!.public_id);
    await expect(supplementaryRow).toBeVisible();
    await expect(supplementaryRow.getByText("Supplementary Offer", { exact: true })).toBeVisible();

    const changeQuotationRow = offerRow(page, changeQuotation!.public_id);
    await expect(changeQuotationRow).toBeVisible();
    await expect(changeQuotationRow.getByText("Change Quotation", { exact: true })).toBeVisible();

    // Each series opens independently, and the related offer's own page shows its purpose
    // and Base Offer link rather than presenting itself as a revision of the Base Offer.
    await supplementaryRow.getByRole("link", { name: "Open" }).click();
    await expect(page).toHaveURL(new RegExp(`/commercial-offers/${supplementary!.public_id}`));
    await expect(page.getByText("Supplementary Offer", { exact: true }).first()).toBeVisible();
    await page.getByRole("tab", { name: "Traceability" }).click();
    await expect(page.getByText(record.commercial_offer.offer_code).first()).toBeVisible();

    await page.goto(`/opportunities/${record.opportunity.public_id}`);
    await offerRow(page, changeQuotation!.public_id)
      .getByRole("link", { name: "Open" })
      .click();
    await expect(page).toHaveURL(new RegExp(`/commercial-offers/${changeQuotation!.public_id}`));
    await expect(page.getByText("Change Quotation", { exact: true }).first()).toBeVisible();
  });
});
