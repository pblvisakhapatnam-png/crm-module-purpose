import { useEffect, useRef, useState } from "react";

import { PageHeader, SectionCard } from "../../components/PageLayout";
import ResourceRequirementFormFields from "./ResourceRequirementFormFields";
import {
  type ReturnTarget,
  clearSession,
  getToken,
  hrefWithReturnTarget,
  readErrorDetail,
  readRoleCodes,
  readSafeReturnTarget,
} from "./pageSession";
import {
  type EquipmentStructure,
  type RequirementDefaults,
  type RequirementForm,
  type ResourceRequirement,
  CREW_UNTOUCHED,
  type CrewTouched,
  DATE_FACTS_CURRENT,
  type DateFacts,
  canWriteRequirements,
  crewTouchedAfterEdit,
  dateFactsAllowSave,
  dateFactsAnswered,
  dateFactsAsked,
  dateFactsSaveProblem,
  formAfterLineDefaults,
  formFromDefaults,
  isCompleteIsoDate,
  newRequestKey,
  REQUIREMENT_NETWORK_ERROR,
  requirementFormProblem,
  requirementPayload,
  requirementRecordedText,
  siteText,
} from "./resourceRequirementState";
import { SIGN_IN_FIRST } from "../../components/signInMessages";

// Record what one Work Order line needs on site (WRR-001). Reached from a line's "Add a requirement" on
// the Work Order page, which names the line in the query string. The form starts from the server's
// suggested values: the Work Order's crew in force, a class from the line's category.

type Feedback = { kind: "success" | "error"; text: string } | null;

function lineFromQuery(): string {
  if (typeof window === "undefined") return "";
  return new URLSearchParams(window.location.search).get("work_order_line") ?? "";
}

