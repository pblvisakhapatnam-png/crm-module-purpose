import { useEffect, useRef, useState } from "react";

import DateInput from "../../components/DateInput";
import { SectionCard } from "../../components/PageLayout";
import { createQueryController, initialQueryView, queryViewKeeping } from "../equipment/certificatesState";
import { getToken, readErrorDetail } from "../resource-requirements/pageSession";
import { formatTermDate } from "./workOrderBillingTermsState";
import {
  CALENDAR_CHOICE_OPTIONS,
  CALENDAR_UNCHANGED,
  HOLIDAY_KIND_OPTIONS,
  WORKING_DAY_RATE_OPTIONS,
  type CalendarDay,
  type ChangeNote,
  type HolidayForm,
  type HolidayList,
  type ResultingHolidays,
  addAddedRow,
  addWorkingRow,
  answerOptions,
  calendarChoice,
  calendarDayText,
  canChooseUnchanged,
  changeText,
  dayChargeText,
  dayWhatText,
  formFromHolidayList,
  groupTitle,
  holidayFormProblem,
  holidayListPayload,
  holidaysStatusText,
  linesText,
  notesForSavedVersion,
  periodText,
  removeAddedRow,
  removeWorkingRow,
  setCalendarChoice,
  setCalendarNote,
  showsChanges,
  typedWorkingRows,
  updateAddedRow,
  updateWorkingRow,
  yearsNotCompleteText,
} from "./workOrderHolidaysState";

// The Work Order's holidays (Slice 7D Part 4; since HOL-1, its changes to PBL's holiday calendar). Every Work Order
// follows PBL's calendar for each line's site state; this section records how this one changes it - a holiday added,
// or a calendar holiday made a working day at the normal or the overtime rate (Q4) - one list for every line
// (decision 27), and shows the holidays that apply to each state's lines over the contract.
//
// The backend re-checks every rule - each date against the contract above all - and writes every refusal message
// shown here; hiding the form from a read-only role is a convenience, not the control.

type Feedback = { kind: "success" | "error"; text: string } | null;

async function readSaveError(response: Response): Promise<string> {
  try {
    const body = (await response.clone().json()) as { detail?: unknown };
    if (Array.isArray(body.detail)) return "Check the holidays entered: one of them is not accepted.";
  } catch {
    // fall through
  }
  return readErrorDetail(response, `The holidays could not be saved. HTTP ${response.status}.`);
}

type Props = {
  workOrderPublicId: string;
  holidays: HolidayList | null;
  holidaysLoaded: boolean;
  holidaysError: string;
  canEdit: boolean;
  isClosed: boolean;
  token: string | null;
  // The page-load generation this section was rendered for. Every write hands it back, so a save that
  // finishes after a newer page load has started is discarded instead of applied over it.
  loadGeneration: number;
  onApplied: (holidays: HolidayList, loadGeneration: number) => void;
  // Changes whenever what the holidays that apply are worked out from changes on the page (resultingRefreshKey).
  resultingKey: string;
};

