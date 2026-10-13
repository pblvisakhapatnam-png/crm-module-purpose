import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

import DateInput from "../../components/DateInput";
import { PageHeader, SectionCard, StatusBadge } from "../../components/PageLayout";
import { createQueryController, formatDay, initialQueryView, queryViewKeeping, type QueryView } from "../equipment/certificatesState";
import {
  formatDateTime,
  getToken,
  hrefWithReturnTarget,
  readRoleCodes,
  readSafeReturnTarget,
  SESSION_CHANGED_EVENT,
  type ReturnTarget,
} from "../resource-requirements/pageSession";
import { createLatestOnly } from "../resource-requirements/resourceRequirementState";
import { SIGN_IN_AGAIN } from "../../components/signInMessages";
import { fetchAssignment, fetchKitOptions, newRequestKey, sendAction } from "./allocationRequests";
import {
  type Answer,
  type Assignment,
  type KitOptions,
  BILLING_CYCLE_OPTIONS,
  RELEASE_REASONS,
  STATUS_HELD,
  answerLabel,
  answerResultText,
  answerTone,
  assetLabel,
  assignmentDaysText,
  billingCycleLabel,
  canAllocate,
  canSetBillingCycle,
  complianceLabel,
  complianceTone,
  conflictText,
  daysText,
  endReasonLabel,
  kitPiecesToSend,
  kitProblem,
  machineKindText,
  pieceText,
  requirementText,
  resultsToShow,
  siteText,
  statusLabel,
  statusTone,
  warningLabel,
  WORK_ORDER_CLOSED_TEXT,
  kitFeedbackKey,
  kitPieceSelectable,
  draftAfterRefresh,
  loadDraftsAfterRefresh,
  loadFeedbackKey,
  reconcileChoices,
  datesProblem,
  hasStarted,
  releaseProblem,
  todayIso,
  tripDayAfterRefresh,
  tripDayProblem,
  removeFeedbackKey,
  workOrderClosed,
} from "./allocationState";

// One allocation (design sections 6.4 to 6.10): what it holds, for which unit, the stored and today's answers,
// its history, its billing cycle, the kit going to site trip by trip, and - for Operations and Admin while it is
// held - checking again, changing dates, replacing and freeing. Each action's message sits beside its button.
// After every write the page reads the allocation again, through its own controller, so it never shows an older
// answer over a newer one.

type Feedback = { kind: "success" | "error"; text: string } | null;

/** An action's message, placed by the caller beside the control that sent it. */
function ActionMessage({ value }: { value: Feedback | undefined }) {
  return value ? <p className={`action-feedback ${value.kind === "success" ? "text-success" : "text-danger"}`}>{value.text}</p> : null;
}
type ActionName = "check" | "billing" | "dates" | "free" | "trip" | "load" | "kit" | "remove";

type Picker = { trip: number; options: KitOptions | null; error: string; chosen: Record<string, string>; accept: boolean; key: string };

function AnswerBlock({ title, answer, assetPublicId }: { title: string; answer: Answer | null; assetPublicId: string }) {
  if (!answer) return null;
  return (
    <div>
      <p>
        <strong>{title}</strong> ({formatDay(answer.evaluated_on)}, {answer.site_state_label}
        {answer.central_government_site ? ", central-government site" : ""}):{" "}
        <StatusBadge code={answer.overall_code} label={answerLabel(answer.overall_code)} tone={answerTone(answer.overall_code)} />
      </p>
      <ul className="compact-list">
        {resultsToShow(answer).map((result, index) => (
          <li key={index}>{answerResultText(result, assetPublicId)}</li>
        ))}
      </ul>
    </div>
  );
}

