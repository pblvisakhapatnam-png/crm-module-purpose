import { describe, expect, it } from "vitest";

import {
  describeHoldings,
  formatHundredths,
  hundredthsLeft,
  LineHandoff,
  quantityProblem,
  startingChoice,
  toHundredths,
} from "./handoffQuantities";

// TB-1 CS-04 part 1: the Create Work Order page offers what the server says is left of each offer line (the lifecycle
// view's `line_handoff`, counted in one statement) and compares what is typed in exact hundredths.

const entry = (lineId: string, quantity: string, left: string, workOrders: [string, string][] = []): LineHandoff => ({
  offer_line_public_id: lineId,
  line_number: 1,
  quantity,
  quantity_on_work_orders: "0",
  quantity_left: left,
  work_orders: workOrders.map(([code, held]) => ({ work_order_public_id: `${code}-id`, work_order_code: code, quantity: held })),
});

describe("toHundredths and formatHundredths", () => {
  it("reads a quantity as whole hundredths, exactly", () => {
    expect(toHundredths("10.00")).toBe(BigInt(1000));
    expect(toHundredths("0.01")).toBe(BigInt(1));
    expect(toHundredths("1e2")).toBe(BigInt(10000));
    expect(toHundredths("9999999999999999.99")).toBe(BigInt("999999999999999999"));
  });

  it("refuses what is not a quantity with at most two decimals", () => {
    for (const value of ["1.234", "abc", "", "-1", "1.2.3"]) expect(toHundredths(value)).toBeNull();
  });

  it("writes hundredths back as the plain number", () => {
    expect(formatHundredths(BigInt(1))).toBe("0.01");
    expect(formatHundredths(BigInt(150))).toBe("1.5");
    expect(formatHundredths(BigInt(105))).toBe("1.05");
    expect(formatHundredths(BigInt(1000))).toBe("10");
    expect(formatHundredths(BigInt(0))).toBe("0");
  });
});

describe("what is left, as the server counts it", () => {
  it("takes the server's remainder whole, above the integers a JavaScript number holds exactly", () => {
    const big = entry("a", "9007199254740992.00", "9007199254740991.99", [["WO-1", "0.01"]]);
    expect(formatHundredths(hundredthsLeft(big))).toBe("9007199254740991.99");
    expect(Number("9007199254740991.99")).toBe(9007199254740992); // what a number would have made of it
    expect(hundredthsLeft(undefined)).toBe(BigInt(0));
  });

  it("names the Work Orders holding a line", () => {
    expect(describeHoldings(entry("a", "10", "0", [["WO-1", "6.00"], ["WO-2", "4.00"]]))).toBe("WO-1 (6), WO-2 (4)");
    expect(describeHoldings(undefined)).toBe("");
  });
});

describe("startingChoice", () => {
  it("ticks every active line with something left, for all that is left, and no line in full", () => {
    const choice = startingChoice(
      ["a", "b", "c", "d"],
      [entry("a", "10", "4.50", [["WO-1", "5.50"]]), entry("b", "1", "0.00", [["WO-1", "1.00"]]), entry("c", "3", "3.00")],
    );
    expect(choice.selected).toEqual(["a", "c"]); // "d" has no entry: the server did not count it, so it is not offered
    expect(choice.quantities).toEqual({ a: "4.5", c: "3" });
  });
});

describe("quantityProblem", () => {
  const big = entry("a", "9007199254740992.00", "9007199254740991.99", [["WO-1", "0.01"]]);

  it("allows up to what is left, to the hundredth", () => {
    expect(quantityProblem(1, "9007199254740991.99", big)).toBeNull();
    expect(quantityProblem(1, "9007199254740992", big)).toBe("Line 1 has 9007199254740991.99 left to hand off.");
    expect(quantityProblem(1, "0.01", entry("a", "1", "0.01"))).toBeNull();
    expect(quantityProblem(1, "0.02", entry("a", "1", "0.01"))).toBe("Line 1 has 0.01 left to hand off.");
  });

  it("refuses an empty, zero, over-precise or over-long quantity, as the server would", () => {
    const line = entry("a", "10", "10.00");
    expect(quantityProblem(2, "", line)).toBe("Line 2's quantity is required.");
    expect(quantityProblem(2, "0", line)).toBe("Line 2's quantity must be greater than 0.");
    expect(quantityProblem(2, "1.005", line)).toBe("Line 2's quantity can have at most 2 decimal places.");
    expect(quantityProblem(2, "12345678901234567", line)).toBe("Line 2's quantity is larger than can be recorded.");
  });
});
