// Slice 7D Part 3 - the rules the contract-period screen and the "apply to other lines" picker
// decide for themselves. The backend owns every refusal; these decide what the screen offers.
//
// The frontend has no component-test capability yet (docs/agent/DEFERRED_REQUIREMENTS.md), so the
// rules are pure and tested here, and the wiring is covered by the diff and the owner's screen check.

import { describe, expect, it } from "vitest";

import { periodLabel, type LineBillingTerms } from "./workOrderBillingTermsState";
import {
  CONTRACT_END_FIXED_DATE,
  CONTRACT_END_UNTIL_WORK_COMPLETE,
  confirmationText,
  contractPeriodPayload,
  copyButtonLabel,
  copyHadFailures,
  copyResultText,
  copyTargetRows,
  dayAfter,
  defaultExtensionStart,
  EXTENSION_ORDER_WARNING_DAYS,
  endDateLockedByExtensions,
  existingTermsSummary,
  extensionOrderDateWarning,
  extensionSummary,
  gapBeforeStart,
  gapConfirmationText,
  gapText,
  indiaToday,
  latestExtension,
  removeExtensionConfirmationText,
  restoredEndText,
  formAfterEndBasisChange,
  formFromContractPeriod,
  initialCopySelection,
  lineDatesText,
  missingContractDatesText,
  rowsNeedingConfirmation,
  toggleCopySelection,
  type ContractExtension,
  type ContractPeriod,
  type CopyResult,
  type CopyTargetRow,
} from "./workOrderContractPeriodState";

const LINES = [
  { public_id: "line-1", line_number: 1, scope_description: "Crane hire" },
  { public_id: "line-2", line_number: 2, scope_description: "Overtime hours" },
  { public_id: "line-3", line_number: 3, scope_description: "Standby crane" },
];

function terms(publicId: string, periods: Partial<LineBillingTerms["periods"][number]>[]): LineBillingTerms {
  return {
    work_order_line_public_id: publicId,
    line_number: 1,
    quoted_uom: "job",
    quoted_rate_amount: null,
    current_period_number: periods.length ? 1 : null,
    periods: periods.map((period, index) => ({
      period_number: index + 1,
      billing_uom_code: null,
      normal_rate_amount: null,
      ...period,
    })) as LineBillingTerms["periods"],
    terms_complete: periods.length > 0,
    line_missing_items: [],
  };
}

function period(overrides: Partial<ContractPeriod> = {}): ContractPeriod {
  return {
    work_order_public_id: "wo-1",
    period_public_id: "cp-1",
    period_version: 1,
    contract_start_date: "2027-01-01",
    contract_end_basis_code: CONTRACT_END_FIXED_DATE,
    contract_end_date: "2027-03-31",
    contract_notes: null,
    contract_state_code: "ACTIVE",
    contract_state_label: "Active, ends in 12 days, on 31 March 2027",
    days_until_start: null,
    days_until_end: 12,
    needs_firm_end_date: false,
    is_complete: true,
    missing_items: [],
    extensions: [],
    gaps: [],
    updated_by: null,
    updated_by_display_name: null,
    updated_at: null,
    ...overrides,
  };
}

function extensionRecord(overrides: Partial<ContractExtension> = {}): ContractExtension {
  return {
    extension_public_id: "ext-1",
    extension_sequence_no: 1,
    previous_end_basis_code: CONTRACT_END_FIXED_DATE,
    previous_end_date: "2027-03-31",
    new_end_date: "2027-06-30",
    extension_start_date: "2027-04-01",
    customer_reference: "EXT/1",
    received_date: "2027-03-01",
    extension_notes: null,
    created_by: null,
    created_by_display_name: "Sales User 1",
    created_at: "2027-03-01T10:00:00Z",
    ...overrides,
  };
}

