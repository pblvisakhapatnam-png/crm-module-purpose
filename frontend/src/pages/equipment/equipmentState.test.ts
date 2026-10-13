import { describe, expect, it } from "vitest";

import {
  INITIAL_MACHINE_FILTERS,
  INITIAL_MACHINE_STATE,
  INITIAL_PREVIEW_STATE,
  attentionRows,
  type EquipmentImport,
  type EquipmentModel,
  type ListUpdate,
  type Machine,
  type MachineAction,
  type MachineEvent,
  type MachineReferences,
  type MachineState,
  type PreviewAction,
  type PreviewRow,
  type PreviewState,
  type StructureCapability,
  canManageEquipment,
  capabilityText,
  capabilityValueProblem,
  confirmProblem,
  confirmedPairs,
  correctionProblem,
  correctionValuesText,
  createListController,
  createMachineLoader,
  detailFields,
  detailsPayload,
  createPreviewController,
  editingAfterLoad,
  flagLabel,
  initialListView,
  initialPairChoices,
  listView,
  machineQuery,
  machineReducer,
  modelFormProblem,
  modelPayload,
  modelSavedText,
  pairChoicesProblem,
  previewReducer,
  readableValues,
  reasonText,
  rowReadingLines,
  valueRuleFormFor,
  valueRulePayload,
  valueRuleProblem,
  type Structure,
  EMPTY_KIT_FORM,
  EMPTY_MODEL_FORM,
  assetName,
  classKindNote,
  craneModelChoices,
  detailsMissingText,
  isKitClass,
  kindChoices,
  kindLockedReason,
  kindProblem,
  kitFormProblem,
  kitModelsFor,
  kitPayload,
  machineFiltersFromSearch,
  piecesHeldText,
  retiredText,
  retireFormProblem,
  retirePayload,
  retirementText,
  takesKit,
} from "./equipmentState";

const TONNES: StructureCapability = {
  capability_code: "RATED_CAPACITY",
  capability_label: "Rated capacity",
  unit_code: "TONNE",
  unit_symbol: "t",
  whole_numbers_only: false,
  value_kind_code: "MINIMUM",
  allowed_values: null,
  is_key: true,
  is_active: true,
};
const AXLES: StructureCapability = { ...TONNES, capability_code: "AXLE_COUNT", capability_label: "Axles", unit_code: "COUNT", unit_symbol: "", whole_numbers_only: true, is_key: false };
const AXLE_CONFIGURATION: StructureCapability = {
  ...TONNES,
  capability_code: "AXLE_CONFIGURATION",
  capability_label: "Axle configuration",
  unit_code: null,
  unit_symbol: null,
  value_kind_code: "CHOICE",
  allowed_values: ["6X4", "8X4"],
  is_key: false,
};

const STRUCTURE: Structure = {
  taxonomy_version: 3,
  component_depth: 3,
  units: [{ unit_code: "KILOGRAM", unit_label: "kilogram", unit_symbol: "kg" }],
  classes: [
    {
      class_code: "CRANE",
      class_label: "Crane",
      class_kind_code: "MACHINE",
      tracking_code: "SINGLE",
      fits_class_codes: [],
      kit_for_class_codes: [],
      business_line_codes: ["HIRING"],
      is_active: true,
      types: [{ type_code: "CRAWLER", type_label: "Crawler", is_active: true }],
      capabilities: [TONNES],
    },
    {
      class_code: "PRIME_MOVER",
      class_label: "Prime Mover",
      class_kind_code: "MACHINE",
      tracking_code: "SINGLE",
      fits_class_codes: [],
      kit_for_class_codes: [],
      business_line_codes: ["TRANSPORTATION"],
      is_active: true,
      types: [],
      capabilities: [AXLES, AXLE_CONFIGURATION],
    },
    // ERT-2: a kind of kit, counted, kit for Crane.
    {
      class_code: "COUNTERWEIGHT",
      class_label: "Counterweight",
      class_kind_code: "PART",
      tracking_code: "COUNTED",
      fits_class_codes: [],
      kit_for_class_codes: ["CRANE"],
      business_line_codes: [],
      is_active: true,
      types: [],
      capabilities: [{ ...TONNES, capability_code: "WEIGHT", capability_label: "Weight" }],
    },
  ],
};

function previewImport(overrides: Partial<EquipmentImport> = {}): EquipmentImport {
  return {
    import_public_id: "i-1",
    import_status_code: "PREVIEWED",
    report_date: "2026-09-25",
    row_count: 2,
    fingerprint_prefix: "abc",
    uploaded_by_display_name: "Admin",
    uploaded_at: "2026-09-25T00:00:00Z",
    published_by_display_name: null,
    published_at: null,
    discard_reason_code: null,
    counts: { NEW: 2 },
    preview_version: 1,
    preview_computed_at: "2026-09-25T00:00:00Z",
    is_current: true,
    stale_reason: null,
    preview: {
      counts: { NEW: 2 },
      rows: [],
      missing: [],
      unmapped_model_names: [],
      closing_links: [],
      pair_proposals: [
        { part_machine_number: "C-1", proposed_machine_number: "M-1", candidates: [{ machine_number: "M-1", asset_reference: null }] },
        { part_machine_number: "C-2", proposed_machine_number: null, candidates: [{ machine_number: "M-1", asset_reference: null }] },
      ],
    },
    ...overrides,
  };
}

function row(overrides: Partial<PreviewRow>): PreviewRow {
  return {
    row_number: 3,
    machine_number: "M-1",
    outcome_code: "NEW",
    reason_code: null,
    asset_public_id: null,
    asset_reference: null,
    kind_code: "MACHINE",
    class_code: "CRANE",
    class_label: "Crane",
    type_code: null,
    type_label: null,
    model_public_id: null,
    model_label: null,
    status_code: "ACTIVE",
    changed_facts: [],
    flags: [],
    rules_applied: [],
    corrections: [],
    closing_links: [],
    plum: { category: "CRANES", model_name: null, capacity: "230 KG", commenced_year: "0", status: "Active" },
    needs_attention: true,
    ...overrides,
  };
}

function machine(version: number, publicId = "a-1"): Machine {
  return { asset_public_id: publicId, asset_version: version } as Machine;
}

function event(publicId: string): MachineEvent {
  return { public_id: publicId, event_name: "EQUIPMENT_ASSET_CHANGED", event_timestamp: "2026-09-25T00:00:00Z", reason: null };
}

/** A promise the test settles when it chooses, to answer requests out of order. */
function deferred<T>() {
  let resolve: (value: T) => void = () => undefined;
  const promise = new Promise<T>((settle) => {
    resolve = settle;
  });
  return { promise, resolve };
}

/** Lets every answer already given run to its end. */
const settle = () => new Promise((done) => setTimeout(done, 0));

describe("who may manage equipment", () => {
  it("is Admin only; the backend is the control", () => {
    expect(canManageEquipment(["ADMIN"])).toBe(true);
    expect(canManageEquipment(["OPERATIONS_USER", "SALES_MANAGER"])).toBe(false);
  });
});

