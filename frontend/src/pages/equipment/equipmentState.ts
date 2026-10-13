// Pure rules for the Equipment screens (ERT-1), kept out of the components so they can be tested without a
// browser DOM. The backend re-checks everything and words every refusal; these keep a form from sending
// what it can already tell is incomplete, and word what the screens show.
//
// Machines come from Plum's vehicle report, through a preview that changes nothing until Admin confirms
// it. Plum's facts are corrected only by a recorded correction; facts Plum does not hold (serial number,
// year of manufacture) are entered here; a machine's capabilities come from its model unless Admin gives
// it its own value.
//
// Detachable kit (ERT-2) is recorded here, never read from Plum: pieces of a kit model, held for every
// machine of the crane models it fits and shared by them. Some kinds are tracked one by one, some as counted
// sets; a piece is retired with the day and the reason, and a counted set shrinks only that way.

import { createLatestOnly } from "../resource-requirements/resourceRequirementState";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

export { newRequestKey } from "../resource-requirements/resourceRequirementState";

// --- What the API returns ------------------------------------------------------------------------------

export type CapabilityValue = {
  capability_code: string;
  capability_label: string;
  unit_code: string | null;
  unit_symbol: string | null;
  value_kind_code: string;
  is_key: boolean;
  value: string | null;
  choice_value: string | null;
};

export type MachineCapability = CapabilityValue & {
  source_code: "OWN" | "MODEL" | "NONE";
  reason: string | null;
  set_by_display_name: string | null;
  set_at: string | null;
};

export type MachineSummary = {
  asset_public_id: string;
  asset_reference: string;
  asset_kind_code: string;
  // PLUM, or PLATFORM for a piece of kit Admin recorded (ERT-2).
  origin_code: string;
  // Plum's machine number; none for a piece of kit, which has no Plum row.
  machine_number: string | null;
  // 1, or a counted set's count.
  quantity: number;
  class_code: string;
  class_label: string;
  type_code: string | null;
  type_label: string | null;
  model_public_id: string | null;
  model_label: string | null;
  key_capability: CapabilityValue | null;
  asset_status_code: string;
  flag_codes: string[];
  details_missing: boolean;
  facts_report_date: string | null;
  asset_version: number;
};

// `asset_version` is what a fit or a removal is guarded by, for the part as well as the machine.
export type AssetReference = { asset_public_id: string; asset_reference: string; machine_number: string; class_code: string; asset_version: number };

export type MachineLink = {
  link_public_id: string;
  machine: AssetReference;
  part: AssetReference;
  fitted_on: string;
  removed_on: string | null;
};

export type MachineCorrection = {
  correction_public_id: string;
  field_code: string;
  // Withheld for an engine or chassis number the signed-in user may not see (Admin only, for now).
  plum_value: string | null;
  corrected_value: string | null;
  corrected_value_label: string | null;
  values_withheld: boolean;
  // Withheld with the values, for an engine or chassis number the user may not see.
  reason: string | null;
  correction_status_code: string;
  closed_reason_code: string | null;
  closed_by_display_name: string | null;
  closed_at: string | null;
  recorded_by_display_name: string | null;
  recorded_at: string;
};

export type Machine = MachineSummary & {
  engine_number: string | null;
  chassis_number: string | null;
  // Engine and chassis numbers are shown to Admin only, for now (owner, 25 September 2026).
  identity_numbers_withheld: boolean;
  commenced_year: number | null;
  owning_company: string | null;
  serial_number: string | null;
  year_of_manufacture: number | null;
  capabilities: MachineCapability[];
  flags: { flag_code: string; subject_code: string; raised_at: string; raised_by_import_public_id: string | null }[];
  corrections: MachineCorrection[];
  fitted_parts: MachineLink[];
  fitted_to: MachineLink | null;
  link_history: MachineLink[];
  plum: { category: string | null; model_name: string | null; capacity: string | null } | null;
  reconciliation_status_code: string | null;
  // ERT-2. A machine: the kit held for its model, and how many active machines of it share that kit.
  kit: KitHeld[];
  model_active_unit_count: number | null;
  // A piece of kit: the crane models it fits, and, once retired, when and why.
  fits_models: ModelReference[];
  retired_on: string | null;
  retirement_reason_code: string | null;
  retirement_note: string | null;
  created_at: string;
  updated_at: string;
};

export type ModelReference = { model_public_id: string; label: string };

/** One kit model fitting a machine's model, and what is held of it for every machine of those models. */
export type KitHeld = {
  kit_model_public_id: string;
  label: string;
  class_code: string;
  class_label: string;
  type_code: string | null;
  type_label: string | null;
  tracking_code: string;
  key_capability: CapabilityValue | null;
  pieces_held: number;
  records_held: number;
  fits_models: ModelReference[];
};

export type EquipmentModel = {
  model_public_id: string;
  maker: string;
  model_name: string;
  label: string;
  class_code: string;
  class_label: string;
  class_kind_code: string;
  type_code: string | null;
  type_label: string | null;
  maker_part_number: string | null;
  capabilities: CapabilityValue[];
  mapped_names: string[];
  machine_count: number;
  // ERT-2: a kit model's crane models and the pieces held of it; a machine model's active machines.
  is_kit: boolean;
  fits_models: ModelReference[];
  pieces_held: number;
  fits_no_active_crane: boolean;
  active_unit_count: number;
  model_version: number;
  is_retired: boolean;
};

export type StructureCapability = {
  capability_code: string;
  capability_label: string;
  unit_code: string | null;
  unit_symbol: string | null;
  whole_numbers_only: boolean;
  value_kind_code: string;
  allowed_values: string[] | null;
  is_key: boolean;
  is_active: boolean;
};

export type StructureClass = {
  class_code: string;
  class_label: string;
  class_kind_code: string;
  // SINGLE: a record for each piece; COUNTED: a record holds a counted set (ERT-2).
  tracking_code: string;
  // Fitted by a dated link to these classes.
  fits_class_codes: string[];
  // Kit for these machine classes: held for the models it fits, never fitted (ERT-2).
  kit_for_class_codes: string[];
  business_line_codes: string[];
  is_active: boolean;
  types: { type_code: string; type_label: string; is_active: boolean }[];
  capabilities: StructureCapability[];
};

export type Structure = {
  taxonomy_version: number;
  // How deep fitted parts may nest, the machine being level 1.
  component_depth: number;
  units: { unit_code: string; unit_label: string; unit_symbol: string }[];
  classes: StructureClass[];
};

export type PreviewFlag = { flag_code: string; subject_code: string };

export type PreviewRow = {
  row_number: number;
  machine_number: string | null;
  outcome_code: string;
  reason_code: string | null;
  asset_public_id: string | null;
  asset_reference: string | null;
  kind_code: string | null;
  class_code: string | null;
  class_label: string | null;
  type_code: string | null;
  type_label: string | null;
  model_public_id: string | null;
  model_label: string | null;
  status_code: string | null;
  changed_facts: string[];
  flags: PreviewFlag[];
  // The readings and corrections the row was read with. An engine or chassis number is never repeated here.
  rules_applied: PreviewRule[];
  corrections: PreviewCorrection[];
  // Fitted-part links of this row's asset that confirming will close.
  closing_links: ClosingLink[];
  plum: { category: string | null; model_name: string | null; capacity: string | null; commenced_year: string | null; status: string | null };
  needs_attention: boolean;
};

export type PreviewRule = {
  rule_public_id: string;
  column_code: string;
  action_code: string;
  plum_value: string | null;
  result_number: string | null;
  result_unit_code: string | null;
  result_class_code: string | null;
  result_type_code: string | null;
};

export type ClosingLink = {
  machine_asset_public_id: string;
  machine_machine_number: string;
  part_asset_public_id: string;
  part_machine_number: string;
  because: string;
};

export type PreviewCorrection = { correction_public_id: string; field_code: string; effect_code: string; corrected_value_label: string | null };

