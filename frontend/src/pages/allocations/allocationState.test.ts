import { describe, expect, it } from "vitest";

import {
  type Assignment,
  type Candidate,
  type KitOption,
  type SiteFacts,
  EMPTY_ALLOCATE_FORM,
  allPages,
  allocateProblem,
  answerIsForDates,
  assetLabel,
  assignmentDaysText,
  canAllocate,
  canSetBillingCycle,
  capabilityText,
  complianceLabel,
  createPayload,
  datesProblem,
  finderParams,
  formAfterChoosing,
  kitFeedbackKey,
  kitPieceSelectable,
  kitPiecesToSend,
  kitProblem,
  leftOutText,
  lineSiteProblem,
  draftAfterRefresh,
  loadDrafts,
  loadDraftsAfterRefresh,
  loadFeedbackKey,
  reconcileChoices,
  releaseProblem,
  tripDayAfterRefresh,
  tripDayProblem,
  sortForDisplay,
  replacePayload,
  replaceStartProblem,
  replacingProblem,
  removeFeedbackKey,
  requirementText,
  siteText,
  statusLabel,
  unitFromSearch,
  unitRows,
  warningLabel,
  workOrderClosed,
} from "./allocationState";

const machine = {
  asset_public_id: "m1",
  asset_reference: "EQ-000101",
  asset_kind_code: "MACHINE",
  machine_number: "MH 12 AB 1234",
  serial_number: null,
  class_code: "CRANE",
  class_label: "Crane",
  type_code: "CRAWLER",
  type_label: "Crawler",
  model_public_id: "model",
  model_label: "ACME CC 250",
  asset_status_code: "ACTIVE",
  asset_version: 3,
  quantity: 1,
  tracking_code: "SINGLE",
  key_capability: { capability_code: "RATED_CAPACITY", capability_label: "Rated capacity", unit_symbol: "t", value: "250.000", choice_value: null, is_key: true },
  capabilities: [],
  flag_codes: [],
};

function answer(overall: string) {
  return {
    decision_public_id: null,
    overall_code: overall,
    valid_until: null,
    evaluated_on: "2026-09-28",
    site_state_code: "IN-MH",
    site_state_label: "Maharashtra",
    central_government_site: false,
    period_from: "2026-10-03",
    period_to: "2026-11-27",
    results: [],
  };
}

function candidate(overall: string | null, available = true): Candidate {
  return { machine, available, conflicts: [], answer: overall ? answer(overall) : null };
}

const SITE_OK: SiteFacts = {
  site_public_id: "s1",
  site_label: "Jetty 2, Invented Port",
  state_text: "Maharashtra",
  state_code: "IN-MH",
  state_label: "Maharashtra",
  central_government_site: false,
  problem_code: null,
  problem_message: null,
};
const OK = { site: SITE_OK, datesShown: true };

function assignment(unit: number, from: string, reference: string): Assignment {
  return { unit_number: unit, planned_from: from, assignment_reference: reference } as Assignment;
}

describe("who may do what", () => {
  it("allocates for Operations and Admin, and sets the billing cycle for those who change billing terms", () => {
    expect(canAllocate(["OPERATIONS_USER"])).toBe(true);
    expect(canAllocate(["SALES_USER", "FINANCE_USER"])).toBe(false);
    expect(canSetBillingCycle(["SALES_MANAGER"])).toBe(true);
    expect(canSetBillingCycle(["FINANCE_USER", "MANAGEMENT_READ_ONLY"])).toBe(false);
  });
});

