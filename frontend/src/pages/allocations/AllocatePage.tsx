import { useEffect, useRef, useState } from "react";

import DateInput from "../../components/DateInput";
import { PageHeader, SectionCard, StatusBadge } from "../../components/PageLayout";
import { SIGN_IN_FIRST } from "../../components/signInMessages";
import { createQueryController, formatDay, initialQueryView, queryView, type QueryView } from "../equipment/certificatesState";
import {
  getToken,
  hrefWithReturnTarget,
  readRoleCodes,
  readSafeReturnTarget,
  SESSION_CHANGED_EVENT,
  type ReturnTarget,
} from "../resource-requirements/pageSession";
import { createLatestOnly } from "../resource-requirements/resourceRequirementState";
import { fetchAssignment, fetchCandidates, newRequestKey, send, ASSIGNMENTS_URL } from "./allocationRequests";
import {
  type AllocateForm,
  type Assignment,
  type AssignmentAction,
  type Candidate,
  type Candidates,
  type FinderQuery,
  BILLING_CYCLE_OPTIONS,
  EMPTY_ALLOCATE_FORM,
  REPLACEMENT_REASONS,
  allocateProblem,
  answerIsForDates,
  answerLabel,
  answerResultText,
  answerTone,
  WORK_ORDER_CLOSED_TEXT,
  assetLabel,
  assignmentDaysText,
  billingCycleLabel,
  canAllocate,
  canSetBillingCycle,
  capabilityText,
  conflictText,
  createPayload,
  daysText,
  formAfterChoosing,
  leftOutText,
  machineKindText,
  replacePayload,
  requirementText,
  resultsToShow,
  siteText,
  replaceStartProblem,
  replacingProblem,
  unitFromSearch,
  todayIso,
  workOrderClosed,
} from "./allocationState";

// Allocate a machine to one unit of a requirement, or replace an allocation's machine (design sections 6.2, 6.3
// and 6.6). The server finds the machines that meet the requirement, says which are free and gives each today's
// answer for the site; the user chooses one. Every rule is the server's; this page only words it.

type Feedback = { kind: "success" | "error"; text: string } | null;

/** This finder's own address, for a machine's page to come back to. */
function finderHref(): string {
  return typeof window === "undefined" ? "" : `${window.location.pathname}${window.location.search}`;
}

function readQuery(): FinderQuery {
  const params = new URLSearchParams(typeof window === "undefined" ? "" : window.location.search);
  return {
    requirement: params.get("requirement") ?? "",
    unit: unitFromSearch(params.get("unit")),
    from: "",
    to: "",
    replacing: params.get("replacing") ?? "",
  };
}