export type UnmappedName = {
  source_name: string;
  normalized_source_name: string;
  category: string | null;
  class_code: string | null;
  make: string | null;
  model: string | null;
  machine_count: number;
};

export type PairProposal = {
  part_machine_number: string;
  proposed_machine_number: string | null;
  candidates: { machine_number: string; asset_reference: string | null }[];
};

export type ImportPreview = {
  counts: Record<string, number>;
  rows: PreviewRow[];
  missing: { asset_public_id: string; asset_reference: string; machine_number: string }[];
  unmapped_model_names: UnmappedName[];
  pair_proposals: PairProposal[];
  closing_links: ClosingLink[];
};

export type ImportSummary = {
  import_public_id: string;
  import_status_code: string;
  report_date: string;
  row_count: number;
  fingerprint_prefix: string;
  uploaded_by_display_name: string | null;
  uploaded_at: string;
  published_by_display_name: string | null;
  published_at: string | null;
  discard_reason_code: string | null;
  counts: Record<string, number>;
};

export type EquipmentImport = ImportSummary & {
  preview_version: number;
  preview_computed_at: string;
  is_current: boolean;
  stale_reason: string | null;
  preview: ImportPreview;
};

export type ValueRule = {
  rule_public_id: string;
  column_code: string;
  plum_value: string | null;
  value_withheld: boolean;
  action_code: string;
  result_number: string | null;
  result_unit_code: string | null;
  result_class_code: string | null;
  result_type_code: string | null;
  // Withheld with the values, for an engine or chassis number the user may not see.
  reason: string | null;
  rule_status_code: string;
  recorded_by_display_name: string | null;
  recorded_at: string;
  rows_in_latest_report: number | null;
};

export type CorrectionToSend = {
  correction_public_id: string;
  asset_public_id: string;
  asset_reference: string;
  machine_number: string;
  field_code: string;
  plum_value: string | null;
  corrected_value: string | null;
  corrected_value_label: string | null;
  values_withheld: boolean;
  // Withheld with the values, for an engine or chassis number the user may not see.
  reason: string | null;
  recorded_by_display_name: string | null;
  recorded_at: string;
  plum_changed: boolean;
};

export const WITHHELD_TEXT = "Shown to Admin only";

/** A correction's values in words, or why they are not shown. */
/** A reason as the user may see it: withheld with the engine or chassis number it may repeat. */
export function reasonText(reason: string | null): string {
  return reason ?? "The reason is shown to Admin only.";
}

export function correctionValuesText(correction: Pick<MachineCorrection, "plum_value" | "corrected_value_label" | "values_withheld">): string {
  if (correction.values_withheld) return `${WITHHELD_TEXT}: Plum's value and the correct one.`;
  return `Plum has ${correction.plum_value ?? "nothing"}; read as ${correction.corrected_value_label ?? "-"}.`;
}

// --- Who may do what (the backend is the control; this only hides what would be refused) ---------------

export const EQUIPMENT_MANAGE_ROLES = ["ADMIN"];

export function canManageEquipment(roleCodes: readonly string[]): boolean {
  return roleCodes.some((role) => EQUIPMENT_MANAGE_ROLES.includes(role));
}

// --- Words ---------------------------------------------------------------------------------------------

const FLAG_LABELS: Record<string, string> = {
  CATEGORY_NOT_MAPPED: "Plum's category is not one the platform knows",
  MODEL_NOT_MAPPED: "Model name not mapped to a model yet",
  CLASS_DISAGREES: "The mapped model is another kind of machine",
  NOT_A_NUMBER: "Plum's figure is not a number",
  OUT_OF_PATTERN: "Plum's value is outside what is plausible",
  DIFFERS_FROM_MODEL: "Plum's figure differs from the rating",
  UNIT_UNCLEAR: "What Plum's figure measures is unclear",
  VALUE_MISSING: "Plum gives no figure to check",
  NOT_IN_LATEST_REPORT: "Not in the latest confirmed report",
  POSSIBLY_RENUMBERED: "May be a known machine under a new number",
  PART_NOT_FITTED: "Part not fitted to a machine",
  DUPLICATE_SOURCE_KEY: "Its machine number is on two rows of a report",
  PLUM_CHANGED_CORRECTED_VALUE: "Plum changed a value that was corrected",
};

export const FIELD_LABELS: Record<string, string> = {
  CATEGORY: "Kind of machine (Plum's category)",
  MODEL: "Model",
  ENGINE_NUMBER: "Engine number",
  CHASSIS_NUMBER: "Chassis number",
  COMMENCED_YEAR: "Commenced year",
  OWNING_COMPANY: "Owning company",
  STATUS: "Active or inactive",
  CAPACITY: "Capacity figure (for the check)",
};

export const CORRECTION_FIELDS = Object.keys(FIELD_LABELS);

const OUTCOME_LABELS: Record<string, string> = {
  NEW: "New",
  CHANGED: "Changed",
  UNCHANGED: "Unchanged",
  RETIRED: "Retired",
  REACTIVATED: "Reactivated",
  NOT_BROUGHT_IN: "Not brought in",
  SET_ASIDE: "Set aside",
  MISSING: "Missing from this report",
};

const REASON_LABELS: Record<string, string> = {
  NO_MACHINE_NUMBER: "No machine number",
  VALUE_TOO_LONG: "A value is longer than the platform keeps",
  DUPLICATE_SOURCE_KEY: "Machine number on two rows",
  CATEGORY_NOT_MAPPED: "Unknown category",
  STATUS_NOT_RECOGNISED: "Status is neither Active nor Inactive",
  INACTIVE_NOT_KNOWN: "Inactive, and never brought in",
  CLASS_NOT_USED: "A kind no business line uses",
};

export const VALUE_RULE_ACTION_LABELS: Record<string, string> = {
  SPLIT_NUMBER_AND_UNIT: "A number and its unit",
  REASSIGN_TO_TYPE: "Names a type, not a figure",
  NOT_A_VALUE: "Means nothing was entered",
};

export const IMPORT_STATUS_LABELS: Record<string, string> = {
  PREVIEWED: "Preview - not confirmed",
  PUBLISHED: "Confirmed",
  DISCARDED: "Discarded",
};

export function flagLabel(flag: PreviewFlag, capabilityLabels: Record<string, string> = {}): string {
  const base = FLAG_LABELS[flag.flag_code] ?? flag.flag_code;
  const subject = flag.subject_code ? capabilityLabels[flag.subject_code] ?? FIELD_LABELS[flag.subject_code] ?? flag.subject_code : "";
  return subject ? `${base}: ${subject.toLowerCase()}` : base;
}

export function flagCodeLabel(code: string): string {
  return FLAG_LABELS[code] ?? code;
}

export function outcomeLabel(code: string): string {
  return OUTCOME_LABELS[code] ?? code;
}

export function reasonLabel(code: string | null): string {
  return code ? REASON_LABELS[code] ?? code : "";
}

export function statusLabel(code: string | null): string {
  return code === "ACTIVE" ? "Active" : code === "RETIRED" ? "Retired" : code ?? "-";
}

export function plainNumber(value: string | null | undefined): string {
  if (value === null || value === undefined || value === "") return "";
  const number = Number(value);
  return Number.isFinite(number) ? String(number) : value;
}

export function capabilityText(capability: CapabilityValue | null): string {
  if (!capability) return "-";
  if (capability.choice_value) return `${capability.capability_label} ${capability.choice_value}`;
  if (capability.value === null) return "-";
  return `${capability.capability_label} ${plainNumber(capability.value)}${capability.unit_symbol ? ` ${capability.unit_symbol}` : ""}`;
}

export function machineKindText(item: Pick<MachineSummary, "class_label" | "type_label" | "model_label">): string {
  return [item.type_label ? `${item.class_label}, ${item.type_label.toLowerCase()}` : item.class_label, item.model_label].filter(Boolean).join(" - ");
}

/** Capability labels by code, for flags whose subject is a capability. */
export function capabilityLabels(structure: Structure | null): Record<string, string> {
  const labels: Record<string, string> = {};
  for (const item of structure?.classes ?? []) for (const capability of item.capabilities) labels[capability.capability_code] = capability.capability_label;
  return labels;
}

