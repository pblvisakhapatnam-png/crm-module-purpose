import { describe, expect, it } from "vitest";

import {
  type EquipmentStructure,
  type LineFacts,
  type RequirementDefaults,
  type ResourceRequirement,
  canWriteRequirements,
  capabilityFieldLabel,
  capabilityFields,
  CREW_UNTOUCHED,
  contractText,
  createLatestOnly,
  crewTouchedAfterEdit,
  fetchAllRequirementPages,
  findClass,
  formAfterClassChange,
  formAfterLineDefaults,
  formFromDefaults,
  formFromRequirement,
  formWithCapabilityValue,
  hiringClasses,
  isCompleteIsoDate,
  newRequestKey,
  newRequirementHref,
  plainNumber,
  requirementDatesText,
  requirementFormProblem,
  requirementPayload,
  requirementRecordedText,
  requirementSummary,
  typeOptions,
  warningLabel,
  workOrderCrewText,
  shiftsPerDayText,
} from "./resourceRequirementState";

const capability = (overrides: Partial<EquipmentStructure["classes"][number]["capabilities"][number]>) => ({
  capability_code: "RATED_CAPACITY",
  capability_label: "Rated capacity",
  unit_code: "TONNE",
  unit_symbol: "t",
  whole_numbers_only: false,
  value_kind_code: "MINIMUM",
  allowed_values: null,
  is_key: false,
  display_order: 10,
  is_active: true,
  ...overrides,
});

const structure: EquipmentStructure = {
  taxonomy_version: 1,
  classes: [
    {
      class_code: "PRIME_MOVER",
      class_label: "Prime Mover",
      display_order: 50,
      business_line_codes: ["TRANSPORTATION"],
      is_active: true,
      types: [],
      capabilities: [
        capability({
          capability_code: "AXLE_CONFIGURATION",
          capability_label: "Axle configuration",
          unit_code: null,
          unit_symbol: null,
          value_kind_code: "CHOICE",
          allowed_values: ["4X2", "6X4"],
        }),
      ],
    },
    {
      class_code: "CRANE",
      class_label: "Crane",
      display_order: 10,
      business_line_codes: ["HIRING"],
      is_active: true,
      types: [
        { type_code: "CRAWLER", type_label: "Crawler", display_order: 10, is_active: true },
        { type_code: "DERRICK", type_label: "Derrick", display_order: 80, is_active: false },
      ],
      capabilities: [
        capability({ capability_code: "MAIN_BOOM_LENGTH", capability_label: "Main boom length", unit_code: "METRE", unit_symbol: "m", display_order: 20 }),
        capability({ is_key: true }),
        capability({ capability_code: "OLD_REACH", capability_label: "Old reach", unit_symbol: "m", display_order: 30, is_active: false }),
      ],
    },
    {
      class_code: "GENERATOR",
      class_label: "Generator",
      display_order: 100,
      business_line_codes: [],
      is_active: true,
      types: [],
      capabilities: [],
    },
    {
      class_code: "TRAILER",
      class_label: "Trailer",
      display_order: 60,
      business_line_codes: ["HIRING"],
      is_active: true,
      types: [],
      capabilities: [capability({ capability_code: "AXLE_COUNT", capability_label: "Axles", unit_code: "COUNT", unit_symbol: "", whole_numbers_only: true })],
    },
  ],
};

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
  billing_terms_period_number: null,
  billing_uom_code: null,
  shifts_per_day: null,
  work_order_crew_code: null,
  work_order_crew_operators: null,
  work_order_crew_helpers: null,
};

const defaults: RequirementDefaults = {
  work_order_public_id: "wo1",
  work_order_code: "WO-000001",
  work_order_line_public_id: "line1",
  work_order_line_number: 2,
  line,
  suggested: {
    units_required: 1,
    required_from: "2026-10-01",
    required_to: null,
    crew_operators_required: 2,
    crew_helpers_required: 0,
    priority_code: "NORMAL",
    equipment_class_code: "CRANE",
    equipment_type_code: null,
    equipment_class_matched_term: "Crane",
  },
  existing_requirement_count: 0,
};