describe("words", () => {
  it("names a hold, an unknown warning code as it is, and compliance with no answer", () => {
    expect(statusLabel("HELD")).toBe("Held for this Work Order");
    expect(statusLabel("RELEASED")).toBe("Freed");
    expect(warningLabel("SOMETHING_NEW")).toBe("SOMETHING_NEW");
    expect(complianceLabel(null)).toContain("Not checked");
  });

  it("shows a machine by its reference and registration, and a capability without trailing zeros", () => {
    expect(assetLabel(machine)).toBe("EQ-000101 (MH 12 AB 1234)");
    expect(assetLabel({ asset_reference: "EQ-000512", machine_number: null, serial_number: "HB-01" })).toBe("EQ-000512 (HB-01)");
    expect(capabilityText(machine.key_capability)).toBe("Rated capacity 250 t");
  });

  it("says what a requirement asks for, and what was left out", () => {
    const requirement = {
      units_required: 2,
      equipment_class_label: "Crane",
      equipment_type_label: "Crawler",
      capabilities: [{ capability_code: "RATED_CAPACITY", capability_label: "Rated capacity", unit_symbol: "t", minimum_value: "200.000", choice_value: null }],
    } as unknown as Parameters<typeof requirementText>[0];
    expect(requirementText(requirement)).toBe("2 x Crawler crane, rated capacity at least 200 t");
    expect(leftOutText({ TYPE_UNKNOWN: 2, RATING_UNKNOWN: 0, BELOW_REQUIREMENT: 1 })).toBe(
      "Not offered, of this class: 2 with type not known (its model is not mapped); 1 with below what is asked.",
    );
    expect(leftOutText({ TYPE_UNKNOWN: 0 })).toBe("");
  });

  it("says an allocation that ended before it started never went", () => {
    expect(assignmentDaysText({ planned_from: "2026-10-03", effective_to: "2026-10-02", assignment_status_code: "RELEASED" })).toBe(
      "Never went (ended before it started)",
    );
    expect(assignmentDaysText({ planned_from: "2026-10-03", effective_to: null, assignment_status_code: "HELD" })).toBe("from 3 October 2026, with no end date");
  });

  it("names the site with its central-government answer", () => {
    const site = { site_public_id: "s", site_label: "Jetty 2, Mumbai", state_text: "Maharashtra", state_code: "IN-MH", state_label: "Maharashtra", central_government_site: false, problem_code: null, problem_message: null };
    expect(siteText(site)).toBe("Jetty 2, Mumbai, Maharashtra; not a central-government site");
    expect(siteText({ ...site, central_government_site: null })).toContain("not answered");
  });
});

describe("units on a requirement", () => {
  it("marks the units the server says are covered, so only the others are offered (8A-R8-002)", () => {
    const allocations = [assignment(1, "2026-10-03", "AL-1"), assignment(2, "2026-10-03", "AL-2")];
    // Unit 1 fully covered, unit 2 only partly, unit 3 empty: only unit 1 is covered.
    const rows = unitRows(3, allocations, [1]);
    expect(rows.map((row) => [row.unit, row.required && !row.covered])).toEqual([[1, false], [2, true], [3, true]]);
    expect(unitRows(2, allocations, [1, 2]).map((row) => row.required && !row.covered)).toEqual([false, false]);
    expect(unitRows(2, [], []).map((row) => row.required && !row.covered)).toEqual([true, true]);
  });

  it("lists every unit required, and a unit above them only while it has allocations", () => {
    const rows = unitRows(2, [assignment(1, "2026-10-10", "AL-2"), assignment(1, "2026-10-03", "AL-1"), assignment(3, "2026-10-03", "AL-3")]);
    expect(rows.every((row) => !row.covered)).toBe(true);
    expect(rows.map((row) => [row.unit, row.required, row.allocations.map((item) => item.assignment_reference)])).toEqual([
      [1, true, ["AL-1", "AL-2"]],
      [2, true, []],
      [3, false, ["AL-3"]],
    ]);
  });
});