export function findClass(structure: Structure | null, classCode: string | null): StructureClass | undefined {
  return structure?.classes.find((item) => item.class_code === classCode);
}

/** Classes a model can be of: every live class, machines first, parts after. */
export function modelClasses(structure: Structure | null): StructureClass[] {
  const live = (structure?.classes ?? []).filter((item) => item.is_active);
  return [...live.filter((item) => item.class_kind_code === "MACHINE"), ...live.filter((item) => item.class_kind_code === "PART")];
}

/** The kinds a model's form offers: a model Plum names are mapped to is not offered a kind of kit, since no Plum
 *  name is mapped to a kit model (independent review, round 3, ERT2-R3-001). */
export function kindChoices(structure: Structure | null, model: EquipmentModel | null): StructureClass[] {
  const mapped = Boolean(model?.mapped_names.length);
  return modelClasses(structure).filter((item) => !(mapped && isKitClass(item) && item.class_code !== model?.class_code));
}

/** Classes a machine can be corrected to, or a value can name a type of: live machine classes. */
export function machineClasses(structure: Structure | null): StructureClass[] {
  return (structure?.classes ?? []).filter((item) => item.is_active && item.class_kind_code === "MACHINE");
}

// --- Detachable kit (ERT-2) ------------------------------------------------------------------------------

/** A kind of kit: held for the models it fits, never fitted to a machine. */
export function isKitClass(item: StructureClass | undefined): boolean {
  return Boolean(item && item.kit_for_class_codes.length);
}

/** Whether the structure gives kit to this kind of machine - today, cranes. Only their pages show a kit section
 *  (independent review, round 1, ERT2-R1-003). */
export function takesKit(structure: Structure | null, classCode: string): boolean {
  return (structure?.classes ?? []).some((item) => item.kit_for_class_codes.includes(classCode));
}

/** What a record's details form offers. A machine: its serial number. A piece of kit (`tracking` set): its own
 *  number when tracked one by one, its count when a counted set (raised only), and its model within its kind -
 *  count and model only while it is active, as the server refuses both once it is retired (ERT2-R4-005). */
export function detailFields(machine: Pick<MachineSummary, "asset_status_code">, tracking: string | null): { number: boolean; count: boolean; model: boolean } {
  const active = machine.asset_status_code === "ACTIVE";
  return { number: tracking !== "COUNTED", count: tracking === "COUNTED" && active, model: tracking !== null && active };
}

/** The details a form sends: only the fields it offers, and a count or model only when changed. */
export function detailsPayload(
  machine: Pick<MachineSummary, "asset_status_code" | "quantity" | "model_public_id">,
  tracking: string | null,
  draft: { serial: string; year: string; quantity: string; modelId: string },
): Record<string, unknown> {
  const fields = detailFields(machine, tracking);
  return {
    serial_number: fields.number ? draft.serial.trim() || null : null,
    year_of_manufacture: draft.year.trim() ? Number(draft.year) : null,
    ...(fields.count && Number(draft.quantity) !== machine.quantity ? { quantity: Number(draft.quantity) } : {}),
    ...(fields.model && draft.modelId && draft.modelId !== machine.model_public_id ? { model_public_id: draft.modelId } : {}),
  };
}

/** What a retirement did, read from the record before and after it: the whole record, or some pieces of a counted
 *  set that stays with the rest (ERT2-R1-004). */
export function retiredText(before: Pick<MachineSummary, "quantity">, after: Pick<MachineSummary, "quantity" | "asset_status_code">): string {
  if (after.asset_status_code !== "ACTIVE") return "Retired. Its history is kept.";
  const gone = before.quantity - after.quantity;
  return `${gone} piece${gone === 1 ? "" : "s"} retired from the set; ${after.quantity} left in it. Its history is kept.`;
}

/** Why a model's kind cannot change, as the server would refuse it, or null: records use the model, or kit is
 *  recorded as fitting it (ERT2-R1-006). */
export function kindLockedReason(model: EquipmentModel | null, models: EquipmentModel[]): string | null {
  if (!model) return null;
  if (model.machine_count > 0) {
    const records = model.machine_count === 1 ? "1 record uses" : `${model.machine_count} records use`;
    return `${records} this model, so its kind cannot change. Record a new model instead.`;
  }
  if (models.some((item) => item.fits_models.some((fit) => fit.model_public_id === model.model_public_id))) {
    return "Kit is recorded as fitting this model, so its kind cannot change. Take it off those kit models first.";
  }
  return null;
}

/** The label a kind carries where models are chosen: a machine, a part, or kit. */
export function classKindNote(item: StructureClass): string {
  if (isKitClass(item)) return " (kit)";
  return item.class_kind_code === "PART" ? " (a part)" : "";
}

/** The crane models a kit model of this kind may fit: models of the classes it is kit for, live ones - or
 *  one already chosen, which a retired model stays. */
export function craneModelChoices(models: EquipmentModel[], kitClass: StructureClass | undefined, kept: readonly string[] = []): EquipmentModel[] {
  if (!kitClass || !isKitClass(kitClass)) return [];
  return models.filter(
    (model) => kitClass.kit_for_class_codes.includes(model.class_code) && (!model.is_retired || kept.includes(model.model_public_id)),
  );
}

/** The kit models pieces can be added of for a machine: live kit models that fit its model. */
export function kitModelsFor(models: EquipmentModel[], machineModelPublicId: string | null): EquipmentModel[] {
  if (!machineModelPublicId) return [];
  return models.filter((model) => model.is_kit && !model.is_retired && model.fits_models.some((fit) => fit.model_public_id === machineModelPublicId));
}

/** What a record is called beside its reference: Plum's machine number, or - for a piece of kit, which has
 *  none - its model, with its own number where it has one. */
export function assetName(item: Pick<MachineSummary, "machine_number" | "model_label" | "class_label">, serialNumber?: string | null): string {
  if (item.machine_number) return item.machine_number;
  const kind = item.model_label ?? item.class_label;
  return serialNumber ? `${kind}, no. ${serialNumber}` : kind;
}

/** How many pieces a record holds, where it holds more than one. */
export function quantityText(quantity: number): string {
  return quantity > 1 ? `${quantity} pieces` : "";
}

export function piecesHeldText(item: Pick<KitHeld, "pieces_held" | "records_held" | "tracking_code">): string {
  if (item.pieces_held === 0) return "None held yet";
  if (item.tracking_code === "COUNTED") return `${item.pieces_held} held, counted`;
  return `${item.pieces_held} held`;
}

/** Why a record appears under "Details to complete". */
export function detailsMissingText(item: Pick<MachineSummary, "origin_code">): string {
  return item.origin_code === "PLATFORM" ? "Its own number to enter" : "Serial number or year of manufacture to enter";
}

export const RETIREMENT_REASON_LABELS: Record<string, string> = {
  SCRAPPED: "Scrapped",
  LOST: "Lost",
  SOLD: "Sold",
  RECORDED_BY_MISTAKE: "Recorded by mistake",
  OTHER: "Other - say why in the note",
};

export function retirementText(machine: Pick<Machine, "retired_on" | "retirement_reason_code" | "retirement_note">): string | null {
  if (!machine.retired_on || !machine.retirement_reason_code) return null;
  const reason = (RETIREMENT_REASON_LABELS[machine.retirement_reason_code] ?? machine.retirement_reason_code).split(" - ")[0];
  return `Retired on ${machine.retired_on}: ${reason.toLowerCase()}${machine.retirement_note ? `. ${machine.retirement_note}` : ""}.`;
}

/** Adding pieces of a kit model: how many, and - for one piece of a kind tracked one by one - its own number. */
export type KitForm = { kitModelId: string; count: string; serialNumber: string; year: string };

export const EMPTY_KIT_FORM: KitForm = { kitModelId: "", count: "1", serialNumber: "", year: "" };

export const MAX_KIT_COUNT = 50;

