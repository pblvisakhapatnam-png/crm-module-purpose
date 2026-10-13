// Requests whose answers arrive late, out of order, or not at all (review rounds 2 and 3, F-07, F-10,
// F-12, F-13 and F-14). The frontend has no component tests yet, so the rules live in pure code - the
// planning-list controller, the requirement page's reducer and the date-facts rules - and are tested here.

import { describe, expect, it } from "vitest";

import { INITIAL_DETAIL_STATE, type DetailState, detailReducer } from "./resourceRequirementDetailState";
import {
  DATE_FACTS_CURRENT,
  INITIAL_PLANNING_LIST_VIEW,
  type LineFacts,
  type PlanningFilters,
  type PlanningListUpdate,
  type ResourceRequirement,
  createPlanningListController,
  dateFactsAllowSave,
  dateFactsAnswered,
  dateFactsAsked,
  dateFactsSaveProblem,
  formFromRequirement,
  planningListView,
} from "./resourceRequirementState";

// --- Answers that the test resolves by hand, in whatever order it chooses -----------------------------

type Deferred<T> = { promise: Promise<T>; resolve: (value: T) => void; reject: (error: Error) => void };

function deferred<T>(): Deferred<T> {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((ok, fail) => {
    resolve = ok;
    reject = fail;
  });
  return { promise, resolve, reject };
}

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

