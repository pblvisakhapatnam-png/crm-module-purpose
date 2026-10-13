import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

const manifest = loadManifest();
const record = manifest.records["terminal_guard"];

test.skip(!record, "core-regression-bundle manifest is missing the 'terminal_guard' record.");

test.describe("Commercial Offer generic terminal-status UI guard (Slice 6M.1 and Slice 9F)", () => {
  test("Accepted/Rejected status and content stay locked while outcome notes remain editable", async ({ page }) => {
    await login(page, "sales1");

    await page.goto(`/commercial-offers/${record.commercial_offer.public_id}`);
    await expect(page.getByText(record.commercial_offer.offer_code).first()).toBeVisible();
    await expect(page.getByText("Rejected", { exact: true }).first()).toBeVisible();

    await page.getByRole("button", { name: "Edit Commercial Offer / Status" }).click();

    const statusSelect = page.getByLabel("Offer status");
    await expect(statusSelect).toBeVisible();

    // While terminal, the form shows exactly one read-only option carrying the current
    // status (so the value stays visible) and none of the normally-selectable targets
    // (Draft/Ready for Review/Withdrawn/Closed) -- Accepted/Rejected were never among
    // those selectable targets even outside the terminal case (Slice 6M.1).
    const optionLabels = await statusSelect.locator("option").allTextContents();
    expect(optionLabels).toHaveLength(1);
    expect(optionLabels[0]).toMatch(/final status, cannot be changed here/);
    for (const selectableStatus of ["Draft", "Ready For Review", "Withdrawn", "Closed"]) {
      expect(optionLabels.some((label) => label.startsWith(selectableStatus))).toBe(false);
    }

    await expect(statusSelect).toBeDisabled();
    await expect(
      page.getByText(/Its status and commercial details are read-only; only its outcome date and outcome remarks may be updated here\./)
    ).toBeVisible();

    // Slice 9F freezes commercial content on every sent/concluded version, while preserving the
    // established backend path for outcome-date/remarks corrections on the current concluded row.
    await expect(page.getByLabel("Remarks / requirement notes")).toBeDisabled();
    await expect(page.getByLabel("Outcome date")).toBeEditable();
    const outcomeRemarks = page.getByLabel("Outcome remarks");
    await expect(outcomeRemarks).toBeEditable();
    await outcomeRemarks.fill("Customer rejection outcome confirmed in the conversation log.");
    await page.getByRole("button", { name: "Save Commercial Offer" }).click();
    await expect(page.getByText("Commercial Offer updated successfully.")).toBeVisible();
  });
});
