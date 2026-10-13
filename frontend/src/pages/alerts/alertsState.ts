// Certificate reminders and escalation (ELG-2): the Alerts page's and the menu count's rules, kept apart from the
// components so they are tested without a browser. docs/agent/slices/elg-2-certificate-reminders.md, sections 5
// and 6. The reminders are worked out by the server each time they are read; the screen is their only channel.

import { ALERT_COUNT_KEY } from "../../components/sessionAlertCount";
import { type AssetSummary, formatDay } from "../equipment/certificatesState";
import { readErrorDetail } from "../resource-requirements/pageSession";
import { createLatestOnly } from "../resource-requirements/resourceRequirementState";

export type AlertReached = { step_number: number; role_code: string; role_label: string; reached_on: string };
export type AlertSeenBy = { display_name: string; seen_at: string };

export type AlertAllocation = {
  assignment_public_id: string;
  assignment_reference: string;
  work_order_public_id: string;
  work_order_code: string;
  work_order_line_number: number;
  unit_number: number;
  trip_number: number | null;
  kit_line_public_id: string | null;
  site_label: string | null;
  site_state_code: string;
  site_state_label: string;
  central_government_site: boolean;
  period_from: string;
  period_to: string | null;
};

export type AlertItem = {
  reminder_key: string;
  reminder_kind_code: string;
  reminder_kind_label: string;
  // Null for PBL's holiday calendar not set up, which is about a year, not a machine (HOL-1).
  asset: AssetSummary | null;
  certificate_asset_reference: string | null;
  kind_code: string;
  kind_label: string;
  outcome_code: string;
  date_on: string;
  reason_code: string;
  mark_public_id: string | null;
  allocation: AlertAllocation | null;
  // The year a calendar reminder is about (HOL-1); null for every certificate reminder.
  calendar_year?: number | null;
  began_on: string;
  first_reminder_on: string;
  reminder_on: string;
  reminders_so_far: number;
  reached: AlertReached[];
  seen_by_me: boolean;
  seen_by: AlertSeenBy[];
};

export type Alerts = {
  today: string;
  counts: { total: number; unseen: number; by_kind: Record<string, number> };
  total: number;
  limit: number;
  offset: number;
  items: AlertItem[];
};

export type AlertCount = { unseen: number; total: number };

export const REMINDER_KIND_CODES = [
  "CERTIFICATE_RUNNING_OUT",
  "NOT_YET_RECORDED",
  "BEFORE_JOB_STARTS",
  "DURING_JOB",
  // HOL-1, Q2: PBL's holiday calendar for a year not marked complete.
  "HOLIDAY_CALENDAR_NOT_SET_UP",
] as const;

export const REMINDER_KIND_LABELS: Record<string, string> = {
  CERTIFICATE_RUNNING_OUT: "A certificate running out",
  NOT_YET_RECORDED: "A certificate not yet recorded",
  BEFORE_JOB_STARTS: "Runs out before the job starts",
  DURING_JOB: "Runs out during the job",
  HOLIDAY_CALENDAR_NOT_SET_UP: "PBL's holiday calendar not set up",
};

/** Whether a reminder is about a year of PBL's holiday calendar rather than a machine (HOL-1). */
export function isCalendarReminder(item: Pick<AlertItem, "reminder_kind_code">): boolean {
  return item.reminder_kind_code === "HOLIDAY_CALENDAR_NOT_SET_UP";
}

// --- The list ------------------------------------------------------------------------------------------------

export type AlertFilters = { kind: string; unseenOnly: boolean; search: string };

/** At first, only what you have not seen: the list then matches the count in the menu. */
export const INITIAL_ALERT_FILTERS: AlertFilters = { kind: "", unseenOnly: true, search: "" };

/** The search box's limit, as the server's. */
export const ALERT_SEARCH_MAX_LENGTH = 100;

/** The Alerts page's address with these filters: a page opened from a reminder comes back to the list as it was
 *  (the owner's screen check, 1 October 2026). */
