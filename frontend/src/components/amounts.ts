// How a page checks an amount before sending it, held to the server's own limits so the person is told which field to
// correct instead of getting the server's list of field errors. Moved here from
// pages/work-orders/workOrderBillingTermsState.ts, which re-exports both; amountProblem gained `zeroAllowed` for the
// amounts the server accepts at 0 (TB-1 finding TB1-801).

/**
 * A number's digits before and after the decimal point, as the server counts them: leading zeros of the
 * whole part and trailing zeros of the fraction do not count. Exponent notation ("1e3", "1.5e-2") is
 * written out first, because a browser number field accepts it and the server reads it as the plain
 * number (review round 3, finding F-07). Null when the text is not a number in either form.
 */
export function decimalDigits(value: string): { whole: string; fraction: string } | null {
  const match = /^\+?(\d*)(?:\.(\d*))?(?:[eE]([+-]?\d+))?$/.exec(value);
  if (!match || (match[1] ?? "") + (match[2] ?? "") === "") return null;
  const digits = (match[1] ?? "") + (match[2] ?? "");
  const point = (match[1] ?? "").length + Number(match[3] ?? "0");
  let whole: string;
  let fraction: string;
  if (point <= 0) {
    whole = "";
    fraction = "0".repeat(-point) + digits;
  } else if (point >= digits.length) {
    whole = digits + "0".repeat(point - digits.length);
    fraction = "";
  } else {
    whole = digits.slice(0, point);
    fraction = digits.slice(point);
  }
  return { whole: whole.replace(/^0+/, ""), fraction: fraction.replace(/0+$/, "") };
}

/**
 * Why an amount the server would refuse cannot be sent, naming the field, or null. Blank is not a problem:
 * it is reported missing, not refused. Plain and exponent forms are held to the same limits. An amount must
 * be greater than 0 unless `zeroAllowed`, for the amounts the server accepts at 0.
 */
export function amountProblem(label: string, value: string, wholeDigits: number, zeroAllowed = false): string | null {
  const trimmed = value.trim();
  if (trimmed === "") return null;
  const number = Number(trimmed);
  if (!Number.isFinite(number)) return `${label} must be a number.`;
  if (zeroAllowed && number < 0) return `${label} must be 0 or more.`;
  if (!zeroAllowed && number <= 0) return `${label} must be greater than 0.`;
  const digits = decimalDigits(trimmed);
  if (!digits) return `${label} must be a number.`;
  if (digits.fraction.length > 2) return `${label} can have at most 2 decimal places.`;
  if (digits.whole.length > wholeDigits) return `${label} is larger than can be recorded.`;
  return null;
}
