import { describe, expect, it } from "vitest";

import {
  ALERTS_SEEN_EVENT,
  ALERT_COUNT_KEY,
  ALERT_COUNT_MAX_AGE_MS,
  INITIAL_ALERT_FILTERS,
  alertFiltersFromSearch,
  alertsPageHref,
  type AlertItem,
  type Alerts,
  alertText,
  alertsQuery,
  announceAlertsChanged,
  countForToken,
  countLabel,
  createCountLoader,
  actInSession,
  alertsMarkedSeen,
  showMarkedSeen,
  shownOfText,
  createSessionGuard,
  readActionAnswer,
  createShownQuery,
  isCalendarReminder,
  isOverdue,
  jobText,
  reachedText,
  readCachedCount,
  reasonText,
  remindedText,
  tokenFingerprint,
  unseenPairs,
  writeCachedCount,
} from "./alertsState";
import { createQueryController, initialQueryView, queryViewKeeping } from "../equipment/certificatesState";

const TODAY = "2026-10-01";

function item(overrides: Partial<AlertItem> = {}): AlertItem {
  return {
    reminder_key: "CERTIFICATE_RUNNING_OUT|asset|a|a|INSURANCE|2026-10-21",
    reminder_kind_code: "CERTIFICATE_RUNNING_OUT",
    reminder_kind_label: "A certificate running out",
    asset: {
      asset_public_id: "a",
      asset_reference: "EQ-000123",
      asset_kind_code: "MACHINE",
      origin_code: "PLUM",
      class_code: "CRANE",
      class_label: "Crane",
      type_code: "CRAWLER",
      type_label: "Crawler",
      machine_number: "MH-01",
      serial_number: null,
      asset_status_code: "ACTIVE",
    },
    certificate_asset_reference: null,
    kind_code: "INSURANCE",
    kind_label: "Insurance",
    outcome_code: "VALID",
    date_on: "2026-10-21",
    reason_code: "RUNS_OUT",
    mark_public_id: null,
    allocation: null,
    began_on: TODAY,
    first_reminder_on: TODAY,
    reminder_on: TODAY,
    reminders_so_far: 1,
    reached: [{ step_number: 1, role_code: "ADMIN", role_label: "Admin", reached_on: TODAY }],
    seen_by_me: false,
    seen_by: [],
    ...overrides,
  };
}

const JOB = {
  assignment_public_id: "al",
  assignment_reference: "AL-000031",
  work_order_public_id: "wo",
  work_order_code: "WO-000012",
  work_order_line_number: 1,
  unit_number: 1,
  trip_number: null,
  kit_line_public_id: null,
  site_label: "Jetty 2, Dahej",
  site_state_code: "IN-GJ",
  site_state_label: "Gujarat",
  central_government_site: false,
  period_from: "2026-10-20",
  period_to: "2026-12-31",
};

describe("the list's query", () => {
  it("asks for what the controls show; at first only what you have not seen", () => {
    expect(INITIAL_ALERT_FILTERS.unseenOnly).toBe(true);
    expect(alertsQuery(INITIAL_ALERT_FILTERS, 0, 100)).toBe("unseen_only=true&limit=100&offset=0");
    expect(alertsQuery({ kind: "DURING_JOB", unseenOnly: false, search: " AL-000031 " }, 100, 100)).toBe(
      "reminder_kind_code=DURING_JOB&search=AL-000031&limit=100&offset=100",
    );
  });
});

