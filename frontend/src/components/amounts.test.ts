import { describe, expect, it } from "vitest";

import { amountProblem } from "./amounts";

// The cases for amounts that must be greater than 0 are in pages/work-orders/workOrderBillingTermsState.test.ts, where
// the check began. These are the amounts the server accepts at 0: an offer value, an amendment line's rate (TB-1
// finding TB1-801).

describe("amountProblem, for an amount that may be 0", () => {
  const offerValue = (value: string) => amountProblem("Offer value", value, 16, true);

  it("accepts 0 and what the server accepts", () => {
    for (const accepted of ["", "0", "0.00", "100000", "100000.50", "9999999999999999.99", "1e3"]) {
      expect(offerValue(accepted), accepted).toBeNull();
    }
  });

  it("refuses, naming the field, what the server would refuse", () => {
    expect(offerValue("1,00,000")).toBe("Offer value must be a number.");
    expect(offerValue("Rs 5000")).toBe("Offer value must be a number.");
    expect(offerValue("-1")).toBe("Offer value must be 0 or more.");
    expect(offerValue("1.234")).toBe("Offer value can have at most 2 decimal places.");
    expect(offerValue("10000000000000000")).toBe("Offer value is larger than can be recorded.");
  });

  it("still refuses 0 where it is not allowed", () => {
    expect(amountProblem("Proposed quantity", "0", 16)).toBe("Proposed quantity must be greater than 0.");
    expect(amountProblem("Proposed quantity", "0.5", 16)).toBeNull();
  });
});
