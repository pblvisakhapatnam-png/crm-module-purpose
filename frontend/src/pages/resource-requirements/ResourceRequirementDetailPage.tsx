import { useEffect, useReducer, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import { PageHeader, SectionCard, StatusBadge } from "../../components/PageLayout";
import { billingBasisLabel, formatTermDate } from "../work-orders/workOrderBillingTermsState";
import ResourceRequirementFormFields from "./ResourceRequirementFormFields";
import {
  type ReturnTarget,
  clearSession,
  formatDateTime,
  getToken,
  hrefWithReturnTarget,
  readErrorDetail,
  readRoleCodes,
  readSafeReturnTarget,
} from "./pageSession";
import { INITIAL_DETAIL_STATE, detailReducer } from "./resourceRequirementDetailState";
import {
  type EquipmentStructure,
  type RequirementDefaults,
  type RequirementForm,
  type ResourceRequirement,
  canWriteRequirements,
  capabilityText,
  contractText,
  crewText,
  dateFactsAllowSave,
  dateFactsSaveProblem,
  isCompleteIsoDate,
  isLiveRequirement,
  itemMachineText,
  lineDatesText,
  priorityLabel,
  requirementDatesText,
  requirementFormProblem,
  requirementPayload,
  requirementSummary,
  shiftsPerDayText,
  siteText,
  statusLabel,
  warningLabel,
  workOrderCrewText,
} from "./resourceRequirementState";
import { SIGN_IN_FIRST } from "../../components/signInMessages";
import RequirementMachinesSection from "../allocations/RequirementMachinesSection";
import { canAllocate, lineSiteProblem } from "../allocations/allocationState";
import { centralAnswerText } from "../work-orders/WorkOrderLineDetailsSection";

// One requirement: what it asks for, the line's facts read live, its warnings, and - for Operations and
// Admin while it is open - changing it or cancelling it with a reason. Cancelling is final. What each
// event does to the page is resourceRequirementDetailState.ts's reducer, tested on its own.

const GRID_STYLE = { display: "grid", gridTemplateColumns: "220px 1fr", gap: "8px 12px", margin: 0 } as const;

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <>
      <dt style={{ color: "#6b7280", fontWeight: 700 }}>{label}</dt>
      <dd style={{ margin: 0 }}>{children}</dd>
    </>
  );
}