describe("allocating", () => {
  it("starts a new machine's confirmation afresh", () => {
    const ticked = { ...EMPTY_ALLOCATE_FORM, machine_public_id: "m1", accept_warnings: true };
    expect(formAfterChoosing(ticked, "m1").accept_warnings).toBe(true);
    expect(formAfterChoosing(ticked, "m2")).toMatchObject({ machine_public_id: "m2", accept_warnings: false });
  });

  it("refuses a busy or blocked machine, and a warning until ticked; a replacement needs its reason", () => {
    const form = { ...EMPTY_ALLOCATE_FORM, machine_public_id: "m1" };
    expect(allocateProblem(form, undefined, false, OK)).toBe("Choose a machine.");
    expect(allocateProblem(form, candidate("ELIGIBLE", false), false, OK)).toContain("allocated elsewhere");
    expect(allocateProblem(form, candidate("BLOCKED"), false, OK)).toContain("cannot be allocated");
    expect(allocateProblem(form, candidate("OVERRIDE_REQUIRED"), false, OK)).toContain("cannot be allocated");
    expect(allocateProblem(form, candidate("WARNING"), false, OK)).toContain("I have seen these warnings");
    expect(allocateProblem({ ...form, accept_warnings: true }, candidate("WARNING"), false, OK)).toBeNull();
    expect(allocateProblem(form, candidate("ELIGIBLE"), true, OK)).toContain("why the machine is being replaced");
    expect(allocateProblem({ ...form, reason_code: "OTHER" }, candidate("ELIGIBLE"), true, OK)).toContain("other reason");
    expect(allocateProblem({ ...form, reason_code: "BREAKDOWN" }, candidate("ELIGIBLE"), true, OK)).toBeNull();
    expect(allocateProblem(form, candidate(null), false, OK)).toContain("no answer for the site");
  });

  it("offers nothing while the site cannot be judged, naming what to put right (8A-R1-007)", () => {
    const form = { ...EMPTY_ALLOCATE_FORM, machine_public_id: "m1" };
    for (const problem_code of ["SITE_NOT_RECORDED", "STATE_NOT_RECOGNISED", "CENTRAL_NOT_ANSWERED"]) {
      const site = { ...SITE_OK, problem_code, problem_message: `Put right: ${problem_code}` };
      expect(allocateProblem(form, candidate(null), false, { site, datesShown: true })).toBe(`Put right: ${problem_code}`);
      expect(allocateProblem(form, candidate("ELIGIBLE"), true, { site, datesShown: true })).toBe(`Put right: ${problem_code}`);
    }
    expect(lineSiteProblem({ site: null, site_central_government: false }, 2)).toBe("Record the site on line 2's details first.");
    expect(lineSiteProblem({ site: { public_id: "s1" }, site_central_government: null }, 1)).toContain("central-government site");
    expect(lineSiteProblem({ site: { public_id: "s1" } }, 1)).toContain("central-government site");
    expect(lineSiteProblem({ site: { public_id: "s1" }, site_central_government: false }, 1)).toBeNull();
    expect(lineSiteProblem({ site: { public_id: "s1" }, site_central_government: true }, 1)).toBeNull();
  });

  it("offers nothing on a closed Work Order (8A-R2-001)", () => {
    const form = { ...EMPTY_ALLOCATE_FORM, machine_public_id: "m1" };
    expect(workOrderClosed({ work_order_status_code: "CLOSED" })).toBe(true);
    expect(workOrderClosed({ work_order_status_code: "AWAITING_RELEASE_TO_OPS" })).toBe(false);
    expect(allocateProblem(form, candidate("ELIGIBLE"), false, { ...OK, workOrderClosed: true })).toContain("This Work Order is closed");
    expect(allocateProblem({ ...form, reason_code: "BREAKDOWN" }, candidate("ELIGIBLE"), true, { ...OK, workOrderClosed: true })).toContain("closed");
    expect(allocateProblem(form, candidate("ELIGIBLE"), false, { ...OK, workOrderClosed: false })).toBeNull();
  });

  it("replaces only a held allocation on the unit and requirement shown (8A-R4-002)", () => {
    const replacing = { assignment_reference: "AL-000007", assignment_status_code: "HELD", unit_number: 1, requirement: { requirement_public_id: "r1" } };
    expect(replacingProblem(replacing, { requirement: "r1", unit: 1 })).toBeNull();
    expect(replacingProblem(replacing, { requirement: "r1", unit: 2 })).toContain("is on unit 1");
    expect(replacingProblem(replacing, { requirement: "r2", unit: 1 })).toContain("is on unit 1");
    expect(replacingProblem({ ...replacing, assignment_status_code: "REPLACED" }, { requirement: "r1", unit: 1 })).toContain("no longer held");
  });

  it("offers nothing while the unit is taken on the days shown (8A-R3-004)", () => {
    const form = { ...EMPTY_ALLOCATE_FORM, machine_public_id: "m1" };
    expect(allocateProblem(form, candidate("ELIGIBLE"), false, { ...OK, unitTaken: true })).toContain("already has a machine");
    expect(allocateProblem(form, candidate("ELIGIBLE"), false, { ...OK, unitTaken: false })).toBeNull();
  });

  it("starts a replacement only on a day of the allocation it replaces (8A-R3-003)", () => {
    const replaced = { assignment_reference: "AL-000007", planned_from: "2026-10-10", effective_to: "2026-10-31" };
    const before = "2026-10-01";
    expect(replaceStartProblem("2026-10-10", replaced, before)).toBeNull();
    expect(replaceStartProblem("2026-10-31", replaced, before)).toBeNull();
    expect(replaceStartProblem("2026-10-03", replaced, before)).toContain("must start on a day of AL-000007");
    expect(replaceStartProblem("2026-11-01", replaced, before)).toContain("must start on a day of AL-000007");
    expect(replaceStartProblem("2027-05-01", { ...replaced, effective_to: null }, before)).toBeNull();
    const form = { ...EMPTY_ALLOCATE_FORM, machine_public_id: "m1", reason_code: "BREAKDOWN" };
    const problem = replaceStartProblem("2026-10-03", replaced, before);
    expect(allocateProblem(form, candidate("ELIGIBLE"), true, { ...OK, replaceProblem: problem })).toBe(problem);
  });

  it("keeps a started allocation's first day: only its last day can change (TB-1 finding TB1-306)", () => {
    const held = { assignment_reference: "AL-000007", planned_from: "2026-10-10" };
    expect(datesProblem("2026-10-12", held, "2026-10-01")).toBeNull();
    expect(datesProblem("2026-10-10", held, "2026-10-10")).toBeNull();
    expect(datesProblem("2026-10-12", held, "2026-10-10")).toContain("its first day cannot change");
    expect(datesProblem("2026-10-08", held, "2026-10-20")).toContain("Recorded by mistake");
  });

  it("saves only for the dates the machines were found for (8A-R1-006)", () => {
    const found = { period_from: "2026-10-03", period_to: "2026-11-27" };
    expect(answerIsForDates(found, { from: "2026-10-03", to: "2026-11-27" })).toBe(true);
    expect(answerIsForDates(found, { from: "2026-10-03", to: "2026-11-20" })).toBe(false);
    expect(answerIsForDates(found, { from: "2026-10-04", to: "2026-11-27" })).toBe(false);
    expect(answerIsForDates({ period_from: "2026-10-03", period_to: null }, { from: "2026-10-03", to: "" })).toBe(true);
    expect(answerIsForDates({ period_from: "2026-10-03", period_to: null }, { from: "2026-10-03", to: "2026-11-27" })).toBe(false);
    const form = { ...EMPTY_ALLOCATE_FORM, machine_public_id: "m1" };
    expect(allocateProblem(form, candidate("ELIGIBLE"), false, { site: SITE_OK, datesShown: false })).toContain("Find machines for these days first");
  });

  it("sends the billing cycle only when the user may set it and chose one", () => {
    const form = { ...EMPTY_ALLOCATE_FORM, machine_public_id: "m1", billing_cycle_code: "MONTHLY", notes: "  " };
    const period = { period_from: "2026-10-03", period_to: null };
    expect(createPayload("r", 2, period, form, "k", true)).toMatchObject({ unit_number: 2, billing_cycle_code: "MONTHLY", notes: null, planned_to: null });
    expect(createPayload("r", 2, period, form, "k", false)).not.toHaveProperty("billing_cycle_code");
    expect(replacePayload(4, period, { ...form, billing_cycle_code: "" }, "k", true)).not.toHaveProperty("billing_cycle_code");
    expect(replacePayload(4, period, form, "k", true)).toMatchObject({ expected_assignment_version: 4, replace_from: "2026-10-03" });
  });

  it("asks the finder for the period shown, and the unit in the address", () => {
    expect(finderParams({ requirement: "r", unit: 2, from: "", to: "", replacing: "" }).toString()).toBe("requirement_public_id=r&unit_number=2");
    expect(finderParams({ requirement: "r", unit: 1, from: "2026-10-03", to: "2026-11-27", replacing: "a" }).get("replacing_assignment_public_id")).toBe("a");
    expect(unitFromSearch("3")).toBe(3);
    expect(unitFromSearch("0")).toBe(1);
    expect(unitFromSearch("x")).toBe(1);
  });
});