describe("an extension's own start date, and the gap a later one leaves (22 September 2026)", () => {
  it("offers the day after a fixed end, and nothing where there is no fixed end to follow", () => {
    expect(defaultExtensionStart(period())).toBe("2027-04-01");
    expect(defaultExtensionStart(period({ contract_end_date: "2027-12-31" }))).toBe("2028-01-01");
    expect(
      defaultExtensionStart(period({ contract_end_basis_code: CONTRACT_END_UNTIL_WORK_COMPLETE, contract_end_date: null })),
    ).toBe("");
    expect(defaultExtensionStart(null)).toBe("");
  });

  it("counts the day after across a month end and a leap day", () => {
    expect(dayAfter("2028-02-28")).toBe("2028-02-29");
    expect(dayAfter("2028-02-29")).toBe("2028-03-01");
  });

  it("finds no gap when the extension runs straight on, or the date is incomplete", () => {
    expect(gapBeforeStart(period(), "2027-04-01")).toBeNull();
    expect(gapBeforeStart(period(), "")).toBeNull();
    expect(gapBeforeStart(period(), "20270")).toBeNull();
  });

  it("names the days a later start leaves outside the contract, and asks before recording it", () => {
    expect(gapBeforeStart(period(), "2027-04-15")).toEqual({ first: "2027-04-01", last: "2027-04-14" });
    expect(gapConfirmationText(period(), "2027-04-15")).toBe(
      "This extension starts on 15 April 2027, not on 1 April 2027, the day after the contract ends. " +
        "The days from 1 April 2027 to 14 April 2027 will be outside the contract: no log sheet or bill may " +
        "fall on them. Record it anyway?",
    );
  });

  it("lists a gap by its days, and a one-day gap by its day", () => {
    expect(gapText({ first_day: "2027-04-01", last_day: "2027-04-14", extension_sequence_no: 1 })).toBe(
      "No contract runs on 1 April 2027 to 14 April 2027, before extension 1.",
    );
    expect(gapText({ first_day: "2027-04-01", last_day: "2027-04-01", extension_sequence_no: 2 })).toBe(
      "No contract runs on 1 April 2027, before extension 2.",
    );
  });

  it("names the start in the history only when it is not the day after", () => {
    expect(extensionSummary(extensionRecord())).toBe("31 March 2027 to 30 June 2027");
    expect(extensionSummary(extensionRecord({ extension_start_date: "2027-04-15" }))).toBe(
      "31 March 2027 to 30 June 2027, starting 15 April 2027",
    );
  });
});

describe("what the contract period reads as", () => {
  it("names what is still missing", () => {
    expect(missingContractDatesText(null)).toBe("Contract dates not loaded");
    expect(missingContractDatesText(period())).toBe("Contract dates recorded");
    expect(
      missingContractDatesText(period({ is_complete: false, missing_items: ["CONTRACT_START", "CONTRACT_END"] })),
    ).toBe("Missing: contract start date, contract end date");
  });

  it("fills the form from what is recorded, and from nothing when nothing is", () => {
    expect(formFromContractPeriod(period()).contract_end_date).toBe("2027-03-31");
    expect(formFromContractPeriod(null)).toEqual({
      contract_start_date: "",
      contract_end_basis_code: "",
      contract_end_date: "",
      contract_notes: "",
    });
  });

  it("clears a typed end date when the answer becomes until the work is complete", () => {
    // The backend refuses a request holding both, so the form must not be able to send one.
    const form = formFromContractPeriod(period());
    expect(formAfterEndBasisChange(form, CONTRACT_END_UNTIL_WORK_COMPLETE).contract_end_date).toBe("");
    expect(formAfterEndBasisChange(form, "").contract_end_date).toBe("");
    expect(formAfterEndBasisChange(form, CONTRACT_END_FIXED_DATE).contract_end_date).toBe("2027-03-31");
  });

  it("sends no end date unless the answer is a fixed one", () => {
    const form = { ...formFromContractPeriod(period()), contract_end_basis_code: CONTRACT_END_UNTIL_WORK_COMPLETE };
    expect(contractPeriodPayload(form, 1).contract_end_date).toBeNull();
    expect(contractPeriodPayload(form, 1).contract_end_basis_code).toBe(CONTRACT_END_UNTIL_WORK_COMPLETE);
    expect(contractPeriodPayload(formFromContractPeriod(period()), 1).contract_end_date).toBe("2027-03-31");
  });

  it("sends nothing rather than an empty string for a blank field", () => {
    const payload = contractPeriodPayload(formFromContractPeriod(null), null);
    expect(payload).toEqual({
      expected_period_version: null,
      contract_start_date: null,
      contract_end_basis_code: null,
      contract_end_date: null,
      contract_notes: null,
    });
  });
});