export function kitFormProblem(form: KitForm, trackingCode: string | undefined): string | null {
  if (!form.kitModelId) return "Choose the kit model.";
  if (!/^\d+$/.test(form.count.trim()) || Number(form.count) < 1 || Number(form.count) > MAX_KIT_COUNT) {
    return `Give how many, from 1 to ${MAX_KIT_COUNT}.`;
  }
  if (form.serialNumber.trim() && (trackingCode === "COUNTED" || Number(form.count) !== 1)) {
    return "A piece's own number is given one piece at a time, and a counted set has none.";
  }
  if (form.year.trim() && !/^\d{4}$/.test(form.year.trim())) return "Give the year of manufacture as four digits.";
  return null;
}

/** The request "add kit" sends, with the premise it was made on: the machine page it came from and the versions of
 *  that machine and of the kit model it showed - the server refuses the add if either changed (ERT2-R1-001). */
export function kitPayload(
  form: KitForm,
  requestKey: string,
  machine: Pick<MachineSummary, "asset_public_id" | "asset_version">,
  kitModel: Pick<EquipmentModel, "model_version">,
): Record<string, unknown> {
  return {
    create_request_key: requestKey,
    machine_public_id: machine.asset_public_id,
    expected_asset_version: machine.asset_version,
    kit_model_public_id: form.kitModelId,
    expected_model_version: kitModel.model_version,
    count: Number(form.count),
    serial_number: form.serialNumber.trim() || null,
    year_of_manufacture: form.year.trim() ? Number(form.year) : null,
  };
}

/** Retiring a piece, or some pieces of a counted set: the reason, the day, a note (required with Other). */
export type RetireForm = { reasonCode: string; retiredOn: string; note: string; count: string };

export function retireFormProblem(form: RetireForm, held: number, today: string): string | null {
  if (!form.reasonCode) return "Choose why it was retired.";
  if (form.reasonCode === "OTHER" && !form.note.trim()) return "Say why in the note: it is required with Other.";
  if (!form.retiredOn) return "Give the day it was retired.";
  if (form.retiredOn > today) return "The day it was retired cannot be in the future.";
  if (held > 1 && (!/^\d+$/.test(form.count.trim()) || Number(form.count) < 1 || Number(form.count) > held)) {
    return `Give how many of the ${held} pieces left, from 1 to ${held}.`;
  }
  return null;
}

export function retirePayload(form: RetireForm, held: number): Record<string, unknown> {
  return {
    reason_code: form.reasonCode,
    retired_on: form.retiredOn,
    note: form.note.trim() || null,
    ...(held > 1 ? { count: Number(form.count) } : {}),
  };
}

// --- The machine list's requests ---------------------------------------------------------------------------

export type MachineFilters = {
  kindCode: string;
  classCode: string;
  statusCode: string;
  flaggedOnly: boolean;
  detailsToComplete: boolean;
  search: string;
  // ERT-2: one kit model's pieces, or the kit held for one machine model.
  kitModelPublicId: string;
  fitsModelPublicId: string;
};

export const INITIAL_MACHINE_FILTERS: MachineFilters = {
  kindCode: "MACHINE",
  classCode: "",
  statusCode: "ACTIVE",
  flaggedOnly: false,
  detailsToComplete: false,
  search: "",
  kitModelPublicId: "",
  fitsModelPublicId: "",
};

/** The list's first filters from its address: `?kit_model=` a kit model's pieces, `?fits_model=` the kit held
 *  for a machine model - the links from a machine's kit section. */
export function machineFiltersFromSearch(search: string): MachineFilters {
  const params = new URLSearchParams(search);
  const kitModelPublicId = params.get("kit_model") ?? "";
  const fitsModelPublicId = params.get("fits_model") ?? "";
  if (!kitModelPublicId && !fitsModelPublicId) return INITIAL_MACHINE_FILTERS;
  return { ...INITIAL_MACHINE_FILTERS, kindCode: "PART", kitModelPublicId, fitsModelPublicId };
}

export function machineQuery(filters: MachineFilters, offset: number, pageSize: number): string {
  const params = new URLSearchParams({ limit: String(pageSize + 1), offset: String(offset) });
  if (filters.kindCode) params.set("kind_code", filters.kindCode);
  if (filters.classCode) params.set("class_code", filters.classCode);
  if (filters.statusCode) params.set("status_code", filters.statusCode);
  if (filters.flaggedOnly) params.set("flagged_only", "true");
  if (filters.detailsToComplete) params.set("details_to_complete", "true");
  if (filters.search.trim()) params.set("search", filters.search.trim());
  if (filters.kitModelPublicId) params.set("kit_model_public_id", filters.kitModelPublicId);
  if (filters.fitsModelPublicId) params.set("fits_model_public_id", filters.fitsModelPublicId);
  return params.toString();
}

export type ListUpdate<Row> =
  | { kind: "loading"; offset: number }
  | { kind: "rows"; rows: Row[]; offset: number }
  | { kind: "failed"; message: string }
  | { kind: "signed-out" };

export type ListView<Row> = { rows: Row[]; offset: number; hasNextPage: boolean; loading: boolean; error: string };

export function initialListView<Row>(): ListView<Row> {
  return { rows: [], offset: 0, hasNextPage: false, loading: false, error: "" };
}

/**
 * What a list shows: rows only as the answer to the request now awaited. The moment a new request starts -
 * a filter change, a page turn, a refresh - the previous rows are no longer shown, so a list never shows one
 * filter's rows under another's controls (the WRR-001 planning list's rule, review round 4).
 */
export function listView<Row>(view: ListView<Row>, update: ListUpdate<Row>, pageSize: number): ListView<Row> {
  switch (update.kind) {
    case "loading":
      return { rows: [], offset: update.offset, hasNextPage: false, loading: true, error: "" };
    case "rows":
      return { rows: update.rows.slice(0, pageSize), offset: update.offset, hasNextPage: update.rows.length > pageSize, loading: false, error: "" };
    case "failed":
      return { ...view, rows: [], hasNextPage: false, loading: false, error: update.message };
    case "signed-out":
      return { ...initialListView<Row>(), error: SIGN_IN_FIRST };
    default:
      return view;
  }
}

/**
 * A list's loading, kept out of the component. It holds the filters itself, so every load asks for the
 * filters the controls show, and every load takes a ticket before anything else - even one that finds no
 * session - so an older answer is never shown after a newer request (the WRR-001 rules, rounds 2 and 3).
 */
export function createListController<Filters, Row>(deps: {
  initialFilters: Filters;
  getToken: () => string | null;
  fetchRows: (token: string, filters: Filters, offset: number) => Promise<Row[]>;
  show: (update: ListUpdate<Row>) => void;
  failure: string;
}) {
  let filters = deps.initialFilters;
  const latest = createLatestOnly();

  async function load(offset: number): Promise<void> {
    const ticket = latest.begin();
    const token = deps.getToken();
    if (!token) {
      deps.show({ kind: "signed-out" });
      return;
    }
    deps.show({ kind: "loading", offset });
    try {
      const rows = await deps.fetchRows(token, filters, offset);
      if (latest.isLatest(ticket)) deps.show({ kind: "rows", rows, offset });
    } catch (error) {
      if (latest.isLatest(ticket)) deps.show({ kind: "failed", message: error instanceof Error ? error.message : deps.failure });
    }
  }

  return {
    filters: (): Filters => filters,
    setFilters: (next: Partial<Filters>): Promise<void> => {
      filters = { ...filters, ...next };
      return load(0);
    },
    load,
  };
}

// --- Forms -----------------------------------------------------------------------------------------------------

export type CapabilityDraft = { capabilityCode: string; value: string; reason: string };

