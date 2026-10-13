import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { readErrorDetail } from "./errorDetail";

// TB-1 finding TB1-801: six CRM actions put the server's refusal on screen as it came. FastAPI words a refusal of the
// request itself as a list of field errors, and React, given a list of objects to show, replaced the whole page with
// an error screen. Every refusal is now read into words; this fails when a page passes the server's detail on unread.

const SRC = fileURLToPath(new URL("..", import.meta.url));

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(entry.name) && !/\.test\.tsx?$/.test(entry.name) ? [path] : [];
  });
}

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });
}

describe("readErrorDetail", () => {
  it("gives the server's own words when it gave a sentence", async () => {
    const response = jsonResponse(409, { detail: "This amendment is no longer open for changes." });
    expect(await readErrorDetail(response, "Could not add the amendment line.")).toBe("This amendment is no longer open for changes.");
  });

  it("turns FastAPI's list of field errors into a sentence, never the list itself", async () => {
    // The shape FastAPI sends when a field is refused: typing "1,00,000" as an offer value.
    const response = jsonResponse(422, {
      detail: [{ type: "decimal_parsing", loc: ["body", "offer_value"], msg: "Input should be a valid decimal", input: "1,00,000" }],
    });
    const text = await readErrorDetail(response, "Could not create the related Commercial Offer.");
    expect(typeof text).toBe("string");
    expect(text).toBe("Check the values entered: one of them is not accepted.");
  });

  it("falls back to the page's own words, with the status, when the answer has no words or is not JSON", async () => {
    expect(await readErrorDetail(jsonResponse(500, {}), "Could not create the Work Order.")).toBe("Could not create the Work Order. HTTP 500.");
    expect(await readErrorDetail(jsonResponse(400, { detail: { code: "X" } }), "Nothing was saved.")).toBe("Nothing was saved. HTTP 400.");
    const plain = new Response("Internal Server Error", { status: 502, headers: { "Content-Type": "text/plain" } });
    expect(await readErrorDetail(plain, "Could not remove the amendment line.")).toBe("Could not remove the amendment line. HTTP 502.");
  });
});

describe("server refusals on screen", () => {
  it("no page passes the server's detail on without reading it into words", () => {
    const files = sourceFiles(SRC);
    expect(files.length).toBeGreaterThan(50);
    // `body?.detail || "..."` and `body.detail ?? "..."` hand a list of objects to the screen as readily as a sentence.
    const unread = files.filter((file) => /\.detail\s*(\|\||\?\?)/.test(readFileSync(file, "utf-8"))).map((file) => relative(SRC, file));
    expect(unread).toEqual([]);
  });
});
