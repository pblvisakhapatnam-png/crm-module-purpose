import { useEffect, useRef, useState } from "react";

import { PageHeader, SectionCard } from "../../components/PageLayout";
import { SESSION_CHANGED_EVENT, clearSession, getToken, hrefWithReturnTarget, readErrorDetail, readRoleCodes } from "../resource-requirements/pageSession";
import { createLatestOnly } from "../resource-requirements/resourceRequirementState";
import { EquipmentNav, FeedbackLine } from "./EquipmentParts";
import {
  EMPTY_MODEL_FORM,
  MODEL_CHANGED_ELSEWHERE_TEXT,
  type EquipmentModel,
  type Feedback,
  type ModelForm,
  type Structure,
  canManageEquipment,
  capabilityText,
  classKindNote,
  craneModelChoices,
  editingAfterLoad,
  findClass,
  isKitClass,
  kindChoices,
  kindLockedReason,
  kindProblem,
  modelFormFrom,
  modelFormProblem,
  modelPayload,
  modelSavedText,
  newRequestKey,
} from "./equipmentState";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

// Models - makers' models with their rated capabilities - and the Plum model names mapped to them (ERT-1,
// Q4). A machine's capabilities are read from its model, so correcting a rating here corrects every
// machine of it. Admin records and changes models; everyone may read them.
//
// A kit model (ERT-2) names the crane models it fits; its pieces are held for every crane of them. No Plum
// name is mapped to one: kit is recorded on the platform.

