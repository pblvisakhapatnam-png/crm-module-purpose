import fs from "node:fs";

export interface SeedAccount {
  public_id: string;
  account_name: string;
}

export interface SeedOpportunity {
  public_id: string;
  opportunity_name: string;
}

export interface SeedOffer {
  public_id: string;
  offer_code: string;
  line_public_id: string;
}

export interface SeedWorkOrder {
  public_id: string;
  work_order_code: string;
  line_public_ids: string[];
}

export interface SeedRelatedOffer {
  public_id: string;
  offer_code: string;
  offer_purpose: string;
  base_offer_public_id: string | null;
  related_work_order_public_id: string | null;
}

export interface SeedAmendment {
  public_id: string;
  amendment_type_code: string;
  amendment_status_code: string;
  amendment_sequence_no: number;
}

export interface SeedRecord {
  account: SeedAccount;
  opportunity: SeedOpportunity;
  commercial_offer: SeedOffer;
  commercial_offer_status: string;
  work_orders: SeedWorkOrder[];
  related_offers?: SeedRelatedOffer[];
  amendments?: SeedAmendment[];
  blocked_reason?: string;
}

export interface SeedLead {
  public_id: string;
  company_name: string;
  lead_status_code: string;
}

export interface DemoMeta {
  track: string;
  fictional_customer: string;
  purpose: string;
  interactive: boolean;
  fallback_of: string | null;
  presenter_role: string;
  presenter_action: string;
  expected_result: string;
}

/**
 * Slice 6P vendor-demo-bundle records are deliberately more permissive than SeedRecord above:
 * the Lead-only Track A records (lead_interactive before conversion) have no commercial_offer
 * at all. A separate, more permissive interface avoids loosening SeedRecord (and therefore
 * every existing spec's type-checking assumptions) just to accommodate this one scenario.
 */
export interface VendorDemoRecord {
  lead?: SeedLead;
  activities?: { public_id: string }[];
  account?: SeedAccount;
  opportunity?: SeedOpportunity;
  commercial_offer?: SeedOffer;
  commercial_offer_status?: string;
  work_orders?: SeedWorkOrder[];
  related_offers?: SeedRelatedOffer[];
  amendments?: SeedAmendment[];
  demo_meta?: DemoMeta;
}

export interface VendorDemoManifest {
  manifest_version: number;
  run_id: string;
  scenario: string;
  created_at: string;
  actor: { public_id: string; username: string };
  records: Record<string, VendorDemoRecord>;
  urls: Record<string, string>;
}

export interface Manifest {
  manifest_version: number;
  run_id: string;
  scenario: string;
  created_at: string;
  actor: { public_id: string; username: string };
  records: Record<string, SeedRecord>;
  urls: Record<string, string>;
}

const SUPPORTED_MANIFEST_VERSION = 1;

/** Reads the manifest written by scripts/run-e2e.ps1 (backend seed --json output). */
export function loadManifest(): Manifest {
  const path = process.env.MANIFEST_PATH;
  if (!path) {
    throw new Error(
      "MANIFEST_PATH environment variable is not set. Run the suite through scripts/run-e2e.ps1, " +
        "which seeds core-regression-bundle and passes the manifest path in."
    );
  }
  if (!fs.existsSync(path)) {
    throw new Error(`MANIFEST_PATH points to a file that does not exist: ${path}`);
  }
  const manifest = JSON.parse(fs.readFileSync(path, "utf-8")) as Manifest;
  if (manifest.manifest_version !== SUPPORTED_MANIFEST_VERSION) {
    throw new Error(
      `Unsupported manifest_version ${manifest.manifest_version}; this suite understands version ${SUPPORTED_MANIFEST_VERSION}.`
    );
  }
  return manifest;
}

/**
 * Reads the separate related-offer-regression-bundle manifest (Slice 6O.1), seeded and
 * written to a second file by scripts/run-e2e.ps1 alongside the core-regression-bundle
 * manifest above. Kept as its own manifest/run id rather than merged into the core bundle,
 * so the two scenario catalogues stay independently seedable/cleanable.
 */
