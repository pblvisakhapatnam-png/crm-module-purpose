import { useEffect, useReducer, useState } from "react";
import { useParams } from "react-router-dom";

import { PageHeader, SectionCard } from "../../components/PageLayout";
import { clearSession, formatDateTime, getToken, readErrorDetail } from "../resource-requirements/pageSession";
import { EquipmentNav, FeedbackLine } from "./EquipmentParts";
import {
  FIELD_LABELS,
  IMPORT_STATUS_LABELS,
  INITIAL_PREVIEW_STATE,
  VALUE_RULE_ACTION_LABELS,
  type EquipmentImport,
  type EquipmentModel,
  type Feedback,
  type ImportActionPath,
  type PreviewRow,
  type Structure,
  type UnmappedName,
  type ValueRuleForm,
  attentionRows,
  capabilityLabels,
  confirmProblem,
  createPreviewController,
  findClass,
  flagLabel,
  machineClasses,
  outcomeLabel,
  previewReducer,
  readableValues,
  rowReadingLines,
  reasonLabel,
  valueRuleFormFor,
  valueRulePayload,
  valueRuleProblem,
} from "./equipmentState";

// One uploaded report (ERT-1, design section 5): what confirming it would do, and the actions beside each
// item - map a model name, read a doubtful value another way, pair a carrier with its crane. Mapping or
// reading takes effect when the preview is refreshed; confirming applies it all in one step. What each
// answer does to the page is previewReducer's and createPreviewController's, tested on their own.

const OUTCOME_ORDER = ["NEW", "CHANGED", "UNCHANGED", "RETIRED", "REACTIVATED", "NOT_BROUGHT_IN", "SET_ASIDE", "MISSING"];