const requirement: ResourceRequirement = {
  requirement_public_id: "rr1",
  requirement_reference: "RR-000001",
  work_order_public_id: "wo1",
  work_order_code: "WO-000001",
  work_order_line_public_id: "line1",
  work_order_line_number: 2,
  units_required: 2,
  required_from: "2026-10-15",
  required_to: null,
  crew_operators_required: 1,
  crew_helpers_required: 1,
  crew_notes: null,
  priority_code: "URGENT",
  planning_notes: "Tide window",
  requirement_status_code: "OPEN",
  requirement_version: 3,
  items: [
    {
      item_number: 1,
      equipment_class_code: "CRANE",
      equipment_class_label: "Crane",
      equipment_type_code: "CRAWLER",
      equipment_type_label: "Crawler",
      equipment_specification: null,
      capabilities: [
        {
          capability_code: "RATED_CAPACITY",
          capability_label: "Rated capacity",
          unit_code: "TONNE",
          unit_symbol: "t",
          value_kind_code: "MINIMUM",
          is_key: true,
          minimum_value: "220.000",
          choice_value: null,
        },
      ],
    },
  ],
  warnings: [],
  line,
  cancellation_reason: null,
  cancelled_at: null,
  created_at: "2026-09-24T10:00:00Z",
  updated_at: "2026-09-24T10:00:00Z",
};

describe("who may write", () => {
  it("is Operations and Admin only", () => {
    expect(canWriteRequirements(["OPERATIONS_USER"])).toBe(true);
    expect(canWriteRequirements(["ADMIN"])).toBe(true);
    for (const role of ["SALES_USER", "SALES_MANAGER", "FINANCE_USER", "MANAGEMENT_READ_ONLY"]) {
      expect(canWriteRequirements([role])).toBe(false);
    }
  });
});

describe("the structure", () => {
  it("offers only live classes Hiring deploys, in the structure's order", () => {
    expect(hiringClasses(structure).map((item) => item.class_code)).toEqual(["CRANE", "TRAILER"]);
    expect(hiringClasses(null)).toEqual([]);
  });

  it("offers live types, and a retired one only when the requirement already has it", () => {
    const crane = findClass(structure, "CRANE");
    expect(typeOptions(crane).map((item) => item.type_code)).toEqual(["CRAWLER"]);
    expect(typeOptions(crane, "DERRICK").map((item) => item.type_code)).toEqual(["CRAWLER", "DERRICK"]);
  });

  it("puts the key capability first and leaves out a retired one unless it is kept", () => {
    const crane = findClass(structure, "CRANE");
    expect(capabilityFields(crane).map((item) => item.capability_code)).toEqual(["RATED_CAPACITY", "MAIN_BOOM_LENGTH"]);
    expect(capabilityFields(crane, ["OLD_REACH"]).map((item) => item.capability_code)).toEqual([
      "RATED_CAPACITY",
      "MAIN_BOOM_LENGTH",
      "OLD_REACH",
    ]);
  });

  it("labels a capability with its unit, and a count or a list without one", () => {
    const crane = findClass(structure, "CRANE")!;
    expect(capabilityFieldLabel(crane.capabilities[1])).toBe("Rated capacity (t)");
    expect(capabilityFieldLabel(findClass(structure, "TRAILER")!.capabilities[0])).toBe("Axles");
    expect(capabilityFieldLabel(findClass(structure, "PRIME_MOVER")!.capabilities[0])).toBe("Axle configuration");
  });
});

describe("the form", () => {
  it("starts from what the server suggests", () => {
    const form = formFromDefaults(defaults);
    expect(form.units_required).toBe("1");
    expect(form.required_from).toBe("2026-10-01");
    expect(form.crew_operators_required).toBe("2");
    expect(form.crew_helpers_required).toBe("0");
    expect(form.equipment_class_code).toBe("CRANE");
    expect(form.equipment_type_code).toBe("");
  });

  it("starts the crew empty when the Work Order's crew is not recorded", () => {
    const form = formFromDefaults({ ...defaults, suggested: { ...defaults.suggested, crew_operators_required: null, crew_helpers_required: null } });
    expect(form.crew_operators_required).toBe("");
    expect(requirementFormProblem(form, structure)).toBe("Enter the operators.");
  });

  it("reads a saved requirement back without the stored trailing zeros", () => {
    const form = formFromRequirement(requirement);
    expect(form.capability_values).toEqual({ RATED_CAPACITY: "220" });
    expect(form.equipment_type_code).toBe("CRAWLER");
    expect(form.required_to).toBe("");
    expect(form.planning_notes).toBe("Tide window");
  });

  it("clears the type and capabilities when the class changes, and keeps them when it does not", () => {
    const form = formWithCapabilityValue({ ...formFromRequirement(requirement) }, "MAIN_BOOM_LENGTH", "60");
    expect(formAfterClassChange(form, "CRANE")).toBe(form);
    const changed = formAfterClassChange(form, "TRAILER");
    expect(changed.equipment_type_code).toBe("");
    expect(changed.capability_values).toEqual({});
  });
});