describe("what a reminder means, in words", () => {
  it("says each reason with its date", () => {
    expect(reasonText(item(), TODAY)).toBe("Insurance runs out on 21 October 2026");
    expect(reasonText(item({ date_on: TODAY }), TODAY)).toBe("Insurance runs out today, 1 October 2026");
    expect(reasonText(item({ date_on: "2026-09-29" }), TODAY)).toBe("Insurance ran out on 29 September 2026");
    expect(reasonText(item({ reason_code: "MARK_ENDS", kind_label: "Road tax" }), TODAY)).toBe(
      'Road tax: "not applicable" until 21 October 2026; the road tax is needed after that',
    );
    expect(reasonText(item({ reason_code: "MARK_ENDS", kind_label: "Road tax", date_on: "2026-09-20" }), TODAY)).toBe(
      'Road tax: the "not applicable" mark ended on 20 September 2026, so the road tax is needed',
    );
    expect(reasonText(item({ reason_code: "MARK_WITHDRAWN", date_on: "2026-09-25" }), TODAY)).toBe(
      'Insurance needed since the "not applicable" mark was withdrawn on 25 September 2026',
    );
    expect(reasonText(item({ reason_code: "COPY_MISSING", date_on: "2026-09-01" }), TODAY)).toBe(
      "Insurance: covered until 1 September 2026; the certificate taking over after it has no copy attached",
    );
    expect(reasonText(item({ reason_code: "MACHINE_ADDED", kind_label: "Load test", date_on: "2026-10-01" }), TODAY)).toBe(
      "Load test missing since 1 October 2026 - added to the Equipment Master then",
    );
    expect(reasonText(item({ reason_code: "RULE_IN_EFFECT", date_on: "2026-06-01" }), TODAY)).toBe(
      "Insurance missing since 1 June 2026 - required by a rule from that day",
    );
    expect(reasonText(item({ reason_code: "RULE_IN_EFFECT", date_on: "2026-12-01" }), TODAY)).toBe(
      "Insurance needed from 1 December 2026 - required by a rule from that day",
    );
    expect(reasonText(item({ reason_code: "REGISTERED_TRANSPORT", kind_label: "Fitness", date_on: "2026-07-01" }), TODAY)).toBe(
      "Fitness missing since 1 July 2026 - registered as a transport vehicle",
    );
    // A job starting after a registration saying transport takes effect: not yet missing (ELG2-R5-001).
    expect(reasonText(item({ reason_code: "REGISTERED_TRANSPORT", kind_label: "Fitness", date_on: "2026-10-14" }), TODAY)).toBe(
      "Fitness needed from 14 October 2026 - registered as a transport vehicle from that day",
    );
  });

  it("names the job an allocation reminder is about", () => {
    expect(jobText(item())).toBe("");
    const before = item({ reminder_kind_code: "BEFORE_JOB_STARTS", allocation: JOB });
    expect(jobText(before)).toBe("before the job at Jetty 2, Dahej, Gujarat starts on 20 October 2026");
    const during = item({ reminder_kind_code: "DURING_JOB", allocation: { ...JOB, period_to: null } });
    expect(jobText(during)).toBe("during the job at Jetty 2, Dahej, Gujarat, 20 October 2026 with no end date");
    expect(alertText(before, TODAY)).toBe("Insurance runs out on 21 October 2026, before the job at Jetty 2, Dahej, Gujarat starts on 20 October 2026");
  });

  it("says how often it has been reminded, and whom it has reached", () => {
    expect(remindedText(item())).toBe("Reminded once, on 1 October 2026");
    expect(remindedText(item({ reminders_so_far: 4, first_reminder_on: "2026-08-05" }))).toBe("Reminded 4 times since 5 August 2026");
    expect(
      reachedText(
        item({
          reached: [
            { step_number: 1, role_code: "ADMIN", role_label: "Admin", reached_on: "2026-08-05" },
            { step_number: 2, role_code: "OPERATIONS_USER", role_label: "Operations User", reached_on: "2026-09-20" },
          ],
        }),
      ),
    ).toBe("Admin from 5 August 2026; Operations User from 20 September 2026");
  });

  it("shows a date already come as urgent", () => {
    expect(isOverdue(item({ date_on: TODAY }), TODAY)).toBe(true);
    expect(isOverdue(item({ date_on: "2026-10-02" }), TODAY)).toBe(false);
  });
});

describe("marking all shown as seen", () => {
  it("sends each reminder not yet seen, on its current reminder day", () => {
    const items = [item({ reminder_key: "a", reminder_on: "2026-10-01" }), item({ reminder_key: "b", seen_by_me: true }), item({ reminder_key: "c", reminder_on: "2026-09-30" })];
    expect(unseenPairs(items)).toEqual([
      { reminder_key: "a", reminder_on: "2026-10-01" },
      { reminder_key: "c", reminder_on: "2026-09-30" },
    ]);
  });
});

describe("telling the menu its count may have changed", () => {
  it("raises the event the menu reads its count again on (the owner's HOL-1 screen check)", () => {
    const raised: string[] = [];
    announceAlertsChanged({ dispatchEvent: (event: Event) => (raised.push(event.type), true) });
    expect(raised).toEqual([ALERTS_SEEN_EVENT]);
  });
});

