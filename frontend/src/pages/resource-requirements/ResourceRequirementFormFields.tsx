import {
  type EquipmentStructure,
  type LineFacts,
  type RequirementForm,
  PRIORITY_OPTIONS,
  capabilityFieldLabel,
  capabilityFields,
  contractText,
  findClass,
  formAfterClassChange,
  formWithCapabilityValue,
  hiringClasses,
  lineDatesText,
  typeOptions,
  workOrderCrewText,
} from "./resourceRequirementState";
import DateInput from "../../components/DateInput";

// The fields of a requirement, shared by the new-requirement page and the change form. The page owns the
// Save button and its messages; this owns only the fields and the line's facts shown beside them.

type Props = {
  form: RequirementForm;
  structure: EquipmentStructure | null;
  line: LineFacts;
  onChange: (next: RequirementForm) => void;
  // On a change, the type and capabilities already saved stay offered even if retired since.
  keptTypeCode?: string;
  keptCapabilityCodes?: readonly string[];
  // Why the class was suggested, on a new requirement: the word in the line's category that matched.
  suggestedFrom?: string | null;
};

const HINT_STYLE = { color: "#6b7280", fontSize: "0.9em", fontWeight: 400 } as const;
// Fields sit at the top of their row rather than stretching to its height, so a hint beneath one field
// never pushes the boxes beside it down. Hints go beneath the box, never between the label and the box.
const GRID_STYLE = { alignItems: "start" } as const;

