/**
 * The currencies an amount may be recorded in. INR is the default and the operating currency (Q-08, ADR-023); the
 * others are kept for future work in neighbouring countries (owner's decision, 4 October 2026, TB1-600).
 *
 * The backend holds the same list in backend/app/shared/currency.py and refuses any other code: add a currency in
 * both places.
 */
export const DEFAULT_CURRENCY = "INR";

export const OPERATING_CURRENCIES = [
  { code: "INR", name: "Indian rupee" },
  { code: "USD", name: "US dollar" },
  { code: "GBP", name: "Pound sterling" },
  { code: "EUR", name: "Euro" },
] as const;

export const UNSUPPORTED_CURRENCY_MESSAGE = `Currency must be one of ${OPERATING_CURRENCIES.map((c) => c.code).join(", ")}.`;

export function isOperatingCurrency(code: string): boolean {
  return OPERATING_CURRENCIES.some((currency) => currency.code === code);
}

/**
 * The choices to offer, as value and label. A record saved before the list existed may hold another code; it is
 * offered too, marked, so the screen shows what is stored instead of quietly showing INR.
 */
export function currencyChoices(current?: string | null): Array<{ value: string; label: string }> {
  const choices: Array<{ value: string; label: string }> = OPERATING_CURRENCIES.map(({ code, name }) => ({
    value: code,
    label: `${code} - ${name}`,
  }));
  if (current && !isOperatingCurrency(current)) {
    choices.push({ value: current, label: `${current} - no longer offered` });
  }
  return choices;
}

export type CurrencyTotal = { currency_code: string; amount: string | number };

/** An amount in its own currency, whole units, Indian digit grouping. */
export function formatCurrencyAmount(value: string | number | null | undefined, currencyCode: string): string {
  if (value === null || value === undefined || value === "") return "-";
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return "-";
  try {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: currencyCode, maximumFractionDigits: 0 }).format(parsed);
  } catch {
    // A code Intl does not accept (an older record); show it as text rather than fail the page.
    return `${currencyCode} ${parsed.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
  }
}

/**
 * A report's totals, one per currency, never converted or added together. The backend always sends INR first and
 * adds another currency only when a record is in it, so where everything is in INR this shows a single INR amount.
 */
export function formatCurrencyTotals(totals: CurrencyTotal[] | null | undefined): string {
  if (!totals || totals.length === 0) return "-";
  return totals.map((total) => formatCurrencyAmount(total.amount, total.currency_code)).join(" · ");
}
