import { describe, expect, it } from "vitest";

import type { WorkOrderLineDetail } from "./WorkOrderLineDetailsSection";
import type { LineBillingTerms } from "./workOrderBillingTermsState";
import {
  INITIAL_WORK_ORDER_PAGE_STATE,
  type WorkOrder,
  type WorkOrderLine,
  type WorkOrderPageAction,
  type WorkOrderPageState,
  workOrderPageReducer,
} from "./workOrderPageState";

// Slice 7D Part 2, item 1. These replay the two sequences Part 1's review round 5 described - going to
// another Work Order while one is loading, and pressing Refresh while a save is in flight - which no
// component test could cover, the frontend having no component-test capability yet.

const workOrder = (publicId: string): WorkOrder =>
  ({
    public_id: publicId,
    work_order_code: `WO-${publicId}`,
    work_order_status_code: "HANDOFF_CREATED",
    commercial_offer_public_id: "co-1",
    opportunity_public_id: "opp-1",
    source_offer_status_code: "ACCEPTED",
    created_at: "2026-09-15T04:00:00",
    updated_at: "2026-09-15T04:00:00",
  }) as WorkOrder;

const line = (publicId: string): WorkOrderLine =>
  ({ public_id: publicId, line_number: 1, scope_description: "Crane", uom: "Month", currency_code: "INR" }) as WorkOrderLine;

const detail = (linePublicId: string, version: number): WorkOrderLineDetail =>
  ({ work_order_line_public_id: linePublicId, line_number: 1, detail_version: version, is_complete: false, missing_items: [] }) as WorkOrderLineDetail;

const terms = (linePublicId: string, periods: number): LineBillingTerms =>
  ({
    work_order_line_public_id: linePublicId,
    line_number: 1,
    quoted_uom: "Month",
    quoted_rate_amount: null,
    current_period_number: periods === 0 ? null : 1,
    periods: Array.from({ length: periods }, (_, index) => ({ period_number: index + 1 })),
    terms_complete: false,
    line_missing_items: ["NO_TERMS"],
  }) as unknown as LineBillingTerms;

/** Replay a sequence of actions from the page's starting state. */
function replay(...actions: WorkOrderPageAction[]): WorkOrderPageState {
  return actions.reduce(workOrderPageReducer, INITIAL_WORK_ORDER_PAGE_STATE);
}

/** Everything one successful load of `publicId` dispatches, at generation `g`. */
function fullLoad(g: number, publicId: string, lineId: string): WorkOrderPageAction[] {
  return [
    { type: "load-started", generation: g, workOrderPublicId: publicId },
    { type: "work-order-loaded", generation: g, workOrder: workOrder(publicId) },
    { type: "lines-loaded", generation: g, lines: [line(lineId)] },
    { type: "line-details", generation: g, result: { status: "loaded", entries: [detail(lineId, 1)] } },
    { type: "billing-terms", generation: g, result: { status: "loaded", entries: [terms(lineId, 1)] } },
    { type: "load-finished", generation: g },
  ];
}