/** A number the backend will take for a capability: above zero, up to three decimals, whole where counted. */
export function capabilityValueProblem(capability: StructureCapability, value: string): string | null {
  if (capability.value_kind_code === "CHOICE") {
    return capability.allowed_values?.includes(value) ? null : `Choose the ${capability.capability_label.toLowerCase()} from its list.`;
  }
  if (!/^\d+(\.\d{1,3})?$/.test(value.trim()) || Number(value) <= 0) {
    return `Give the ${capability.capability_label.toLowerCase()} as a number above zero, with up to three decimals.`;
  }
  if (capability.whole_numbers_only && !/^\d+$/.test(value.trim())) return `${capability.capability_label} is counted in whole numbers.`;
  if (Number(value) >= 1_000_000_000) return `${capability.capability_label} is too large.`;
  return null;
}

export function capabilityPayload(capability: StructureCapability, value: string): { capability_code: string; value: string | null; choice_value: string | null } {
  return capability.value_kind_code === "CHOICE"
    ? { capability_code: capability.capability_code, value: null, choice_value: value }
    : { capability_code: capability.capability_code, value: value.trim(), choice_value: null };
}

export type ModelForm = {
  maker: string;
  modelName: string;
  classCode: string;
  typeCode: string;
  values: Record<string, string>;
  isRetired: boolean;
  // ERT-2: the maker's part number, any model; the crane models a kit model fits.
  makerPartNumber: string;
  fitsModelIds: string[];
};

export const EMPTY_MODEL_FORM: ModelForm = {
  maker: "",
  modelName: "",
  classCode: "",
  typeCode: "",
  values: {},
  isRetired: false,
  makerPartNumber: "",
  fitsModelIds: [],
};

/**
 * The model form after the models are loaded again: if the model being changed has a newer version now -
 * someone else saved it - the form closes, so a draft made against the older version is never sent
 * (independent review, round 4, ERT1-R4-005). A new model's form, or one still current, stays open - with
 * the model as loaded now: a name mapped to it, or a record made of it, does not change its version, and the
 * form's guards must see them (ERT2-R4-003).
 */
export function editingAfterLoad(
  editing: EquipmentModel | "new" | null,
  models: EquipmentModel[],
): { editing: EquipmentModel | "new" | null; closedAsStale: boolean } {
  if (editing === null || editing === "new") return { editing, closedAsStale: false };
  const now = models.find((model) => model.model_public_id === editing.model_public_id);
  if (now && now.model_version === editing.model_version) return { editing: now, closedAsStale: false };
  return { editing: null, closedAsStale: true };
}

/** A kind the model's form may not send - the server would refuse it - for a draft made before a name was
 *  mapped to the model, a record was made of it, or kit came to fit it (ERT2-R4-003). */
export function kindProblem(form: ModelForm, model: EquipmentModel | null, models: EquipmentModel[], structure: Structure | null): string | null {
  if (!model || form.classCode === model.class_code) return null;
  const locked = kindLockedReason(model, models);
  if (locked) return locked;
  if (!kindChoices(structure, model).some((item) => item.class_code === form.classCode)) {
    return "Plum model names are mapped to this model, so it cannot become a kind of kit.";
  }
  return null;
}

export const MODEL_CHANGED_ELSEWHERE_TEXT = "Someone else changed this model while you had it open, so your changes were not saved. Open it again to change it.";

export function modelFormFrom(model: EquipmentModel): ModelForm {
  const values: Record<string, string> = {};
  for (const capability of model.capabilities) values[capability.capability_code] = capability.choice_value ?? plainNumber(capability.value);
  return {
    maker: model.maker,
    modelName: model.model_name,
    classCode: model.class_code,
    typeCode: model.type_code ?? "",
    values,
    isRetired: model.is_retired,
    makerPartNumber: model.maker_part_number ?? "",
    fitsModelIds: model.fits_models.map((fit) => fit.model_public_id),
  };
}

export function modelFormProblem(form: ModelForm, structure: Structure | null): string | null {
  if (!form.maker.trim() || !form.modelName.trim()) return "Give the model's maker and its name.";
  const equipmentClass = findClass(structure, form.classCode);
  if (!equipmentClass) return "Choose the kind of machine or part the model is.";
  if (isKitClass(equipmentClass) && form.fitsModelIds.length === 0) return "Choose the crane models this kit fits: at least one.";
  for (const capability of equipmentClass.capabilities) {
    const value = (form.values[capability.capability_code] ?? "").trim();
    if (value) {
      const problem = capabilityValueProblem(capability, value);
      if (problem) return problem;
    }
  }
  return null;
}

export function modelPayload(form: ModelForm, structure: Structure | null): Record<string, unknown> {
  const equipmentClass = findClass(structure, form.classCode);
  return {
    maker: form.maker.trim(),
    model_name: form.modelName.trim(),
    class_code: form.classCode,
    type_code: form.typeCode || null,
    capabilities: (equipmentClass?.capabilities ?? [])
      .filter((capability) => (form.values[capability.capability_code] ?? "").trim())
      .map((capability) => capabilityPayload(capability, form.values[capability.capability_code])),
    maker_part_number: form.makerPartNumber.trim() || null,
    // Only a kit model fits crane models; any other sends none.
    fits_model_public_ids: isKitClass(equipmentClass) ? form.fitsModelIds : [],
  };
}

/** What the model form says after a save. A new model the server already had from this form - its reply lost on
 *  the way - was saved once, earlier: "already saved", not "nothing changed" (TB-1 TB1-102 part b). */
export function modelSavedText(result: { event: unknown; replayed?: boolean }): string {
  if (result.replayed) return "Already saved: nothing more was recorded.";
  return result.event ? "Model saved." : "Nothing changed, so nothing was saved.";
}

export type ValueRuleForm = {
  columnCode: string;
  plumValue: string;
  actionCode: string;
  resultNumber: string;
  resultUnitCode: string;
  resultClassCode: string;
  resultTypeCode: string;
  reason: string;
};

export function valueRuleFormFor(columnCode: string, plumValue: string): ValueRuleForm {
  return {
    columnCode,
    plumValue,
    actionCode: columnCode === "CAPACITY" ? "SPLIT_NUMBER_AND_UNIT" : "NOT_A_VALUE",
    resultNumber: "",
    resultUnitCode: "",
    resultClassCode: "",
    resultTypeCode: "",
    reason: "",
  };
}

export function valueRuleProblem(form: ValueRuleForm): string | null {
  if (!form.plumValue.trim()) return "Give the value as Plum records it.";
  if (form.actionCode === "SPLIT_NUMBER_AND_UNIT") {
    if (!/^\d+(\.\d{1,3})?$/.test(form.resultNumber.trim()) || Number(form.resultNumber) <= 0) return "Give the number the value holds.";
    if (!form.resultUnitCode) return "Choose the unit the value is in.";
  }
  if (form.actionCode === "REASSIGN_TO_TYPE" && (!form.resultClassCode || !form.resultTypeCode)) return "Choose the kind of machine and the type the value names.";
  if (!form.reason.trim()) return "Give the reason for reading the value this way.";
  return null;
}

export function valueRulePayload(form: ValueRuleForm, importPublicId: string | null): Record<string, unknown> {
  return {
    column_code: form.columnCode,
    plum_value: form.plumValue,
    action_code: form.actionCode,
    result_number: form.actionCode === "SPLIT_NUMBER_AND_UNIT" ? form.resultNumber.trim() : null,
    result_unit_code: form.actionCode === "SPLIT_NUMBER_AND_UNIT" ? form.resultUnitCode : null,
    result_class_code: form.actionCode === "REASSIGN_TO_TYPE" ? form.resultClassCode : null,
    result_type_code: form.actionCode === "REASSIGN_TO_TYPE" ? form.resultTypeCode : null,
    reason: form.reason.trim(),
    import_public_id: importPublicId,
  };
}

/**
 * What a preview row was read with, in words: every correction of the machine and every reading of a Plum
 * value that decided it. Shown beside the row whether or not a flag remains, so a confirmation never takes
 * in a corrected or re-read value unseen (independent review, round 1, ERT1-R1-006).
 */
