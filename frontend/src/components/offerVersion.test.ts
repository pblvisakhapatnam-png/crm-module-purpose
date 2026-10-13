import { describe, expect, it } from "vitest";

import { offerVersionLabel } from "./offerVersion";

describe("offerVersionLabel", () => {
  it("names the version beside the shared offer code", () => {
    expect(offerVersionLabel("CO-000123", 1)).toBe("CO-000123 v1");
    expect(offerVersionLabel("CO-000123", 2)).toBe("CO-000123 v2");
  });

  it("shows the code alone when the version is not known", () => {
    expect(offerVersionLabel("CO-000123", null)).toBe("CO-000123");
    expect(offerVersionLabel("CO-000123")).toBe("CO-000123");
  });
});