export default function ResourceRequirementFormFields({
  form,
  structure,
  line,
  onChange,
  keptTypeCode = "",
  keptCapabilityCodes = [],
  suggestedFrom = null,
}: Props) {
  const classes = hiringClasses(structure);
  const selectedClass = findClass(structure, form.equipment_class_code);
  // A class retired since the requirement was saved stays selectable on that requirement.
  const classOptions =
    selectedClass && !classes.some((item) => item.class_code === selectedClass.class_code) ? [...classes, selectedClass] : classes;
  const capabilities = capabilityFields(selectedClass, [...keptCapabilityCodes, ...Object.keys(form.capability_values)]);
  const set = (patch: Partial<RequirementForm>) => onChange({ ...form, ...patch });

  return (
    <div style={{ display: "grid", gap: "14px" }}>
      <fieldset style={{ border: "1px solid #e5e7eb", padding: "12px" }}>
        <legend style={{ fontWeight: 700 }}>What is needed</legend>
        <div className="form-grid" style={GRID_STYLE}>
          <label className="field-stack">
            Number of machines
            <input
              type="number"
              min={1}
              step={1}
              value={form.units_required}
              onChange={(event) => set({ units_required: event.target.value })}
            />
            <span style={HINT_STYLE}>
              The line's quantity, {line.quantity} {line.uom}, counts billing units, not machines.
            </span>
          </label>
          <label className="field-stack">
            Kind of machine
            <select value={form.equipment_class_code} onChange={(event) => onChange(formAfterClassChange(form, event.target.value))}>
              <option value="">Choose...</option>
              {classOptions.map((item) => (
                <option key={item.class_code} value={item.class_code}>
                  {item.class_label}
                </option>
              ))}
            </select>
            {suggestedFrom ? <span style={HINT_STYLE}>Suggested from the line's category, "{suggestedFrom}".</span> : null}
          </label>
          <label className="field-stack">
            Type
            <select
              value={form.equipment_type_code}
              onChange={(event) => set({ equipment_type_code: event.target.value })}
              disabled={!selectedClass || selectedClass.types.length === 0}
            >
              <option value="">Any type</option>
              {typeOptions(selectedClass, keptTypeCode).map((item) => (
                <option key={item.type_code} value={item.type_code}>
                  {item.type_label}
                </option>
              ))}
            </select>
          </label>
        </div>

        {capabilities.length > 0 ? (
          <div className="form-grid" style={{ ...GRID_STYLE, marginTop: "10px" }}>
            {capabilities.map((capability) => (
              <label className="field-stack" key={capability.capability_code}>
                {capability.value_kind_code === "CHOICE" ? capabilityFieldLabel(capability) : `${capabilityFieldLabel(capability)}, at least`}
                {capability.value_kind_code === "CHOICE" ? (
                  <select
                    value={form.capability_values[capability.capability_code] ?? ""}
                    onChange={(event) => onChange(formWithCapabilityValue(form, capability.capability_code, event.target.value))}
                  >
                    <option value="">Any</option>
                    {(capability.allowed_values ?? []).map((value) => (
                      <option key={value} value={value}>
                        {value}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    inputMode="decimal"
                    value={form.capability_values[capability.capability_code] ?? ""}
                    onChange={(event) => onChange(formWithCapabilityValue(form, capability.capability_code, event.target.value))}
                  />
                )}
                {capability.is_key ? <span style={HINT_STYLE}>The main capability: planners compare this first.</span> : null}
              </label>
            ))}
          </div>
        ) : null}

        <label className="field-stack" style={{ marginTop: "10px" }}>
          Anything else about the machine (optional)
          <textarea
            rows={2}
            maxLength={1000}
            value={form.equipment_specification}
            onChange={(event) => set({ equipment_specification: event.target.value })}
            placeholder="For example: fly jib, attachments, counterweight"
          />
        </label>
      </fieldset>

      <fieldset style={{ border: "1px solid #e5e7eb", padding: "12px" }}>
        <legend style={{ fontWeight: 700 }}>When</legend>
        <div className="form-grid" style={GRID_STYLE}>
          <label className="field-stack">
            Needed from
            <DateInput value={form.required_from} onChange={(event) => set({ required_from: event.target.value })} />
          </label>
          <label className="field-stack">
            Needed until (optional)
            <DateInput value={form.required_to} onChange={(event) => set({ required_to: event.target.value })} />
            <span style={HINT_STYLE}>Leave empty for "until the line ends".</span>
          </label>
        </div>
        <p style={{ ...HINT_STYLE, margin: "8px 0 0 0" }}>
          Contract: {contractText(line)}. This line: {lineDatesText(line)}. The dates must sit inside both.
        </p>
      </fieldset>

      <fieldset style={{ border: "1px solid #e5e7eb", padding: "12px" }}>
        <legend style={{ fontWeight: 700 }}>Crew on site</legend>
        <div className="form-grid" style={GRID_STYLE}>
          <label className="field-stack">
            Operators
            <input type="number" min={0} step={1} value={form.crew_operators_required} onChange={(event) => set({ crew_operators_required: event.target.value })} />
          </label>
          <label className="field-stack">
            Helpers
            <input type="number" min={0} step={1} value={form.crew_helpers_required} onChange={(event) => set({ crew_helpers_required: event.target.value })} />
          </label>
        </div>
        <p style={{ ...HINT_STYLE, margin: "8px 0 0 0" }}>
          The Work Order's terms: {workOrderCrewText(line)}. These are what the customer is charged for, never what the crew
          are paid.
        </p>
        <label className="field-stack" style={{ marginTop: "10px" }}>
          Licences and skills needed (optional)
          <textarea rows={2} maxLength={2000} value={form.crew_notes} onChange={(event) => set({ crew_notes: event.target.value })} />
        </label>
      </fieldset>

      <div className="form-grid" style={GRID_STYLE}>
        <label className="field-stack">
          Priority
          <select value={form.priority_code} onChange={(event) => set({ priority_code: event.target.value })}>
            {PRIORITY_OPTIONS.map((option) => (
              <option key={option.code} value={option.code}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="field-stack">
        Anything planning must know (optional)
        <textarea
          rows={3}
          maxLength={4000}
          value={form.planning_notes}
          onChange={(event) => set({ planning_notes: event.target.value })}
          placeholder="For example: site access, tide windows, working hours"
        />
      </label>
    </div>
  );
}
