import { useEffect, useReducer, useState } from "react";
import { useParams } from "react-router-dom";

import { PageHeader, SectionCard, StatusBadge } from "../../components/PageLayout";
import {
  clearSession,
  formatDateTime,
  getToken,
  hrefWithReturnTarget,
  readErrorDetail,
  readRoleCodes,
  readSafeReturnTarget,
} from "../resource-requirements/pageSession";
import { EquipmentNav, FeedbackLine, Row } from "./EquipmentParts";
import MachineCertificates from "./MachineCertificates";
import AllocationsSection from "../allocations/AllocationsSection";
import {
  CORRECTION_FIELDS,
  EMPTY_KIT_FORM,
  FIELD_LABELS,
  INITIAL_MACHINE_STATE,
  RETIREMENT_REASON_LABELS,
  type EquipmentModel,
  type KitForm,
  type Machine,
  type MachineCorrection,
  type MachineEvent,
  type MachineSummary,
  type RetireForm,
  type Structure,
  WITHHELD_TEXT,
  assetName,
  canManageEquipment,
  correctionValuesText,
  capabilityLabels,
  capabilityPayload,
  capabilityText,
  capabilityValueProblem,
  correctionProblem,
  createMachineLoader,
  detailFields,
  detailsPayload,
  findClass,
  flagLabel,
  kitFormProblem,
  kitModelsFor,
  kitPayload,
  machineClasses,
  machineKindText,
  machineReducer,
  newRequestKey,
  piecesHeldText,
  plainNumber,
  reasonText,
  retireFormProblem,
  retiredText,
  retirePayload,
  retirementText,
  statusLabel,
  takesKit,
} from "./equipmentState";
import DateInput from "../../components/DateInput";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

// One machine or fitted part (ERT-1): Plum's facts as of the report they came from, each corrected one
// marked; the facts the platform holds; its capabilities; its fitted parts; its flags, corrections and
// events. Admin may enter details, set its own values, correct a Plum value, and fit or remove a part.
// What each answer does to the page is machineReducer's and createMachineLoader's, tested on their own.
//
// Every asset also shows its certificates and a check for a site (ELG-1, MachineCertificates).
//
// A machine also shows the detachable kit held for its model (ERT-2): shared by every machine of the models
// each kit model fits, not this machine's alone. Admin adds pieces there. A piece of kit has its own page -
// this one, without Plum's facts - where Admin enters its details and retires it.

// Today where PBL works, as the server judges a date "in the future".
const TODAY = () => new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Kolkata" }).format(new Date());