describe("going to another Work Order while one is still loading", () => {
  it("ignores the first Work Order's answers once the second load has started", () => {
    const state = replay(
      { type: "load-started", generation: 1, workOrderPublicId: "wo-a" },
      { type: "load-started", generation: 2, workOrderPublicId: "wo-b" },
      // wo-a's answers arrive late, every one of them.
      { type: "work-order-loaded", generation: 1, workOrder: workOrder("wo-a") },
      { type: "lines-loaded", generation: 1, lines: [line("line-a")] },
      { type: "line-details", generation: 1, result: { status: "loaded", entries: [detail("line-a", 1)] } },
      { type: "billing-terms", generation: 1, result: { status: "loaded", entries: [terms("line-a", 1)] } },
      { type: "related-offers", generation: 1, result: { status: "loaded", entries: [] } },
      { type: "load-finished", generation: 1 },
    );
    expect(state.generation).toBe(2);
    expect(state.workOrderPublicId).toBe("wo-b");
    expect(state.workOrder).toBeNull();
    expect(state.lines).toEqual([]);
    expect(state.lineDetails).toEqual({ entries: [], loadedFor: null });
    expect(state.billingTerms).toEqual({ entries: [], loadedFor: null });
    // Still loading: the late load-finished belonged to the load that was left behind.
    expect(state.loading).toBe(true);
  });

  it("shows the second Work Order's own answers when they arrive", () => {
    const state = replay(
      { type: "load-started", generation: 1, workOrderPublicId: "wo-a" },
      ...fullLoad(2, "wo-b", "line-b"),
      { type: "line-details", generation: 1, result: { status: "loaded", entries: [detail("line-a", 9)] } },
    );
    expect(state.workOrder?.public_id).toBe("wo-b");
    expect(state.lines.map((item) => item.public_id)).toEqual(["line-b"]);
    expect(state.lineDetails.loadedFor).toBe("wo-b");
    expect(state.lineDetails.entries.map((item) => item.work_order_line_public_id)).toEqual(["line-b"]);
    expect(state.loading).toBe(false);
  });

  it("marks nothing loaded for a Work Order whose own lists have not answered yet", () => {
    const state = replay(
      { type: "load-started", generation: 1, workOrderPublicId: "wo-a" },
      { type: "work-order-loaded", generation: 1, workOrder: workOrder("wo-a") },
      { type: "lines-loaded", generation: 1, lines: [line("line-a")] },
      { type: "billing-terms", generation: 1, result: { status: "loading" } },
    );
    // Forms are editable only while loadedFor names the Work Order on screen, so nothing is editable.
    expect(state.billingTerms.loadedFor).toBeNull();
  });
});

describe("a save that finishes after a newer load has started", () => {
  it("is discarded, and does not stop the newer load becoming editable", () => {
    const saved = { ...terms("line-a", 2), terms_complete: true };
    const state = replay(
      ...fullLoad(1, "wo-a", "line-a"),
      // Refresh: generation 2 starts while a save from generation 1 is still in flight.
      { type: "load-started", generation: 2, workOrderPublicId: "wo-a" },
      { type: "billing-terms-applied", generation: 1, entry: saved },
      // The refreshed load answers afterwards and must still take effect.
      { type: "billing-terms", generation: 2, result: { status: "loaded", entries: [terms("line-a", 1)] } },
    );
    expect(state.generation).toBe(2);
    expect(state.billingTerms.loadedFor).toBe("wo-a");
    expect(state.billingTerms.entries[0].terms_complete).toBe(false);
  });

  it("is discarded when it belongs to a Work Order that is no longer on screen", () => {
    const state = replay(
      ...fullLoad(1, "wo-a", "line-a"),
      { type: "load-started", generation: 2, workOrderPublicId: "wo-b" },
      { type: "line-detail-saved", generation: 1, detail: detail("line-a", 2) },
    );
    expect(state.lineDetails.entries).toEqual([]);
  });
});

describe("a save in the current load", () => {
  it("replaces that line's entry, leaves the generation alone and keeps the forms editable", () => {
    const state = replay(
      ...fullLoad(3, "wo-a", "line-a"),
      { type: "line-detail-saved", generation: 3, detail: detail("line-a", 2) },
      { type: "billing-terms-applied", generation: 3, entry: terms("line-a", 2) },
    );
    expect(state.generation).toBe(3);
    expect(state.lineDetails.loadedFor).toBe("wo-a");
    expect(state.lineDetails.entries[0].detail_version).toBe(2);
    expect(state.billingTerms.loadedFor).toBe("wo-a");
    expect(state.billingTerms.entries[0].periods).toHaveLength(2);
  });

  it("adds an entry for a line the load did not return one for", () => {
    const state = replay(
      { type: "load-started", generation: 1, workOrderPublicId: "wo-a" },
      { type: "billing-terms", generation: 1, result: { status: "loaded", entries: [] } },
      { type: "billing-terms-applied", generation: 1, entry: terms("line-a", 1) },
    );
    expect(state.billingTerms.entries).toHaveLength(1);
  });
});