export function alertsPageHref(filters: AlertFilters): string {
  const params = new URLSearchParams();
  if (filters.kind) params.set("kind", filters.kind);
  if (!filters.unseenOnly) params.set("all", "1");
  if (filters.search.trim()) params.set("search", filters.search.trim());
  const query = params.toString();
  return query ? `/alerts?${query}` : "/alerts";
}

/** The filters an Alerts address carries; anything not understood is left as it is at first. */
export function alertFiltersFromSearch(search: string): AlertFilters {
  const params = new URLSearchParams(search);
  const kind = params.get("kind") ?? "";
  return {
    kind: (REMINDER_KIND_CODES as readonly string[]).includes(kind) ? kind : INITIAL_ALERT_FILTERS.kind,
    unseenOnly: params.get("all") !== "1",
    search: (params.get("search") ?? "").slice(0, ALERT_SEARCH_MAX_LENGTH),
  };
}

export function alertsQuery(filters: AlertFilters, offset: number, pageSize: number): string {
  const params = new URLSearchParams();
  if (filters.kind) params.set("reminder_kind_code", filters.kind);
  if (filters.unseenOnly) params.set("unseen_only", "true");
  if (filters.search.trim()) params.set("search", filters.search.trim());
  params.set("limit", String(pageSize));
  params.set("offset", String(offset));
  return params.toString();
}

function lower(label: string): string {
  return label.charAt(0).toLowerCase() + label.slice(1);
}

/** What the reminder is about, with its date and reason (design section 5.2): "Insurance runs out on 5 October
 *  2026", "Load test missing since 3 October 2026 - machine added to the Equipment Master". */
export function reasonText(item: Pick<AlertItem, "kind_label" | "reason_code" | "date_on">, today: string): string {
  const kind = item.kind_label;
  const day = formatDay(item.date_on);
  switch (item.reason_code) {
    case "RUNS_OUT":
      if (item.date_on < today) return `${kind} ran out on ${day}`;
      return item.date_on === today ? `${kind} runs out today, ${day}` : `${kind} runs out on ${day}`;
    case "MARK_ENDS":
      return item.date_on < today
        ? `${kind}: the "not applicable" mark ended on ${day}, so the ${lower(kind)} is needed`
        : `${kind}: "not applicable" until ${day}; the ${lower(kind)} is needed after that`;
    case "MARK_WITHDRAWN":
      return `${kind} needed since the "not applicable" mark was withdrawn on ${day}`;
    case "COPY_MISSING":
      return `${kind}: covered until ${day}; the certificate taking over after it has no copy attached`;
    case "MACHINE_ADDED":
      return `${kind} missing since ${day} - added to the Equipment Master then`;
    case "RULE_IN_EFFECT":
      return item.date_on > today
        ? `${kind} needed from ${day} - required by a rule from that day`
        : `${kind} missing since ${day} - required by a rule from that day`;
    case "CALENDAR_NOT_COMPLETE": {
      // HOL-1, Q2: dated 1 January of the year it is about.
      const year = item.date_on.slice(0, 4);
      return item.date_on <= today
        ? `PBL's holiday calendar for ${year} is not marked complete, and ${year} began on ${day}`
        : `PBL's holiday calendar for ${year} is not marked complete; ${year} begins on ${day}`;
    }
    case "REGISTERED_TRANSPORT":
      // A job's rules may be chosen for a later day, so the registration may not have taken effect yet (ELG2-R5-001).
      return item.date_on > today
        ? `${kind} needed from ${day} - registered as a transport vehicle from that day`
        : `${kind} missing since ${day} - registered as a transport vehicle`;
    default:
      return `${kind}: ${day}`;
  }
}

/** For an allocation reminder, the job it is about: "before the job at Dahej, Gujarat starts on 20 October 2026". */
export function jobText(item: Pick<AlertItem, "reminder_kind_code" | "allocation">): string {
  const job = item.allocation;
  if (!job) return "";
  const site = [job.site_label, job.site_state_label].filter(Boolean).join(", ");
  const at = site ? ` at ${site}` : "";
  if (item.reminder_kind_code === "BEFORE_JOB_STARTS") return `before the job${at} starts on ${formatDay(job.period_from)}`;
  const until = job.period_to ? `to ${formatDay(job.period_to)}` : "with no end date";
  return `during the job${at}, ${formatDay(job.period_from)} ${until}`;
}