export default function ImportPreviewPage() {
  const params = useParams();
  const importId = params?.importId;
  const [state, dispatch] = useReducer(previewReducer, INITIAL_PREVIEW_STATE);
  const [structure, setStructure] = useState<Structure | null>(null);
  const [models, setModels] = useState<EquipmentModel[]>([]);
  const [showAll, setShowAll] = useState(false);
  const [waiting, setWaiting] = useState(false);
  const equipmentImport = state.equipmentImport;
  const loadError = state.loadError;
  const busy = state.pendingAction !== null;

  // Loads and the three actions; each answer names its import, and only the later copy is shown.
  const [controller] = useState(() =>
    createPreviewController({
      getToken,
      fetchImport: async (token, publicId) => {
        let response: Response;
        try {
          response = await fetch(`/api/equipment-reference/imports/${encodeURIComponent(publicId)}`, { headers: { Authorization: `Bearer ${token}` } });
        } catch {
          throw new Error("Network error while loading the report.");
        }
        if (response.status === 401) clearSession();
        if (!response.ok) throw new Error(await readErrorDetail(response, "The report could not be loaded."));
        return (await response.json()) as EquipmentImport;
      },
      sendAction: async (token, publicId, path, body) => {
        let response: Response;
        try {
          response = await fetch(`/api/equipment-reference/imports/${encodeURIComponent(publicId)}/${path}`, {
            method: "POST",
            headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
        } catch {
          throw new Error("Network error: it may or may not have been done. Reload the report to see.");
        }
        if (response.status === 401) clearSession();
        if (!response.ok) throw new Error(await readErrorDetail(response, "That was not done."));
        return (await response.json()) as { equipment_import: EquipmentImport; replayed: boolean };
      },
      dispatch,
    }),
  );
  const load = (publicId: string) => controller.load(publicId);

  async function loadModels() {
    const token = getToken();
    if (!token) return;
    try {
      const response = await fetch("/api/equipment-reference/models", { headers: { Authorization: `Bearer ${token}` } });
      if (response.ok) setModels((await response.json()) as EquipmentModel[]);
    } catch {
      // The mapping choices only.
    }
  }

  useEffect(() => {
    setWaiting(new URLSearchParams(window.location.search).get("waiting") === "1");
    if (typeof importId === "string") void load(importId);
    void loadModels();
    const token = getToken();
    if (token) {
      void (async () => {
        try {
          const response = await fetch("/api/equipment-reference/structure", { headers: { Authorization: `Bearer ${token}` } });
          if (response.ok) setStructure((await response.json()) as Structure);
        } catch {
          // Labels only.
        }
      })();
    }
  }, [importId]);

  function act(path: ImportActionPath) {
    if (equipmentImport) void controller.act(path, equipmentImport, state.pairs);
  }

  async function mapName(item: UnmappedName, modelPublicId: string) {
    const key = `map:${item.normalized_source_name}`;
    const token = getToken();
    if (!token || !equipmentImport) return;
    // The answer is shown only while this import is still the one on the page.
    const publicId = equipmentImport.import_public_id;
    try {
      const response = await fetch("/api/equipment-reference/model-mappings", {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ source_name: item.source_name, model_public_id: modelPublicId }),
      });
      if (!response.ok) {
        dispatch({ type: "item-refused", publicId, key, text: await readErrorDetail(response, "The name was not mapped.") });
        return;
      }
      dispatch({ type: "item-recorded", publicId, key, text: "Mapped. Refresh the preview to see its effect." });
    } catch {
      dispatch({ type: "item-refused", publicId, key, text: "Network error: the name may not have been mapped." });
    }
  }

  async function recordReading(key: string, form: ValueRuleForm): Promise<boolean> {
    const token = getToken();
    if (!token || !equipmentImport) return false;
    const publicId = equipmentImport.import_public_id;
    try {
      const response = await fetch("/api/equipment-reference/value-rules", {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(valueRulePayload(form, publicId)),
      });
      if (!response.ok) {
        dispatch({ type: "item-refused", publicId, key, text: await readErrorDetail(response, "The reading was not recorded.") });
        return false;
      }
      dispatch({ type: "item-recorded", publicId, key, text: "Recorded for this value wherever it appears. Refresh the preview to see its effect." });
      return true;
    } catch {
      dispatch({ type: "item-refused", publicId, key, text: "Network error: the reading may not have been recorded." });
      return false;
    }
  }

  if (!equipmentImport) {
    return (
      <section>
        <PageHeader eyebrow="Equipment - Plum report" title="Report preview" back={{ href: "/equipment/plum-report", label: "Back to Plum report" }}>
          {loadError ? <p className="text-danger">{loadError}</p> : <p className="helper-text">Loading the report...</p>}
        </PageHeader>
      </section>
    );
  }

  const preview = equipmentImport.preview;
  const isPreview = equipmentImport.import_status_code === "PREVIEWED";
  const problem = confirmProblem(state);
  const labels = capabilityLabels(structure);
  const rows = attentionRows(preview, showAll);

  return (
    <section>
      <PageHeader
        eyebrow="Equipment - Plum report"
        title={`Report of ${equipmentImport.report_date}`}
        subtitle={`${IMPORT_STATUS_LABELS[equipmentImport.import_status_code] ?? equipmentImport.import_status_code}. ${equipmentImport.row_count} rows, uploaded by ${equipmentImport.uploaded_by_display_name ?? "-"} on ${formatDateTime(equipmentImport.uploaded_at)}. Fingerprint ${equipmentImport.fingerprint_prefix}.`}
        back={{ href: "/equipment/plum-report", label: "Back to Plum report" }}
        actions={
          <button type="button" onClick={() => typeof importId === "string" && void load(importId)}>
            Reload
          </button>
        }
      >
        {loadError ? <p className="text-danger">{loadError}</p> : null}
        {waiting ? <p className="helper-text">This report was already waiting as a preview, so that preview is shown.</p> : null}
        {/* Where the eye goes after mapping a name: Reload only re-reads this preview; Refresh computes it again. */}
        {equipmentImport.import_status_code === "PREVIEWED" && state.changedSinceComputed ? (
          <p className="text-warning">
            You mapped a name or recorded a reading since this preview was computed.{" "}
            <button type="button" disabled={busy} onClick={() => act("refresh")}>
              Refresh the preview
            </button>
          </p>
        ) : null}
      </PageHeader>
      <EquipmentNav current="" />

      <SectionCard title="What confirming would do">
        <ul>
          {OUTCOME_ORDER.filter((code) => preview.counts[code]).map((code) => (
            <li key={code}>
              {outcomeLabel(code)}: {preview.counts[code]}
            </li>
          ))}
        </ul>
        {isPreview ? (
          <>
            {!equipmentImport.is_current || state.changedSinceComputed ? (
              <p className="text-warning">{state.changedSinceComputed ? "You changed a mapping or a reading since this preview was computed." : equipmentImport.stale_reason}</p>
            ) : null}
            <div className="page-actions">
              <button type="button" disabled={busy} onClick={() => act("refresh")}>
                Refresh
              </button>
              <button type="button" disabled={busy || Boolean(problem)} onClick={() => act("publish")}>
                Confirm
              </button>
              <button type="button" disabled={busy} onClick={() => act("discard")}>
                Discard
              </button>
            </div>
            {problem && !state.actionFeedback ? <p className="helper-text">{problem}</p> : null}
          </>
        ) : null}
        <FeedbackLine feedback={state.actionFeedback} />
      </SectionCard>

      {isPreview && preview.unmapped_model_names.length ? (
        <SectionCard title="Model names to map">
          <p className="helper-text">
            Map each name once; every later report uses the mapping. A model not listed yet can be recorded on the{" "}
            <a href="/equipment/models">
              Models
            </a>{" "}
            page.
          </p>
          {preview.unmapped_model_names.map((item) => (
            <MapNameRow key={item.normalized_source_name} item={item} models={models} structure={structure} feedback={state.itemFeedback[`map:${item.normalized_source_name}`]} onMap={(id) => void mapName(item, id)} />
          ))}
        </SectionCard>
      ) : null}

      {isPreview && preview.pair_proposals.length ? (
        <SectionCard title="Crane halves to pair">
          <p className="helper-text">Each part is fitted to the machine you confirm when the report is confirmed. The proposal is the only crane of the same model without one.</p>
          {preview.pair_proposals.map((proposal) => {
            const choice = state.pairs[proposal.part_machine_number] ?? { machineNumber: "", confirmed: false };
            return (
              <div key={proposal.part_machine_number} className="page-actions actions-with-fields">
                <span>
                  Part <strong>{proposal.part_machine_number}</strong> fitted to
                </span>
                <label className="field-stack">
                  Machine
                  <select
                    aria-label={`Machine for ${proposal.part_machine_number}`}
                    value={choice.machineNumber}
                    onChange={(event) => dispatch({ type: "pair-changed", part: proposal.part_machine_number, choice: { machineNumber: event.target.value, confirmed: false } })}
                  >
                    <option value="">Not paired yet</option>
                    {proposal.candidates.map((candidate) => (
                      <option key={candidate.machine_number} value={candidate.machine_number}>
                        {candidate.machine_number}
                        {candidate.asset_reference ? ` (${candidate.asset_reference})` : " (in this report)"}
                        {candidate.machine_number === proposal.proposed_machine_number ? " - proposed" : ""}
                      </option>
                    ))}
                  </select>
                </label>
                <label>
                  <input
                    type="checkbox"
                    disabled={!choice.machineNumber}
                    checked={choice.confirmed}
                    onChange={(event) => dispatch({ type: "pair-changed", part: proposal.part_machine_number, choice: { ...choice, confirmed: event.target.checked } })}
                  />{" "}
                  Confirm pair for {proposal.part_machine_number}
                </label>
              </div>
            );
          })}
        </SectionCard>
      ) : null}

      <SectionCard title={showAll ? "Every row" : "Rows needing attention"}>
        <label>
          <input type="checkbox" checked={showAll} onChange={(event) => setShowAll(event.target.checked)} /> Show every row
        </label>
        <p className="helper-text">Lines are counted as in the file: line 1 is the report's title and line 2 its column headings, so the first machine is on line 3.</p>
        <div className="data-table-wrap">
          <table className="data-table data-table-wide">
            <thead>
              <tr>
                <th>Line in file</th>
                <th>Machine number</th>
                <th>Outcome</th>
                <th>Kind and model</th>
                <th>Flags, corrections and readings</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <PreviewRowLine
                  key={row.row_number}
                  row={row}
                  labels={labels}
                  structure={structure}
                  canRead={isPreview}
                  itemFeedback={state.itemFeedback}
                  onRecord={recordReading}
                />
              ))}
            </tbody>
          </table>
        </div>
        {rows.length === 0 ? <p className="helper-text">No row needs attention.</p> : null}
      </SectionCard>

      {preview.missing.length ? (
        <SectionCard title="Known machines missing from this report">
          <p className="helper-text">Not retired: an export may be partial. Each is flagged when the report is confirmed.</p>
          <ul>
            {preview.missing.map((item) => (
              <li key={item.asset_public_id}>
                <a href={`/equipment/machines/${item.asset_public_id}`}>
                  {item.asset_reference}
                </a>{" "}
                - {item.machine_number}
              </li>
            ))}
          </ul>
        </SectionCard>
      ) : null}
    </section>
  );
}