describe("a load that fails", () => {
  it("clears the lines and both per-line lists when the Work Order itself fails", () => {
    const state = replay(
      ...fullLoad(1, "wo-a", "line-a"),
      { type: "load-started", generation: 2, workOrderPublicId: "wo-a" },
      { type: "load-failed", generation: 2, error: "Could not load Work Order. HTTP 500." },
    );
    expect(state.workOrder).toBeNull();
    expect(state.lines).toEqual([]);
    expect(state.lineDetails.loadedFor).toBeNull();
    expect(state.billingTerms.loadedFor).toBeNull();
    expect(state.loading).toBe(false);
    expect(state.error).toBe("Could not load Work Order. HTTP 500.");
  });

  it("drops the entries of a list whose own refresh failed, so no form is editable from it", () => {
    const state = replay(
      ...fullLoad(1, "wo-a", "line-a"),
      { type: "load-started", generation: 2, workOrderPublicId: "wo-a" },
      { type: "work-order-loaded", generation: 2, workOrder: workOrder("wo-a") },
      { type: "lines-loaded", generation: 2, lines: [line("line-a")] },
      { type: "billing-terms", generation: 2, result: { status: "failed", error: "Billing terms could not be loaded. HTTP 500." } },
    );
    expect(state.billingTerms).toEqual({ entries: [], loadedFor: null });
    expect(state.billingTermsError).toBe("Billing terms could not be loaded. HTTP 500.");
  });

  it("keeps the Work Order but no lines when only the lines request fails", () => {
    const state = replay(
      { type: "load-started", generation: 1, workOrderPublicId: "wo-a" },
      { type: "work-order-loaded", generation: 1, workOrder: workOrder("wo-a") },
      { type: "lines-failed", generation: 1, error: "Work Order loaded, but lines could not be loaded. HTTP 500." },
    );
    expect(state.workOrder?.public_id).toBe("wo-a");
    expect(state.lines).toEqual([]);
    expect(state.loading).toBe(false);
  });

  it("ignores a failure that belongs to an older load", () => {
    const state = replay(
      ...fullLoad(2, "wo-b", "line-b"),
      { type: "line-details", generation: 1, result: { status: "failed", error: "stale" } },
      { type: "load-failed", generation: 1, error: "stale" },
    );
    expect(state.lineDetails.loadedFor).toBe("wo-b");
    expect(state.lineDetailsError).toBe("");
    expect(state.workOrder?.public_id).toBe("wo-b");
    expect(state.error).toBe("");
  });
});

describe("the side lists", () => {
  it("each show their own loading, entries and error, and ignore an older load's answer", () => {
    const loaded = replay(
      { type: "load-started", generation: 1, workOrderPublicId: "wo-a" },
      { type: "related-offers", generation: 1, result: { status: "loading" } },
      { type: "amendments", generation: 1, result: { status: "failed", error: "Work Order Amendments could not be loaded. HTTP 500." } },
      { type: "handoff-events", generation: 1, result: { status: "loaded", entries: [] } },
    );
    expect(loaded.relatedOffers).toEqual({ entries: [], loading: true, error: "" });
    expect(loaded.amendments.error).toBe("Work Order Amendments could not be loaded. HTTP 500.");
    expect(loaded.handoffEvents).toEqual({ entries: [], loading: false, error: "" });

    const afterNewLoad = workOrderPageReducer(
      { ...loaded, generation: 2 },
      { type: "related-offers", generation: 1, result: { status: "loaded", entries: [{ public_id: "co-9" }] as never } },
    );
    expect(afterNewLoad.relatedOffers.entries).toEqual([]);
  });
});