describe("the count in the menu", () => {
  function memoryStore() {
    const values = new Map<string, string>();
    return {
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => void values.set(key, value),
      values,
    };
  }

  it("is read again after five minutes, and never shown for another session", () => {
    const store = memoryStore();
    writeCachedCount(() => store, "token-a", 3, 1_000);
    expect(readCachedCount(() => store, "token-a", 1_000 + ALERT_COUNT_MAX_AGE_MS - 1)).toBe(3);
    expect(readCachedCount(() => store, "token-a", 1_000 + ALERT_COUNT_MAX_AGE_MS)).toBeNull();
    expect(readCachedCount(() => store, "token-b", 1_001)).toBeNull();
    // A clock moved back is not trusted.
    expect(readCachedCount(() => store, "token-a", 999)).toBeNull();
  });

  it("works when the browser refuses its storage, or holds something else", () => {
    const refusing = () => {
      throw new Error("refused");
    };
    expect(() => writeCachedCount(refusing, "token-a", 3, 1)).not.toThrow();
    expect(readCachedCount(refusing, "token-a", 1)).toBeNull();
    const store = memoryStore();
    store.setItem(ALERT_COUNT_KEY, "not json");
    expect(readCachedCount(() => store, "token-a", 1)).toBeNull();
    store.setItem(ALERT_COUNT_KEY, JSON.stringify({ token: "token-a", unseen: "3", at: 1 }));
    expect(readCachedCount(() => store, "token-a", 1)).toBeNull();
  });

  it("keeps a fingerprint of the session, never the sign-in token (TB-1 TB1-802)", () => {
    // Three dot-separated parts like a real token's, built here so no token-shaped text sits in the repository
    // (scripts/check_tracked_secrets.py refuses one).
    const token = ["header-part-of-the-test", "payload-part-of-the-test", "signature-part-of-the-test"].join(".");
    const store = memoryStore();
    writeCachedCount(() => store, token, 4, 1_000);
    const kept = store.values.get(ALERT_COUNT_KEY) ?? "";
    expect(kept).not.toContain(token);
    for (const part of token.split(".")) expect(kept).not.toContain(part);
    expect(JSON.parse(kept)).toEqual({ session: tokenFingerprint(token), unseen: 4, at: 1_000 });
    expect(readCachedCount(() => store, token, 1_001)).toBe(4);
    // The earlier form, which kept the token itself, is never read back.
    store.setItem(ALERT_COUNT_KEY, JSON.stringify({ token, unseen: 4, at: 1_000 }));
    expect(readCachedCount(() => store, token, 1_001)).toBeNull();
  });

  it("tells sessions apart by their fingerprint", () => {
    expect(tokenFingerprint("token-a")).toBe(tokenFingerprint("token-a"));
    expect(tokenFingerprint("token-a")).not.toBe(tokenFingerprint("token-b"));
    expect(tokenFingerprint("token-a")).toMatch(/^[0-9a-z]+$/);
  });

  it("shows a count only for the session it was read for", () => {
    expect(countForToken({ token: "a", unseen: 2 }, "a")).toBe(2);
    expect(countForToken({ token: "a", unseen: 2 }, "b")).toBeNull();
    expect(countForToken({ token: "a", unseen: 2 }, null)).toBeNull();
    expect(countForToken(null, "a")).toBeNull();
  });

  it("shows nothing when nothing is waiting", () => {
    expect(countLabel(null)).toBe("");
    expect(countLabel(0)).toBe("");
    expect(countLabel(7)).toBe("7");
    expect(countLabel(120)).toBe("99+");
  });
});

describe("which list stays on screen", () => {
  it("keeps the list only while the same query is read again", () => {
    const shown = createShownQuery({ page: 0 });
    expect(shown.keeps()).toBe(false);
    shown.answered();
    expect(shown.keeps()).toBe(true);
    shown.ask({ page: 1 });
    expect(shown.keeps()).toBe(false);
    shown.answered();
    shown.ask({ page: 1 });
    expect(shown.keeps()).toBe(true);
    shown.cleared();
    expect(shown.keeps()).toBe(false);
  });
});

