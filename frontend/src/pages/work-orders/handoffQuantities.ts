// What the Create Work Order page offers for each offer line (TB-1 CS-04 part 1: an offer line's quantity goes onto
// Work Orders once, whole or in parts). The server counts what each line has left, in one statement, in the offer's
// lifecycle view (`line_handoff`, review round 2); the page only checks what is typed against it. Quantities are
// NUMERIC(18,2) - up to 16 whole digits, past the integers a JavaScript number holds exactly - so they are compared as
// whole hundredths in a bigint, never as a number (review round 1).

import { amountProblem, decimalDigits } from "../../components/amounts";

/** One active offer line as the lifecycle view counts it; quantities arrive as decimal strings. */
export type LineHandoff = {
  offer_line_public_id: string;
  line_number: number;
  quantity: string;
  quantity_on_work_orders: string;
  quantity_left: string;
  work_orders: { work_order_public_id: string; work_order_code: string | null; quantity: string }[];
};

/** A quantity in hundredths, or null when it is not a number with at most two decimals. Exponent notation is read as
 * the server reads it (`decimalDigits`). */
export function toHundredths(value: string | number | null | undefined): bigint | null {
  const digits = decimalDigits(String(value ?? "").trim());
  if (!digits || digits.fraction.length > 2) return null;
  return BigInt(digits.whole || "0") * BigInt(100) + BigInt(digits.fraction.padEnd(2, "0"));
}

/** Hundredths written as the plain number they stand for: 150 as "1.5", 1000 as "10". */
export function formatHundredths(value: bigint): string {
  const sign = value < BigInt(0) ? "-" : "";
  const size = value < BigInt(0) ? -value : value;
  const whole = (size / BigInt(100)).toString();
  const fraction = (size % BigInt(100)).toString().padStart(2, "0").replace(/0+$/, "");
  return sign + (fraction ? `${whole}.${fraction}` : whole);
}

/** What the server says is left of a line, in hundredths; nothing when it has no entry for the line. */
export function hundredthsLeft(entry: LineHandoff | undefined): bigint {
  return entry ? (toHundredths(entry.quantity_left) ?? BigInt(0)) : BigInt(0);
}

/** The Work Orders holding a line, as "WO-1 (6), WO-2 (4)". */
export function describeHoldings(entry: LineHandoff | undefined): string {
  return (entry?.work_orders ?? [])
    .map((part) => {
      const quantity = toHundredths(part.quantity);
      return `${part.work_order_code ?? part.work_order_public_id} (${quantity === null ? part.quantity : formatHundredths(quantity)})`;
    })
    .join(", ");
}

/** The page's starting choice: every active line with something left is ticked, for all that is left. */
export function startingChoice(
  activeLineIds: string[],
  lineHandoff: LineHandoff[],
): { selected: string[]; quantities: Record<string, string> } {
  const byLine = new Map(lineHandoff.map((entry) => [entry.offer_line_public_id, entry]));
  const selected = activeLineIds.filter((lineId) => hundredthsLeft(byLine.get(lineId)) > BigInt(0));
  return {
    selected,
    quantities: Object.fromEntries(selected.map((lineId) => [lineId, formatHundredths(hundredthsLeft(byLine.get(lineId)))])),
  };
}

/** Why a typed quantity cannot be sent for a line, or null: above 0, at most 2 decimals and 16 whole digits (as the
 * server's column), and no more than the server says is left. */
export function quantityProblem(lineNumber: number, typed: string, entry: LineHandoff | undefined): string | null {
  const label = `Line ${lineNumber}'s quantity`;
  if (typed.trim() === "") return `${label} is required.`;
  const problem = amountProblem(label, typed, 16);
  if (problem) return problem;
  const left = hundredthsLeft(entry);
  return (toHundredths(typed) ?? BigInt(0)) > left ? `Line ${lineNumber} has ${formatHundredths(left)} left to hand off.` : null;
}
