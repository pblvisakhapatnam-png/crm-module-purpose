// Market rates per offer line (Slice 4G): which rates belong to a line, the line's basis history in words, and where
// a rate's quote copy is attached. Pure functions, so the wording can be tested without rendering the page.

import { formatCurrencyAmount } from "../../components/currency";
import { formatDateTime } from "../../components/dateTimeDisplay";

export type BasisChoice = {
  public_id: string;
  pricing_evidence_public_id: string;
  selection_reason: string;
  chosen_by_display_name?: string | null;
  chosen_at: string;
  ended_by_display_name?: string | null;
  ended_at?: string | null;
  is_current: boolean;
  carried_over_from_version_number?: number | null;
};

export type QuoteCopy = {
  document_public_id: string;
  file_name: string;
  uploaded_at?: string | null;
  attached_to_rate_public_id: string;
  attached_to_line_number?: number | null;
  attached_to_offer_version_number: number;
  attached_here: boolean;
};

export type MarketRate = {
  public_id: string;
  line_public_id?: string | null;
  line_number?: number | null;
  line_status_code?: string | null;
  recorded_for_whole_offer: boolean;
  quote_copy_rate_public_id?: string | null;
  quote_copies: QuoteCopy[];
  basis_history: BasisChoice[];
  evidence_type: string;
  source_name?: string | null;
  vendor_contact?: string | null;
  equipment_service_description: string;
  rate_amount: string;
  currency_code: string;
  rate_basis: string;
  collected_by_name?: string | null;
  collected_at?: string | null;
  source_reference?: string | null;
  is_selected_basis: boolean;
  selection_reason?: string | null;
  comparison_notes?: string | null;
};

export const RATE_TYPE_LABELS: Readonly<Record<string, string>> = {
  market_rate: "Market rate",
  historical_plum_rate: "Historical Plum rate",
};

/** The rates entered for one line, the basis rate first. */
export function ratesForLine(rates: MarketRate[], linePublicId: string): MarketRate[] {
  return rates
    .filter((rate) => !rate.recorded_for_whole_offer && rate.line_public_id === linePublicId)
    .sort((a, b) => Number(b.is_selected_basis) - Number(a.is_selected_basis));
}

/** Rates recorded for the whole offer before rates were kept per line. */
export function wholeOfferRates(rates: MarketRate[]): MarketRate[] {
  return rates.filter((rate) => rate.recorded_for_whole_offer);
}

/** "Sagar Equipment Hire - INR 92,000.00 per day": a rate in one line of words. */
export function rateSummary(rate: MarketRate): string {
  const source = rate.source_name?.trim() || RATE_TYPE_LABELS[rate.evidence_type] || "Rate";
  return `${source} - ${formatCurrencyAmount(rate.rate_amount, rate.currency_code)} ${rate.rate_basis}`;
}

function who(name: string | null | undefined): string {
  return name?.trim() || "an unknown user";
}

/** One basis choice in words. A past choice never reads as current. */
export function basisChoiceText(choice: BasisChoice): string {
  const carried = choice.carried_over_from_version_number
    ? ` (carried over from version ${choice.carried_over_from_version_number})`
    : "";
  if (choice.is_current || !choice.ended_at) {
    return `The basis since ${formatDateTime(choice.chosen_at)}, chosen by ${who(choice.chosen_by_display_name)}${carried}: ${choice.selection_reason}`;
  }
  return (
    `Was the basis until ${formatDateTime(choice.ended_at)}, chosen by ${who(choice.chosen_by_display_name)} ` +
    `on ${formatDateTime(choice.chosen_at)}${carried}: ${choice.selection_reason}`
  );
}

export type LineBasisHistoryEntry = { rate: MarketRate; choice: BasisChoice };

/** Every basis choice on a line, newest first, each with the rate it chose. */
export function lineBasisHistory(lineRates: MarketRate[]): LineBasisHistoryEntry[] {
  return lineRates
    .flatMap((rate) => rate.basis_history.map((choice) => ({ rate, choice })))
    .sort((a, b) => (a.choice.chosen_at < b.choice.chosen_at ? 1 : a.choice.chosen_at > b.choice.chosen_at ? -1 : 0));
}

/** Where a quote copy is attached, when it is not on this rate itself. */
export function quoteCopyPlace(copy: QuoteCopy, currentVersionNumber: number | null | undefined): string {
  if (copy.attached_here) return "";
  const line = copy.attached_to_line_number ? `line ${copy.attached_to_line_number}'s rate` : "a rate for the whole offer";
  if (currentVersionNumber && copy.attached_to_offer_version_number !== currentVersionNumber) {
    return `Attached to ${line} on version ${copy.attached_to_offer_version_number}`;
  }
  return `Attached to ${line}`;
}

/**
 * Which of the lines' market-rate panels Jump to should go to (owner's screen check, Slice 4G): the first whose start
 * is on screen; else the one the screen is inside; else the nearest one above or below. The tail of the previous
 * line's panel at the top of the screen does not count, so a reader looking at line 4 goes to line 4's rates.
 * `panels` are their positions relative to the window, in page order; -1 when there are none.
 */
export function nearestPanelIndex(panels: Array<{ top: number; bottom: number }>, viewportHeight: number): number {
  const startsOnScreen = panels.findIndex((panel) => panel.top >= 0 && panel.top < viewportHeight);
  if (startsOnScreen >= 0) return startsOnScreen;
  const inside = panels.findIndex((panel) => panel.top < 0 && panel.bottom > 0);
  if (inside >= 0) return inside;
  let nearest = -1;
  let nearestDistance = Number.POSITIVE_INFINITY;
  panels.forEach((panel, index) => {
    const distance = panel.top >= viewportHeight ? panel.top - viewportHeight : -panel.bottom;
    if (distance < nearestDistance) {
      nearest = index;
      nearestDistance = distance;
    }
  });
  return nearest;
}

/** The rates of this offer a new rate may refer to for its quote copy: those that have a quote to share. */
export function quoteCopyChoices(rates: MarketRate[]): Array<{ value: string; label: string }> {
  return rates
    .filter((rate) => !rate.recorded_for_whole_offer && rate.quote_copies.length > 0)
    .sort((a, b) => (a.line_number ?? 0) - (b.line_number ?? 0))
    .map((rate) => ({ value: rate.public_id, label: `Line ${rate.line_number}: ${rateSummary(rate)}` }));
}