export function rowReadingLines(
  row: Pick<PreviewRow, "corrections" | "rules_applied" | "closing_links" | "asset_public_id">,
  structure: Structure | null,
): string[] {
  const lines: string[] = [];
  // A fitted part the report will take off its machine (independent review, round 3, ERT1-R3-001).
  for (const link of row.closing_links) {
    lines.push(
      link.part_asset_public_id === row.asset_public_id
        ? `Will be taken off ${link.machine_machine_number}: after this report the two no longer fit together.`
        : `${link.part_machine_number} will be taken off it: after this report the two no longer fit together.`,
    );
  }
  for (const correction of row.corrections) {
    const field = FIELD_LABELS[correction.field_code] ?? correction.field_code;
    const value = correction.corrected_value_label === null ? "" : ` as ${correction.corrected_value_label}`;
    if (correction.effect_code === "PLUM_AGREES") lines.push(`${field}: Plum now holds the corrected value, so the correction closes when this report is confirmed.`);
    else if (correction.effect_code === "PLUM_CHANGED") lines.push(`${field}: Plum now holds another value. The correction still applies${value}; keep it or close it on the machine's page.`);
    else lines.push(`${field}: corrected${value}, not as Plum holds it.`);
  }
  for (const rule of row.rules_applied) {
    const column = FIELD_LABELS[rule.column_code] ?? rule.column_code;
    const plum = rule.plum_value === null ? "Plum's value" : `"${rule.plum_value}"`;
    if (rule.action_code === "SPLIT_NUMBER_AND_UNIT") {
      const unit = structure?.units.find((item) => item.unit_code === rule.result_unit_code);
      lines.push(`${column}: ${plum} read as ${plainNumber(rule.result_number)} ${unit?.unit_symbol || unit?.unit_label || rule.result_unit_code || ""}`.trimEnd() + ".");
    } else if (rule.action_code === "REASSIGN_TO_TYPE") {
      const equipmentClass = findClass(structure, rule.result_class_code);
      const type = equipmentClass?.types.find((item) => item.type_code === rule.result_type_code);
      lines.push(`${column}: ${plum} read as naming a type, ${equipmentClass?.class_label ?? rule.result_class_code} - ${type?.type_label ?? rule.result_type_code}.`);
    } else {
      lines.push(`${column}: ${plum} read as nothing entered.`);
    }
  }
  return lines;
}

/** The columns a flag on a preview row lets Admin record a reading for, with Plum's value in each. */
export function readableValues(row: PreviewRow): { columnCode: string; plumValue: string }[] {
  const readable: { columnCode: string; plumValue: string }[] = [];
  const capacityFlag = row.flags.some((flag) => ["NOT_A_NUMBER", "OUT_OF_PATTERN", "UNIT_UNCLEAR"].includes(flag.flag_code) && flag.subject_code !== "COMMENCED_YEAR");
  if (capacityFlag && row.plum.capacity) readable.push({ columnCode: "CAPACITY", plumValue: row.plum.capacity });
  const yearFlag = row.flags.some((flag) => flag.flag_code === "OUT_OF_PATTERN" && flag.subject_code === "COMMENCED_YEAR");
  if (yearFlag && row.plum.commenced_year) readable.push({ columnCode: "COMMENCED_YEAR", plumValue: row.plum.commenced_year });
  return readable;
}

// --- Pairs on a preview --------------------------------------------------------------------------------------

export type PairChoice = { machineNumber: string; confirmed: boolean };

/** Each part starts with the proposed machine chosen but not confirmed: Admin confirms each pair. */
export function initialPairChoices(preview: ImportPreview): Record<string, PairChoice> {
  const choices: Record<string, PairChoice> = {};
  for (const proposal of preview.pair_proposals) {
    choices[proposal.part_machine_number] = { machineNumber: proposal.proposed_machine_number ?? "", confirmed: false };
  }
  return choices;
}

export function confirmedPairs(choices: Record<string, PairChoice>): { part_machine_number: string; machine_machine_number: string }[] {
  return Object.entries(choices)
    .filter(([, choice]) => choice.confirmed && choice.machineNumber)
    .map(([part, choice]) => ({ part_machine_number: part, machine_machine_number: choice.machineNumber }));
}

/** Two parts confirmed to one machine cannot both be fitted to it. */
export function pairChoicesProblem(choices: Record<string, PairChoice>): string | null {
  const seen = new Set<string>();
  for (const pair of confirmedPairs(choices)) {
    if (seen.has(pair.machine_machine_number)) return `${pair.machine_machine_number} is chosen for two parts. Choose one part for it.`;
    seen.add(pair.machine_machine_number);
  }
  return null;
}

// --- The preview page -------------------------------------------------------------------------------------------

export type Feedback = { kind: "success" | "error"; text: string } | null;

export type PreviewState = {
  // The import the page is for: an answer about any other import changes nothing here.
  publicId: string | null;
  equipmentImport: EquipmentImport | null;
  latestLoad: number | null;
  loadError: string;
  // Admin recorded a mapping or a reading since this preview was computed: it must be refreshed.
  changedSinceComputed: boolean;
  pairs: Record<string, PairChoice>;
  actionFeedback: Feedback;
  // Feedback beside the item that caused it: a name mapped, a value read.
  itemFeedback: Record<string, Feedback>;
  // The action awaited - Refresh, Confirm or Discard. Only its answer may give the message or unlock the
  // buttons; a load never does (independent review, round 3, ERT1-R3-002).
  pendingAction: number | null;
};

export const INITIAL_PREVIEW_STATE: PreviewState = {
  publicId: null,
  equipmentImport: null,
  latestLoad: null,
  loadError: "",
  changedSinceComputed: false,
  pairs: {},
  actionFeedback: null,
  itemFeedback: {},
  pendingAction: null,
};

export type PreviewAction =
  | { type: "load-started"; ticket: number; publicId: string }
  | { type: "loaded"; ticket: number; equipmentImport: EquipmentImport }
  | { type: "load-failed"; ticket: number; text: string }
  | { type: "action-started"; publicId: string; ticket: number }
  | { type: "refreshed"; ticket: number; equipmentImport: EquipmentImport }
  | { type: "published"; ticket: number; equipmentImport: EquipmentImport; replayed: boolean }
  | { type: "discarded"; ticket: number; equipmentImport: EquipmentImport }
  | { type: "action-refused"; publicId: string; ticket: number; text: string }
  | { type: "item-recorded"; publicId: string; key: string; text: string }
  | { type: "item-refused"; publicId: string; key: string; text: string }
  | { type: "pair-changed"; part: string; choice: PairChoice };

/**
 * How late a copy of an import is: a confirmed or discarded import is later than any preview of it, and a
 * preview with a higher version is later than one with a lower. Answers can arrive in any order; an earlier
 * copy never replaces a later one (independent review, round 2, ERT1-R2-004).
 */
export function importOrder(equipmentImport: EquipmentImport): number {
  return (equipmentImport.import_status_code === "PREVIEWED" ? 0 : 1_000_000_000) + equipmentImport.preview_version;
}

// A later copy of the import replaces the pair choices made on the one before it: a choice kept across a
// refresh might name a machine the new preview no longer offers; an earlier copy is not installed. An
// answer about another import is ignored, and so is an action's answer that is not the one awaited - an
// older action's changes nothing at all, whatever copy it carries (independent review, round 4,
// ERT1-R4-002). The awaited action's answer (`answer`, with its ticket) gives the message and unlocks the
// buttons; a load's (`answer` null) leaves both.
function installedPreview(
  state: PreviewState,
  equipmentImport: EquipmentImport,
  answer: { ticket: number; feedback: Feedback } | null,
): PreviewState {
  if (equipmentImport.import_public_id !== state.publicId) return state;
  if (answer !== null && answer.ticket !== state.pendingAction) return state;
  const settled = answer !== null
    ? { pendingAction: null, actionFeedback: answer.feedback }
    : { pendingAction: state.pendingAction, actionFeedback: state.pendingAction !== null ? state.actionFeedback : null };
  if (state.equipmentImport && importOrder(equipmentImport) < importOrder(state.equipmentImport)) return { ...state, ...settled };
  return {
    ...INITIAL_PREVIEW_STATE,
    publicId: state.publicId,
    latestLoad: state.latestLoad,
    equipmentImport,
    pairs: initialPairChoices(equipmentImport.preview),
    ...settled,
  };
}