describe("how an extension reads in the history", () => {
  function extension(overrides: Partial<ContractExtension> = {}): ContractExtension {
    return {
      extension_public_id: "ext-1",
      extension_sequence_no: 1,
      previous_end_basis_code: CONTRACT_END_FIXED_DATE,
      previous_end_date: "2027-03-31",
      new_end_date: "2027-06-30",
      extension_start_date: "2027-04-01",
      customer_reference: "EXT/1",
      received_date: "2027-03-01",
      extension_notes: null,
      created_by: null,
      created_by_display_name: "Sales User 1",
      created_at: "2027-03-01T10:00:00Z",
      ...overrides,
    };
  }

  it("names both ends of the move", () => {
    expect(extensionSummary(extension())).toBe("31 March 2027 to 30 June 2027");
  });

  it("says what the contract said before when there was no date", () => {
    expect(
      extensionSummary(extension({ previous_end_basis_code: CONTRACT_END_UNTIL_WORK_COMPLETE, previous_end_date: null })),
    ).toBe("Until the work is complete, to 30 June 2027");
    expect(extensionSummary(extension({ previous_end_basis_code: null, previous_end_date: null }))).toBe(
      "No end date recorded, to 30 June 2027",
    );
  });
});

describe("once an extension exists, the end date moves only through extensions (22 September 2026)", () => {
  const first = extensionRecord();
  const second = extensionRecord({
    extension_public_id: "ext-2",
    extension_sequence_no: 2,
    previous_end_date: "2027-06-30",
    new_end_date: "2027-09-30",
    extension_start_date: "2027-07-01",
  });

  it("locks the end date only when an extension has been recorded", () => {
    expect(endDateLockedByExtensions(null)).toBe(false);
    expect(endDateLockedByExtensions(period())).toBe(false);
    expect(endDateLockedByExtensions(period({ extensions: [first] }))).toBe(true);
  });

  it("offers only the most recent extension for removal", () => {
    expect(latestExtension(period())).toBeNull();
    expect(latestExtension(period({ extensions: [first, second] }))?.extension_public_id).toBe("ext-2");
  });

  it("says what the end goes back to, whatever it was before", () => {
    expect(restoredEndText(second)).toBe("30 June 2027");
    expect(restoredEndText(extensionRecord({ previous_end_basis_code: CONTRACT_END_UNTIL_WORK_COMPLETE, previous_end_date: null }))).toBe(
      "until the work is complete",
    );
    expect(restoredEndText(extensionRecord({ previous_end_basis_code: null, previous_end_date: null }))).toBe("not recorded");
  });

  it("asks before removing, naming the move and where the end goes back to", () => {
    expect(removeExtensionConfirmationText(second)).toBe(
      "Remove extension 2 (30 June 2027 to 30 September 2027)? The contract end date goes back to 30 June 2027. " +
        "The removal is kept in the Work Order's audit log.",
    );
  });
});

