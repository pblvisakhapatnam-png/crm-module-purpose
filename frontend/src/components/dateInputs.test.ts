import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { DATE_INPUT_MAX, DATE_TIME_INPUT_MAX } from "./DateInput";

// Every date box goes through DateInput, which stops the year at four digits. The limit was once added page by
// page and most pages were missed (owner's screen checks, 22 and 28 September 2026); this fails when a page adds
// a plain date or date-and-time box again.

const SRC = fileURLToPath(new URL("..", import.meta.url));

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name) ? [path] : [];
  });
}

/** Whether source text has a plain date or date-and-time box: type="date", type={"datetime-local"} and so on. */
function hasPlainDateBox(text: string): boolean {
  return /\btype\s*=\s*(?:\{\s*)?["'`](?:date|datetime-local)["'`]/.test(text);
}

describe("date boxes", () => {
  it("are recognised however the type is written", () => {
    expect(hasPlainDateBox('<input type="date" value={day} />')).toBe(true);
    expect(hasPlainDateBox("<input type='datetime-local' />")).toBe(true);
    expect(hasPlainDateBox('<input type={"date"} />')).toBe(true);
    expect(hasPlainDateBox('<DateInput value={day} />')).toBe(false);
    expect(hasPlainDateBox('<input type="text" />')).toBe(false);
  });

  it("every date and date-and-time box in the application is a DateInput", () => {
    const files = sourceFiles(SRC).filter((file) => !file.endsWith(join("components", "DateInput.tsx")));
    expect(files.length).toBeGreaterThan(50);
    const plain = files.filter((file) => hasPlainDateBox(readFileSync(file, "utf-8"))).map((file) => relative(SRC, file));
    expect(plain).toEqual([]);
  });

  it("stops the year at four digits", () => {
    expect(DATE_INPUT_MAX).toBe("9999-12-31");
    expect(DATE_TIME_INPUT_MAX).toBe("9999-12-31T23:59");
  });
});