export default function ModelsPage() {
  const [structure, setStructure] = useState<Structure | null>(null);
  const [models, setModels] = useState<EquipmentModel[]>([]);
  const [loadError, setLoadError] = useState("");
  const [canManage, setCanManage] = useState(false);
  // The model being changed, or "new" while a new one is recorded; null when no form is open.
  const [editing, setEditing] = useState<EquipmentModel | "new" | null>(null);
  const [feedback, setFeedback] = useState<Record<string, Feedback>>({});
  const loads = useRef(createLatestOnly());
  // The form open when a load answers, read without waiting for a render.
  const editingNow = useRef(editing);
  editingNow.current = editing;
  // A form opened from a row far down the list is brought into view (owner's screen check, ERT-2).
  const editorCard = useRef<HTMLDivElement>(null);
  const openForm = editing === null ? null : editing === "new" ? "new" : editing.model_public_id;
  useEffect(() => {
    if (openForm) editorCard.current?.scrollIntoView({ block: "start" });
  }, [openForm]);

  async function load() {
    const ticket = loads.current.begin();
    const token = getToken();
    if (!token) {
      setLoadError(SIGN_IN_FIRST);
      return;
    }
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [modelsResponse, structureResponse] = await Promise.all([
        fetch("/api/equipment-reference/models", { headers }),
        fetch("/api/equipment-reference/structure", { headers }),
      ]);
      if (modelsResponse.status === 401) clearSession();
      if (!loads.current.isLatest(ticket)) return;
      if (!modelsResponse.ok) {
        setLoadError(await readErrorDetail(modelsResponse, "The models could not be loaded."));
        return;
      }
      setLoadError("");
      const list = (await modelsResponse.json()) as EquipmentModel[];
      setModels(list);
      // A model changed elsewhere since its form was opened: the form closes rather than send a stale draft.
      const after = editingAfterLoad(editingNow.current, list);
      if (after.closedAsStale) {
        setEditing(null);
        setFeedback({ editor: { kind: "error", text: MODEL_CHANGED_ELSEWHERE_TEXT } });
      } else if (after.editing !== editingNow.current) {
        // The same version, loaded again: the open form keeps its draft and checks it against the model as it is now.
        setEditing(after.editing);
      }
      if (structureResponse.ok) setStructure((await structureResponse.json()) as Structure);
    } catch {
      if (loads.current.isLatest(ticket)) setLoadError("Network error while loading the models.");
    }
  }

  useEffect(() => {
    setCanManage(canManageEquipment(readRoleCodes()));
    void load();
    const refresh = () => void load();
    window.addEventListener(SESSION_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, refresh);
  }, []);

  async function removeMapping(name: string) {
    const token = getToken();
    if (!token) return;
    try {
      const response = await fetch("/api/equipment-reference/model-mappings", {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ source_name: name, model_public_id: null }),
      });
      setFeedback({ [`map:${name}`]: response.ok ? { kind: "success", text: "Mapping removed." } : { kind: "error", text: await readErrorDetail(response, "The mapping was not removed.") } });
      if (response.ok) void load();
    } catch {
      setFeedback({ [`map:${name}`]: { kind: "error", text: "Network error: the mapping may not have been removed." } });
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="Equipment"
        title="Models"
        subtitle="Each maker's model, with its rated capabilities in the platform's units, and the Plum model names mapped to it. Machines read their capabilities from their model unless a machine has its own value."
      >
        {loadError ? <p className="text-danger">{loadError}</p> : null}
      </PageHeader>
      <EquipmentNav current="/equipment/models" />

      {canManage ? (
        <div ref={editorCard}>
          <SectionCard title={editing && editing !== "new" ? `Change ${editing.label}` : "Record a model"}>
            {editing ? (
              <ModelEditor
                key={editing === "new" ? "new" : `${editing.model_public_id}-${editing.model_version}`}
                model={editing === "new" ? null : editing}
                structure={structure}
                models={models}
                onSaved={(text) => {
                  setEditing(null);
                  setFeedback({ editor: { kind: "success", text } });
                  void load();
                }}
                onCancel={() => setEditing(null)}
              />
            ) : (
              <button type="button" onClick={() => { setEditing("new"); setFeedback({}); }}>
                Record a model
              </button>
            )}
            <FeedbackLine feedback={feedback.editor} />
          </SectionCard>
        </div>
      ) : null}

      {canManage ? <MapNameCard models={models} onMapped={() => void load()} /> : null}

      {models.length ? (
        <div className="data-table-wrap">
          <table className="data-table data-table-wide">
            <thead>
              <tr>
                <th>Model</th>
                <th>Kind and type</th>
                <th>Rated capabilities</th>
                <th>Plum names mapped</th>
                <th>Records</th>
                <th>Kit</th>
                {canManage ? <th /> : null}
              </tr>
            </thead>
            <tbody>
              {models.map((model) => (
                <tr key={model.model_public_id}>
                  <td>
                    <strong>{model.label}</strong>
                    {model.maker_part_number ? <div className="helper-text">Maker's part number {model.maker_part_number}</div> : null}
                    {model.is_retired ? <div className="helper-text">Retired</div> : null}
                  </td>
                  <td>
                    {model.class_label}
                    {model.is_kit ? " (kit)" : ""}
                    {model.type_label ? `, ${model.type_label.toLowerCase()}` : ""}
                  </td>
                  <td>{model.capabilities.map((capability) => capabilityText(capability)).join("; ") || "-"}</td>
                  <td>
                    {model.mapped_names.map((name) => (
                      <div key={name}>
                        {name}{" "}
                        {canManage ? (
                          <button type="button" onClick={() => void removeMapping(name)}>
                            Remove
                          </button>
                        ) : null}
                        <FeedbackLine feedback={feedback[`map:${name}`]} />
                      </div>
                    ))}
                    {model.mapped_names.length ? null : "-"}
                  </td>
                  <td>{model.machine_count}</td>
                  <td>
                    {model.is_kit ? (
                      <>
                        <div>Fits {model.fits_models.map((fit) => fit.label).join(", ")}</div>
                        <div>
                          <a href={hrefWithReturnTarget(`/equipment?kit_model=${model.model_public_id}`, "/equipment/models", "Back to models")}>{model.pieces_held} held</a>
                        </div>
                        {model.fits_no_active_crane ? <div className="text-warning">No active crane of these models is left: retire the kit sold or scrapped with them.</div> : null}
                      </>
                    ) : model.class_kind_code === "MACHINE" ? (
                      `${model.active_unit_count} active`
                    ) : (
                      "-"
                    )}
                  </td>
                  {canManage ? (
                    <td>
                      <button type="button" onClick={() => { setEditing(model); setFeedback({}); }}>
                        Change
                      </button>
                    </td>
                  ) : null}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : !loadError ? (
        <div className="empty-state">No models recorded yet. Admin records them, then maps Plum's model names to them.</div>
      ) : null}
    </section>
  );
}

function ModelEditor({
  model,
  structure,
  models,
  onSaved,
  onCancel,
}: {
  model: EquipmentModel | null;
  structure: Structure | null;
  models: EquipmentModel[];
  onSaved: (text: string) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<ModelForm>(model ? modelFormFrom(model) : EMPTY_MODEL_FORM);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [saving, setSaving] = useState(false);
  // One key per form, so a double click or a retry records one model; the key with a changed form is refused (409).
  const [requestKey] = useState(newRequestKey);
  const equipmentClass = findClass(structure, form.classCode);
  const problem = modelFormProblem(form, structure) ?? kindProblem(form, model, models, structure);
  const craneChoices = craneModelChoices(models, equipmentClass, model?.fits_models.map((fit) => fit.model_public_id) ?? []);
  // The server refuses a new kind while records use the model or kit fits it: the box is not offered then.
  const kindLocked = kindLockedReason(model, models);
  const edit = (next: Partial<ModelForm>) => {
    setForm({ ...form, ...next });
    setFeedback(null);
  };
  const toggleFit = (modelPublicId: string, chosen: boolean) =>
    edit({ fitsModelIds: chosen ? [...form.fitsModelIds, modelPublicId] : form.fitsModelIds.filter((item) => item !== modelPublicId) });

  async function save() {
    const token = getToken();
    if (!token || problem) return;
    setSaving(true);
    try {
      const body = model
        ? { ...modelPayload(form, structure), is_retired: form.isRetired, expected_model_version: model.model_version }
        : { ...modelPayload(form, structure), create_request_key: requestKey };
      const response = await fetch(model ? `/api/equipment-reference/models/${model.model_public_id}` : "/api/equipment-reference/models", {
        method: model ? "PUT" : "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        setFeedback({ kind: "error", text: await readErrorDetail(response, "The model was not saved.") });
        return;
      }
      onSaved(modelSavedText((await response.json()) as { event: unknown; replayed: boolean }));
    } catch {
      setFeedback({ kind: "error", text: "Network error: the model may not have been saved. Reload to see." });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="form-grid">
        <label className="field-stack">
          Maker
          <input value={form.maker} onChange={(event) => edit({ maker: event.target.value })} maxLength={100} />
        </label>
        <label className="field-stack">
          Model name
          <input value={form.modelName} onChange={(event) => edit({ modelName: event.target.value })} maxLength={100} />
        </label>
        <label className="field-stack">
          Kind
          <select
            value={form.classCode}
            disabled={Boolean(kindLocked)}
            onChange={(event) => edit({ classCode: event.target.value, typeCode: "", values: {}, fitsModelIds: [] })}
          >
            <option value="">Choose the kind</option>
            {kindChoices(structure, model).map((item) => (
              <option key={item.class_code} value={item.class_code}>
                {item.class_label}
                {classKindNote(item)}
              </option>
            ))}
          </select>
          {kindLocked ? <span className="helper-text">{kindLocked}</span> : null}
          {!kindLocked && model?.mapped_names.length && !model.is_kit ? (
            <span className="helper-text">Plum model names are mapped to it, so the kinds of kit are not offered.</span>
          ) : null}
        </label>
        <label className="field-stack">
          Maker's part number (optional)
          <input value={form.makerPartNumber} onChange={(event) => edit({ makerPartNumber: event.target.value })} maxLength={100} />
        </label>
        {equipmentClass && equipmentClass.types.length ? (
          <label className="field-stack">
            Type
            <select value={form.typeCode} onChange={(event) => edit({ typeCode: event.target.value })}>
              <option value="">Not stated</option>
              {equipmentClass.types
                .filter((item) => item.is_active || item.type_code === form.typeCode)
                .map((item) => (
                  <option key={item.type_code} value={item.type_code}>
                    {item.type_label}
                  </option>
                ))}
            </select>
          </label>
        ) : null}
        {(equipmentClass?.capabilities ?? []).map((capability) => (
          <label key={capability.capability_code} className="field-stack">
            {capability.capability_label}
            {capability.unit_symbol ? ` (${capability.unit_symbol})` : ""}
            {capability.value_kind_code === "CHOICE" ? (
              <select value={form.values[capability.capability_code] ?? ""} onChange={(event) => edit({ values: { ...form.values, [capability.capability_code]: event.target.value } })}>
                <option value="">Not stated</option>
                {(capability.allowed_values ?? []).map((value) => (
                  <option key={value} value={value}>
                    {value}
                  </option>
                ))}
              </select>
            ) : (
              <input value={form.values[capability.capability_code] ?? ""} onChange={(event) => edit({ values: { ...form.values, [capability.capability_code]: event.target.value } })} />
            )}
          </label>
        ))}
        {model ? (
          <label>
            <input type="checkbox" checked={form.isRetired} onChange={(event) => edit({ isRetired: event.target.checked })} /> Retired (no new mappings)
          </label>
        ) : null}
      </div>
      {isKitClass(equipmentClass) ? (
        <fieldset className="choice-list section-form">
          <legend>Crane models this kit fits - its pieces are held for every crane of them</legend>
          {craneChoices.length === 0 ? <p className="helper-text">No crane model is recorded yet.</p> : null}
          {craneChoices.map((choice) => (
            <label key={choice.model_public_id}>
              <input type="checkbox" checked={form.fitsModelIds.includes(choice.model_public_id)} onChange={(event) => toggleFit(choice.model_public_id, event.target.checked)} />{" "}
              {choice.label}
              {choice.is_retired ? " (retired)" : ""}
            </label>
          ))}
        </fieldset>
      ) : null}
      <div className="section-form">
        <button type="button" disabled={saving || Boolean(problem)} onClick={() => void save()}>
          {saving ? "Saving..." : "Save model"}
        </button>{" "}
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
        {problem && (form.maker || form.modelName || form.classCode) ? <p className="helper-text">{problem}</p> : null}
        <FeedbackLine feedback={feedback} />
      </div>
    </div>
  );
}

function MapNameCard({ models, onMapped }: { models: EquipmentModel[]; onMapped: () => void }) {
  const [name, setName] = useState("");
  const [modelId, setModelId] = useState("");
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [saving, setSaving] = useState(false);

  async function map() {
    const token = getToken();
    if (!token) return;
    setSaving(true);
    try {
      const response = await fetch("/api/equipment-reference/model-mappings", {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ source_name: name.trim(), model_public_id: modelId }),
      });
      if (!response.ok) {
        setFeedback({ kind: "error", text: await readErrorDetail(response, "The name was not mapped.") });
        return;
      }
      setFeedback({ kind: "success", text: "Name mapped. The next preview of a report uses it." });
      setName("");
      setModelId("");
      onMapped();
    } catch {
      setFeedback({ kind: "error", text: "Network error: the name may not have been mapped." });
    } finally {
      setSaving(false);
    }
  }

  return (
    <SectionCard title="Map a Plum model name">
      <div className="form-grid">
        <label className="field-stack">
          Model name as Plum records it
          <input value={name} onChange={(event) => { setName(event.target.value); setFeedback(null); }} maxLength={200} />
        </label>
        <label className="field-stack">
          Model
          <select value={modelId} onChange={(event) => { setModelId(event.target.value); setFeedback(null); }}>
            <option value="">Choose a model</option>
            {models
              // Kit is recorded on the platform: no Plum name is mapped to a kit model.
              .filter((model) => !model.is_retired && !model.is_kit)
              .map((model) => (
                <option key={model.model_public_id} value={model.model_public_id}>
                  {model.label} ({model.class_label})
                </option>
              ))}
          </select>
        </label>
      </div>
      <button type="button" disabled={saving || !name.trim() || !modelId} onClick={() => void map()}>
        Map name
      </button>
      <FeedbackLine feedback={feedback} />
    </SectionCard>
  );
}