export default function MachinePage() {
  const params = useParams();
  const assetId = params?.assetId;
  const [state, dispatch] = useReducer(machineReducer, INITIAL_MACHINE_STATE);
  // Opened from an allocation or the finder, the page leads back there; otherwise to the machines list.
  const [returnTarget] = useState(() => readSafeReturnTarget("/equipment", "Back to machines"));
  const [structure, setStructure] = useState<Structure | null>(null);
  const [models, setModels] = useState<EquipmentModel[]>([]);
  const [events, setEvents] = useState<MachineEvent[]>([]);
  const [eventsWithheld, setEventsWithheld] = useState(false);
  const [canManage, setCanManage] = useState(false);
  // Each successful "Add kit" opens a fresh form, with a fresh request key.
  const [kitRound, setKitRound] = useState(0);
  const { machine } = state;
  const busy = state.pendingSave !== null;
  const loadError = state.loadError;

  // The machine and its events load together; only what the latest load asked for is shown.
  const [loader] = useState(() =>
    createMachineLoader({
      getToken,
      fetchMachine: async (token, publicId) => {
        const response = await fetch(`/api/equipment-reference/machines/${encodeURIComponent(publicId)}`, { headers: { Authorization: `Bearer ${token}` } });
        if (response.status === 401) clearSession();
        if (!response.ok) throw new Error(await readErrorDetail(response, "The machine could not be loaded."));
        return (await response.json()) as Machine;
      },
      fetchEvents: async (token, publicId) => {
        const response = await fetch(`/api/events/recent?record_type=equipment_asset&record_public_id=${encodeURIComponent(publicId)}&limit=25`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        // Business events are Admin's and Management's (EVENTS_READ): another role is told so, not shown "none".
        setEventsWithheld(response.status === 403);
        return response.ok ? ((await response.json()) as MachineEvent[]) : [];
      },
      dispatch,
      showEvents: setEvents,
      // Labels and choices only: a failure leaves the page showing the machine with what it had.
      fetchReferences: async (token) => {
        const headers = { Authorization: `Bearer ${token}` };
        const [structureResponse, modelsResponse] = await Promise.all([
          fetch("/api/equipment-reference/structure", { headers }),
          fetch("/api/equipment-reference/models", { headers }),
        ]);
        if (!structureResponse.ok || !modelsResponse.ok) throw new Error("The structure or the models could not be loaded.");
        return { structure: (await structureResponse.json()) as Structure, models: (await modelsResponse.json()) as EquipmentModel[] };
      },
      showReferences: (references) => {
        setStructure(references.structure);
        setModels(references.models);
      },
    }),
  );
  const load = (publicId: string) => loader.load(publicId);

  useEffect(() => {
    setCanManage(canManageEquipment(readRoleCodes()));
    if (typeof assetId === "string") void load(assetId);
  }, [assetId]);

  /** Send one of Admin's changes; a success installs the machine it returns, a refusal is shown beside the form. */
  async function send(key: string, path: string, body: Record<string, unknown>, success: string | ((after: Machine) => string), method = "POST") {
    if (!machine) return;
    // Every answer names the machine and the save it belongs to: moving to another machine leaves it behind.
    const publicId = machine.asset_public_id;
    const ticket = loader.beginSave(publicId);
    const token = getToken();
    if (!token) {
      loader.refused(ticket, publicId, key, SIGN_IN_FIRST);
      return;
    }
    try {
      const response = await fetch(`/api/equipment-reference/machines/${publicId}${path}`, {
        method,
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ expected_asset_version: machine.asset_version, ...body }),
      });
      if (response.status === 401) clearSession();
      if (!response.ok) {
        const text = await readErrorDetail(response, "The change was not saved.");
        loader.refused(ticket, publicId, key, response.status === 409 ? `${text} Your change was not saved.` : text);
        return;
      }
      const result = (await response.json()) as { machine: Machine; event: unknown };
      const text = typeof success === "function" ? success(result.machine) : success;
      void loader.saved(ticket, result.machine, key, result.event ? text : "Nothing changed, so nothing was saved.");
    } catch {
      loader.refused(ticket, publicId, key, "Network error: the change may not have been saved. Reload to see.");
    }
  }

  /** Add pieces of a kit model (ERT-2). They are held for the model, so the machine is read again to show
   *  them; its version does not move, so the page keeps what it shows and gains the kit. */
  async function addKit(body: Record<string, unknown>, modelLabel: string) {
    if (!machine) return;
    const publicId = machine.asset_public_id;
    const ticket = loader.beginSave(publicId);
    const token = getToken();
    if (!token) {
      loader.refused(ticket, publicId, "kit", SIGN_IN_FIRST);
      return;
    }
    const headers = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };
    try {
      const response = await fetch("/api/equipment-reference/kit", { method: "POST", headers, body: JSON.stringify(body) });
      if (response.status === 401) clearSession();
      if (!response.ok) {
        loader.refused(ticket, publicId, "kit", await readErrorDetail(response, "The kit was not added."));
        return;
      }
      const result = (await response.json()) as { pieces: MachineSummary[]; replayed: boolean };
      // Read again in the page's one order of views: a reload asked for after this one is not replaced by it.
      const view = loader.beginView();
      const fresh = await fetch(`/api/equipment-reference/machines/${publicId}`, { headers });
      if (!fresh.ok) {
        loader.refused(ticket, publicId, "kit", "The kit was added. Reload to see it.");
        return;
      }
      const text = result.replayed
        ? "Already added: nothing more was recorded."
        : `Added to the kit for this model: ${result.pieces.length === 1 ? `1 record of ${modelLabel}` : `${result.pieces.length} records of ${modelLabel}`}.`;
      setKitRound((round) => round + 1);
      void loader.saved(ticket, (await fresh.json()) as Machine, "kit", text, view);
    } catch {
      loader.refused(ticket, publicId, "kit", "Network error: the kit may not have been added. Reload to see.");
    }
  }

  if (!machine) {
    return (
      <section>
        <PageHeader eyebrow="Equipment" title="Machine" back={returnTarget}>
          {loadError ? <p className="text-danger">{loadError}</p> : <p className="helper-text">Loading the machine...</p>}
        </PageHeader>
      </section>
    );
  }

  const labels = capabilityLabels(structure);
  const openCorrections = machine.corrections.filter((item) => item.correction_status_code === "OPEN");
  const correctionFor = (field: string) => openCorrections.find((item) => item.field_code === field);
  const plumChanged = new Set(machine.flags.filter((flag) => flag.flag_code === "PLUM_CHANGED_CORRECTED_VALUE").map((flag) => flag.subject_code));
  const isMachine = machine.asset_kind_code === "MACHINE";
  // A piece of kit, recorded on the platform: no Plum facts, no corrections, never fitted (ERT-2).
  const isKit = machine.origin_code === "PLATFORM";
  const tracking = findClass(structure, machine.class_code)?.tracking_code;
  const retired = retirementText(machine);
  // The kind of machine the kit is shared among, in the structure's own word: today, "crane".
  const machineKind = machine.class_label.toLowerCase();
  // The kit list's links lead to the machines list, which offers the way back here (owner's screen check).
  const backHref = `/equipment/machines/${machine.asset_public_id}`;
  const backLabel = `Back to ${machine.machine_number ?? machine.asset_reference}`;
  const hasCapabilities = (findClass(structure, machine.class_code)?.capabilities.length ?? 0) > 0;

  return (
    <section>
      <PageHeader
        eyebrow={isMachine ? "Equipment - machine" : isKit ? "Equipment - kit" : "Equipment - fitted part"}
        title={`${machine.asset_reference} - ${assetName(machine, machine.serial_number)}`}
        badges={<StatusBadge code={machine.asset_status_code} label={statusLabel(machine.asset_status_code)} />}
        subtitle={
          isKit
            ? `${machineKindText(machine)}. Kit recorded on the platform, held for every crane of the models it fits.`
            : `${machineKindText(machine)}. Plum's facts are as of the report of ${machine.facts_report_date ?? "-"}.`
        }
        back={returnTarget}
        actions={
          <button type="button" onClick={() => typeof assetId === "string" && void load(assetId)}>
            Reload
          </button>
        }
      >
        {loadError ? <p className="text-danger">{loadError}</p> : null}
        {retired ? <p className="helper-text">{retired}</p> : null}
      </PageHeader>
      <EquipmentNav current="" />

      {isKit ? null : (
      <SectionCard title="Plum's facts">
        <dl className="facts-list">
          <Row label="Machine number">{machine.machine_number}</Row>
          <FactRow label="Engine number" value={machine.identity_numbers_withheld ? WITHHELD_TEXT : machine.engine_number} correction={correctionFor("ENGINE_NUMBER")} />
          <FactRow label="Chassis number" value={machine.identity_numbers_withheld ? WITHHELD_TEXT : machine.chassis_number} correction={correctionFor("CHASSIS_NUMBER")} />
          <FactRow label="Commenced year" value={machine.commenced_year?.toString() ?? null} correction={correctionFor("COMMENCED_YEAR")} />
          <FactRow label="Owning company" value={machine.owning_company} correction={correctionFor("OWNING_COMPANY")} />
          <FactRow label="Status" value={statusLabel(machine.asset_status_code)} correction={correctionFor("STATUS")} />
          <Row label="As Plum records it">
            {machine.plum ? `${machine.plum.category ?? "no category"}; model name ${machine.plum.model_name ?? "none"}; capacity ${machine.plum.capacity ?? "none"}` : "-"}
          </Row>
        </dl>
      </SectionCard>
      )}

      <SectionCard title={isKit ? "Its details" : "Details Plum does not hold"}>
        <dl className="facts-list">
          {isKit && tracking === "COUNTED" ? (
            <Row label="Pieces in the set">{machine.quantity}</Row>
          ) : (
            <Row label={isKit ? "Its own number" : "Serial number"}>{machine.serial_number ?? "Not entered yet"}</Row>
          )}
          <Row label="Year of manufacture">{machine.year_of_manufacture ?? "Not entered yet"}</Row>
        </dl>
        {canManage ? (
          state.openForm === "details" ? (
            <DetailsForm
              machine={machine}
              kitTracking={isKit ? tracking ?? "SINGLE" : null}
              modelChoices={isKit ? models.filter((model) => model.class_code === machine.class_code && (!model.is_retired || model.model_public_id === machine.model_public_id)) : []}
              busy={busy}
              onSave={(body) => void send("details", "/details", body, "Details saved.", "PUT")}
              onCancel={() => dispatch({ type: "form-opened", form: null })}
            />
          ) : (
            <button type="button" onClick={() => dispatch({ type: "form-opened", form: "details" })}>
              Enter details
            </button>
          )
        ) : null}
        <FeedbackLine feedback={state.feedback.details} />
      </SectionCard>

      <SectionCard title="Kind, model and capabilities">
        <dl className="facts-list">
          <FactRow label="Kind" value={machine.class_label} correction={correctionFor("CATEGORY")} />
          <Row label="Type">{machine.type_label ?? "-"}</Row>
          <FactRow label="Model" value={machine.model_label ?? "Not mapped yet"} correction={correctionFor("MODEL")} />
        </dl>
        {isMachine || isKit ? (
          <table className="data-table section-form">
            <thead>
              <tr>
                <th>Capability</th>
                <th>Value</th>
                <th>From</th>
              </tr>
            </thead>
            <tbody>
              {machine.capabilities.map((capability) => (
                <tr key={capability.capability_code}>
                  <td>{capability.capability_label}</td>
                  <td>{capability.source_code === "NONE" ? "-" : capabilityText(capability).replace(`${capability.capability_label} `, "")}</td>
                  <td>
                    {capability.source_code === "OWN" ? `Its own value: ${capability.reason ?? ""}` : capability.source_code === "MODEL" ? "Its model" : "-"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : null}
        {canManage && (isMachine || (isKit && hasCapabilities)) ? (
          state.openForm === "capabilities" ? (
            <OwnValuesForm
              machine={machine}
              structure={structure}
              busy={busy}
              onSave={(capabilities) => void send("capabilities", "/capabilities", { capabilities }, "Own values saved.", "PUT")}
              onCancel={() => dispatch({ type: "form-opened", form: null })}
            />
          ) : (
            <button type="button" onClick={() => dispatch({ type: "form-opened", form: "capabilities" })}>
              {isKit ? "Set this piece's own values" : "Set this machine's own values"}
            </button>
          )
        ) : null}
        <FeedbackLine feedback={state.feedback.capabilities} />
      </SectionCard>

      {isMachine ? (
        <SectionCard title="Fitted parts">
          {machine.fitted_parts.length === 0 ? <p className="helper-text">No part fitted.</p> : null}
          {machine.fitted_parts.map((link) => (
            <RemovablePart key={link.link_public_id} link={link} canManage={canManage} busy={busy} onRemove={(removedOn) => void send("parts", `/fitted-parts/${link.part.asset_public_id}/remove`, { removed_on: removedOn, expected_part_version: link.part.asset_version }, "Part removed.")} />
          ))}
          {machine.link_history.length ? (
            <p className="helper-text">
              Earlier: {machine.link_history.map((link) => `${link.part.machine_number} (${link.fitted_on} to ${link.removed_on})`).join("; ")}
            </p>
          ) : null}
          {canManage ? (
            state.openForm === "fit" ? (
              <FitPartForm machine={machine} structure={structure} busy={busy} onSave={(body) => void send("parts", "/fitted-parts", body, "Part fitted.")} onCancel={() => dispatch({ type: "form-opened", form: null })} />
            ) : (
              <button type="button" onClick={() => dispatch({ type: "form-opened", form: "fit" })}>
                Pair a part
              </button>
            )
          ) : null}
          <FeedbackLine feedback={state.feedback.parts} />
        </SectionCard>
      ) : isKit ? (
        <SectionCard title="Held for">
          <p>{machine.fits_models.map((fit) => fit.label).join(", ") || "-"}</p>
          <p className="helper-text">
            Kit is not fitted to one crane: it is held for every crane of these models, and goes to site with whichever the job needs.
          </p>
        </SectionCard>
      ) : (
        <SectionCard title="Fitted to">
          {machine.fitted_to ? (
            <a href={`/equipment/machines/${machine.fitted_to.machine.asset_public_id}`}>
              {machine.fitted_to.machine.asset_reference} - {machine.fitted_to.machine.machine_number}, since {machine.fitted_to.fitted_on}
            </a>
          ) : (
            <p className="helper-text">Not fitted to a machine. Pair it from its machine's page, or when a report is confirmed.</p>
          )}
        </SectionCard>
      )}

      {isMachine && takesKit(structure, machine.class_code) ? (
        <SectionCard title={machine.model_label ? `Kit for ${machine.model_label}` : "Kit"}>
          {!machine.model_public_id ? (
            <p className="helper-text">Map its model to see its kit.</p>
          ) : (
            <>
              <p className="helper-text">
                Held for every {machineKind} of this model, not for this one alone: shared by {machine.model_active_unit_count ?? 0} active{" "}
                {machineKind}
                {machine.model_active_unit_count === 1 ? "" : "s"} of it.
              </p>
              {machine.kit.length === 0 ? (
                <p className="helper-text">No kit model fits this model yet. Record one on the Models page.</p>
              ) : (
                <table className="data-table section-form">
                  <thead>
                    <tr>
                      <th>Kind</th>
                      <th>Kit model</th>
                      <th>Key rating</th>
                      <th>Held</th>
                      <th>Also fits</th>
                    </tr>
                  </thead>
                  <tbody>
                    {machine.kit.map((item) => (
                      <tr key={item.kit_model_public_id}>
                        <td>
                          {item.class_label}
                          {item.type_label ? `, ${item.type_label.toLowerCase()}` : ""}
                        </td>
                        <td>
                          <a href={hrefWithReturnTarget(`/equipment?kit_model=${item.kit_model_public_id}`, backHref, backLabel)}>{item.label}</a>
                        </td>
                        <td>{capabilityText(item.key_capability)}</td>
                        <td>{piecesHeldText(item)}</td>
                        <td>
                          {item.fits_models
                            .filter((fit) => fit.model_public_id !== machine.model_public_id)
                            .map((fit) => fit.label)
                            .join(", ") || "-"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              <p className="helper-text">
                <a href={hrefWithReturnTarget(`/equipment?fits_model=${machine.model_public_id}`, backHref, backLabel)}>See every piece held for this model</a>
              </p>
              {canManage ? (
                state.openForm === "kit" ? (
                  <KitAddForm
                    key={kitRound}
                    machine={machine}
                    choices={kitModelsFor(models, machine.model_public_id)}
                    structure={structure}
                    busy={busy}
                    onSave={(body, label) => void addKit(body, label)}
                    onCancel={() => dispatch({ type: "form-opened", form: null })}
                  />
                ) : (
                  <button type="button" onClick={() => dispatch({ type: "form-opened", form: "kit" })}>
                    Add kit
                  </button>
                )
              ) : null}
            </>
          )}
          <FeedbackLine feedback={state.feedback.kit} />
        </SectionCard>
      ) : null}

      {isKit && canManage ? (
        <SectionCard title="Retire">
          {machine.asset_status_code !== "ACTIVE" ? (
            // The section stays, so the message of a retirement just made is seen beside its button's place.
            <p className="helper-text">Nothing more to do: this piece is retired, and its history is kept above.</p>
          ) : state.openForm === "retire" ? (
            <RetireKitForm
              held={machine.quantity}
              busy={busy}
              onSave={(body) => void send("retire", "/retire", body, (after) => retiredText(machine, after))}
              onCancel={() => dispatch({ type: "form-opened", form: null })}
            />
          ) : (
            <button type="button" onClick={() => dispatch({ type: "form-opened", form: "retire" })}>
              {machine.quantity > 1 ? "Retire pieces" : "Retire this piece"}
            </button>
          )}
          <FeedbackLine feedback={state.feedback.retire} />
        </SectionCard>
      ) : null}

      {/* ELG-1: its certificates, and whether it may work at a site. */}
      <MachineCertificates assetPublicId={machine.asset_public_id} />

      {/* 8A core: where the machine is held, and where it was. */}
      {machine.asset_kind_code === "MACHINE" ? (
        <AllocationsSection
          title="Allocations"
          filter="machine_public_id"
          recordPublicId={machine.asset_public_id}
          hide={["machine"]}
          returnTo={{ href: `/equipment/machines/${machine.asset_public_id}`, label: "Back to the machine" }}
          empty="This machine has not been allocated to a Work Order."
        />
      ) : null}

      <SectionCard title="Flags">
        {machine.flags.length === 0 ? <p className="helper-text">No flags.</p> : null}
        <ul>
          {machine.flags.map((flag) => (
            <li key={`${flag.flag_code}-${flag.subject_code}`}>{flagLabel(flag, labels)}</li>
          ))}
        </ul>
      </SectionCard>

      {isKit ? null : (
      <SectionCard title="Corrections">
        {machine.corrections.length === 0 ? <p className="helper-text">No correction recorded.</p> : null}
        {machine.corrections.map((correction) => (
          <CorrectionLine
            key={correction.correction_public_id}
            correction={correction}
            plumChanged={plumChanged.has(correction.field_code)}
            canManage={canManage}
            busy={busy}
            onClose={() => void send("corrections", `/corrections/${correction.correction_public_id}/close`, {}, "Correction closed.")}
            onKeep={() =>
              void send(
                "corrections",
                "/corrections",
                { field_code: correction.field_code, corrected_value: correction.corrected_value, reason: correction.reason },
                "Correction kept against Plum's new value.",
              )
            }
          />
        ))}
        {canManage ? (
          state.openForm === "correction" ? (
            <CorrectionForm
              machine={machine}
              structure={structure}
              models={models}
              busy={busy}
              onSave={(body) => void send("corrections", "/corrections", body, "Correction recorded. It applies now and on every import until Plum agrees.")}
              onCancel={() => dispatch({ type: "form-opened", form: null })}
            />
          ) : (
            <button type="button" onClick={() => dispatch({ type: "form-opened", form: "correction" })}>
              Correct a Plum value
            </button>
          )
        ) : null}
        <FeedbackLine feedback={state.feedback.corrections} />
      </SectionCard>
      )}

      <SectionCard title="Events">
        {eventsWithheld ? (
          <p className="helper-text">Business events are shown to Admin and Management only.</p>
        ) : events.length === 0 ? (
          <p className="helper-text">No events to show.</p>
        ) : null}
        <ul>
          {events.map((event) => (
            <li key={event.public_id}>
              {formatDateTime(event.event_timestamp)} - {event.reason ?? event.event_name}
            </li>
          ))}
        </ul>
      </SectionCard>
    </section>
  );
}

function FactRow({ label, value, correction }: { label: string; value: string | null; correction: MachineCorrection | undefined }) {
  return (
    <Row label={label}>
      {value ?? "-"}
      {correction ? (
        <div className="helper-text">
          {correction.values_withheld ? "Corrected." : `Corrected: Plum has ${correction.plum_value ?? "nothing"}.`} {reasonText(correction.reason)}
        </div>
      ) : null}
    </Row>
  );
}

/** A machine's serial number and year of manufacture - or, for a piece of kit (`kitTracking` set), its own
 *  number (one tracked one by one) or its count (a counted set, raised only), its year, and its model within
 *  the same kind. */
function DetailsForm({
  machine,
  kitTracking,
  modelChoices,
  busy,
  onSave,
  onCancel,
}: {
  machine: Machine;
  kitTracking: string | null;
  modelChoices: EquipmentModel[];
  busy: boolean;
  onSave: (body: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [serial, setSerial] = useState(machine.serial_number ?? "");
  const [year, setYear] = useState(machine.year_of_manufacture?.toString() ?? "");
  const [quantity, setQuantity] = useState(String(machine.quantity));
  const [modelId, setModelId] = useState(machine.model_public_id ?? "");
  const fields = detailFields(machine, kitTracking);
  const problem =
    year && !/^\d{4}$/.test(year.trim())
      ? "Give the year of manufacture as four digits."
      : fields.count && (!/^\d+$/.test(quantity.trim()) || Number(quantity) < machine.quantity)
        ? `Give the count, ${machine.quantity} or more. A set shrinks only by retiring the pieces that left.`
        : null;
  const body = () => detailsPayload(machine, kitTracking, { serial, year, quantity, modelId });
  return (
    <div className="form-grid section-form">
      {fields.count ? (
        <label className="field-stack">
          Pieces in the set
          <input value={quantity} onChange={(event) => setQuantity(event.target.value)} inputMode="numeric" maxLength={4} />
        </label>
      ) : null}
      {fields.number ? (
        <label className="field-stack">
          {kitTracking ? "Its own number" : "Serial number"}
          <input value={serial} onChange={(event) => setSerial(event.target.value)} maxLength={100} />
        </label>
      ) : null}
      <label className="field-stack">
        Year of manufacture
        <input value={year} onChange={(event) => setYear(event.target.value)} inputMode="numeric" maxLength={4} />
      </label>
      {fields.model ? (
        <label className="field-stack">
          Model
          <select value={modelId} onChange={(event) => setModelId(event.target.value)}>
            {modelChoices.map((model) => (
              <option key={model.model_public_id} value={model.model_public_id}>
                {model.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}
      <div className="form-actions">
        <button type="button" disabled={busy || Boolean(problem)} onClick={() => onSave(body())}>
          Save details
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
        {problem ? <p className="text-danger">{problem}</p> : null}
      </div>
    </div>
  );
}

function OwnValuesForm({
  machine,
  structure,
  busy,
  onSave,
  onCancel,
}: {
  machine: Machine;
  structure: Structure | null;
  busy: boolean;
  onSave: (capabilities: Record<string, unknown>[]) => void;
  onCancel: () => void;
}) {
  const equipmentClass = findClass(structure, machine.class_code);
  const [drafts, setDrafts] = useState<Record<string, { value: string; reason: string }>>(() => {
    const initial: Record<string, { value: string; reason: string }> = {};
    for (const capability of machine.capabilities) {
      if (capability.source_code === "OWN") initial[capability.capability_code] = { value: capability.choice_value ?? plainNumber(capability.value), reason: capability.reason ?? "" };
    }
    return initial;
  });
  const capabilities = equipmentClass?.capabilities ?? [];
  let problem: string | null = null;
  for (const capability of capabilities) {
    const draft = drafts[capability.capability_code];
    if (!draft || !draft.value.trim()) continue;
    problem = capabilityValueProblem(capability, draft.value) ?? (draft.reason.trim() ? null : `Give the reason for the ${capability.capability_label.toLowerCase()}.`);
    if (problem) break;
  }
  const payload = capabilities
    .filter((capability) => drafts[capability.capability_code]?.value.trim())
    .map((capability) => ({ ...capabilityPayload(capability, drafts[capability.capability_code].value), reason: drafts[capability.capability_code].reason.trim() }));
  return (
    <div className="section-form">
      <p className="helper-text">Leave a value blank to use the model's rating.</p>
      {capabilities.map((capability) => (
        <div key={capability.capability_code} className="form-grid">
          <label className="field-stack">
            {capability.capability_label}
            {capability.unit_symbol ? ` (${capability.unit_symbol})` : ""}
            <input
              value={drafts[capability.capability_code]?.value ?? ""}
              onChange={(event) => setDrafts({ ...drafts, [capability.capability_code]: { value: event.target.value, reason: drafts[capability.capability_code]?.reason ?? "" } })}
            />
          </label>
          <label className="field-stack">
            Reason
            <input
              value={drafts[capability.capability_code]?.reason ?? ""}
              maxLength={1000}
              onChange={(event) => setDrafts({ ...drafts, [capability.capability_code]: { value: drafts[capability.capability_code]?.value ?? "", reason: event.target.value } })}
            />
          </label>
        </div>
      ))}
      <button type="button" disabled={busy || Boolean(problem)} onClick={() => onSave(payload)}>
        Save own values
      </button>{" "}
      <button type="button" onClick={onCancel}>
        Cancel
      </button>
      {problem ? <p className="text-danger">{problem}</p> : null}
    </div>
  );
}

/** Add pieces of a kit model that fits this machine's model: several alike make a record each, a counted kind
 *  one set. The form's own request key: a double click adds once. */
function KitAddForm({
  machine,
  choices,
  structure,
  busy,
  onSave,
  onCancel,
}: {
  machine: Machine;
  choices: EquipmentModel[];
  structure: Structure | null;
  busy: boolean;
  onSave: (body: Record<string, unknown>, modelLabel: string) => void;
  onCancel: () => void;
}) {
  const [form, setForm] = useState<KitForm>(EMPTY_KIT_FORM);
  const [requestKey] = useState(newRequestKey);
  const chosen = choices.find((model) => model.model_public_id === form.kitModelId);
  const tracking = findClass(structure, chosen?.class_code ?? null)?.tracking_code;
  const problem = kitFormProblem(form, tracking);
  const edit = (next: Partial<KitForm>) => setForm({ ...form, ...next });
  return (
    <div className="form-grid section-form">
      <label className="field-stack">
        Kit model
        <select value={form.kitModelId} onChange={(event) => edit({ kitModelId: event.target.value, serialNumber: "" })}>
          <option value="">{choices.length ? "Choose a kit model" : "No kit model fits this model yet"}</option>
          {choices.map((model) => (
            <option key={model.model_public_id} value={model.model_public_id}>
              {model.label} ({model.class_label.toLowerCase()})
            </option>
          ))}
        </select>
      </label>
      <label className="field-stack">
        {tracking === "COUNTED" ? "How many in the set" : "How many alike"}
        <input value={form.count} onChange={(event) => edit({ count: event.target.value })} inputMode="numeric" maxLength={2} />
      </label>
      {tracking !== "COUNTED" && form.count.trim() === "1" ? (
        <label className="field-stack">
          Its own number (optional)
          <input value={form.serialNumber} onChange={(event) => edit({ serialNumber: event.target.value })} maxLength={100} />
        </label>
      ) : null}
      <label className="field-stack">
        Year of manufacture (optional)
        <input value={form.year} onChange={(event) => edit({ year: event.target.value })} inputMode="numeric" maxLength={4} />
      </label>
      <div className="form-actions">
        <button type="button" disabled={busy || Boolean(problem)} onClick={() => chosen && onSave(kitPayload(form, requestKey, machine, chosen), chosen.label)}>
          Add kit
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
        <p className="helper-text">
          {tracking === "COUNTED" ? "A counted kind is one record of the whole set." : "Several alike make one record each, numbered on their own pages."}
        </p>
        {problem && form.kitModelId ? <p className="text-danger">{problem}</p> : null}
      </div>
    </div>
  );
}

/** Retire a piece of kit, or some pieces of a counted set, with the reason and the day (a note with Other). */
function RetireKitForm({ held, busy, onSave, onCancel }: { held: number; busy: boolean; onSave: (body: Record<string, unknown>) => void; onCancel: () => void }) {
  const [form, setForm] = useState<RetireForm>({ reasonCode: "", retiredOn: TODAY(), note: "", count: String(held) });
  const problem = retireFormProblem(form, held, TODAY());
  const edit = (next: Partial<RetireForm>) => setForm({ ...form, ...next });
  return (
    <div className="form-grid section-form">
      <label className="field-stack">
        Why
        <select value={form.reasonCode} onChange={(event) => edit({ reasonCode: event.target.value })}>
          <option value="">Choose why</option>
          {Object.entries(RETIREMENT_REASON_LABELS).map(([code, label]) => (
            <option key={code} value={code}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <label className="field-stack">
        Retired on
        <DateInput value={form.retiredOn} onChange={(event) => edit({ retiredOn: event.target.value })} />
      </label>
      {held > 1 ? (
        <label className="field-stack">
          How many of the {held} pieces
          <input value={form.count} onChange={(event) => edit({ count: event.target.value })} inputMode="numeric" maxLength={4} />
        </label>
      ) : null}
      <label className="field-stack">
        Note{form.reasonCode === "OTHER" ? "" : " (optional)"}
        <input value={form.note} onChange={(event) => edit({ note: event.target.value })} maxLength={1000} />
      </label>
      <div className="form-actions">
        <button type="button" disabled={busy || Boolean(problem)} onClick={() => onSave(retirePayload(form, held))}>
          Retire
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
        {problem && form.reasonCode ? <p className="text-danger">{problem}</p> : null}
      </div>
    </div>
  );
}

function RemovablePart({ link, canManage, busy, onRemove }: { link: Machine["fitted_parts"][number]; canManage: boolean; busy: boolean; onRemove: (removedOn: string) => void }) {
  const [removedOn, setRemovedOn] = useState(TODAY());
  return (
    <div className="page-actions actions-with-fields">
      <a href={`/equipment/machines/${link.part.asset_public_id}`}>
        {link.part.asset_reference} - {link.part.machine_number}
      </a>
      <span>fitted since {link.fitted_on}</span>
      {canManage ? (
        <>
          <label className="field-stack">
            Removed on
            <DateInput value={removedOn} onChange={(event) => setRemovedOn(event.target.value)} />
          </label>
          <button type="button" disabled={busy || !removedOn} onClick={() => onRemove(removedOn)}>
            Remove part
          </button>
        </>
      ) : null}
    </div>
  );
}

function FitPartForm({
  machine,
  structure,
  busy,
  onSave,
  onCancel,
}: {
  machine: Machine;
  structure: Structure | null;
  busy: boolean;
  onSave: (body: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [parts, setParts] = useState<MachineSummary[] | null>(null);
  const [partId, setPartId] = useState("");
  const [fittedOn, setFittedOn] = useState(TODAY());
  const fitting = (structure?.classes ?? []).filter((item) => item.fits_class_codes.includes(machine.class_code)).map((item) => item.class_code);
  useEffect(() => {
    const token = getToken();
    if (!token) return;
    void (async () => {
      try {
        const response = await fetch("/api/equipment-reference/machines?kind_code=PART&flagged_only=true&status_code=ACTIVE&limit=200", {
          headers: { Authorization: `Bearer ${token}` },
        });
        setParts(response.ok ? ((await response.json()) as MachineSummary[]) : []);
      } catch {
        setParts([]);
      }
    })();
  }, []);
  const choices = (parts ?? []).filter((part) => part.flag_codes.includes("PART_NOT_FITTED") && fitting.includes(part.class_code));
  const chosen = choices.find((part) => part.asset_public_id === partId);
  return (
    <div className="form-grid section-form">
      <label className="field-stack">
        Part not yet fitted
        <select value={partId} onChange={(event) => setPartId(event.target.value)}>
          <option value="">{parts === null ? "Loading..." : choices.length ? "Choose a part" : "No unfitted part of a kind this machine takes"}</option>
          {choices.map((part) => (
            <option key={part.asset_public_id} value={part.asset_public_id}>
              {part.asset_reference} - {part.machine_number} ({part.model_label ?? part.class_label})
            </option>
          ))}
        </select>
      </label>
      <label className="field-stack">
        Fitted on
        <DateInput value={fittedOn} onChange={(event) => setFittedOn(event.target.value)} />
      </label>
      <div className="form-actions">
        <button
          type="button"
          disabled={busy || !chosen || !fittedOn}
          // The part's version as this list showed it: a part changed since is refused, not fitted unseen.
          onClick={() => chosen && onSave({ part_public_id: chosen.asset_public_id, expected_part_version: chosen.asset_version, fitted_on: fittedOn })}
        >
          Fit part
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </div>
  );
}

function CorrectionLine({
  correction,
  plumChanged,
  canManage,
  busy,
  onClose,
  onKeep,
}: {
  correction: MachineCorrection;
  plumChanged: boolean;
  canManage: boolean;
  busy: boolean;
  onClose: () => void;
  onKeep: () => void;
}) {
  const open = correction.correction_status_code === "OPEN";
  return (
    <div className="divided-item">
      <strong>{FIELD_LABELS[correction.field_code] ?? correction.field_code}</strong>: {correctionValuesText(correction)}{" "}
      <span className="helper-text">
        {reasonText(correction.reason)} - {correction.recorded_by_display_name ?? "-"}, {formatDateTime(correction.recorded_at)}.{" "}
        {open ? "Open." : `Closed${correction.closed_reason_code === "PLUM_AGREES" ? ": Plum now agrees" : correction.closed_reason_code === "SUPERSEDED" ? ": replaced by a newer correction" : ""}.`}
      </span>
      {open && plumChanged ? <p className="text-warning">Plum now holds another value. Keep this correction, or close it.</p> : null}
      {open && canManage ? (
        <div className="page-actions">
          {plumChanged && !correction.values_withheld ? (
            <button type="button" disabled={busy} onClick={onKeep}>
              Keep correction
            </button>
          ) : null}
          <button type="button" disabled={busy} onClick={onClose}>
            Close correction
          </button>
        </div>
      ) : null}
    </div>
  );
}

function CorrectionForm({
  machine,
  structure,
  models,
  busy,
  onSave,
  onCancel,
}: {
  machine: Machine;
  structure: Structure | null;
  models: EquipmentModel[];
  busy: boolean;
  onSave: (body: Record<string, unknown>) => void;
  onCancel: () => void;
}) {
  const [fieldCode, setFieldCode] = useState("");
  const [value, setValue] = useState("");
  const [reason, setReason] = useState("");
  const problem = correctionProblem(fieldCode, value, reason);
  const choose = (next: string) => {
    setFieldCode(next);
    setValue("");
  };
  return (
    <div className="form-grid section-form">
      <label className="field-stack">
        Field to correct
        <select value={fieldCode} onChange={(event) => choose(event.target.value)}>
          <option value="">Choose a field</option>
          {CORRECTION_FIELDS.map((code) => (
            <option key={code} value={code}>
              {FIELD_LABELS[code]}
            </option>
          ))}
        </select>
      </label>
      <label className="field-stack">
        Correct value
        {fieldCode === "CATEGORY" ? (
          <select value={value} onChange={(event) => setValue(event.target.value)}>
            <option value="">Choose the kind</option>
            {machineClasses(structure).map((item) => (
              <option key={item.class_code} value={item.class_code}>
                {item.class_label}
              </option>
            ))}
          </select>
        ) : fieldCode === "MODEL" ? (
          <select value={value} onChange={(event) => setValue(event.target.value)}>
            <option value="">Choose the model</option>
            {models
              // Kit is recorded on the platform: no machine is corrected to a kit model.
              .filter((model) => !model.is_retired && !model.is_kit && (model.class_code === machine.class_code || model.class_kind_code === "PART"))
              .map((model) => (
                <option key={model.model_public_id} value={model.model_public_id}>
                  {model.label} ({model.class_label})
                </option>
              ))}
          </select>
        ) : fieldCode === "STATUS" ? (
          <select value={value} onChange={(event) => setValue(event.target.value)}>
            <option value="">Choose</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
          </select>
        ) : (
          <input value={value} onChange={(event) => setValue(event.target.value)} maxLength={200} />
        )}
      </label>
      <label className="field-stack">
        Reason
        <input value={reason} onChange={(event) => setReason(event.target.value)} maxLength={1000} />
      </label>
      <div className="form-actions">
        <button type="button" disabled={busy || Boolean(problem)} onClick={() => onSave({ field_code: fieldCode, corrected_value: value.trim(), reason: reason.trim() })}>
          Record correction
        </button>
        <button type="button" onClick={onCancel}>
          Cancel
        </button>
        {fieldCode && problem ? <p className="helper-text">{problem}</p> : null}
      </div>
    </div>
  );
}