describe("what stops the form being sent", () => {
  const valid = formFromRequirement(requirement);

  it.each([
    [{ units_required: "0" }, "Number of machines must be at least 1."],
    [{ units_required: "1.5" }, "Number of machines must be a whole number of at least 1."],
    [{ units_required: "2147483648" }, "Number of machines is larger than can be recorded."],
    [{ required_from: "" }, "Enter the date the machines are needed from."],
    [{ required_to: "2026-10-14" }, "The requirement cannot end on 14 October 2026, before it starts on 15 October 2026."],
    [{ crew_helpers_required: "-1" }, "Helpers must be a whole number, 0 or more."],
    [{ equipment_class_code: "" }, "Choose the kind of machine needed."],
  ])("refuses %o", (overrides, message) => {
    expect(requirementFormProblem({ ...valid, ...overrides }, structure)).toBe(message);
  });

  it.each([
    ["0", "Rated capacity must be greater than 0."],
    ["abc", "Rated capacity must be a number."],
    ["1.2345", "Rated capacity can have at most 3 decimal places."],
    ["1234567890", "Rated capacity is larger than can be recorded."],
    ["1e10", "Rated capacity is larger than can be recorded."],
  ])("refuses a capability value of %s", (value, message) => {
    expect(requirementFormProblem(formWithCapabilityValue(valid, "RATED_CAPACITY", value), structure)).toBe(message);
  });

  it("takes whole numbers only for a count", () => {
    const trailer = formWithCapabilityValue(formAfterClassChange(valid, "TRAILER"), "AXLE_COUNT", "4.5");
    expect(requirementFormProblem(trailer, structure)).toBe("Axles is counted in whole numbers.");
    expect(requirementFormProblem(formWithCapabilityValue(trailer, "AXLE_COUNT", "4"), structure)).toBeNull();
  });

  it("lets a blank capability and a blank end date through", () => {
    expect(requirementFormProblem(formWithCapabilityValue(valid, "RATED_CAPACITY", ""), structure)).toBeNull();
  });
});

describe("the request", () => {
  it("sends the fields, one item, and only the capabilities given - never a unit", () => {
    const form = formWithCapabilityValue(formFromRequirement(requirement), "MAIN_BOOM_LENGTH", " ");
    expect(requirementPayload({ ...form, crew_notes: "  " }, structure)).toEqual({
      units_required: 2,
      required_from: "2026-10-15",
      required_to: null,
      crew_operators_required: 1,
      crew_helpers_required: 1,
      crew_notes: null,
      priority_code: "URGENT",
      planning_notes: "Tide window",
      items: [
        {
          equipment_class_code: "CRANE",
          equipment_type_code: "CRAWLER",
          equipment_specification: null,
          capabilities: [{ capability_code: "RATED_CAPACITY", minimum_value: "220" }],
        },
      ],
    });
  });

  it("sends a fixed-list capability as its chosen value", () => {
    const form = formWithCapabilityValue(formAfterClassChange(formFromRequirement(requirement), "PRIME_MOVER"), "AXLE_CONFIGURATION", "6X4");
    const item = (requirementPayload(form, structure).items as Array<{ capabilities: unknown[] }>)[0];
    expect(item.capabilities).toEqual([{ capability_code: "AXLE_CONFIGURATION", choice_value: "6X4" }]);
  });

  it("makes a version 4 UUID from random bytes", () => {
    const key = newRequestKey((bytes) => bytes.fill(0xff));
    expect(key).toBe("ffffffff-ffff-4fff-bfff-ffffffffffff");
    expect(newRequestKey()).toMatch(/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/);
  });
});