export function loadRelatedOffersManifest(): Manifest {
  const path = process.env.RELATED_OFFERS_MANIFEST_PATH;
  if (!path) {
    throw new Error(
      "RELATED_OFFERS_MANIFEST_PATH environment variable is not set. Run the suite through scripts/run-e2e.ps1, " +
        "which seeds related-offer-regression-bundle and passes the manifest path in."
    );
  }
  if (!fs.existsSync(path)) {
    throw new Error(`RELATED_OFFERS_MANIFEST_PATH points to a file that does not exist: ${path}`);
  }
  const manifest = JSON.parse(fs.readFileSync(path, "utf-8")) as Manifest;
  if (manifest.manifest_version !== SUPPORTED_MANIFEST_VERSION) {
    throw new Error(
      `Unsupported manifest_version ${manifest.manifest_version}; this suite understands version ${SUPPORTED_MANIFEST_VERSION}.`
    );
  }
  return manifest;
}

/**
 * Reads the separate work-order-amendment-regression-bundle manifest (Slice 6O.2), seeded
 * and written to a third file by scripts/run-e2e.ps1 alongside the core-regression-bundle
 * and related-offer-regression-bundle manifests above. Kept as its own manifest/run id for
 * the same reason those two are kept separate: each scenario catalogue stays independently
 * seedable/cleanable and no two Playwright tests mutate records seeded for another spec.
 */
export function loadWorkOrderAmendmentsManifest(): Manifest {
  const path = process.env.WORK_ORDER_AMENDMENTS_MANIFEST_PATH;
  if (!path) {
    throw new Error(
      "WORK_ORDER_AMENDMENTS_MANIFEST_PATH environment variable is not set. Run the suite through " +
        "scripts/run-e2e.ps1, which seeds work-order-amendment-regression-bundle and passes the manifest path in."
    );
  }
  if (!fs.existsSync(path)) {
    throw new Error(`WORK_ORDER_AMENDMENTS_MANIFEST_PATH points to a file that does not exist: ${path}`);
  }
  const manifest = JSON.parse(fs.readFileSync(path, "utf-8")) as Manifest;
  if (manifest.manifest_version !== SUPPORTED_MANIFEST_VERSION) {
    throw new Error(
      `Unsupported manifest_version ${manifest.manifest_version}; this suite understands version ${SUPPORTED_MANIFEST_VERSION}.`
    );
  }
  return manifest;
}

/**
 * Reads the Slice 6P vendor-demo-bundle manifest, written by scripts/vendor-demo.ps1 to
 * e2e/.manifest/vendor-demo.json. Unlike the three loaders above, only a demo-preflight-only run
 * (scripts/vendor-demo.ps1 preflight) sets this env var; the ordinary full regression run
 * (scripts/run-e2e.ps1) does not seed vendor-demo-bundle and never sets
 * VENDOR_DEMO_MANIFEST_PATH, so demo-preflight.spec.ts guards its own call.
 */
export function loadVendorDemoManifest(): VendorDemoManifest {
  const path = process.env.VENDOR_DEMO_MANIFEST_PATH;
  if (!path) {
    throw new Error(
      "VENDOR_DEMO_MANIFEST_PATH environment variable is not set. Run the demo-preflight suite through " +
        "scripts/vendor-demo.ps1 preflight, which seeds vendor-demo-bundle and passes the manifest path in."
    );
  }
  if (!fs.existsSync(path)) {
    throw new Error(`VENDOR_DEMO_MANIFEST_PATH points to a file that does not exist: ${path}`);
  }
  const manifest = JSON.parse(fs.readFileSync(path, "utf-8")) as VendorDemoManifest;
  if (manifest.manifest_version !== SUPPORTED_MANIFEST_VERSION) {
    throw new Error(
      `Unsupported manifest_version ${manifest.manifest_version}; this suite understands version ${SUPPORTED_MANIFEST_VERSION}.`
    );
  }
  return manifest;
}