describe("the machine list", () => {
  it("asks for exactly the filters shown", () => {
    const query = new URLSearchParams(machineQuery({ ...INITIAL_MACHINE_FILTERS, flaggedOnly: true, search: " TN 01 " }, 25, 25));
    expect(query.get("kind_code")).toBe("MACHINE");
    expect(query.get("status_code")).toBe("ACTIVE");
    expect(query.get("flagged_only")).toBe("true");
    expect(query.get("details_to_complete")).toBeNull();
    expect(query.get("search")).toBe("TN 01");
    expect(query.get("limit")).toBe("26");
    expect(query.get("offset")).toBe("25");
  });

  it("shows rows only as the answer to the request awaited", () => {
    let view = listView(initialListView<number>(), { kind: "rows", rows: [1, 2, 3], offset: 0 }, 2);
    expect(view).toMatchObject({ rows: [1, 2], hasNextPage: true, loading: false });
    view = listView(view, { kind: "loading", offset: 2 }, 2);
    expect(view.rows).toEqual([]);
    expect(view.loading).toBe(true);
    view = listView(view, { kind: "failed", message: "No." }, 2);
    expect(view).toMatchObject({ rows: [], error: "No.", loading: false });
  });

  it("applies only the latest answer, with the filters the controls show, and none after signing out", async () => {
    const shown: ListUpdate<string>[] = [];
    const resolvers: Array<(rows: string[]) => void> = [];
    let token: string | null = "t";
    const asked: string[] = [];
    const controller = createListController<{ kind: string }, string>({
      initialFilters: { kind: "MACHINE" },
      getToken: () => token,
      failure: "failed",
      fetchRows: (_token, filters) => {
        asked.push(filters.kind);
        return new Promise((resolve) => resolvers.push(resolve));
      },
      show: (update) => shown.push(update),
    });
    const first = controller.load(0);
    const second = controller.setFilters({ kind: "PART" });
    resolvers[1](["part"]);
    resolvers[0](["machine"]);
    await Promise.all([first, second]);
    expect(asked).toEqual(["MACHINE", "PART"]);
    expect(shown.filter((update) => update.kind === "rows")).toEqual([{ kind: "rows", rows: ["part"], offset: 0 }]);

    const third = controller.load(0);
    token = null;
    await controller.load(0);
    resolvers[2](["late"]);
    await third;
    expect(shown.at(-1)).toEqual({ kind: "signed-out" });
    expect(shown.some((update) => update.kind === "rows" && update.rows.includes("late"))).toBe(false);
  });
});

describe("words", () => {
  it("names a flag and its subject", () => {
    expect(flagLabel({ flag_code: "DIFFERS_FROM_MODEL", subject_code: "RATED_CAPACITY" }, { RATED_CAPACITY: "Rated capacity" })).toBe(
      "Plum's figure differs from the rating: rated capacity",
    );
    expect(flagLabel({ flag_code: "OUT_OF_PATTERN", subject_code: "COMMENCED_YEAR" })).toBe("Plum's value is outside what is plausible: commenced year");
    expect(flagLabel({ flag_code: "MODEL_NOT_MAPPED", subject_code: "" })).toBe("Model name not mapped to a model yet");
  });

  it("says a correction's values are Admin's only when they are withheld, and never shows them", () => {
    expect(correctionValuesText({ plum_value: null, corrected_value_label: null, values_withheld: true })).toBe(
      "Shown to Admin only: Plum's value and the correct one.",
    );
    expect(correctionValuesText({ plum_value: "E-1", corrected_value_label: "E-2", values_withheld: false })).toBe("Plum has E-1; read as E-2.");
    expect(correctionValuesText({ plum_value: null, corrected_value_label: "Crane", values_withheld: false })).toBe("Plum has nothing; read as Crane.");
    // The reason goes with the values: it may repeat the numbers.
    expect(reasonText(null)).toBe("The reason is shown to Admin only.");
    expect(reasonText("Typo in Plum.")).toBe("Typo in Plum.");
  });

  it("writes a capability in its unit", () => {
    expect(capabilityText({ ...TONNES, value: "100.000", choice_value: null })).toBe("Rated capacity 100 t");
    expect(capabilityText({ ...AXLE_CONFIGURATION, value: null, choice_value: "8X4" })).toBe("Axle configuration 8X4");
    expect(capabilityText(null)).toBe("-");
  });
});

describe("the models page", () => {
  it("closes a model's form when a newer version of it is loaded, and keeps a current or new one open", () => {
    const model = { model_public_id: "m-1", model_version: 1 } as EquipmentModel;
    expect(editingAfterLoad(model, [{ ...model, model_version: 2 }])).toEqual({ editing: null, closedAsStale: true });
    expect(editingAfterLoad(model, [model])).toEqual({ editing: model, closedAsStale: false });
    expect(editingAfterLoad("new", [])).toEqual({ editing: "new", closedAsStale: false });
    expect(editingAfterLoad(null, [model])).toEqual({ editing: null, closedAsStale: false });
  });

  it("says a save the server already had from the form was saved, not that nothing changed (TB-1 TB1-102 b)", () => {
    expect(modelSavedText({ event: null, replayed: true })).toBe("Already saved: nothing more was recorded.");
    expect(modelSavedText({ event: { event_name: "EQUIPMENT_MODEL_RECORDED" }, replayed: false })).toBe("Model saved.");
    expect(modelSavedText({ event: null, replayed: false })).toBe("Nothing changed, so nothing was saved.");
    // A change's answer carries no `replayed` flag to read.
    expect(modelSavedText({ event: null })).toBe("Nothing changed, so nothing was saved.");
  });
});

