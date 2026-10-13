import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { afterEach, describe, expect, it } from "vitest";

import { formatDateTime } from "./dateTimeDisplay";
import { apiDateTimeToIndiaInput, enteredIndiaTimeToUtc, nowAsIndiaInput } from "./enteredDateTime";

// The entered-time fix (October 2026): a market rate's "Collected at" typed as 10:30 showed 4:00 pm, because the offer
// page sent the typed India time with no zone and the API stored it as UTC. These fail if a typed time is sent so that
// it comes back shifted, or if a page with a date-and-time box sends its value some other way.

const SRC = fileURLToPath(new URL("..", import.meta.url));
const BROWSER_ZONE = process.env.TZ;

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name) ? [path] : [];
  });
}

/** What the API sends back for a moment it was given: UTC, without a zone (the CRM tables' times). */
function asTheApiReturnsIt(sent: string): string {
  return sent.replace(/\.\d{3}Z$/, "");
}

afterEach(() => {
  if (BROWSER_ZONE === undefined) delete process.env.TZ;
  else process.env.TZ = BROWSER_ZONE;
});

describe("enteredIndiaTimeToUtc", () => {
  it("sends 10:30 typed in India as the same moment in UTC, with its zone", () => {
    expect(enteredIndiaTimeToUtc("2026-10-12T10:30")).toBe("2026-10-12T05:00:00.000Z");
    expect(enteredIndiaTimeToUtc(" 2026-10-12T10:30:15 ")).toBe("2026-10-12T05:00:15.000Z");
  });

  it("comes back on screen as the time typed, not 5 hours 30 minutes later", () => {
    const shown = formatDateTime(asTheApiReturnsIt(enteredIndiaTimeToUtc("2026-10-12T10:30") ?? ""));
    expect(shown).toMatch(/12 Oct 2026, 10:30\s?am/i);
    // What the offer page used to send - the typed time with ":00" and no zone - shows 4:00 pm.
    expect(formatDateTime("2026-10-12T10:30:00")).toMatch(/0?4:00\s?pm/i);
  });

  it("keeps India's day when UTC is still on the day before", () => {
    expect(enteredIndiaTimeToUtc("2026-10-12T00:30")).toBe("2026-10-11T19:00:00.000Z");
    expect(formatDateTime(asTheApiReturnsIt("2026-10-11T19:00:00.000Z"))).toMatch(/12 Oct 2026, 12:30\s?am/i);
  });

  it("reads the typed time as India's whatever the browser's own zone", () => {
    process.env.TZ = "America/New_York";
    expect(enteredIndiaTimeToUtc("2026-10-12T10:30")).toBe("2026-10-12T05:00:00.000Z");
    process.env.TZ = "UTC";
    expect(enteredIndiaTimeToUtc("2026-10-12T10:30")).toBe("2026-10-12T05:00:00.000Z");
  });

  it("gives nothing for an empty box or anything that is not a date and time", () => {
    expect(enteredIndiaTimeToUtc("")).toBeNull();
    expect(enteredIndiaTimeToUtc("   ")).toBeNull();
    expect(enteredIndiaTimeToUtc("2026-10-12")).toBeNull();
    expect(enteredIndiaTimeToUtc("2026-10-12T10:30Z")).toBeNull();
    expect(enteredIndiaTimeToUtc("tomorrow")).toBeNull();
  });
});

describe("apiDateTimeToIndiaInput and nowAsIndiaInput", () => {
  it("puts a saved time back into a box as India's time", () => {
    expect(apiDateTimeToIndiaInput("2026-10-12T05:00:00")).toBe("2026-10-12T10:30");
    expect(apiDateTimeToIndiaInput("2026-10-12T05:00:00Z")).toBe("2026-10-12T10:30");
    expect(apiDateTimeToIndiaInput("2026-10-11T19:00:00+00:00")).toBe("2026-10-12T00:30");
    expect(apiDateTimeToIndiaInput(null)).toBe("");
    expect(apiDateTimeToIndiaInput("not a date")).toBe("");
  });

  it("a saved time put back into a box and saved again is the same moment", () => {
    expect(enteredIndiaTimeToUtc(apiDateTimeToIndiaInput("2026-10-12T05:00:00"))).toBe("2026-10-12T05:00:00.000Z");
  });

  it("starts a box at now in India", () => {
    process.env.TZ = "America/New_York";
    expect(nowAsIndiaInput(new Date("2026-10-11T19:00:00Z"))).toBe("2026-10-12T00:30");
  });
});

describe("date-and-time boxes", () => {
  it("every page sends each of its date-and-time boxes through enteredIndiaTimeToUtc", () => {
    // Counted per file: a page with more boxes than calls has a box whose value goes out some other way. It cannot see
    // which call takes which box; the screen check and Playwright see that.
    const count = (text: string, pattern: RegExp) => text.match(pattern)?.length ?? 0;
    const files = sourceFiles(SRC).filter((file) => !/[\\/](?:DateInput\.tsx|enteredDateTime\.ts)$/.test(file));
    const boxes = files
      .map((file) => ({ file, text: readFileSync(file, "utf-8") }))
      .map(({ file, text }) => ({
        file: relative(SRC, file),
        boxes: count(text, /\bwithTime\b/g),
        sent: count(text, /\benteredIndiaTimeToUtc\(/g),
      }))
      .filter((page) => page.boxes > 0);
    expect(boxes.reduce((total, page) => total + page.boxes, 0)).toBeGreaterThanOrEqual(8);
    expect(boxes.filter((page) => page.sent < page.boxes)).toEqual([]);
  });

  it("no page keeps its own way of sending a typed time", () => {
    const own = sourceFiles(SRC)
      .filter((file) => /\b(?:formatCollectedDateTimeInput|datetimeLocalToIso|nowAsDatetimeLocal)\b/.test(readFileSync(file, "utf-8")))
      .map((file) => relative(SRC, file));
    expect(own).toEqual([]);
  });
});
