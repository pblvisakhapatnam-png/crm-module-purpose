// A converted Lead is final: its details and qualification decision can no longer change, and its work continues on
// the Account and Opportunity it became (TB-1 finding TB1-302, 4 October 2026), as the server enforces.
export const CONVERTED_LEAD_NOTE =
  "This Lead has been converted, so its details and qualification decision can no longer be changed. Work continues on its Account and Opportunity.";

/** Whether the Lead's details and qualification decision may still be changed. */
export function leadCanBeChanged(statusCode: string): boolean {
  return statusCode !== "CONVERTED";
}
