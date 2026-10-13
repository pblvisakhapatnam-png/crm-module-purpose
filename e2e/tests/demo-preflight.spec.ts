import { Page, test, expect } from "@playwright/test";
import { login } from "./fixtures/auth";
import { VendorDemoManifest, loadVendorDemoManifest } from "./fixtures/manifest";

/**
 * Slice 6P non-destructive demo-preflight suite ("@demo-preflight" in every test title so
 * scripts/vendor-demo.ps1 preflight can run only this file via `--grep "@demo-preflight"`).
 *
 * This is a readiness check, not another business-rule regression suite: it only confirms that
 * the pages a presenter is about to show actually load and render the expected guidance. It
 * never performs the live-mutation action a presenter will perform during the walkthorugh
 * (qualifying/converting the Lead, marking the offer Submitted, creating the Work Order shell,
 * validating the amendment) - those stay untouched for the real demonstration. Where a check
 * needs to see a "completed" state (e.g. an amendment's original/proposed value rendering, or
 * an already-linked Work Order), it uses the bundle's own fallback record instead of consuming
 * the interactive one.
 *
 * VENDOR_DEMO_MANIFEST_PATH is only ever set by scripts/vendor-demo.ps1 preflight, never by the
 * ordinary full regression run (scripts/run-e2e.ps1). Playwright still imports every spec file
 * in testDir to collect tests regardless of --grep, so this file must not throw at module scope
 * the way the other spec files' loaders do -- doing so would abort collection (and therefore the
 * entire suite) for every other spec whenever this env var is unset. Only the "env var unset"
 * case degrades to skipping this whole file's tests; if the env var IS set but points to a
 * missing file or malformed manifest, loadVendorDemoManifest() still throws for real, so a
 * genuine bug surfaces loudly instead of silently reporting "0 tests, all skipped".
 */

const manifest: VendorDemoManifest | null = process.env.VENDOR_DEMO_MANIFEST_PATH
  ? loadVendorDemoManifest()
  : null;

function record(key: string) {
  return manifest?.records[key];
}

// React Router's error screen, which a crashed page shows since TE-2A. The two texts this checked
// before were Next.js's, which no longer appear (TB-1 REP-1, corrected 8 October 2026).
async function assertNoFatalError(page: Page): Promise<void> {
  await expect(page.getByText("Unexpected Application Error!")).toHaveCount(0);
}