describe("the menu's count, latest-only", () => {
  function deferred() {
    let resolve!: (value: number) => void;
    let reject!: (error: Error) => void;
    const promise = new Promise<number>((ok, fail) => {
      resolve = ok;
      reject = fail;
    });
    return { promise, resolve, reject };
  }

  function harness(initialToken: string | null) {
    const values = new Map<string, string>();
    const store = { getItem: (key: string) => values.get(key) ?? null, setItem: (key: string, value: string) => void values.set(key, value) };
    const shown: (number | null)[] = [];
    const asked: { token: string; answer: ReturnType<typeof deferred> }[] = [];
    let token = initialToken;
    const loader = createCountLoader({
      getToken: () => token,
      fetchCount: (given) => {
        const answer = deferred();
        asked.push({ token: given, answer });
        return answer.promise;
      },
      store: () => store,
      now: () => 1_000,
      show: (unseen) => shown.push(unseen),
    });
    return { loader, shown, asked, values, setToken: (next: string | null) => (token = next) };
  }

  it("never lets an older answer replace a newer one for the same session", async () => {
    const h = harness("token-a");
    const first = h.loader.load(true);
    const second = h.loader.load(true);
    h.asked[1].answer.resolve(4);
    await second;
    h.asked[0].answer.resolve(9);
    await first;
    expect(h.shown.filter((value) => value !== null)).toEqual([4]);
    expect(JSON.parse(h.values.get(ALERT_COUNT_KEY)!).unseen).toBe(4);
  });

  it("never shows, or keeps, an earlier session's count under a later one", async () => {
    const h = harness("token-a");
    const first = h.loader.load(true);
    h.setToken("token-b");
    const second = h.loader.load(true);
    // A's answer arrives after B's request began: neither shown nor kept.
    h.asked[0].answer.resolve(9);
    await first;
    expect(h.shown.at(-1)).toBeNull();
    expect(h.values.get(ALERT_COUNT_KEY)).toBeUndefined();
    h.asked[1].answer.resolve(2);
    await second;
    expect(h.shown.at(-1)).toBe(2);
    expect(JSON.parse(h.values.get(ALERT_COUNT_KEY)!)).toMatchObject({ session: tokenFingerprint("token-b"), unseen: 2 });
  });

  it("reads a fresh count from the session's storage, and nothing without a session", async () => {
    const h = harness("token-a");
    h.values.set(ALERT_COUNT_KEY, JSON.stringify({ session: tokenFingerprint("token-a"), unseen: 5, at: 900 }));
    await h.loader.load(false);
    expect(h.asked).toHaveLength(0);
    expect(h.shown.at(-1)).toBe(5);
    h.setToken(null);
    await h.loader.load(false);
    expect(h.shown.at(-1)).toBeNull();
    expect(h.asked).toHaveLength(0);
  });

  it("shows nothing new when the count cannot be read", async () => {
    const h = harness("token-a");
    const load = h.loader.load(true);
    h.asked[0].answer.reject(new Error("offline"));
    await load;
    expect(h.shown).toEqual([null]);
  });
});

describe("an action's answer and the session it started in", () => {
  it("applies an answer only while the session it started in is current", () => {
    const guard = createSessionGuard();
    const started = guard.now();
    expect(guard.isCurrent(started)).toBe(true);
    // Signed out, or in as someone else, while the answer was on its way: it is not applied.
    guard.changed();
    expect(guard.isCurrent(started)).toBe(false);
    const restarted = guard.now();
    expect(guard.isCurrent(restarted)).toBe(true);
  });
});

