import { useEffect, useRef, useState } from "react";

import DateInput from "../../components/DateInput";
import { PageHeader, SectionCard, StatusBadge } from "../../components/PageLayout";
import { SIGN_IN_FIRST } from "../../components/signInMessages";
import { actInSession, announceAlertsChanged, createSessionGuard, readActionAnswer } from "../alerts/alertsState";
import { createQueryController, formatDay } from "../equipment/certificatesState";
import { FeedbackLine } from "../equipment/EquipmentParts";
import type { Feedback } from "../equipment/equipmentState";
import { SESSION_CHANGED_EVENT, clearSession, formatDateTime, getToken, readErrorDetail, readRoleCodes } from "../resource-requirements/pageSession";
import {
  ALL_INDIA,
  KIND_OPTIONS,
  NAME_MAX_LENGTH,
  STATES,
  type CalendarAnswer,
  type CalendarState,
  type CalendarYear,
  type CalendarYearAction,
  type CalendarYears,
  type HolidayRow,
  type YearForm,
  addRow,
  appliesText,
  calendarPageAfter,
  calendarPageSaved,
  formFromYear,
  initialCalendarPage,
  passedDaysWarning,
  pickerYears,
  removeRow,
  startYearProblem,
  toggleState,
  updateRow,
  yearFormChanged,
  yearFormProblem,
  yearFromSearch,
  yearPayload,
  yearStateText,
  yearToShow,
} from "./holidayCalendarState";

// PBL's holiday calendar (HOL-1, design section 6): one calendar for each year, kept by Admin and read by everyone.
// Every Work Order follows it for each line's site state, and its own terms change it - on the Work Order page. A year
// is complete once Admin marks it so; until then the Alerts keep reminding (Q2). Any year may be changed at any time,
// and every change is kept (Q3).

async function readJson<T>(response: Response, fallback: string): Promise<T> {
  if (response.status === 401) clearSession();
  if (!response.ok) throw new Error(await readErrorDetail(response, fallback));
  return (await response.json()) as T;
}

function canManageCalendar(roleCodes: readonly string[]): boolean {
  // HOLIDAY_CALENDAR_MANAGE: Admin until a position is mapped under ORA-001. A usability aid: the server decides.
  return roleCodes.includes("ADMIN");
}