describe("an extension order dated long ago is warned about, never refused", () => {
  const today = "2026-09-22";

  it("says nothing within 15 days, or for a date still ahead", () => {
    expect(EXTENSION_ORDER_WARNING_DAYS).toBe(15);
    expect(extensionOrderDateWarning("2026-09-22", today)).toBeNull();
    expect(extensionOrderDateWarning("2026-09-07", today)).toBeNull();
    expect(extensionOrderDateWarning("2026-12-01", today)).toBeNull();
  });

  it("asks the user to check a date more than 15 days before today", () => {
    expect(extensionOrderDateWarning("2026-09-06", today)).toBe(
      "This order is dated 6 September 2026, more than 15 days ago. Check the date before recording it. It can still be recorded.",
    );
  });

  it("counts across a month and a year end by the calendar", () => {
    expect(extensionOrderDateWarning("2026-12-17", "2027-01-01")).toBeNull();
    expect(extensionOrderDateWarning("2026-12-16", "2027-01-01")).not.toBeNull();
  });

  it("says nothing while the date is incomplete", () => {
    expect(extensionOrderDateWarning("", today)).toBeNull();
    expect(extensionOrderDateWarning("20260", today)).toBeNull();
  });

  it("takes today as the date in India, not in the browser's own zone", () => {
    // 20:00 UTC on 21 September is already 22 September in India.
    expect(indiaToday(new Date(Date.UTC(2026, 8, 21, 20, 0)))).toBe("2026-09-22");
    expect(indiaToday(new Date(Date.UTC(2026, 8, 21, 18, 0)))).toBe("2026-09-21");
  });
});

describe("a period stops saying 'From contract start' once the date is known", () => {
  it("shows the contract start date for period 1 when it is recorded", () => {
    expect(periodLabel({ period_number: 1, effective_from: null }, "2027-01-01")).toBe("From 1 January 2027");
    expect(periodLabel({ period_number: 1, effective_from: null, effective_to: "2027-02-28" }, "2027-01-01")).toBe(
      "From 1 January 2027 to 28 February 2027",
    );
  });

  it("still says 'From contract start' while no date is recorded", () => {
    expect(periodLabel({ period_number: 1, effective_from: null })).toBe("From contract start");
    expect(periodLabel({ period_number: 1, effective_from: null }, null)).toBe("From contract start");
  });

  it("leaves a later period's own date alone", () => {
    expect(periodLabel({ period_number: 2, effective_from: "2027-03-01" }, "2027-01-01")).toBe("From 1 March 2027");
  });
});

describe("what a line's own dates read as", () => {
  it("says a blank line follows the Work Order rather than showing dashes", () => {
    // "Nothing recorded" and "follows the Work Order" are the same thing here, and only the second
    // tells the reader anything (owner decision 13).
    expect(lineDatesText(undefined)).toBe("The same dates as the Work Order");
    expect(lineDatesText({ line_start_date: null, line_end_date: null })).toBe("The same dates as the Work Order");
  });

  it("names both dates when the line carries both", () => {
    expect(lineDatesText({ line_start_date: "2027-02-01", line_end_date: "2027-03-01" })).toBe(
      "1 February 2027 to 1 March 2027",
    );
  });

  it("says which end the Work Order still supplies when only one date is recorded", () => {
    expect(lineDatesText({ line_start_date: "2027-02-01", line_end_date: null })).toBe(
      "From 1 February 2027, to the Work Order's end date",
    );
    expect(lineDatesText({ line_start_date: null, line_end_date: "2027-03-01" })).toBe(
      "From the Work Order's start date, to 1 March 2027",
    );
  });
});

describe("which lines the copy offers", () => {
  const allTerms = [
    terms("line-1", [{ billing_uom_code: "MONTH", normal_rate_amount: "100000.00" }]),
    terms("line-2", [{ billing_uom_code: "SHIFT", normal_rate_amount: "12000.00" }]),
  ];

  it("lists every other line and never the source", () => {
    const rows = copyTargetRows(LINES, allTerms, "line-1");
    expect(rows.map((row) => row.public_id)).toEqual(["line-2", "line-3"]);
  });

  it("works from any line, not only the first", () => {
    // The source is whichever line you are standing on (owner decision 20).
    expect(copyTargetRows(LINES, allTerms, "line-3").map((row) => row.line_number)).toEqual([1, 2]);
  });

  it("shows each line's own basis and rate so one that differs is easy to leave alone", () => {
    const rows = copyTargetRows(LINES, allTerms, "line-1");
    expect(rows[0].existingSummary).toBe("INR 12000.00 per shift");
    expect(rows[1].existingSummary).toBe("No terms yet");
  });

  it("describes a line whose basis has not been chosen without inventing one", () => {
    expect(existingTermsSummary(terms("line-9", [{ normal_rate_amount: "500.00" }]))).toBe(
      "INR 500.00, billing basis not chosen",
    );
    expect(existingTermsSummary(terms("line-9", [{ billing_uom_code: "DAY" }]))).toBe("no rate per day");
  });

  it("reads the period in force, not simply the first one", () => {
    const entry = terms("line-9", [
      { billing_uom_code: "MONTH", normal_rate_amount: "100000.00" },
      { billing_uom_code: "MONTH", normal_rate_amount: "112000.00" },
    ]);
    entry.current_period_number = 2;
    expect(existingTermsSummary(entry)).toBe("INR 112000.00 per month");
  });
});

