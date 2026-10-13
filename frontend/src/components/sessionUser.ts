// Who is signed in, for the sidebar (owner's screen check, 22 September 2026: the application never
// said, so a tester moving between sales1 and finance1 had to remember which was current). Kept apart
// from SessionActions so it can be tested without a browser DOM.

export type SignedInUser = {
  display_name: string;
  roles: string[];
};

/** Read the current-user response, or null when it is not the shape expected. */
export function signedInUserFromResponse(body: unknown): SignedInUser | null {
  if (!body || typeof body !== "object") return null;
  const record = body as { display_name?: unknown; roles?: unknown };
  if (typeof record.display_name !== "string" || !record.display_name.trim()) return null;
  const roles = Array.isArray(record.roles) ? record.roles.filter((role): role is string => typeof role === "string") : [];
  return { display_name: record.display_name, roles };
}

/** The roles under the name. Empty when the server named none. */
export function signedInRolesText(user: SignedInUser): string {
  return user.roles.join(", ");
}

/** A name as fetched, with the session token it was fetched for. */
export type ResolvedSessionUser = {
  token: string;
  user: SignedInUser | null;
};

/**
 * The name to show for the session in use now, or null. A name fetched for an earlier token is never
 * shown for a later one: when the session changes - signing out and in as someone else in this tab or
 * another - the sidebar falls back to plain "Signed in" until the new session's own name arrives, and
 * stays there if that request fails or never answers (independent review, round 5, finding F-01).
 */
export function userForToken(resolved: ResolvedSessionUser | null, token: string | null): SignedInUser | null {
  if (!token || !resolved || resolved.token !== token) return null;
  return resolved.user;
}
