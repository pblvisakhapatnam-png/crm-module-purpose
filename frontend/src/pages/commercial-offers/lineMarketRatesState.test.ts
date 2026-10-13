import { describe, expect, it } from "vitest";

import {
  basisChoiceText,
  lineBasisHistory,
  nearestPanelIndex,
  quoteCopyChoices,
  quoteCopyPlace,
  ratesForLine,
  wholeOfferRates,
  type BasisChoice,
  type MarketRate,
} from "./lineMarketRatesState";

function rate(overrides: Partial<MarketRate>): MarketRate {
  return {
    public_id: "r",
    line_public_id: "line-1",
    line_number: 1,
    line_status_code: "ACTIVE",
    recorded_for_whole_offer: false,
    quote_copies: [],
    basis_history: [],
    evidence_type: "market_rate",
    source_name: "Sagar Equipment Hire",
    equipment_service_description: "Crane",
    rate_amount: "92000.00",
    currency_code: "INR",
    rate_basis: "per day",
    is_selected_basis: false,
    ...overrides,
  };
}

const PAST: BasisChoice = {
  public_id: "c1",
  pricing_evidence_public_id: "a",
  selection_reason: "Lowest quote.",
  chosen_by_display_name: "Ops One",
  chosen_at: "2026-10-01T04:30:00",
  ended_by_display_name: "Sales One",
  ended_at: "2026-10-02T04:30:00",
  is_current: false,
};

const CURRENT: BasisChoice = {
  public_id: "c2",
  pricing_evidence_public_id: "b",
  selection_reason: "The lowest vendor withdrew.",
  chosen_by_display_name: "Sales One",
  chosen_at: "2026-10-02T04:30:00",
  ended_at: null,
  is_current: true,
};

describe("ratesForLine", () => {
  it("keeps only the line's own rates, the basis rate first, and never a rate for the whole offer", () => {
    const rates = [
      rate({ public_id: "a" }),
      rate({ public_id: "b", is_selected_basis: true }),
      rate({ public_id: "c", line_public_id: "line-2", line_number: 2 }),
      rate({ public_id: "d", line_public_id: null, line_number: null, recorded_for_whole_offer: true }),
    ];
    expect(ratesForLine(rates, "line-1").map((r) => r.public_id)).toEqual(["b", "a"]);
    expect(wholeOfferRates(rates).map((r) => r.public_id)).toEqual(["d"]);
  });
});

describe("basisChoiceText", () => {
  it("shows an earlier choice as past, with when it ended, who chose it and why", () => {
    const text = basisChoiceText(PAST);
    expect(text.startsWith("Was the basis until 02 Oct 2026")).toBe(true);
    expect(text).toContain("chosen by Ops One on 01 Oct 2026");
    expect(text.endsWith(": Lowest quote.")).toBe(true);
  });

  it("shows the current choice as current, and says when it was carried over from an earlier version", () => {
    expect(basisChoiceText(CURRENT).startsWith("The basis since 02 Oct 2026")).toBe(true);
    expect(basisChoiceText({ ...CURRENT, carried_over_from_version_number: 1 })).toContain("(carried over from version 1)");
  });
});

describe("lineBasisHistory", () => {
  it("lists every choice on the line, newest first, each with the rate it chose", () => {
    const history = lineBasisHistory([
      rate({ public_id: "a", basis_history: [PAST] }),
      rate({ public_id: "b", basis_history: [CURRENT], is_selected_basis: true }),
    ]);
    expect(history.map((entry) => [entry.rate.public_id, entry.choice.public_id])).toEqual([
      ["b", "c2"],
      ["a", "c1"],
    ]);
  });
});

describe("nearestPanelIndex", () => {
  const panel = (top: number, bottom: number) => ({ top, bottom });

  it("goes to the first panel whose start is on screen, not the tail of the one above", () => {
    expect(nearestPanelIndex([panel(-900, -500), panel(-100, 200), panel(600, 900)], 800)).toBe(2);
    expect(nearestPanelIndex([panel(-900, -500), panel(700, 1200)], 800)).toBe(1);
  });

  it("goes to the top of the panel the screen is inside when no panel starts on screen", () => {
    expect(nearestPanelIndex([panel(-900, -500), panel(-100, 1200), panel(1500, 1900)], 800)).toBe(1);
  });

  it("goes to the nearest panel above or below when none is on screen", () => {
    expect(nearestPanelIndex([panel(-900, -50), panel(1500, 1800)], 800)).toBe(0);
    expect(nearestPanelIndex([panel(-900, -600), panel(850, 1200)], 800)).toBe(1);
  });

  it("says when there is no panel to go to", () => {
    expect(nearestPanelIndex([], 800)).toBe(-1);
  });
});

describe("quoteCopyPlace", () => {
  const copy = {
    document_public_id: "d",
    file_name: "quote.png",
    attached_to_rate_public_id: "a",
    attached_to_line_number: 1,
    attached_to_offer_version_number: 1,
    attached_here: false,
  };

  it("says nothing for a copy attached to the rate itself", () => {
    expect(quoteCopyPlace({ ...copy, attached_here: true }, 1)).toBe("");
  });

  it("names the line, and the version when the copy is on an earlier one", () => {
    expect(quoteCopyPlace(copy, 1)).toBe("Attached to line 1's rate");
    expect(quoteCopyPlace(copy, 2)).toBe("Attached to line 1's rate on version 1");
  });
});

describe("quoteCopyChoices", () => {
  it("offers the line rates that have a quote, by line, and never a rate for the whole offer", () => {
    const quote = [
      {
        document_public_id: "d",
        file_name: "quote.png",
        attached_to_rate_public_id: "a",
        attached_to_line_number: 1,
        attached_to_offer_version_number: 1,
        attached_here: true,
      },
    ];
    const choices = quoteCopyChoices([
      rate({ public_id: "b", line_number: 2, line_public_id: "line-2", quote_copies: quote }),
      rate({ public_id: "a", quote_copies: quote }),
      rate({ public_id: "c", line_number: 3, line_public_id: "line-3" }),
      rate({ public_id: "d", recorded_for_whole_offer: true, line_public_id: null, line_number: null, quote_copies: quote }),
    ]);
    expect(choices.map((choice) => choice.value)).toEqual(["a", "b"]);
    expect(choices[0].label.startsWith("Line 1: Sagar Equipment Hire - ")).toBe(true);
  });
});
