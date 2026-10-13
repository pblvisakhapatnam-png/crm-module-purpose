import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { ALERT_COUNT_KEY, forgetAlertCount } from "./sessionAlertCount";

const SRC = fileURLToPath(new URL("..", import.meta.url));

function functionBody(file: string, name: string): string {
  const source = readFileSync(`${SRC}${file}`, "utf-8");
  const start = source.indexOf(`export function ${name}(`);
  expect(start, `${name} in ${file}`).toBeGreaterThanOrEqual(0);
  return source.slice(start, source.indexOf("\n}\n", start));
}

describe("the alert count kept per session (TB-1 TB1-802)", () => {
  it("is removed when the session ends", () => {
    const values = new Map<string, string>([[ALERT_COUNT_KEY, "{}"], ["other", "kept"]]);
    forgetAlertCount(() => ({ removeItem: (key: string) => void values.delete(key) }));
    expect(values.has(ALERT_COUNT_KEY)).toBe(false);
    expect(values.get("other")).toBe("kept");
  });

  it("is forgotten quietly when the browser refuses its storage", () => {
    expect(() =>
      forgetAlertCount(() => {
        throw new Error("refused");
      }),
    ).not.toThrow();
  });

  it("is removed by Sign out and by the shared session clearing", () => {
    expect(functionBody("components/useSession.ts", "signOut")).toContain("forgetAlertCount(");
    expect(functionBody("pages/resource-requirements/pageSession.ts", "clearSession")).toContain("forgetAlertCount(");
  });
});