describe("forms", () => {
  it("takes a capability value above zero, up to three decimals, whole where counted, a choice from its list", () => {
    expect(capabilityValueProblem(TONNES, "100.5")).toBeNull();
    expect(capabilityValueProblem(TONNES, "0")).not.toBeNull();
    expect(capabilityValueProblem(TONNES, "1.2345")).not.toBeNull();
    expect(capabilityValueProblem(TONNES, "ten")).not.toBeNull();
    expect(capabilityValueProblem(AXLES, "6.5")).toBe("Axles is counted in whole numbers.");
    expect(capabilityValueProblem(AXLE_CONFIGURATION, "8X4")).toBeNull();
    expect(capabilityValueProblem(AXLE_CONFIGURATION, "4X2")).not.toBeNull();
  });

  it("builds a model without a unit and without the blank capabilities", () => {
    const form = {
      maker: " ACME ",
      modelName: "AC 100",
      classCode: "PRIME_MOVER",
      typeCode: "",
      values: { AXLE_COUNT: "3", AXLE_CONFIGURATION: "" },
      isRetired: false,
      makerPartNumber: "",
      // A machine model fits nothing, whatever the form was left holding.
      fitsModelIds: ["left-over"],
    };
    expect(modelFormProblem(form, STRUCTURE)).toBeNull();
    expect(modelPayload(form, STRUCTURE)).toEqual({
      maker: "ACME",
      model_name: "AC 100",
      class_code: "PRIME_MOVER",
      type_code: null,
      capabilities: [{ capability_code: "AXLE_COUNT", value: "3", choice_value: null }],
      maker_part_number: null,
      fits_model_public_ids: [],
    });
    expect(modelFormProblem({ ...form, values: { AXLE_COUNT: "3.5" } }, STRUCTURE)).toBe("Axles is counted in whole numbers.");
    expect(modelFormProblem({ ...form, maker: " " }, STRUCTURE)).not.toBeNull();
  });

  it("offers a reading only for the values a flag is about, and sends only what the reading carries", () => {
    const flagged = row({ flags: [{ flag_code: "NOT_A_NUMBER", subject_code: "PLATFORM_CAPACITY" }, { flag_code: "OUT_OF_PATTERN", subject_code: "COMMENCED_YEAR" }] });
    expect(readableValues(flagged)).toEqual([
      { columnCode: "CAPACITY", plumValue: "230 KG" },
      { columnCode: "COMMENCED_YEAR", plumValue: "0" },
    ]);
    expect(readableValues(row({ flags: [{ flag_code: "MODEL_NOT_MAPPED", subject_code: "" }] }))).toEqual([]);

    const form = { ...valueRuleFormFor("CAPACITY", "230 KG"), resultNumber: "230", resultUnitCode: "KILOGRAM", resultClassCode: "CRANE" };
    expect(valueRuleProblem(form)).toBe("Give the reason for reading the value this way.");
    const payload = valueRulePayload({ ...form, reason: " Kilograms. " }, "i-1");
    expect(payload).toMatchObject({ action_code: "SPLIT_NUMBER_AND_UNIT", result_number: "230", result_unit_code: "KILOGRAM", result_class_code: null, reason: "Kilograms.", import_public_id: "i-1" });
    expect(valueRuleFormFor("COMMENCED_YEAR", "0").actionCode).toBe("NOT_A_VALUE");
  });

  it("checks a correction before sending it", () => {
    expect(correctionProblem("", "x", "r")).not.toBeNull();
    expect(correctionProblem("COMMENCED_YEAR", "15", "r")).toBe("Give the commenced year as four digits.");
    expect(correctionProblem("CAPACITY", "80 t", "r")).toBe("Give the capacity as a plain number.");
    expect(correctionProblem("ENGINE_NUMBER", "E-1", " ")).toBe("Give the reason for the correction.");
    expect(correctionProblem("ENGINE_NUMBER", "E-1", "Typo in Plum.")).toBeNull();
  });
});

