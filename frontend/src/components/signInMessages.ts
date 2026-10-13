// What a page says when nobody is signed in, or the server no longer accepts the session: one wording
// everywhere. The application says "Sign in" and "Sign out", never log in or log out (owner, 27 September
// 2026).

import { readErrorDetail } from "./errorDetail";

/** No session in this browser. */
export const SIGN_IN_FIRST = "Sign in first. No active session was found.";

/** The server refused the session: there is none, or it has ended. */
export const SIGN_IN_AGAIN = "Sign in first, or sign in again if your session has ended.";

/** A sign-in refused for its username or password. */
export const SIGN_IN_FAILED = "Sign-in failed. Check the username and password.";

/** A sign-in refused because its username is stopped, when the server's answer cannot be read. */
export const SIGN_IN_STOPPED = "Too many failed sign-ins for this username. Try again later.";

/**
 * Why the sign-in page's request was refused, for the message beside its button. A username stopped after repeated
 * wrong passwords (TB-1 TB1-204 part a) is answered 429, and the server says for how long.
 */
export async function signInRefusal(response: Response): Promise<string> {
  if (response.status === 429) return readErrorDetail(response, SIGN_IN_STOPPED);
  return SIGN_IN_FAILED;
}