describe("words for the screens", () => {
  it("says a save the server already had from the form was recorded earlier (TB-1 TB1-102 b)", () => {
    expect(requirementRecordedText("RR-000123", false)).toBe("Recorded as RR-000123. Opening it...");
    expect(requirementRecordedText("RR-000123", true)).toBe("Already recorded as RR-000123. Opening it...");
  });

  it("summarises a requirement in one line with its key capability", () => {
    expect(requirementSummary(requirement)).toBe("2 x Crawler crane, rated capacity at least 220 t");
    const anyForklift = {
      units_required: 1,
      items: [{ ...requirement.items[0], equipment_class_label: "Forklift", equipment_type_code: null, equipment_type_label: null, capabilities: [] }],
    };
    expect(requirementSummary(anyForklift)).toBe("1 x Forklift");
  });

  it("says a blank end date means until the line ends", () => {
    expect(requirementDatesText(requirement)).toBe("From 15 October 2026, until the line ends");
    expect(requirementDatesText({ required_from: "2026-10-15", required_to: "2027-03-31" })).toBe("15 October 2026 to 31 March 2027");
  });

  it("describes the Work Order's crew as its terms record it", () => {
    expect(workOrderCrewText(line)).toBe("Not recorded yet");
    expect(workOrderCrewText({ ...line, work_order_crew_code: "NONE" })).toBe("Equipment only: no crew");
    expect(
      workOrderCrewText({ ...line, work_order_crew_code: "STATED", work_order_crew_operators: 1, work_order_crew_helpers: 2, billing_uom_code: "SHIFT" }),
    ).toBe("1 operator, 2 helpers per shift");
    expect(workOrderCrewText({ ...line, work_order_crew_code: "STATED", work_order_crew_operators: 2, work_order_crew_helpers: null })).toBe(
      "Crew stated, but a number is not recorded yet",
    );
  });

  it("describes the contract, including one with no dates", () => {
    expect(contractText(line)).toBe("Not recorded yet");
    expect(contractText({ ...line, contract_start_date: "2026-10-01", contract_end_date: "2027-09-30" })).toBe(
      "1 October 2026 to 30 September 2027",
    );
    expect(contractText({ ...line, contract_start_date: "2026-10-01", contract_end_basis_code: "UNTIL_WORK_COMPLETE" })).toBe(
      "1 October 2026, until the work is complete",
    );
  });

  it("words every warning and shows an unknown one as it is", () => {
    expect(warningLabel("SITE_NOT_RECORDED")).toBe("The line has no site recorded yet");
    expect(warningLabel("SOMETHING_NEW")).toBe("SOMETHING_NEW");
  });

  it("drops only trailing zeros after a decimal point", () => {
    expect(plainNumber("220.000")).toBe("220");
    expect(plainNumber("26.500")).toBe("26.5");
    expect(plainNumber("100")).toBe("100");
    expect(plainNumber(null)).toBe("");
  });

  it("builds the link to record a requirement, carrying where to come back to", () => {
    expect(newRequirementHref("line 1", "/work-orders/wo1", "Back to Work Order")).toBe(
      "/resource-requirements/new?work_order_line=line+1&returnTo=%2Fwork-orders%2Fwo1&returnLabel=Back+to+Work+Order",
    );
  });
});

describe("reading every requirement", () => {
  const pages = (total: number) => async (offset: number, limit: number) =>
    Array.from({ length: Math.max(0, Math.min(limit, total - offset)) }, (_, index) => offset + index);

  it("reads on past a full page until a page comes back short", async () => {
    const all = await fetchAllRequirementPages(pages(450), 200);
    expect(all).toHaveLength(450);
    expect(all[449]).toBe(449);
  });

  it("asks once more after an exactly full page, and stops at the empty one", async () => {
    const asked: number[] = [];
    const all = await fetchAllRequirementPages(async (offset, limit) => {
      asked.push(offset);
      return pages(400)(offset, limit);
    }, 200);
    expect(all).toHaveLength(400);
    expect(asked).toEqual([0, 200, 400]);
  });

  it("fails rather than show a partial list when there are more pages than it will read", async () => {
    await expect(fetchAllRequirementPages(async (_offset, limit) => Array.from({ length: limit }, () => 1), 1)).rejects.toThrow(
      "Too many requirements",
    );
  });

  it("passes a failed page's error on", async () => {
    await expect(
      fetchAllRequirementPages(async () => {
        throw new Error("HTTP 500");
      }),
    ).rejects.toThrow("HTTP 500");
  });
});

