import { useEffect, useRef, useState } from "react";

import { PageHeader, StatusBadge } from "../../components/PageLayout";
import { EquipmentNav, FeedbackLine } from "../equipment/EquipmentParts";
import type { Feedback } from "../equipment/equipmentState";
import { createQueryController, formatDay, initialQueryView, queryViewKeeping } from "../equipment/certificatesState";
import { SESSION_CHANGED_EVENT, clearSession, formatDateTime, getToken, hrefWithReturnTarget, readErrorDetail } from "../resource-requirements/pageSession";
import {
  ALERT_SEARCH_MAX_LENGTH,
  REMINDER_KIND_CODES,
  REMINDER_KIND_LABELS,
  type AlertFilters,
  type AlertItem,
  type Alerts,
  actInSession,
  alertFiltersFromSearch,
  alertText,
  alertsPageHref,
  alertsQuery,
  announceAlertsChanged,
  createSessionGuard,
  createShownQuery,
  isCalendarReminder,
  isOverdue,
  reachedText,
  readActionAnswer,
  showMarkedSeen,
  shownOfText,
  remindedText,
  unseenPairs,
} from "./alertsState";

// Alerts (ELG-2, design section 6): the certificate reminders that have reached the signed-in person - and, since HOL-1,
// a year of PBL's holiday calendar not marked complete - worked out by the server each time the page is read. "Mark as
// seen" quiets a reminder for you until its next reminder day; it never stops the reminders, nor their reaching more
// people (Q17). Nothing is sent: the screen is the only channel.

const PAGE_SIZE = 100;

type SeenAnswer = { marked: number; already: number };

type Query = { filters: AlertFilters; offset: number };