describe("the holiday list (Slice 7D Part 4)", () => {
  const holidays = (workOrderPublicId: string, version: number) =>
    ({
      work_order_public_id: workOrderPublicId,
      holiday_list_public_id: "hl-1",
      list_version: version,
      holidays_answer_code: "CALENDAR_UNCHANGED",
      changes: [],
      is_complete: true,
      missing_items: [],
    }) as never;

  it("is cleared by a new load, and shows only once its own load has answered", () => {
    const loading = replay(
      { type: "load-started", generation: 1, workOrderPublicId: "wo-a" },
      { type: "holidays", generation: 1, result: { status: "loading" } },
    );
    expect(loading.holidays).toBeNull();
    expect(loading.holidaysLoaded).toBe(false);

    const loaded = workOrderPageReducer(loading, { type: "holidays", generation: 1, result: { status: "loaded", entries: [holidays("wo-a", 1)] } });
    expect(loaded.holidaysLoaded).toBe(true);
    expect(loaded.holidays).toMatchObject({ list_version: 1 });

    const next = workOrderPageReducer(loaded, { type: "load-started", generation: 2, workOrderPublicId: "wo-b" });
    expect(next.holidays).toBeNull();
    expect(next.holidaysLoaded).toBe(false);
  });

  it("drops the list when its load fails, so no form is editable from a failed load", () => {
    const state = replay(
      { type: "load-started", generation: 1, workOrderPublicId: "wo-a" },
      { type: "holidays", generation: 1, result: { status: "loaded", entries: [holidays("wo-a", 1)] } },
      { type: "holidays", generation: 1, result: { status: "failed", error: "The holidays could not be loaded. HTTP 500." } },
    );
    expect(state.holidays).toBeNull();
    expect(state.holidaysLoaded).toBe(false);
    expect(state.holidaysError).toBe("The holidays could not be loaded. HTTP 500.");
  });

  it("applies a save from its own generation, and ignores one from an older load", () => {
    const loaded = replay(
      { type: "load-started", generation: 1, workOrderPublicId: "wo-a" },
      { type: "holidays", generation: 1, result: { status: "loaded", entries: [holidays("wo-a", 1)] } },
    );
    const saved = workOrderPageReducer(loaded, { type: "holidays-applied", generation: 1, holidays: holidays("wo-a", 2) });
    expect(saved.holidays).toMatchObject({ list_version: 2 });
    expect(saved.generation).toBe(1);

    const refreshed = workOrderPageReducer(saved, { type: "load-started", generation: 2, workOrderPublicId: "wo-a" });
    const late = workOrderPageReducer(refreshed, { type: "holidays-applied", generation: 1, holidays: holidays("wo-a", 3) });
    expect(late.holidays).toBeNull();
  });

  it("never shows Work Order A's saved holidays under Work Order B, whenever A's save answers (HOL1-R4-001)", () => {
    const onA = replay(
      { type: "load-started", generation: 1, workOrderPublicId: "wo-a" },
      { type: "holidays", generation: 1, result: { status: "loaded", entries: [holidays("wo-a", 1)] } },
    );
    // A's save is on its way when the user opens B: B's load begins, then A's answer arrives with A's generation.
    const openingB = workOrderPageReducer(onA, { type: "load-started", generation: 2, workOrderPublicId: "wo-b" });
    const lateWhileLoading = workOrderPageReducer(openingB, { type: "holidays-applied", generation: 1, holidays: holidays("wo-a", 2) });
    expect(lateWhileLoading.holidays).toBeNull();
    expect(lateWhileLoading.workOrderPublicId).toBe("wo-b");

    // Or after B's own holidays have loaded: B's stay as they are.
    const onB = workOrderPageReducer(openingB, { type: "holidays", generation: 2, result: { status: "loaded", entries: [holidays("wo-b", 7)] } });
    const lateAfterLoad = workOrderPageReducer(onB, { type: "holidays-applied", generation: 1, holidays: holidays("wo-a", 2) });
    expect(lateAfterLoad).toBe(onB);
    expect(lateAfterLoad.holidays).toMatchObject({ work_order_public_id: "wo-b", list_version: 7 });
  });
});