describe("kit", () => {
  const hook = { ...machine, asset_public_id: "hook", asset_reference: "EQ-000512", machine_number: null, tracking_code: "SINGLE" };
  const weights = { ...machine, asset_public_id: "cw", asset_reference: "EQ-000513", machine_number: null, tracking_code: "COUNTED", quantity: 4 };
  const options: KitOption[] = [
    { piece: hook, available: true, quantity_free: 1, conflicts: [], answer: answer("ELIGIBLE") },
    { piece: weights, available: true, quantity_free: 3, conflicts: [], answer: answer("ELIGIBLE") },
  ];

  it("keeps, when the options are read again, only choices still possible (8A-FB2-003)", () => {
    const chosen = { hook: "on", cw: "3" };
    expect(reconcileChoices(chosen, options)).toEqual(chosen);
    // The hook block taken meanwhile, and only two counterweight blocks still free: both choices go.
    const now = [
      { ...options[0], available: false },
      { ...options[1], quantity_free: 2 },
    ];
    expect(reconcileChoices(chosen, now)).toEqual({});
    // A count still within what is free stays; a piece now blocked goes; a piece no longer offered goes.
    expect(reconcileChoices({ cw: "2", hook: "on" }, [{ ...options[1], quantity_free: 2 }, { ...options[0], answer: answer("BLOCKED") }])).toEqual({ cw: "2" });
    expect(reconcileChoices({ gone: "on" }, options)).toEqual({});
  });

  it("sends a ticked piece as one and a counted set as typed", () => {
    expect(kitPiecesToSend({ hook: "on", cw: "2" }, options)).toEqual([
      { piece_public_id: "hook", quantity: 1 },
      { piece_public_id: "cw", quantity: 2 },
    ]);
    expect(kitPiecesToSend({ cw: "" }, options)).toEqual([]);
  });

  it("refuses nothing chosen, more than is free, a fraction, and a warning until ticked", () => {
    expect(kitProblem({}, options, false)).toBe("Choose at least one piece.");
    expect(kitProblem({ cw: "4" }, options, false)).toBe("Only 3 of EQ-000513 are free over these days.");
    expect(kitProblem({ cw: "1.5" }, options, false)).toContain("whole number");
    const warned = [{ ...options[0], answer: answer("WARNING") }];
    expect(kitProblem({ hook: "on" }, warned, false)).toContain("I have seen these warnings");
    expect(kitProblem({ hook: "on" }, warned, true)).toBeNull();
    expect(kitProblem({ hook: "on" }, [{ ...options[0], answer: answer("BLOCKED") }], true)).toContain("cannot go");
    expect(kitProblem({ hook: "on" }, [{ ...options[0], answer: null }], true)).toContain("cannot be judged for the site");
  });

  it("keeps each kit action's message to its own trip or line (8A-R5-002)", () => {
    expect(kitFeedbackKey(1)).not.toBe(kitFeedbackKey(2));
    expect(removeFeedbackKey("line-a")).not.toBe(removeFeedbackKey("line-b"));
    expect(new Set([kitFeedbackKey(1), removeFeedbackKey("1"), "kit", "remove"]).size).toBe(4);
  });

  it("offers the next Trip (Own Load) on the allocation's first day, following it, and refuses a day outside (8A-FB2-004)", () => {
    // First read: the first day.
    expect(tripDayAfterRefresh("", undefined, "2026-10-04")).toBe("2026-10-04");
    // The start moves later: the form still showed the old first day, so it follows.
    expect(tripDayAfterRefresh("2026-10-04", "2026-10-04", "2026-10-06")).toBe("2026-10-06");
    // A day the user chose stays.
    expect(tripDayAfterRefresh("2026-10-20", "2026-10-04", "2026-10-06")).toBe("2026-10-20");
    expect(tripDayProblem("2026-10-05", "2026-10-06", "2026-11-20")).toContain("goes on a day of the allocation");
    expect(tripDayProblem("2026-11-21", "2026-10-06", "2026-11-20")).toContain("goes on a day of the allocation");
    expect(tripDayProblem("2026-10-06", "2026-10-06", "2026-11-20")).toBeNull();
    expect(tripDayProblem("2027-03-01", "2026-10-06", null)).toBeNull();
    expect(tripDayProblem("", "2026-10-06", null)).toContain("Choose the day");
  });

  it("frees only with a reason, and with a note when the reason is Other (8A-FB-005)", () => {
    const free = (reason_code: string, note: string) => releaseProblem({ last_day: "", reason_code, note }, "2026-10-10", "2026-10-01");
    expect(free("", "")).toContain("Choose why");
    expect(free("OTHER", "   ")).toContain("other reason");
    expect(free("OTHER", "Customer postponed")).toBeNull();
    expect(free("NOT_NEEDED", "")).toBeNull();
  });

  it("keeps a started allocation's days: a last day is needed unless it was recorded by mistake (owner, 1 October 2026)", () => {
    const form = { last_day: "", reason_code: "NOT_NEEDED", note: "" };
    expect(releaseProblem(form, "2026-10-10", "2026-10-10")).toContain("give its last day on the job");
    expect(releaseProblem(form, "2026-10-10", "2026-10-09")).toBeNull();
    expect(releaseProblem({ ...form, last_day: "2026-10-12" }, "2026-10-10", "2026-10-20")).toBeNull();
    expect(releaseProblem({ ...form, reason_code: "RECORDED_BY_MISTAKE" }, "2026-10-10", "2026-10-20")).toBeNull();
  });

  it("starts a started allocation's replacement after its first day (owner, 1 October 2026)", () => {
    const replaced = { assignment_reference: "AL-000007", planned_from: "2026-10-10", effective_to: "2026-10-31" };
    expect(replaceStartProblem("2026-10-10", replaced, "2026-10-10")).toContain("must start after its first day");
    expect(replaceStartProblem("2026-10-11", replaced, "2026-10-10")).toBeNull();
    expect(replaceStartProblem("2026-10-10", replaced, "2026-10-09")).toBeNull();
  });

  it("keeps what the user is typing when a fresh copy does not change that value (owner's screen check)", () => {
    // First read, or another allocation: the recorded value.
    expect(draftAfterRefresh("typed", undefined, "MONTHLY")).toBe("MONTHLY");
    // The recorded value unchanged by the fresh copy: the draft stays.
    expect(draftAfterRefresh("typed", "", "")).toBe("typed");
    expect(draftAfterRefresh({ from: "2026-10-05", to: "" }, { from: "2026-10-04", to: "" }, { from: "2026-10-04", to: "" })).toEqual({
      from: "2026-10-05",
      to: "",
    });
    // Changed: the fresh value.
    expect(draftAfterRefresh("typed", "WEEKLY", "MONTHLY")).toBe("MONTHLY");
    const trip = { trip_public_id: "t", goes_on: "2026-10-04", kit: [] };
    const before = [{ ...trip, trip_number: 1, note: null }];
    const after = [
      { ...trip, trip_number: 1, note: null },
      { ...trip, trip_number: 2, note: "Crawlers" },
    ];
    // Typing "Base" into trip 1 while a new trip 2 arrives: trip 1 keeps it, trip 2 takes its recorded note.
    expect(loadDraftsAfterRefresh({ 1: "Base" }, before, after)).toEqual({ 1: "Base", 2: "Crawlers" });
    expect(loadDraftsAfterRefresh({ 1: "Base" }, undefined, after)).toEqual({ 1: "", 2: "Crawlers" });
  });

  it("keeps what each Trip (Own Load) carries to its own trip", () => {
    expect(loadFeedbackKey(1)).not.toBe(loadFeedbackKey(2));
    expect(new Set([loadFeedbackKey(1), kitFeedbackKey(1), "trip"]).size).toBe(3);
    const trip = { trip_public_id: "t", goes_on: "2026-10-01", kit: [] };
    expect(loadDrafts([{ ...trip, trip_number: 1, note: null }, { ...trip, trip_number: 2, note: "Crawlers" }])).toEqual({
      1: "",
      2: "Crawlers",
    });
  });

  it("offers only free pieces that can be allocated, with a warning or without (8A-R4-004)", () => {
    expect(kitPieceSelectable(options[0])).toBe(true);
    expect(kitPieceSelectable({ ...options[0], answer: answer("WARNING") })).toBe(true);
    for (const overall of ["BLOCKED", "OVERRIDE_REQUIRED"]) {
      expect(kitPieceSelectable({ ...options[0], answer: answer(overall) })).toBe(false);
    }
    expect(kitPieceSelectable({ ...options[0], answer: null })).toBe(false);
    expect(kitPieceSelectable({ ...options[0], available: false })).toBe(false);
  });
});