describe("an action run in its session", () => {
  function deferred<T>() {
    let resolve!: (value: T) => void;
    let reject!: (reason: unknown) => void;
    const promise = new Promise<T>((yes, no) => {
      resolve = yes;
      reject = no;
    });
    return { promise, resolve, reject };
  }

  function recorder() {
    const done: string[] = [];
    return {
      done,
      then: {
        apply: (answer: unknown) => done.push(`applied ${JSON.stringify(answer)}`),
        failed: () => done.push("failed"),
        settled: () => done.push("settled"),
      },
    };
  }

  // A response that has arrived, its body still being read.
  function arrived(status: number, body: Promise<unknown>): Response {
    return { ok: status >= 200 && status < 300, status, json: () => body } as unknown as Response;
  }

  it("drops an answer whose body arrives after the session changed", async () => {
    const guard = createSessionGuard();
    const body = deferred<unknown>();
    const { done, then } = recorder();
    const acting = actInSession(guard, () => readActionAnswer(arrived(200, body.promise), "Nothing was marked."), then);
    // The response has come; its body is still on its way when the person signs out, or in as someone else.
    await Promise.resolve();
    guard.changed();
    body.resolve({ marked: 1, already: 0 });
    await acting;
    expect(done).toEqual([]);
  });

  it("drops a refusal - a session ended included - read after the session changed", async () => {
    const guard = createSessionGuard();
    const body = deferred<unknown>();
    const { done, then } = recorder();
    const acting = actInSession(guard, () => readActionAnswer(arrived(401, body.promise), "Nothing was marked."), then);
    await Promise.resolve();
    guard.changed();
    body.resolve({ detail: "Sign in again." });
    await acting;
    expect(done).toEqual([]);
  });

  it("drops a network failure from an earlier session", async () => {
    const guard = createSessionGuard();
    const failing = deferred<unknown>();
    const { done, then } = recorder();
    const acting = actInSession(guard, () => failing.promise, then);
    guard.changed();
    failing.reject(new Error("offline"));
    await acting;
    expect(done).toEqual([]);
  });

  it("applies the whole answer, or the failure, in the session it started in", async () => {
    const guard = createSessionGuard();
    const seen = recorder();
    await actInSession(guard, () => readActionAnswer(arrived(200, Promise.resolve({ marked: 2, already: 0 })), "Nothing was marked."), seen.then);
    expect(seen.done).toEqual(["settled", 'applied {"status":200,"body":{"marked":2,"already":0}}']);
    const refused = recorder();
    await actInSession(guard, () => readActionAnswer(arrived(409, Promise.resolve({ detail: "It has moved on." })), "Nothing was marked."), refused.then);
    expect(refused.done).toEqual(["settled", 'applied {"status":409,"refusal":"It has moved on."}']);
    const offline = recorder();
    await actInSession(guard, () => Promise.reject(new Error("offline")), offline.then);
    expect(offline.done).toEqual(["settled", "failed"]);
  });
});

describe("the list after reminders are marked seen", () => {
  it("marks them seen where they are and lowers the count of those not seen by those newly seen", () => {
    const first = item({ reminder_key: "a", seen_by_me: false });
    const second = item({ reminder_key: "b", seen_by_me: false });
    const already = item({ reminder_key: "c", seen_by_me: true });
    const alerts = {
      today: TODAY,
      counts: { total: 3, unseen: 2, by_kind: { CERTIFICATE_RUNNING_OUT: 3 } },
      total: 3,
      limit: 100,
      offset: 0,
      items: [first, second, already],
    } as Alerts;
    const after = alertsMarkedSeen(alerts, ["a", "c"]);
    // Still listed, in the same order: the message beside the button stays with its row.
    expect(after.items.map((row) => [row.reminder_key, row.seen_by_me])).toEqual([
      ["a", true],
      ["b", false],
      ["c", true],
    ]);
    expect(after.counts).toEqual({ total: 3, unseen: 1, by_kind: { CERTIFICATE_RUNNING_OUT: 3 } });
    expect(after.total).toBe(3);
    // A key not on the page changes nothing.
    expect(alertsMarkedSeen(alerts, ["z"])).toEqual(alerts);
  });
});

describe("coming back to Alerts from a page a reminder links to", () => {
  it("carries the filters in the address and reads them back", () => {
    expect(alertsPageHref(INITIAL_ALERT_FILTERS)).toBe("/alerts");
    const filters = { kind: "BEFORE_JOB_STARTS", unseenOnly: false, search: "AL-000598" };
    const href = alertsPageHref(filters);
    expect(href).toBe("/alerts?kind=BEFORE_JOB_STARTS&all=1&search=AL-000598");
    expect(alertFiltersFromSearch(href.slice("/alerts".length))).toEqual(filters);
    expect(alertFiltersFromSearch("")).toEqual(INITIAL_ALERT_FILTERS);
  });

  it("leaves anything it does not understand as it is at first", () => {
    expect(alertFiltersFromSearch("?kind=SOMETHING_ELSE&all=yes&search=" + "x".repeat(150))).toEqual({
      kind: "",
      unseenOnly: true,
      search: "x".repeat(100),
    });
  });
});

