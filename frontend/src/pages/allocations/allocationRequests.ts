// The allocation screens' requests (8A core): one way to read and one way to write, so every page handles a missing
// session, a refused session and the server's own refusal alike.

import { SIGN_IN_AGAIN } from "../../components/signInMessages";
import { clearSession, getToken, readErrorDetail } from "../resource-requirements/pageSession";
import type { Assignment, AssignmentAction, Candidates, FinderQuery, KitOptions } from "./allocationState";
import { allPages, finderParams, sortForDisplay } from "./allocationState";

// A refusal keeps the server's status: a 409 says the copy on screen is out of date (8A-FB-006).
export type Sent<T> = { ok: true; body: T } | { ok: false; message: string; status: number | null };

/** A write. Its message, when refused, is the server's own words. */
export async function send<T>(method: "POST" | "PUT", url: string, body: unknown, fallback: string): Promise<Sent<T>> {
  const token = getToken();
  if (!token) return { ok: false, message: SIGN_IN_AGAIN, status: null };
  try {
    const response = await fetch(url, {
      method,
      headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (response.status === 401) {
      clearSession();
      return { ok: false, message: SIGN_IN_AGAIN, status: 401 };
    }
    if (!response.ok) return { ok: false, message: await readErrorDetail(response, fallback), status: response.status };
    return { ok: true, body: (await response.json()) as T };
  } catch {
    return { ok: false, message: `${fallback} Network error: try again.`, status: null };
  }
}

/** A read, for a query controller (certificatesState.ts's createQueryController): throws the words to show. */
async function read<T>(token: string, url: string, fallback: string): Promise<T> {
  const response = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (response.status === 401) {
    clearSession();
    throw new Error(SIGN_IN_AGAIN);
  }
  if (!response.ok) throw new Error(await readErrorDetail(response, fallback));
  return (await response.json()) as T;
}

export const ASSIGNMENTS_URL = "/api/resource-assignments";

export function fetchAssignment(token: string, publicId: string): Promise<Assignment> {
  return read<Assignment>(token, `${ASSIGNMENTS_URL}/${encodeURIComponent(publicId)}`, "The allocation could not be loaded.");
}

/** Every allocation the filters match, page by page (8A-R9-003), each page the ones recorded after the last
 * row of the one before (8A-FB-004), then in the order the screens show them. */
export async function fetchAssignments(token: string, params: URLSearchParams): Promise<Assignment[]> {
  const rows = await allPages<Assignment>(
    (after, limit) => {
      const page = new URLSearchParams(params);
      page.set("limit", String(limit));
      if (after) page.set("after", after.assignment_public_id);
      return read<Assignment[]>(token, `${ASSIGNMENTS_URL}?${page.toString()}`, "The allocations could not be loaded.");
    },
  );
  return sortForDisplay(rows);
}

export function fetchCandidates(token: string, query: FinderQuery): Promise<Candidates> {
  return read<Candidates>(token, `${ASSIGNMENTS_URL}/candidates?${finderParams(query).toString()}`, "The machines could not be found.");
}

export function fetchKitOptions(token: string, publicId: string, tripNumber: number): Promise<KitOptions> {
  return read<KitOptions>(
    token,
    `${ASSIGNMENTS_URL}/${encodeURIComponent(publicId)}/kit-options?trip_number=${tripNumber}`,
    "The kit could not be loaded.",
  );
}

export function sendAction(publicId: string, action: string, method: "POST" | "PUT", body: unknown, fallback: string): Promise<Sent<AssignmentAction>> {
  return send<AssignmentAction>(method, `${ASSIGNMENTS_URL}/${encodeURIComponent(publicId)}/${action}`, body, fallback);
}

/** A key for one form's create request: a double-click or a retry makes one allocation, not two (ADR-023). */
export function newRequestKey(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`;
}