export function alertText(item: AlertItem, today: string): string {
  const job = jobText(item);
  return job ? `${reasonText(item, today)}, ${job}` : reasonText(item, today);
}

export function remindedText(item: Pick<AlertItem, "reminders_so_far" | "first_reminder_on">): string {
  if (item.reminders_so_far <= 1) return `Reminded once, on ${formatDay(item.first_reminder_on)}`;
  return `Reminded ${item.reminders_so_far} times since ${formatDay(item.first_reminder_on)}`;
}

export function reachedText(item: Pick<AlertItem, "reached">): string {
  return item.reached.map((step) => `${step.role_label} from ${formatDay(step.reached_on)}`).join("; ");
}

/** The reminders on the page not yet seen by you, as "Mark all shown as seen" sends them. */
export function unseenPairs(items: readonly Pick<AlertItem, "reminder_key" | "reminder_on" | "seen_by_me">[]): { reminder_key: string; reminder_on: string }[] {
  return items.filter((item) => !item.seen_by_me).map((item) => ({ reminder_key: item.reminder_key, reminder_on: item.reminder_on }));
}

/**
 * The list after reminders are marked seen: each one marked "Seen by you" where it is, and the count of those not
 * seen lowered by those newly seen. The list is not read again, so a marked reminder stays in place with "Marked as
 * seen." beside it - the message is not taken away with the row - and leaves a list of those not seen when the list is
 * next read (the full E2E run on the final tree, design section 16, refinement 11).
 */
/**
 * After reminders are marked seen, show them so on the list in hand through the read's own controller: a read still
 * on its way - formed before the marks were made - is dropped, and cannot bring them back unseen (independent review,
 * ELG2-R6-001). Nothing is shown when no list is.
 */
export function showMarkedSeen(controller: { answered: (answer: Alerts) => void }, shown: Alerts | null, keys: readonly string[]): void {
  if (shown) controller.answered(alertsMarkedSeen(shown, keys));
}

export function alertsMarkedSeen(alerts: Alerts, keys: readonly string[]): Alerts {
  const marked = new Set(keys);
  let newlySeen = 0;
  const items = alerts.items.map((item) => {
    if (!marked.has(item.reminder_key) || item.seen_by_me) return item;
    newlySeen += 1;
    return { ...item, seen_by_me: true };
  });
  return { ...alerts, items, counts: { ...alerts.counts, unseen: Math.max(0, alerts.counts.unseen - newlySeen) } };
}

/**
 * How many reminders the list holds of all those it is drawn from, so a filter's share is visible: "6 of the 45
 * reminders you have not seen", and after one of them is marked seen, "5 of the 44" (the owner, 2 October 2026). A
 * reminder marked seen here, and kept in its place until the list is read again, is counted as seen.
 */
export function shownOfText(alerts: Pick<Alerts, "total" | "counts" | "items">, unseenOnly: boolean): string {
  const reminders = (count: number) => (count === 1 ? "reminder" : "reminders");
  if (unseenOnly) {
    const markedHere = alerts.items.filter((item) => item.seen_by_me).length;
    const shown = Math.max(0, alerts.total - markedHere);
    const all = alerts.counts.unseen;
    return shown === all ? `${all} ${reminders(all)} you have not seen` : `${shown} of the ${all} ${reminders(all)} you have not seen`;
  }
  const all = alerts.counts.total;
  return alerts.total === all
    ? `${all} ${reminders(all)} that have reached you`
    : `${alerts.total} of the ${all} ${reminders(all)} that have reached you`;
}

/** Whether a reminder is about a date already passed or missing papers: shown as urgent. */
export function isOverdue(item: Pick<AlertItem, "date_on">, today: string): boolean {
  return item.date_on <= today;
}

// --- The count in the menu ---------------------------------------------------------------------------------------