describe("lists of allocations", () => {
  type Row = { id: number; status: string };
  // A server listing HELD rows in the order they were recorded, `after` the row given (8A-FB-004).
  const server = (rows: Row[], asked: (number | null)[]) => async (after: Row | null, limit: number) => {
    asked.push(after ? after.id : null);
    return rows.filter((row) => row.status === "HELD" && (after === null || row.id > after.id)).slice(0, limit);
  };

  it("fetches every page until one comes back short, so none stops at one page (8A-R9-003)", async () => {
    const rows = Array.from({ length: 401 }, (_, id) => ({ id, status: "HELD" }));
    const asked: (number | null)[] = [];
    expect(await allPages(server(rows, asked), 200)).toEqual(rows);
    expect(asked).toEqual([null, 199, 399]);
    // An exact multiple of the page size ends with an empty page.
    asked.length = 0;
    expect(await allPages(server(rows.slice(0, 400), asked), 200)).toHaveLength(400);
    expect(asked).toEqual([null, 199, 399]);
  });

  it("reads each row once when one leaves the list between two pages (8A-FB-004)", async () => {
    const rows = Array.from({ length: 401 }, (_, id) => ({ id, status: "HELD" }));
    const asked: (number | null)[] = [];
    const list = server(rows, asked);
    let pages = 0;
    const fetchPage = async (after: Row | null, limit: number) => {
      const page = await list(after, limit);
      // After the first page, a row already read is freed: it leaves the HELD list. Skipping 200 rows would now
      // skip row 200 as well; reading after row 199 does not.
      if (pages++ === 0) rows[5].status = "RELEASED";
      return page;
    };
    const read = await allPages(fetchPage, 200);
    expect(read.map((row) => row.id)).toEqual(Array.from({ length: 401 }, (_, id) => id));
    expect(new Set(read.map((row) => row.id)).size).toBe(401);
  });

  it("lists held allocations first, then by first day, Work Order, line and unit, else in the order recorded", () => {
    const row = (reference: string, status: string, planned_from: string, work_order_code = "WO-1", unit_number = 1) => ({
      assignment_reference: reference,
      assignment_status_code: status,
      planned_from,
      work_order_code,
      work_order_line_number: 1,
      unit_number,
    });
    const recorded = [
      row("AL-1", "RELEASED", "2026-10-01"),
      row("AL-2", "HELD", "2026-10-09"),
      row("AL-3", "HELD", "2026-10-04", "WO-2"),
      row("AL-4", "HELD", "2026-10-04", "WO-1", 2),
      row("AL-5", "HELD", "2026-10-04", "WO-1", 1),
      row("AL-6", "REPLACED", "2026-10-01"),
    ];
    expect(sortForDisplay(recorded).map((item) => item.assignment_reference)).toEqual(["AL-5", "AL-4", "AL-3", "AL-2", "AL-1", "AL-6"]);
    expect(recorded[0].assignment_reference).toBe("AL-1");
  });
});
