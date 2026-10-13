import { readdirSync, readFileSync } from "node:fs";
import { join, relative } from "node:path";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  currencyChoices,
  DEFAULT_CURRENCY,
  formatCurrencyAmount,
  formatCurrencyTotals,
  isOperatingCurrency,
  OPERATING_CURRENCIES,
  UNSUPPORTED_CURRENCY_MESSAGE,
} from "./currency";

// TB1-600: an amount is recorded only in a currency on the one list, chosen from CurrencySelect. The currency boxes
// were once free text that took any three letters; this fails when a page adds one again.

const SRC = fileURLToPath(new URL("..", import.meta.url));

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.tsx$/.test(entry.name) && !/\.test\.tsx$/.test(entry.name) ? [path] : [];
  });
}

/** Whether source text has a free-text box for a currency: an <input ... /> whose attributes mention a currency. */
function hasCurrencyTextBox(text: string): boolean {
  return (text.match(/<input\b[\s\S]*?\/>/g) ?? []).some((input) => /currency/i.test(input));
}

describe("the currency list", () => {
  it("is INR first, INR by default, and the same four codes the backend holds", () => {
    // backend/app/shared/currency.py holds the same list; a currency is added in both.
    expect(OPERATING_CURRENCIES.map((currency) => currency.code)).toEqual(["INR", "USD", "GBP", "EUR"]);
    expect(DEFAULT_CURRENCY).toBe("INR");
    expect(UNSUPPORTED_CURRENCY_MESSAGE).toBe("Currency must be one of INR, USD, GBP, EUR.");
    expect(isOperatingCurrency("USD")).toBe(true);
    expect(isOperatingCurrency("AUD")).toBe(false);
  });

  it("offers the four, and an older record's other code marked, so the screen shows what is stored", () => {
    expect(currencyChoices("INR").map((choice) => choice.value)).toEqual(["INR", "USD", "GBP", "EUR"]);
    const withOlder = currencyChoices("XYZ");
    expect(withOlder.map((choice) => choice.value)).toEqual(["INR", "USD", "GBP", "EUR", "XYZ"]);
    expect(withOlder[4].label).toContain("no longer offered");
  });
});

describe("report totals", () => {
  it("show a single INR amount where everything is in INR", () => {
    const shown = formatCurrencyTotals([{ currency_code: "INR", amount: "1234567.00" }]);
    expect(shown).toBe(formatCurrencyAmount("1234567.00", "INR"));
    expect(shown).not.toContain("·");
    expect(shown).toContain("12,34,567");
  });

  it("show each currency separately, never added together", () => {
    const shown = formatCurrencyTotals([
      { currency_code: "INR", amount: "1000" },
      { currency_code: "USD", amount: "50" },
    ]);
    expect(shown.split(" · ")).toEqual([formatCurrencyAmount("1000", "INR"), formatCurrencyAmount("50", "USD")]);
  });

  it("show a code the browser does not know as text rather than failing", () => {
    expect(formatCurrencyAmount("100", "X1")).toBe("X1 100");
    expect(formatCurrencyAmount(null, "INR")).toBe("-");
    expect(formatCurrencyTotals([])).toBe("-");
  });
});

describe("currency boxes", () => {
  it("are recognised however the input is written", () => {
    expect(hasCurrencyTextBox('<input\n  value={form.currency_code}\n  maxLength={3}\n/>')).toBe(true);
    expect(hasCurrencyTextBox("<input value={x} onChange={(e) => setCurrencyCode(e.target.value)} />")).toBe(true);
    expect(hasCurrencyTextBox("<CurrencySelect value={form.currency_code} onChange={setCode} />")).toBe(false);
    expect(hasCurrencyTextBox('<input value={form.rate_basis} />')).toBe(false);
  });

  it("every currency box in the application is a CurrencySelect", () => {
    const files = sourceFiles(SRC);
    expect(files.length).toBeGreaterThan(50);
    const textBoxes = files.filter((file) => hasCurrencyTextBox(readFileSync(file, "utf-8"))).map((file) => relative(SRC, file));
    expect(textBoxes).toEqual([]);
  });
});