/** Where the menu keeps the count it last read, for at most five minutes (design section 6); Sign out removes it. */
export { ALERT_COUNT_KEY };
export const ALERT_COUNT_MAX_AGE_MS = 5 * 60 * 1000;
/**
 * Raised when the reminders reaching the person may have changed - reminders marked seen, the Alerts list read afresh, or
 * a calendar year saved: the menu reads its count again at once rather than keep a count up to five minutes old. Raise it
 * with `announceAlertsChanged`.
 */
export const ALERTS_SEEN_EVENT = "pbl-alerts-seen";

/**
 * Tell the menu to read its count again now. The owner's HOL-1 screen check (3 October 2026) found the menu still showing
 * 1 after a year marked complete had ended its reminder, and after a page reload, while Alerts listed none: the count
 * was the one kept for five minutes. A reminder can end on another page - a year marked complete, a renewal recorded - so
 * those pages raise it, and so does the Alerts page whenever it reads its list, so the two never disagree there.
 */
export function announceAlertsChanged(target: Pick<EventTarget, "dispatchEvent"> = window): void {
  target.dispatchEvent(new Event(ALERTS_SEEN_EVENT));
}

type CountStore = Pick<Storage, "getItem" | "setItem">;
type CachedCount = { session: string; unseen: number; at: number };

/**
 * A fingerprint of the sign-in token: it tells one session's kept count from another's without keeping the token,
 * which is a credential (TB-1 finding TB1-802). cyrb53, a 53-bit string hash; it cannot be turned back into the token.
 */
export function tokenFingerprint(token: string): string {
  let h1 = 0xdeadbeef ^ token.length;
  let h2 = 0x41c6ce57 ^ token.length;
  for (let i = 0; i < token.length; i++) {
    const c = token.charCodeAt(i);
    h1 = Math.imul(h1 ^ c, 2654435761);
    h2 = Math.imul(h2 ^ c, 1597334677);
  }
  h1 = Math.imul(h1 ^ (h1 >>> 16), 2246822507) ^ Math.imul(h2 ^ (h2 >>> 13), 3266489909);
  h2 = Math.imul(h2 ^ (h2 >>> 16), 2246822507) ^ Math.imul(h1 ^ (h1 >>> 13), 3266489909);
  return (4294967296 * (2097151 & h2) + (h1 >>> 0)).toString(36);
}

/**
 * The count last read for this session, if it was read in the last five minutes. A count read for another session -
 * someone else signed in, in this tab or another - is never shown for this one; nor is one kept in the earlier form,
 * which held the token itself. The store is passed as a function because merely reaching `window.sessionStorage` can
 * throw.
 */
export function readCachedCount(store: () => CountStore, token: string, now: number): number | null {
  try {
    const saved = store().getItem(ALERT_COUNT_KEY);
    if (!saved) return null;
    const parsed = JSON.parse(saved) as Partial<CachedCount>;
    if (parsed.session !== tokenFingerprint(token) || typeof parsed.unseen !== "number" || typeof parsed.at !== "number") {
      return null;
    }
    if (now - parsed.at < 0 || now - parsed.at >= ALERT_COUNT_MAX_AGE_MS) return null;
    return parsed.unseen;
  } catch {
    return null;
  }
}

export function writeCachedCount(store: () => CountStore, token: string, unseen: number, now: number): void {
  try {
    store().setItem(ALERT_COUNT_KEY, JSON.stringify({ session: tokenFingerprint(token), unseen, at: now }));
  } catch {
    // Storage refused: the count is read again on the next page instead.
  }
}

/** A count fetched, with the session it was fetched for. */
export type ResolvedCount = { token: string; unseen: number };

/** The count to show now: only one fetched for the session in use. */
export function countForToken(resolved: ResolvedCount | null, token: string | null): number | null {
  if (!token || !resolved || resolved.token !== token) return null;
  return resolved.unseen;
}

/**
 * The menu's count, loaded latest-only (independent review, ELG2-R1-003): every load takes a ticket, and only the
 * latest load's answer is shown or kept - an older request answering after a newer one changes nothing, for the same
 * session or another. The session in use is read at the start of every load, so a count read for an earlier session
 * is never shown under a later one. `show` receives the count to show, or null.
 */
