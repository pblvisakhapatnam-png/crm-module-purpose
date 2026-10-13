// Whether the left menu is shown. The frontend has no component-test capability yet
// (docs/agent/DEFERRED_REQUIREMENTS.md), so the rule is tested here and the button by the screen check.

import { describe, expect, it } from "vitest";

import { MENU_SHOWN_KEY, readMenuShown, writeMenuShown } from "./menuPreference";

function memoryStore(initial: Record<string, string> = {}) {
  const values = new Map(Object.entries(initial));
  return {
    values,
    getItem: (key: string) => values.get(key) ?? null,
    setItem: (key: string, value: string) => {
      values.set(key, value);
    },
  };
}

function refusedStore(): never {
  throw new Error("SecurityError: storage is disabled");
}

describe("the left menu", () => {
  it("is shown beside the page on a desktop, and hidden where it would stack above it, until the user chooses", () => {
    expect(readMenuShown(() => memoryStore(), false)).toBe(true);
    expect(readMenuShown(() => memoryStore(), true)).toBe(false);
  });

  it("keeps the user's choice, whatever the width", () => {
    const store = memoryStore();
    writeMenuShown(() => store, false);
    expect(store.values.get(MENU_SHOWN_KEY)).toBe("false");
    expect(readMenuShown(() => store, false)).toBe(false);

    writeMenuShown(() => store, true);
    expect(readMenuShown(() => store, true)).toBe(true);
  });

  it("ignores a stored value it did not write", () => {
    // Both widths: at the desktop width the default is itself `true`, so a reading that wrongly
    // accepted any stored value would pass there. The stacked width is what distinguishes them.
    expect(readMenuShown(() => memoryStore({ [MENU_SHOWN_KEY]: "maybe" }), false)).toBe(true);
    expect(readMenuShown(() => memoryStore({ [MENU_SHOWN_KEY]: "maybe" }), true)).toBe(false);
  });

  it("falls back to the default, and never throws, when the browser refuses its storage", () => {
    expect(readMenuShown(refusedStore, false)).toBe(true);
    expect(readMenuShown(refusedStore, true)).toBe(false);
    expect(() => writeMenuShown(refusedStore, false)).not.toThrow();

    const failingReads = { getItem: refusedStore, setItem: () => undefined };
    expect(readMenuShown(() => failingReads, false)).toBe(true);
    expect(readMenuShown(() => failingReads, true)).toBe(false);

    const failingWrites = { getItem: () => null, setItem: refusedStore };
    expect(() => writeMenuShown(() => failingWrites, true)).not.toThrow();
  });
});