describe("the preview page", () => {
  it("installs only the load awaited, and a newly installed preview starts its pair choices again", () => {
    let state = previewReducer(INITIAL_PREVIEW_STATE, { type: "load-started", ticket: 1, publicId: "i-1" });
    state = previewReducer(state, { type: "load-started", ticket: 2, publicId: "i-1" });
    state = previewReducer(state, { type: "loaded", ticket: 1, equipmentImport: previewImport({ preview_version: 1 }) });
    expect(state.equipmentImport).toBeNull();
    state = previewReducer(state, { type: "loaded", ticket: 2, equipmentImport: previewImport({ preview_version: 2 }) });
    expect(state.equipmentImport?.preview_version).toBe(2);
    expect(state.pairs["C-1"]).toEqual({ machineNumber: "M-1", confirmed: false });

    state = previewReducer(state, { type: "pair-changed", part: "C-1", choice: { machineNumber: "M-1", confirmed: true } });
    state = previewReducer(state, { type: "item-recorded", publicId: "i-1", key: "map:X", text: "Mapped." });
    expect(state.changedSinceComputed).toBe(true);
    // A refresh replaces the preview and every choice made on the one before it.
    state = previewReducer(state, { type: "action-started", publicId: "i-1", ticket: 7 });
    state = previewReducer(state, { type: "refreshed", ticket: 7, equipmentImport: previewImport({ preview_version: 3 }) });
    expect(state.pendingAction).toBeNull();
    expect(state.changedSinceComputed).toBe(false);
    expect(state.pairs["C-1"].confirmed).toBe(false);
    // A load asked before the refresh cannot put the older preview back.
    state = previewReducer(state, { type: "loaded", ticket: 2, equipmentImport: previewImport({ preview_version: 2 }) });
    expect(state.equipmentImport?.preview_version).toBe(3);
  });

  it("offers Confirm only for a current preview with nothing changed since, and no machine chosen twice", () => {
    const loaded = previewReducer(
      previewReducer(INITIAL_PREVIEW_STATE, { type: "load-started", ticket: 1, publicId: "i-1" }),
      { type: "loaded", ticket: 1, equipmentImport: previewImport() },
    );
    expect(confirmProblem(loaded)).toBeNull();
    expect(confirmProblem({ ...loaded, changedSinceComputed: true })).toContain("Refresh the preview");
    expect(confirmProblem({ ...loaded, equipmentImport: previewImport({ is_current: false, stale_reason: "Another report was confirmed." }) })).toBe(
      "Another report was confirmed.",
    );
    expect(confirmProblem({ ...loaded, equipmentImport: previewImport({ import_status_code: "PUBLISHED" }) })).not.toBeNull();
    const twice = {
      ...loaded,
      pairs: { "C-1": { machineNumber: "M-1", confirmed: true }, "C-2": { machineNumber: "M-1", confirmed: true } },
    };
    expect(confirmProblem(twice)).toBe("M-1 is chosen for two parts. Choose one part for it.");
    expect(pairChoicesProblem({ "C-1": { machineNumber: "M-1", confirmed: false }, "C-2": { machineNumber: "M-1", confirmed: true } })).toBeNull();
  });

  it("words every correction and reading a row was read with, never repeating an engine or chassis number", () => {
    const corrected = row({
      needs_attention: true,
      corrections: [
        { correction_public_id: "c-1", field_code: "CATEGORY", effect_code: "APPLIED", corrected_value_label: "Crane" },
        { correction_public_id: "c-2", field_code: "OWNING_COMPANY", effect_code: "PLUM_AGREES", corrected_value_label: "PBL" },
        { correction_public_id: "c-3", field_code: "ENGINE_NUMBER", effect_code: "PLUM_CHANGED", corrected_value_label: null },
      ],
      rules_applied: [
        { rule_public_id: "r-1", column_code: "CAPACITY", action_code: "SPLIT_NUMBER_AND_UNIT", plum_value: "230 KG", result_number: "230.000", result_unit_code: "KILOGRAM", result_class_code: null, result_type_code: null },
        { rule_public_id: "r-2", column_code: "CHASSIS_NUMBER", action_code: "NOT_A_VALUE", plum_value: null, result_number: null, result_unit_code: null, result_class_code: null, result_type_code: null },
        { rule_public_id: "r-3", column_code: "CAPACITY", action_code: "REASSIGN_TO_TYPE", plum_value: "CRAWLER", result_number: null, result_unit_code: null, result_class_code: "CRANE", result_type_code: "CRAWLER" },
      ],
    });
    expect(rowReadingLines(corrected, STRUCTURE)).toEqual([
      "Kind of machine (Plum's category): corrected as Crane, not as Plum holds it.",
      "Owning company: Plum now holds the corrected value, so the correction closes when this report is confirmed.",
      "Engine number: Plum now holds another value. The correction still applies; keep it or close it on the machine's page.",
      'Capacity figure (for the check): "230 KG" read as 230 kg.',
      "Chassis number: Plum's value read as nothing entered.",
      'Capacity figure (for the check): "CRAWLER" read as naming a type, Crane - Crawler.',
    ]);
    // Shown by default even with no flag left: the backend marks such a row as needing attention.
    expect(attentionRows({ ...previewImport().preview, rows: [corrected, row({ needs_attention: false })] }, false)).toEqual([corrected]);
    expect(rowReadingLines(row({}), STRUCTURE)).toEqual([]);
    // A fitted part the report will take off its machine, from either end.
    const link = { machine_asset_public_id: "m-1", machine_machine_number: "M-1", part_asset_public_id: "p-1", part_machine_number: "C-1", because: "CLASS_CHANGED" };
    expect(rowReadingLines(row({ asset_public_id: "m-1", closing_links: [link] }), STRUCTURE)).toEqual([
      "C-1 will be taken off it: after this report the two no longer fit together.",
    ]);
    expect(rowReadingLines(row({ asset_public_id: "p-1", closing_links: [link] }), STRUCTURE)).toEqual([
      "Will be taken off M-1: after this report the two no longer fit together.",
    ]);
  });

  it("shows one import only under its own address, and no earlier copy of it over a later one", async () => {
    let state: PreviewState = INITIAL_PREVIEW_STATE;
    const dispatch = (action: PreviewAction) => {
      state = previewReducer(state, action);
    };
    const imports: Record<string, ReturnType<typeof deferred<EquipmentImport>>> = { "i-1": deferred(), "i-2": deferred() };
    const refresh = deferred<{ equipment_import: EquipmentImport; replayed: boolean }>();
    const controller = createPreviewController({
      getToken: () => "t",
      fetchImport: (_token, publicId) => imports[publicId].promise,
      sendAction: () => refresh.promise,
      dispatch,
    });

    // Import i-1 is shown, a pair is chosen, and a refresh is asked for.
    const first = controller.load("i-1");
    imports["i-1"].resolve(previewImport({ preview_version: 1 }));
    await first;
    dispatch({ type: "pair-changed", part: "C-1", choice: { machineNumber: "M-1", confirmed: true } });
    const refreshing = controller.act("refresh", state.equipmentImport as EquipmentImport, state.pairs);
    expect(state.pendingAction).not.toBeNull();

    // The page moves to i-2 before the refresh answers: i-1 and its choices go at once.
    const second = controller.load("i-2");
    expect(state.equipmentImport).toBeNull();
    expect(state.pendingAction).toBeNull();
    expect(state.pairs).toEqual({});
    imports["i-2"].resolve(previewImport({ import_public_id: "i-2", preview_version: 1 }));
    await second;
    // i-1's refresh answers late, and a mapping recorded from i-1's page answers too: neither lands on i-2.
    refresh.resolve({ equipment_import: previewImport({ preview_version: 2 }), replayed: false });
    await refreshing;
    dispatch({ type: "item-recorded", publicId: "i-1", key: "map:X", text: "Mapped." });
    expect(state.equipmentImport?.import_public_id).toBe("i-2");
    expect(state.actionFeedback).toBeNull();
    expect(state.changedSinceComputed).toBe(false);
    expect(state.pendingAction).toBeNull();

    // On one import, answers arrive in any order: the later copy stands.
    dispatch({ type: "load-started", ticket: 99, publicId: "i-2" });
    dispatch({ type: "action-started", publicId: "i-2", ticket: 50 });
    dispatch({ type: "refreshed", ticket: 50, equipmentImport: previewImport({ import_public_id: "i-2", preview_version: 3 }) });
    dispatch({ type: "pair-changed", part: "C-1", choice: { machineNumber: "M-1", confirmed: true } });
    dispatch({ type: "loaded", ticket: 99, equipmentImport: previewImport({ import_public_id: "i-2", preview_version: 2 }) });
    expect(state.equipmentImport?.preview_version).toBe(3);
    expect(state.pairs["C-1"].confirmed).toBe(true);
    // The same copy, read again, keeps the choices made on it but says whether it is still current.
    dispatch({ type: "load-started", ticket: 100, publicId: "i-2" });
    dispatch({ type: "loaded", ticket: 100, equipmentImport: previewImport({ import_public_id: "i-2", preview_version: 3, is_current: false, stale_reason: "Another report was confirmed." }) });
    expect(state.pairs["C-1"].confirmed).toBe(true);
    expect(confirmProblem(state)).toBe("Another report was confirmed.");
    // A confirmation is later than any preview of the same version: a preview read after it cannot come back.
    dispatch({ type: "action-started", publicId: "i-2", ticket: 51 });
    dispatch({ type: "published", ticket: 51, equipmentImport: previewImport({ import_public_id: "i-2", preview_version: 3, import_status_code: "PUBLISHED" }), replayed: false });
    dispatch({ type: "load-started", ticket: 101, publicId: "i-2" });
    dispatch({ type: "loaded", ticket: 101, equipmentImport: previewImport({ import_public_id: "i-2", preview_version: 3 }) });
    expect(state.equipmentImport?.import_status_code).toBe("PUBLISHED");
  });

  it("lets only the awaited action give the message and unlock the buttons, and no load unlock them", () => {
    let state = previewReducer(INITIAL_PREVIEW_STATE, { type: "load-started", ticket: 1, publicId: "i-1" });
    state = previewReducer(state, { type: "loaded", ticket: 1, equipmentImport: previewImport({ preview_version: 1 }) });
    // A refresh (1) is left waiting; the page is left and opened again, and the import is confirmed (2).
    state = previewReducer(state, { type: "action-started", publicId: "i-1", ticket: 1 });
    state = previewReducer(state, { type: "load-started", ticket: 2, publicId: "i-9" });
    state = previewReducer(state, { type: "load-started", ticket: 3, publicId: "i-1" });
    state = previewReducer(state, { type: "loaded", ticket: 3, equipmentImport: previewImport({ preview_version: 2 }) });
    state = previewReducer(state, { type: "action-started", publicId: "i-1", ticket: 2 });
    // A reload finishing while the confirmation is awaited unlocks nothing.
    state = previewReducer(state, { type: "load-started", ticket: 4, publicId: "i-1" });
    state = previewReducer(state, { type: "loaded", ticket: 4, equipmentImport: previewImport({ preview_version: 2 }) });
    expect(state.pendingAction).toBe(2);
    state = previewReducer(state, { type: "published", ticket: 2, equipmentImport: previewImport({ preview_version: 2, import_status_code: "PUBLISHED" }), replayed: false });
    expect(state.actionFeedback).toEqual({ kind: "success", text: "Report confirmed. The machines are updated." });
    // The old refresh answers now - as a success, or as a refusal: neither changes anything.
    const late = previewReducer(state, { type: "refreshed", ticket: 1, equipmentImport: previewImport({ preview_version: 3 }) });
    expect(late).toBe(state);
    expect(previewReducer(state, { type: "action-refused", publicId: "i-1", ticket: 1, text: "Refused." }).actionFeedback).toEqual(state.actionFeedback);

    // While a newer action is awaited, an older one's answer does not unlock the buttons.
    let waiting = previewReducer(state, { type: "action-started", publicId: "i-1", ticket: 3 });
    waiting = previewReducer(waiting, { type: "action-refused", publicId: "i-1", ticket: 1, text: "Refused." });
    expect(waiting.pendingAction).toBe(3);
    expect(waiting.actionFeedback).toBeNull();
  });

  it("ignores an old action's answer of the same copy after the import was left, opened again and changed", () => {
    let state = previewReducer(INITIAL_PREVIEW_STATE, { type: "load-started", ticket: 1, publicId: "i-1" });
    state = previewReducer(state, { type: "loaded", ticket: 1, equipmentImport: previewImport({ preview_version: 1 }) });
    state = previewReducer(state, { type: "action-started", publicId: "i-1", ticket: 1 });
    // Left and opened again: the refresh has made version 2, which the reload shows.
    state = previewReducer(state, { type: "load-started", ticket: 2, publicId: "i-9" });
    state = previewReducer(state, { type: "load-started", ticket: 3, publicId: "i-1" });
    state = previewReducer(state, { type: "loaded", ticket: 3, equipmentImport: previewImport({ preview_version: 2, is_current: false, stale_reason: "Refresh it." }) });
    state = previewReducer(state, { type: "pair-changed", part: "C-1", choice: { machineNumber: "M-1", confirmed: true } });
    state = previewReducer(state, { type: "item-recorded", publicId: "i-1", key: "map:X", text: "Mapped." });
    // The old refresh's answer - the same version 2, but said to be current - changes nothing.
    const after = previewReducer(state, { type: "refreshed", ticket: 1, equipmentImport: previewImport({ preview_version: 2, is_current: true }) });
    expect(after).toBe(state);
    expect(after.changedSinceComputed).toBe(true);
    expect(after.pairs["C-1"].confirmed).toBe(true);
    expect(confirmProblem(after)).not.toBeNull();
  });

  it("sends only the pairs confirmed", () => {
    const choices = initialPairChoices(previewImport().preview);
    expect(confirmedPairs(choices)).toEqual([]);
    expect(confirmedPairs({ ...choices, "C-1": { machineNumber: "M-1", confirmed: true } })).toEqual([{ part_machine_number: "C-1", machine_machine_number: "M-1" }]);
  });
});