export default function ResourceRequirementDetailPage() {
  const params = useParams();
  const requirementId = params?.requirementId;
  const [state, dispatch] = useReducer(detailReducer, INITIAL_DETAIL_STATE);
  const [structure, setStructure] = useState<EquipmentStructure | null>(null);
  const [signInError, setSignInError] = useState("");
  const [canWrite, setCanWrite] = useState(false);
  const [returnTarget, setReturnTarget] = useState<ReturnTarget>({ href: "/resource-requirements", label: "Back to resource planning" });
  const [saving, setSaving] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  // Every request that may change the page - a load, or reading the Work Order for a date - is numbered;
  // the reducer applies only the answer it is waiting for.
  const tickets = useRef(0);
  const nextTicket = () => (tickets.current += 1);
  const { requirement, form } = state;
  const loadError = signInError || state.loadError;

  async function load(publicId: string) {
    const ticket = nextTicket();
    dispatch({ type: "load-started", ticket });
    const token = getToken();
    if (!token) {
      setSignInError(SIGN_IN_FIRST);
      return;
    }
    setSignInError("");
    try {
      const headers = { Authorization: `Bearer ${token}` };
      const [requirementResponse, structureResponse] = await Promise.all([
        fetch(`/api/resource-requirements/${encodeURIComponent(publicId)}`, { headers }),
        fetch("/api/equipment-reference/structure", { headers }),
      ]);
      if (requirementResponse.status === 401) clearSession();
      if (!requirementResponse.ok) {
        dispatch({ type: "load-failed", ticket, text: await readErrorDetail(requirementResponse, "The requirement could not be loaded.") });
        return;
      }
      // Installed only if this is still the load awaited; a fresh copy replaces every draft (see the reducer).
      dispatch({ type: "loaded", ticket, requirement: (await requirementResponse.json()) as ResourceRequirement });
      if (structureResponse.ok) setStructure((await structureResponse.json()) as EquipmentStructure);
    } catch {
      dispatch({ type: "load-failed", ticket, text: "Network error while loading the requirement." });
    }
  }

  useEffect(() => {
    setReturnTarget(readSafeReturnTarget("/resource-requirements", "Back to resource planning"));
    setCanWrite(canWriteRequirements(readRoleCodes()));
    if (typeof requirementId === "string") void load(requirementId);
  }, [requirementId]);

  /**
   * The line's facts on the date the change form now says, so the terms beside the fields are that date's.
   * Save waits for them, and a failed read must be repeated before saving (see the reducer).
   */
  async function loadLineFactsFor(date: string) {
    const ticket = nextTicket();
    dispatch({ type: "edit-date-changed", ticket, date });
    const token = getToken();
    if (!requirement || !isCompleteIsoDate(date)) return;
    if (!token) {
      dispatch({ type: "edit-line-failed", ticket });
      return;
    }
    try {
      const params = new URLSearchParams({ work_order_line_public_id: requirement.work_order_line_public_id, required_from: date });
      const response = await fetch(`/api/resource-requirements/defaults?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        dispatch({ type: "edit-line-failed", ticket });
        return;
      }
      const defaults = (await response.json()) as RequirementDefaults;
      dispatch({ type: "edit-line-loaded", ticket, line: defaults.line });
    } catch {
      dispatch({ type: "edit-line-failed", ticket });
    }
  }

  function changeForm(next: RequirementForm) {
    if (form && next.required_from !== form.required_from) void loadLineFactsFor(next.required_from);
    dispatch({ type: "form-changed", form: next });
  }

  async function saveChange() {
    // Save cannot be pressed until the facts for the date on the form are in; the reason is shown beside the
    // button from the facts themselves, never copied into the save message.
    if (!requirement || !form || !dateFactsAllowSave(state.dateFacts)) return;
    const problem = requirementFormProblem(form, structure);
    if (problem) {
      dispatch({ type: "change-refused", text: problem });
      return;
    }
    const token = getToken();
    if (!token) {
      dispatch({ type: "change-refused", text: "Your session has ended. Sign in again, then save." });
      return;
    }
    setSaving(true);
    try {
      const response = await fetch(`/api/resource-requirements/${encodeURIComponent(requirement.requirement_public_id)}`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ ...requirementPayload(form, structure), expected_requirement_version: requirement.requirement_version }),
      });
      if (response.status === 409) {
        dispatch({
          type: "change-refused",
          text: "Someone else changed this requirement after you opened it. Refresh to see their version; your changes here will be discarded.",
        });
        return;
      }
      if (!response.ok) {
        dispatch({ type: "change-refused", text: await readErrorDetail(response, "The change could not be saved.") });
        return;
      }
      const body = (await response.json()) as { resource_requirement: ResourceRequirement; event: unknown };
      dispatch({ type: "change-saved", requirement: body.resource_requirement, recorded: Boolean(body.event) });
    } catch {
      dispatch({ type: "change-refused", text: "Network error while saving the change. Try again." });
    } finally {
      setSaving(false);
    }
  }

  async function cancelRequirement() {
    if (!requirement) return;
    const token = getToken();
    if (!token) {
      dispatch({ type: "cancel-refused", text: "Your session has ended. Sign in again, then cancel." });
      return;
    }
    setCancelling(true);
    try {
      const response = await fetch(`/api/resource-requirements/${encodeURIComponent(requirement.requirement_public_id)}/cancel`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ expected_requirement_version: requirement.requirement_version, cancellation_reason: state.reason.trim() }),
      });
      if (response.status === 409) {
        dispatch({ type: "cancel-refused", text: "Someone else changed this requirement after you opened it. Refresh, then cancel." });
        return;
      }
      if (!response.ok) {
        dispatch({ type: "cancel-refused", text: await readErrorDetail(response, "The requirement could not be cancelled.") });
        return;
      }
      const body = (await response.json()) as { resource_requirement: ResourceRequirement };
      dispatch({ type: "cancelled", requirement: body.resource_requirement });
    } catch {
      dispatch({ type: "cancel-refused", text: "Network error while cancelling. Try again." });
    } finally {
      setCancelling(false);
    }
  }

  const item = requirement?.items[0];
  const isOpen = isLiveRequirement(requirement?.requirement_status_code);
  const isClosedWorkOrder = requirement?.line.work_order_status_code === "CLOSED";
  const writable = canWrite && isOpen && !isClosedWorkOrder;
  const workOrderHref = requirement
    ? hrefWithReturnTarget(`/work-orders/${requirement.work_order_public_id}`, `/resource-requirements/${requirement.requirement_public_id}`, "Back to requirement")
    : "";

  return (
    <section>
      <PageHeader
        eyebrow="Resource requirement"
        back={returnTarget}
        title={requirement ? `${requirement.requirement_reference} - ${requirementSummary(requirement)}` : "Resource requirement"}
        badges={
          requirement ? (
            <>
              <StatusBadge code={requirement.requirement_status_code} label={statusLabel(requirement.requirement_status_code)} />
              {requirement.priority_code === "URGENT" ? <span className="status-badge status-badge--warning">Urgent</span> : null}
            </>
          ) : null
        }
        subtitle="What one Work Order line needs on site, and the machines allocated to it. Before the Work Order is released, allocated machines are held for it."
        actions={
          <button type="button" onClick={() => typeof requirementId === "string" && void load(requirementId)} style={{ padding: "10px 12px" }}>
            Refresh
          </button>
        }
      >
        {loadError ? <p style={{ color: "crimson" }}>{loadError}</p> : null}
        {!loadError && !requirement ? <p className="helper-text">Loading the requirement...</p> : null}
      </PageHeader>

      {requirement && item ? (
        <div style={{ marginTop: "24px", display: "grid", gap: "16px", maxWidth: "1120px" }}>
          {requirement.warnings.length > 0 ? (
            <SectionCard title="Needs attention" tone="amber">
              <ul style={{ margin: 0, paddingLeft: "20px" }}>
                {requirement.warnings.map((warning) => (
                  <li key={warning}>{warningLabel(warning)}</li>
                ))}
              </ul>
            </SectionCard>
          ) : null}

          <SectionCard title="What is needed" tone="blue">
            <dl style={GRID_STYLE}>
              <Row label="Number of machines">{requirement.units_required}</Row>
              <Row label="Machine">{itemMachineText(item)}</Row>
              <Row label="Capabilities">
                {item.capabilities.length > 0 ? item.capabilities.map((capability) => capabilityText(capability)).join("; ") : "None stated"}
              </Row>
              <Row label="Anything else">{item.equipment_specification || "-"}</Row>
              <Row label="When">{requirementDatesText(requirement)}</Row>
              <Row label="Crew on site">{crewText(requirement.crew_operators_required, requirement.crew_helpers_required)}</Row>
              <Row label="Licences and skills">{requirement.crew_notes || "-"}</Row>
              <Row label="Priority">{priorityLabel(requirement.priority_code)}</Row>
              <Row label="Planning notes">{requirement.planning_notes || "-"}</Row>
              <Row label="Recorded">
                {formatDateTime(requirement.created_at)}
                {requirement.created_by_display_name ? ` by ${requirement.created_by_display_name}` : ""}
              </Row>
              <Row label="Last changed">
                {formatDateTime(requirement.updated_at)}
                {requirement.updated_by_display_name ? ` by ${requirement.updated_by_display_name}` : ""}
              </Row>
              {requirement.cancelled_at ? (
                <Row label="Cancelled">
                  {formatDateTime(requirement.cancelled_at)}
                  {requirement.cancelled_by_display_name ? ` by ${requirement.cancelled_by_display_name}` : ""}: {requirement.cancellation_reason}
                </Row>
              ) : null}
            </dl>
          </SectionCard>

          <SectionCard title="The Work Order line, as it stands now" tone="teal">
            <dl style={GRID_STYLE}>
              <Row label="Work Order">
                <a href={workOrderHref} style={{ color: "#1d4ed8", fontWeight: 700 }}>
                  {requirement.work_order_code}
                </a>
                , line {requirement.work_order_line_number}
              </Row>
              <Row label="Scope">{requirement.line.scope_description}</Row>
              <Row label="Quantity (billing units)">
                {requirement.line.quantity} {requirement.line.uom}
              </Row>
              <Row label="Site">{siteText(requirement.line)}</Row>
              <Row label="Central-government site">{centralAnswerText(requirement.line.site_central_government)}</Row>
              <Row label="Contract">{contractText(requirement.line)}</Row>
              <Row label="Line dates">{lineDatesText(requirement.line)}</Row>
              <Row label="Billing basis">
                {billingBasisLabel(requirement.line.billing_uom_code) ?? "Not recorded yet"}
                {shiftsPerDayText(requirement.line.shifts_per_day) ? `, ${shiftsPerDayText(requirement.line.shifts_per_day)}` : ""}
              </Row>
              <Row label="Crew in the Work Order">{workOrderCrewText(requirement.line)}</Row>
              {requirement.line.contract_gaps.length > 0 ? (
                <Row label="No contract runs">
                  {requirement.line.contract_gaps
                    .map((gap) => `${formatTermDate(gap.first_day)} to ${formatTermDate(gap.last_day)}`)
                    .join("; ")}
                </Row>
              ) : null}
            </dl>
          </SectionCard>

          <RequirementMachinesSection
            requirementPublicId={requirement.requirement_public_id}
            unitsRequired={requirement.units_required}
            unitsCovered={requirement.units_covered ?? 0}
            coveredUnits={requirement.covered_unit_numbers ?? []}
            canAllocateHere={canAllocate(readRoleCodes()) && isOpen && !isClosedWorkOrder}
            siteProblem={lineSiteProblem(requirement.line, requirement.work_order_line_number)}
          />

          {writable ? (
            <SectionCard title="Change this requirement" tone="violet">
              {form ? (
                <>
                  <ResourceRequirementFormFields
                    form={form}
                    structure={structure}
                    line={state.editLine ?? requirement.line}
                    onChange={changeForm}
                    keptTypeCode={item.equipment_type_code ?? ""}
                    keptCapabilityCodes={item.capabilities.map((capability) => capability.capability_code)}
                  />
                  <div style={{ marginTop: "14px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
                    <button
                      type="button"
                      onClick={() => void saveChange()}
                      disabled={saving || !dateFactsAllowSave(state.dateFacts)}
                      style={{ padding: "8px 12px", fontWeight: 700 }}
                    >
                      {saving ? "Saving..." : state.dateFacts.status === "loading" ? "Reading the Work Order for that date..." : "Save changes"}
                    </button>
                    {state.dateFacts.status === "failed" ? (
                      <button type="button" onClick={() => void loadLineFactsFor(form.required_from)} style={{ padding: "8px 12px" }}>
                        Read the Work Order again
                      </button>
                    ) : null}
                    <button type="button" onClick={() => dispatch({ type: "change-discarded" })} style={{ padding: "8px 12px" }}>
                      Discard changes
                    </button>
                  </div>
                  {state.dateFacts.status === "failed" ? (
                    <p style={{ color: "crimson", margin: "6px 0 0 0" }}>{dateFactsSaveProblem(state.dateFacts)}</p>
                  ) : null}
                </>
              ) : (
                <button type="button" onClick={() => dispatch({ type: "change-started" })} style={{ padding: "8px 12px", fontWeight: 700 }}>
                  Change the requirement
                </button>
              )}
              {state.saveFeedback ? (
                <p style={{ color: state.saveFeedback.kind === "success" ? "#065f46" : "crimson", margin: "6px 0 0 0" }}>
                  {state.saveFeedback.text}
                </p>
              ) : null}
            </SectionCard>
          ) : null}

          {writable || state.cancelFeedback ? (
            <SectionCard title="Cancel this requirement" tone="slate">
              {writable ? (
                <>
                  <p style={{ marginTop: 0 }}>
                    Cancelling is final: the requirement is kept with its reason and cannot be reopened. Every machine held for it
                    is freed, and stays on the Work Order's history.
                  </p>
                  <label className="field-stack" style={{ maxWidth: "640px" }}>
                    Why it is being cancelled
                    <textarea
                      rows={2}
                      maxLength={2000}
                      value={state.reason}
                      onChange={(event) => dispatch({ type: "reason-changed", reason: event.target.value })}
                    />
                  </label>
                  <div style={{ marginTop: "10px", display: "flex", gap: "10px", flexWrap: "wrap" }}>
                    {state.confirmingCancel ? (
                      <>
                        <button type="button" onClick={() => void cancelRequirement()} disabled={cancelling} style={{ padding: "8px 12px", fontWeight: 700 }}>
                          {cancelling ? "Cancelling..." : "Yes, cancel it"}
                        </button>
                        <button type="button" onClick={() => dispatch({ type: "cancel-withdrawn" })} style={{ padding: "8px 12px" }}>
                          Keep it
                        </button>
                      </>
                    ) : (
                      <button type="button" onClick={() => dispatch({ type: "cancel-asked" })} style={{ padding: "8px 12px" }}>
                        Cancel this requirement
                      </button>
                    )}
                  </div>
                </>
              ) : null}
              {state.cancelFeedback ? (
                <p style={{ color: state.cancelFeedback.kind === "success" ? "#065f46" : "crimson", margin: "6px 0 0 0" }}>
                  {state.cancelFeedback.text}
                </p>
              ) : null}
            </SectionCard>
          ) : null}

          {!writable && isOpen && !canWrite ? (
            <p style={{ color: "#6b7280" }}>Your role can view this requirement. Operations and Admin can change or cancel it.</p>
          ) : null}
          {isOpen && isClosedWorkOrder ? (
            <p style={{ color: "#6b7280" }}>This Work Order is closed, so its requirements can no longer be changed.</p>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