export default function HolidayCalendarPage() {
  const [page, setPage] = useState(initialCalendarPage);
  const answer = page.view.answer;
  const { loading, error } = page.view;
  const [canManage, setCanManage] = useState(false);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<Feedback>(null);
  const [startText, setStartText] = useState("");
  const [startFeedback, setStartFeedback] = useState<Feedback>(null);
  const nextRowKey = useRef(0);
  const [session] = useState(() => createSessionGuard());
  const [nextRead] = useState(() => ({ keepShown: false }));

  const [controller] = useState(() =>
    createQueryController<number | null, CalendarAnswer>({
      initialQuery: yearFromSearch(typeof window === "undefined" ? "" : window.location.search),
      getToken,
      failure: "Network error: the holiday calendar could not be loaded.",
      fetchAnswer: async (token, asked) => {
        const headers = { Authorization: `Bearer ${token}` };
        const years = await readJson<CalendarYears>(await fetch("/api/holiday-calendar/years", { headers }), "The calendar's years could not be loaded.");
        const shown = yearToShow(asked, years.today);
        const [year, states] = await Promise.all([
          fetch(`/api/holiday-calendar/years/${shown}`, { headers }).then((response) => readJson<CalendarYear>(response, `The calendar for ${shown} could not be loaded.`)),
          fetch("/api/holiday-calendar/states", { headers }).then((response) => readJson<CalendarState[]>(response, "The states could not be loaded.")),
        ]);
        return { years, year, states };
      },
      show: (update) => {
        const keepShown = nextRead.keepShown;
        if (update.kind !== "loading") nextRead.keepShown = false;
        setPage((current) => calendarPageAfter(current, update, keepShown));
      },
    }),
  );

  function load(keepShown: boolean) {
    nextRead.keepShown = keepShown;
    setCanManage(canManageCalendar(readRoleCodes()));
    void controller.refresh();
  }

  useEffect(() => {
    load(false);
    const refresh = () => {
      session.changed();
      setBusy(false);
      setFeedback(null);
      load(false);
    };
    window.addEventListener(SESSION_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, refresh);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function pick(year: number) {
    setFeedback(null);
    setStartFeedback(null);
    window.history.replaceState(null, "", `/holiday-calendar?year=${year}`);
    void controller.setQuery(year);
  }

  function edit(next: YearForm) {
    setPage((current) => ({ ...current, form: next }));
    setFeedback(null);
  }

  function start() {
    const problem = startYearProblem(startText);
    if (problem) {
      setStartFeedback({ kind: "error", text: problem });
      return;
    }
    setStartText("");
    pick(Number(startText.trim()));
  }

  async function save(year: CalendarYear, form: YearForm, stateLabels: Record<string, string>) {
    const problem = yearFormProblem(form, year.calendar_year, stateLabels);
    if (problem) {
      setFeedback({ kind: "error", text: problem });
      return;
    }
    const token = getToken();
    if (!token) {
      setFeedback({ kind: "error", text: SIGN_IN_FIRST });
      return;
    }
    setBusy(true);
    await actInSession(
      session,
      async () =>
        readActionAnswer<CalendarYearAction>(
          await fetch(`/api/holiday-calendar/years/${year.calendar_year}`, {
            method: "PUT",
            headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
            body: JSON.stringify(yearPayload(form, year.year_version)),
          }),
          "The calendar was not saved.",
        ),
      {
        settled: () => setBusy(false),
        failed: () => setFeedback({ kind: "error", text: "Network error: the calendar was not saved." }),
        apply: (result) => {
          if (result.status === 401) {
            clearSession();
            return;
          }
          if ("refusal" in result) {
            // Saved by someone else meanwhile: read the year again, keeping the message.
            if (result.status === 409) load(true);
            setFeedback({ kind: "error", text: result.refusal });
            return;
          }
          setPage((current) => calendarPageSaved(current, result.body.year));
          // A year marked complete ends its reminder, and one unmarked raises it again: the menu's count follows.
          if (result.body.event) announceAlertsChanged();
          setFeedback({
            kind: "success",
            text: result.body.event ? `Saved as version ${result.body.year.year_version}. Every Work Order uses it from now.` : "Nothing changed, so nothing was saved.",
          });
        },
      },
    );
  }

  const year = answer?.year ?? null;
  const form = page.form;
  const stateLabels = Object.fromEntries((answer?.states ?? []).map((state) => [state.state_code, state.state_label]));

  return (
    <section>
      <PageHeader
        eyebrow="Hiring"
        title="Holiday Calendar"
        subtitle="PBL's holidays, year by year. Every Work Order follows this calendar for each line's site state; its own terms change it on the Work Order page. A holiday is charged as each line's off-day term says. Admin keeps the calendar and marks a year complete; until then the Alerts keep reminding."
      >
        {error ? <p className="text-danger">{error}</p> : null}
      </PageHeader>

      {answer ? (
        <div className="page-actions" role="group" aria-label="Years">
          {pickerYears(answer).map((item) => (
            <button key={item.calendar_year} type="button" aria-pressed={item.calendar_year === answer.year.calendar_year} disabled={busy || loading} onClick={() => pick(item.calendar_year)}>
              {item.calendar_year}: {yearStateText(item)}
            </button>
          ))}
        </div>
      ) : null}
      {canManage && answer ? (
        <div className="page-actions actions-with-fields">
          <label className="field-stack">
            Another year
            <input className="count-field" inputMode="numeric" maxLength={4} value={startText} disabled={busy} onChange={(event) => {
              setStartText(event.target.value);
              setStartFeedback(null);
            }} />
          </label>
          <button type="button" disabled={busy || loading} onClick={start}>
            Open the year
          </button>
          <FeedbackLine feedback={startFeedback} />
        </div>
      ) : null}
      {loading && !answer ? <p className="helper-text">Loading the holiday calendar...</p> : null}

      {year ? (
        <SectionCard title={`${year.calendar_year}`}>
          <p>
            <StatusBadge code={year.is_complete ? "COMPLETE" : "NOT_COMPLETE"} tone={year.is_complete ? "success" : "warning"} label={yearStateText(year)} />
          </p>
          {year.updated_at ? (
            <p className="helper-text">
              Saved by {year.updated_by_display_name ?? "-"} on {formatDateTime(year.updated_at)}
              {year.is_complete && year.complete_marked_at ? `; marked complete by ${year.complete_marked_by_display_name ?? "-"} on ${formatDateTime(year.complete_marked_at)}` : ""}.
            </p>
          ) : (
            <p className="helper-text">Not set up yet. {canManage ? "Enter its holidays below and save to start it." : "Admin sets it up."}</p>
          )}

          {canManage && form ? (
            <YearEditor
              year={year}
              form={form}
              states={answer!.states}
              busy={busy}
              disabled={busy || loading}
              feedback={feedback}
              onEdit={edit}
              onAdd={() => {
                nextRowKey.current += 1;
                edit(addRow(form, `new-${nextRowKey.current}`));
              }}
              onUndo={() => edit(formFromYear(year))}
              onSave={() => void save(year, form, stateLabels)}
            />
          ) : (
            <ReadOnlyYear year={year} />
          )}
        </SectionCard>
      ) : null}
    </section>
  );
}

function ReadOnlyYear({ year }: { year: CalendarYear }) {
  if (year.holidays.length === 0) return <p className="empty-state">No holidays entered for {year.calendar_year}.</p>;
  return (
    <div className="data-table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Date</th>
            <th>Holiday</th>
            <th>Kind</th>
            <th>Where</th>
          </tr>
        </thead>
        <tbody>
          {year.holidays.map((holiday) => (
            <tr key={holiday.holiday_public_id}>
              <td>{formatDay(holiday.holiday_date)}</td>
              <td>{holiday.holiday_name}</td>
              <td>{holiday.holiday_kind_label}</td>
              <td>{appliesText(holiday)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function YearEditor(props: {
  year: CalendarYear;
  form: YearForm;
  states: CalendarState[];
  busy: boolean;
  disabled: boolean;
  feedback: Feedback;
  onEdit: (next: YearForm) => void;
  onAdd: () => void;
  onUndo: () => void;
  onSave: () => void;
}) {
  const { year, form, states, busy, disabled, feedback, onEdit, onAdd, onUndo, onSave } = props;
  const changed = yearFormChanged(form, year);
  const warning = passedDaysWarning(form, year);
  const row = (key: string, change: Partial<Omit<HolidayRow, "key">>) => onEdit(updateRow(form, key, change));

  return (
    <>
      {form.rows.length > 0 ? (
        <div className="data-table-wrap">
          <table className="data-table data-table-wide">
            <thead>
              <tr>
                <th>Date</th>
                <th>Holiday</th>
                <th>Kind</th>
                <th>Where</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {form.rows.map((item) => (
                <tr key={item.key}>
                  <td>
                    <DateInput aria-label="Date" value={item.date} min={`${year.calendar_year}-01-01`} max={`${year.calendar_year}-12-31`} disabled={disabled} onChange={(event) => row(item.key, { date: event.target.value })} />
                  </td>
                  <td>
                    <input aria-label="Holiday" value={item.name} maxLength={NAME_MAX_LENGTH} disabled={disabled} onChange={(event) => row(item.key, { name: event.target.value })} />
                  </td>
                  <td>
                    <select aria-label="Kind" value={item.kind} disabled={disabled} onChange={(event) => row(item.key, { kind: event.target.value })}>
                      {KIND_OPTIONS.map((option) => (
                        <option key={option.code} value={option.code}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <select aria-label="Where" value={item.appliesTo} disabled={disabled} onChange={(event) => row(item.key, { appliesTo: event.target.value })}>
                      <option value={ALL_INDIA}>All of India</option>
                      <option value={STATES}>These states</option>
                    </select>
                    {item.appliesTo === STATES ? (
                      <details>
                        <summary>
                          {item.states.length === 0 ? "Choose the states" : states.filter((state) => item.states.includes(state.state_code)).map((state) => state.state_label).join(", ")}
                        </summary>
                        <fieldset className="state-picker">
                          {states.map((state) => (
                            <label key={state.state_code}>
                              <input type="checkbox" checked={item.states.includes(state.state_code)} disabled={disabled} onChange={() => onEdit(toggleState(form, item.key, state.state_code))} /> {state.state_label}
                            </label>
                          ))}
                        </fieldset>
                      </details>
                    ) : null}
                  </td>
                  <td>
                    <button type="button" disabled={disabled} onClick={() => onEdit(removeRow(form, item.key))}>
                      Remove
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="empty-state">No holidays entered for {year.calendar_year} yet.</p>
      )}
      <div className="page-actions">
        <button type="button" disabled={disabled} onClick={onAdd}>
          Add a holiday
        </button>
      </div>
      <label className="tick-row">
        <input type="checkbox" checked={form.complete} disabled={disabled} onChange={(event) => onEdit({ ...form, complete: event.target.checked })} />
        <span>
          This year's calendar is complete. Until it is marked so, the Alerts remind Admin - and Management once the year has begun - and each Work
          Order running into it says so.
        </span>
      </label>
      {warning ? <p className="text-warning">{warning}</p> : null}
      <div className="page-actions">
        <button type="button" disabled={disabled || !changed} onClick={onSave}>
          {busy ? "Saving..." : "Save"}
        </button>
        <button type="button" disabled={disabled || !changed} onClick={onUndo}>
          Undo changes
        </button>
      </div>
      <FeedbackLine feedback={feedback ?? undefined} />
    </>
  );
}
