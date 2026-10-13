import { test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { loadManifest } from "./fixtures/manifest";

const manifest = loadManifest();
const record = manifest.records["read_only_view"];

test.skip(!record, "core-regression-bundle manifest is missing the 'read_only_view' record.");
test.skip(!record?.work_orders?.length, "'read_only_view' record has no pre-created Work Order.");

test.describe("Management Read Only role sees data but no mutating actions", () => {
  test("can view the seeded Commercial Offer and Work Order with no create/edit controls offered", async ({
    page,
  }) => {
    const workOrder = record.work_orders[0];
    await login(page, "readonly1");

    await page.goto(`/commercial-offers/${record.commercial_offer.public_id}`);
    await expect(page.getByText(record.commercial_offer.offer_code).first()).toBeVisible();
    await expect(page.getByText("Accepted", { exact: true }).first()).toBeVisible();

    // Backend authorization is authoritative; this only checks the UX-level hiding documented
    // in Slice 6O (frontend role-aware hiding is not itself a security control).
    await expect(page.getByRole("button", { name: "Edit Commercial Offer / Status" })).toHaveCount(0);
    // Substring match on purpose: for an absence check, the broader match is the stronger assertion.
    await expect(page.getByRole("link", { name: "Create Work Order" })).toHaveCount(0);

    await page.goto(`/work-orders/${workOrder.public_id}`);
    await expect(page.getByText("Awaiting release to Ops", { exact: true }).first()).toBeVisible();
    await expect(page.getByText(record.commercial_offer.offer_code).first()).toBeVisible();

    // MANAGEMENT_READ_ONLY is in EVENT_VIEW_ROLES, so the provenance event detail should still
    // be visible even though this role cannot create/mutate anything.
    await expect(page.getByText("How this Work Order was created").first()).toBeVisible();

    await page.goto("/work-orders/new");
    await expect(
      page.getByText("Your role can view Work Orders but cannot create one.")
    ).toBeVisible();
  });
});
