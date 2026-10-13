import { describe, expect, it } from "vitest";

import { leadCanBeChanged } from "./leadStatus";

describe("leadCanBeChanged", () => {
  it("lets every status before conversion be changed", () => {
    for (const status of ["NEW", "CONTACTED", "REVIEW_PENDING", "UNDER_REVIEW", "QUALIFICATION_READY", "QUALIFIED", "UNQUALIFIED", "CLOSED"]) {
      expect(leadCanBeChanged(status)).toBe(true);
    }
  });

  it("never lets a converted Lead be changed", () => {
    expect(leadCanBeChanged("CONVERTED")).toBe(false);
  });
});
