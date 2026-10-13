import { describe, expect, it } from "vitest";

import { type DetailState, INITIAL_DETAIL_STATE, MISSING_REASON, detailReducer } from "./resourceRequirementDetailState";
import { type LineFacts, type ResourceRequirement, formFromRequirement } from "./resourceRequirementState";

const line: LineFacts = {
  work_order_status_code: "HANDOFF_CREATED",
  scope_description: "Hiring of 250mt crane",
  equipment_service_category: "Crane",
  quantity: "8.00",
  uom: "Days",
  site: null,
  line_start_date: null,
  line_end_date: null,
  contract_start_date: null,
  contract_end_basis_code: null,
  contract_end_date: null,
  contract_gaps: [],
  billing_terms_period_number: 1,
  billing_uom_code: "SHIFT",
  shifts_per_day: null,
  work_order_crew_code: "STATED",
  work_order_crew_operators: 2,
  work_order_crew_helpers: 1,
};

function requirementAt(version: number, units: number): ResourceRequirement {
  return {
    requirement_public_id: "rr1",
    requirement_reference: "RR-000001",
    work_order_public_id: "wo1",
    work_order_code: "WO-000001",
    work_order_line_public_id: "line1",
    work_order_line_number: 1,
    units_required: units,
    required_from: "2026-10-15",
    required_to: null,
    crew_operators_required: 2,
    crew_helpers_required: 1,
    crew_notes: null,
    priority_code: "NORMAL",
    planning_notes: null,
    requirement_status_code: "OPEN",
    requirement_version: version,
    items: [
      {
        item_number: 1,
        equipment_class_code: "CRANE",
        equipment_class_label: "Crane",
        equipment_type_code: null,
        equipment_type_label: null,
        equipment_specification: null,
        capabilities: [],
      },
    ],
    warnings: [],
    line,
    cancellation_reason: null,
    cancelled_at: null,
    created_at: "2026-09-24T10:00:00Z",
    updated_at: "2026-09-24T10:00:00Z",
  };
}

const run = (state: DetailState, ...actions: Parameters<typeof detailReducer>[1][]) => actions.reduce(detailReducer, state);

describe("the requirement page's state", () => {
  const loaded = run(INITIAL_DETAIL_STATE, { type: "load-started", ticket: 1 }, { type: "loaded", ticket: 1, requirement: requirementAt(1, 2) });

  it("a reload installs the new version and discards every draft made against the old one", () => {
    // A change half made, the date tried with its facts, a refusal shown, and a cancellation half confirmed.
    const draft = run(
      loaded,
      { type: "change-started" },
      { type: "form-changed", form: { ...formFromRequirement(requirementAt(1, 2)), units_required: "5" } },
      { type: "edit-date-changed", ticket: 7, date: "2027-02-10" },
      { type: "edit-line-loaded", ticket: 7, line: { ...line, billing_uom_code: "DAY" } },
      { type: "change-refused", text: "Someone else changed this requirement after you opened it." },
      { type: "reason-changed", reason: "Customer will use its own crane" },
      { type: "cancel-asked" },
    );
    expect(draft.form?.units_required).toBe("5");
    expect(draft.confirmingCancel).toBe(true);

    const reloaded = run(draft, { type: "load-started", ticket: 2 }, { type: "loaded", ticket: 2, requirement: requirementAt(2, 3) });
    expect(reloaded).toEqual({ ...INITIAL_DETAIL_STATE, requirement: requirementAt(2, 3) });
    expect(reloaded.form).toBeNull();
    expect(reloaded.editLine).toBeNull();
    expect(reloaded.reason).toBe("");
    expect(reloaded.confirmingCancel).toBe(false);
    expect(reloaded.saveFeedback).toBeNull();
    expect(reloaded.cancelFeedback).toBeNull();
  });

  it("a change starts from the requirement as loaded", () => {
    const started = detailReducer(loaded, { type: "change-started" });
    expect(started.form).toEqual(formFromRequirement(requirementAt(1, 2)));
  });

  it("an edit clears a stale refusal, and a saved change keeps its message but drops the form", () => {
    const refused = run(loaded, { type: "change-started" }, { type: "change-refused", text: "No." });
    const edited = detailReducer(refused, { type: "form-changed", form: refused.form! });
    expect(edited.saveFeedback).toBeNull();
    const saved = detailReducer(edited, { type: "change-saved", requirement: requirementAt(2, 2), recorded: true });
    expect(saved.form).toBeNull();
    expect(saved.requirement?.requirement_version).toBe(2);
    expect(saved.saveFeedback).toEqual({ kind: "success", text: "Changes saved." });
    expect(detailReducer(edited, { type: "change-saved", requirement: requirementAt(1, 2), recorded: false }).saveFeedback?.text).toBe(
      "Nothing changed, so nothing was saved.",
    );
  });

  it("a saved change withdraws a cancellation that was half confirmed against the old version", () => {
    const halfCancelled = run(loaded, { type: "reason-changed", reason: "No longer needed" }, { type: "cancel-asked" }, { type: "change-started" });
    const saved = detailReducer(halfCancelled, { type: "change-saved", requirement: requirementAt(2, 2), recorded: true });
    expect(saved.confirmingCancel).toBe(false);
  });

  it("the date's facts apply only while a change is open", () => {
    expect(run(loaded, { type: "edit-date-changed", ticket: 7, date: "2027-02-10" }, { type: "edit-line-loaded", ticket: 7, line }).editLine).toBeNull();
    const open = run(
      loaded,
      { type: "change-started" },
      { type: "edit-date-changed", ticket: 7, date: "2027-02-10" },
      { type: "edit-line-loaded", ticket: 7, line },
    );
    expect(open.editLine).toBe(line);
    expect(detailReducer(open, { type: "change-discarded" }).editLine).toBeNull();
  });

  it("cancelling asks for a reason, then a confirmation", () => {
    const noReason = detailReducer(loaded, { type: "cancel-asked" });
    expect(noReason.confirmingCancel).toBe(false);
    expect(noReason.cancelFeedback).toEqual({ kind: "error", text: MISSING_REASON });
    const typed = detailReducer(noReason, { type: "reason-changed", reason: "  " });
    expect(typed.cancelFeedback).toBeNull();
    expect(detailReducer(typed, { type: "cancel-asked" }).confirmingCancel).toBe(false);
    const confirming = run(typed, { type: "reason-changed", reason: "Own crane" }, { type: "cancel-asked" });
    expect(confirming.confirmingCancel).toBe(true);
    expect(detailReducer(confirming, { type: "cancel-withdrawn" }).confirmingCancel).toBe(false);
    // Changing the reason after confirming asks for the confirmation again.
    expect(detailReducer(confirming, { type: "reason-changed", reason: "" }).confirmingCancel).toBe(false);
  });

  it("a cancellation installs the cancelled requirement and says so; a refusal withdraws the confirmation", () => {
    const confirming = run(loaded, { type: "reason-changed", reason: "Own crane" }, { type: "cancel-asked" });
    const cancelled = detailReducer(confirming, { type: "cancelled", requirement: { ...requirementAt(2, 2), requirement_status_code: "CANCELLED" } });
    expect(cancelled.requirement?.requirement_status_code).toBe("CANCELLED");
    expect(cancelled.reason).toBe("");
    expect(cancelled.cancelFeedback).toEqual({ kind: "success", text: "Requirement cancelled." });
    const refused = detailReducer(confirming, { type: "cancel-refused", text: "Refresh, then cancel." });
    expect(refused.confirmingCancel).toBe(false);
    expect(refused.reason).toBe("Own crane");
  });
});