export default function AllocationPage() {
  const params = useParams();
  const assignmentId = typeof params?.assignmentId === "string" ? params.assignmentId : "";
  const [view, setView] = useState<QueryView<Assignment>>(initialQueryView<Assignment>());
  const [roles, setRoles] = useState<string[]>([]);
  const [returnTarget, setReturnTarget] = useState<ReturnTarget>({ href: "/resource-assignments", label: "Back to allocations" });
  const [busy, setBusy] = useState<ActionName | null>(null);
  // Keyed by the action, or for kit and loads by their trip or line (kitFeedbackKey, removeFeedbackKey, loadFeedbackKey).
  const [feedback, setFeedback] = useState<Record<string, Feedback>>({});
  const [cycle, setCycle] = useState("");
  const [dates, setDates] = useState({ from: "", to: "", accept: false });
  const [freeForm, setFreeForm] = useState({ last_day: "", reason_code: "", note: "", confirming: false });
  const [tripForm, setTripForm] = useState({ goes_on: "", note: "" });
  // What each Trip (Own Load) carries, by trip number.
  const [loads, setLoads] = useState<Record<number, string>>({});
  // The kit picker, for one trip; its options say the allocation version they answer for (8A-FB2-003).
  const [picker, setPicker] = useState<Picker | null>(null);
  // Counted up on every session change: a request answering for an earlier session changes nothing (8A-FB2-002).
  const session = useRef(0);
  const pickerTickets = useRef(createLatestOnly());
  // The allocation as last read, to tell which drafts a fresh copy changes.
  const recorded = useRef<Assignment | null>(null);
  const controller = useRef(
    createQueryController<string, Assignment>({
      initialQuery: assignmentId,
      getToken,
      fetchAnswer: fetchAssignment,
      show: (update) => {
        // Read again after a save, the allocation already shown stays on the page until the fresh copy arrives, so
        // the page does not empty and jump back to the top (owner's screen check, 29 September 2026).
        setView((current) => queryViewKeeping(current, update, (shown) => shown.assignment_public_id === controller.current.query()));
        if (update.kind === "answer") {
          // A fresh copy replaces the drafts whose recorded value it changes; what the user is typing meanwhile in
          // the others stays (draftAfterRefresh).
          const answer = update.answer;
          const before = recorded.current?.assignment_public_id === answer.assignment_public_id ? recorded.current : null;
          recorded.current = answer;
          setCycle((draft) => draftAfterRefresh(draft, before ? (before.billing_cycle_code ?? "") : undefined, answer.billing_cycle_code ?? ""));
          setDates((draft) => {
            const now = { from: answer.planned_from, to: answer.planned_to ?? "" };
            const was = before ? { from: before.planned_from, to: before.planned_to ?? "" } : undefined;
            return draftAfterRefresh({ from: draft.from, to: draft.to }, was, now) === now ? { ...now, accept: false } : draft;
          });
          setLoads((drafts) => loadDraftsAfterRefresh(drafts, before?.trips, answer.trips));
          // Another Trip (Own Load) starts on the allocation's first day - a crane often goes in several loads at
          // once - and follows it when it moves, unless the user chose another day (8A-FB2-004).
          setTripForm((current) => ({ ...current, goes_on: tripDayAfterRefresh(current.goes_on, before?.planned_from, answer.planned_from) }));
        }
      },
      failure: "The allocation could not be loaded.",
    }),
  );

  useEffect(() => {
    setRoles(readRoleCodes());
    setReturnTarget(readSafeReturnTarget("/resource-assignments", "Back to allocations"));
    void controller.current.setQuery(assignmentId);
  }, [assignmentId]);

  useEffect(() => {
    // Signing out, or in as someone else (8A-FB-002): the roles are read again; the allocation, the picker, the
    // messages and any request in flight are dropped; and the allocation is read again under the new session -
    // with none, the page asks to sign in.
    const onSessionChanged = () => {
      session.current += 1;
      setRoles(readRoleCodes());
      pickerTickets.current.begin();
      setPicker(null);
      setBusy(null);
      setFeedback({});
      setCycle("");
      setDates({ from: "", to: "", accept: false });
      setFreeForm({ last_day: "", reason_code: "", note: "", confirming: false });
      setTripForm({ goes_on: "", note: "" });
      setLoads({});
      recorded.current = null;
      setView(initialQueryView<Assignment>());
      void controller.current.refresh();
    };
    window.addEventListener(SESSION_CHANGED_EVENT, onSessionChanged);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, onSessionChanged);
  }, []);

  const assignment = view.answer;
  // No action, and no typing, while one is sent or the allocation is read again: an action sends the version
  // shown, which a fresh copy is about to move on, and a fresh copy replaces a draft whose value it changes
  // (8A-FB-001).
  const waiting = busy !== null || view.loading;
  const held = assignment?.assignment_status_code === STATUS_HELD;
  // A closed Work Order's allocations are read only: the server refuses every write (8A-R2-001).
  const closed = assignment ? workOrderClosed(assignment.requirement) : false;
  const mayAct = canAllocate(roles) && held && !closed;
  const mayBill = canSetBillingCycle(roles) && held && !closed;

  function say(key: string, value: Feedback) {
    setFeedback((current) => ({ ...current, [key]: value }));
  }

  /** Send one action. `saved` when it was, so a form is cleared or closed only then; a refusal's status. An
   * answer that comes after the session changed changes nothing: the page belongs to the new session (8A-FB2-002). */
  async function act(
    action: ActionName,
    path: string,
    method: "POST" | "PUT",
    body: Record<string, unknown>,
    done: string,
    fallback: string,
    key: string = action,
  ): Promise<{ saved: boolean; status: number | null }> {
    if (!assignment) return { saved: false, status: null };
    const asked = assignment.assignment_public_id;
    const generation = session.current;
    setBusy(action);
    say(key, null);
    const sent = await sendAction(asked, path, method, { expected_assignment_version: assignment.assignment_version, ...body }, fallback);
    if (session.current !== generation) return { saved: false, status: null };
    if (!sent.ok) {
      say(key, { kind: "error", text: sent.message });
      // Refused as out of date (409): the allocation is read again at once, controls waiting, so the next action
      // sends the version now recorded (8A-FB-006).
      if (sent.status === 409) void controller.current.refreshIf(asked);
      setBusy(null);
      return { saved: false, status: sent.status };
    }
    say(key, { kind: "success", text: sent.body.events.length === 0 ? "Nothing changed, so nothing was recorded." : done });
    // The response carries the allocation as it now stands: it is shown at once, unless the page has moved on to
    // another allocation - no second read that could fail and take the result off the screen (8A-FB-007).
    if (controller.current.isCurrent(asked)) controller.current.answered(sent.body.assignment);
    setBusy(null);
    return { saved: true, status: null };
  }

  /** Open the kit picker for a trip, or - `keep` - read its options again, keeping the choices still possible
   * (8A-FB-003, 8A-FB2-003). Only the latest request's answer is taken, and none after the session changed. */
  async function loadPicker(trip: number, keep: boolean) {
    if (!assignment) return;
    const forAssignment = assignment;
    const generation = session.current;
    const ticket = pickerTickets.current.begin();
    setPicker((current) => {
      const kept = keep && current?.trip === trip ? current : null;
      return { trip, options: null, error: "", chosen: kept ? kept.chosen : {}, accept: kept ? kept.accept : false, key: kept ? kept.key : newRequestKey() };
    });
    const current = () => pickerTickets.current.isLatest(ticket) && session.current === generation;
    const same = (open: Picker | null): open is Picker => open !== null && open.trip === trip;
    const token = getToken();
    if (!token) {
      setPicker((open) => (same(open) ? { ...open, error: SIGN_IN_AGAIN } : open));
      return;
    }
    try {
      const options = await fetchKitOptions(token, forAssignment.assignment_public_id, trip);
      if (!current()) return;
      setPicker((open) => (same(open) ? { ...open, options, chosen: reconcileChoices(open.chosen, options.pieces) } : open));
      // The server answered for a newer allocation than the page shows: the page reads it, so the two agree.
      if (options.assignment_version > forAssignment.assignment_version) void controller.current.refreshIf(forAssignment.assignment_public_id);
    } catch (error) {
      if (current()) setPicker((open) => (same(open) ? { ...open, error: error instanceof Error ? error.message : "The kit could not be loaded." } : open));
    }
  }

  useEffect(() => {
    // The allocation changed with a picker open - its dates, another trip, another piece listed: options for another
    // version are not shown (see `shownOptions`) and are read again, keeping the choices still possible.
    if (!assignment || !picker) return;
    if (!mayAct || assignment.assignment_public_id !== controller.current.query()) {
      pickerTickets.current.begin();
      setPicker(null);
      return;
    }
    if (picker.options?.assignment_version === assignment.assignment_version) return;
    void loadPicker(picker.trip, true);
  }, [assignment?.assignment_public_id, assignment?.assignment_version]);

  // The picker's options, only when they answer for the allocation as shown: never one version's kit under
  // another's controls (8A-FB2-003).
  const shownOptions = picker?.options && assignment && picker.options.assignment_version === assignment.assignment_version ? picker.options : null;

  async function listKit() {
    if (!picker || !shownOptions) return;
    const problem = kitProblem(picker.chosen, shownOptions.pieces, picker.accept);
    if (problem) {
      say(kitFeedbackKey(picker.trip), { kind: "error", text: problem });
      return;
    }
    const trip = picker.trip;
    const result = await act(
      "kit",
      "kit",
      "POST",
      { create_request_key: picker.key, trip_number: trip, pieces: kitPiecesToSend(picker.chosen, shownOptions.pieces), accept_warnings: picker.accept },
      "Listed.",
      "The kit could not be listed.",
      kitFeedbackKey(trip),
    );
    // A refusal keeps the picker open with the choices, so they can be corrected; refused as taken or out of date
    // (409), the options are read again, so the picker shows what is free now.
    if (result.saved) setPicker(null);
    else if (result.status === 409) void loadPicker(trip, true);
  }

  const machineId = assignment?.machine?.asset_public_id ?? "";
  const pageHref = assignment ? `/resource-assignments/${assignment.assignment_public_id}` : "";
  const replaceHref = assignment
    ? hrefWithReturnTarget(
        `/resource-assignments/new?requirement=${assignment.requirement.requirement_public_id}&unit=${assignment.unit_number}&replacing=${assignment.assignment_public_id}`,
        pageHref,
        "Back to the allocation",
      )
    : "";

  return (
    <section>
      <PageHeader
        eyebrow="Allocation"
        back={returnTarget}
        title={assignment ? `${assignment.assignment_reference} - ${assetLabel(assignment.machine)}` : "Allocation"}
        badges={
          assignment ? (
            <>
              <StatusBadge code={assignment.assignment_status_code} label={statusLabel(assignment.assignment_status_code)} tone={statusTone(assignment.assignment_status_code)} />
              {held ? <StatusBadge code={assignment.compliance_state_code} label={complianceLabel(assignment.compliance_state_code)} tone={complianceTone(assignment.compliance_state_code)} /> : null}
            </>
          ) : null
        }
        subtitle="One machine on one unit of a requirement. Before the Work Order is released it holds the machine for the job."
        actions={
          <button type="button" disabled={waiting} onClick={() => void controller.current.refresh()}>
            Refresh
          </button>
        }
      >
        {view.error ? <p className="text-danger">{view.error}</p> : null}
        {view.loading && !view.answer ? <p className="helper-text">Loading the allocation...</p> : null}
      </PageHeader>

      {assignment ? (
        <div className="page-sections">
          {assignment.warnings.length > 0 ? (
            <SectionCard title="Needs attention" tone="amber">
              <ul className="compact-list">
                {assignment.warnings.map((warning) => (
                  <li key={warning}>{warningLabel(warning)}</li>
                ))}
              </ul>
            </SectionCard>
          ) : null}

          <SectionCard title="What it is for" tone="blue">
            <dl className="facts-list">
              <dt>Work Order</dt>
              <dd>
                <a href={hrefWithReturnTarget(`/work-orders/${assignment.work_order_public_id}`, pageHref, "Back to the allocation")}>{assignment.work_order_code}</a>, line{" "}
                {assignment.work_order_line_number}
              </dd>
              <dt>Requirement</dt>
              <dd>
                <a href={hrefWithReturnTarget(`/resource-requirements/${assignment.requirement.requirement_public_id}`, pageHref, "Back to the allocation")}>
                  {assignment.requirement.requirement_reference}
                </a>
                , unit {assignment.unit_number} of {assignment.requirement.units_required}: {requirementText(assignment.requirement)}
              </dd>
              <dt>Machine</dt>
              <dd>
                <a href={hrefWithReturnTarget(`/equipment/machines/${machineId}`, pageHref, "Back to the allocation")}>{assetLabel(assignment.machine)}</a>, {machineKindText(assignment.machine)}
                {assignment.allocated_machine_number && assignment.allocated_machine_number !== assignment.machine?.machine_number
                  ? ` (registration when allocated: ${assignment.allocated_machine_number})`
                  : ""}
              </dd>
              <dt>Site</dt>
              <dd>{siteText(assignment.site)}</dd>
              <dt>Days</dt>
              <dd>{assignmentDaysText(assignment)}</dd>
              <dt>Billing cycle</dt>
              <dd>
                {billingCycleLabel(assignment.billing_cycle_code)}
                {assignment.billing_cycle_set_by_display_name ? ` (set by ${assignment.billing_cycle_set_by_display_name}, ${formatDateTime(assignment.billing_cycle_set_at)})` : ""}
              </dd>
              <dt>Note</dt>
              <dd>{assignment.notes || "-"}</dd>
              <dt>Recorded</dt>
              <dd>
                {formatDateTime(assignment.created_at)}
                {assignment.created_by_display_name ? ` by ${assignment.created_by_display_name}` : ""}
              </dd>
            </dl>
          </SectionCard>

          <SectionCard title="History" tone="slate">
            <dl className="facts-list">
              <dt>Replaces</dt>
              <dd>
                {assignment.replaces ? (
                  <a href={`/resource-assignments/${assignment.replaces.assignment_public_id}`}>
                    {assignment.replaces.assignment_reference}: {assignment.replaces.asset_reference}, {daysText(assignment.replaces.planned_from, assignment.replaces.effective_to)}
                  </a>
                ) : (
                  "-"
                )}
              </dd>
              <dt>Replaced by</dt>
              <dd>
                {assignment.replaced_by ? (
                  <a href={`/resource-assignments/${assignment.replaced_by.assignment_public_id}`}>
                    {assignment.replaced_by.assignment_reference}: {assignment.replaced_by.asset_reference}, from {formatDay(assignment.replaced_by.planned_from)}
                  </a>
                ) : (
                  "-"
                )}
              </dd>
              {assignment.ended_at ? (
                <>
                  <dt>Ended</dt>
                  <dd>
                    {endReasonLabel(assignment.end_reason_code)}
                    {assignment.end_note ? `: ${assignment.end_note}` : ""} - {formatDateTime(assignment.ended_at)}
                    {assignment.ended_by_display_name ? ` by ${assignment.ended_by_display_name}` : ""}
                  </dd>
                </>
              ) : null}
            </dl>
          </SectionCard>

          <SectionCard title="Eligibility" tone="teal">
            <AnswerBlock title="Stored answer" answer={assignment.decision} assetPublicId={machineId} />
            {held ? (
              assignment.today ? (
                <AnswerBlock title="Today's answer" answer={assignment.today} assetPublicId={machineId} />
              ) : (
                <p className="helper-text">{complianceLabel(assignment.compliance_state_code)}</p>
              )
            ) : null}
            {mayAct ? (
              <div className="form-actions">
                <button type="button" disabled={waiting} onClick={() => void act("check", "check", "POST", {}, "Checked again: the answer is stored.", "It could not be checked again.")}>
                  {busy === "check" ? "Checking..." : "Check again"}
                </button>
              </div>
            ) : null}
            <ActionMessage value={feedback.check} />
          </SectionCard>

          {mayBill ? (
            <SectionCard title="Billing cycle" tone="violet">
              <div className="form-grid">
                <label className="field-stack">
                  How often this machine is invoiced
                  <select value={cycle} disabled={waiting} onChange={(event) => setCycle(event.target.value)}>
                    {BILLING_CYCLE_OPTIONS.map((option) => (
                      <option key={option.code} value={option.code}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="form-actions">
                  <button
                    type="button"
                    disabled={waiting}
                    onClick={() => void act("billing", "billing-cycle", "PUT", { billing_cycle_code: cycle || null }, "Billing cycle saved.", "The billing cycle could not be saved.")}
                  >
                    {busy === "billing" ? "Saving..." : "Save the billing cycle"}
                  </button>
                </div>
              </div>
              <ActionMessage value={feedback.billing} />
            </SectionCard>
          ) : null}

          <SectionCard title="Trips (Own Load) to site" tone="teal">
            <p className="helper-text">
              A crane may go in several loads: each Trip (Own Load) says which part of the machine it carries, and lists
              its kit.
            </p>
            {assignment.trips.map((trip) => (
              <div key={trip.trip_public_id} className="divided-item">
                <p>
                  <strong>Trip (Own Load) {trip.trip_number}</strong>, on {formatDay(trip.goes_on)}
                </p>
                {mayAct ? (
                  <div className="form-grid">
                    <label className="field-stack">
                      What this load carries
                      <input
                        value={loads[trip.trip_number] ?? ""}
                        maxLength={500}
                        placeholder="e.g. Base & carbody"
                        disabled={waiting}
                        onChange={(event) => {
                          setLoads({ ...loads, [trip.trip_number]: event.target.value });
                          say(loadFeedbackKey(trip.trip_number), null);
                        }}
                      />
                    </label>
                    <div className="form-actions">
                      <button
                        type="button"
                        disabled={waiting}
                        onClick={() =>
                          void act(
                            "load",
                            `trips/${trip.trip_number}/note`,
                            "PUT",
                            { note: (loads[trip.trip_number] ?? "").trim() || null },
                            "Saved.",
                            "What this load carries could not be saved.",
                            loadFeedbackKey(trip.trip_number),
                          )
                        }
                      >
                        {busy === "load" ? "Saving..." : "Save"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <p>{trip.note ? `Carries: ${trip.note}` : "What this load carries is not recorded."}</p>
                )}
                <ActionMessage value={feedback[loadFeedbackKey(trip.trip_number)]} />
                {trip.kit.length === 0 ? <p className="helper-text">No kit listed on this Trip (Own Load).</p> : null}
                {trip.kit.length > 0 ? (
                  <div className="data-table-wrap">
                    <table className="data-table">
                      <thead>
                        <tr>
                          <th>Piece</th>
                          <th>How many</th>
                          <th>Answer</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {trip.kit.map((line) => (
                          <tr key={line.kit_line_public_id}>
                            <td>{line.piece ? pieceText(line.piece) : line.piece_public_id}</td>
                            <td>{line.quantity}</td>
                            <td>
                              {(line.today ?? line.decision) ? (
                                <StatusBadge
                                  code={(line.today ?? line.decision)!.overall_code}
                                  label={answerLabel((line.today ?? line.decision)!.overall_code)}
                                  tone={answerTone((line.today ?? line.decision)!.overall_code)}
                                />
                              ) : (
                                "-"
                              )}
                            </td>
                            <td className="cell-actions">
                              {line.line_status_code === "REMOVED" ? (
                                `Removed ${formatDateTime(line.removed_at)}`
                              ) : mayAct ? (
                                <button
                                  type="button"
                                  disabled={waiting}
                                  onClick={() =>
                                    void act(
                                      "remove",
                                      `kit/${encodeURIComponent(line.kit_line_public_id)}/remove`,
                                      "POST",
                                      {},
                                      "Taken off the list.",
                                      "The piece could not be taken off.",
                                      removeFeedbackKey(line.kit_line_public_id),
                                    )
                                  }
                                >
                                  Remove
                                </button>
                              ) : (
                                "Listed"
                              )}
                              <ActionMessage value={feedback[removeFeedbackKey(line.kit_line_public_id)]} />
                              {!line.fits_machine && line.line_status_code !== "REMOVED" ? <div className="text-warning">No longer fits the machine's model</div> : null}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : null}
                {mayAct ? (
                  <div className="form-actions">
                    <button type="button" disabled={waiting} onClick={() => void loadPicker(trip.trip_number, false)}>
                      Add pieces to Trip (Own Load) {trip.trip_number}
                    </button>
                  </div>
                ) : null}
                {picker && picker.trip === trip.trip_number ? (
                  <div className="section-form">
                    {picker.error ? <p className="text-danger">{picker.error}</p> : null}
                    {assignment.site.problem_message ? <p className="text-danger">{assignment.site.problem_message}</p> : null}
                    {!shownOptions && !picker.error ? <p className="helper-text">Loading the kit held for this machine's model...</p> : null}
                    {shownOptions && !shownOptions.machine_has_model ? <p className="helper-text">Map this machine's model to see its kit.</p> : null}
                    {shownOptions && shownOptions.machine_has_model && shownOptions.pieces.length === 0 ? (
                      <p className="helper-text">No kit is held for this machine's model.</p>
                    ) : null}
                    {shownOptions && shownOptions.pieces.length > 0 ? (
                      <div className="data-table-wrap">
                        <table className="data-table">
                          <thead>
                            <tr>
                              <th>Take</th>
                              <th>Piece</th>
                              <th>Free over {daysText(shownOptions.window_from, shownOptions.window_to)}</th>
                              <th>Answer</th>
                            </tr>
                          </thead>
                          <tbody>
                            {shownOptions.pieces.map((option) => {
                              const id = option.piece.asset_public_id;
                              const value = picker.chosen[id] ?? "";
                              const setValue = (next: string) => setPicker({ ...picker, chosen: { ...picker.chosen, [id]: next } });
                              return (
                                <tr key={id}>
                                  <td>
                                    {option.piece.tracking_code === "COUNTED" ? (
                                      <span className="count-field">
                                        <input
                                          aria-label={`How many of ${option.piece.asset_reference}`}
                                          inputMode="numeric"
                                          maxLength={3}
                                          placeholder="0"
                                          value={value}
                                          disabled={waiting || !kitPieceSelectable(option)}
                                          onChange={(event) => setValue(event.target.value)}
                                        />
                                        nos.
                                      </span>
                                    ) : (
                                      <input
                                        type="checkbox"
                                        aria-label={`Take ${option.piece.asset_reference}`}
                                        checked={value !== ""}
                                        disabled={waiting || !kitPieceSelectable(option)}
                                        onChange={(event) => setValue(event.target.checked ? "1" : "")}
                                      />
                                    )}
                                  </td>
                                  <td>{pieceText(option.piece)}</td>
                                  <td>
                                    {option.piece.tracking_code === "COUNTED" ? `${option.quantity_free} of ${option.piece.quantity}` : option.available ? "Free" : "Taken"}
                                    {option.conflicts.length > 0 ? <div className="helper-text">{option.conflicts.map(conflictText).join("; ")}</div> : null}
                                  </td>
                                  <td>
                                    {option.answer ? (
                                      <>
                                        <StatusBadge code={option.answer.overall_code} label={answerLabel(option.answer.overall_code)} tone={answerTone(option.answer.overall_code)} />
                                        {option.answer.overall_code !== "ELIGIBLE" ? (
                                          <ul className="compact-list">
                                            {resultsToShow(option.answer).map((result, index) => (
                                              <li key={index}>{answerResultText(result, id)}</li>
                                            ))}
                                          </ul>
                                        ) : null}
                                      </>
                                    ) : (
                                      "-"
                                    )}
                                  </td>
                                </tr>
                              );
                            })}
                          </tbody>
                        </table>
                      </div>
                    ) : null}
                    {shownOptions?.pieces.some((option) => option.answer?.overall_code === "WARNING" && (picker.chosen[option.piece.asset_public_id] ?? "") !== "") ? (
                      <label className="tick-row">
                        <input type="checkbox" checked={picker.accept} disabled={waiting} onChange={(event) => setPicker({ ...picker, accept: event.target.checked })} />
                        I have seen these warnings
                      </label>
                    ) : null}
                    <div className="form-actions">
                      <button type="button" disabled={waiting || !shownOptions} onClick={() => void listKit()}>
                        {busy === "kit" ? "Listing..." : "List these pieces"}
                      </button>
                      <button type="button" disabled={waiting} onClick={() => setPicker(null)}>
                        Close
                      </button>
                    </div>
                  </div>
                ) : null}
                <ActionMessage value={feedback[kitFeedbackKey(trip.trip_number)]} />
              </div>
            ))}
            {mayAct ? (
              <div className="form-grid">
                <label className="field-stack">
                  Another Trip (Own Load) goes on
                  <DateInput value={tripForm.goes_on} disabled={waiting} onChange={(event) => setTripForm({ ...tripForm, goes_on: event.target.value })} />
                </label>
                <label className="field-stack">
                  What this load carries
                  <input
                    value={tripForm.note}
                    maxLength={500}
                    placeholder="e.g. Crawlers, left and right"
                    disabled={waiting}
                    onChange={(event) => setTripForm({ ...tripForm, note: event.target.value })}
                  />
                </label>
                <div className="form-actions">
                  <button
                    type="button"
                    disabled={waiting || tripDayProblem(tripForm.goes_on, assignment.planned_from, assignment.planned_to) !== null}
                    onClick={() =>
                      void act(
                        "trip",
                        "trips",
                        "POST",
                        { goes_on: tripForm.goes_on, note: tripForm.note.trim() || null },
                        "Trip (Own Load) added.",
                        "The Trip (Own Load) could not be added.",
                      ).then((result) => result.saved && setTripForm((current) => ({ ...current, note: "" })))
                    }
                  >
                    {busy === "trip" ? "Adding..." : "Add a Trip (Own Load)"}
                  </button>
                </div>
                {tripForm.goes_on && tripDayProblem(tripForm.goes_on, assignment.planned_from, assignment.planned_to) ? (
                  <p className="text-warning">{tripDayProblem(tripForm.goes_on, assignment.planned_from, assignment.planned_to)}</p>
                ) : null}
              </div>
            ) : null}
            <ActionMessage value={feedback.trip} />
          </SectionCard>

          {mayAct ? (
            <SectionCard title="Change the dates" tone="violet">
              <div className="form-grid">
                <label className="field-stack">
                  From
                  <DateInput value={dates.from} disabled={waiting} onChange={(event) => setDates({ ...dates, from: event.target.value })} />
                </label>
                <label className="field-stack">
                  To
                  <DateInput value={dates.to} disabled={waiting} onChange={(event) => setDates({ ...dates, to: event.target.value })} />
                </label>
                <div className="form-actions">
                  <button
                    type="button"
                    disabled={waiting || !dates.from || datesProblem(dates.from, assignment, todayIso()) !== null}
                    onClick={() =>
                      void act("dates", "dates", "PUT", { planned_from: dates.from, planned_to: dates.to || null, accept_warnings: dates.accept }, "Dates changed, and checked again.", "The dates could not be changed.")
                    }
                  >
                    {busy === "dates" ? "Saving..." : "Save the dates"}
                  </button>
                </div>
                {dates.from && datesProblem(dates.from, assignment, todayIso()) ? (
                  <p className="text-warning">{datesProblem(dates.from, assignment, todayIso())}</p>
                ) : null}
              </div>
              <label className="tick-row">
                <input type="checkbox" checked={dates.accept} disabled={waiting} onChange={(event) => setDates({ ...dates, accept: event.target.checked })} />
                Allocate with any warnings the new dates bring
              </label>
              <ActionMessage value={feedback.dates} />
            </SectionCard>
          ) : null}

          {mayAct ? (
            <SectionCard title="Replace or free the machine" tone="slate">
              <p>
                {waiting ? (
                  <button type="button" disabled>
                    Replace the machine
                  </button>
                ) : (
                  <a className="button-link-secondary" href={replaceHref}>
                    Replace the machine
                  </a>
                )}{" "}
                <span className="helper-text">A breakdown, say: the new machine takes the unit from a day you choose, and both stay on the history.</span>
              </p>
              <div className="form-grid">
                <label className="field-stack">
                  {hasStarted(assignment.planned_from, todayIso())
                    ? "Last day on the job (needed: it has started; empty only if recorded by mistake)"
                    : "Last day on the job (empty: it never goes)"}
                  <DateInput
                    value={freeForm.last_day}
                    disabled={waiting}
                    onChange={(event) => setFreeForm({ ...freeForm, last_day: event.target.value, confirming: false })}
                  />
                </label>
                <label className="field-stack">
                  Why it is being freed
                  <select
                    value={freeForm.reason_code}
                    disabled={waiting}
                    onChange={(event) => setFreeForm({ ...freeForm, reason_code: event.target.value, confirming: false })}
                  >
                    <option value="">Choose</option>
                    {RELEASE_REASONS.map((reason) => (
                      <option key={reason.code} value={reason.code}>
                        {reason.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="field-stack">
                  Note
                  <input
                    value={freeForm.note}
                    maxLength={2000}
                    disabled={waiting}
                    onChange={(event) => setFreeForm({ ...freeForm, note: event.target.value, confirming: false })}
                  />
                </label>
                <div className="form-actions">
                  {freeForm.confirming ? (
                    <>
                      <button
                        type="button"
                        disabled={waiting}
                        onClick={() =>
                          void act(
                            "free",
                            "release",
                            "POST",
                            { last_day: freeForm.last_day || null, reason_code: freeForm.reason_code, note: freeForm.note.trim() || null },
                            "Freed. The allocation stays on the history.",
                            "The machine could not be freed.",
                          )
                        }
                      >
                        {busy === "free" ? "Freeing..." : "Yes, free it"}
                      </button>
                      <button type="button" disabled={waiting} onClick={() => setFreeForm({ ...freeForm, confirming: false })}>
                        Keep it
                      </button>
                    </>
                  ) : (
                    <button
                      type="button"
                      disabled={waiting}
                      onClick={() => {
                        // "Other" needs a note: refused here, beside the button, before asking to confirm (8A-FB-005).
                        const problem = releaseProblem(freeForm, assignment.planned_from, todayIso());
                        if (problem) say("free", { kind: "error", text: problem });
                        else {
                          say("free", null);
                          setFreeForm({ ...freeForm, confirming: true });
                        }
                      }}
                    >
                      Free the machine
                    </button>
                  )}
                </div>
              </div>
              <ActionMessage value={feedback.free} />
            </SectionCard>
          ) : null}

          {/* Once freed, the section with the button is gone: its message stays where the section was. */}
          {!mayAct && feedback.free?.kind === "success" ? <ActionMessage value={feedback.free} /> : null}

          {closed && held ? <p className="helper-text">{WORK_ORDER_CLOSED_TEXT}</p> : null}
          {!canAllocate(roles) && held && !closed ? <p className="helper-text">Your role can view this allocation. Operations and Admin change it.</p> : null}
        </div>
      ) : null}
    </section>
  );
}