test.describe("Slice 6P vendor demo preflight @demo-preflight", () => {
  test.skip(
    !manifest,
    "VENDOR_DEMO_MANIFEST_PATH is not set -- run this suite through scripts/vendor-demo.ps1 preflight."
  );

  test("login page responds and both an authorized and a read-only prototype user can log in @demo-preflight", async ({
    page,
  }) => {
    await page.goto("/login");
    await expect(page.getByLabel("Username")).toBeVisible();
    await assertNoFatalError(page);

    await login(page, "sales1");
    await login(page, "readonly1");
  });

  test("primary Lead record loads without a fatal error @demo-preflight", async ({ page }) => {
    const lead = record("lead_interactive")?.lead;
    test.skip(!lead, "vendor-demo-bundle manifest is missing the 'lead_interactive' record.");

    await login(page, "sales1");
    await page.goto(`/leads/${lead!.public_id}`);
    await expect(page.getByText(lead!.company_name).first()).toBeVisible();
    await assertNoFatalError(page);
  });

  test("Base Offer prepared for submission loads with lines, pricing and T&C readiness @demo-preflight", async ({
    page,
  }) => {
    const offer = record("offer_ready_to_submit")?.commercial_offer;
    test.skip(!offer, "vendor-demo-bundle manifest is missing the 'offer_ready_to_submit' record.");

    await login(page, "sales1");
    await page.goto(`/commercial-offers/${offer!.public_id}`);
    await expect(page.getByText(offer!.offer_code).first()).toBeVisible();
    await assertNoFatalError(page);
  });

  test("accepted offer with no Work Order shows the correct pre-handoff guidance @demo-preflight", async ({
    page,
  }) => {
    const record_ = record("offer_accepted_no_wo");
    test.skip(!record_, "vendor-demo-bundle manifest is missing the 'offer_accepted_no_wo' record.");

    await login(page, "sales1");
    await page.goto(`/commercial-offers/${record_!.commercial_offer!.public_id}`);
    await page.getByRole("tab", { name: "Submission" }).click();
    await expect(
      page.getByText("No Work Order has been created yet from this Commercial Offer.", { exact: false })
    ).toBeVisible();
    await assertNoFatalError(page);
  });

  test("existing Work Order (Track C fallback) shows source-line traceability @demo-preflight", async ({ page }) => {
    const record_ = record("offer_accepted_with_wo");
    const workOrder = record_?.work_orders?.[0];
    test.skip(!workOrder, "vendor-demo-bundle manifest is missing the 'offer_accepted_with_wo' record's Work Order.");

    await login(page, "sales1");
    await page.goto(`/work-orders/${workOrder!.public_id}`);
    await expect(page.getByText("Awaiting release to Ops", { exact: true }).first()).toBeVisible();
    const traceabilityRow = page.getByRole("row", {
      name: new RegExp(record_!.commercial_offer!.line_public_id),
    });
    await expect(traceabilityRow).toBeVisible();
    await assertNoFatalError(page);
  });

  test("Supplementary Offer and Change Quotation relationships render on the Base Offer @demo-preflight", async ({
    page,
  }) => {
    const record_ = record("related_offers_chain");
    const baseOffer = record_?.commercial_offer;
    test.skip(!baseOffer, "vendor-demo-bundle manifest is missing the 'related_offers_chain' record.");

    await login(page, "sales1");
    // The Base Offer's own "Related Commercial Offers" section (Traceability tab) lists every
    // related offer regardless of whether it is linked to a Work Order (the Supplementary
    // Offer here is not).
    await page.goto(`/commercial-offers/${baseOffer!.public_id}`);
    await page.getByRole("tab", { name: "Traceability" }).click();
    for (const related of record_!.related_offers ?? []) {
      await expect(page.getByText(related.offer_code).first()).toBeVisible();
    }
    await assertNoFatalError(page);
  });

  test("Work Order Amendment detail renders original and proposed values (Track F fallback) @demo-preflight", async ({
    page,
  }) => {
    const record_ = record("amendment_commercial_fallback_validated");
    const workOrder = record_?.work_orders?.[0];
    const amendment = record_?.amendments?.[0];
    test.skip(
      !workOrder || !amendment,
      "vendor-demo-bundle manifest is missing the 'amendment_commercial_fallback_validated' record."
    );

    await login(page, "sales1");
    await page.goto(`/work-orders/${workOrder!.public_id}/amendments/${amendment!.public_id}`);
    await expect(page.getByText("Original (source line snapshot)").first()).toBeVisible();
    await expect(page.getByText("Proposed", { exact: true }).first()).toBeVisible();
    await expect(page.getByText("It has not been applied to the Work Order.", { exact: false })).toBeVisible();
    await assertNoFatalError(page);
  });

  test("Management Read Only role sees data but no mutation controls @demo-preflight", async ({ page }) => {
    const record_ = record("amendment_commercial_fallback_validated");
    const workOrder = record_?.work_orders?.[0];
    test.skip(!workOrder, "vendor-demo-bundle manifest is missing the 'amendment_commercial_fallback_validated' record.");

    await login(page, "readonly1");
    await page.goto(`/work-orders/${workOrder!.public_id}`);
    await expect(page.getByRole("link", { name: "Record Work Order Amendment" })).toHaveCount(0);
    await assertNoFatalError(page);
  });

  test("every direct link in the vendor-demo-bundle manifest resolves without a fatal error @demo-preflight", async ({
    page,
  }) => {
    // Every URL was already exercised individually via more specific assertions above; this
    // pass only needs to confirm none of the (deduplicated) paths render a fatal error page.
    // Generous timeout because the bundle produces dozens of distinct pages to visit in one test.
    test.setTimeout(180_000);
    await login(page, "sales1");
    const paths = [...new Set(Object.values(manifest!.urls).map((url) => new URL(url).pathname))];
    test.skip(paths.length === 0, "vendor-demo-bundle manifest has no urls.");

    for (const path of paths) {
      await page.goto(path, { waitUntil: "domcontentloaded", timeout: 45_000 });
      await assertNoFatalError(page);
    }
  });
});