export default function WorkOrderHolidaysSection(props: Props) {
  const { holidays, canEdit, isClosed, holidaysLoaded, workOrderPublicId, resultingKey } = props;
  const editable = canEdit && !isClosed && holidaysLoaded;
  const [resulting, setResulting] = useState(initialQueryView<ResultingHolidays>());
  const [controller] = useState(() =>
    createQueryController<string, ResultingHolidays>({
      initialQuery: workOrderPublicId,
      getToken,
      failure: "Network error: the holidays that apply could not be loaded.",
      fetchAnswer: async (token, publicId) => {
        const response = await fetch(`/api/work-orders/${encodeURIComponent(publicId)}/holidays/resulting`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (!response.ok) throw new Error(await readErrorDetail(response, "The holidays that apply could not be loaded."));
        return (await response.json()) as ResultingHolidays;
      },
      // Read again for the same Work Order, the days stay on screen until the new answer arrives.
      show: (update) => setResulting((current) => queryViewKeeping(current, update, (answer) => answer.work_order_public_id === workOrderPublicId)),
    }),
  );

  useEffect(() => {
    void controller.setQuery(workOrderPublicId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [workOrderPublicId, resultingKey]);

  const shown = resulting.answer && resulting.answer.work_order_public_id === workOrderPublicId ? resulting.answer : null;

  return (
    <SectionCard title="Holidays: PBL's calendar and this Work Order's changes">
      <p>
        Every Work Order follows <a href="/holiday-calendar">PBL's holiday calendar</a> for each line's site state. Record here how this Work Order
        changes it: a holiday it adds, or a calendar holiday it works - at the normal or the overtime rate. Weekly off days are recorded with each
        line's billing terms. A holiday is charged as each line's "Work on an off day or holiday" term says.
      </p>
      {isClosed ? <p className="helper-text">This Work Order is closed, so its holidays can no longer be changed.</p> : null}
      {props.holidaysError ? <p className="text-danger">{props.holidaysError}</p> : null}
      {!holidaysLoaded && !props.holidaysError ? <p className="helper-text">Loading the holidays...</p> : null}

      {holidaysLoaded ? (
        <p>
          <span className={`status-badge ${holidays?.is_complete ? "status-badge--success" : "status-badge--warning"}`}>{holidaysStatusText(holidays)}</span>
        </p>
      ) : null}

      {holidaysLoaded ? (
        editable ? <HolidayListForm {...props} calendarDays={shown?.calendar_days ?? null} resulting={shown} /> : <ReadOnlyChanges holidays={holidays} />
      ) : null}

      <ResultingPanel resulting={shown} loading={resulting.loading} error={resulting.error} onRefresh={() => void controller.refresh()} />
    </SectionCard>
  );
}

function ReadOnlyChanges({ holidays }: { holidays: HolidayList | null }) {
  if (!holidays || holidays.holidays_answer_code == null) return <p>Not answered yet.</p>;
  if (holidays.holidays_answer_code === CALENDAR_UNCHANGED) return <p>The Work Order follows PBL's holiday calendar unchanged.</p>;
  if (holidays.changes.length === 0) return <p>The Work Order changes PBL's calendar, but no change is entered yet.</p>;
  return (
    <ul className="compact-list">
      {holidays.changes.map((change) => (
        <li key={change.change_public_id}>{changeText(change)}</li>
      ))}
    </ul>
  );
}

function HolidayListForm({
  workOrderPublicId,
  holidays,
  token,
  loadGeneration,
  onApplied,
  calendarDays,
  resulting,
}: Props & { calendarDays: CalendarDay[] | null; resulting: ResultingHolidays | null }) {
  const [form, setForm] = useState<HolidayForm>(() => formFromHolidayList(holidays));
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  // The version the last save made, so its notes can be shown beside "Holidays saved." once worked out.
  const [savedVersion, setSavedVersion] = useState<number | null>(null);
  const nextRowKey = useRef(0);
  const newKey = () => {
    nextRowKey.current += 1;
    return `new-${nextRowKey.current}`;
  };

  // A newer version from the server - this save's own, or another page load's - replaces the form.
  useEffect(() => {
    setForm(formFromHolidayList(holidays));
  }, [holidays?.list_version, holidays?.work_order_public_id]);

  function change(next: HolidayForm) {
    // The user's own edit clears a stale message; the post-save reset above does not, so the
    // confirmation survives it (the Slice 9D lesson, carried forward).
    setFeedback(null);
    setSavedVersion(null);
    setForm(next);
  }

  async function save() {
    const problem = holidayFormProblem(form);
    if (problem) {
      setFeedback({ kind: "error", text: problem });
      return;
    }
    if (!token) {
      setFeedback({ kind: "error", text: "Your session has ended. Sign in again, then save the holidays." });
      return;
    }
    setSaving(true);
    setFeedback(null);
    setSavedVersion(null);
    try {
      const response = await fetch(`/api/work-orders/${encodeURIComponent(workOrderPublicId)}/holidays`, {
        method: "PUT",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(holidayListPayload(form, holidays?.list_version ?? null)),
      });
      if (response.status === 409) {
        setFeedback({ kind: "error", text: "These holidays have changed since the page loaded. Reload to see the latest version." });
        return;
      }
      if (!response.ok) {
        setFeedback({ kind: "error", text: await readSaveError(response) });
        return;
      }
      const body = (await response.json()) as { holiday_list: HolidayList; event: unknown };
      onApplied(body.holiday_list, loadGeneration);
      setSavedVersion(body.holiday_list.list_version);
      setFeedback({ kind: "success", text: body.event ? "Holidays saved." : "Nothing changed, so nothing was saved." });
    } catch {
      setFeedback({ kind: "error", text: "Network error while saving the holidays. Try again." });
    } finally {
      setSaving(false);
    }
  }

  const unchangedAllowed = canChooseUnchanged(form);
  const typed = typedWorkingRows(form, calendarDays ?? []);

  return (
    <div className="section-form">
      <label className="field-stack">
        This Work Order and PBL's calendar
        <select value={form.answer} onChange={(event) => change({ ...form, answer: event.target.value })}>
          {answerOptions(holidays).map((option) => (
            <option key={option.code} value={option.code} disabled={option.code === CALENDAR_UNCHANGED && !unchangedAllowed}>
              {option.label}
            </option>
          ))}
        </select>
        {!unchangedAllowed ? <span className="helper-text">To record that it follows PBL's calendar unchanged, remove the changes listed first.</span> : null}
      </label>

      {showsChanges(form) ? (
        <>
          <h4>PBL's calendar holidays inside the contract</h4>
          {calendarDays === null ? (
            <p className="helper-text">Loading PBL's calendar...</p>
          ) : resulting?.period_from == null ? (
            <p className="helper-text">Record the contract start to see PBL's calendar holidays here.</p>
          ) : calendarDays.length === 0 ? (
            <p className="helper-text">PBL's calendar has no holiday inside the contract for this Work Order's sites yet.</p>
          ) : (
            <div className="data-table-wrap">
              <table className="data-table data-table-wide">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Holiday</th>
                    <th>For</th>
                    <th>This Work Order</th>
                    <th>Note (optional)</th>
                  </tr>
                </thead>
                <tbody>
                  {calendarDays.map((day) => {
                    const choice = calendarChoice(form, day.holiday_date);
                    return (
                      <tr key={day.holiday_date}>
                        <td>{formatTermDate(day.holiday_date)}</td>
                        <td>{calendarDayText(day)}</td>
                        <td>{linesText(day.line_numbers)}</td>
                        <td>
                          <select
                            aria-label={`This Work Order on ${formatTermDate(day.holiday_date)}`}
                            value={choice.rate}
                            onChange={(event) => change(setCalendarChoice(form, day.holiday_date, event.target.value, newKey()))}
                          >
                            {CALENDAR_CHOICE_OPTIONS.map((option) => (
                              <option key={option.code} value={option.code}>
                                {option.label}
                              </option>
                            ))}
                          </select>
                        </td>
                        <td>
                          <input
                            aria-label={`Note for ${formatTermDate(day.holiday_date)}`}
                            maxLength={255}
                            value={choice.note}
                            disabled={choice.rate === ""}
                            onChange={(event) => change(setCalendarNote(form, day.holiday_date, event.target.value))}
                          />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          <h4>Working days on dates not in PBL's calendar yet</h4>
          <p className="helper-text">For a year whose calendar is not set up yet. When PBL's calendar has the day, it applies with no change here.</p>
          {typed.map((row) => (
            <div key={row.key} className="page-actions actions-with-fields">
              <label className="field-stack">
                Date
                <DateInput value={row.holiday_date} onChange={(event) => change(updateWorkingRow(form, row.key, { holiday_date: event.target.value }))} />
              </label>
              <label className="field-stack">
                Charged
                <select value={row.rate} onChange={(event) => change(updateWorkingRow(form, row.key, { rate: event.target.value }))}>
                  <option value="">Not chosen</option>
                  {WORKING_DAY_RATE_OPTIONS.map((option) => (
                    <option key={option.code} value={option.code}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-stack">
                Note (optional)
                <input maxLength={255} value={row.note} onChange={(event) => change(updateWorkingRow(form, row.key, { note: event.target.value }))} />
              </label>
              <button type="button" onClick={() => change(removeWorkingRow(form, row.key))}>
                Remove
              </button>
            </div>
          ))}
          <div className="page-actions">
            <button type="button" onClick={() => change(addWorkingRow(form, newKey()))}>
              Add a working day
            </button>
          </div>

          <h4>Holidays this Work Order adds</h4>
          {form.added.map((row) => (
            <div key={row.key} className="page-actions actions-with-fields">
              <label className="field-stack">
                Date
                <DateInput value={row.holiday_date} onChange={(event) => change(updateAddedRow(form, row.key, { holiday_date: event.target.value }))} />
              </label>
              <label className="field-stack">
                Kind
                <select value={row.holiday_kind_code} onChange={(event) => change(updateAddedRow(form, row.key, { holiday_kind_code: event.target.value }))}>
                  <option value="">Not chosen</option>
                  {HOLIDAY_KIND_OPTIONS.map((option) => (
                    <option key={option.code} value={option.code}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field-stack">
                Description (optional)
                <input maxLength={255} value={row.description} onChange={(event) => change(updateAddedRow(form, row.key, { description: event.target.value }))} />
              </label>
              <button type="button" onClick={() => change(removeAddedRow(form, row.key))}>
                Remove
              </button>
            </div>
          ))}
          <div className="page-actions">
            <button type="button" onClick={() => change(addAddedRow(form, newKey()))}>
              Add a holiday
            </button>
          </div>
        </>
      ) : null}

      <div className="form-actions">
        <button type="button" disabled={saving} onClick={() => void save()}>
          {saving ? "Saving..." : "Save holidays"}
        </button>
        {feedback ? (
          <p className={`action-feedback ${feedback.kind === "success" ? "text-success" : "text-danger"}`} role={feedback.kind === "error" ? "alert" : "status"}>
            {feedback.text}
          </p>
        ) : null}
      </div>
      {feedback?.kind === "success" ? <ChangeNotes notes={notesForSavedVersion(resulting, savedVersion)} /> : null}
    </div>
  );
}

/** What the platform notes about the Work Order's changes - a working day that does nothing, for one - each with its date. */
function ChangeNotes({ notes }: { notes: ChangeNote[] }) {
  return (
    <>
      {notes.map((note) => (
        <p key={`${note.holiday_date}-${note.note_code}`} className="text-warning">
          {formatTermDate(note.holiday_date)}: {note.message}
        </p>
      ))}
    </>
  );
}

function ResultingPanel({
  resulting,
  loading,
  error,
  onRefresh,
}: {
  resulting: ResultingHolidays | null;
  loading: boolean;
  error: string;
  onRefresh: () => void;
}) {
  const yearsNote = resulting ? yearsNotCompleteText(resulting.years_not_complete) : null;
  return (
    <details className="secondary-disclosure" open>
      <summary>Holidays that apply</summary>
      <div className="page-actions">
        <button type="button" disabled={loading} onClick={onRefresh}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>
      {error ? <p className="text-danger">{error}</p> : null}
      {!resulting && loading ? <p className="helper-text">Loading the holidays that apply...</p> : null}
      {resulting ? (
        <>
          <p className="helper-text">{periodText(resulting)}</p>
          {yearsNote ? (
            <p className="text-warning">
              {yearsNote} <a href="/holiday-calendar">Holiday Calendar</a>
            </p>
          ) : null}
          <ChangeNotes notes={resulting.change_notes} />
          {resulting.groups.map((group) => (
            <div key={group.line_numbers.join("-")}>
              <h4>{groupTitle(group)}</h4>
              {group.problem_message ? <p className="text-warning">{group.problem_message}</p> : null}
              {group.days.length > 0 ? (
                <div className="data-table-wrap">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Date</th>
                        <th>What</th>
                        <th>Charged</th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.days.map((day) => (
                        <tr key={day.holiday_date}>
                          <td>{formatTermDate(day.holiday_date)}</td>
                          <td>
                            {dayWhatText(day)}
                            {day.note ? <div className="helper-text">{day.note}</div> : null}
                          </td>
                          <td className={day.lines_without_overtime_rate.length > 0 ? "text-warning" : undefined}>{dayChargeText(day)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : resulting.period_from ? (
                <p className="helper-text">No holiday inside the contract.</p>
              ) : null}
            </div>
          ))}
        </>
      ) : null}
    </details>
  );
}