function MapNameRow({
  item,
  models,
  structure,
  feedback,
  onMap,
}: {
  item: UnmappedName;
  models: EquipmentModel[];
  structure: Structure | null;
  feedback: Feedback | undefined;
  onMap: (modelPublicId: string) => void;
}) {
  const [modelId, setModelId] = useState("");
  // A name under a category may map to a model of that kind, or to a part of that kind (a crane's carrier).
  const fitting = new Set([item.class_code, ...(structure?.classes ?? []).filter((c) => item.class_code && c.fits_class_codes.includes(item.class_code)).map((c) => c.class_code)]);
  const choices = models.filter((model) => !model.is_retired && fitting.has(model.class_code));
  return (
    <div className="divided-item">
      <div className="page-actions actions-with-fields">
        <span>
          <strong>{item.source_name}</strong> - {item.category ?? "no category"}, {item.machine_count} machine{item.machine_count === 1 ? "" : "s"}
          {item.make || item.model ? ` (make ${item.make ?? "-"}, model ${item.model ?? "-"})` : ""}
        </span>
        <label className="field-stack">
          Model
          <select aria-label={`Model for ${item.source_name}`} value={modelId} onChange={(event) => setModelId(event.target.value)}>
            <option value="">{choices.length ? "Choose a model" : "No model of this kind yet"}</option>
            {choices.map((model) => (
              <option key={model.model_public_id} value={model.model_public_id}>
                {model.label} ({model.class_label})
              </option>
            ))}
          </select>
        </label>
        <button type="button" disabled={!modelId} onClick={() => onMap(modelId)}>
          Map
        </button>
      </div>
      <FeedbackLine feedback={feedback} />
    </div>
  );
}

