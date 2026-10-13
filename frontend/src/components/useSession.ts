import { useEffect, useState } from "react";

import { forgetAlertCount } from "./sessionAlertCount";
import { signedInUserFromResponse, userForToken, type ResolvedSessionUser, type SignedInUser } from "./sessionUser";

// The session in this browser, for the menu's Session panel and the sign-in page: whether one is in use, and
// whose it is. Moved here from SessionActions so the sign-in page can offer Sign out while someone is signed in
// (owner, 27 September 2026).

const TOKEN_KEY = "pbl_auth_token";
const SESSION_CHANGED_EVENT = "pbl-session-changed";
const VIEWED_ACCOUNT_IDS_KEY = "pbl_viewed_account_ids_this_session";
const VIEWED_OPPORTUNITY_IDS_KEY = "pbl_viewed_opportunity_ids_this_session";

type TokenPayload = {
  exp?: unknown;
};

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

function tokenIsUsable(token: string): boolean {
  const payload = decodeTokenPayload(token);
  if (!payload) return false;

  const exp = typeof payload.exp === "number" ? payload.exp : Number(payload.exp ?? 0);
  if (!exp) return false;

  return exp * 1000 > Date.now();
}

/** Sign out in this browser: forget the session and what was viewed under it, and tell every page. */
export function signOut() {
  if (typeof window === "undefined") return;

  window.localStorage.removeItem(TOKEN_KEY);
  window.sessionStorage.removeItem(VIEWED_ACCOUNT_IDS_KEY);
  window.sessionStorage.removeItem(VIEWED_OPPORTUNITY_IDS_KEY);
  forgetAlertCount(() => window.sessionStorage);
  window.dispatchEvent(new Event(SESSION_CHANGED_EVENT));
}

function readUsableToken(): string | null {
  if (typeof window === "undefined") return null;

  const token = window.localStorage.getItem(TOKEN_KEY);
  if (!token) return null;

  if (!tokenIsUsable(token)) {
    signOut();
    return null;
  }

  return token;
}

export type Session = {
  /** False until the browser's session has been read: show neither state before then. */
  mounted: boolean;
  token: string | null;
  /** Whose session it is, once the server has said - only ever for the token in use now. */
  user: SignedInUser | null;
};

export function useSession(): Session {
  const [mounted, setMounted] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  // The name is kept with the token it was fetched for, and shown only while that token is the one in
  // use, so a change of session can never leave the previous person's name on screen.
  const [resolved, setResolved] = useState<ResolvedSessionUser | null>(null);

  useEffect(() => {
    function refreshSessionState() {
      setToken(readUsableToken());
    }

    setMounted(true);
    refreshSessionState();

    const intervalId = window.setInterval(refreshSessionState, 60_000);

    window.addEventListener(SESSION_CHANGED_EVENT, refreshSessionState);
    window.addEventListener("storage", refreshSessionState);
    window.addEventListener("focus", refreshSessionState);
    document.addEventListener("visibilitychange", refreshSessionState);

    return () => {
      window.clearInterval(intervalId);
      window.removeEventListener(SESSION_CHANGED_EVENT, refreshSessionState);
      window.removeEventListener("storage", refreshSessionState);
      window.removeEventListener("focus", refreshSessionState);
      document.removeEventListener("visibilitychange", refreshSessionState);
    };
  }, []);

  // Who the token belongs to, asked of the server each time the session changes - a new sign-in in this
  // tab or another. Until the answer for this token arrives, and if it never does, no name is shown.
  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    fetch("/api/auth/me", { headers: { Authorization: `Bearer ${token}` } })
      .then((response) => (response.ok ? response.json() : null))
      .then((body) => {
        if (!cancelled) setResolved({ token, user: signedInUserFromResponse(body) });
      })
      .catch(() => {
        if (!cancelled) setResolved({ token, user: null });
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  return { mounted, token, user: userForToken(resolved, token) };
}
