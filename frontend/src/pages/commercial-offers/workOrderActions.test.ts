import { describe, expect, it } from "vitest";

import { createWorkOrderLabel, existingWorkOrdersNote } from "./workOrderActions";

// TB-1 CS-04 part 1, review round 8: with a Work Order holding part of an offer, the page offers "Create another Work
// Order" and the note under the existing Work Orders agrees with it.

describe("the offer page's Work Order actions", () => {
  it("offers the first Work Order, then another beside those that exist", () => {
    expect(createWorkOrderLabel(0)).toBe("Create Work Order");
    expect(createWorkOrderLabel(1)).toBe("Create another Work Order");
    expect(createWorkOrderLabel(3)).toBe("Create another Work Order");
  });

  it("points to Create another Work Order when an offer with a part on a Work Order has more left", () => {
    const note = existingWorkOrdersNote(true);
    expect(note).toContain(createWorkOrderLabel(1));
    expect(note).toContain("only what is not on a Work Order yet");
    expect(note).not.toMatch(/not offered/);
  });

  it("states the rule without pointing to a link the page does not show", () => {
    const note = existingWorkOrdersNote(false);
    expect(note).toContain("only what is not on a Work Order yet");
    expect(note).not.toContain("Create another Work Order");
    expect(note).not.toMatch(/not offered/);
  });
});