describe("ticking chooses, and nothing is written until the button is pressed", () => {
  const rows = copyTargetRows(LINES, [terms("line-2", [{ billing_uom_code: "SHIFT" }])], "line-1");

  it("ticks the lines with no terms to begin with and leaves the others unticked", () => {
    expect(initialCopySelection(rows)).toEqual(["line-3"]);
  });

  it("unticking simply leaves a line out", () => {
    expect(toggleCopySelection(["line-3"], "line-3")).toEqual([]);
    expect(toggleCopySelection(["line-3"], "line-2")).toEqual(["line-3", "line-2"]);
  });

  it("says how many lines the button will change", () => {
    expect(copyButtonLabel(0)).toBe("Choose at least one line");
    expect(copyButtonLabel(1)).toBe("Apply these terms to 1 line");
    expect(copyButtonLabel(3)).toBe("Apply these terms to 3 lines");
  });

  it("asks only about ticked lines that already have terms", () => {
    expect(rowsNeedingConfirmation(rows, ["line-3"])).toEqual([]);
    expect(rowsNeedingConfirmation(rows, ["line-2", "line-3"]).map((row) => row.line_number)).toEqual([2]);
  });

  it("names those lines in the confirmation", () => {
    const two: CopyTargetRow[] = [
      { public_id: "line-2", line_number: 2, scope_description: "", hasTerms: true, existingSummary: "" },
      { public_id: "line-3", line_number: 3, scope_description: "", hasTerms: true, existingSummary: "" },
    ];
    expect(confirmationText([two[0]])).toContain("line 2 already has billing terms");
    expect(confirmationText(two)).toContain("line 2 and line 3 already have billing terms");
    expect(confirmationText(two)).toContain("replace them");
    expect(confirmationText([])).toBe("");
  });
});

describe("what the result says", () => {
  function result(overrides: Partial<CopyResult>): CopyResult {
    return {
      work_order_line_public_id: "line-2",
      line_number: 2,
      outcome: "COPIED",
      periods_copied: 1,
      replaced_period_count: 0,
      message: null,
      ...overrides,
    };
  }

  it("reports copied and replaced lines separately", () => {
    const text = copyResultText([
      result({ line_number: 2, outcome: "COPIED" }),
      result({ line_number: 3, outcome: "REPLACED", replaced_period_count: 2 }),
    ]);
    expect(text).toBe("Terms copied to line 2. Terms replaced on line 3.");
  });

  it("names a line that could not be written without hiding the ones that were", () => {
    const results = [
      result({ line_number: 2, outcome: "FAILED", periods_copied: 0, message: "Line 2 could not be written" }),
      result({ line_number: 3, outcome: "COPIED" }),
    ];
    expect(copyResultText(results)).toBe("Terms copied to line 3. Could not be written: line 2.");
    expect(copyHadFailures(results)).toBe(true);
    expect(copyHadFailures([result({})])).toBe(false);
  });

  it("joins three or more line names readably", () => {
    const text = copyResultText([
      result({ line_number: 2 }),
      result({ line_number: 3 }),
      result({ line_number: 4 }),
    ]);
    expect(text).toBe("Terms copied to line 2, line 3 and line 4.");
  });
});