export function previewReducer(state: PreviewState, action: PreviewAction): PreviewState {
  switch (action.type) {
    case "load-started":
      // Another import: the one shown and every choice made on it go at once.
      return action.publicId === state.publicId
        ? { ...state, latestLoad: action.ticket, loadError: "" }
        : { ...INITIAL_PREVIEW_STATE, publicId: action.publicId, latestLoad: action.ticket };
    case "loaded": {
      if (action.ticket !== state.latestLoad) return state;
      const settled = { ...state, latestLoad: null, loadError: "" };
      const shown = state.equipmentImport;
      if (!shown) return installedPreview(settled, action.equipmentImport, null);
      const order = importOrder(action.equipmentImport) - importOrder(shown);
      // The same copy keeps the choices made on it, and takes whether it is still current.
      if (order === 0 && action.equipmentImport.import_public_id === state.publicId) return { ...settled, equipmentImport: action.equipmentImport };
      return order > 0 ? installedPreview(settled, action.equipmentImport, null) : settled;
    }
    case "load-failed":
      return action.ticket === state.latestLoad ? { ...state, latestLoad: null, loadError: action.text } : state;
    case "action-started":
      return action.publicId === state.publicId ? { ...state, pendingAction: action.ticket, actionFeedback: null } : state;
    case "refreshed":
      return installedPreview(state, action.equipmentImport, {
        ticket: action.ticket,
        feedback: { kind: "success", text: "Preview refreshed with everything as it stands now." },
      });
    case "published":
      return installedPreview(state, action.equipmentImport, {
        ticket: action.ticket,
        feedback: {
          kind: "success",
          text: action.replayed ? "This report was already confirmed; nothing was done twice." : "Report confirmed. The machines are updated.",
        },
      });
    case "discarded":
      return installedPreview(state, action.equipmentImport, { ticket: action.ticket, feedback: { kind: "success", text: "Preview discarded. Nothing was changed." } });
    case "action-refused":
      return action.publicId === state.publicId && action.ticket === state.pendingAction
        ? { ...state, pendingAction: null, actionFeedback: { kind: "error", text: action.text } }
        : state;
    case "item-recorded":
      return action.publicId === state.publicId
        ? { ...state, changedSinceComputed: true, itemFeedback: { ...state.itemFeedback, [action.key]: { kind: "success", text: action.text } } }
        : state;
    case "item-refused":
      return action.publicId === state.publicId ? { ...state, itemFeedback: { ...state.itemFeedback, [action.key]: { kind: "error", text: action.text } } } : state;
    case "pair-changed":
      return { ...state, pairs: { ...state.pairs, [action.part]: action.choice }, actionFeedback: null };
    default:
      return state;
  }
}

export type ImportActionPath = "refresh" | "publish" | "discard";

/**
 * The preview page's loading and its three actions, kept out of the component (ERT1-R2-004). Every load
 * takes a ticket, and only the latest may show; every answer names the import it is about, and the reducer
 * installs it only on that import's page and only if it is not earlier than what is shown.
 */
export function createPreviewController(deps: {
  getToken: () => string | null;
  // Each resolves with the import, or rejects with an Error whose message is what to show.
  fetchImport: (token: string, publicId: string) => Promise<EquipmentImport>;
  sendAction: (token: string, publicId: string, path: ImportActionPath, body: Record<string, unknown>) => Promise<{ equipment_import: EquipmentImport; replayed: boolean }>;
  dispatch: (action: PreviewAction) => void;
}) {
  const loads = createLatestOnly();
  let actions = 0;
  const failure = (error: unknown, fallback: string) => (error instanceof Error ? error.message : fallback);

  async function load(publicId: string): Promise<void> {
    const ticket = loads.begin();
    deps.dispatch({ type: "load-started", ticket, publicId });
    const token = deps.getToken();
    if (!token) {
      deps.dispatch({ type: "load-failed", ticket, text: SIGN_IN_FIRST });
      return;
    }
    try {
      const equipmentImport = await deps.fetchImport(token, publicId);
      if (loads.isLatest(ticket)) deps.dispatch({ type: "loaded", ticket, equipmentImport });
    } catch (error) {
      if (loads.isLatest(ticket)) deps.dispatch({ type: "load-failed", ticket, text: failure(error, "The report could not be loaded.") });
    }
  }

  async function act(path: ImportActionPath, equipmentImport: EquipmentImport, pairs: Record<string, PairChoice>): Promise<void> {
    const publicId = equipmentImport.import_public_id;
    actions += 1;
    const ticket = actions;
    deps.dispatch({ type: "action-started", publicId, ticket });
    const token = deps.getToken();
    if (!token) {
      deps.dispatch({ type: "action-refused", publicId, ticket, text: SIGN_IN_FIRST });
      return;
    }
    const body: Record<string, unknown> = { expected_preview_version: equipmentImport.preview_version };
    if (path === "publish") body.pairs = confirmedPairs(pairs);
    try {
      const result = await deps.sendAction(token, publicId, path, body);
      if (path === "refresh") deps.dispatch({ type: "refreshed", ticket, equipmentImport: result.equipment_import });
      else if (path === "publish") deps.dispatch({ type: "published", ticket, equipmentImport: result.equipment_import, replayed: result.replayed });
      else deps.dispatch({ type: "discarded", ticket, equipmentImport: result.equipment_import });
    } catch (error) {
      deps.dispatch({ type: "action-refused", publicId, ticket, text: failure(error, "That was not done.") });
    }
  }

  return { load, act };
}

/** Why Confirm is not offered now, or null when it is. */
export function confirmProblem(state: PreviewState): string | null {
  const equipmentImport = state.equipmentImport;
  if (!equipmentImport || equipmentImport.import_status_code !== "PREVIEWED") return "Only a preview can be confirmed.";
  if (state.changedSinceComputed) return "You changed a mapping or a reading. Refresh the preview to see its effect before confirming.";
  if (!equipmentImport.is_current) return equipmentImport.stale_reason ?? "This preview is out of date. Refresh it.";
  return pairChoicesProblem(state.pairs);
}

/** The rows a preview shows by default: those needing attention - set aside, new, changed, flagged. */
export function attentionRows(preview: ImportPreview, showAll: boolean): PreviewRow[] {
  return showAll ? preview.rows : preview.rows.filter((row) => row.needs_attention && row.outcome_code !== "NOT_BROUGHT_IN");
}

// --- The machine page ---------------------------------------------------------------------------------------------

export type MachineForm = "details" | "capabilities" | "correction" | "fit" | "kit" | "retire" | null;

export type MachineState = {
  // The machine the page is for: a save answered for any other changes nothing here.
  publicId: string | null;
  machine: Machine | null;
  latestLoad: number | null;
  loadError: string;
  openForm: MachineForm;
  feedback: Record<string, Feedback>;
  // The save awaited. Only its answer, on this machine's page, may give a message or unlock the forms; a
  // load never does (independent review, round 3, ERT1-R3-003).
  pendingSave: number | null;
  // When the request for the machine shown was sent, in the order of every request for this page's view. Kit
  // held for the model changes the view without changing the machine's version (ERT2-R1-002).
  shownView: number;
};

export const INITIAL_MACHINE_STATE: MachineState = {
  publicId: null,
  machine: null,
  latestLoad: null,
  loadError: "",
  openForm: null,
  feedback: {},
  pendingSave: null,
  shownView: 0,
};

export type MachineAction =
  | { type: "load-started"; ticket: number; publicId: string }
  | { type: "loaded"; ticket: number; machine: Machine; view: number }
  | { type: "load-failed"; ticket: number; text: string }
  | { type: "form-opened"; form: MachineForm }
  | { type: "save-started"; publicId: string; ticket: number }
  | { type: "saved"; ticket: number; machine: Machine; key: string; text: string; view: number }
  | { type: "refused"; publicId: string; ticket: number; key: string; text: string };

