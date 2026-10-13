// The "Back to ..." link guard (Slice 6A; TB-1 TB1-805). A kept value is also resolved the way a browser
// resolves a link on a page of the site - Node's URL is the WHATWG parser browsers implement - so a value
// the guard keeps cannot lead off the site however the browser reads it.

import { readdirSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { afterEach, describe, expect, it, vi } from "vitest";

import { readSafeReturnTarget, safeReturnHref } from "./returnTarget";

const ORIGIN = "https://crm.example.test";
const PAGE = `${ORIGIN}/accounts/3f0c1d2e-0000-4000-8000-000000000001`;

function leadsTo(href: string): string {
  return new URL(href, PAGE).origin;
}

describe("the return-link guard", () => {
  it.each([
    "/opportunities/9a1b2c3d-0000-4000-8000-000000000002",
    "/work-orders/abc?view=lines&returnTo=%2Fwork-orders#lines",
    "/",
    "/./accounts",
  ])("keeps a page of this site: %s", (value) => {
    expect(safeReturnHref(value, ORIGIN)).toBe(value);
    expect(leadsTo(value)).toBe(ORIGIN);
  });

  it.each([
    ["protocol-relative", "//evil.example"],
    ["protocol-relative, naming this site", "//crm.example.test/accounts"],
    ["protocol-relative, naming this site with its default port", "//crm.example.test:443/accounts"],
    ["absolute", "https://evil.example"],
    ["absolute, naming this site", `${ORIGIN}/accounts`],
    ["slash then backslash", "/\\evil.example/x"],
    ["slash, tab, slash", "/\t/evil.example/x"],
    ["slash, line feed, slash", "/\n/evil.example/x"],
    ["slash, carriage return, slash", "/\r/evil.example/x"],
    ["backslashes only", "\\\\evil.example"],
    ["a script", "javascript:alert(1)"],
    ["no leading slash", "accounts"],
    ["empty", ""],
  ])("refuses a value that is not a page of this site (%s)", (_, value) => {
    expect(safeReturnHref(value, ORIGIN)).toBeNull();
  });

  it("refuses the values a browser reads as another site, which the old copies kept", () => {
    // The old test: starts with "/", not "//", and no "://". Both pass it and both leave the site.
    for (const value of ["/\\evil.example/x", "/\t/evil.example/x"]) {
      const oldCopyKept = value.startsWith("/") && !value.startsWith("//") && !value.includes("://");
      expect(oldCopyKept).toBe(true);
      expect(leadsTo(value)).toBe("https://evil.example");
      expect(safeReturnHref(value, ORIGIN)).toBeNull();
    }
  });

  it("refuses a missing value", () => {
    expect(safeReturnHref(null, ORIGIN)).toBeNull();
    expect(safeReturnHref(undefined, ORIGIN)).toBeNull();
  });
});

describe("a page's Back link", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function onPageWith(search: string) {
    vi.stubGlobal("window", { location: { search, origin: ORIGIN } });
  }

  it("follows a safe returnTo with its label, trimmed and cut to 60 characters", () => {
    onPageWith(`?returnTo=${encodeURIComponent("/opportunities/9a1b")}&returnLabel=${encodeURIComponent(`  ${"x".repeat(70)}  `)}`);
    expect(readSafeReturnTarget("/accounts", "Back to Accounts")).toEqual({ href: "/opportunities/9a1b", label: "x".repeat(60) });
  });

  it("keeps the page's own label when the link gives none", () => {
    onPageWith(`?returnTo=${encodeURIComponent("/opportunities/9a1b")}&returnLabel=${encodeURIComponent("   ")}`);
    expect(readSafeReturnTarget("/accounts", "Back to Accounts")).toEqual({ href: "/opportunities/9a1b", label: "Back to Accounts" });
  });

  it("ignores the link's label too when its returnTo leads off the site (TB1-805's phishing link)", () => {
    onPageWith("?returnTo=%2F%5Cevil.example%2Fsign-in&returnLabel=Sign%20in%20again");
    expect(readSafeReturnTarget("/accounts", "Back to Accounts")).toEqual({ href: "/accounts", label: "Back to Accounts" });

    onPageWith("?returnTo=%2F%09%2Fevil.example%2Fsign-in&returnLabel=Sign%20in%20again");
    expect(readSafeReturnTarget("/accounts", "Back to Accounts")).toEqual({ href: "/accounts", label: "Back to Accounts" });
  });

  it("ignores a protocol-relative returnTo and its label even when it names this site (Slice 6A)", () => {
    // Both would lead to this site; the rule refuses the form, not only the destination.
    expect(leadsTo("//crm.example.test/accounts")).toBe(ORIGIN);
    expect(leadsTo("//crm.example.test:443/accounts")).toBe(ORIGIN);
    for (const value of ["//crm.example.test/accounts", "//crm.example.test:443/accounts"]) {
      onPageWith(`?returnTo=${encodeURIComponent(value)}&returnLabel=${encodeURIComponent("Chosen by the link")}`);
      expect(readSafeReturnTarget("/opportunities", "Back to Opportunities")).toEqual({ href: "/opportunities", label: "Back to Opportunities" });
    }
  });

  it("uses the page's default when there is no returnTo", () => {
    onPageWith("");
    expect(readSafeReturnTarget("/work-orders", "Back to Work Orders")).toEqual({ href: "/work-orders", label: "Back to Work Orders" });
  });
});

describe("one guard, not eight copies", () => {
  const SRC = fileURLToPath(new URL("..", import.meta.url));
  const sources = (readdirSync(SRC, { recursive: true }) as string[])
    .map((path) => path.replace(/\\/g, "/"))
    .filter((path) => /\.tsx?$/.test(path) && !path.endsWith(".test.ts") && path !== "components/returnTarget.ts");

  it("no page reads returnTo for itself", () => {
    const readers = sources.filter((path) => readFileSync(`${SRC}${path}`, "utf-8").includes('get("returnTo")'));
    expect(readers).toEqual([]);
  });

  it.each([
    "pages/accounts/AccountDetailPage.tsx",
    "pages/opportunities/OpportunityDetailPage.tsx",
    "pages/commercial-offers/CommercialOfferDetailPage.tsx",
    "pages/work-orders/WorkOrderDetailPage.tsx",
    "pages/work-orders/NewWorkOrderAmendmentPage.tsx",
    "pages/work-orders/WorkOrderAmendmentDetailPage.tsx",
    "pages/EventsPage.tsx",
    "pages/resource-requirements/pageSession.ts",
  ])("%s takes the shared guard", (path) => {
    expect(readFileSync(`${SRC}${path}`, "utf-8")).toMatch(/readSafeReturnTarget[^;]*from "(\.\.\/)+components\/returnTarget"/);
  });
});