export function createCountLoader(deps: {
  getToken: () => string | null;
  fetchCount: (token: string) => Promise<number>;
  store: () => CountStore;
  now: () => number;
  show: (unseen: number | null) => void;
}) {
  const latest = createLatestOnly();
  let token: string | null = null;
  let resolved: ResolvedCount | null = null;
  const emit = () => deps.show(countForToken(resolved, token));

  return {
    /** Read the count; `force` skips the five minutes kept in the session's storage. */
    load: async (force: boolean): Promise<void> => {
      const ticket = latest.begin();
      const asked = deps.getToken();
      token = asked;
      emit();
      if (!asked) return;
      const cached = force ? null : readCachedCount(deps.store, asked, deps.now());
      if (cached !== null) {
        resolved = { token: asked, unseen: cached };
        emit();
        return;
      }
      try {
        const unseen = await deps.fetchCount(asked);
        if (!latest.isLatest(ticket)) return;
        writeCachedCount(deps.store, asked, unseen, deps.now());
        resolved = { token: asked, unseen };
        emit();
      } catch {
        // The menu works without its count.
      }
    },
  };
}

/** The count as the menu shows it: nothing when nothing is waiting. */
export function countLabel(unseen: number | null): string {
  if (!unseen || unseen < 1) return "";
  return unseen > 99 ? "99+" : String(unseen);
}

// --- Which list stays on screen ----------------------------------------------------------------------------------

/**
 * The query the list on screen answers, and the one now asked. Reading the same query again - after marking
 * reminders seen - keeps the list on screen until the new one arrives, so the page does not jump to its top (8A's
 * screen check); asking another - a filter, a page, a session change - clears it at once, so a list is never shown
 * under controls it does not answer (ELG-1 review, round 2).
 */
export function createShownQuery<Query>(initial: Query) {
  let asked = JSON.stringify(initial);
  let shown: string | null = null;
  return {
    ask: (query: Query): void => {
      asked = JSON.stringify(query);
    },
    /** Whether the list on screen may stay while the query now asked is read. */
    keeps: (): boolean => shown !== null && shown === asked,
    answered: (): void => {
      shown = asked;
    },
    cleared: (): void => {
      shown = null;
    },
  };
}

// --- The session an action belongs to ---------------------------------------------------------------------------

/**
 * The session a page's actions belong to (independent review, ELG2-R2-005): a count that every session change moves
 * on. An action - marking seen, saving a setting - notes the session it started in, and its answer is applied only
 * while that session is still the current one, so one person's answer is never shown under another's controls.
 */
export function createSessionGuard() {
  let current = 0;
  return {
    now: (): number => current,
    changed: (): void => {
      current += 1;
    },
    isCurrent: (session: number): boolean => session === current,
  };
}

export type SessionGuard = ReturnType<typeof createSessionGuard>;

/** An action's whole answer: its status, and its body or the refusal in words. */
export type ActionAnswer<T> = { status: number; body: T } | { status: number; refusal: string };

/** Read the whole of an action's answer - the body, or the refusal's words - before anything is applied. */
export async function readActionAnswer<T>(response: Response, refused: string): Promise<ActionAnswer<T>> {
  if (!response.ok) return { status: response.status, refusal: await readErrorDetail(response, refused) };
  return { status: response.status, body: (await response.json()) as T };
}

/**
 * Run one action - marking seen, saving a setting - so that nothing of its answer is applied outside the session it
 * started in (independent review, ELG2-R2-005 and R3-001). `exchange` makes the request and reads the whole answer,
 * body included (`readActionAnswer`); only then is the session checked, immediately before anything is applied:
 * `settled`, then `apply` - or `failed` when the network failed. An answer arriving in another session is dropped
 * whole, a refusal saying the session has ended included.
 */
export async function actInSession<T>(
  guard: SessionGuard,
  exchange: () => Promise<T>,
  then: { apply: (answer: T) => void; failed: () => void; settled: () => void },
): Promise<void> {
  const startedIn = guard.now();
  let answer: { value: T } | null;
  try {
    answer = { value: await exchange() };
  } catch {
    answer = null;
  }
  if (!guard.isCurrent(startedIn)) return;
  then.settled();
  if (answer) then.apply(answer.value);
  else then.failed();
}