/**
 * A later version of the machine replaces every open form and message made against the version before it:
 * a form kept across a reload would be sent with the new version number and silently undo what someone else
 * changed (the WRR-001 rule, rounds 1 and 2). Answers - loads and saves - can arrive in any order, so what
 * decides is the version, never the arrival: an earlier version never replaces a later one, and the same
 * version keeps the forms made on it (independent review, round 2, ERT1-R2-005). The same version can still
 * show different kit - what is held for its model changes without it - so between two answers of one version,
 * the one asked for later wins (ERT2-R1-002). Only the latest load may install. A load of another machine
 * stops showing the one before at once, so nothing is done to it under the new machine's address, and a save
 * answered for another machine changes nothing.
 */
function installedMachine(state: MachineState, machine: Machine, feedback: Record<string, Feedback>, view: number): MachineState {
  const shown = state.machine;
  const kept = { ...state, feedback: { ...state.feedback, ...feedback } };
  if (shown && machine.asset_version < shown.asset_version) return kept;
  if (shown && machine.asset_version === shown.asset_version) return view < state.shownView ? kept : { ...kept, machine, shownView: view };
  return { ...INITIAL_MACHINE_STATE, publicId: state.publicId, latestLoad: state.latestLoad, pendingSave: state.pendingSave, machine, feedback, shownView: view };
}

export function machineReducer(state: MachineState, action: MachineAction): MachineState {
  switch (action.type) {
    case "load-started":
      return action.publicId === state.publicId
        ? { ...state, latestLoad: action.ticket, loadError: "" }
        : { ...INITIAL_MACHINE_STATE, publicId: action.publicId, latestLoad: action.ticket };
    case "loaded":
      return action.ticket === state.latestLoad && action.machine.asset_public_id === state.publicId
        ? installedMachine({ ...state, latestLoad: null, loadError: "" }, action.machine, {}, action.view)
        : state;
    case "load-failed":
      return action.ticket === state.latestLoad ? { ...state, latestLoad: null, loadError: action.text } : state;
    case "form-opened":
      return { ...state, openForm: action.form, feedback: {} };
    case "save-started":
      return action.publicId === state.publicId ? { ...state, pendingSave: action.ticket } : state;
    case "saved": {
      if (action.machine.asset_public_id !== state.publicId) return state;
      // An older save's answer - from before the page was left and opened again - installs a later version
      // but says nothing and unlocks nothing.
      if (action.ticket !== state.pendingSave) return installedMachine(state, action.machine, {}, action.view);
      return { ...installedMachine(state, action.machine, { [action.key]: { kind: "success", text: action.text } }, action.view), pendingSave: null };
    }
    case "refused":
      return action.publicId === state.publicId && action.ticket === state.pendingSave
        ? { ...state, pendingSave: null, feedback: { ...state.feedback, [action.key]: { kind: "error", text: action.text } } }
        : state;
    default:
      return state;
  }
}

export type MachineEvent = { public_id: string; event_name: string; event_timestamp: string; reason: string | null };

export type MachineReferences = { structure: Structure | null; models: EquipmentModel[] };

/**
 * The machine page's loading, kept out of the component (independent review, round 1, ERT1-R1-005). The
 * machine and its events are one view. Every load takes a ticket before anything else and clears the events
 * shown, so another machine's events are never shown under this one; an answer for a load no longer awaited
 * - an older one, or another machine's after the page moved on - installs nothing and asks for no events;
 * and only the latest request for events may show them.
 */
export function createMachineLoader(deps: {
  getToken: () => string | null;
  // Resolves with the machine, or rejects with an Error whose message is what to show.
  fetchMachine: (token: string, publicId: string) => Promise<Machine>;
  fetchEvents: (token: string, publicId: string) => Promise<MachineEvent[]>;
  dispatch: (action: MachineAction) => void;
  showEvents: (events: MachineEvent[]) => void;
  // The structure and models the page's forms offer choices from, read with every load and shown only for
  // the latest one, as the machine is (independent review, round 4, ERT2-R4-004).
  fetchReferences?: (token: string) => Promise<MachineReferences>;
  showReferences?: (references: MachineReferences) => void;
}) {
  const machines = createLatestOnly();
  const events = createLatestOnly();
  let saves = 0;
  // Every request whose answer is a view of the machine takes its place in one order when it is sent: loads,
  // saves, and the reading again after kit is added (ERT2-R1-002).
  let views = 0;
  const saveViews = new Map<number, number>();
  // The machine the page is for: a save answered after the page moved to another machine installs nothing.
  let current: string | null = null;

  async function loadEvents(token: string, publicId: string): Promise<void> {
    const ticket = events.begin();
    let rows: MachineEvent[] = [];
    try {
      rows = await deps.fetchEvents(token, publicId);
    } catch {
      rows = [];
    }
    if (events.isLatest(ticket)) deps.showEvents(rows);
  }

  async function load(publicId: string): Promise<void> {
    const ticket = machines.begin();
    const view = (views += 1);
    current = publicId;
    events.begin();
    deps.showEvents([]);
    deps.dispatch({ type: "load-started", ticket, publicId });
    const token = deps.getToken();
    if (!token) {
      deps.dispatch({ type: "load-failed", ticket, text: SIGN_IN_FIRST });
      return;
    }
    const references = deps.fetchReferences ? deps.fetchReferences(token).catch(() => null) : Promise.resolve(null);
    let machine: Machine;
    try {
      machine = await deps.fetchMachine(token, publicId);
    } catch (error) {
      if (machines.isLatest(ticket)) deps.dispatch({ type: "load-failed", ticket, text: error instanceof Error ? error.message : "The machine could not be loaded." });
      return;
    }
    if (!machines.isLatest(ticket)) return;
    deps.dispatch({ type: "loaded", ticket, machine, view });
    const shown = await references;
    if (shown && machines.isLatest(ticket)) deps.showReferences?.(shown);
    await loadEvents(token, publicId);
  }

  return {
    load,
    /** A save starts: its ticket, carried by its answer, says which save the page is waiting for. */
    beginSave: (publicId: string): number => {
      saves += 1;
      views += 1;
      saveViews.set(saves, views);
      deps.dispatch({ type: "save-started", publicId, ticket: saves });
      return saves;
    },
    /** A view asked for as part of a save - the machine read again once kit is added - takes its place in the
     *  order when it is asked for, not when its save began. */
    beginView: (): number => (views += 1),
    /** A save was refused, or its answer was lost: shown only on the page of the machine it was made on. */
    refused: (ticket: number, publicId: string, key: string, text: string): void => {
      deps.dispatch({ type: "refused", publicId, ticket, key, text });
    },
    /**
     * A save's answer: installed unless a later version is already shown (the reducer decides, by version,
     * not by when it arrived). It cancels no load: a reload begun since may bring a later version still.
     * The machine's events are read again.
     */
    saved: (ticket: number, machine: Machine, key: string, text: string, view?: number): Promise<void> => {
      if (machine.asset_public_id !== current) return Promise.resolve();
      deps.dispatch({ type: "saved", ticket, machine, key, text, view: view ?? saveViews.get(ticket) ?? 0 });
      const token = deps.getToken();
      return token ? loadEvents(token, machine.asset_public_id) : Promise.resolve();
    },
  };
}

/** The value a correction form sends for a field, and why it cannot be sent yet. */
export function correctionProblem(fieldCode: string, value: string, reason: string): string | null {
  if (!fieldCode) return "Choose the field to correct.";
  if (!value.trim()) return "Give the correct value.";
  if (fieldCode === "COMMENCED_YEAR" && !/^\d{4}$/.test(value.trim())) return "Give the commenced year as four digits.";
  if (fieldCode === "CAPACITY" && (!/^\d+(\.\d{1,3})?$/.test(value.trim()) || Number(value) <= 0)) return "Give the capacity as a plain number.";
  if (!reason.trim()) return "Give the reason for the correction.";
  return null;
}
