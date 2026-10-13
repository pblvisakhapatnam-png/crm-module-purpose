// The session and navigation helpers the Resource Requirement pages share. Earlier pages each carry their
// own copy of these; the new pages share one instead of adding three more copies.

import { forgetAlertCount } from "../../components/sessionAlertCount";

const TOKEN_KEY = "pbl_auth_token";
export const SESSION_CHANGED_EVENT = "pbl-session-changed";

type TokenPayload = { role_codes?: unknown; exp?: unknown };

function decodeTokenPayload(token: string): TokenPayload | null {
  const parts = token.split(".");
  if (parts.length !== 3 || !parts[1]) return null;
  try {
    const base64 = parts[1].replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64 + "=".repeat((4 - (base64.length % 4)) % 4);
    return JSON.parse(window.atob(padded)) as TokenPayload;
  } catch {
    return null;
  }
}

export function clearSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(TOKEN_KEY);
  forgetAlertCount(() => window.sessionStorage);
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}

/** The current token, or null when there is none or it has expired (and then the session is cleared). */
export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  const token = window.localStorage.getItem(TOKEN_KEY);
  if (!token) return null;
  const payload = decodeTokenPayload(token);
  const exp = typeof payload?.exp === "number" ? payload.exp : Number(payload?.exp ?? 0);
  if (!payload || !exp || exp * 1000 <= Date.now()) {
    clearSession();
    return null;
  }
  return token;
}

/** The signed-in roles, for hiding actions a role cannot take. The backend is the control, not this. */
export function readRoleCodes(): string[] {
  const token = getToken();
  if (!token) return [];
  const payload = decodeTokenPayload(token);
  return Array.isArray(payload?.role_codes) ? payload!.role_codes.filter((role): role is string => typeof role === "string") : [];
}

// Kept here for the pages that import them from this module; they live in components/returnTarget.ts.
export { readSafeReturnTarget, type ReturnTarget } from "../../components/returnTarget";

export function hrefWithReturnTarget(href: string, returnTo: string, returnLabel: string): string {
  const separator = href.includes("?") ? "&" : "?";
  return `${href}${separator}returnTo=${encodeURIComponent(returnTo)}&returnLabel=${encodeURIComponent(returnLabel)}`;
}

// Kept here for the pages that import it from this module; it lives in components/dateTimeDisplay.ts.
export { formatDateTime } from "../../components/dateTimeDisplay";

// Kept here for the pages that import it from this module; it lives in components/errorDetail.ts.
export { readErrorDetail } from "../../components/errorDetail";