describe("the machine page", () => {
  it("lets a save install a newer version that no older load can replace, and closes every form", () => {
    let state = machineReducer(INITIAL_MACHINE_STATE, { type: "load-started", ticket: 1, publicId: "a-1" });
    state = machineReducer(state, { type: "loaded", ticket: 1, machine: machine(1), view: 1 });
    state = machineReducer(state, { type: "form-opened", form: "correction" });
    state = machineReducer(state, { type: "save-started", publicId: "a-1", ticket: 1 });
    state = machineReducer(state, { type: "load-started", ticket: 2, publicId: "a-1" });
    state = machineReducer(state, { type: "saved", ticket: 1, machine: machine(2), key: "corrections", text: "Saved.", view: 2 });
    expect(state.pendingSave).toBeNull();
    expect(state.openForm).toBeNull();
    expect(state.feedback.corrections).toEqual({ kind: "success", text: "Saved." });
    state = machineReducer(state, { type: "loaded", ticket: 2, machine: machine(1), view: 3 });
    expect(state.machine?.asset_version).toBe(2);
  });

  it("stops showing one machine the moment another is asked for, and keeps it while the same one reloads", () => {
    let state = machineReducer(INITIAL_MACHINE_STATE, { type: "load-started", ticket: 1, publicId: "a-1" });
    state = machineReducer(state, { type: "loaded", ticket: 1, machine: machine(1), view: 1 });
    expect(machineReducer(state, { type: "load-started", ticket: 2, publicId: "a-1" }).machine?.asset_public_id).toBe("a-1");
    state = machineReducer(state, { type: "load-started", ticket: 2, publicId: "b-2" });
    expect(state.machine).toBeNull();
    expect(state.latestLoad).toBe(2);
  });

  it("shows a machine's events only under that machine, and only from the latest request", async () => {
    const actions: MachineAction[] = [];
    const shown: MachineEvent[][] = [];
    const machines: Record<string, ReturnType<typeof deferred<Machine>>> = { "a-1": deferred(), "b-2": deferred() };
    const eventAnswers: Array<{ publicId: string; answer: ReturnType<typeof deferred<MachineEvent[]>> }> = [];
    const loader = createMachineLoader({
      getToken: () => "t",
      fetchMachine: (_token, publicId) => machines[publicId].promise,
      fetchEvents: (_token, publicId) => {
        const answer = deferred<MachineEvent[]>();
        eventAnswers.push({ publicId, answer });
        return answer.promise;
      },
      dispatch: (action) => actions.push(action),
      showEvents: (events) => shown.push(events),
    });

    // The page opens machine a-1, then moves to b-2 before a-1 answers.
    const first = loader.load("a-1");
    const second = loader.load("b-2");
    machines["b-2"].resolve(machine(1, "b-2"));
    machines["a-1"].resolve(machine(1, "a-1"));
    await settle();
    // a-1's late answer installs nothing and asks for no events.
    expect(actions.filter((action) => action.type === "loaded").map((action) => action.type === "loaded" && action.machine.asset_public_id)).toEqual(["b-2"]);
    expect(eventAnswers.map((item) => item.publicId)).toEqual(["b-2"]);
    // Each load cleared the events shown before it.
    expect(shown).toEqual([[], []]);
    eventAnswers[0].answer.resolve([event("e-b")]);
    await Promise.all([first, second]);
    expect(shown.at(-1)).toEqual([event("e-b")]);

    // b-2's events are asked for again; a-1 is opened before they answer: they are not shown under a-1.
    machines["a-1"] = deferred();
    const reload = loader.load("b-2");
    await settle();
    const moved = loader.load("a-1");
    eventAnswers[1].answer.resolve([event("e-b-late")]);
    await reload;
    expect(shown.at(-1)).toEqual([]);

    // A save answered for b-2 after the page moved to a-1 installs nothing there.
    await loader.saved(1, machine(2, "b-2"), "details", "Saved.");
    expect(actions.some((action) => action.type === "saved")).toBe(false);
    machines["a-1"].resolve(machine(4, "a-1"));
    await settle();
    expect(actions.at(-1)).toMatchObject({ type: "loaded", machine: { asset_public_id: "a-1" } });
    expect(eventAnswers.at(-1)?.publicId).toBe("a-1");
    eventAnswers.at(-1)?.answer.resolve([event("e-a")]);
    await moved;
    expect(shown.at(-1)).toEqual([event("e-a")]);
  });

  it("never lets an earlier version replace a later one, whichever of a save and a reload answers first", async () => {
    function page(): { state: () => MachineState; loader: ReturnType<typeof createMachineLoader>; reload: ReturnType<typeof deferred<Machine>> } {
      let state = INITIAL_MACHINE_STATE;
      const reload = deferred<Machine>();
      const answers = [Promise.resolve(machine(1))];
      const loader = createMachineLoader({
        getToken: () => "t",
        fetchMachine: () => answers.shift() ?? reload.promise,
        fetchEvents: async () => [],
        dispatch: (action) => {
          state = machineReducer(state, action);
        },
        showEvents: () => undefined,
      });
      return { state: () => state, loader, reload };
    }

    // A save committed version 2 but its answer is late; someone else makes version 3, and Reload reads it.
    const late = page();
    await late.loader.load("a-1");
    const lateSave = late.loader.beginSave("a-1");
    const reloading = late.loader.load("a-1");
    late.reload.resolve(machine(3));
    await reloading;
    expect(late.state().pendingSave).toBe(lateSave);
    await late.loader.saved(lateSave, machine(2), "details", "Details saved.");
    expect(late.state().machine?.asset_version).toBe(3);
    expect(late.state().feedback.details).toEqual({ kind: "success", text: "Details saved." });

    // The other order: the save answers first, and the reload begun meanwhile still brings version 3.
    const early = page();
    await early.loader.load("a-1");
    const earlySave = early.loader.beginSave("a-1");
    const reloadingAgain = early.loader.load("a-1");
    await early.loader.saved(earlySave, machine(2), "details", "Details saved.");
    expect(early.state().machine?.asset_version).toBe(2);
    early.reload.resolve(machine(3));
    await reloadingAgain;
    expect(early.state().machine?.asset_version).toBe(3);
  });

  it("a load older than a save changes nothing, and a load without a session says so", async () => {
    const actions: MachineAction[] = [];
    const answer = deferred<Machine>();
    let token: string | null = "t";
    let state = INITIAL_MACHINE_STATE;
    const loader = createMachineLoader({
      getToken: () => token,
      fetchMachine: () => answer.promise,
      fetchEvents: async () => [],
      dispatch: (action) => {
        actions.push(action);
        state = machineReducer(state, action);
      },
      showEvents: () => undefined,
    });
    const loading = loader.load("a-1");
    await loader.saved(loader.beginSave("a-1"), machine(5), "details", "Saved.");
    answer.resolve(machine(4));
    await loading;
    expect(state.machine?.asset_version).toBe(5);
    expect(state.feedback.details).toEqual({ kind: "success", text: "Saved." });

    token = null;
    await loader.load("a-1");
    expect(actions.at(-1)).toMatchObject({ type: "load-failed", text: "Sign in first. No active session was found." });
  });

  it("shows a refused save only on the page of the machine it was made on, and only the awaited one", async () => {
    let state = INITIAL_MACHINE_STATE;
    const answers: Record<string, Machine> = { "a-1": machine(1, "a-1"), "b-2": machine(1, "b-2") };
    const loader = createMachineLoader({
      getToken: () => "t",
      fetchMachine: async (_token, publicId) => answers[publicId],
      fetchEvents: async () => [],
      dispatch: (action) => {
        state = machineReducer(state, action);
      },
      showEvents: () => undefined,
    });
    await loader.load("a-1");
    const onA = loader.beginSave("a-1");
    expect(state.pendingSave).toBe(onA);
    // The page moves to b-2 before a-1's save answers; b-2's own save starts.
    await loader.load("b-2");
    expect(state.pendingSave).toBeNull();
    const onB = loader.beginSave("b-2");
    // a-1's refusal - a 409, a 422, a lost connection - arrives: nothing of it shows on b-2.
    loader.refused(onA, "a-1", "details", "Someone else changed this machine.");
    expect(state.feedback).toEqual({});
    expect(state.pendingSave).toBe(onB);
    // b-2's own refusal shows beside its form and unlocks it.
    loader.refused(onB, "b-2", "details", "Give the year as four digits.");
    expect(state.feedback.details).toEqual({ kind: "error", text: "Give the year as four digits." });
    expect(state.pendingSave).toBeNull();
  });

  it("a reload discards an open form made against the version before it", () => {
    let state = machineReducer(INITIAL_MACHINE_STATE, { type: "load-started", ticket: 1, publicId: "a-1" });
    state = machineReducer(state, { type: "loaded", ticket: 1, machine: machine(1), view: 1 });
    state = machineReducer(state, { type: "form-opened", form: "details" });
    state = machineReducer(state, { type: "load-started", ticket: 2, publicId: "a-1" });
    state = machineReducer(state, { type: "loaded", ticket: 2, machine: machine(3), view: 2 });
    expect(state.openForm).toBeNull();
    expect(state.machine?.asset_version).toBe(3);
  });

  it("between two answers of one version, shows the one asked for later: kit changes without the version (ERT2-R1-002)", () => {
    const withKit = (held: number) => ({ ...machine(1), kit: [{ pieces_held: held }] }) as unknown as Machine;
    let state = machineReducer(INITIAL_MACHINE_STATE, { type: "load-started", ticket: 1, publicId: "a-1" });
    state = machineReducer(state, { type: "loaded", ticket: 1, machine: withKit(0), view: 1 });
    // Kit is added (the save, view 2) and the machine read again (view 3); a reload is asked for after that (view 4).
    state = machineReducer(state, { type: "save-started", publicId: "a-1", ticket: 1 });
    state = machineReducer(state, { type: "load-started", ticket: 2, publicId: "a-1" });
    state = machineReducer(state, { type: "loaded", ticket: 2, machine: withKit(4), view: 4 });
    // The read after the add arrives last: its message shows, its older kit does not replace the later one.
    state = machineReducer(state, { type: "saved", ticket: 1, machine: withKit(2), key: "kit", text: "Added.", view: 3 });
    expect(state.machine?.kit).toEqual([{ pieces_held: 4 }]);
    expect(state.feedback.kit).toEqual({ kind: "success", text: "Added." });
    expect(state.pendingSave).toBeNull();
    // A later answer of the same version still replaces it.
    state = machineReducer(state, { type: "load-started", ticket: 3, publicId: "a-1" });
    state = machineReducer(state, { type: "loaded", ticket: 3, machine: withKit(5), view: 5 });
    expect(state.machine?.kit).toEqual([{ pieces_held: 5 }]);
  });

  it("shows the structure and models only of the latest load, whichever answers last (ERT2-R4-004)", async () => {
    const references: Record<string, ReturnType<typeof deferred<MachineReferences>>> = { "a-1": deferred(), "b-2": deferred() };
    const asked: string[] = [];
    const shown: MachineReferences[] = [];
    let current = "";
    const loader = createMachineLoader({
      getToken: () => "t",
      fetchMachine: async (_token, publicId) => machine(1, publicId),
      fetchEvents: async () => [],
      dispatch: () => undefined,
      showEvents: () => undefined,
      fetchReferences: () => {
        asked.push(current);
        return references[current].promise;
      },
      showReferences: (answer) => shown.push(answer),
    });
    current = "a-1";
    const onA = loader.load("a-1");
    // A's machine answers and is shown; its structure and models are still on their way when B is opened.
    await settle();
    current = "b-2";
    const onB = loader.load("b-2");
    const forB = { structure: STRUCTURE, models: [model({ model_public_id: "for-b" })] };
    references["b-2"].resolve(forB);
    await onB;
    references["a-1"].resolve({ structure: STRUCTURE, models: [model({ model_public_id: "for-a" })] });
    await onA;
    expect(asked).toEqual(["a-1", "b-2"]);
    expect(shown).toEqual([forB]);
  });

  it("orders every view the page asks for by when it was asked: loads, saves, and the read after adding kit", async () => {
    const actions: MachineAction[] = [];
    const answer = deferred<Machine>();
    const loader = createMachineLoader({
      getToken: () => "t",
      fetchMachine: () => answer.promise,
      fetchEvents: async () => [],
      dispatch: (action) => actions.push(action),
      showEvents: () => undefined,
    });
    const loading = loader.load("a-1");
    answer.resolve(machine(1));
    await loading;
    const save = loader.beginSave("a-1");
    const readAgain = loader.beginView();
    await loader.saved(save, machine(1), "kit", "Added.", readAgain);
    await loader.saved(save, machine(2), "details", "Saved.");
    const views = actions.flatMap((action) => (action.type === "loaded" || action.type === "saved" ? [action.view] : []));
    // The load first; the read after the add, asked for after its save began; a save's own answer at its start.
    expect(views).toEqual([1, 3, 2]);
  });
});