export default function AllocatePage() {
  const [view, setView] = useState<QueryView<Candidates>>(initialQueryView<Candidates>());
  const [dates, setDates] = useState({ from: "", to: "" });
  const [form, setForm] = useState<AllocateForm>(EMPTY_ALLOCATE_FORM);
  const [replacing, setReplacing] = useState<Assignment | null>(null);
  const [replacingError, setReplacingError] = useState("");
  const [roles, setRoles] = useState<string[]>([]);
  const [returnTarget, setReturnTarget] = useState<ReturnTarget>({ href: "/resource-requirements", label: "Back to resource planning" });
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const requestKey = useRef(newRequestKey());
  const replacingTickets = useRef(createLatestOnly());
  // Counted up on every session change: a save answering for an earlier session changes nothing (8A-FB2-002).
  const session = useRef(0);
  const controller = useRef(
    createQueryController<FinderQuery, Candidates>({
      initialQuery: readQuery(),
      getToken,
      fetchAnswer: fetchCandidates,
      show: (update) => {
        setView((current) => queryView(current, update));
        // The first answer gives the period the server chose; the date boxes then show it.
        if (update.kind === "answer") setDates({ from: update.answer.period_from, to: update.answer.period_to ?? "" });
      },
      failure: "The machines could not be found.",
    }),
  );

  const query = controller.current.query();
  const isReplacing = Boolean(query.replacing);

  /** The allocation being replaced, read under the session now in use: an answer is shown only for the latest
   * request, so one sent before signing out never appears after (8A-FB-002). */
  function loadReplacing() {
    const ticket = replacingTickets.current.begin();
    setReplacing(null);
    setReplacingError("");
    if (!query.replacing) return;
    const token = getToken();
    if (!token) {
      setReplacingError(SIGN_IN_FIRST);
      return;
    }
    fetchAssignment(token, query.replacing).then(
      (found) => replacingTickets.current.isLatest(ticket) && setReplacing(found),
      (error: unknown) =>
        replacingTickets.current.isLatest(ticket) &&
        setReplacingError(error instanceof Error ? error.message : "The allocation being replaced could not be loaded."),
    );
  }

  useEffect(() => {
    setRoles(readRoleCodes());
    const requirementHref = query.requirement ? `/resource-requirements/${query.requirement}` : "/resource-requirements";
    setReturnTarget(readSafeReturnTarget(requirementHref, "Back to the requirement"));
    void controller.current.refresh();
    loadReplacing();
    // Signing out, or in as someone else: the roles are read again, the machines found, the choice and the
    // message dropped, and the machines found again under the new session - with none, the page asks to sign in.
    const onSessionChanged = () => {
      session.current += 1;
      requestKey.current = newRequestKey();
      setRoles(readRoleCodes());
      setSaving(false);
      setFeedback(null);
      setForm(EMPTY_ALLOCATE_FORM);
      setDates({ from: "", to: "" });
      setView(initialQueryView<Candidates>());
      void controller.current.refresh();
      loadReplacing();
    };
    window.addEventListener(SESSION_CHANGED_EVENT, onSessionChanged);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, onSessionChanged);
  }, []);

  function findAgain() {
    setFeedback(null);
    setForm((current) => ({ ...current, machine_public_id: "", accept_warnings: false }));
    void controller.current.setQuery({ ...controller.current.query(), from: dates.from, to: dates.to });
  }

  function changeDates(next: { from: string; to: string }) {
    // The machines shown were found for the dates before: the choice goes, and saving waits for a fresh find.
    setDates(next);
    setFeedback(null);
    setForm((current) => ({ ...current, machine_public_id: "", accept_warnings: false }));
  }

  const answer = view.answer;
  const chosen: Candidate | undefined = answer?.candidates.find((item) => item.machine.asset_public_id === form.machine_public_id);
  const mayAllocate = canAllocate(roles);
  const mayBill = canSetBillingCycle(roles);
  const datesShown = answer ? answerIsForDates(answer, dates) && !view.loading : false;
  const siteProblem = answer?.site.problem_code ? answer.site.problem_message : null;
  const closed = answer ? workOrderClosed(answer.requirement) : false;
  const unitTaken = Boolean(answer && answer.unit_conflicts.length > 0);
  const replacingWrong = isReplacing && replacing ? replacingProblem(replacing, { requirement: query.requirement, unit: query.unit }) : null;
  const replaceProblem =
    replacingWrong ?? (answer && isReplacing && replacing ? replaceStartProblem(answer.period_from, replacing, todayIso()) : null);
  const mayChoose = mayAllocate && datesShown && !siteProblem && !closed && !unitTaken && !replaceProblem;

  async function allocate() {
    if (!answer) return;
    const problem = allocateProblem(form, chosen, isReplacing, {
      site: answer.site,
      datesShown,
      workOrderClosed: closed,
      unitTaken,
      replaceProblem,
    });
    if (problem) {
      setFeedback({ kind: "error", text: problem });
      return;
    }
    if (isReplacing && !replacing) {
      setFeedback({ kind: "error", text: "The allocation being replaced is not loaded yet." });
      return;
    }
    const period = { period_from: answer.period_from, period_to: answer.period_to };
    const generation = session.current;
    setSaving(true);
    setFeedback(null);
    const sent = isReplacing
      ? await send<AssignmentAction>(
          "POST",
          `${ASSIGNMENTS_URL}/${encodeURIComponent(query.replacing)}/replace`,
          replacePayload(replacing!.assignment_version, period, form, requestKey.current, mayBill),
          "The machine could not be replaced.",
        )
      : await send<AssignmentAction>(
          "POST",
          ASSIGNMENTS_URL,
          createPayload(answer.requirement.requirement_public_id, answer.unit_number, period, form, requestKey.current, mayBill),
          "The machine could not be allocated.",
        );
    // Signed out, or in as someone else, meanwhile: the answer belongs to the earlier session and changes nothing here.
    if (session.current !== generation) return;
    setSaving(false);
    if (!sent.ok) {
      setFeedback({ kind: "error", text: sent.message });
      // A refused request never reached the database's key; a new try gets its own key only after a change.
      return;
    }
    setFeedback({ kind: "success", text: `${sent.body.assignment.assignment_reference} is held. Opening it...` });
    window.location.assign(
      hrefWithReturnTarget(
        `/resource-assignments/${sent.body.assignment.assignment_public_id}`,
        `/resource-requirements/${answer.requirement.requirement_public_id}`,
        "Back to the requirement",
      ),
    );
  }

  const requirement = answer?.requirement;
  const leftOut = answer ? leftOutText(answer.left_out) : "";

  return (
    <section>
      <PageHeader
        eyebrow={isReplacing ? "Replace a machine" : "Allocate a machine"}
        back={returnTarget}
        title={requirement ? `${requirement.requirement_reference}, unit ${query.unit} - ${requirementText(requirement)}` : "Find a machine"}
        subtitle={
          isReplacing
            ? "The new machine takes the unit over from its first day; the old one's days end the day before, and both stay on the Work Order's history."
            : "Only machines that meet what the requirement asks for are offered. Before the Work Order is released, an allocation holds the machine for it."
        }
      >
        {view.error ? <p className="text-danger">{view.error}</p> : null}
        {replacingError ? <p className="text-danger">{replacingError}</p> : null}
        {view.loading ? <p className="helper-text">Finding machines...</p> : null}
      </PageHeader>

      <div className="page-sections">
        {isReplacing && replacing ? (
          <SectionCard title="Replacing" tone="amber">
            <dl className="facts-list">
              <dt>Allocation</dt>
              <dd>
                {replacing.assignment_reference}: {assetLabel(replacing.machine)}, {assignmentDaysText(replacing)}
              </dd>
              <dt>Billing cycle</dt>
              <dd>{billingCycleLabel(replacing.billing_cycle_code)} - kept for the new machine unless changed below</dd>
            </dl>
          </SectionCard>
        ) : null}

        {answer ? (
          <SectionCard title="Where and when" tone="blue">
            <dl className="facts-list">
              <dt>Site</dt>
              <dd>
                {siteText(answer.site)}
                {answer.site.problem_message ? <span className="text-danger"> - {answer.site.problem_message}</span> : null}
              </dd>
              <dt>Requirement's days</dt>
              <dd>{daysText(answer.requirement.required_from, answer.requirement.planned_end)}</dd>
            </dl>
            <div className="form-grid">
              <label className="field-stack">
                {isReplacing ? "Replaces from" : "From"}
                <DateInput value={dates.from} disabled={saving} onChange={(event) => changeDates({ ...dates, from: event.target.value })} />
              </label>
              <label className="field-stack">
                To
                <DateInput value={dates.to} disabled={saving} onChange={(event) => changeDates({ ...dates, to: event.target.value })} />
              </label>
              <div className="form-actions">
                <button type="button" onClick={findAgain} disabled={view.loading || saving}>
                  Find machines for these days
                </button>
              </div>
            </div>
            {answer.unit_conflicts.length > 0 ? (
              <p className="text-danger">
                Unit {answer.unit_number} already has a machine on some of these days: {answer.unit_conflicts.map(conflictText).join("; ")}.
                Choose other days.
              </p>
            ) : null}
          </SectionCard>
        ) : null}

        {answer ? (
          <SectionCard title={`Machines for ${daysText(answer.period_from, answer.period_to)}`} tone="teal">
            {!datesShown && !view.loading ? (
              <p className="text-warning">These machines are for the dates found before. Find machines for these days to choose from them.</p>
            ) : null}
            {answer.candidates.length === 0 ? <p className="empty-state">No machine of this kind meets the requirement.</p> : null}
            {leftOut ? <p className="helper-text">{leftOut}</p> : null}
            {answer.candidates.length > 0 ? (
              <div className="data-table-wrap">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Choose</th>
                      <th>Machine</th>
                      <th>Kind</th>
                      <th>Key capability</th>
                      <th>Today's answer for the site</th>
                    </tr>
                  </thead>
                  <tbody>
                    {answer.candidates.map((item) => {
                      const blocked = item.answer && ["BLOCKED", "OVERRIDE_REQUIRED"].includes(item.answer.overall_code);
                      return (
                        <tr key={item.machine.asset_public_id}>
                          <td>
                            <input
                              type="radio"
                              name="machine"
                              aria-label={`Choose ${assetLabel(item.machine)}`}
                              checked={form.machine_public_id === item.machine.asset_public_id}
                              disabled={saving || !item.available || Boolean(blocked) || !item.answer || !mayChoose}
                              onChange={() => {
                                setFeedback(null);
                                setForm((current) => formAfterChoosing(current, item.machine.asset_public_id));
                              }}
                            />
                          </td>
                          <td>
                            <a href={hrefWithReturnTarget(`/equipment/machines/${item.machine.asset_public_id}`, finderHref(), "Back to allocating")}>
                              {assetLabel(item.machine)}
                            </a>
                            {item.machine.flag_codes.length > 0 ? <div className="helper-text">Data to check: {item.machine.flag_codes.join(", ")}</div> : null}
                          </td>
                          <td>{machineKindText(item.machine)}</td>
                          <td>{capabilityText(item.machine.key_capability)}</td>
                          <td>
                            {item.available ? null : <div className="text-warning">{item.conflicts.map(conflictText).join("; ")}</div>}
                            {item.answer ? (
                              <>
                                <StatusBadge code={item.answer.overall_code} label={answerLabel(item.answer.overall_code)} tone={answerTone(item.answer.overall_code)} />
                                {item.answer.overall_code !== "ELIGIBLE" ? (
                                  <ul className="compact-list">
                                    {resultsToShow(item.answer).map((result, index) => (
                                      <li key={index}>{answerResultText(result, item.machine.asset_public_id)}</li>
                                    ))}
                                  </ul>
                                ) : null}
                              </>
                            ) : item.available ? (
                              <span className="helper-text">Not judged: the site cannot be judged yet</span>
                            ) : null}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            ) : null}
          </SectionCard>
        ) : null}

        {answer && mayAllocate && closed ? <p className="text-warning">{WORK_ORDER_CLOSED_TEXT}</p> : null}
        {answer && mayAllocate && !closed ? (
          <SectionCard title={isReplacing ? "Replace with the machine chosen" : "Allocate the machine chosen"} tone="violet">
            {siteProblem ? <p className="text-danger">{siteProblem}</p> : null}
            {replaceProblem ? <p className="text-danger">{replaceProblem}</p> : null}
            <p>{chosen ? `${assetLabel(chosen.machine)}, ${machineKindText(chosen.machine)}` : "Choose a machine above."}</p>
            <div className="form-grid">
              {mayBill ? (
                <label className="field-stack">
                  Billing cycle
                  <select value={form.billing_cycle_code} disabled={saving} onChange={(event) => setForm({ ...form, billing_cycle_code: event.target.value })}>
                    {BILLING_CYCLE_OPTIONS.map((option) => (
                      <option key={option.code} value={option.code}>
                        {isReplacing && option.code === "" ? "Keep the replaced machine's" : option.label}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
              {isReplacing ? (
                <>
                  <label className="field-stack">
                    Why it is being replaced
                    <select value={form.reason_code} disabled={saving} onChange={(event) => setForm({ ...form, reason_code: event.target.value })}>
                      <option value="">Choose</option>
                      {REPLACEMENT_REASONS.map((reason) => (
                        <option key={reason.code} value={reason.code}>
                          {reason.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="field-stack">
                    Note
                    <input value={form.reason_note} maxLength={2000} disabled={saving} onChange={(event) => setForm({ ...form, reason_note: event.target.value })} />
                  </label>
                </>
              ) : (
                <label className="field-stack">
                  Note
                  <input value={form.notes} maxLength={2000} disabled={saving} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
                </label>
              )}
            </div>
            {chosen?.answer?.overall_code === "WARNING" ? (
              <label className="tick-row">
                <input
                  type="checkbox"
                  checked={form.accept_warnings}
                  disabled={saving}
                  onChange={(event) => setForm({ ...form, accept_warnings: event.target.checked })}
                />
                I have seen these warnings: {resultsToShow(chosen.answer).map((result) => answerResultText(result, chosen.machine.asset_public_id)).join("; ")}
              </label>
            ) : null}
            <div className="form-actions">
              <button type="button" onClick={() => void allocate()} disabled={saving || !chosen || !mayChoose}>
                {saving
                  ? "Saving..."
                  : chosen?.answer?.overall_code === "WARNING"
                    ? isReplacing
                      ? "Replace, with these warnings"
                      : "Allocate, with these warnings"
                    : isReplacing
                      ? "Replace the machine"
                      : "Allocate"}
              </button>
            </div>
            {feedback ? <p className={`action-feedback ${feedback.kind === "success" ? "text-success" : "text-danger"}`}>{feedback.text}</p> : null}
            <p className="helper-text">
              Held until the Work Order is released: nobody else can take the machine for these days. Answers are for{" "}
              {formatDay(answer.period_from)} onwards, at the site as recorded now.
            </p>
          </SectionCard>
        ) : null}
        {answer && !mayAllocate ? <p className="helper-text">Your role can see the machines. Operations and Admin allocate them.</p> : null}
      </div>
    </section>
  );
}
