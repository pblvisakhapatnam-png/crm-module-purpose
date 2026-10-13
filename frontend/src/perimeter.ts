/**
 * Keeps the app's own sign-in token out of the `Authorization` header when a shared HTTP Basic
 * Auth login protects the whole site, as it does on the hosted CRM pilot (TE-5).
 *
 * A request carries one `Authorization` header. The pages put `Bearer <token>` there on every API
 * call, and a browser adds the site's Basic Auth login only to a request that has no
 * `Authorization` header of its own. Behind a Basic Auth proxy, every signed-in API call would
 * therefore be refused by the proxy before it reached the application.
 *
 * With this switched on, API requests carry the page's `Authorization` value in
 * PERIMETER_TOKEN_HEADER instead. The browser adds the Basic Auth login, the proxy checks and
 * removes it, and the nginx in front of the backend (frontend/nginx/default.conf) copies the token
 * back into `Authorization`. The backend is unchanged and still makes every access decision.
 *
 * Only same-origin `/api/` requests are touched, and only when `init.headers` carries an
 * `Authorization` header. A `Request` object passed as the first argument is left alone: no page
 * calls fetch that way, and rebuilding one would mean re-reading its body.
 */

export const PERIMETER_TOKEN_HEADER = "X-PBL-Authorization";

export function relocateAuthorization(
  input: RequestInfo | URL,
  init: RequestInit | undefined,
  origin: string,
): RequestInit | undefined {
  if (typeof Request !== "undefined" && input instanceof Request) {
    return init;
  }
  if (!init?.headers) {
    return init;
  }

  let url: URL;
  try {
    url = new URL(input instanceof URL ? input.href : String(input), origin);
  } catch {
    return init;
  }
  if (url.origin !== origin || !url.pathname.startsWith("/api/")) {
    return init;
  }

  const headers = new Headers(init.headers);
  const authorization = headers.get("Authorization");
  if (authorization === null) {
    return init;
  }
  headers.delete("Authorization");
  headers.set(PERIMETER_TOKEN_HEADER, authorization);
  return { ...init, headers };
}

export function installPerimeterFetchShim(target: Window = window): void {
  const originalFetch = target.fetch.bind(target);
  target.fetch = (input: RequestInfo | URL, init?: RequestInit) =>
    originalFetch(input, relocateAuthorization(input, init, target.location.origin));
}