export default function AlertsPage() {
  // Opened from a page a reminder links to, the list comes back as it was: the filters are in the address.
  const [opened] = useState(() => alertFiltersFromSearch(typeof window === "undefined" ? "" : window.location.search));
  const [filters, setFilters] = useState<AlertFilters>(opened);
  const [offset, setOffset] = useState(0);
  const [view, setView] = useState(initialQueryView<Alerts>());
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<Record<string, Feedback>>({});
  const alerts = view.answer;
  const { loading, error } = view;
  // The list now shown, for marking seen on it (showMarkedSeen).
  const shownView = useRef(view);
  shownView.current = view;
  // Reading the same query again keeps the list on screen; another clears it at once (alertsState.ts).
  const [shown] = useState(() => createShownQuery<Query>({ filters: opened, offset: 0 }));
  // An answer to marking seen is applied only in the session it was asked in (alertsState.ts).
  const [session] = useState(() => createSessionGuard());

  const [controller] = useState(() =>
    createQueryController<Query, Alerts>({
      initialQuery: { filters: opened, offset: 0 },
      getToken,
      failure: "Network error: the alerts could not be loaded.",
      fetchAnswer: async (token, query) => {
        const response = await fetch(`/api/eligibility/alerts?${alertsQuery(query.filters, query.offset, PAGE_SIZE)}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.status === 401) clearSession();
        if (!response.ok) throw new Error(await readErrorDetail(response, "The alerts could not be loaded."));
        return (await response.json()) as Alerts;
      },
      show: (update) => {
        const keep = shown.keeps();
        if (update.kind === "answer") shown.answered();
        else if (update.kind !== "loading") shown.cleared();
        setView((current) => queryViewKeeping(current, update, () => keep));
        // The list is read afresh: the menu's count follows it, so the two never disagree on this page.
        if (update.kind === "answer") announceAlertsChanged();
      },
    }),
  );

  function change(next: Partial<AlertFilters>) {
    const merged = { ...filters, ...next };
    setFilters(merged);
    setOffset(0);
    setFeedback({});
    shown.ask({ filters: merged, offset: 0 });
    void controller.setQuery({ filters: merged, offset: 0 });
  }

  function page(nextOffset: number) {
    setOffset(nextOffset);
    setFeedback({});
    shown.ask({ filters, offset: nextOffset });
    void controller.setQuery({ filters, offset: nextOffset });
  }

  useEffect(() => {
    void controller.refresh();
    // After a session change - signed out, or in as someone else - the list is read again for the new person.
    const refresh = () => {
      session.changed();
      setBusy(false);
      setFeedback({});
      shown.cleared();
      void controller.refresh();
    };
    window.addEventListener(SESSION_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(SESSION_CHANGED_EVENT, refresh);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function markSeen(where: string, pairs: { reminder_key: string; reminder_on: string }[]) {
    const token = getToken();
    if (!token || pairs.length === 0) return;
    const asked = controller.query();
    setBusy(true);
    setFeedback({});
    // The whole answer is read, then applied only in the session it was asked in (alertsState.ts).
    await actInSession(
      session,
      async () =>
        readActionAnswer<SeenAnswer>(
          await fetch("/api/eligibility/alerts/seen", {
            method: "POST",
            headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
            body: JSON.stringify({ items: pairs }),
          }),
          "Nothing was marked.",
        ),
      {
        settled: () => setBusy(false),
        failed: () => setFeedback({ [where]: { kind: "error", text: "Network error: nothing was marked." } }),
        apply: (answer) => {
          if (answer.status === 401) {
            clearSession();
            return;
          }
          // The list is not read again: the message stays beside the button that asked. A refusal says to read the
          // list again (Refresh); marked reminders say "Seen by you" where they are, and leave a list of those not
          // seen when it is next read (alertsState.ts, alertsMarkedSeen).
          if ("refusal" in answer) {
            setFeedback({ [where]: { kind: "error", text: answer.refusal } });
            return;
          }
          const marked = answer.body.marked + answer.body.already;
          setFeedback({ [where]: { kind: "success", text: marked === 1 ? "Marked as seen." : `${marked} marked as seen.` } });
          announceAlertsChanged();
          if (controller.isCurrent(asked)) {
            showMarkedSeen(controller, shownView.current.answer, pairs.map((pair) => pair.reminder_key));
          }
        },
      },
    );
  }

  const items = alerts?.items ?? [];
  const hasNextPage = alerts ? offset + items.length < alerts.total : false;
  const unseenShown = unseenPairs(items);

  return (
    <section>
      <PageHeader
        eyebrow="Equipment"
        title="Alerts"
        subtitle="Certificate reminders that have reached you, and PBL's holiday calendar for a year not yet complete. Mark one as seen to quiet it until its next reminder - it still goes on reaching others until its cause is dealt with: a renewal in force with its copy attached, the certificate marked not applicable where the law allows, or the machine retired - and, for a job's reminder, also the machine freed from or replaced on that job. A calendar reminder ends when Admin marks the year complete."
      >
        {error ? <p className="text-danger">{error}</p> : null}
      </PageHeader>
      <EquipmentNav current="/alerts" />
      <p className="helper-text">
        Reminders are shown here only. Email and SMS will come when they are connected. See also{" "}
        <a href="/equipment/certificates">Certificates due</a> and <a href="/equipment/alert-settings">Reminder settings</a>.
      </p>

      <div className="page-actions" role="group" aria-label="Kinds of reminder">
        <button type="button" aria-pressed={filters.kind === ""} disabled={busy} onClick={() => change({ kind: "" })}>
          All ({alerts?.counts.total ?? 0})
        </button>
        {REMINDER_KIND_CODES.map((kind) => (
          <button key={kind} type="button" aria-pressed={filters.kind === kind} disabled={busy} onClick={() => change({ kind })}>
            {REMINDER_KIND_LABELS[kind]} ({alerts?.counts.by_kind[kind] ?? 0})
          </button>
        ))}
      </div>

      <div className="page-actions actions-with-fields">
        <label className="field-stack">
          Machine, piece, Work Order, allocation or year
          <input value={filters.search} disabled={busy} onChange={(event) => change({ search: event.target.value })} maxLength={ALERT_SEARCH_MAX_LENGTH} />
        </label>
        <label>
          <input type="checkbox" checked={filters.unseenOnly} disabled={busy} onChange={(event) => change({ unseenOnly: event.target.checked })} /> Only those I have
          not seen ({alerts?.counts.unseen ?? 0})
        </label>
        <button type="button" onClick={() => void controller.refresh()} disabled={loading || busy}>
          {loading ? "Loading..." : "Refresh"}
        </button>
        <button type="button" onClick={() => void markSeen("all", unseenShown)} disabled={busy || loading || unseenShown.length === 0}>
          Mark all shown as seen
        </button>
      </div>
      <FeedbackLine feedback={feedback.all} />
      {alerts ? <p className="helper-text">{shownOfText(alerts, filters.unseenOnly)}</p> : null}

      {items.length > 0 ? (
        <div className="data-table-wrap">
          <table className="data-table data-table-wide">
            <thead>
              <tr>
                <th>Reminder</th>
                <th>Machine, piece or year</th>
                <th>What it means</th>
                <th>Reached</th>
                <th>Seen</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <AlertRow
                  key={item.reminder_key}
                  item={item}
                  today={alerts!.today}
                  backTo={alertsPageHref(filters)}
                  // Not while the list is read: a read and a mark never overlap (ELG2-R6-001).
                  busy={busy || loading}
                  feedback={feedback[item.reminder_key]}
                  onSeen={() => void markSeen(item.reminder_key, unseenPairs([item]))}
                />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      {!loading && !error && alerts && items.length === 0 ? (
        <div className="empty-state">
          {alerts.counts.total === 0
            ? `No reminder has reached you. Worked out on ${formatDay(alerts.today)}; Reminder settings says who each reminder reaches.`
            : "Nothing among these. Untick \"Only those I have not seen\", or clear the search, to see the others."}
        </div>
      ) : null}

      <div className="pagination-row">
        <button type="button" disabled={loading || busy || offset === 0} onClick={() => page(Math.max(0, offset - PAGE_SIZE))}>
          Previous
        </button>
        <button type="button" disabled={loading || busy || !hasNextPage} onClick={() => page(offset + PAGE_SIZE)}>
          Next
        </button>
      </div>
    </section>
  );
}

function AlertRow(props: { item: AlertItem; today: string; backTo: string; busy: boolean; feedback: Feedback | undefined; onSeen: () => void }) {
  const { item, today, backTo, busy, feedback, onSeen } = props;
  const job = item.allocation;
  // Each page a reminder links to offers the way back to this list, as it was (the owner's screen check).
  const linked = (href: string) => hrefWithReturnTarget(href, backTo, "Back to Alerts");
  return (
    <tr>
      <td>
        <StatusBadge code={item.reminder_kind_code} tone={isOverdue(item, today) ? "danger" : "warning"} label={item.reminder_kind_label} />
      </td>
      <td>
        {item.asset ? (
          <>
            <a href={linked(`/equipment/machines/${item.asset.asset_public_id}`)}>{item.asset.asset_reference}</a> {item.asset.machine_number ?? item.asset.serial_number ?? ""}
            <div className="helper-text">
              {item.asset.type_label ? `${item.asset.type_label} ${item.asset.class_label.toLowerCase()}` : item.asset.class_label}
            </div>
          </>
        ) : isCalendarReminder(item) ? (
          <a href={linked(`/holiday-calendar?year=${item.calendar_year ?? item.date_on.slice(0, 4)}`)}>Holiday Calendar {item.calendar_year ?? item.date_on.slice(0, 4)}</a>
        ) : null}
      </td>
      <td>
        {alertText(item, today)}
        {item.certificate_asset_reference ? <div className="helper-text">On its fitted part {item.certificate_asset_reference}</div> : null}
        {job ? (
          <div className="helper-text">
            <a href={linked(`/work-orders/${job.work_order_public_id}`)}>{job.work_order_code}</a>, line {job.work_order_line_number}, unit {job.unit_number}:{" "}
            <a href={linked(`/resource-assignments/${job.assignment_public_id}`)}>{job.assignment_reference}</a>
            {job.trip_number ? `, Trip (Own Load) ${job.trip_number}` : ""}
          </div>
        ) : null}
        <div className="helper-text">{remindedText(item)}</div>
      </td>
      <td>{reachedText(item)}</td>
      <td>
        {item.seen_by.length > 0 ? (
          <div className="helper-text">
            Seen by {item.seen_by.map((seen) => `${seen.display_name} (${formatDateTime(seen.seen_at)})`).join("; ")}
          </div>
        ) : null}
        {item.seen_by_me ? (
          <span className="helper-text">Seen by you</span>
        ) : (
          <button type="button" disabled={busy} onClick={onSeen}>
            Mark as seen
          </button>
        )}
        <FeedbackLine feedback={feedback} />
      </td>
    </tr>
  );
}