describe("a mark and a read of the list on its way", () => {
  it("drops a read formed before the mark, so it cannot bring the reminder back unseen", async () => {
    const unseen = {
      today: TODAY,
      counts: { total: 1, unseen: 1, by_kind: { CERTIFICATE_RUNNING_OUT: 1 } },
      total: 1,
      limit: 100,
      offset: 0,
      items: [item({ reminder_key: "a", seen_by_me: false })],
    } as Alerts;
    const reads: ((answer: Alerts) => void)[] = [];
    let view = initialQueryView<Alerts>();
    const controller = createQueryController<string, Alerts>({
      initialQuery: "",
      getToken: () => "token",
      failure: "Network error.",
      fetchAnswer: () => new Promise<Alerts>((resolve) => reads.push(resolve)),
      show: (update) => {
        // As the page keeps the list shown while the same query is read again.
        view = queryViewKeeping(view, update, () => true);
      },
    });
    const opened = controller.refresh();
    reads[0](unseen);
    await opened;

    // Refresh, still on its way, formed before the mark; the mark answers first.
    const refreshing = controller.refresh();
    showMarkedSeen(controller, view.answer, ["a"]);
    expect(view.answer?.items[0].seen_by_me).toBe(true);
    expect(view.loading).toBe(false);

    reads[1](unseen);
    await refreshing;
    expect(view.answer?.items[0].seen_by_me).toBe(true);
    expect(view.answer?.counts.unseen).toBe(0);
  });

  it("shows nothing when no list is shown", () => {
    const answered: Alerts[] = [];
    showMarkedSeen({ answered: (answer) => answered.push(answer) }, null, ["a"]);
    expect(answered).toEqual([]);
  });
});

describe("how many the list holds of all those it is drawn from", () => {
  const list = (total: number, unseen: number, all: number, items: AlertItem[] = []) =>
    ({ total, counts: { total: all, unseen, by_kind: {} }, items }) as Pick<Alerts, "total" | "counts" | "items">;

  it("shows a filter's share of the reminders not seen, and of all of them", () => {
    expect(shownOfText(list(6, 45, 60), true)).toBe("6 of the 45 reminders you have not seen");
    expect(shownOfText(list(45, 45, 60), true)).toBe("45 reminders you have not seen");
    expect(shownOfText(list(1, 1, 1), true)).toBe("1 reminder you have not seen");
    expect(shownOfText(list(9, 45, 60), false)).toBe("9 of the 60 reminders that have reached you");
    expect(shownOfText(list(60, 45, 60), false)).toBe("60 reminders that have reached you");
  });

  it("counts a reminder marked seen here as seen, as the list will once read again", () => {
    // Six matched; one marked seen here, so 44 not seen in all: five of them still match.
    const marked = [item({ reminder_key: "a", seen_by_me: true }), item({ reminder_key: "b", seen_by_me: false })];
    expect(shownOfText(list(6, 44, 60, marked), true)).toBe("5 of the 44 reminders you have not seen");
    // Read again: the server's own figures say the same.
    expect(shownOfText(list(5, 44, 60), true)).toBe("5 of the 44 reminders you have not seen");
  });
});

describe("PBL's holiday calendar not set up (HOL-1, Q2)", () => {
  const calendar = (dateOn: string) =>
    item({
      reminder_key: `HOLIDAY_CALENDAR_NOT_SET_UP|holiday_calendar_year|${dateOn.slice(0, 4)}|||${dateOn}`,
      reminder_kind_code: "HOLIDAY_CALENDAR_NOT_SET_UP",
      reminder_kind_label: "PBL's holiday calendar not set up",
      asset: null,
      kind_code: "",
      kind_label: "",
      outcome_code: "",
      reason_code: "CALENDAR_NOT_COMPLETE",
      date_on: dateOn,
      calendar_year: Number(dateOn.slice(0, 4)),
    });

  it("is told apart from a certificate's reminder", () => {
    expect(isCalendarReminder(calendar("2027-01-01"))).toBe(true);
    expect(isCalendarReminder(item())).toBe(false);
  });

  it("says the year is not complete, before and after it begins", () => {
    expect(reasonText(calendar("2027-01-01"), TODAY)).toBe("PBL's holiday calendar for 2027 is not marked complete; 2027 begins on 1 January 2027");
    expect(reasonText(calendar("2026-01-01"), TODAY)).toBe("PBL's holiday calendar for 2026 is not marked complete, and 2026 began on 1 January 2026");
    expect(alertText(calendar("2027-01-01"), TODAY)).toBe(reasonText(calendar("2027-01-01"), TODAY));
  });

  it("can be the kind a list is filtered on, from its address too", () => {
    const filters = { ...INITIAL_ALERT_FILTERS, kind: "HOLIDAY_CALENDAR_NOT_SET_UP" };
    expect(alertFiltersFromSearch(alertsPageHref(filters).slice("/alerts".length))).toEqual(filters);
    expect(alertsQuery(filters, 0, 100)).toContain("reminder_kind_code=HOLIDAY_CALENDAR_NOT_SET_UP");
  });
});