export default function NewResourceRequirementPage() {
  const [lineId] = useState(lineFromQuery);
  const [returnTarget, setReturnTarget] = useState<ReturnTarget>({ href: "/resource-requirements", label: "Back to resource planning" });
  const [defaults, setDefaults] = useState<RequirementDefaults | null>(null);
  const [structure, setStructure] = useState<EquipmentStructure | null>(null);
  const [form, setForm] = useState<RequirementForm | null>(null);
  const [loadError, setLoadError] = useState("");
  const [canWrite, setCanWrite] = useState(false);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  // Whether the Work Order's facts for the start date on the form are in. While they are on their way, or
  // after reading them failed, the crew and terms shown are another date's, so Save waits (F-07, F-12).
  const [dateFacts, setDateFacts] = useState<DateFacts>(DATE_FACTS_CURRENT);
  // One key for this form, kept across retries, so a repeated save records one requirement (ADR-023).
  const requestKey = useRef(newRequestKey());
  // Crew numbers the user has typed are theirs, each on its own: a new start date never overwrites one, and
  // the other still follows the date. Read from a ref because the answer for a new date arrives after the
  // render that asked for it.
  const crewTouched = useRef<CrewTouched>(CREW_UNTOUCHED);
  // Each reading of the Work Order for a date is numbered; only the answer awaited is applied.
  const dateTickets = useRef(0);

  useEffect(() => {
    setReturnTarget(readSafeReturnTarget("/resource-requirements", "Back to resource planning"));
    setCanWrite(canWriteRequirements(readRoleCodes()));
    if (!lineId) {
      setLoadError("No Work Order line was named. Start from a line's \"Add a requirement\" on the Work Order page.");
      return;
    }
    const token = getToken();
    if (!token) {
      setLoadError(SIGN_IN_FIRST);
      return;
    }
    let cancelled = false;
    void (async () => {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const [defaultsResponse, structureResponse] = await Promise.all([
          fetch(`/api/resource-requirements/defaults?work_order_line_public_id=${encodeURIComponent(lineId)}`, { headers }),
          fetch("/api/equipment-reference/structure", { headers }),
        ]);
        if (cancelled) return;
        if (defaultsResponse.status === 401 || structureResponse.status === 401) clearSession();
        if (!defaultsResponse.ok) {
          setLoadError(await readErrorDetail(defaultsResponse, "The Work Order line could not be loaded."));
          return;
        }
        if (!structureResponse.ok) {
          setLoadError(await readErrorDetail(structureResponse, "The equipment structure could not be loaded."));
          return;
        }
        const loadedDefaults = (await defaultsResponse.json()) as RequirementDefaults;
        const loadedStructure = (await structureResponse.json()) as EquipmentStructure;
        if (cancelled) return;
        setDefaults(loadedDefaults);
        setStructure(loadedStructure);
        setForm(formFromDefaults(loadedDefaults));
      } catch {
        if (!cancelled) setLoadError("Network error while loading the Work Order line.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [lineId]);

  function change(next: RequirementForm) {
    // The user's own edit clears a stale message.
    setFeedback(null);
    if (form) crewTouched.current = crewTouchedAfterEdit(crewTouched.current, form, next);
    if (form && next.required_from !== form.required_from) void loadDefaultsFor(next.required_from);
    setForm(next);
  }

  /**
   * The Work Order's facts on a new start date - the billing terms and crew in force then (Q4) - shown beside
   * the fields, and the crew filled from them unless the user has typed crew of their own.
   */
  async function loadDefaultsFor(date: string) {
    dateTickets.current += 1;
    const ticket = dateTickets.current;
    setDateFacts(dateFactsAsked(ticket, date));
    if (!isCompleteIsoDate(date)) return;
    const token = getToken();
    const answered = (succeeded: boolean) => setDateFacts((current) => dateFactsAnswered(current, ticket, succeeded));
    if (!token || !lineId) {
      answered(false);
      return;
    }
    try {
      const params = new URLSearchParams({ work_order_line_public_id: lineId, required_from: date });
      const response = await fetch(`/api/resource-requirements/defaults?${params.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        answered(false);
        return;
      }
      const next = (await response.json()) as RequirementDefaults;
      // A later date was asked for meanwhile: this answer is stale and changes nothing.
      if (ticket !== dateTickets.current) return;
      setDefaults((current) => (current ? { ...current, line: next.line } : current));
      setForm((current) => (current ? formAfterLineDefaults(current, next.suggested, crewTouched.current) : current));
      answered(true);
    } catch {
      answered(false);
    }
  }

  async function save() {
    // Save cannot be pressed until the facts for the date on the form are in; the reason is shown beside the
    // button from the facts themselves, never copied into this message.
    if (!form || !defaults || !dateFactsAllowSave(dateFacts)) return;
    const problem = requirementFormProblem(form, structure);
    if (problem) {
      setFeedback({ kind: "error", text: problem });
      return;
    }
    const token = getToken();
    if (!token) {
      setFeedback({ kind: "error", text: "Your session has ended. Sign in again, then save." });
      return;
    }
    setSaving(true);
    setFeedback(null);
    try {
      const response = await fetch("/api/resource-requirements", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({
          ...requirementPayload(form, structure),
          work_order_public_id: defaults.work_order_public_id,
          work_order_line_public_id: defaults.work_order_line_public_id,
          create_request_key: requestKey.current,
        }),
      });
      if (!response.ok) {
        setFeedback({ kind: "error", text: await readErrorDetail(response, "The requirement could not be recorded.") });
        return;
      }
      const body = (await response.json()) as { resource_requirement: ResourceRequirement; replayed: boolean };
      const created = body.resource_requirement;
      setFeedback({ kind: "success", text: requirementRecordedText(created.requirement_reference, body.replayed) });
      window.location.assign(
        hrefWithReturnTarget(`/resource-requirements/${created.requirement_public_id}`, returnTarget.href, returnTarget.label),
      );
    } catch {
      setFeedback({ kind: "error", text: REQUIREMENT_NETWORK_ERROR });
    } finally {
      setSaving(false);
    }
  }

  return (
    <section>
      <PageHeader
        eyebrow="Resource requirement"
        back={returnTarget}
        title="Add a requirement"
        subtitle="Record what this Work Order line needs on site - what kind of machine, how capable, how many, when, and with what crew - so planning can start before the Work Order is released. It does not change the Work Order and does not reserve or assign anything."
      >
        {loadError ? <p style={{ color: "crimson" }}>{loadError}</p> : null}
        {!loadError && !form ? <p className="helper-text">Loading the Work Order line...</p> : null}
      </PageHeader>

      {defaults && form ? (
        <div style={{ marginTop: "24px", display: "grid", gap: "16px", maxWidth: "960px" }}>
          <SectionCard title={`${defaults.work_order_code}, line ${defaults.work_order_line_number}`} tone="teal">
            <p style={{ marginTop: 0 }}>{defaults.line.scope_description}</p>
            <p style={{ margin: 0, color: "#6b7280" }}>
              Category: {defaults.line.equipment_service_category || "-"}. Site: {siteText(defaults.line)}.
              {defaults.existing_requirement_count > 0
                ? ` This line already has ${defaults.existing_requirement_count} requirement${defaults.existing_requirement_count === 1 ? "" : "s"}.`
                : ""}
            </p>
            <p style={{ marginBottom: 0 }}>
              <a href={returnTarget.href} style={{ color: "#1d4ed8", fontWeight: 700 }}>
                {returnTarget.label}
              </a>
            </p>
          </SectionCard>

          {canWrite ? (
            <SectionCard title="The requirement" tone="blue">
              <ResourceRequirementFormFields
                form={form}
                structure={structure}
                line={defaults.line}
                onChange={change}
                suggestedFrom={
                  defaults.suggested.equipment_class_code && form.equipment_class_code === defaults.suggested.equipment_class_code
                    ? defaults.suggested.equipment_class_matched_term
                    : null
                }
              />
              <div style={{ marginTop: "14px" }}>
                <button
                  type="button"
                  onClick={() => void save()}
                  disabled={saving || !dateFactsAllowSave(dateFacts)}
                  style={{ padding: "8px 12px", fontWeight: 700 }}
                >
                  {saving ? "Saving..." : dateFacts.status === "loading" ? "Reading the Work Order for that date..." : "Save requirement"}
                </button>
                {dateFacts.status === "failed" ? (
                  <>
                    {" "}
                    <button
                      type="button"
                      onClick={() => {
                        setFeedback(null);
                        void loadDefaultsFor(form.required_from);
                      }}
                      style={{ padding: "8px 12px" }}
                    >
                      Read the Work Order again
                    </button>
                    <p style={{ color: "crimson", margin: "6px 0 0 0" }}>{dateFactsSaveProblem(dateFacts)}</p>
                  </>
                ) : null}
                {feedback ? (
                  <p style={{ color: feedback.kind === "success" ? "#065f46" : "crimson", margin: "6px 0 0 0" }}>{feedback.text}</p>
                ) : null}
              </div>
            </SectionCard>
          ) : (
            <p style={{ color: "#6b7280" }}>Your role can view resource requirements but cannot record one.</p>
          )}
        </div>
      ) : null}
    </section>
  );
}