function PreviewRowLine({
  row,
  labels,
  structure,
  canRead,
  itemFeedback,
  onRecord,
}: {
  row: PreviewRow;
  labels: Record<string, string>;
  structure: Structure | null;
  canRead: boolean;
  itemFeedback: Record<string, Feedback>;
  onRecord: (key: string, form: ValueRuleForm) => Promise<boolean>;
}) {
  const [reading, setReading] = useState<ValueRuleForm | null>(null);
  const readable = canRead ? readableValues(row) : [];
  const readings = rowReadingLines(row, structure);
  const key = (columnCode: string) => `read:${row.row_number}:${columnCode}`;
  return (
    <>
      <tr>
        <td>{row.row_number}</td>
        <td>
          {row.asset_public_id ? (
            <a href={`/equipment/machines/${row.asset_public_id}`}>
              {row.machine_number}
            </a>
          ) : (
            row.machine_number ?? "(none)"
          )}
        </td>
        <td>
          {outcomeLabel(row.outcome_code)}
          {row.reason_code ? <div className="helper-text">{reasonLabel(row.reason_code)}</div> : null}
          {row.changed_facts.length ? <div className="helper-text">Changes: {row.changed_facts.join(", ").replace(/_code/g, "").replace(/_/g, " ")}</div> : null}
        </td>
        <td>
          {row.class_label ?? "-"}
          {row.kind_code === "PART" ? " (part)" : ""}
          {row.type_label ? `, ${row.type_label.toLowerCase()}` : ""}
          {row.model_label ? ` - ${row.model_label}` : ""}
          <div className="helper-text">Plum: {[row.plum.category, row.plum.model_name, row.plum.capacity].filter(Boolean).join("; ") || "-"}</div>
        </td>
        <td>
          {row.flags.length ? (
            <ul className="compact-list">
              {row.flags.map((flag) => (
                <li key={`${flag.flag_code}-${flag.subject_code}`}>{flagLabel(flag, labels)}</li>
              ))}
            </ul>
          ) : readings.length ? null : (
            "-"
          )}
          {readings.length ? (
            <ul className="helper-text compact-list">
              {readings.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          ) : null}
          {readable.map((item) => (
            <div key={item.columnCode}>
              <button type="button" onClick={() => setReading(valueRuleFormFor(item.columnCode, item.plumValue))}>
                Read "{item.plumValue}" as...
              </button>
              <FeedbackLine feedback={itemFeedback[key(item.columnCode)]} />
            </div>
          ))}
        </td>
      </tr>
      {reading ? (
        <tr className="row-editor">
          <td colSpan={5}>
            <ValueRuleEditor
              form={reading}
              structure={structure}
              onChange={setReading}
              onCancel={() => setReading(null)}
              onSave={async () => {
                if (await onRecord(key(reading.columnCode), reading)) setReading(null);
              }}
            />
          </td>
        </tr>
      ) : null}
    </>
  );
}

function ValueRuleEditor({
  form,
  structure,
  onChange,
  onCancel,
  onSave,
}: {
  form: ValueRuleForm;
  structure: Structure | null;
  onChange: (form: ValueRuleForm) => void;
  onCancel: () => void;
  onSave: () => Promise<void>;
}) {
  const [saving, setSaving] = useState(false);
  const problem = valueRuleProblem(form);
  const actions = form.columnCode === "CAPACITY" ? Object.keys(VALUE_RULE_ACTION_LABELS) : ["NOT_A_VALUE"];
  const typeClass = findClass(structure, form.resultClassCode);
  return (
    <div>
      <p>
        {FIELD_LABELS[form.columnCode] ?? form.columnCode}: how is "{form.plumValue}" to be read, wherever it appears?
      </p>
      <div className="form-grid">
        <label className="field-stack">
          It is
          <select value={form.actionCode} onChange={(event) => onChange({ ...form, actionCode: event.target.value })}>
            {actions.map((code) => (
              <option key={code} value={code}>
                {VALUE_RULE_ACTION_LABELS[code]}
              </option>
            ))}
          </select>
        </label>
        {form.actionCode === "SPLIT_NUMBER_AND_UNIT" ? (
          <>
            <label className="field-stack">
              Number
              <input value={form.resultNumber} onChange={(event) => onChange({ ...form, resultNumber: event.target.value })} />
            </label>
            <label className="field-stack">
              Unit
              <select value={form.resultUnitCode} onChange={(event) => onChange({ ...form, resultUnitCode: event.target.value })}>
                <option value="">Choose a unit</option>
                {(structure?.units ?? []).map((unit) => (
                  <option key={unit.unit_code} value={unit.unit_code}>
                    {unit.unit_label}
                  </option>
                ))}
              </select>
            </label>
          </>
        ) : null}
        {form.actionCode === "REASSIGN_TO_TYPE" ? (
          <>
            <label className="field-stack">
              Kind
              <select value={form.resultClassCode} onChange={(event) => onChange({ ...form, resultClassCode: event.target.value, resultTypeCode: "" })}>
                <option value="">Choose the kind</option>
                {machineClasses(structure)
                  .filter((item) => item.types.length)
                  .map((item) => (
                    <option key={item.class_code} value={item.class_code}>
                      {item.class_label}
                    </option>
                  ))}
              </select>
            </label>
            <label className="field-stack">
              Type
              <select value={form.resultTypeCode} onChange={(event) => onChange({ ...form, resultTypeCode: event.target.value })}>
                <option value="">Choose the type</option>
                {(typeClass?.types ?? [])
                  .filter((item) => item.is_active)
                  .map((item) => (
                    <option key={item.type_code} value={item.type_code}>
                      {item.type_label}
                    </option>
                  ))}
              </select>
            </label>
          </>
        ) : null}
        <label className="field-stack">
          Reason
          <input value={form.reason} onChange={(event) => onChange({ ...form, reason: event.target.value })} maxLength={1000} />
        </label>
      </div>
      <button
        type="button"
        disabled={saving || Boolean(problem)}
        onClick={async () => {
          setSaving(true);
          try {
            await onSave();
          } finally {
            setSaving(false);
          }
        }}
      >
        Record reading
      </button>{" "}
      <button type="button" onClick={onCancel}>
        Cancel
      </button>
      {problem ? <p className="helper-text">{problem}</p> : null}
    </div>
  );
}