describe("answers that arrive out of order", () => {
  it("applies only the answer to the latest request", async () => {
    const latest = createLatestOnly();
    const shown: string[] = [];
    const answer = (value: string, delay: number) => new Promise<string>((resolve) => setTimeout(() => resolve(value), delay));
    async function ask(value: string, delay: number) {
      const ticket = latest.begin();
      const result = await answer(value, delay);
      if (latest.isLatest(ticket)) shown.push(result);
    }
    // The first filter is slow; the second answers first. Only the second may be shown.
    await Promise.all([ask("Open cranes", 30), ask("Cancelled platforms", 5)]);
    expect(shown).toEqual(["Cancelled platforms"]);
  });

  it("makes every earlier ticket stale", () => {
    const latest = createLatestOnly();
    const first = latest.begin();
    const second = latest.begin();
    expect(latest.isLatest(first)).toBe(false);
    expect(latest.isLatest(second)).toBe(true);
  });
});

describe("a moved start date", () => {
  it("knows a whole, real date", () => {
    expect(isCompleteIsoDate("2027-02-10")).toBe(true);
    expect(isCompleteIsoDate("2027-02-30")).toBe(false);
    expect(isCompleteIsoDate("2027-2-10")).toBe(false);
    expect(isCompleteIsoDate("")).toBe(false);
  });

  it("fills untouched crew from the Work Order's numbers on the new date, and leaves typed crew alone", () => {
    const form = formFromDefaults(defaults);
    const later = { crew_operators_required: 3, crew_helpers_required: 1 };
    const refreshed = formAfterLineDefaults(form, later, CREW_UNTOUCHED);
    expect([refreshed.crew_operators_required, refreshed.crew_helpers_required]).toEqual(["3", "1"]);
    // Unanswered on the new date: untouched numbers go back to empty rather than keep the earlier date's.
    const unanswered = formAfterLineDefaults(form, { crew_operators_required: null, crew_helpers_required: null }, CREW_UNTOUCHED);
    expect([unanswered.crew_operators_required, unanswered.crew_helpers_required]).toEqual(["", ""]);
  });

  it("keeps each typed crew number, and still moves the other one with the date (round 4, F-15)", () => {
    const form = formFromDefaults(defaults); // 2 operators, 0 helpers suggested
    const typedOperators = { ...form, crew_operators_required: "4" };
    const touched = crewTouchedAfterEdit(CREW_UNTOUCHED, form, typedOperators);
    expect(touched).toEqual({ operators: true, helpers: false });
    const later = formAfterLineDefaults(typedOperators, { crew_operators_required: 3, crew_helpers_required: 1 }, touched);
    expect([later.crew_operators_required, later.crew_helpers_required]).toEqual(["4", "1"]);
    // The other way round, and an untouched number cleared where the new date's crew is unanswered.
    const typedHelpers = { ...form, crew_helpers_required: "2" };
    const helpersTouched = crewTouchedAfterEdit(CREW_UNTOUCHED, form, typedHelpers);
    const unanswered = formAfterLineDefaults(typedHelpers, { crew_operators_required: null, crew_helpers_required: null }, helpersTouched);
    expect([unanswered.crew_operators_required, unanswered.crew_helpers_required]).toEqual(["", "2"]);
    // A typed number stays the user's own while they go on to edit other fields.
    const thenUnits = { ...typedOperators, units_required: "3" };
    expect(crewTouchedAfterEdit(touched, typedOperators, thenUnits)).toEqual({ operators: true, helpers: false });
  });
});

describe("the shifts a day the Work Order states (Slice 7D Part 5)", () => {
  it("says every stated count, singular for one, and nothing when the Work Order states none", () => {
    expect(shiftsPerDayText(1)).toBe("1 shift a day");
    expect(shiftsPerDayText(2)).toBe("2 shifts a day");
    expect(shiftsPerDayText(3)).toBe("3 shifts a day");
    expect(shiftsPerDayText(null)).toBeNull();
    expect(shiftsPerDayText(undefined)).toBeNull();
  });
});
