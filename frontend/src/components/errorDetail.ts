// How a page reads the server's refusal into words. FastAPI words a refusal of the request itself as a list of field
// errors, not a sentence; six CRM actions once put that list on screen as it came, and React replaced the whole page
// with an error screen (TB-1 finding TB1-801). Moved here unchanged from pages/resource-requirements/pageSession.ts,
// which re-exports it.

/** The server's refusal, worded by the server where it gave words. */
export async function readErrorDetail(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: unknown };
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) return "Check the values entered: one of them is not accepted.";
  } catch {
    // fall through
  }
  return `${fallback} HTTP ${response.status}.`;
}