// --- Detachable kit (ERT-2) ---------------------------------------------------------------------------------

function model(overrides: Partial<EquipmentModel>): EquipmentModel {
  return {
    model_public_id: "m",
    maker: "ACME",
    model_name: "X",
    label: "ACME X",
    class_code: "CRANE",
    class_label: "Crane",
    class_kind_code: "MACHINE",
    type_code: null,
    type_label: null,
    maker_part_number: null,
    capabilities: [],
    mapped_names: [],
    machine_count: 0,
    is_kit: false,
    fits_models: [],
    pieces_held: 0,
    fits_no_active_crane: false,
    active_unit_count: 0,
    model_version: 1,
    is_retired: false,
    ...overrides,
  };
}

describe("detachable kit", () => {
  const counterweight = STRUCTURE.classes.find((item) => item.class_code === "COUNTERWEIGHT");
  const crane = STRUCTURE.classes.find((item) => item.class_code === "CRANE");

  it("knows a kind of kit and says so where models are chosen", () => {
    expect(isKitClass(counterweight)).toBe(true);
    expect(isKitClass(crane)).toBe(false);
    expect(classKindNote(counterweight!)).toBe(" (kit)");
    expect(classKindNote(crane!)).toBe("");
  });

  it("shows a kit section only on a kind of machine the structure gives kit to (ERT2-R1-003)", () => {
    expect(takesKit(STRUCTURE, "CRANE")).toBe(true);
    expect(takesKit(STRUCTURE, "FORKLIFT")).toBe(false);
    expect(takesKit(STRUCTURE, "COUNTERWEIGHT")).toBe(false);
    expect(takesKit(null, "CRANE")).toBe(false);
  });

  it("says what a retirement did: the whole record, or some pieces of a set that stays (ERT2-R1-004)", () => {
    expect(retiredText({ quantity: 1 }, { quantity: 1, asset_status_code: "RETIRED" })).toBe("Retired. Its history is kept.");
    expect(retiredText({ quantity: 6 }, { quantity: 6, asset_status_code: "RETIRED" })).toBe("Retired. Its history is kept.");
    expect(retiredText({ quantity: 6 }, { quantity: 4, asset_status_code: "ACTIVE" })).toBe("2 pieces retired from the set; 4 left in it. Its history is kept.");
    expect(retiredText({ quantity: 6 }, { quantity: 5, asset_status_code: "ACTIVE" })).toBe("1 piece retired from the set; 5 left in it. Its history is kept.");
  });

  it("does not offer a kind of kit to a model Plum names are mapped to (ERT2-R3-001)", () => {
    const codes = (model_: EquipmentModel | null) => kindChoices(STRUCTURE, model_).map((item) => item.class_code);
    expect(codes(null)).toContain("COUNTERWEIGHT");
    expect(codes(model({ mapped_names: [] }))).toContain("COUNTERWEIGHT");
    const mapped = codes(model({ mapped_names: ["ACME CC 100"] }));
    expect(mapped).toContain("CRANE");
    expect(mapped).not.toContain("COUNTERWEIGHT");
  });

  it("checks an open model form against the model as loaded again, and refuses a kind it may no longer send (ERT2-R4-003)", () => {
    const crane = model({ model_public_id: "c1", model_version: 3 });
    // A name is mapped while the form is open: the version does not move, the form stays, and sees the mapping.
    const mapped = { ...crane, mapped_names: ["ACME X"] };
    expect(editingAfterLoad(crane, [mapped])).toEqual({ editing: mapped, closedAsStale: false });
    const draft = { ...EMPTY_MODEL_FORM, maker: "ACME", modelName: "X", classCode: "COUNTERWEIGHT", fitsModelIds: ["c9"] };
    expect(kindProblem(draft, crane, [crane], STRUCTURE)).toBeNull();
    expect(kindProblem(draft, mapped, [mapped], STRUCTURE)).toBe("Plum model names are mapped to this model, so it cannot become a kind of kit.");
    expect(kindProblem(draft, { ...crane, machine_count: 2 }, [crane], STRUCTURE)).toContain("2 records use this model");
    expect(kindProblem({ ...draft, classCode: "CRANE" }, mapped, [mapped], STRUCTURE)).toBeNull();
    expect(kindProblem(draft, null, [], STRUCTURE)).toBeNull();
  });

  it("offers a piece's count and model only while it is active, and sends only what it offers (ERT2-R4-005)", () => {
    const active = { asset_status_code: "ACTIVE", quantity: 6, model_public_id: "k1" };
    const retired = { ...active, asset_status_code: "RETIRED" };
    const draft = { serial: " SN-1 ", year: "2015", quantity: "8", modelId: "k2" };
    expect(detailFields(active, null)).toEqual({ number: true, count: false, model: false });
    expect(detailFields(active, "COUNTED")).toEqual({ number: false, count: true, model: true });
    expect(detailFields(retired, "COUNTED")).toEqual({ number: false, count: false, model: false });
    expect(detailFields(retired, "SINGLE")).toEqual({ number: true, count: false, model: false });
    expect(detailsPayload(active, "COUNTED", draft)).toEqual({ serial_number: null, year_of_manufacture: 2015, quantity: 8, model_public_id: "k2" });
    expect(detailsPayload(retired, "COUNTED", draft)).toEqual({ serial_number: null, year_of_manufacture: 2015 });
    expect(detailsPayload(retired, "SINGLE", draft)).toEqual({ serial_number: "SN-1", year_of_manufacture: 2015 });
    expect(detailsPayload(active, null, draft)).toEqual({ serial_number: "SN-1", year_of_manufacture: 2015 });
  });

  it("does not offer a new kind for a model the server would refuse it for (ERT2-R1-006)", () => {
    const crane = model({ model_public_id: "c1" });
    const hook = model({ model_public_id: "k1", class_code: "HOOK_BLOCK", is_kit: true, fits_models: [{ model_public_id: "c1", label: "ACME X" }] });
    expect(kindLockedReason(null, [crane])).toBeNull();
    expect(kindLockedReason(crane, [crane])).toBeNull();
    expect(kindLockedReason(model({ model_public_id: "c1", machine_count: 1 }), [crane])).toBe(
      "1 record uses this model, so its kind cannot change. Record a new model instead.",
    );
    expect(kindLockedReason(hook, [crane, hook])).toBeNull();
    expect(kindLockedReason(model({ ...hook, machine_count: 3 }), [crane, hook])).toContain("3 records use this model");
    expect(kindLockedReason(crane, [crane, hook])).toBe(
      "Kit is recorded as fitting this model, so its kind cannot change. Take it off those kit models first.",
    );
  });

  it("offers a kit model the live crane models of the classes it is kit for, and keeps a retired one already chosen", () => {
    const models = [
      model({ model_public_id: "c1", class_code: "CRANE" }),
      model({ model_public_id: "c2", class_code: "CRANE", is_retired: true }),
      model({ model_public_id: "p1", class_code: "PRIME_MOVER" }),
    ];
    expect(craneModelChoices(models, counterweight).map((item) => item.model_public_id)).toEqual(["c1"]);
    expect(craneModelChoices(models, counterweight, ["c2"]).map((item) => item.model_public_id)).toEqual(["c1", "c2"]);
    expect(craneModelChoices(models, crane)).toEqual([]);
  });

  it("adds pieces only of live kit models that fit the machine's model", () => {
    const models = [
      model({ model_public_id: "k1", is_kit: true, fits_models: [{ model_public_id: "c1", label: "ACME CC 100" }] }),
      model({ model_public_id: "k2", is_kit: true, is_retired: true, fits_models: [{ model_public_id: "c1", label: "ACME CC 100" }] }),
      model({ model_public_id: "k3", is_kit: true, fits_models: [{ model_public_id: "c9", label: "ACME CC 900" }] }),
    ];
    expect(kitModelsFor(models, "c1").map((item) => item.model_public_id)).toEqual(["k1"]);
    expect(kitModelsFor(models, null)).toEqual([]);
  });

  it("needs a kit model's crane models, and sends them only for kit", () => {
    const form = { ...EMPTY_MODEL_FORM, maker: "ACME", modelName: "Block 3.9 t", classCode: "COUNTERWEIGHT", makerPartNumber: " PN-1 " };
    expect(modelFormProblem(form, STRUCTURE)).toBe("Choose the crane models this kit fits: at least one.");
    const chosen = { ...form, fitsModelIds: ["c1", "c2"] };
    expect(modelFormProblem(chosen, STRUCTURE)).toBeNull();
    expect(modelPayload(chosen, STRUCTURE)).toMatchObject({ maker_part_number: "PN-1", fits_model_public_ids: ["c1", "c2"] });
  });

  it("names a piece of kit by its model and own number, a machine by Plum's number", () => {
    expect(assetName({ machine_number: "T-1", model_label: "ACME CC 100", class_label: "Crane" })).toBe("T-1");
    expect(assetName({ machine_number: null, model_label: "ACME insert 6 m", class_label: "Boom and jib section" })).toBe("ACME insert 6 m");
    expect(assetName({ machine_number: null, model_label: null, class_label: "Hook block" }, "HB-7")).toBe("Hook block, no. HB-7");
    expect(detailsMissingText({ origin_code: "PLATFORM" })).toBe("Its own number to enter");
    expect(detailsMissingText({ origin_code: "PLUM" })).toBe("Serial number or year of manufacture to enter");
  });

  it("says what is held, and when and why a piece was retired", () => {
    expect(piecesHeldText({ pieces_held: 0, records_held: 0, tracking_code: "SINGLE" })).toBe("None held yet");
    expect(piecesHeldText({ pieces_held: 4, records_held: 4, tracking_code: "SINGLE" })).toBe("4 held");
    expect(piecesHeldText({ pieces_held: 6, records_held: 1, tracking_code: "COUNTED" })).toBe("6 held, counted");
    expect(retirementText({ retired_on: "2026-09-20", retirement_reason_code: "OTHER", retirement_note: "Returned to the supplier" })).toBe(
      "Retired on 2026-09-20: other. Returned to the supplier.",
    );
    expect(retirementText({ retired_on: null, retirement_reason_code: null, retirement_note: null })).toBeNull();
  });

  it("adds pieces with a count, and a number only to one piece of a kind tracked one by one", () => {
    const form = { ...EMPTY_KIT_FORM, kitModelId: "k1" };
    expect(kitFormProblem({ ...EMPTY_KIT_FORM }, "SINGLE")).toBe("Choose the kit model.");
    expect(kitFormProblem({ ...form, count: "0" }, "SINGLE")).not.toBeNull();
    expect(kitFormProblem({ ...form, count: "51" }, "SINGLE")).not.toBeNull();
    expect(kitFormProblem({ ...form, count: "2", serialNumber: "SN" }, "SINGLE")).not.toBeNull();
    expect(kitFormProblem({ ...form, serialNumber: "SN" }, "COUNTED")).not.toBeNull();
    expect(kitFormProblem({ ...form, year: "15" }, "SINGLE")).toBe("Give the year of manufacture as four digits.");
    expect(kitFormProblem({ ...form, count: "6" }, "COUNTED")).toBeNull();
    expect(kitPayload({ ...form, count: "3", year: "2015" }, "key-1", { asset_public_id: "a-1", asset_version: 4 }, { model_version: 2 })).toEqual({
      create_request_key: "key-1",
      machine_public_id: "a-1",
      expected_asset_version: 4,
      kit_model_public_id: "k1",
      expected_model_version: 2,
      count: 3,
      serial_number: null,
      year_of_manufacture: 2015,
    });
  });

  it("retires with a reason and a day not in the future, a note with Other, and a count only from a set", () => {
    const form = { reasonCode: "LOST", retiredOn: "2026-09-20", note: "", count: "6" };
    expect(retireFormProblem({ ...form, reasonCode: "" }, 1, "2026-09-26")).toBe("Choose why it was retired.");
    expect(retireFormProblem({ ...form, reasonCode: "OTHER" }, 1, "2026-09-26")).toBe("Say why in the note: it is required with Other.");
    expect(retireFormProblem({ ...form, retiredOn: "2026-09-27" }, 1, "2026-09-26")).toBe("The day it was retired cannot be in the future.");
    expect(retireFormProblem({ ...form, count: "7" }, 6, "2026-09-26")).not.toBeNull();
    expect(retireFormProblem({ ...form, count: "2" }, 6, "2026-09-26")).toBeNull();
    expect(retirePayload({ ...form, count: "2" }, 6)).toEqual({ reason_code: "LOST", retired_on: "2026-09-20", note: null, count: 2 });
    expect(retirePayload(form, 1)).toEqual({ reason_code: "LOST", retired_on: "2026-09-20", note: null });
  });

  it("opens the list on a kit model's pieces or a model's kit from its address", () => {
    expect(machineFiltersFromSearch("")).toEqual(INITIAL_MACHINE_FILTERS);
    const pieces = machineFiltersFromSearch("?kit_model=k1");
    expect(pieces).toMatchObject({ kindCode: "PART", kitModelPublicId: "k1", fitsModelPublicId: "" });
    expect(machineQuery(pieces, 0, 25)).toContain("kit_model_public_id=k1");
    expect(machineQuery(machineFiltersFromSearch("?fits_model=c1"), 0, 25)).toContain("fits_model_public_id=c1");
  });
});