function requirementAt(version: number, reference = "RR-000001"): ResourceRequirement {
  return {
    requirement_public_id: "rr1",
    requirement_reference: reference,
    work_order_public_id: "wo1",
    work_order_code: "WO-000001",
    work_order_line_public_id: "line1",
    work_order_line_number: 1,
    units_required: version,
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

// --- The planning list ---------------------------------------------------------------------------------

function planningList(token: () => string | null = () => "token") {
  const asked: { filters: PlanningFilters; offset: number; answer: Deferred<ResourceRequirement[]> }[] = [];
  const shown: PlanningListUpdate[] = [];
  const controller = createPlanningListController({
    getToken: token,
    fetchRows: (_token, filters, offset) => {
      const answer = deferred<ResourceRequirement[]>();
      asked.push({ filters: { ...filters }, offset, answer });
      return answer.promise;
    },
    show: (update) => shown.push(update),
  });
  const lastRows = () => [...shown].reverse().find((update) => update.kind === "rows" || update.kind === "signed-out" || update.kind === "failed");
  return { controller, asked, shown, lastRows };
}

describe("the planning list's requests", () => {
  it("shows only the answer to the latest request, whatever order the answers arrive in", async () => {
    const { controller, asked, lastRows } = planningList();
    const first = controller.setFilters({ statusCode: "OPEN" });
    const second = controller.setFilters({ statusCode: "CANCELLED", classCode: "AERIAL_WORK_PLATFORM" });
    asked[1].answer.resolve([requirementAt(1, "RR-000002")]);
    await second;
    asked[0].answer.resolve([requirementAt(1, "RR-000001")]);
    await first;
    const shown = lastRows();
    expect(shown?.kind === "rows" && shown.rows.map((row) => row.requirement_reference)).toEqual(["RR-000002"]);
  });

  it("reloads with the filters the controls show, as a session change does", async () => {
    const { controller, asked } = planningList();
    void controller.setFilters({ statusCode: "CANCELLED", classCode: "CRANE" });
    void controller.load(0);
    expect(asked.map((request) => request.filters)).toEqual([
      { statusCode: "CANCELLED", classCode: "CRANE" },
      { statusCode: "CANCELLED", classCode: "CRANE" },
    ]);
    expect(controller.filters()).toEqual({ statusCode: "CANCELLED", classCode: "CRANE" });
  });

  it("never shows an answer that arrives after signing out", async () => {
    let token: string | null = "token";
    const { controller, asked, lastRows } = planningList(() => token);
    const inFlight = controller.load(0);
    token = null;
    await controller.load(0);
    expect(lastRows()).toEqual({ kind: "signed-out" });
    asked[0].answer.resolve([requirementAt(1)]);
    await inFlight;
    expect(lastRows()).toEqual({ kind: "signed-out" });
  });

  it("shows a failure only when it is the latest request's", async () => {
    const { controller, asked, lastRows } = planningList();
    const first = controller.load(0);
    const second = controller.load(25);
    asked[1].answer.resolve([requirementAt(1)]);
    await second;
    asked[0].answer.reject(new Error("HTTP 500"));
    await first;
    expect(lastRows()?.kind).toBe("rows");
  });
});

// --- The requirement page ------------------------------------------------------------------------------

const run = (state: DetailState, ...actions: Parameters<typeof detailReducer>[1][]) => actions.reduce(detailReducer, state);

describe("the requirement page's loads", () => {
  it("keeps the newest version, and the draft opened on it, when an older load answers last", () => {
    const state = run(
      INITIAL_DETAIL_STATE,
      { type: "load-started", ticket: 1 },
      { type: "load-started", ticket: 2 },
      { type: "loaded", ticket: 2, requirement: requirementAt(2) },
      { type: "change-started" },
      { type: "form-changed", form: { ...formFromRequirement(requirementAt(2)), units_required: "7" } },
      { type: "loaded", ticket: 1, requirement: requirementAt(1) },
    );
    expect(state.requirement?.requirement_version).toBe(2);
    expect(state.form?.units_required).toBe("7");
  });

  it("does not let a load asked before a save put the older version back", () => {
    const state = run(
      INITIAL_DETAIL_STATE,
      { type: "load-started", ticket: 1 },
      { type: "loaded", ticket: 1, requirement: requirementAt(1) },
      { type: "load-started", ticket: 2 },
      { type: "change-started" },
      { type: "change-saved", requirement: requirementAt(3), recorded: true },
      { type: "loaded", ticket: 2, requirement: requirementAt(2) },
    );
    expect(state.requirement?.requirement_version).toBe(3);
    expect(state.saveFeedback?.text).toBe("Changes saved.");
  });

  it("does not let a load asked before a cancellation put the open version back", () => {
    const state = run(
      INITIAL_DETAIL_STATE,
      { type: "load-started", ticket: 1 },
      { type: "loaded", ticket: 1, requirement: requirementAt(1) },
      { type: "load-started", ticket: 2 },
      { type: "cancelled", requirement: { ...requirementAt(2), requirement_status_code: "CANCELLED" } },
      { type: "loaded", ticket: 2, requirement: requirementAt(1) },
    );
    expect(state.requirement?.requirement_status_code).toBe("CANCELLED");
  });

  it("reports a failed load only when it is the load awaited", () => {
    const stale = run(INITIAL_DETAIL_STATE, { type: "load-started", ticket: 1 }, { type: "load-started", ticket: 2 }, { type: "load-failed", ticket: 1, text: "HTTP 500" });
    expect(stale.loadError).toBe("");
    const current = detailReducer(stale, { type: "load-failed", ticket: 2, text: "HTTP 500" });
    expect(current.loadError).toBe("HTTP 500");
  });
});

describe("saving a change waits for the date's facts", () => {
  const editing = run(
    INITIAL_DETAIL_STATE,
    { type: "load-started", ticket: 1 },
    { type: "loaded", ticket: 1, requirement: requirementAt(1) },
    { type: "change-started" },
  );

  it("may save until the date moves, then waits for the facts of the new date", () => {
    expect(dateFactsSaveProblem(editing.dateFacts)).toBeNull();
    const asked = detailReducer(editing, { type: "edit-date-changed", ticket: 5, date: "2027-02-10" });
    expect(dateFactsSaveProblem(asked.dateFacts)).toMatch(/^Reading the Work Order/);
    const answered = detailReducer(asked, { type: "edit-line-loaded", ticket: 5, line: { ...line, billing_uom_code: "DAY" } });
    expect(dateFactsSaveProblem(answered.dateFacts)).toBeNull();
    expect(answered.editLine?.billing_uom_code).toBe("DAY");
  });

  it("stays refused after a failed read, until a read succeeds", () => {
    const failed = run(editing, { type: "edit-date-changed", ticket: 5, date: "2027-02-10" }, { type: "edit-line-failed", ticket: 5 });
    expect(dateFactsSaveProblem(failed.dateFacts)).toMatch(/could not be read/);
    const retried = run(failed, { type: "edit-date-changed", ticket: 6, date: "2027-02-10" }, { type: "edit-line-loaded", ticket: 6, line });
    expect(dateFactsSaveProblem(retried.dateFacts)).toBeNull();
  });

  it("applies only the answer for the latest date", () => {
    const state = run(
      editing,
      { type: "edit-date-changed", ticket: 5, date: "2027-02-10" },
      { type: "edit-date-changed", ticket: 6, date: "2027-03-10" },
      { type: "edit-line-loaded", ticket: 5, line: { ...line, billing_uom_code: "DAY" } },
    );
    expect(state.editLine).toBeNull();
    expect(state.dateFacts.status).toBe("loading");
    expect(detailReducer(state, { type: "edit-line-failed", ticket: 5 }).dateFacts.status).toBe("loading");
  });
});

describe("the date-facts rules the new-requirement page uses", () => {
  it("waits for a whole date only, and counts only the awaited answer", () => {
    expect(dateFactsAsked(3, "2027-02-10")).toEqual({ status: "loading", ticket: 3 });
    expect(dateFactsAsked(4, "")).toEqual({ status: "current", ticket: 4 });
    const loading = dateFactsAsked(3, "2027-02-10");
    expect(dateFactsAnswered(loading, 2, true)).toBe(loading);
    expect(dateFactsAnswered(loading, 3, false)).toEqual({ status: "failed", ticket: 3 });
    expect(dateFactsAnswered(loading, 3, true)).toEqual({ status: "current", ticket: 3 });
    expect(dateFactsSaveProblem(DATE_FACTS_CURRENT)).toBeNull();
  });
});

describe("what the planning list shows (round 4, F-16)", () => {
  const PAGE = 25;

  it("stops showing the previous filter's rows the moment a new request starts, even if no answer comes", async () => {
    const shownViews: ReturnType<typeof planningListView>[] = [];
    let view = INITIAL_PLANNING_LIST_VIEW;
    const answers: Deferred<ResourceRequirement[]>[] = [];
    const controller = createPlanningListController({
      getToken: () => "token",
      fetchRows: () => {
        const answer = deferred<ResourceRequirement[]>();
        answers.push(answer);
        return answer.promise;
      },
      show: (update) => {
        view = planningListView(view, update, PAGE);
        shownViews.push(view);
      },
    });
    const first = controller.load(0);
    answers[0].resolve([requirementAt(1, "RR-000001")]);
    await first;
    expect(view.rows.map((row) => row.requirement_reference)).toEqual(["RR-000001"]);

    void controller.setFilters({ statusCode: "CANCELLED" }); // never answered
    expect(view.rows).toEqual([]);
    expect(view.loading).toBe(true);
    expect(view.offset).toBe(0);
  });

  it("keeps the page asked for, so a refresh after a filter change asks for the first page", () => {
    const onPageTwo = planningListView(INITIAL_PLANNING_LIST_VIEW, { kind: "rows", rows: [requirementAt(1)], offset: 25 }, PAGE);
    expect(onPageTwo.offset).toBe(25);
    const filterChanged = planningListView(onPageTwo, { kind: "loading", offset: 0 }, PAGE);
    expect(filterChanged.offset).toBe(0);
    expect(filterChanged.rows).toEqual([]);
    expect(filterChanged.hasNextPage).toBe(false);
  });

  it("shows no rows after a failure or a sign-out, and knows when there is a next page", () => {
    const full = planningListView(INITIAL_PLANNING_LIST_VIEW, { kind: "rows", rows: Array.from({ length: 26 }, () => requirementAt(1)), offset: 0 }, PAGE);
    expect(full.rows).toHaveLength(25);
    expect(full.hasNextPage).toBe(true);
    expect(planningListView(full, { kind: "failed", message: "HTTP 500" }, PAGE)).toMatchObject({ rows: [], error: "HTTP 500", loading: false });
    expect(planningListView(full, { kind: "signed-out" }, PAGE).rows).toEqual([]);
  });
});

describe("a failed read of the date's facts and its retry (round 4, F-17)", () => {
  it("refuses Save while the facts are loading or failed, and only then", () => {
    expect(dateFactsAllowSave({ status: "loading", ticket: 1 })).toBe(false);
    expect(dateFactsAllowSave({ status: "failed", ticket: 1 })).toBe(false);
    expect(dateFactsAllowSave(DATE_FACTS_CURRENT)).toBe(true);
  });

  it("leaves no stale refusal behind once a retry succeeds", () => {
    const state = run(
      INITIAL_DETAIL_STATE,
      { type: "load-started", ticket: 1 },
      { type: "loaded", ticket: 1, requirement: requirementAt(1) },
      { type: "change-started" },
      { type: "edit-date-changed", ticket: 5, date: "2027-02-10" },
      { type: "edit-line-failed", ticket: 5 },
      // A message from before the retry - a server refusal, say - must not outlive it.
      { type: "change-refused", text: "This requirement starts on 10 February 2027, after line 1 ends." },
    );
    expect(dateFactsAllowSave(state.dateFacts)).toBe(false);
    const retrying = detailReducer(state, { type: "edit-date-changed", ticket: 6, date: "2027-02-10" });
    expect(retrying.saveFeedback).toBeNull();
    const retried = detailReducer(retrying, { type: "edit-line-loaded", ticket: 6, line });
    expect(dateFactsAllowSave(retried.dateFacts)).toBe(true);
    expect(dateFactsSaveProblem(retried.dateFacts)).toBeNull();
    expect(retried.saveFeedback).toBeNull();
  });
});
