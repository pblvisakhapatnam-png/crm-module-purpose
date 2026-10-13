import { describe, expect, it } from "vitest";

import {
  EMPTY_LOADED_LIST,
  canEditLine,
  createLatestGate,
  isUserToggle,
  lineCardOpen,
  listLoadFailed,
  listLoaded,
  listWhileLoading,
  upsertLineDetail,
} from "./workOrderLineDetailState";

const line = (id: string, version: number | null) => ({ work_order_line_public_id: id, detail_version: version });

describe("upsertLineDetail", () => {
  it("replaces the saved line's entry in place", () => {
    const result = upsertLineDetail([line("a", 1), line("b", null)], line("a", 2));
    expect(result).toEqual([line("a", 2), line("b", null)]);
  });

  it("adds the saved entry when the page does not hold it yet, instead of dropping it", () => {
    expect(upsertLineDetail([], line("a", 1))).toEqual([line("a", 1)]);
  });

  it("does not mutate the list it was given", () => {
    const current = [line("a", 1)];
    upsertLineDetail(current, line("a", 2));
    expect(current).toEqual([line("a", 1)]);
  });
});

describe("canEditLine", () => {
  it("refuses editing before the line details have loaded", () => {
    expect(canEditLine(false, undefined)).toBe(false);
    expect(canEditLine(false, line("a", 3))).toBe(false);
  });

  it("refuses editing a line whose entry is missing even after loading", () => {
    expect(canEditLine(true, undefined)).toBe(false);
  });

  it("allows editing once the entry is present, including a line never saved", () => {
    expect(canEditLine(true, line("a", null))).toBe(true);
    expect(canEditLine(true, line("a", 4))).toBe(true);
  });
});

describe("loaded list state", () => {
  const editable = (state: { entries: { work_order_line_public_id: string }[]; loadedFor: string | null }, workOrder: string) =>
    canEditLine(state.loadedFor === workOrder, state.entries[0]);

  it("makes nothing editable while a refresh is running", () => {
    const loaded = listLoaded("wo-1", [line("a", 2)]);
    expect(editable(loaded, "wo-1")).toBe(true);
    expect(editable(listWhileLoading(loaded), "wo-1")).toBe(false);
  });

  it("after a successful load, a failed refresh leaves no stale entry shown as loaded or editable", () => {
    const refreshing = listWhileLoading(listLoaded("wo-1", [line("a", 2)]));
    const failed = listLoadFailed<ReturnType<typeof line>>();
    expect(failed).toEqual({ entries: [], loadedFor: null });
    expect(editable(failed, "wo-1")).toBe(false);
    expect(refreshing.loadedFor).toBeNull();
  });

  it("a new Work Order load clears what an earlier successful load left, so nothing stays editable", () => {
    // WorkOrderDetailPage resets both lists to EMPTY_LOADED_LIST when a load starts, before the lines
    // request that can fail and skip the line-detail and billing-term loads (review round 4).
    const earlier = listLoaded("wo-1", [line("a", 2)]);
    expect(editable(earlier, "wo-1")).toBe(true);
    const reset = EMPTY_LOADED_LIST as typeof earlier;
    expect(editable(reset, "wo-1")).toBe(false);
    expect(reset.entries.find((entry) => entry.work_order_line_public_id === "a")).toBeUndefined();
  });

  it("starts empty and not loaded", () => {
    expect(EMPTY_LOADED_LIST).toEqual({ entries: [], loadedFor: null });
  });
});

describe("createLatestGate", () => {
  it("lets a list load apply when nothing newer has happened", () => {
    const gate = createLatestGate();
    const load = gate.begin();
    expect(gate.isLatest(load)).toBe(true);
  });

  it("stops a load that started before a save from overwriting that save", () => {
    const gate = createLatestGate();
    const slowLoad = gate.begin();
    gate.begin(); // a save is applied while the load is still in flight
    expect(gate.isLatest(slowLoad)).toBe(false);
  });

  it("lets only the newest of two overlapping loads apply", () => {
    const gate = createLatestGate();
    const first = gate.begin();
    const second = gate.begin();
    expect(gate.isLatest(first)).toBe(false);
    expect(gate.isLatest(second)).toBe(true);
  });
});

describe("lineCardOpen", () => {
  it("shows an incomplete or not-yet-loaded line open, and a complete line closed, by default", () => {
    expect(lineCardOpen(null, false)).toBe(true);
    expect(lineCardOpen(null, undefined)).toBe(true);
    expect(lineCardOpen(null, true)).toBe(false);
  });

  it("keeps the user's choice even when completeness changes", () => {
    expect(lineCardOpen(true, true)).toBe(true);
    expect(lineCardOpen(false, false)).toBe(false);
  });
});

describe("isUserToggle", () => {
  it("ignores the toggle the page caused by setting open itself", () => {
    expect(isUserToggle(true, true)).toBe(false);
    expect(isUserToggle(false, false)).toBe(false);
  });

  it("records a change away from what the page was showing", () => {
    expect(isUserToggle(false, true)).toBe(true);
    expect(isUserToggle(true, false)).toBe(true);
  });
});
